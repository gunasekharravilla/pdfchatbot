import humanize
import os
import tempfile

from telegram import ReplyKeyboardRemove, ParseMode
from telegram.ext import ConversationHandler

from pdf_bot.constants import PDF_INFO
from pdf_bot.language import set_lang
from pdf_bot.utils import check_user_data, send_result_file
from pdf_bot.files.utils import run_cmd


def compress_pdf(update, context):
    if not check_user_data(update, context, PDF_INFO):
        return ConversationHandler.END

    _ = set_lang(update, context)
    update.effective_message.reply_text(
        _("Compressing your PDF file"),
        reply_markup=ReplyKeyboardRemove(),
    )

    with tempfile.NamedTemporaryFile() as tf:
        user_data = context.user_data
        file_id, file_name = user_data[PDF_INFO]
        pdf_file = context.bot.get_file(file_id)
        pdf_file.download(custom_path=tf.name)

        with tempfile.TemporaryDirectory() as dir_name:
            out_fn = os.path.join(
                dir_name, f"Compressed_{os.path.splitext(file_name)[0]}.pdf"
            )
            command = (
                "gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 "
                "-dPDFSETTINGS=/default -dNOPAUSE -dQUIET -dBATCH "
                f'-sOutputFile="{out_fn}" "{tf.name}"'
            )

            if run_cmd(command):
                old_size = os.path.getsize(tf.name)
                new_size = os.path.getsize(out_fn)
                update.effective_message.reply_text(
                    _(
                        "File size reduced by <b>{:.0%}</b>, "
                        "from <b>{}</b> to <b>{}</b>".format(
                            (1 - new_size / old_size),
                            humanize.naturalsize(old_size),
                            humanize.naturalsize(new_size),
                        )
                    ),
                    parse_mode=ParseMode.HTML,
                )
                send_result_file(update, context, out_fn, "compress")

            else:
                update.effective_message.reply_text(
                    _("Something went wrong, try again")
                )

    # Clean up memory
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]

    return ConversationHandler.END
