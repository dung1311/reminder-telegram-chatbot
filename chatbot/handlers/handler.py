from telegram import Update
from telegram.ext import (
    ContextTypes,
)
from telegram.ext import ConversationHandler, MessageHandler, filters

from chatbot.core.config import settings
from chatbot.services.activities import (
    create_activity,
    delete_activity,
    get_activity,
    list_activities,
    update_activity,
)


HELP_TEXT = (
    "Xin chào Dũng đẹp trai. Đây là menu quản lý hoạt động:\n"
    "/start - Mở menu\n"
    "/menu - Xem menu lệnh\n"
    "/list_activities - Liệt kê các hoạt động\n"
    "/add_activity - Thêm hoạt động bằng form tương tác\n"
    "(lần lượt nhập tên, ngày DD-MM-YYYY, giờ HH:MM, kiểu lặp: none|daily|every:2, yêu cầu xác nhận: yes|no, timeout phút)\n"
    "/edit_activity id|ten|ngày|giờ|lap_lai|requires_confirm|timeout_phút\n"
    "Ví dụ: /edit_activity 1|Hop nhom|03-04-2026|09:00|no|yes|10\n"
    "/delete_activity id"
)


def _is_admin(update: Update) -> bool:
    user = update.effective_user
    if user is None:
        return False
    return str(user.id) == str(settings.admin_id)


async def _require_admin(update: Update) -> bool:
    if _is_admin(update):
        return True
    if update.message is not None:
        await update.message.reply_text("Xin lỗi, bot này chỉ dành cho Dũng đẹp trai.")
    return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_admin(update):
        return
    await update.message.reply_text(HELP_TEXT)


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_admin(update):
        return
    await update.message.reply_text(HELP_TEXT)


async def list_activities_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_admin(update):
        return

    items = list_activities()
    if not items:
        await update.message.reply_text("Dũng đẹp trai ơi, hiện chưa có hoạt động nào.")
        return
    lines = ["Danh sách hoạt động của Dũng đẹp trai:"]
    for item in items:
        repeat_raw = item.get("repeat")
        if isinstance(repeat_raw, bool):
            repeat_display = "hàng ngày" if repeat_raw else "không"
        elif isinstance(repeat_raw, dict):
            if repeat_raw.get("type") == "none":
                repeat_display = "không"
            elif repeat_raw.get("type") == "daily":
                repeat_display = "hàng ngày"
            elif repeat_raw.get("type") == "every_n_days":
                repeat_display = f"mỗi {repeat_raw.get('interval')} ngày"
            else:
                repeat_display = str(repeat_raw)
        else:
            repeat_display = str(repeat_raw)
        req_conf = item.get("require_confirmation", True)
        req_display = "có" if req_conf else "không"
        lines.append(
            (
                f"#{item['id']} | {item['name']} | ngày {item['reminder_date']} | "
                f"giờ {item['reminder_time']} | lặp lại: {repeat_display} | "
                f"yêu cầu xác nhận: {req_display} | timeout: {item['confirm_timeout_minutes']} phút"
            )
        )
    await update.message.reply_text("\n".join(lines))


# edit flow states
(TITLE, DATE, TIME, REPEAT_TYPE, REQUIRES_CONFIRM, TIMEOUT) = range(6)
# edit flow states
(
    EDIT_SELECT,
    EDIT_TITLE,
    EDIT_DATE,
    EDIT_TIME,
    EDIT_REPEAT,
    EDIT_REQUIRES_CONFIRM,
    EDIT_TIMEOUT,
) = range(6, 13)


async def add_activity_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _require_admin(update):
        return ConversationHandler.END
    await update.message.reply_text("Nhập tên hoạt động:")
    return TITLE


async def add_activity_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_activity"] = {"name": update.message.text.strip()}
    await update.message.reply_text("Nhập ngày nhắc (DD-MM-YYYY):")
    return DATE


async def add_activity_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_activity"]["reminder_date"] = update.message.text.strip()
    await update.message.reply_text("Nhập giờ nhắc (HH:MM):")
    return TIME


async def add_activity_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_activity"]["reminder_time"] = update.message.text.strip()
    await update.message.reply_text(
        "Nhập kiểu lặp: 'none' (không lặp), 'daily' (hàng ngày) hoặc 'every:N' (mỗi N ngày). Ví dụ: every:2"
    )
    return REPEAT_TYPE


