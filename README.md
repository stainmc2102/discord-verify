# Discord Verify Bot

Bot Discord để xác minh thành viên qua trang web (Google reCAPTCHA). Dự án bao gồm một bot Discord chính (`main.py`) và một web server nhẹ dùng Flask (`web_server.py`) để hiển thị captcha và ghi nhận trạng thái xác minh.

## Tính năng
- Gửi embed xác minh có nút `Xác Minh` trong kênh đã cấu hình
- Mỗi user nhận một đường dẫn xác minh riêng (dựa trên guild_id và user_id)
- Trang web xác minh hiển thị avatar và tên user
- Sử dụng Google reCAPTCHA để chặn bot/spam
- Sau khi xác minh, bot tự động cấp `role` đã cấu hình
- Hỗ trợ cấu hình riêng cho từng server (lưu vào `guild_settings.json`)
- Hỗ trợ public URL thông qua `PUBLIC_URL` hoặc dùng `ngrok` (pyngrok)

## Nội dung repo
- `main.py` — Bot Discord chính (slash commands, view/button, logic cấp role)
- `web_server.py` — Flask app cho trang xác minh, xử lý reCAPTCHA và trạng thái
- `templates/verify.html` — Giao diện trang xác minh (Tiếng Việt)
- `guild_settings.json` — Lưu cài đặt verify per-guild (tạo tự động)
- `.env.example` — Ví dụ các biến môi trường cần cấu hình
- `pyproject.toml` — dependencies chính của dự án

## Yêu cầu
- Python 3.11+
- Kết nối Internet (để gọi reCAPTCHA và (tuỳ chọn) ngrok)

## Phụ thuộc / Dependencies
Bạn có thể cài trực tiếp các phụ thuộc bằng `pip` từ `requirements.txt` (gợi ý cho môi trường reproducible).

Các gói chính (phiên bản đã kiểm tra / khuyến nghị):

- `aiohappyeyeballs==2.6.1`
- `aiohttp==3.13.2`
- `aiosignal==1.4.0`
- `attrs==25.4.0`
- `blinker==1.9.0`
- `certifi==2025.11.12`
- `charset-normalizer==3.4.4`
- `click==8.3.1`
- `discord.py==2.6.4`
- `Flask==3.1.2`
- `frozenlist==1.8.0`
- `idna==3.11`
- `itsdangerous==2.2.0`
- `Jinja2==3.1.6`
- `MarkupSafe==3.0.3`
- `multidict==6.7.0`
- `propcache==0.4.1`
- `pyngrok==7.5.0`
- `python-dotenv==1.2.1`
- `PyYAML==6.0.3`
- `requests==2.32.5`
- `typing_extensions==4.15.0`
- `urllib3==2.5.0`
- `Werkzeug==3.1.3`
- `yarl==1.22.0`

Cài từ `requirements.txt`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Cài đặt (chạy local)
1. Clone repo (nếu chưa):

```bash
git clone <repo-url>
cd discord-verify
```

2. Tạo môi trường ảo và cài dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install "discord-py>=2.6.4" flask pyngrok python-dotenv requests
```

3. Tạo file `.env` từ `.env.example` và điền giá trị cần thiết:

```bash
cp .env.example .env
# Mở .env và điền các giá trị:
# DISCORD_TOKEN — token bot Discord
# VERIFY_CHANNEL_ID — (tùy chọn) ID kênh mặc định để bot gửi embed
# VERIFIED_ROLE_ID — (tùy chọn) ID role mặc định để cấp khi hoàn tất xác minh
# RECAPTCHA_SITE_KEY / RECAPTCHA_SECRET_KEY — Google reCAPTCHA v2 keys
# NGROK_AUTH_TOKEN — (tùy chọn) token ngrok nếu muốn tự động mở tunnel
# PUBLIC_URL — (tùy chọn) nếu bạn host web ở môi trường có URL công khai, đặt vào đây
```

4. Chạy bot:

```bash
python main.py
```

Lưu ý: `main.py` khởi động một thread Flask (port `3000`) rồi chạy bot. Nếu bạn muốn chạy Flask / bot riêng biệt khi deploy, tách cách khởi chạy theo nhu cầu.

## Cấu hình URL công khai
- Cách 1 (khuyến nghị local/test): Sử dụng `ngrok` — đặt `NGROK_AUTH_TOKEN` trong `.env` rồi chạy `python main.py`. Ứng dụng sẽ cố gắng dùng `pyngrok` để mở tunnel tới port `3000`.
- Cách 2 (production): Set `PUBLIC_URL` thành URL công khai của server (ví dụ `https://example.com:3000`), khi đó bot sẽ dùng URL đó để tạo link verify.

