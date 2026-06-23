# rules/security — Xử lý secret (nạp khi đụng PrivateConfig/key/deploy)

> Đọc cùng [CORE](../CORE.md) (secret không echo đã ở đó). Đây là chi tiết + hành động.

- `config/PrivateConfig.java` và `runAider.bat` chứa **API key/secret LIVE commit thẳng vào repo** (Binance key/secret, Gemini key).
- Các key này ĐÃ LỘ trong git history → cần **rotate (xoay)** + chuyển sang config KHÔNG track.
- Khi đụng các file này: KHÔNG echo secret ra commit / log / chat. Nhắc user rotate nếu chưa làm.
