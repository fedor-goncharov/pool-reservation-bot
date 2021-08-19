from selenium import webdriver
import selenium
from pyvirtualdisplay import Display

from datetime import datetime
import time
import signal


def reservation_process(datetime_str, url_str, configuration):

	def reservation_process_signal_callback(signum, stack, datetime_str, url_str, browser, display):
		
		# on SIGINT, SIGTERM, SIGKILL 
		if browser is not None:
			browser.quit()

		if display is not None:
			display.stop()

		sys.exit('Gracefully stopped the reservation subprocess PID {} the serivce with signal {}.'.format(os.pid(), signum))

	
	page_reload = configuration['page_reload_n']
	browser_delay = configuration['browser_delay_t']
	reload_delay = configuration['reload_delay_t']

	registration_datetime = datetime.strptime(datetime_str, '%d/%m/%Y %H:%M')
	registration_done = False
	browser = None
	display = None

	# init catch calls SIGINT, SIGTERM
	# (signals from the parent process, unfortunately cannot be catched independently)

	signal.signal(signal.SIGINT, lambda signum, stack: reservation_process_signal_callback(signum, stack, 
		datetime_str=datetime_str, url_str=url_str, browser=browser, display=display))
	signal.signal(signal.SIGTERM, lambda signum, stack: reservation_process_signal_callback(signum, stack, 
		datetime_str=datetime_str, url_str=url_str, browser=browser, display=display))
	

	# sleep before before registration opening
	waiting_time = (registration_datetime - datetime.now()).total_seconds() - browser_delay
	if (waiting_time < 0.0):
		waiting_time = 0.0
		
	time.sleep(waiting_time)

	# open browser
	chrome_options = webdriver.ChromeOptions()
	chrome_options.add_argument('--headless')
	chrome_options.add_argument('--no-sandbox')
	display = Display(visible=0, size=(800, 600)) # start virtual display
	display.start() 

	browser = webdriver.Chrome()

	# input login and password in the fields
	browser.get('') # loging page 
	username = browser.find_element_by_id('') # find login / email
	username.send_keys('') # type login / mail
	passw = browser.find_element_by_id('') # find passwd
	passw.send_keys('') # type passwd

	# click login button
	loginButton = browser.find_element_by_name('') # find button
	loginButton.click()

	# go to the reservation page and click reserve
	browser.get(url_str) # load page

	while True: 

		date_now = datetime.now()

		if (date_now >= registration_datetime):

			# click reservation button (should be the only one on the page)
			ntries = 0
			while ((ntries < page_reload) and (registration_done == False)):

				browser.get(url_str) # load page
				try:
					reserveButton = browser.find_element_by_name('') # find `reserve` click
					reserveButton.click() # click `reserve`
					registration_done = True
	
				except selenium.common.exceptions.NoSuchElementException as e:
					ntries += 1
					
				time.sleep(reload_delay)			
			break

		else:
			time.sleep(0.01)

	# TODO
	# send screenshot to the user as a report
	browser.save_screenshot('res_scr.png')
	
	browser.quit()
	display.stop()
