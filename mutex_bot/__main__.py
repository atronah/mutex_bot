import logging.config
import os.path

import yaml
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, Defaults
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mutex_bot.bot import start_handler, help_handler, resource_handler

CONF_FILENAME = 'conf.yaml'

logging.getLogger().setLevel(logging.INFO)

with open(CONF_FILENAME, 'rt') as conf:
    config = yaml.safe_load(conf)


# logging.config.dictConfig(config['logging'])
# defaults = Defaults(parse_mode=ParseMode.MARKDOWN_V2)
bot_token = config['access']['bot_token']
application = ApplicationBuilder().token(bot_token).build()

application.add_handler(CommandHandler('start', start_handler))
application.add_handler(CommandHandler('help', help_handler))
application.add_handler(CommandHandler('resource', resource_handler))

application.run_polling()
