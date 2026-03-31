from dataclasses import dataclass
from typing import Optional, Any


@dataclass
class Activity:
    id: int
    name: str
    reminder_date: str
    reminder_time: str
    # repeat is stored as an object: {"type": "none"|"daily"|"every_n_days", "interval": int}
    repeat: Any
    confirm_timeout_minutes: int
    created_at: str
    updated_at: str
    pending_message_id: Optional[int] = None
    pending_sent_at: Optional[str] = None
    pending_expires_at: Optional[str] = None
    last_sent_date: Optional[str] = None
    last_confirmed: Optional[bool] = None
    last_confirmed_at: Optional[str] = None
    require_confirmation: Optional[bool] = None