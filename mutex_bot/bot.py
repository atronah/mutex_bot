import logging

from telegram import Update
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown, mention_markdown


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_markdown_v2(escape_markdown(f'Welcome to ')
                                           + mention_markdown(context.bot.id, context.bot.username, 2)
                                           + escape_markdown(', ', 2)
                                           + user.mention_markdown_v2()
                                           + escape_markdown('. Your ID is ', 2)
                                           + f'`{user.id}`'
                                           + escape_markdown('. This chat ID is ', 2)
                                           + f'`{update.effective_chat.id}`')


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('no help yet')