## Các lệnh (Admin)
- `/verifychannel <channel>` — Đặt kênh xác minh cho server hiện tại
- `/verifyrole <role>` — Đặt role sẽ được cấp sau khi xác minh
- `/refreshverify` — Làm mới embed xác minh trong kênh đã set
- `/verifyinfo` — Hiển thị cài đặt hiện tại của server

Lệnh prefix cũ:
- `!refresh` — tương đương `/refreshverify` (Admin)

## Cách hoạt động 
1. Admin set kênh & role bằng lệnh bot.
2. Bot gửi embed xác minh (kèm nút `Xác Minh`) vào kênh đó.
3. User nhấn nút → bot sinh đường link verify và lưu thông tin tạm (avatar, tên,...).
4. User mở link → hoàn thành reCAPTCHA → web thêm verify_key vào danh sách verified.
5. Bot vòng kiểm tra (task) sẽ cấp role cho member tương ứng và xóa khóa tạm.

## Biến môi trường (chi tiết)
- `DISCORD_TOKEN` (bắt buộc): Token bot Discord
- `VERIFY_CHANNEL_ID` (tùy chọn): ID kênh mặc định để bot gửi embed
- `VERIFIED_ROLE_ID` (tùy chọn): ID role mặc định để cấp
- `RECAPTCHA_SITE_KEY` và `RECAPTCHA_SECRET_KEY` (nên có): Google reCAPTCHA v2
- `SESSION_SECRET` (tùy chọn): Flask session secret (mặc định có fallback)
- `NGROK_AUTH_TOKEN` (tùy chọn): token cho ngrok nếu muốn tự mở tunnel
- `PUBLIC_URL` (tùy chọn): nếu set thì dùng URL này thay vì mở ngrok

## Triển khai (gợi ý)
- Đặt `PUBLIC_URL` tới domain/host nơi Flask app reachable (port 3000). Đảm bảo firewall mở port nếu cần.
- Chạy `python main.py` trong một process manager (`systemd`, `pm2`, `supervisord`, v.v.) để giữ bot và web server chạy.

## Debug & Troubleshoot
- Nếu bot không khởi động: kiểm tra `DISCORD_TOKEN` trong `.env`.
- Nếu trang verify báo `reCAPTCHA chưa được cấu hình`: kiểm tra `RECAPTCHA_SITE_KEY` / `RECAPTCHA_SECRET_KEY`.
- Nếu public URL rỗng và bạn không muốn dùng ngrok: set `PUBLIC_URL`.
- Nếu role không được cấp: kiểm tra bot có quyền `Manage Roles` và role verified nằm dưới role bot trong danh sách role server.

## Ghi chú kỹ thuật
- Dữ liệu cài đặt guild được lưu vào `guild_settings.json` (JSON đơn giản). Tệp này được tạo/tự động cập nhật khi admin dùng lệnh set.
- Flask app lưu trạng thái tạm `verified_users` và `user_info_store` trong bộ nhớ process — khi deploy nhiều instance, nên chuyển sang persistence bên ngoài (Redis / DB) để đồng bộ.


---

