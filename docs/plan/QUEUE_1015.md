# QUEUE_1015 — việc chuẩn bị song song với nạp dữ liệu VZ (MASTER 2026-10-15)

Chạy TUẦN TỰ P1 → P5, song song với Phase 1 (Phase 1 ưu tiên đĩa/kernel; sàn đĩa 30 GB). Luật chung: không đụng 242 (chỉ đọc khi ghi rõ), shadow, systemd; không Binance REST từ Oracle; Kaggle ≤ 2 kernel; Python logging, Java SLF4J; mỗi P xong commit (trailer) + 1 dòng vào `docs/research/VZ_QUEUE_STATUS.md`. P nào BLOCKED ⇒ ghi lý do, sang P kế.

## P1 — kiểm toàn vẹn sau khi owner tự xoá dataset Kaggle (làm ngay)
- Danh sách PHẢI còn: mọi `vz-*`; `bcast-2020-2021h1-p1`; `sim-ho26-bundle` + dataset HO4 (`ho4p1-*`, bundle Vision A/B); `sim-jar-ecost` (sha 246087fb); jar nền ECMEAS/HO4 (b7c89f09, 0944841c) và jar dùng bởi `ho4p1_queue`/`ec_parity.py`/`ecm_q.py`/`bcast_sim`; `wfo-ticker-2021…2025`; mọi dataset mà template sim hiện hành (K24 + skipFull, `PARITY["ho4p1-c2"]`) khai trong kernel-metadata.
- Thiếu cái nào ⇒ báo ngay; jar thiếu thì build lại từ đúng commit ghi trong docs và so sha256 với số đã ghi (khác ⇒ BLOCKED, không thay thế).
- Output: `docs/data/KAGGLE_REQUIRED.md` (slug, còn/thiếu, ai dùng).

## P2 — thu liquidation forward (nhạy thời gian: ngày nào không thu là mất)
- Sửa/viết lại `collector/liq_ws.py` (hiện 0 dòng): WebSocket `wss://fstream.binance.com/market/stream` stream `!forceOrder@arr` (WS, KHÔNG phải REST). Ghi parquet/CSV theo ngày `~/collect/liq/YYYY-MM-DD.csv.gz`: event_time, symbol, side, order_type, price, avg_price, orig_qty, filled_qty, status, trade_time. Reconnect backoff, heartbeat log mỗi 5′ (số event), xoay file theo ngày UTC.
- Chạy nền trên Oracle bằng systemd user unit hoặc `setsid nohup` + cron watchdog 5′ (tự khởi động lại nếu chết). Không chạy trên 242.
- Ghi rõ giới hạn: Binance chỉ đẩy lệnh thanh lý mới nhất mỗi symbol mỗi giây (snapshot) ⇒ là mẫu, không phải toàn bộ.
- Kiểm: sau 1 giờ có event; so sơ bộ với nến 1m cùng phút (giá thanh lý nằm trong [low, high] ≥ 99%). Mỗi tuần upload gộp lên Kaggle `chuyendinh/vz-liq-forward` (version).

## P3 — pipeline so shadow #2 ↔ sim (cho release v1)
- Mục tiêu: hằng tuần so lệnh paper của `shadow-c3b` (K24 + skipFull) với sim cùng cấu hình chạy trên dữ liệu Vision cùng giai đoạn, theo `docs/prereg/PREREG_SHADOW2_PROMOTION.md` (đọc kỹ thước + luật). Sim chạy mode chi phí OFF (shadow paper không có chi phí vào).
- Bước: (1) lấy ledger lệnh shadow c3b (đọc file/log trên Oracle, chỉ đọc); (2) dựng bundle ticker sim từ Vision cho giai đoạn đó bằng exporter đã dùng cho HO4 (99c5f040 / `ho4p1-jar-exp`) — tìm trong docs; (3) chạy sim Kaggle; (4) so khớp: tỉ lệ lệnh trùng (symbol, phút vào ±1′), chênh giá vào, chênh PnL, lệnh chỉ có ở một bên + lý do.
- Đoạn shadow #2 không đạt chuẩn (10-12 09:06 → 10-15 14:49) loại khỏi so sánh. Chạy thử tuần đầu 10-15 15:00 → 10-22 khi đủ dữ liệu; trước đó dry-run trên 10-11 → 10-12 09:00 để kiểm đường ống.
- Output: `research/shadow/compare_shadow2.py` + báo cáo tuần `docs/result/SHADOW2_WEEK_<n>.md`.

## P4 — xuất tập ỨNG VIÊN của hệ (sửa lỗi phương pháp T9: chân hệ ≠ sự kiện crash)
- Thêm key sim `SIM_EXPORT_CANDIDATES=<path>` (mặc định tắt ⇒ byte-identical, kiểm parity md5 ad26fd55 như ECMEAS). Khi bật: mỗi tick selector ghi mọi ứng viên được đánh giá: ts, symbol, bar_ret, p15/gate r, q_t, qua gate (bool), điểm/thứ hạng S1, top-K (bool), có vào lệnh (bool), lý do loại (full/held/…).
- Branch `feat/sim-export-candidates` từ module, test, parity off; chạy 1 kernel năm **2024** (năm khám phá) ⇒ `chuyendinh/vz-cand-2024`. KHÔNG chạy năm xác nhận.
- Join layer `research/vz/e1/e1_cand.py`: gắn feature E1 (as-of, causal) vào tập ứng viên 2024; smoke + V-a causal. Không tính outcome (để MASTER pre-reg sau).

## P5 — kill-switch live (chuẩn bị, KHÔNG deploy)
- Spec + code sau cờ (mặc định TẮT): theo dõi equity paper/live; ngưỡng bậc DD (cảnh báo / tạm dừng mở lệnh mới / dừng hẳn) và số ngày không lập đỉnh (UW) — tham số đọc từ config, KHÔNG đặt giá trị (owner chốt khẩu vị). Hành vi "tạm dừng" = không mở lệnh mới, vẫn quản lý vị thế đang có; gửi Telegram qua kênh healthcheck hiện có.
- Unit test; parity sim tắt cờ = byte-identical. Commit branch `feat/kill-switch`, không merge, không deploy.
