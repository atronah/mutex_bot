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
import i18n
import yaml
import logging
import logging.config
import sys
from datetime import datetime


# default settings
from telegram.utils import helpers

settings: Dict[str, Dict[str, Any]] = {
    'access': {
        'token': None,
        'admin_user_list': []
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


def tr(context: object, message_id: object, **kwargs: object) -> object:
    i18n.set('locale', context.chat_data.get('lang', 'en'))
    return i18n.t(message_id, **kwargs)


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
        # type: (User) -> tuple[bool, tuple[str, dict] or None]
        if not self._acquired:
            self._acquired = datetime.now()
            self._user = user
            return True, None
        elif self._user == user:
            self._acquired = datetime.now()
            return True, ('common.re_acquired', {})
        return False, ('common.already_acquired_by', dict(username=self.user.name))

    def release(self, user):
        # type: (User) -> tuple[bool, tuple[str, dict] or None]
        if not self.acquired:
            return True, None
        elif self._user == user:
            self._acquired = None
            self._user = None
            return True, None
        return False, ('common.cannot_release_acquired_by', dict(username=self.user.name))

    def change_state(self, user):
        # type: (User) -> tuple[bool, tuple[str, dict] or None]
        return self.release(user) if self.acquired else self.acquire(user)

    def force_cleanup(self):
        self._acquired: [datetime, None] = None
        self._user: [User, None] = None


class Group(dict):
    def __init__(self, name):
        super().__init__()
        self._name = name

    @property
    def name(self):
        return self._name

    @property
    def display_name(self):
        resource_states = ''.join([r.state_mark for r in self.values()])
        return f'{resource_states} [{self._name}]'

    @property
    def resources(self):
        return self.values()

    @property
    def data(self):
        return {
            'name': self.name,
            'resources': dict(self)
        }

    def force_cleanup(self):
        for r in self.resources:
            r.force_cleanup()


def recursive_update(target_dict, update_dict):
    if not isinstance(update_dict, dict):
        return target_dict
    for k, v in update_dict.items():
        if isinstance(v, collections.abc.Mapping):
            target_dict[k] = recursive_update(target_dict.get(k, {}), v)
        else:
            target_dict[k] = v
    return target_dict



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
    exception_info = str(context.error)
    import traceback
    exception_info += os.linesep
    exception_info += traceback.format_exc()
    context.bot.sendMessage(update.effective_chat.id, tr(context, 'common.internal_exception', exception_info=exception_info))
    raise context.error


def start(update: Update, context: CallbackContext):
    if len(context.chat_data.get('resources', [])) == 0:
        update.message.reply_markdown(tr(context, 'common.first_add_resource'))
    else:
        messages_with_resources = context.chat_data.setdefault('messages_with_resources', [])
        while messages_with_resources:
            message = messages_with_resources.pop()
            try:
                message.delete()
            except:
                pass
        message = update.message.reply_text(tr(context, 'common.your_resources'),
                                            reply_markup=build_keyboard(update=update, context=context))
        messages_with_resources.append(message)


def help_command(update: Update, context: CallbackContext):
    help_message = tr(context, 'common.help')
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
        resource_full_name = resource_name
        if ':' in resource_name:
            group_name, resource_name = resource_name.split(':')
            resources = resources.setdefault(group_name, Group(group_name))

        if resource_name in resources:
            message = f'Resource with the name "{resource_full_name}" already exists'
        else:
            resources[resource_name] = Resource(resource_name)
            message = tr(context, 'common.resource_successfully_added', resource_full_name=resource_full_name)
        if group_name:
            message += ' ' + tr(context, 'common.in_group_name', group_name=group_name)
    else:
        message = tr(context, 'common.have_to_specify_resource_name')

    update.message.reply_text(message)

    start(update, context)


def remove_resource(update: Update, context: CallbackContext):
    context.user_data['mode'] = REMOVING_USER_MODE
    update.message.reply_text(tr(context, 'common.send_name_to_remove'),
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
        update.message.reply_text(tr(context, 'common.nothing_to_export'))


def import_chat_data(update: Update, context: CallbackContext):
    update.message.reply_text(tr(context, 'common.maybe_later_dots'))


def finish(update: Update, context: CallbackContext):
    if context.user_data.get('mode', STANDARD_USER_MODE) != STANDARD_USER_MODE:
        context.user_data['mode'] = STANDARD_USER_MODE
        update.message.reply_text(tr(context, 'common.finished'), reply_markup=ReplyKeyboardRemove())
        start(update, context)
    else:
        update.message.reply_text(tr(context, 'common.nothing_to_finish'))


def other_messages(update, context):
    if context.user_data.get('mode', STANDARD_USER_MODE) == REMOVING_USER_MODE:
        resource_full_name = resource_name = update.message.text
        if ':' in resource_name:
            group_name, resource_name = resource_name.split(':')
            resources = context.chat_data.get('resources', {}).get(group_name, {})
        else:
            group_name = None
            resources = context.chat_data.get('resources', {})

        if resource_name not in resources:
            answer_message = tr(context, 'common.unknown_resource', resource_full_name=resource_full_name)
        else:
            resource = resources[resource_name]
            can_be_removed, _ = resource.release(update.effective_user)
            if can_be_removed:
                del resources[resource_name]
                if group_name and not resources:
                    del context.chat_data['resources'][group_name]
                answer_message = tr(context, 'common.resource_removed')
            else:
                answer_message = tr(context, 'common.cannot_remove_acquired_resource')
        update.message.reply_text(answer_message, reply_markup=build_keyboard(update, context))
    else:
        logger = logging.getLogger('unknown_messages')
        logger.debug(f'{update.effective_user.id} {update.message.text}')
        update.message.reply_text(tr(context, 'common.do_not_understand_and_logged'))


def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    resource_full_name = ''

    if query.data == '_back':
        context.chat_data['level'] = '/'.join(context.chat_data.get('level', '').split('/')[:-1])
        success, answer_message = True, tr(context, 'common.done')
    else:
        level = context.chat_data.get('level', '')
        resources = context.chat_data['resources']
        resource_full_name = query.data
        if '/' in level:
            resource_list = []
            for resource_name in level.split('/')[1:]:
                if resource_name in resources:
                    resource_list.append(resource_name)
                    resources = resources[resource_name]
            resource_list.append(resource_full_name)
            resource_full_name = ':'.join(resource_list)

        resource = resources[query.data]

        if isinstance(resource, Group):
            context.chat_data['level'] = '/'.join([level, query.data])
            success, answer_message = True, tr(context, 'common.done')
        else:
            success, message_info = resource.change_state(update.effective_user)
            if message_info:
                message_id, kwargs = message_info
                answer_message = tr(context, message_id, **kwargs)
            else:
                answer_message = ''

    if not success:
        message = tr(context,
                     'common.another_needs',
                     owner=resource.user.mention_html(),
                     requester=update.effective_user.mention_html(),
                     resource_full_name=resource_full_name)
        context.bot.sendMessage(update.effective_chat.id,
                                message,
                                parse_mode=ParseMode.HTML)

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer(answer_message or tr(context, 'common.done'))
    if success:
        query.edit_message_text(text=tr(context, 'common.your_resources'), reply_markup=build_keyboard(update, context))


def lang(update: Update, context: CallbackContext) -> None:
    if context.args:
        context.chat_data['lang'] = context.args[0]
        update.message.reply_text(tr(context, 'common.lang_changed'))
    start(update, context)


def force_cleanup(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id in settings['access'].get('admin_user_list', []):
        for r in context.chat_data['resources'].values():
            print(f'clean {r.name} ({type(r)})')
            r.force_cleanup()
        start(update, context)
    else:
        update.message.reply_text(tr(context, 'common.admin_rights_required'))



def main():
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


if __name__ == '__main__':
    main()