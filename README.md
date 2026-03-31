## Hướng dẫn nhanh: Lấy Telegram Bot Token và ADMIN_ID

1) Tạo Telegram Bot và lấy `BOT_TOKEN`
- Mở Telegram, chat với BotFather (@BotFather).
- Gõ `/newbot` và làm theo hướng dẫn (đặt tên + username cho bot).
- Sau khi tạo xong, BotFather sẽ trả về `HTTP API token` — copy đoạn token này (dạng `123456:ABC-DEF...`).

2) Lấy `ADMIN_ID` (ID Telegram của bạn)
Có 2 cách nhanh:

- Cách A (dùng @userinfobot):
  - Mở Telegram, tìm và chat với @userinfobot.
  - Gõ `/start` hoặc xem tin nhắn trả về; bot sẽ hiển thị `user id` của bạn.

- Cách B (dùng API):
  - Thay `YOUR_BOT_TOKEN` bằng token lấy từ BotFather và chạy lệnh curl:

```bash
curl -s "https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates" | jq
```
  - Sau khi bạn gửi tin nhắn tới bot (hoặc gọi `/start`), trong kết quả JSON sẽ có `from.id` — đó là `ADMIN_ID` của bạn.

3) Cập nhật file `.env.example`
- Tạo file `.env` từ `.env.example` hoặc chỉnh trực tiếp `.env.example` (khuyến nghị: tạo `.env`).
- Thêm token và admin id, ví dụ:

```
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
ADMIN_ID=987654321
```

4) Cài đặt và chạy bot
- Cài dependencies (nếu chưa cài):

```bash
pip install -r requirements.txt
```

- Chạy bot:

```bash
python main.py
```

5) Ghi chú
- `ADMIN_ID` phải là số nguyên (không có dấu cách).
- Nếu không thấy tin nhắn khi dùng `getUpdates`, hãy gửi `/start` tới bot từ tài khoản Telegram của bạn trước khi chạy `getUpdates`.

Nếu muốn, tôi có thể thêm script nhỏ `get_admin_id.py` để tự động in `ADMIN_ID` (bạn chỉ cần chạy với `BOT_TOKEN`).
