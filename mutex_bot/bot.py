import logging
import os

from telegram import Update
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown, mention_markdown

from sqlalchemy import select
from sqlalchemy.orm import Session

from .model import engine
from .model import Resource


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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


async def resource_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_message = ''
    if context.args[0] == 'add':
        with Session(engine) as session:
            resource = Resource(name=context.args[1])
            session.add(resource)
            session.commit()
            reply_message = "Added successfully"
    elif context.args[0] == 'list':
        with Session(engine) as session:
            stmt = select(Resource)
            reply_message = os.linesep.join([f"- {resource!r}" for resource in session.scalars(stmt)])

    await update.message.reply_text(reply_message or 'Sorry, I have nothing to say')