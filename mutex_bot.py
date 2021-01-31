import collections.abc
import io
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
                'level': 'INFO',
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
                'level': 'INFO',
                'filename': 'unknown_messages.log',
                'formatter': 'default'
            }
        },
        'loggers': {
            'unknown_messages': {
                'level': 'INFO',
                'handlers': ['unknown_messages']
            }
        },
        'root': {
            'level': 'INFO',
            'handlers': ['general']
        },
    }
}

STANDARD_USER_MODE, REMOVING_USER_MODE = range(2)
FINISH_REMOVING = '__finish_removing'


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

    @property
    def data(self):
        return {
            'name': self.name,
            'acquired': self.acquired,
            'user': {
                'id': self.user.id,
                'username': self.user.username,
                'fullname': self.user.full_name,
            }
        }

    def acquire(self, user: User):
        # type: (User) -> tuple[bool, str]
        if not self._acquired:
            self._acquired = datetime.now()
            self._user = user
            return True, ''
        elif self._user == user:
            self._acquired = datetime.now()
            return True, 're-acquired'
        return False, f'The resource is already acquired by {self.user.name}'

    def release(self, user: User):
        # type: (User) -> tuple[bool, str]
        if not self.acquired:
            return True, ''
        elif self._user == user:
            self._acquired = None
            self._user = None
            return True, ''
        return False, f'You cannot release resource acquired by another user: {self.user.name}'

    def change_state(self, user: User):
        # type: (User) -> tuple[bool, str]
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
    if context.user_data.get('mode', STANDARD_USER_MODE) == REMOVING_USER_MODE:
        buttons.append([InlineKeyboardButton('----> Finish removing <----', callback_data=FINISH_REMOVING)])
    return InlineKeyboardMarkup(buttons)


def start(update: Update, context: CallbackContext):
    if len(context.chat_data.get('resources', [])) == 0:
        update.message.reply_markdown('At first you must add resources by `/add_resource <resource_name>` command')
    else:
        update.message.reply_text('Your resources',
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


def remove_resource(update: Update, context: CallbackContext):
    context.user_data['mode'] = REMOVING_USER_MODE

    update.message.reply_text('Choose resource to remove it',
                              reply_markup=build_keyboard(update=update, context=context))


def export_chat_data(update: Update, context: CallbackContext):
    exporting_chat_data = {'chat_id': update.effective_chat.id,
                           'exported': datetime.now(),
                           'resources': []
                           }
    if 'resources' in context.chat_data:
        for n, r in context.chat_data['resources'].items():
            exporting_chat_data['resources'].append(r.data)
        filename = f'chat_data_{update.effective_chat.id}.yml'
        string_stream = io.StringIO(yaml.safe_dump(exporting_chat_data))
        update.message.reply_document(document=string_stream,
                                      filename=filename)
    else:
        update.message.reply_text('Nothing to export')


def import_chat_data(update: Update, context: CallbackContext):
    update.message.reply_text('Maybe later... ')


def message_logger(update, context):
    logger = logging.getLogger('unknown_messages')
    logger.debug(f'{update.effective_user.id} {update.message.text}')
    update.message.reply_text("I don't understand what you mean, that's why I've logged your message")


def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query

    if query.data == FINISH_REMOVING:
        context.user_data['mode'] = STANDARD_USER_MODE
        answer_message = 'Removing finished'
    elif query.data in context.chat_data['resources']:
        resource = context.chat_data['resources'][query.data]

        user_mode = context.user_data.get('mode', STANDARD_USER_MODE)
        if user_mode == STANDARD_USER_MODE:
            _, answer_message = resource.change_state(update.effective_user)
        elif user_mode == REMOVING_USER_MODE:
            can_be_removed, _ = resource.release(update.effective_user)
            if can_be_removed:
                del context.chat_data['resources'][query.data]
                answer_message = 'done'
            else:
                answer_message = 'You cannot remove acquired resource'
    else:
        answer_message = f'unknown resource: {query.data}'

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer(answer_message or 'done')
    query.edit_message_text(text='Your resources', reply_markup=build_keyboard(update, context))


dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('add_resource', add_resource))
dispatcher.add_handler(CommandHandler('remove_resource', remove_resource))
dispatcher.add_handler(CommandHandler('export_chat_data', export_chat_data))
dispatcher.add_handler(CommandHandler('import_chat_data', import_chat_data))
dispatcher.add_handler(MessageHandler(Filters.all, message_logger))
dispatcher.add_handler(CallbackQueryHandler(button))


logging.info('start polling...')
updater.start_polling()
updater.idle()
