import collections.abc
import io
import logging
import logging.config
import os
import re
from datetime import datetime
from typing import Dict, Any

import i18n
import yaml
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, \
    ParseMode
from telegram.ext import CallbackContext

from mutex_bot.resource import Group, Resource

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


def tr(context: object, message_id: object, **kwargs: object) -> str:
    i18n.set('locale', context.chat_data.get('lang', 'en'))
    return i18n.t(message_id, **kwargs)


def current_datetime():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


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
    import traceback
    import tempfile

    try:
        caption = str(context.error)
        traceback_info = traceback.format_exc()
        with tempfile.TemporaryFile() as f:
            f.write(traceback_info.encode('utf-8'))
            f.seek(0)
            context.bot.sendDocument(update.effective_chat.id, f,
                                     caption=caption, filename='traceback.log')
    except Exception as e:
        exception_info = caption + str(e)
        context.bot.sendMessage(update.effective_chat.id,
                                tr(context, 'common.internal_exception', exception_info=exception_info))
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
        message = update.message.reply_text(tr(context, 'common.your_resources', current_datetime=current_datetime()),
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
                     owner=resource.user.mention_html(f'@{resource.user.username} ({resource.user.full_name})'),
                     requester=update.effective_user.mention_html(f'@{update.effective_user.username} ({update.effective_user.full_name})'),
                     resource_full_name=resource_full_name)
        context.bot.sendMessage(update.effective_chat.id,
                                message,
                                parse_mode=ParseMode.HTML)

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer(answer_message or tr(context, 'common.done'))
    if success:
        query.edit_message_text(text=tr(context, 'common.your_resources', current_datetime=current_datetime()),
                                reply_markup=build_keyboard(update, context))


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
