import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from chatbot.models.activities import Activity


DATA_FILE = Path(__file__).resolve().parents[1] / "conversations" / "activities.json"
DATE_FMT = "%d-%m-%Y"
TIME_FMT = "%H:%M"


def _ensure_data_file() -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text(
            json.dumps({"activities": [], "confirmation_logs": []}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _load_data() -> dict[str, Any]:
    _ensure_data_file()
    raw = DATA_FILE.read_text(encoding="utf-8").strip()
    if not raw:
        return {"activities": [], "confirmation_logs": []}
    data = json.loads(raw)
    data.setdefault("activities", [])
    data.setdefault("confirmation_logs", [])
    return data


def _save_data(data: dict[str, Any]) -> None:
    # Reindex activities to ensure ids are contiguous from 1..N
    activities = data.get("activities", [])
    old_to_new: dict[int, int] = {}
    for new_idx, item in enumerate(activities, start=1):
        old_to_new[item.get("id")] = new_idx
        item["id"] = new_idx

    # Update confirmation_logs activity_id references where applicable
    for log in data.get("confirmation_logs", []):
        aid = log.get("activity_id")
        if aid is None:
            continue
        if aid in old_to_new:
            log["activity_id"] = old_to_new[aid]
        else:
            # activity no longer exists (e.g., one-time deleted); set to None
            log["activity_id"] = None

    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _to_activity(payload: dict[str, Any]) -> Activity:
    return Activity(**payload)


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"yes", "y", "true", "1", "co", "có", "lap", "lặp"}:
        return True
    if normalized in {"no", "n", "false", "0", "khong", "không", "khong lap", "không lặp"}:
        return False
    raise ValueError("repeat chỉ nhận yes/no")


def _parse_repeat(value: str) -> dict:
    """Parse repeat from user input into a dict: {type: 'none'|'daily'|'every_n_days', interval: int}

    Accepts values like: 'no', 'none', 'yes', 'daily', 'every:2', 'every 2', '2'
    """
    if isinstance(value, dict):
        return value
    normalized = value.strip().lower()
    if normalized in {"no", "none", "khong", "không", "n"}:
        return {"type": "none", "interval": 0}
    if normalized in {"yes", "y", "daily", "day", "hàng ngày", "hang ngay", "co", "có"}:
        return {"type": "daily", "interval": 1}

    # try patterns like 'every:2' or 'every 2' or just a number meaning every N days
    if normalized.startswith("every:") or normalized.startswith("every "):
        parts = normalized.replace("every:", "").replace("every ", "").strip()
        try:
            n = int(parts)
            if n <= 0:
                raise ValueError
            return {"type": "every_n_days", "interval": n}
        except Exception:
            raise ValueError("repeat không hợp lệ. Ví dụ: 'daily' hoặc 'every:2'")

    # if it's just a number
    try:
        n = int(normalized)
        if n <= 0:
            raise ValueError
        return {"type": "every_n_days", "interval": n}
    except Exception:
        raise ValueError("repeat không hợp lệ. Ví dụ: 'daily' hoặc 'every:2'")


def _validate_date(date_str: str) -> None:
    datetime.strptime(date_str, DATE_FMT)


def _validate_time(time_str: str) -> None:
    datetime.strptime(time_str, TIME_FMT)


def list_activities() -> list[dict[str, Any]]:
    data = _load_data()
    return sorted(data["activities"], key=lambda item: item["id"])


def get_activity(activity_id: int) -> Optional[dict[str, Any]]:
    data = _load_data()
    for item in data["activities"]:
        if item["id"] == activity_id:
            return item
    return None


def create_activity(
    name: str,
    reminder_date: str,
    reminder_time: str,
    repeat: str,
    confirm_timeout_minutes: int,
    require_confirmation: bool = True,
) -> dict[str, Any]:
    _validate_date(reminder_date)
    _validate_time(reminder_time)
    # support old boolean-style repeat and new repeat formats
    try:
        repeat_value = _parse_repeat(repeat)
    except ValueError:
        # fallback to boolean parser for backward compatibility
        repeat_value = {"type": "daily" if _parse_bool(repeat) else "none", "interval": 1 if _parse_bool(repeat) else 0}
    timeout_value = int(confirm_timeout_minutes)
    if timeout_value <= 0:
        raise ValueError("confirm_timeout_minutes phải lớn hơn 0")

    data = _load_data()
    now_iso = datetime.utcnow().isoformat()
    new_id = max((item["id"] for item in data["activities"]), default=0) + 1
    record = {
        "id": new_id,
        "name": name.strip(),
        "reminder_date": reminder_date,
        "reminder_time": reminder_time,
        "repeat": repeat_value,
        "require_confirmation": bool(require_confirmation),
        "confirm_timeout_minutes": timeout_value,
        "created_at": now_iso,
        "updated_at": now_iso,
        "pending_message_id": None,
        "pending_sent_at": None,
        "pending_expires_at": None,
        "last_sent_date": None,
        "last_confirmed": None,
        "last_confirmed_at": None,
    }
    _to_activity(record)
    data["activities"].append(record)
    _save_data(data)
    return record


def update_activity(
    activity_id: int,
    name: str,
    reminder_date: str,
    reminder_time: str,
    repeat: str,
    confirm_timeout_minutes: int,
    require_confirmation: bool = True,
) -> Optional[dict[str, Any]]:
    _validate_date(reminder_date)
    _validate_time(reminder_time)
    try:
        repeat_value = _parse_repeat(repeat)
    except ValueError:
        repeat_value = {"type": "daily" if _parse_bool(repeat) else "none", "interval": 1 if _parse_bool(repeat) else 0}
    timeout_value = int(confirm_timeout_minutes)
    if timeout_value <= 0:
        raise ValueError("confirm_timeout_minutes phải lớn hơn 0")

    data = _load_data()
    for item in data["activities"]:
        if item["id"] == activity_id:
            item["name"] = name.strip()
            item["reminder_date"] = reminder_date
            item["reminder_time"] = reminder_time
            item["repeat"] = repeat_value
            item["confirm_timeout_minutes"] = timeout_value
            item["require_confirmation"] = bool(require_confirmation)
            item["updated_at"] = datetime.utcnow().isoformat()
            _to_activity(item)
            _save_data(data)
            return item
    return None


def delete_activity(activity_id: int) -> bool:
    data = _load_data()
    before = len(data["activities"])
    data["activities"] = [item for item in data["activities"] if item["id"] != activity_id]
    deleted = len(data["activities"]) < before
    if deleted:
        # remove any confirmation logs related to this activity
        data["confirmation_logs"] = [log for log in data.get("confirmation_logs", []) if log.get("activity_id") != activity_id]
        _save_data(data)
    return deleted


def mark_sent(activity_id: int, message_id: int, sent_at: datetime, expires_at: datetime) -> None:
    data = _load_data()
    sent_date = sent_at.strftime(DATE_FMT)
    for item in list(data.get("activities", [])):
        if item["id"] == activity_id:
            # if activity is non-repeating, remove it completely after sending
            repeat_obj = item.get("repeat")
            if isinstance(repeat_obj, bool):
                repeat_obj = {"type": "daily", "interval": 1} if repeat_obj else {"type": "none", "interval": 0}
            rtype = repeat_obj.get("type") if isinstance(repeat_obj, dict) else "none"

            if rtype == "none":
                # remove activity and do not keep any traces
                data["activities"] = [a for a in data.get("activities", []) if a.get("id") != activity_id]
                _save_data(data)
                return

            # otherwise keep pending info
            item["pending_message_id"] = message_id
            item["pending_sent_at"] = sent_at.isoformat()
            item["pending_expires_at"] = expires_at.isoformat()
            item["last_sent_date"] = sent_date
            item["updated_at"] = datetime.utcnow().isoformat()
            break
    _save_data(data)


def mark_sent_no_pending(activity_id: int, message_id: int, sent_at: datetime) -> None:
    """Mark activity as sent (for repeating activities) without creating a pending confirmation.

    Used when the activity does not require confirmation but should still record last_sent_date.
    """
    data = _load_data()
    sent_date = sent_at.strftime(DATE_FMT)
    for item in list(data.get("activities", [])):
        if item["id"] == activity_id:
            item["pending_message_id"] = None
            item["pending_sent_at"] = None
            item["pending_expires_at"] = None
            item["last_sent_date"] = sent_date
            item["updated_at"] = datetime.utcnow().isoformat()
            break
    _save_data(data)


def clear_pending(activity_id: int) -> None:
    data = _load_data()
    for item in data["activities"]:
        if item["id"] == activity_id:
            item["pending_message_id"] = None
            item["pending_sent_at"] = None
            item["pending_expires_at"] = None
            item["updated_at"] = datetime.utcnow().isoformat()
            break
    _save_data(data)


def set_confirmation(activity_id: int, status: bool, confirmed_at: datetime) -> Optional[dict[str, Any]]:
    data = _load_data()
    updated = None
    for item in data["activities"]:
        if item["id"] == activity_id:
            item["last_confirmed"] = status
            item["last_confirmed_at"] = confirmed_at.isoformat()
            item["pending_message_id"] = None
            item["pending_sent_at"] = None
            item["pending_expires_at"] = None
            item["updated_at"] = datetime.utcnow().isoformat()
            updated = item
            break

    if updated is not None:
        data["confirmation_logs"].append(
            {
                "activity_id": activity_id,
                "status": status,
                "confirmed_at": confirmed_at.isoformat(),
            }
        )
        _save_data(data)
    return updated


def find_due_activities(now: datetime) -> list[dict[str, Any]]:
    due_items: list[dict[str, Any]] = []
    today = now.strftime(DATE_FMT)
    current_time = now.strftime(TIME_FMT)
    for item in list_activities():
        if item["pending_message_id"] is not None:
            continue

        repeat_obj = item.get("repeat")
        # normalize old boolean repeat
        if isinstance(repeat_obj, bool):
            repeat_obj = {"type": "daily", "interval": 1} if repeat_obj else {"type": "none", "interval": 0}

        rtype = repeat_obj.get("type") if isinstance(repeat_obj, dict) else "none"

        # repeated patterns
        if rtype == "daily":
            if item["reminder_time"] <= current_time and item.get("last_sent_date") != today:
                due_items.append(item)
            continue

        if rtype == "every_n_days":
            interval = int(repeat_obj.get("interval", 1))
            try:
                baseline = datetime.strptime(item["reminder_date"], DATE_FMT).date()
            except Exception:
                continue
            days_diff = (now.date() - baseline).days
            if days_diff >= 0 and days_diff % interval == 0:
                if item["reminder_time"] <= current_time and item.get("last_sent_date") != today:
                    due_items.append(item)
            continue

        # none - one time reminder
        if item["reminder_date"] != today:
            continue

        if item["reminder_time"] <= current_time and item.get("last_sent_date") != today:
            due_items.append(item)

    return due_items


def find_expired_pending(now: datetime) -> list[dict[str, Any]]:
    expired_items: list[dict[str, Any]] = []
    for item in list_activities():
        expiry_raw = item.get("pending_expires_at")
        if item.get("pending_message_id") is None or not expiry_raw:
            continue
        expires_at = datetime.fromisoformat(expiry_raw)
        if now >= expires_at:
            expired_items.append(item)
    return expired_items


def save(date_str: str, status: bool) -> None:
    data = _load_data()
    data["confirmation_logs"].append(
        {
            "activity_id": None,
            "status": status,
            "confirmed_at": datetime.utcnow().isoformat(),
            "date_label": date_str,
        }
    )
    _save_data(data)