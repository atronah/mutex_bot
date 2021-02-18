import collections.abc
import io
import os
import re
from typing import Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, User, ReplyKeyboardMarkup, ReplyKeyboardRemove, \
    ParseMode
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
from telegram.utils import helpers

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


class Resource(object):
    def __init__(self, name: str):
        self._name = name
        self._acquired: [datetime, None] = None
        self._user: [User, None] = None

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
    def state_mark(self):
        return '🔴' if self._acquired else '⚪️'

    @property
    def display_name(self) -> str:
        acquiring_info = f'({self._user.name})' if self._acquired else ''
        return f'{self.state_mark} {self.name} {acquiring_info}'

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

    def acquire(self, user):
        # type: (User) -> tuple[bool, str]
        if not self._acquired:
            self._acquired = datetime.now()
            self._user = user
            return True, ''
        elif self._user == user:
            self._acquired = datetime.now()
            return True, 're-acquired'
        return False, f'The resource is already acquired by {self.user.name}'

    def release(self, user):
        # type: (User) -> tuple[bool, str]
        if not self.acquired:
            return True, ''
        elif self._user == user:
            self._acquired = None
            self._user = None
            return True, ''
        return False, f'You cannot release resource acquired by another user: {self.user.name}'

    def change_state(self, user):
        # type: (User) -> tuple[bool, str]
        return self.release(user) if self.acquired else self.acquire(user)


class Group(dict):
    def __init__(self, name):
        super().__init__()
        self._name = name
        self._resources: Dict[str, Resource] = {}

    @property
    def name(self):
        return self._name

    @property
    def display_name(self):
        resource_states = ''.join([r.state_mark for r in self.values()])
        return f'{resource_states} [{self._name}]'

    @property
    def resources(self):
        return self._resources

    @property
    def data(self):
        return {
            'name': self.name,
            'resources': dict(self)
        }


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
    if context.user_data.get('mode', STANDARD_USER_MODE) == REMOVING_USER_MODE:
        rows = []
        for k, v in context.chat_data['resources'].items():
            if isinstance(v, Group):
                for gk in v:
                    rows.append([':'.join([k, gk])])
            else:
                rows.append([k])
        rows.append(['/finish'])
        keyboard = ReplyKeyboardMarkup(rows, one_time_keyboard=True, selective=True)
    else:
        rows = []
        resources = context.chat_data['resources']
        level = context.chat_data.get('level', '')
        for resource_name in level.split('/')[1:]:
            if resource_name in resources:
                resources = resources[resource_name]

        for k, v in resources.items():
            rows.append([InlineKeyboardButton(v.display_name, callback_data=k)])

        if level:
            rows.append([InlineKeyboardButton('<', callback_data='_back')])

        keyboard = InlineKeyboardMarkup(rows)
    return keyboard


def error_handler(update: Update, context: CallbackContext):
    update.message.reply_text(f'Internal exception: {str(context.error)}')
    raise context.error


def start(update: Update, context: CallbackContext):
    if len(context.chat_data.get('resources', [])) == 0:
        update.message.reply_markdown('At first you must add resources by `/add_resource <resource_name>` command')
    else:
        messages_with_resources = context.chat_data.setdefault('messages_with_resources', [])
        while messages_with_resources:
            message = messages_with_resources.pop()
            message.delete()
        message = update.message.reply_text('Your resources',
                                            reply_markup=build_keyboard(update=update, context=context))
        messages_with_resources.append(message)


def help_command(update: Update, context: CallbackContext):
    help_message = 'That bot helps to manage resources with exclusive access.\n' \
                   'It allows you to see which ones are busy and which ones are free' \
                   ' and change that its state just by tap on them in resources list\n' \
                   '\n' \
                   'Available commands:\n' \
                   '\n' \
                   '- /start - Starts the bot or/and shows the status of resources\n' \
                   '- /help - Shows that message\n' \
                   '- /add_resource `<name>` - Adds new resource with name `<name>`' \
                   ' to resources list of that chat\n' \
                   '- /remove_resource - Switches the user to removing mode' \
                   ' when he can remove one or more resources' \
                   ' just send theit names to bot by using special keyboard \n' \
                   '- /export_chat_data - Sends to chat .yml file with resources and its states\n' \
                   '- /import_chat_data - (not implemented) loads resources with ots states' \
                   ' from .yml file which was sent to the chat after that command\n'
    escape_chars = r'_*[]()~>#+-=|{}.!'
    help_message = re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', help_message)
    update.message.reply_markdown_v2(help_message)


