import collections.abc
import os
from typing import Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, User
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
    'resources': {
        'limit': 10
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


class Resource(object):
    def __init__(self, name: str):
        self._name = name
        self._acquired: datetime = None
        self._user: User = None

    @property
    def name(self):
        return self._name

    @property
    def user(self):
        return self._user

    @property
    def acquired(self):
        return self._acquired

    @property
    def display_name(self) -> str:
        state_mark = '🔴' if self._acquired else '⚪️'
        acquiring_info = f'({self._user.name})' if self._acquired else ''
        return f'{state_mark} {self.name} {acquiring_info}'

    def acquire(self, user: User) -> tuple[bool, str]:
        if not self._acquired:
            self._acquired = datetime.now()
            self._user = user
            return True, ''
        elif self._user == user:
            self._acquired = datetime.now()
            return True, 're-acquired'
        return False, f'The resource is already acquired by {self.user.name}'

    def release(self, user: User) -> tuple[bool, str]:
        if not self.acquired:
            return True, ''
        elif self._user == user:
            self._acquired = None
            self._user = None
            return True, ''
        return False, f'The resource has been acquired by another user: {self.user.name}'

    def change_state(self, user: User) -> tuple[bool, str]:
        return self.release(user) if self.acquired else self.acquire(user)


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
    buttons = [
                  [InlineKeyboardButton(r.display_name,
                                        callback_data=k)]
                  for k, r in context.chat_data['resources'].items()
              ]
    return InlineKeyboardMarkup(buttons)


def start(update: Update, context: CallbackContext):
    update.message.reply_markdown('Your resources',
                                  reply_markup=build_keyboard(update=update, context=context))


def add_resource(update: Update, context: CallbackContext):
    resources = context.chat_data.setdefault('resources', {})

    if context.args:
        resource_name = ' '.join(context.args)
        if resource_name in resources:
            message = f'Resource with the name "{context.args[0]}" already exists'
        else:
            resources[resource_name] = Resource(resource_name)
            message = f'Resource "{context.args[0]}" was added successfully'
    else:
        message = 'You have to specify a name of resource after the command'

    update.message.reply_text(message,
                              reply_markup = build_keyboard(update=update, context=context))


def message_logger(update, context):
    logger = logging.getLogger('unknown_messages')
    logger.debug(f'{update.effective_user.id} {update.message.text}')
    update.message.reply_text("I don't understand what you mean, that's why I've logged your message")


def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query

    if query.data in context.chat_data['resources']:
        resource = context.chat_data['resources'][query.data]

        state, answer_message = resource.change_state(update.effective_user)
    else:
        answer_message = f'unknown resource: {query.data}'

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer(answer_message or 'done')
    query.edit_message_text(text='Your resources', reply_markup=build_keyboard(update, context))


dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('add_resource', add_resource))
dispatcher.add_handler(MessageHandler(Filters.all, message_logger))
dispatcher.add_handler(CallbackQueryHandler(button))


logging.info('start polling...')
updater.start_polling()
updater.idle()
