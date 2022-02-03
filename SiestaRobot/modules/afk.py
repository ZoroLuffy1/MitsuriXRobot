import random, html
import time
from typing import Optional

from SiestaRobot import dispatcher
from SiestaRobot.modules.disable import (
    DisableAbleCommandHandler,
    DisableAbleMessageHandler,
)
from SiestaRobot.modules.sql import afk_sql as sql
from SiestaRobot.modules.users import get_user_id
from SiestaRobot.modules.language import gs
from SiestaRobot.modules.sql.afk_redis import (
    start_afk,
    end_afk,
    is_user_afk,
    afk_reason,
)
from telegram import MessageEntity, Update
from SiestaRobot import REDIS
from telegram.error import BadRequest
from SiestaRobot.modules.helper_funcs.readable_time import get_readable_time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
    run_async,
)

AFK_GROUP = 7
AFK_REPLY_GROUP = 8


def afk(update: Update, context: CallbackContext):
    args = update.effective_message.text.split(None, 1)
    user = update.effective_user
    chat = update.effective_chat

    if not user:  # ignore channels
        return

    if user.id in [777000, 1087968824]:
        return
    start_afk_time = time.time()
    if len(args) >= 2:
        reason = args[1]
        if len(reason) > 100:
            reason = reason[:100]
            notice = gs(chat.id, "reason_len")
    else:
        reason = ""

    start_afk(update.effective_user.id, reason)
    REDIS.set(f"afk_time_{update.effective_user.id}", start_afk_time)
    fname = update.effective_user.first_name
    try:
        update.effective_message.reply_text(
            text=gs(chat.id, "afk").format(fname, notice)
        )
    except BadRequest:
        pass


def no_longer_afk(update: Update, context: CallbackContext):
    user = update.effective_user
    message = update.effective_message
    chat = update.effective_chat

    if not user:  # ignore channels
        return

    if not is_user_afk(user.id):  # Check if user is afk or not
        return
    end_afk_time = get_readable_time(
        (time.time() - float(REDIS.get(f"afk_time_{user.id}")))
    )
    REDIS.delete(f"afk_time_{user.id}")
    res = end_afk(user.id)

    if res:
        if message.new_chat_members:  # dont say msg
            return
        firstname = update.effective_user.first_name
        try:
            options = [
                gs(chat.id, "afk_array1"),
                gs(chat.id, "afk_array2"),
                gs(chat.id, "afk_array3"),
                gs(chat.id, "afk_array4"),
                gs(chat.id, "afk_array5"),
                gs(chat.id, "afk_array6"),
                gs(chat.id, "afk_array7"),
                gs(chat.id, "afk_array8"),
            ]
            chosen_option = random.choice(options)
            update.effective_message.reply_text(chosen_option.format(firstname))
        except:
            return


def reply_afk(update: Update, context: CallbackContext):
    bot = context.bot
    message = update.effective_message
    userc = update.effective_user
    userc_id = userc.id
    if message.entities and message.parse_entities(
        [MessageEntity.TEXT_MENTION, MessageEntity.MENTION]
    ):
        entities = message.parse_entities(
            [MessageEntity.TEXT_MENTION, MessageEntity.MENTION]
        )

        chk_users = []
        for ent in entities:
            if ent.type == MessageEntity.TEXT_MENTION:
                user_id = ent.user.id
                fst_name = ent.user.first_name

                if user_id in chk_users:
                    return
                chk_users.append(user_id)

            if ent.type != MessageEntity.MENTION:
                return

            user_id = get_user_id(message.text[ent.offset : ent.offset + ent.length])
            if not user_id:
                # Should never happen, since for a user to become AFK they must have spoken. Maybe changed username?
                return

            if user_id in chk_users:
                return
            chk_users.append(user_id)

            try:
                chat = bot.get_chat(user_id)
            except BadRequest:
                print("Error: Could not fetch userid {} for AFK module".format(user_id))
                return
            fst_name = chat.first_name

            check_afk(update, context, user_id, fst_name, userc_id)

    elif message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        fst_name = message.reply_to_message.from_user.first_name
        check_afk(update, context, user_id, fst_name, userc_id)


def check_afk(update, context, user_id, fst_name, userc_id):
    chat = update.effective_chat
    if is_user_afk(user_id):
        reason = afk_reason(user_id)
        since_afk = get_readable_time(
            (time.time() - float(REDIS.get(f"afk_time_{user_id}")))
        )
        if reason == "none":
            if int(userc_id) == int(user_id):
                return
            res = gs(chat.id, "afk_check").format(fst_name, since_afk)
            update.effective_message.reply_text(res, parse_mode="html")
        else:
            if int(userc_id) == int(user_id):
                return
            res = gs(chat.id, "afk_check").format(fst_name, reason, since_afk)
            update.effective_message.reply_text(res, parse_mode="html")


def __user_info__(user_id):
    is_afk = is_user_afk(user_id)
    text = ""
    if is_afk:
        since_afk = get_readable_time(
            (time.time() - float(REDIS.get(f"afk_time_{user_id}")))
        )
        text = "<i>This user is currently afk (away from keyboard).</i>"
        text += f"\n<i>Since: {since_afk}</i>"

    else:
        text = "<i>This user is currently isn't afk (away from keyboard).</i>"
    return text


def __gdpr__(user_id):
    end_afk(user_id)


AFK_HANDLER = DisableAbleCommandHandler("afk", afk, run_async=True)
AFK_REGEX_HANDLER = DisableAbleMessageHandler(
    Filters.regex(r"^(?i)brb(.*)$"), afk, friendly="afk", run_async=True
)
NO_AFK_HANDLER = MessageHandler(Filters.all & Filters.chat_type.groups, no_longer_afk)
AFK_REPLY_HANDLER = MessageHandler(Filters.all & Filters.chat_type.groups, reply_afk)

dispatcher.add_handler(AFK_HANDLER, AFK_GROUP)
dispatcher.add_handler(AFK_REGEX_HANDLER, AFK_GROUP)
dispatcher.add_handler(NO_AFK_HANDLER, AFK_GROUP)
dispatcher.add_handler(AFK_REPLY_HANDLER, AFK_REPLY_GROUP)

__mod_name__ = "Afk​"
__command_list__ = ["afk"]
__handlers__ = [
    (AFK_HANDLER, AFK_GROUP),
    (AFK_REGEX_HANDLER, AFK_GROUP),
    (NO_AFK_HANDLER, AFK_GROUP),
    (AFK_REPLY_HANDLER, AFK_REPLY_GROUP),
]
