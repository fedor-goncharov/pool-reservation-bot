from datetime import datetime
from sessions_utils import get_sessions_list, put_sessions_list
import validators

CHECK_SESS_CORRECT, CHECK_SESS_DATE_ERR_BAD_FORMAT, CHECK_SESS_ERR_DATE_PASSED, CHECK_SESS_ERR_DATE_DELAY = range(4) # list of error codes

datetime_format = '%d/%m/%Y %H:%M'
min_delay_time_sec = 300 # timedelay between two events cannot be less than 5 minutes

def check_new_datetime(datetime_str, sessions_file):
	"""
	Description:
		Check if new datetime is a valid: 
	
		1. Registration moment is later than 'now' (cannot register in the past)
		2. New date is at least 5 mins separated from other dates

	"""

	# 1. Check that date is later than 'now'

	new_datetime = None

	try:
		new_datetime = datetime.strptime(datetime_str, datetime_format)
	except ValueError:
		err_code = CHECK_SESS_ERR_BAD_FORMAT
		err_msg = 'CHECK_SESS_ERR_BAD_FORMAT: date {} is of bad format.'.format(datetime_str)
		return err_code, err_msg

	now = datetime.now()
	if (new_datetime < now):
		err_code = CHECK_SESS_ERR_DATE_PASSED
		err_msg = 'CHECK_SESS_ERR_DATE_PASSED: date {} is too late.'.format(datetime_str)
		return err_code, err_msg

	# 2. Read session-list from file

	sessions_list = get_sessions_list(sessions_file)
	for session in sessions_list:
		session_datetime = datetime.strptime(session['datetime'], datetime_format)
		delay_sec = abs((session_datetime - new_datetime).total_seconds())
		if (delay_sec < min_delay_time_sec):
			err_code = CHECK_SESS_ERR_DATE_DELAY
			err_msg = 'CHECK_SESS_ERR_DATE_DELAY: date {} is too close to already existing session on {}.'.format(datetime_str, session['datetime'])
			return err_code, err_msg

	return CHECK_SESS_CORRECT, ''


def check_new_url(url_str):
	"""
		Function checks correct correctness of the url (only syntax) 
		using validators library.  
	"""

	return validators.url(url_str)