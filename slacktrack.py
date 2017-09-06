#! /usr/bin/env python3

"""
SlackTrack, v1.1

SlackTrack is a barebones Python utility to track user engagement on Slack. Given a set of Slack message export (JSON) files, SlackTrack produces a 
count of how many messages a user sent on each file. This data is then pushed to a Google Sheet of your choice through the Google Sheets API, where
the data can be compiled and analyzed. 

I do have plans to add further functionality soon.

-created by Rishu Harpavat, rharpavat on GitHub

---------------------------------------------------------------

Version Updates: 
- Organized code more efficiently
- Added comments and docstrings for better readability

"""

# Imports, including for Google Sheets API -----------------------------------------------------------------------------------------------------------

from __future__ import print_function
import httplib2
import os

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

from pprint import pprint

from googleapiclient import discovery

import json
from collections import Counter
import requests
import time

# Code -----------------------------------------------------------------------------------------------------------------------------------------------

def get_date(filename):
	"""
	Given a string filename, obtains the date.

	Input:
	filename - string representing the file name (formatted as a normal JSON export from Slack)

	Output:
	Returns the date the file contains message data for.
	"""

	return filename.split(".")[0]

def find_user_info(user_id):
	"""
	Given a user ID, queries the Slack API to find the user details. Returns a tuple containing
	the user's Slack username, full name, and email.

	Input:
	user_id - The Slack unique User ID of the user whose message is being checked

	Output:
	Tuple containing (Slack username, Full Name, Email)

	NOTE: Generate an authentication token with Slack and insert that into payload where specified.
	"""

	payload = {'token': 'insert-authentication-token-here', 'user': user_id} # PAYLOAD: INSERT TOKEN HERE
	r = requests.get('https://slack.com/api/users.info', params=payload)
	data = r.json()
	username = None
	fullname = None
	email = None
	if 'user' in data.keys():
		if 'profile' in data['user'].keys():
			if 'real_name' in data['user']['profile'].keys():
				fullname = data['user']['profile']['real_name']
			if 'email' in data['user']['profile'].keys():
				email = data['user']['profile']['email']
		if 'name' in data['user'].keys():
			username = data['user']['name']
		return [username, fullname, email]


def count_users(filename, subdir):
	"""
	Given a JSON file representing Slack message history, returns a dictionary mapping 
	usernames (keys) to how many times that user sent a message (values).

	Input:
	filename - string representation of the file being scanned
	subdir - string representation of the subdirectory that the file is located in

	Output:
	users - maps usernames (keys) to how many times that user sent a message in the given file (values).
	"""

	str_dir = str(subdir) + '/'

	user_count = Counter() # defines a new empty counter dictionary
	json_file = open(str_dir+filename) # opens the JSON file and closes it after all operations under it are finished
	try:
	    json_data = json.load(json_file) # loads the JSON data into a readable form (i.e. list of Python dictionaries)
	    for msg in json_data: # iterates through each message (dictionary) in the file
	    	if "user" in msg.keys():
	    		user = msg["user"] # finds the user ID of the user who sent the message
	    		user_count[user] += 1 # counts each occurrence
	finally:
		json_file.close()

	users = []
	for user, count in user_count.items():
		user_info = find_user_info(user)
		user_info.append(count)
		user_info.insert(0, get_date(filename))
		users.append(user_info)

	return users

# Google Sheets API Code ------------------------------------------------------------------------------------------------------------------------------

SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Google Sheets API Python Quickstart'

def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'sheets.googleapis.com-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

credentials = get_credentials()

http = credentials.authorize(httplib2.Http())
discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')
service = discovery.build('sheets', 'v4', http=http,
                              discoveryServiceUrl=discoveryUrl)


# BEFORE USING, DO THE FOLLOWING:
#    Insert the spreadsheet ID of the Google Sheet you wish to push the data to.
#    Insert the range of cells you want the data to occupy in the Google Sheet.
#    Insert the name of the root directory on your local hard drive containing the JSON logs of the Slack message exports.


# The ID of the spreadsheet to update.
spreadsheet_id = 'insert-spreadsheet-ID-here'

# Values will be appended after the last row of the table.
range_ = 'insert-data-range'

# How the input data should be interpreted.
value_input_option = 'RAW' 

# How the input data should be inserted.
insert_data_option = 'INSERT_ROWS' 


import os
rootdir = 'insert-root-directory-containing-JSON-logs'

ctr = 1
for subdir, dirs, files in os.walk(rootdir):
	for file in files:
		user_count = count_users(file, subdir)
		for user in user_count:
			value_range_body = {'values': [user]}
			request = service.spreadsheets().values().append(spreadsheetId=spreadsheet_id, range=range_, valueInputOption=value_input_option, insertDataOption=insert_data_option, body=value_range_body)
			response = request.execute()
			time.sleep(1)
			print("--------------------------")
			print(str(ctr)+" Requests Completed")
			print()
			ctr += 1