def add_resource(update: Update, context: CallbackContext):
    resources = context.chat_data.setdefault('resources', {})

    if context.args:
        resource_name = ' '.join(context.args)
        if resource_name.startswith(('_', '<')):
            resource_name = resource_name[1:]
        group_name = None
        if ':' in resource_name:
            group_name, resource_name = resource_name.split(':')
            resources = resources.setdefault(group_name, Group(group_name))

        if resource_name in resources:
            message = f'Resource with the name "{context.args[0]}" already exists'
        else:
            resources[resource_name] = Resource(resource_name)
            message = f'Resource "{context.args[0]}" was added successfully'
        if group_name:
            message += f' in group "{group_name}"'
    else:
        message = 'You have to specify a name of resource after the command'

    update.message.reply_text(message)

    start(update, context)


def remove_resource(update: Update, context: CallbackContext):
    context.user_data['mode'] = REMOVING_USER_MODE
    update.message.reply_text('Send me the name of resource you would like to remove',
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


def finish(update: Update, context: CallbackContext):
    if context.user_data.get('mode', STANDARD_USER_MODE) != STANDARD_USER_MODE:
        context.user_data['mode'] = STANDARD_USER_MODE
        update.message.reply_text('Finished', reply_markup=ReplyKeyboardRemove())
        start(update, context)
    else:
        update.message.reply_text('Nothing to finish')


def other_messages(update, context):
    if context.user_data.get('mode', STANDARD_USER_MODE) == REMOVING_USER_MODE:
        resource_name = update.message.text
        if ':' in resource_name:
            group_name, resource_name = resource_name.split(':')
            resources = context.chat_data.get('resources', {}).get(group_name, {})
        else:
            group_name = None
            resources = context.chat_data.get('resources', {})

        if resource_name not in resources:
            answer_message = f'Unknown resource: {resource_name}'
        else:
            resource = resources[resource_name]
            can_be_removed, _ = resource.release(update.effective_user)
            if can_be_removed:
                del resources[resource_name]
                if group_name and not resources:
                    del context.chat_data['resources'][group_name]
                answer_message = 'Removed'
            else:
                answer_message = 'You cannot remove acquired resource.'
        update.message.reply_text(answer_message, reply_markup=build_keyboard(update, context))
    else:
        logger = logging.getLogger('unknown_messages')
        logger.debug(f'{update.effective_user.id} {update.message.text}')
        update.message.reply_text("I don't understand what you mean, that's why I've logged your message")


def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query

    if query.data == '_back':
        context.chat_data['level'] = '/'.join(context.chat_data.get('level', '').split('/')[:-1])
        success, answer_message = True, 'done'
    else:
        level = context.chat_data.get('level', '')
        resources = context.chat_data['resources']
        if '/' in level:
            for resource_name in level.split('/')[1:]:
                if resource_name in resources:
                    resources = resources[resource_name]

        resource = resources[query.data]

        if isinstance(resource, Group):
            context.chat_data['level'] = '/'.join([level, query.data])
            success, answer_message = True, 'done'
        else:
            success, answer_message = resource.change_state(update.effective_user)

    if not success:
        message = f'@{resource.user.mention_html()},'\
                  f' you''ve acquired the resource that another user needs:'\
                  f' {update.effective_user.mention_html()}'
        context.bot.sendMessage(update.effective_chat.id,
                                message,
                                parse_mode=ParseMode.HTML)

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer(answer_message or 'done')
    query.edit_message_text(text='Your resources', reply_markup=build_keyboard(update, context))


dispatcher.add_error_handler(error_handler)
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('help', help_command))
dispatcher.add_handler(CommandHandler('add_resource', add_resource))
dispatcher.add_handler(CommandHandler('remove_resource', remove_resource))
dispatcher.add_handler(CommandHandler('export_chat_data', export_chat_data))
dispatcher.add_handler(CommandHandler('import_chat_data', import_chat_data))
dispatcher.add_handler(CommandHandler('finish', finish))
dispatcher.add_handler(MessageHandler(Filters.all & ~Filters.status_update, other_messages))
dispatcher.add_handler(CallbackQueryHandler(button))


logging.info('start polling...')
updater.start_polling()
updater.idle()
