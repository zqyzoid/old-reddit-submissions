from requests.exceptions import (
	ReadTimeout,
	Timeout
)
import requests
import datetime
import urllib
import reddit
import shelve
import time
import re


HOUR = 60 * 60
DAY = HOUR * 24
MONTH = DAY * 31

DEFAULT_SLEEP = 20		# Amount of seconds script should wait before trying to send another request
DEFAULT_TIMEOUT = 60	# Default timeout for a request, in seconds


def get_req(url, session=None, headers=None, timeout=DEFAULT_TIMEOUT, sleep=DEFAULT_SLEEP):

	"""Get request with some default parameters"""

	try:
		if session == None:
			get = requests.get(url, timeout=timeout, headers=headers)
		else:
			get = session.get(url, timeout=timeout, headers=headers)
		return get

	except (ReadTimeout, Timeout):
		time.sleep(sleep)
		return get_req(url, session, headers, timeout, sleep)

	except KeyboardInterrupt:
		raise KeyboardInterrupt

	except:
		return RequestDummy()


def get_submissions(subreddit, after, before):
	
	"""Get a list of submisions made within 'after' - 'before' range using the pushshift api
	Each element of the list is a json with info about the submission (date, url, subreddit...)"""

	pushshift_url = 'https://api.pushshift.io/reddit/submission/search?'

	params = {
		'size': 100,
		'sort': 'desc',			# Most upvoted come first
		'after': after,
		'score': '>10',			# Submissions with a score > 10, mostly to filter out spam
		'before': before,
		'subreddit': subreddit,
		'sort_type': 'score'
	}

	url = pushshift_url + urllib.parse.urlencode(params)
	fetch = get_req(url)
	return fetch.json().get('data', [])


def extension(url):

	"""Returns True if url has extension. E.g: 'https://i.redd.it/nq3r9r9fxvl11.jpg' has .jpg"""

	pattern = r'\.(gifv?|jpe?g|png)($|\?)'
	match = re.search(pattern, url, flags=re.IGNORECASE)

	if match == None:
		return False
	else:
		return True


def has_slur(string):
	
	"""Check if there's one of the following slurs in the title"""

	slurs = ('nigg', 'fag', 'cunt')
	string = string.lower()

	for slur in slurs:
		if slur in string:
			return True
	else:
		return False


def subm_removed(url):

	"""Returns True if reddit submission has been removed, None otherwise"""

	# User agent is needed as reddit won't accept your request if you use requests library default user agent
	user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'\
	'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36'
	fetch = get_req(url + '.json', headers={'user-agent': user_agent})

	# reddit is down
	if fetch.json() == {}:
		return True
	else:
		# if submission hasn't been removed, this should equal None
		return fetch.json()[0]['data']['children'][0]['data']['removed_by_category']


def img_removed(url):

	"""Check wheter or not an image has been deleted."""
	# Isn't perfect but it does the job


	imgur_removed = 'https://i.imgur.com/removed.png'
	fetch = get_req(url)

	if fetch.status_code != 200 or fetch.url == imgur_removed:
		return True
	else:
		return False


def format_epoch(epoch):

	"""
	Turn epoch date to human readable date
	1630547957 -> 2021-09-01 22:59:17
	"""

	return datetime.datetime.fromtimestamp(epoch).strftime('%Y-%m-%d %H:%M:%S')


class RequestDummy(requests.models.Response):

	"""In case something goes wrong in the get_req function, return an instance"""

	def __init__(self):
		self.status_code = 404
		self.history = []
		self.url = 'http://example.com'

	def json(self):
		return {}


class PushShiftJson:

	"""Class to be able to access elements as attributes rather than by subscription"""
	# It just looks better this way ;)

	def __init__(self, json):
		self.url 			= json['url']
		self.title 			= json['title']
		self.score			= json['score']
		self.author 		= json['author']
		self.domain			= json['domain']
		self.is_self		= json['is_self']
		self.over_18 		= json['over_18']
		self.full_link 		= json['full_link']
		self.created_utc 	= json['created_utc']
    
		# more info on what a fullname is -> https://www.reddit.com/dev/api/
		# t3_ as I'm asumming this will be used for submissions and not comments
		self.fullname		= 't3_' + json['id']


class PersistenVars:

	"""Class to keep variables persistent in case I have to reset the script"""
	# *Using the shelve module

	def __init__(self, file_path):
		self.file_path = file_path

		try:
			with shelve.open(file_path, 'r') as content:
				self._after = content['after']
				self._index = content['index']
		except:
			print('File doesn\'t exist, use start_shelve() to create file with chose values')
		

	def shelve_set(self, key, value):
		with shelve.open(self.file_path) as content:
			content[key] = value


	@property
	def after(self):
		return self._after
	
	@after.setter
	def after(self, value):
		self._after = value
		self.shelve_set('after', value)

	@property
	def index(self):
		return self._index
	
	@index.setter
	def index(self, value):
		self._index = value
		self.shelve_set('index', value)



def main():

	path_persistent_variables = ''
	pv = PersistenVars(path_persistent_variables)

	subreddit_search = ''	# Subreddit where you'll look for old submissions
	subreddit_submit = ''	# Subreddit where you'll submit

	# Allowed domains for submission's url
	allowed = {
		'imgur.com',
		'i.imgur.com',
		'm.imgur.com'
		'i.redd.it',
		'i.reddituploads.com',
		'24.media.tumblr.com'
	}
	STEP = MONTH
	PAUSE_AFTER_SUBMISSION = HOUR * 2


	while True:

		# Get submissions submitted after pv.after, before pv.after + STEP
		submissions = get_submissions(subreddit_search, pv.after, pv.after + STEP)

		for idx, json in enumerate(submissions):

			submission = PushShiftJson(json)

			# This should only occur if I reset the script.
			if idx < pv.index:
				continue
			else:
				pv.index = idx

			# Remove over 18 submissions and text submissions
			# ... and those that have a slur in the title
			if submission.over_18 or submission.is_self or has_slur(submission.title):
				continue

			# Continue if submission domain is not in allowed
			# Exceptions can be made if the url linked has a file extension like .jpg, .gif
			if submission.domain not in allowed and not extension(submission.url):
				continue

			# Continue if submission or image have been removed / deleted
			if subm_removed(submission.full_link) or img_removed(submission.url):
				continue
			

			comment = 'Submission made by u/{} at {}. Link to original post: {}'.format(
			submission.author, format_epoch(submission.created_utc), submission.full_link)

			headers = reddit.authorize()

			
			# TODO: add case where "submitted" fails
			submitted = reddit.submit(
				title=submission.title,
				sr=subreddit_submit,
				url=submission.url,
				headers=headers
			)

			commented = reddit.comment(
				body=comment,
				fullname=submitted['json']['data']['name'],
				headers=headers
			)
			
			time.sleep(PAUSE_AFTER_SUBMISSION)

		pv.after += STEP

if __name__ == '__main__':
	main()
