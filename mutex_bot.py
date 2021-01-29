import collections.abc
import os
from typing import Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, PicklePersistence
from telegram.ext import CommandHandler, MessageHandler
from telegram.ext import CallbackQueryHandler, CallbackContext
from telegram.ext import Filters
import yaml
import logging
import logging.config
import sys
from datetime import datetime


# default settings
settings: Dict[str, Dict[str, Any]] = {
    'access': {
        'token': None
    },
    'persistence': {
        'filename': 'mutex_bot.data'
    },
    'logging': {
        'version': 1.0,
        'formatters': {
            'default': {
                'format': '[{asctime}]{levelname: <5}({name}): {message}',
                'style': '{'
            }
        },
        'handlers': {
            'general': {
                'class': 'logging.handlers.WatchedFileHandler',
                'level': 'DEBUG',
                'filename': 'bot.log',
                'formatter': 'default'
            },
            'stdout': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'formatter': 'default'
            },
            'unknown_messages': {
                'class': 'logging.handlers.WatchedFileHandler',
                'level': 'DEBUG',
                'filename': 'unknown_messages.log',
                'formatter': 'default'
            }
        },
        'loggers': {
            'unknown_messages': {
                'level': 'DEBUG',
                'handlers': ['unknown_messages']
            }
        },
        'root': {
            'level': 'DEBUG',
            'handlers': ['general']
        },
    }
}

ADD_RESOURCE = '__add_resource'


def recursive_update(target_dict, update_dict):
    if not isinstance(update_dict, dict):
        return target_dict
    for k, v in update_dict.items():
        if isinstance(v, collections.abc.Mapping):
            target_dict[k] = recursive_update(target_dict.get(k, {}), v)
        else:
            target_dict[k] = v
    return target_dict


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


def build_keyboard(update: Update, context: CallbackContext) -> InlineKeyboardMarkup:
    def button_name(resource_name, acquired, user_id, user_name):
        state_mark = f"{'🔴' if acquired else '⚪️'}"
        acquire_info = (' (' + (user_name or user_id or '?') + ')') if acquired else ''
        return f'{state_mark} {resource_name}{acquire_info}'

    buttons = [
                  [InlineKeyboardButton(
                                        button_name(k, r['acquired'], *r['user']),
                                        callback_data=k)]
                  for k, r in context.chat_data['resources'].items()
                  if k != ADD_RESOURCE
              ]
    buttons.append([InlineKeyboardButton("Add resource", callback_data=ADD_RESOURCE)])
    return InlineKeyboardMarkup(buttons)


def start(update: Update, context: CallbackContext):
    context.chat_data.setdefault('resources', {})
    update.message.reply_markdown('Resources',
                                  reply_markup=build_keyboard(update=update, context=context))


def message_logger(update, context):
    logger = logging.getLogger('unknown_messages')
    logger.debug(f'{update.effective_user.id} {update.message.text}')
    update.message.reply_text("I don't understand what you mean, that's why I've logged your message")


def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query

    if query.data == ADD_RESOURCE:
        resource_name = f"Resource {len(context.chat_data['resources']) + 1}"
        context.chat_data['resources'][resource_name] = {
            'acquired': None,
            'user': (None, None)
        }
    elif query.data in context.chat_data['resources']:
        resource = context.chat_data['resources'][query.data]
        if resource['acquired']:
            resource['acquired'] = None
            resource['user'] = (None, None)
        else:
            resource['acquired'] = datetime.now()
            resource['user'] = (update.effective_user.id, update.effective_user.username)

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer()
    query.edit_message_text(text='Resources', reply_markup=build_keyboard(update, context))


dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(MessageHandler(Filters.all, message_logger))
dispatcher.add_handler(CallbackQueryHandler(button))


logging.info('start polling...')
updater.start_polling()
updater.idle()
