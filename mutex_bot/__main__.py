import logging.config
import os.path

import yaml
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, Defaults
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mutex_bot.bot import start, help_handler

CONF_FILENAME = 'conf.yaml'

logging.getLogger().setLevel(logging.INFO)

with open(CONF_FILENAME, 'rt') as conf:
    config = yaml.safe_load(conf)


engine = create_engine('sqlite:///:memory:', echo=True)
sessionmaker = session_maker(engine)

# logging.config.dictConfig(config['logging'])
# defaults = Defaults(parse_mode=ParseMode.MARKDOWN_V2)
bot_token = config['access']['bot_token']
application = ApplicationBuilder().token(bot_token).build()

application.add_handler(CommandHandler('start', start))
application.add_handler(CommandHandler('help', help_handler))

application.run_polling()
