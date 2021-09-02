import requests
from os import environ as env

USERNAME = env['username']
PASSWORD = env['password']

SECRET = env['secret']
CLIENT_ID = env['client_id']


def authorize():
	
	"""
	Get OAuth2 authorization to be able to use Reddit's api
	Returns headers needed to let Reddit know you are the one making the request
	"""

	post_data = {
		'grant_type': 'password',
		'username': USERNAME,
		'password': PASSWORD
	}
	headers = {
		'User-Agent': f'test by {USERNAME}'
	}

	client_auth = requests.auth.HTTPBasicAuth(CLIENT_ID, SECRET)
	response = requests.post('https://www.reddit.com/api/v1/access_token?duration=permanent',
							 auth=client_auth, data=post_data, headers=headers)
	token = response.json()['access_token']

	return {
		'Authorization': 'bearer ' + token,
		'User-Agent': 'Old_submissions by ' + USERNAME
	}


def submit(title, sr, url, kind, headers):

	# kind = one of (link, self, image, video, videogif)

	data = {
		'sr': sr,		# subreddit
		'url': url,
		'title': title,
		'kind': kind,	# kind of submission (video, self...)
		'api_type': 'json',

		'nsfw': False,
		'spoiler': False,
		'resubmit': True,
		'sendreplies': True,
		'validate_on_submit': True
	}

	response = requests.post(
		'https://oauth.reddit.com/api/submit', headers=headers, data=data)

	return response.json()


def comment(body, fullname, headers):
	
	data = {
		'text': body,
		'api_type': 'json',
		'thing_id': fullname,
		'return_rtjson': True
	}
	response = requests.post(
		'https://oauth.reddit.com/api/comment', headers=headers, data=data)
	
	return response.json()


def crosspost(title, sr, crosspost_fullname, headers):
	
	# In case you would rather crosspost a submission

	data = {
		'sr': sr,
		'title': title,
		'kind': 'crosspost',
		'api_type': 'json',
		'crosspost_fullname': crosspost_fullname,

		'nsfw': False,
		'spoiler': False,
		'resubmit': True,
		'sendreplies': True,
		'validate_on_submit': True
	}

	response = requests.post(
		'https://oauth.reddit.com/api/submit', headers=headers, data=data)

	return response.json()