async def add_activity_repeat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_activity"]["repeat"] = update.message.text.strip()
    await update.message.reply_text(
        "Hoạt động này có yêu cầu xác nhận khi nhắc không? (yes/no). Nếu 'no' bot chỉ gửi thông báo, không lưu log xác nhận."
    )
    return REQUIRES_CONFIRM


async def add_activity_timeout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    payload = context.user_data.get("new_activity", {})
    try:
        timeout = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Timeout phải là số nguyên (phút). Nhập lại timeout:")
        return TIMEOUT

    payload["confirm_timeout_minutes"] = timeout
    try:
        created = create_activity(
            name=payload["name"],
            reminder_date=payload["reminder_date"],
            reminder_time=payload["reminder_time"],
            repeat=payload["repeat"],
            confirm_timeout_minutes=payload["confirm_timeout_minutes"],
            require_confirmation=payload.get("require_confirmation", True),
        )
    except Exception as exc:
        await update.message.reply_text(f"Không tạo được hoạt động: {exc}")
        return ConversationHandler.END

    await update.message.reply_text(
        (
            f"Dũng đẹp trai đã tạo hoạt động thành công: #{created['id']} - {created['name']} "
            f"vào {created['reminder_date']} lúc {created['reminder_time']}."
        )
    )
    return ConversationHandler.END


async def add_activity_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Hủy thêm hoạt động.")
    return ConversationHandler.END


async def add_activity_requires_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    v = update.message.text.strip().lower()
    if v in {"yes", "y", "co", "có", "true", "1"}:
        context.user_data["new_activity"]["require_confirmation"] = True
    elif v in {"no", "n", "khong", "không", "false", "0"}:
        context.user_data["new_activity"]["require_confirmation"] = False
    else:
        await update.message.reply_text("Vui lòng trả lời 'yes' hoặc 'no'. Hoạt động có yêu cầu xác nhận không?")
        return REQUIRES_CONFIRM

    await update.message.reply_text("Nhập timeout xác nhận (phút):")
    return TIMEOUT


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Global cancel: ends any active conversation when the user sends /cancel
    if update.message is not None:
        await update.message.reply_text("Đã hủy thao tác. Bạn có thể tiếp tục dùng lệnh khác.")
    return ConversationHandler.END


