from datetime import datetime, timedelta

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from ..core.config import settings
from ..services.activities import (
    clear_pending,
    find_due_activities,
    find_expired_pending,
    get_activity,
    mark_sent,
    mark_sent_no_pending,
    set_confirmation,
)


def _confirm_keyboard(activity_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Có", callback_data=f"confirm|yes|{activity_id}")],
            [InlineKeyboardButton("Không", callback_data=f"confirm|no|{activity_id}")],
        ]
    )


async def send_activity_confirmation(bot: Bot, activity: dict) -> None:
    now = datetime.now(settings.TIMEZONE)
    # normalize repeat info (backwards-compat)
    repeat_obj = activity.get("repeat")
    if isinstance(repeat_obj, bool):
        repeat_obj = {"type": "daily", "interval": 1} if repeat_obj else {"type": "none", "interval": 0}
    rtype = repeat_obj.get("type") if isinstance(repeat_obj, dict) else "none"

    # If activity does not repeat, just notify once without confirmation buttons
    if rtype == "none":
        message = await bot.send_message(
            chat_id=settings.admin_id,
            text=(
                f"Dũng đẹp trai ơi, đến giờ hoạt động: {activity['name']}\n"
                f"Ngày nhắc: {activity['reminder_date']} - Giờ nhắc: {activity['reminder_time']}\n"
                "Lưu ý: hoạt động này là một lần, không cần xác nhận."
            ),
        )
        # mark_sent will remove non-repeating activities from storage
        mark_sent(activity["id"], message.message_id, now, now)
        return

    # repeating activities: send confirmation buttons and set pending
    # check whether this activity requires confirmation
    require_conf = activity.get("require_confirmation", True)
    if not require_conf:
        # send a simple notification and mark as sent without pending
        message = await bot.send_message(
            chat_id=settings.admin_id,
            text=(
                f"Dũng đẹp trai ơi, đến giờ hoạt động: {activity['name']}\n"
                f"Ngày nhắc: {activity['reminder_date']} - Giờ nhắc: {activity['reminder_time']}\n"
                "Thông báo: không yêu cầu xác nhận cho hoạt động này."
            ),
        )
        mark_sent_no_pending(activity["id"], message.message_id, now)
        return

    expires_at = now + timedelta(minutes=activity["confirm_timeout_minutes"])
    message = await bot.send_message(
        chat_id=settings.admin_id,
        text=(
            f"Dũng đẹp trai ơi, đến giờ hoạt động: {activity['name']}\n"
            f"Ngày nhắc: {activity['reminder_date']} - Giờ nhắc: {activity['reminder_time']}\n"
            f"Vui lòng xác nhận trong {activity['confirm_timeout_minutes']} phút."
        ),
        reply_markup=_confirm_keyboard(activity["id"]),
    )
    mark_sent(activity["id"], message.message_id, now, expires_at)


async def process_due_activities(bot: Bot) -> None:
    now = datetime.now(settings.TIMEZONE)
    due_items = find_due_activities(now)
    for activity in due_items:
        await send_activity_confirmation(bot, activity)


async def process_expired_confirmations(bot: Bot) -> None:
    now = datetime.now(settings.TIMEZONE)
    expired_items = find_expired_pending(now)
    for activity in expired_items:
        if activity.get("pending_message_id") is None:
            continue
        await bot.edit_message_text(
            chat_id=settings.admin_id,
            message_id=activity["pending_message_id"],
            text=(
                f"Dũng đẹp trai ơi, hoạt động '{activity['name']}' đã quá thời gian xác nhận. "
                "Tạm thời xem như chưa làm gì."
            ),
            reply_markup=None,
        )
        clear_pending(activity["id"])


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if not query.data or not query.data.startswith("confirm|"):
        return

    _, action, raw_id = query.data.split("|", maxsplit=2)
    activity_id = int(raw_id)
    activity = get_activity(activity_id)

    if activity is None:
        await query.edit_message_text("Không tìm thấy hoạt động này.", reply_markup=None)
        return

    if activity.get("pending_message_id") is None:
        await query.edit_message_text(
            f"Dũng đẹp trai ơi, hoạt động '{activity['name']}' đã hết hạn xác nhận.",
            reply_markup=None,
        )
        return

    status = action == "yes"
    set_confirmation(activity_id=activity_id, status=status, confirmed_at=datetime.now(settings.TIMEZONE))

    if status:
        await query.edit_message_text(
            f"Cảm ơn Dũng đẹp trai đã xác nhận đã làm: {activity['name']}.",
            reply_markup=None,
        )
        return

    await query.edit_message_text(
        f"Đã ghi nhận Dũng đẹp trai chưa làm hoạt động: {activity['name']}.",
        reply_markup=None,
    )