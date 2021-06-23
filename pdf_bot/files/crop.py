import os
import tempfile

from telegram import ReplyKeyboardRemove, ReplyKeyboardMarkup
from telegram.ext import ConversationHandler

from pdf_bot.constants import (
    BY_PERCENT,
    BY_SIZE,
    BACK,
    WAIT_CROP_TYPE,
    WAIT_CROP_PERCENT,
    WAIT_CROP_OFFSET,
    PDF_INFO,
)
from pdf_bot.utils import send_result_file
from pdf_bot.language import set_lang
from pdf_bot.files.utils import run_cmd

MIN_PERCENT = 0
MAX_PERCENT = 100


def ask_crop_type(update, context):
    _ = set_lang(update, context)
    keyboard = [[_(BY_PERCENT), _(BY_SIZE)], [_(BACK)]]
    reply_markup = ReplyKeyboardMarkup(
        keyboard, one_time_keyboard=True, resize_keyboard=True
    )
    update.effective_message.reply_text(
        _("Select the crop type that you'll like to perform"), reply_markup=reply_markup
    )

    return WAIT_CROP_TYPE


def ask_crop_value(update, context):
    _ = set_lang(update, context)
    message = update.effective_message
    reply_markup = ReplyKeyboardMarkup(
        [[_(BACK)]], one_time_keyboard=True, resize_keyboard=True
    )

    if message.text == _(BY_PERCENT):
        message.reply_text(
            _(
                "Send me a number between {} and {}. This is the percentage of margin space to "
                "retain between the content in your PDF file and the page"
            ).format(MIN_PERCENT, MAX_PERCENT),
            reply_markup=reply_markup,
        )

        return WAIT_CROP_PERCENT
    else:
        message.reply_text(
            _(
                "Send me a number that you'll like to adjust the margin size. "
                "Positive numbers will decrease the margin size and negative numbers will increase it"
            ),
            reply_markup=reply_markup,
        )

        return WAIT_CROP_OFFSET


def check_crop_percent(update, context):
    _ = set_lang(update, context)
    message = update.effective_message

    if message.text == _(BACK):
        return ask_crop_type(update, context)

    try:
        percent = float(message.text)
    except ValueError:
        message.reply_text(
            _("The number must be between {} and {}, try again").format(
                MIN_PERCENT, MAX_PERCENT
            )
        )

        return WAIT_CROP_PERCENT

    return crop_pdf(update, context, percent=percent)


def check_crop_size(update, context):
    _ = set_lang(update, context)
    message = update.effective_message

    if message.text == _(BACK):
        return ask_crop_type(update, context)

    try:
        offset = float(update.effective_message.text)
    except ValueError:
        _ = set_lang(update, context)
        update.effective_message.reply_text(_("The number is invalid, try again"))

        return WAIT_CROP_OFFSET

    return crop_pdf(update, context, offset=offset)


def crop_pdf(update, context, percent=None, offset=None):
    _ = set_lang(update, context)
    update.effective_message.reply_text(
        _("Cropping your PDF file"), reply_markup=ReplyKeyboardRemove()
    )

    with tempfile.NamedTemporaryFile(suffix=".pdf") as tf:
        user_data = context.user_data
        file_id, file_name = user_data[PDF_INFO]
        pdf_file = context.bot.get_file(file_id)
        pdf_file.download(custom_path=tf.name)

        with tempfile.TemporaryDirectory() as dir_name:
            out_fn = os.path.join(dir_name, f"Cropped_{file_name}")
            command = f'pdf-crop-margins -o "{out_fn}" "{tf.name}"'

            if percent is not None:
                command += f" -p {percent}"
            else:
                command += f" -a {offset}"

            if run_cmd(command):
                send_result_file(update, context, out_fn, "crop")
            else:
                update.effective_message.reply_text(
                    _("Something went wrong, try again")
                )

    # Clean up memory
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]

    return ConversationHandler.END
