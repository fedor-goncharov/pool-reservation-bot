from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, ConversationHandler, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from functools import wraps
import tabulate # print sessions list as a table
import json


from check_new_session import check_new_datetime, check_new_url
from sessions_utils import add_new_session, get_sessions_list, delete_all_sessions, delete_session

# global configuration
token = ""
config_file_default = 'default.config' 
config_file_user = 'user.config'
log_file_bot = 'reservation_bot.log'
log_file_reservation = 'reservation_service.log'
bot_activated = True

import logging 
logging.basicConfig(
	filename=log_file_bot,
	filemode='a',
	level=logging.DEBUG, 
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger('reservation_bot') # store to reservation_bot.log 

DATETIME, URL_LINK, PROCESS_NEW_SESSION = range(3)
DEFAULT_NLINES_DUMP = 10

restricted_user_list = []
restricted_admin_list = []


# restrction decorator - only restricted users can run user commands
def restricted(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in restricted_user_list:
            logger.info("Unauthorized user call: {}\n".format(user_id))
            return
        return func(update, context, *args, **kwargs)
    return wrapped

# admin decorator - only restricted users can run admin commands
def admin(func):
	@wraps(func)
	def wrapped(update, context, *args, **kwargs):
		user_id = update.effective_user.id
		if user_id not in restricted_admin_list:
			logger.info("Unauthorized admin call: {}\n".format(user_id))
			return
		return func(update, context, *args, **kwargs)
	return wrapped

# activation decorator
def activated(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        global bot_activated
        if (bot_activated == False):
        	update.effective_message.reply_text('Hi! To know more about me you need to activate me.\n'
        		'Type /start to proceed.')
        	return
        return func(update, context, *args, **kwargs)
    return wrapped





@restricted 
def start(update, context):
	
	"""
		Bot is activated.

	"""

	global bot_activated

	if (bot_activated == False):

		bot_activated = True
		help_command(update, context)

	else:

		update.message.reply_text('Hi! I am already activated. Type /help to see my commands.')

	return

# help message with all commands and descriptions
help_message = ['Basic user commands:\n\n',
				'/start - activate the bot\n', 
				'/addsession - add new swimming session\n',
				'/printsessions - print the indexed list of all swimming sessions\n',
				'/deletesession [index] - delete session with (integer) index [n]\n',
				'/deleteall - delete all existing sessions\n',
				'\n',
				'Advanced configuration commands:\n\n',
				'/configprintuser - show user configuration\n',
				'/configprintdefault - show default configuration\n'
				'/configset [key] [value] - set [value] in [key] in the config\n',
				'/configreset - reset all configuration settings to default ones\n',
				'\n',
				'Info commands:\n\n',
				'/help - print the help message\n',
				'/about - print contact information\n' 
				'\n',
				'Log-info (admin permission required):\n\n',
				'/logdumpbot [value = 10] - dump lines from the bot-log\n'
				'/logdumpres [value = 10] - dump lines from the reservation-log\n' 
				]

@restricted
@activated
def help_command(update, context):

	update.message.reply_text(''.join(help_message))
	return

@restricted
@activated
def addsession(update, context):
	"""
		Add new swimming session to the list. 
	"""
	update.message.reply_text('Ok, for this I will need two items:\n\n'
		'1. Date and time of the registration opening (your local time)\n' 
		'2. URL-link to the session page\n\n' 
		'You can always cancel the input of a new session by typing /cancel.')

	update.message.reply_text('Let\'s start with the first one.\n\n' 
		'When does the registration open for your swimming session?\n' 
		'Please, send me the date and time in the following format:\n\n'
		'dd/mm/yyyy hh:mm')

	return DATETIME

def addsession_datetime(update, context, sessions_file):
	"""
		Read datetime string, check that it has valid format.
		If yes, ask url-link for the swimming session, 
		if no , re-enter the datetime
	"""

	datetime_str = update.message.text

	# check that new datetime is a valid one
	check_code, check_err_msg = check_new_datetime(datetime_str, sessions_file)

	# datetime of incorrect format
	if (check_code > 0):
		logger.info('User %s entered incorrect datetime.', update.message.from_user)
		update.message.reply_text('Oops, there is a problem with your date: {}\n'.format(check_err_msg) +  
		'Please, retype the date and time in the following format:\n\n'
		'dd/mm/yyyy hh:mm')
		return DATETIME

	# store timedate in the context
	context.user_data['datetime-str'] = datetime_str

	# entered date is correct, now get url
	update.message.reply_text('Thank you.\n'
		'Now, please type below the url-link of your swimming session.')

	return URL_LINK

def addsession_url_link(update, context):
	
	"""
		Read url-link string, check that it has valid format.
		Ask to accept the new record.
	"""
	
	url_link = update.message.text

	url_link_valid = check_new_url(url_link)
	if (not url_link_valid):
		update.message.reply_text('Oops, your link is not a valid URL-link.\n'
		'Please, retype the URL-link in a good format.')
		return URL_LINK

	context.user_data['url-str'] = url_link
	update.message.reply_text('Thank you.\n')

	# query to finalize adding new session
	keyboard = [
		[ 
			InlineKeyboardButton("Yes", callback_data='Yes'), 
			InlineKeyboardButton("No",  callback_data='No'),
		]
	,]
	reply_markup = InlineKeyboardMarkup(keyboard)

	update.message.reply_text('So, you want to add a session with the following parameters, right?\n\n'
		'Date and time: {}\nURL-link: {}\n'.format(context.user_data['datetime-str'], context.user_data['url-str']),
		reply_markup = reply_markup)
	
	return PROCESS_NEW_SESSION

def addsession_process(update, context, sessions_file):

	query = update.callback_query
	query.answer()
	add_decision = query.data

	if (add_decision == 'No'):	# if final decision is not to add
		context.user_data.clear()
		query.edit_message_text(text='Adding session was cancelled.')
		return ConversationHandler.END

	elif (add_decision == 'Yes'): # if final decision is to add
		err_code, err_msg = add_new_session(
			context.user_data['datetime-str'], 
			context.user_data['url-str'],
			sessions_file=sessions_file
		)

		if (err_code > 0):
			logger.error('Failed to add new session, error code %d, error message: %s', err_code, err_msg)
			update.message.reply_text('New session was not added due to some error.\n'
				'Please, contact the support at /about.')
		else:
			query.edit_message_text(text='New session was added.')

	return ConversationHandler.END

def addsession_cancel(update, context):
	"""
		User called - cancel current input of a new session
	"""

	# clear context - remove temporary record
	context.user_data.clear()

	logger.info("Adding new session was canceled by user %s", update.effective_message.from_user)
	update.message.reply_text('Ok, adding new session was canceled.')

	return ConversationHandler.END

def addsession_unkown(update, context):
	"""

		Uknown command during adding new session, cancel conversation.

	"""
	user = update.message.from_user
	logger.info("User %s called unknown command while adding new session.", user.first_name)
	
	user_data = context.user_data
	user_data.clear()

	update.message.reply_text('You called an unknown command while adding new session.\n'
		'I cancel this attempt - no session will be added.')

	return ConversationHandler.END


@restricted
@activated
def printsessions(update, context, sessions_file, sessions_passed_file):
	"""

		Print all existing sessions (future and passed) as a Markdown table

	"""

	sessions_list = get_sessions_list(sessions_file)
	sessions_passed_list = get_sessions_list(sessions_passed_file)
	sessions_all_list = sessions_list + sessions_passed_list

	if (len(sessions_all_list) == 0):
		update.effective_message.reply_text('Session list is empty.\n')
		return

	else:
		headers = ('Date/Time', 'URL', 'Passed')
		rows = [session.values() for session in sessions_all_list]
		tab_all_sessions_list = "```" + tabulate.tabulate(rows, headers, tablefmt="simple", showindex="always") + "```"
		update.effective_message.reply_text(tab_all_sessions_list, parse_mode="Markdown")

	return

@restricted
@activated
def deletesession(update, context, sessions_file):
	"""

		Delete session from the future ones with some specific index

	"""
	# convert argument to integer
	try:
		if (len(context.args) == 0):
			update.effective_message.reply_text('This command requires an integer argument.\n' 
				'For example, to delete session with index n type:\n /deletesession n\n\n'
				'Type /help to see how to use this command.')
			return

		session_number = int(context.args[0])
	except ValueError:
		update.effective_message.reply_text('Your argument is not an integer number.\n'
			'Type /help to see commands and /printsessions to see all your sessions.')
		return

	err_code, err_msg = delete_session(sessions_file, session_number)
	if (err_code > 0):
		logger.info('User %s tried to delete session with number %d: %s', update.effective_message.from_user, session_number, err_msg)
		update.effective_message.reply_text('Session with such number does not exist.\n'
			'Type /help to see commands and /printsessions to see all your reservations.')
		return
	else:
		update.effective_message.reply_text('Session {} was removed.'.format(session_number))

	return


@restricted
@activated
def deleteall(update, context, sessions_file):
	"""
		Delete all existing sessions from sessions_file
	"""
	err_code, err_msg = delete_all_sessions(sessions_file)
	update.effective_message.reply_text('All sessions were deleted.')
	return

@restricted
@activated
def about(update, context):
	
	update.message.reply_text('I was created by Fedor Goncharov.'  
		'To contact my creator, write to any of the following addresses:\n\n' 
		'email: fedor.goncharov.ol@gmail.com\n'
		'Telegram: @FGoncharov')


@restricted
@activated
def configprintuser(update, context, config_file_user):

	f = open(config_file_user, 'r', encoding='utf-8')
	configuration = json.load(f)
	f.close()

	pretty_config_str = '```\n' + json.dumps(configuration, indent=4) + '\n```'
	update.message.reply_text(pretty_config_str, parse_mode='MarkdownV2')


@restricted
@activated
def configset(update, context, config_file_user):

	if (len(context.args) < 2):
		update.message.reply_text('Two arguments are needed: /configset [key] [value-float]')
		return

	# get key-values arguments
	key = context.args[0]
	value = context.args[1]

	# open file to read current configuration
	f = open(config_file_default, 'r', encoding='utf-8')
	configuration = json.load(f)
	f.close()

	# set key-value and restore configuration in file
	if key not in configuration.keys():
		update.message.reply_text('The key ({}) does not exist in the configuration.'.format(key))
		return
		
	try:

		configuration[key] = type(configuration[key])(value)

	except ValueError:
		update.message.reply_text('Second argument is of bad type. Configuration was not changed.')
		return

	# store new configuration in the user configuration
	f = open(config_file_user, 'w', encoding='utf-8')
	json.dump(configuration, f)
	f.close()

	# send au-revoir message
	update.message.reply_text('Configuration was saved successfully.')




@restricted
@activated
def configreset(update, context, config_file_user, config_file_default):

	f = open(config_file_default, 'r', encoding='utf-8')
	configuration = json.load(f)
	f.close()

	f = open(config_file_user, 'w', encoding='utf-8')
	json.dump(configuration, f)
	f.close()

	# send au-revoir message
	update.message.reply_text('Configuration was to default.')


@restricted
@activated
def configprintdefault(update, context, config_file_default):
	
	f = open(config_file_default, 'r', encoding='utf-8')
	configuration = json.load(f)
	f.close()

	pretty_config_str = '```\n' + json.dumps(configuration, indent=4) + '\n```'
	update.message.reply_text(pretty_config_str, parse_mode='MarkdownV2')



@admin
@activated
def logdumpbot(update, context, log_file_bot):

	try:
		f = open(log_file_bot, 'r', encoding='utf-8')
	except OSError:
		logger.info('Could not open/read file:', log_file_bot)
		update.message.reply_text('INFO: Could not open bot log-records.')
		return

	lines = f. readlines()
	num_lines_to_dump = int(0)


	# read number of lines to dump
	if (len(context.args) == 0):
		num_lines_to_dump = DEFAULT_NLINES_DUMP
	else:
		try:
			num_lines_to_dump = int(context.args[0])
		except ValueError:
			update.effective_message.reply_text('The argument you \' provided is not an integer number.\n'
				'Type /help to see how to use commands.')
			return

	if (num_lines_to_dump <= 0):
		update.effective_message.reply_text('You asked {} lines for the output. It is empty.'.format(num_lines_to_dump))
		return

	dump_lines = lines[-num_lines_to_dump:]
	if len(dump_lines) > 0:
		update.message.reply_text( '```\n' + ''.join(dump_lines) + '\n```', parse_mode='MarkdownV2')
	else:
		update.message.reply_text('Log-file is empty.')


@admin
@activated
def logdumpres(update, context, log_file_reservation):

	try:
		f = open(log_file_reservation, 'r')

	except OSError:
		logger.info('Could not open/read file:', log_file_reservation)
		update.message.reply_text('INFO: Could not open reservation log-records.')
		return

	lines = f. readlines()
	num_lines_to_dump = int(0)

	# read number of lines to dump
	if (len(context.args) == 0):
		num_lines_to_dump = DEFAULT_NLINES_DUMP
	else:
		try:
			num_lines_to_dump = int(context.args[0])
		except ValueError:
			update.effective_message.reply_text('The argument you \' provided is not an integer number.\n'
				'Type /help to see how to use commands.')
			return

	if (num_lines_to_dump <= 0):
		update.effective_message.reply_text('You asked {} lines for the output. It is empty.'.format(num_lines_to_dump))
		return

	dump_lines = lines[-num_lines_to_dump:]
	if (len(dump_lines) > 0):
		update.message.reply_text( '```\n' + ''.join(dump_lines) + '\n```', parse_mode='MarkdownV2')
	else:
		update.message.reply_text('Log-file is empty.')


@restricted
@activated
def unknown_message(update, context):

	update.message.reply_text('Sorry, I am a simple bot and I understand only commands.\n' + 
		'Type /help to see them.')

@restricted
@activated
def unknown_command(update, context):

	update.message.reply_text('Sorry, I don\'t know this command.\n' + 
		'Type /help to see what I can do.')


# main function to call
def run_reservation_bot(bot_token, 
	sessions_file='sessions.lst', 
	sessions_passed_file = 'sessions_passed.lst',
	config_file_user = 'user.config',
	config_file_default = 'default.config', 
	log_file_bot = 'reservation_bot.log', 
	log_file_reservation = 'reservation_service.log'
	):

	global bot_activated # flag variable for bot activation
	
	updater = Updater(bot_token, use_context=True)

	# get the dispatcher to register handlers 
	dp = updater.dispatcher

	# conversation handler for the new session
	addsession_handler = ConversationHandler(
			entry_points = [CommandHandler('addsession', addsession)],
			states = {
				DATETIME: [
					MessageHandler(
						Filters.text & ~(Filters.command), lambda update, context: addsession_datetime(update, context, 
							sessions_file=sessions_file)
					)
				], # get datetime of reservation
				URL_LINK: [
					MessageHandler(
						Filters.text & ~(Filters.command), addsession_url_link
					)
				], # get url-link
				PROCESS_NEW_SESSION: [
					CallbackQueryHandler(lambda update, context: addsession_process(update, context, 
						sessions_file=sessions_file)
					)
				], # finalizing processing function - add session to the list, run process
			},

			fallbacks = [
				CommandHandler('cancel', addsession_cancel), 
				MessageHandler(Filters.command, addsession_unkown)
			],
		)

	dp.add_handler(CommandHandler('start', start))

	# 1. basic commands
	# addsession conversation 
	dp.add_handler(addsession_handler)

	# print all sessions from the database
	dp.add_handler(CommandHandler('printsessions', lambda update, context: printsessions(update, context,
		sessions_file=sessions_file, sessions_passed_file=sessions_passed_file)))

	# delete one session with number
	dp.add_handler(CommandHandler('deletesession', lambda update, context: deletesession(update, context,
		sessions_file=sessions_file)))

	# delete all sessions from the database
	dp.add_handler(CommandHandler('deleteall', lambda update, context: deleteall(update, context, 
		sessions_file=sessions_file)))

	# 2. config commands
	dp.add_handler(CommandHandler('configprintuser', lambda update, context: configprintuser(update, context, 
		config_file_user = config_file_user)))
	dp.add_handler(CommandHandler('configset', lambda update, context: configset(update, context, 
		config_file_user = config_file_user)))
	dp.add_handler(CommandHandler('configreset', lambda update, context: configreset(update, context, 
		config_file_user = config_file_user, config_file_default = config_file_default)))
	dp.add_handler(CommandHandler('configprintdefault', lambda update, context: configprintdefault(update, context, 
		config_file_default = config_file_default)))

	# 3. info commands 

	# print help message
	dp.add_handler(CommandHandler('help', help_command))
	# print authors infromation
	dp.add_handler(CommandHandler('about', about))
	# dump bot-log
	dp.add_handler(CommandHandler('logdumpbot', lambda update, context: logdumpbot(update, context, 
		log_file_bot = log_file_bot)))

	# dump reservation-service-log
	dp.add_handler(CommandHandler('logdumpres', lambda update, context: logdumpres(update, context, 
		log_file_reservation = log_file_reservation)))

	# uknown messages and commands
	dp.add_handler(MessageHandler(Filters.all & ~(Filters.command), unknown_message)) # unknown messages
	dp.add_handler(MessageHandler(Filters.command, unknown_command)) # unknown commands


	updater.start_polling()

	# run the bot until CTRL + C recieved or SIGINT, SIGTERM, SIGABRT

	updater.idle()





# start the bot
run_reservation_bot(bot_token=token, 
	sessions_file='sessions.lst', 
	sessions_passed_file = 'sessions_passed.lst',
	config_file_user = 'user.config', 
	config_file_default = 'default.config', 
	log_file_bot = log_file_bot, 
	log_file_reservation = log_file_reservation
	)
