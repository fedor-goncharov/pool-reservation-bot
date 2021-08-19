from datetime import datetime
import time
import json
from sessions_utils import get_sessions_list, put_sessions_list
from reservation_process import reservation_process


import signal
import os
import sys
from multiprocessing import Process

import logging
logging.basicConfig(
	filename='reservation_service.log',
	filemode='a',
	level=logging.DEBUG, 
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(name='reservation_service')


datetime_format = '%d/%m/%Y %H:%M'



# write log to file and to console
def get_configuration(config_file):
	"""
		Get configuration of the service from the JSON configuration file 
	"""

	try:
		read_file = open(config_file, 'r', encoding='utf-8')
	except FileNotFoundError:
		logger.error('No config file found in {}.',format(config_file))
		sys.exit('Config file along {} is missing'.format(config_file))

	configuration = json.load(read_file)
	read_file.close()

	return configuration

def reservation_service_signal_callback(signum, stack, reservation_proc):
	
	# on recievng a stop signal in the main service process stop the work gently:
	# 1.) kill the subprocess for next reservation with SIGTERM
	# 2.) logs, etc.

	logger.info('Main Service process PID {}, recieved signal {}'.format(pid, signum))

	if reservation_proc is not None:

		pid = reservation_proc.pid

		logger.info('Service subrocess PID {} will recieve signal SIGTERM.'.format(pid))
		reservation_kill(reservation_proc, signal.SIGTERM)
		logger.info('Service subrocess PID {} was killed.'.format(pid))


def reservation_service(sessions_file, sessions_passed_file, config_file):

	"""
		Description:

			Service that continuosly checks file with sessions 
			and runs a single subprocess to perform registrations. 
			Session entries are sorted according date and for the 
			earliest a reservation subprocess is spawned which will 
			perform a reservation at a given time. When an earlier 
			session entry appears - old process is killed and a new 
			one is spawned.

			Service can be stopped on recieving SIGINT, SIGTERM or SIGKILL (Unix) signals, 
			then for SIGINT, SIGTERM it will try to finalize itself gracefully
			by killing spawned subprocess
			(if there is one) and freeing used resources.

		Input:

			sessions_file : file with the database of scheduled sessions
			sessions_passed_file : file with the database of passed sessions
			config_file : configuration file with parameters for the reservation subprocess (browser 
			parameters etc.).

		Output:

			No output / looped

	"""

	cur_datetime_str = ''
	cur_url_str = ''
	proc = None # Process class for the recent reservation

	# check configuration file exists
	configuration = get_configuration(config_file) # initialize configuration

	logger.info('Service process started.')

	signal.signal(signal.SIGINT, lambda signum, stack: reservation_service_signal_callback(signum, stack, 
		reservation_proc = proc))
	signal.signal(signal.SIGTERM, lambda signum, stack: reservation_service_signal_callback(signum, stack, 
		reservation_proc = proc))
	

	while True: # run forever (until (stop) signal is recieved)

		# 1. read sessions_list and sort / clean the list on the passed elements
		sessions_list = get_sessions_list(sessions_file)
		sessions_passed_list = get_sessions_list(sessions_passed_file)
		now = datetime.now()
		sessions_passed = 0

		for session in sessions_list:
			session_datetime = datetime.strptime(session['datetime'], datetime_format)
			delay = now - session_datetime
			if (delay.total_seconds() > configuration['update_delay_t']):
				session['passed'] = True
				sessions_passed += 1
				sessions_passed_list.append(session)
			else:
				break
		
		# remove passed sessions and write them to the file
		sessions_list = sessions_list[sessions_passed:] # removed passed ones from the list

		if (len(sessions_passed_list) > configuration['max_passed_n']): # keep only limited amount of passed sessions
			sessions_passed_list = sessions_passed_list[:-configuration['max_passed_n']]
		put_sessions_list(sessions_list, sessions_file)
		put_sessions_list(sessions_passed_list, sessions_passed_file)

		
		# 2. Check on current reservation processes
		if (len(sessions_list) == 0): #if no more reservations left
			if proc is not None:
				
				# 2.1 kill the current reservation process since it runs too long 
				# (more than update_delay_t)

				logger.info('New session list is empty, max awaiting time exceeded, service subprocess PID {} will recieve signal {}.'.format(proc.pid, signal.SIGTERM))
				reservation_kill(proc, signal.SIGTERM)
				logger.info('Subprocess PID {} was terminated.'.format(proc.pid))

				cur_datetime_str = ''
				cur_url_str = ''
				proc = None
				
		else:
			next_datetime_str = sessions_list[0]['datetime']
			next_url_str = sessions_list[0]['url']
			if ((cur_datetime_str != next_datetime_str) or (cur_url_str != next_url_str)):
				
				# send signal to kill the the `older` process
				if proc is not None:
					
					logger.info('Younger event found: date {}, url {}, older service subprocess PID {} will recieve signal {}.'.format(next_datetime_str, next_datetime_str, proc.pid, signal.SIGTERM))
					reservation_kill(proc, signal.SIGTERM)
					logger.info('Subprocess PID {} was terminated.'.format(proc.pid, signal.SIGTERM))

					cur_datetime_str = ''
					cur_url_str = ''
					proc = None
					

				
				# start new reservation process
				configuration = get_configuration(config_file)
				proc = reservation_call(next_datetime_str, next_url_str, configuration)
				logger.info('Younger subprocess spawned for date {}, url {} at PID: {}'.format(next_datetime_str, \
					next_datetime_str, proc.pid))

				# save parameters of the new process in variables
				cur_datetime_str = next_datetime_str
				cur_url_str = next_url_str


		# sleep between checks
		time.sleep(configuration['update_delay_t'])

	# should never get here
	return


def reservation_call(datetime_str, url_str, configuration):
	"""
		Description:
			Function spawns a subprocess that waits for the good date 
			and then runs the registration.

		Output: 
			multiprocessing.Process class of the spawned subprocess
	"""

	proc = Process(target=reservation_process, args=(datetime_str, url_str, configuration,))
	proc.start()

	return proc

def reservation_kill(reservation_proc, signum):
	"""

		Description:
			
			Function kills the reservaton subprocess related to 
			reservation of the nearest session.
	Input:

		reservation_proc : multiprocessing.Process class for the spanwed
		signal : signal with which the process is killed

		If the subprocess is not killed via standard SIGTERM, bruteforce 
		SIGKILL is applied.

	Output:

		err_code, err_msg - error and code 

	"""

	if reservation_proc is not None:

		# kill softly using multiprocessing lib
		pid = reservation_proc.pid
		reservation_proc.terminate()

		# check if process exists
		try:
			os.kill(pid, 0)
		except OSError:
			logger.warning('Subrocess {} was killed softly via proc.terminate()'.format(pid))
			return
		# process is still not killed
		else:
			try:
				os.kill(pid, signal.SIGKILL)
				logger.warning('Wasn\'t able to kill the process {} softly via proc.terminate(). Used SIGKILL.'.format(pid)) # if got here, process was not killed
			except OSError as ex:
				logger.error('Received OSError when killing the subprocess {} via SIGKILL. Performing sys.exit()'.format(pid))
				sys.exit('Could not kill child process, PID: '.format(pid))

reservation_service(sessions_file='sessions.lst', 
	sessions_passed_file = 'sessions_passed.lst', 
	config_file='user.config')