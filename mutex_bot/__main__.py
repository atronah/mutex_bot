import logging
import os
import sys

import i18n
import yaml
from telegram.ext import PicklePersistence, Updater, CommandHandler, Filters, CallbackQueryHandler, MessageHandler

from mutex_bot.bot import recursive_update, settings, error_handler, help_command, start, add_resource, remove_resource, \
    export_chat_data, import_chat_data, finish, lang, force_cleanup, other_messages, button

if os.path.exists('conf.yml'):
    with open('conf.yml', 'rt') as conf:
        recursive_update(settings, yaml.safe_load(conf))
else:
    with open('conf.yml', 'wt') as conf:
        yaml.dump(settings, conf)

logging.config.dictConfig(settings['logging'])

if not settings['access']['token']:
    logging.error('Empty bot token in conf.yml (`access/token`)')
    sys.exit(1)

if not settings['persistence']['filename']:
    logging.error('Empty filename fot persistence in conf.yml (`persistence/filename`)')
    sys.exit(1)


pp = PicklePersistence(settings['persistence']['filename'])
updater = Updater(token=settings['access']['token'], persistence=pp, use_context=True)
dispatcher = updater.dispatcher


dispatcher.add_error_handler(error_handler)
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('help', help_command))
dispatcher.add_handler(CommandHandler('add_resource', add_resource))
dispatcher.add_handler(CommandHandler('remove_resource', remove_resource))
dispatcher.add_handler(CommandHandler('export_chat_data', export_chat_data))
dispatcher.add_handler(CommandHandler('import_chat_data', import_chat_data))
dispatcher.add_handler(CommandHandler('finish', finish))
dispatcher.add_handler(CommandHandler('lang', lang))
dispatcher.add_handler(CommandHandler('force_cleanup', force_cleanup))
dispatcher.add_handler(MessageHandler(Filters.all & ~Filters.status_update, other_messages))
dispatcher.add_handler(CallbackQueryHandler(button))


i18n.load_path.append('i18n')
i18n.set('fallback', 'en')


logging.info('start polling...')
updater.start_polling()
updater.idle()