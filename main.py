import logging
from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from chatbot.core.config import settings
from chatbot.handlers.fixed_schedule import (
    handle_callback,
    process_due_activities,
    process_expired_confirmations,
)
from chatbot.handlers.handler import (
    add_activity_command,
    delete_activity_command,
    edit_activity_command,
    list_activities_command,
    menu,
    start,
)
from chatbot.handlers.handler import (
    add_activity_title,
    add_activity_date,
    add_activity_time,
    add_activity_repeat,
    add_activity_requires_confirm,
    add_activity_timeout,
    add_activity_cancel,
    cancel_command,
)
from chatbot.handlers.handler import TITLE, DATE, TIME, REPEAT_TYPE, REQUIRES_CONFIRM, TIMEOUT
from chatbot.handlers.handler import (
    EDIT_SELECT,
    EDIT_TITLE,
    EDIT_DATE,
    EDIT_TIME,
    EDIT_REPEAT,
    EDIT_REQUIRES_CONFIRM,
    EDIT_TIMEOUT,
)
from chatbot.handlers.handler import (
    edit_activity_select,
    edit_activity_title,
    edit_activity_date,
    edit_activity_time,
    edit_activity_repeat,
    edit_activity_requires_confirm,
    edit_activity_timeout,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

async def run_scheduler(context: ContextTypes.DEFAULT_TYPE) -> None:
    await process_due_activities(context.bot)
    await process_expired_confirmations(context.bot)


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands(
        [
            BotCommand("start", "Mở menu"),
            BotCommand("menu", "Xem menu"),
            BotCommand("list_activities", "Các hoạt động"),
            BotCommand("add_activity", "Thêm hoạt động"),
            BotCommand("edit_activity", "Sửa hoạt động"),
            BotCommand("delete_activity", "Xóa hoạt động"),
            BotCommand("cancel", "Hủy thao tác"),
        ]
    )

def main():
    app = Application.builder().token(settings.telegram_bot_token).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("list_activities", list_activities_command))
    # Global cancel handler - ends any active ConversationHandler
    app.add_handler(CommandHandler("cancel", cancel_command))
    # Conversation based add_activity
    conv = ConversationHandler(
        entry_points=[CommandHandler("add_activity", add_activity_command)],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_activity_title)],
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_activity_date)],
            TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_activity_time)],
            REPEAT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_activity_repeat)],
            REQUIRES_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_activity_requires_confirm)],
            TIMEOUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_activity_timeout)],
        },
        fallbacks=[CommandHandler("cancel", add_activity_cancel)],
    )
    app.add_handler(conv)
    # Conversation based edit_activity
    edit_conv = ConversationHandler(
        entry_points=[CommandHandler("edit_activity", edit_activity_command)],
        states={
            EDIT_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_activity_select)],
            EDIT_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_activity_title)],
            EDIT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_activity_date)],
            EDIT_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_activity_time)],
            EDIT_REPEAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_activity_repeat)],
            EDIT_REQUIRES_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_activity_requires_confirm)],
            EDIT_TIMEOUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_activity_timeout)],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
    )
    app.add_handler(edit_conv)
    app.add_handler(CommandHandler("delete_activity", delete_activity_command))

    app.add_handler(CallbackQueryHandler(handle_callback))

    if app.job_queue is None:
        raise RuntimeError(
            "JobQueue chưa được cài đặt. Hãy cài python-telegram-bot với extras job-queue."
        )

    app.job_queue.run_repeating(
        run_scheduler,
        interval=30,
        first=5,
        job_kwargs={"misfire_grace_time": 30},
    )

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