async def edit_activity_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start interactive edit flow. Ask for activity id to edit."""
    if not await _require_admin(update):
        return ConversationHandler.END

    await update.message.reply_text(
        "Nhập id hoạt động cần sửa (hoặc gửi 'list' để xem danh sách):"
    )
    return EDIT_SELECT


async def edit_activity_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text.lower() == "list":
        # reuse list command
        items = list_activities()
        if not items:
            await update.message.reply_text("Hiện không có hoạt động nào.")
        else:
            lines = [f"#{it['id']} - {it['name']} (ngày {it['reminder_date']} {it['reminder_time']})" for it in items]
            await update.message.reply_text("\n".join(lines))
        await update.message.reply_text("Nhập id hoạt động cần sửa:")
        return EDIT_SELECT

    try:
        aid = int(text)
    except ValueError:
        await update.message.reply_text("Id không hợp lệ. Nhập lại id hoạt động: (hoặc 'list')")
        return EDIT_SELECT

    activity = get_activity(aid)
    if activity is None:
        await update.message.reply_text("Không tìm thấy hoạt động với id đó. Nhập lại id (hoặc 'list'):")
        return EDIT_SELECT

    # store and ask for new values (use '-' để giữ nguyên)
    context.user_data["edit_activity"] = activity.copy()
    await update.message.reply_text(
        (
            f"Sửa hoạt động #{activity['id']} - {activity['name']}\n"
            "Gửi tên mới hoặc '-' để giữ nguyên:"
        )
    )
    return EDIT_TITLE


async def edit_activity_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    v = update.message.text.strip()
    if v != "-":
        context.user_data["edit_activity"]["name"] = v
    await update.message.reply_text("Gửi ngày mới (DD-MM-YYYY) hoặc '-' để giữ nguyên:")
    return EDIT_DATE


async def edit_activity_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    v = update.message.text.strip()
    if v != "-":
        context.user_data["edit_activity"]["reminder_date"] = v
    await update.message.reply_text("Gửi giờ mới (HH:MM) hoặc '-' để giữ nguyên:")
    return EDIT_TIME


async def edit_activity_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    v = update.message.text.strip()
    if v != "-":
        context.user_data["edit_activity"]["reminder_time"] = v
    await update.message.reply_text(
        "Gửi kiểu lặp: 'none'|'daily'|'every:N' hoặc '-' để giữ nguyên:"
    )
    return EDIT_REPEAT


async def edit_activity_repeat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    v = update.message.text.strip()
    if v != "-":
        context.user_data["edit_activity"]["repeat"] = v
    await update.message.reply_text("Hoạt động này có yêu cầu xác nhận khi nhắc không? (yes/no) hoặc '-' để giữ nguyên:")
    return EDIT_REQUIRES_CONFIRM


async def edit_activity_requires_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    v = update.message.text.strip()
    if v != "-":
        normalized = v.lower()
        if normalized in {"yes", "y", "co", "có", "true", "1"}:
            context.user_data["edit_activity"]["require_confirmation"] = True
        elif normalized in {"no", "n", "khong", "không", "false", "0"}:
            context.user_data["edit_activity"]["require_confirmation"] = False
        else:
            await update.message.reply_text("Vui lòng trả lời 'yes' hoặc 'no' (hoặc '-'):")
            return EDIT_REQUIRES_CONFIRM

    await update.message.reply_text("Gửi timeout xác nhận (phút) hoặc '-' để giữ nguyên:")
    return EDIT_TIMEOUT


async def edit_activity_timeout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    v = update.message.text.strip()
    payload = context.user_data.get("edit_activity", {})
    try:
        if v != "-":
            timeout = int(v)
            payload["confirm_timeout_minutes"] = timeout
    except ValueError:
        await update.message.reply_text("Timeout phải là số nguyên. Nhập lại timeout hoặc '-' để giữ nguyên:")
        return EDIT_TIMEOUT

    # perform update
    try:
        updated = update_activity(
            activity_id=payload["id"],
            name=payload["name"],
            reminder_date=payload["reminder_date"],
            reminder_time=payload["reminder_time"],
            repeat=payload["repeat"],
            confirm_timeout_minutes=int(payload["confirm_timeout_minutes"]),
            require_confirmation=payload.get("require_confirmation", True),
        )
    except Exception as exc:
        await update.message.reply_text(f"Không cập nhật được hoạt động: {exc}")
        return ConversationHandler.END

    if updated is None:
        await update.message.reply_text("Không tìm thấy id hoạt động để cập nhật.")
        return ConversationHandler.END

    await update.message.reply_text(
        (
            f"Dũng đẹp trai đã cập nhật xong hoạt động #{updated['id']} - {updated['name']} "
            f"vào {updated['reminder_date']} lúc {updated['reminder_time']}."
        )
    )
    return ConversationHandler.END


async def delete_activity_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_admin(update):
        return

    if not context.args:
        msg = update.effective_message
        if msg is not None:
            await msg.reply_text("Dũng đẹp trai vui lòng dùng: /delete_activity id")
        else:
            await context.bot.send_message(chat_id=settings.admin_id, text="Dũng đẹp trai vui lòng dùng: /delete_activity id")
        return

    try:
        activity_id = int(context.args[0])
    except ValueError:
        msg = update.effective_message
        if msg is not None:
            await msg.reply_text("Id hoạt động phải là số nguyên.")
        else:
            await context.bot.send_message(chat_id=settings.admin_id, text="Id hoạt động phải là số nguyên.")
        return

    deleted = delete_activity(activity_id)
    if not deleted:
        msg = update.effective_message
        if msg is not None:
            await msg.reply_text("Không tìm thấy hoạt động cần xóa.")
        else:
            await context.bot.send_message(chat_id=settings.admin_id, text="Không tìm thấy hoạt động cần xóa.")
        return

    msg = update.effective_message
    if msg is not None:
        await msg.reply_text(f"Dũng đẹp trai đã xóa hoạt động #{activity_id} thành công.")
    else:
        await context.bot.send_message(chat_id=settings.admin_id, text=f"Dũng đẹp trai đã xóa hoạt động #{activity_id} thành công.")
