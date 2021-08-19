from datetime import datetime
import json

"""
sessions_utils - manipulation with reserviations sessions through their files.

"""

datetime_format = '%d/%m/%Y %H:%M'
CORRECT, ERR_NO_FILE, ERR_FILE_BUSY, ERR_JSON, ERR_IO = range(5)

def add_new_session(new_datetime_str, new_url_link_str, sessions_file):
	"""
		Description:

			1) Read sessions from sessions_file
			2) Add new record to the list of sessions and sort the new list w.r.t. to datetime
			3) Stores back new list in sessions_file
		
		Input:
			new_datetime_str : string : date and time in of the reservation datetime_format
			new_url_link_str : string : url of the reservation page
			sessions_file    : string : name of the file, where all sessions are stored

		Output: 
			exit_code, exit_msg 
			If exit_code > 0, then some error happened and no new element is added to the list.
			Error message is returned in exit_msg, if no error was produced exit_msg = ''.

		Returned errors:
			TODO...

	"""
	# 1. read list of sessions from sessions_file
	sessions_list = get_sessions_list(sessions_file)

	# new element
	new_session = {
			'datetime' : new_datetime_str, 
			'url'      : new_url_link_str,
			'passed'   : False
		}	

	# 2. check that new record is correct, etc.


	# append new element and resort the list by the date
	sessions_list.append(new_session)
	new_sessions_list = sorted(sessions_list, 
		key=lambda k: datetime.strptime(k['datetime'], datetime_format))

	# 3. write the new list back to sessions_file
	err_code, err_msg = put_sessions_list(new_sessions_list, sessions_file)

	return err_code, err_msg

def get_sessions_list(sessions_file):
	""" 
		Get session_list from JSON sessions_file .
	"""

	sessions_list = []
	with open(sessions_file, 'r', encoding='utf-8') as read_file:
		try:
			sessions_list = json.load(read_file)
			read_file.close()
		except ValueError:
			sessions_list = []


	return sessions_list



def put_sessions_list(sessions_list, sessions_file):
	"""
		Write session_list to sessions_file
	"""
	with open(sessions_file, 'w', encoding='utf-8') as output_file:
		try:
			json.dump(sessions_list, output_file)
			output_file.close()
		except ValueError as err:
			err_code = ERR_JSON
			err_msg = 'json error: ' + str(err)
			return err_code, err_msg

	# no errors during writing of the new list
	err_code = 0
	err_msg = ''

	return err_code, err_msg


def delete_all_sessions(sessions_list):
	"""
		Make sessions_list empty
	"""
	try:
		open(sessions_list, 'w').close()
	except Exception as e:
		err_code = ERR_IO
		err_msg = str(e)
		return err_code, err_msg

	return 0, ''

def delete_session(sessions_file, session_number):
	"""
		Delete session with specific number"
	"""

	# get list of all sessions
	err_code = CORRECT
	err_msg = ''

	sessions_list = get_sessions_list(sessions_file)
	if (session_number >= 0 and session_number < len(sessions_list)):
		sessions_list.pop(session_number)
		err_code, err_msg = put_sessions_list(sessions_list, sessions_file)
	else:
		err_code = ERR_IO
		err_msg = 'Session number is out of bounds.'

	return err_code, err_msg


