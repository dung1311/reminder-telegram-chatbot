## Hướng dẫn nhanh: Lấy Telegram Bot Token và ADMIN_ID

1) Tạo Bot và lấy token
- Mở Telegram, chat với @BotFather, gõ `/newbot` và làm theo hướng dẫn.
- Sao chép token (dạng `123456:ABC-DEF...`).

2) Lấy `ADMIN_ID`
- Nhanh nhất: chat với @userinfobot và gửi `/start` — bot trả về `user id`.
- Hoặc: gửi tin nhắn tới bot rồi chạy:
  `curl -s "https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates" | jq` và tìm `from.id`.

3) Cập nhật `.env`
- Tạo `.env` từ `.env.example` và điền:

```
TELEGRAM_BOT_TOKEN=PASTE_YOUR_TOKEN_HERE
ADMIN_ID=YOUR_NUMERIC_USER_ID
```

4) Chạy bot
- Cài dependencies: `pip install -r requirements.txt`
- Chạy: `python main.py`

