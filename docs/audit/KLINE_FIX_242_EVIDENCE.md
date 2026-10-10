# KLINE_FIX_242 — bằng chứng nguyên nhân (F1), thời điểm đọc (F2), kiểm backfill/buffer/healthcheck (agent KFIX, 2026-10-10)

Chỉ đọc 242 (Aerospike `operate` read + LUT, log). Script: `research/analysis/kfix_probe_rest.py`, `kfix_probe_ws.py`,
`kfix_race_read_vs_flush.py`; dữ liệu thô Oracle `~/claude_master/1010/kfix_probe/` (probe.json, cmp.json, ws.json, race_raw.txt).
Runbook: `docs/runbooks/KLINE_FIX_242.md`.

## F1 — luồng nào ghi giá trị sai
Thí nghiệm sống 2026-10-10 13:32–13:46 +07: 29 symbol (15 top quoteVolume + 14 ngẫu nhiên hạng 16–300, seed 20261010) × 15 phút.
Với mỗi nến M, Oracle gọi REST `klines limit=2` ở +1,2,3,4,5,6,8,10,15,25,40 s sau khi M đóng (giờ server, lệch 0,005 s), sau đó lấy
nến final (REST startTime) và record 242 của M (data + LUT).
| Độ trễ sau đóng nến | 1 s | 2 s | 3 s | 4 s | 5 s | 6 s | 8 s | 10–40 s |
|---|---|---|---|---|---|---|---|---|
| snapshot REST == final (5 trường, float32) | 45,3% | 61,1% | 72,0% | 85,7% | 96,8% | 99,5% | 100% | 100% |
- Snapshot **không đơn điệu** (vd MOVR: +1 s = final, +2 s thiếu, +3 s = final) ⇒ REST phục vụ từ nhiều replica trễ khác nhau.
- 242 (V8.1, LUT ghi chốt +5,19…+6,13 s): khớp final **370/435 = 85,1%**, lệch **65 = 14,9%** (audit cả kỳ 15,7%).
  Trên 65 ô lệch: open đúng 65/65; Q242/Qfinal ≤ 1 ở 65/65 (p50 0,9937, min 0,011); **49/65 trùng bit một snapshot REST probe chụp ở
  +1…+4 s** (27 ở +1 s, 13 ở +2 s, 8 ở +3 s, 1 ở +4 s); 12/16 còn lại có Q nằm giữa 2 snapshot kề nhau (probe lấy mẫu mỗi 1 s,
  242 gọi ở thời điểm khác); 4/16 = replica trễ (snapshot probe cùng lúc đã = final).
- Theo biên độ phút final (H−L)/O: < 0,1% 28/232 = 12,1%; 0,1–0,3% 17/126 = 13,5%; ≥ 0,3% 20/77 = 26,0% (khớp xu hướng audit
  10,6% → 45,7%): phút biến động có nhiều trade ở giây cuối ⇒ ảnh chụp sớm thiếu nhiều hơn.
- Loại trừ: (a) luồng nặn `Rest-Price-Loop` ghi đè sau `remove` — không: nó chỉ ghi `curMin` (phút đang mở), và open của ô lệch luôn
  = open REST (nến nặn có open = giá ticker đầu tiên); (b) lấy sai phần tử limit=2 — không: 65/65 open đúng, không lệch phút;
  (c) race đa luồng ghi M — `writeMinuteBatch` khoá stripe theo key phút, merge theo symbol.
- ⇒ **Nguyên nhân chính xác:** `TickerIngestor2AerospikeNew.java:164` (fetch giây 2–10, thực tế xong ở +5–6 s) + `:235` (`limit=2`,
  đúng phần tử nhưng nến M chưa settle ở replica trả lời) + `:288-293` (ghi "chốt vĩnh viễn" rồi `timeBuffer.remove`, không bao giờ lấy lại).
- Giá vào sim đắt hơn Vision TB +0,049% (AUD26): không đo trực tiếp ở đây. Giải thích nhất quán với dữ liệu: close 242 = giá trước vài
  giây cuối phút (sai số đối xứng quanh close thật), nhưng lệnh được CHỌN theo xếp hạng/feature tính trên chính close đó ⇒ chọn lọc ưu
  tiên ô có sai số dương (winner's curse) ⇒ giá vào trung bình cao hơn close sàn. (Giả thuyết — cần kiểm riêng nếu quan trọng.)

## F1b — race thứ hai: live đọc nến M trước khi ingest chốt
Log 242 08–10/10 (3 693 phút): ingest log "Chốt nến phút M" ở +4,87 (p1) / **+5,59 (p50)** / +7,36 (p99) / +16,69 (max) s; trading
"Start check level change" (đọc `LiveTickerWindow` ngay sau) ở +6,00 / +6,05 / +6,10 / +6,11 s. **461/3 693 = 12,5% phút trading đọc
TRƯỚC khi ingest chốt M** ⇒ đọc bản nặn của M (close = giá ticker cuối, H/L từ mẫu ticker 3 s, Q = phần đầu phút từ lần REST trước)
và cache vĩnh viễn (`LiveTickerWindow` chỉ đọc phút mới). Shadow #1 459/3 693 = 12,4%, shadow #2 381/2 803 = 13,6% (đồng hồ Oracle;
lệch đồng hồ Oracle–242 < 1 s, chưa hiệu chỉnh).

## Websocket
- `wss://fstream.binance.com/stream?streams=…` và `/ws/…`: kết nối OK nhưng **0 message/8 s**; `/market/stream?streams=…`: 33 msg/8 s;
  `/public/stream`: 0. (Đường cũ im lặng không báo lỗi — phù hợp việc ingest websocket cũ chết dần 04-24.)
- WS `/market` 30 symbol × 8 phút: **240/240** sự kiện `x=true` (đủ).
- WS `x=true` so REST final (lấy sau ≥ 1′): **232/232 = 100%** trùng O/H/L/C/Q float32 và số trade (29 symbol ASCII × 8 phút).
  Thời điểm tới (đồng hồ Oracle sau đóng nến): p1 0,05 / p50 0,52 / p99 3,05 / max 3,05 s; event time sàn `E` p50 0,48 s. Mỗi phút có
  ~22% symbol (ít giao dịch) tới ở ~3,04 s; 0 sự kiện sau 3,5 s ⇒ ingest: flush giây 1,5 + ghi ngay bản tới muộn, REST sớm giây 4.
- Kết luận chọn phương án: WS x=true là cách DUY NHẤT có nến đúng trước giây 6 mà không dời tick live; REST muốn đúng phải đợi ≥ 8 s.

## Backfill dry-run (F5) — `research/ops/kline_backfill_242.py`, mẫu 170 symbol của audit (`kdiv_syms.json`)
| Ngày +07 | ô so | ô sẽ đổi | % | audit D1 | close | quoteVol | ulp-only (bỏ) | backup gz |
|---|---|---|---|---|---|---|---|---|
| 2026-05-28 | 222 210 | 55 728 | 25,079% | 25,0794% | 38 309 | 55 728 | 1 | 2,8 MB* |
| 2026-06-04 | 227 865 | 65 071 | 28,557% | 28,5573% | 47 724 | 65 069 | 1 | 3,3 MB* |
| 2026-09-15 | 227 520 | 23 013 | 10,115% | 10,1147% | 14 775 | 23 013 | 0 | 1,1 MB* |
| 2026-10-08 | 220 320 | 30 337 | 13,769% | 13,7695% | 20 442 | 30 337 | 0 | 1,5 MB* |
| 2026-09-15 toàn universe | 1 038 240 | 74 191 | 7,146% | — | 48 123 | 74 190 | 0 | 2,1 MB |
(*) định dạng JSON cũ dài hơn; bản cuối dùng số float32 ngắn nhất (roundtrip bit-exact, self-test). Mọi phút của các ngày trên đều có
≥ 1 ô đổi (1 440/1 440). Khớp audit tới 4 chữ số ⇒ đọc record + giải mã + nguồn Vision đúng.
| 2026-10-10 00:00→14:03 (nguồn REST, Vision chưa có) | 128 520 | 14 577 | 11,342% | T10 11,265% | 9 147 | 14 577 | 0 | 0,4 MB |
- Nhánh REST: 340 call `klines limit=1000` tuần tự, trần 300 weight/phút, 0 lần 429/418. Phát hiện **3 phút 242 không có record**
  ngày 10-10 (lỗ reboot 08:03–08:07): script mặc định không tạo record thiếu (chỉ sửa ô có sẵn) — lỗ kiểu này từ nay được pass settle
  khởi động (limit=30) của ingest mới lấp; lỗ lịch sử cần bổ sung `--fill-missing` cho record vắng (chưa làm).
- Sự cố trong lúc làm (khai thật): bản đầu nhánh REST chạy song song 16 luồng, limit=1500 (weight 10), retry khi 429 ⇒ 48×429 rồi
  **IP Oracle 161.118.212.3 bị Binance ban (418) ~13:56 → 14:11:58**. Shadow trên Oracle không ghi lỗi ban trong log (đọc giá từ
  Aerospike 242); 242 không bị ảnh hưởng (IP khác). Đã sửa: REST tuần tự + trần weight + dừng ngay khi 429/418 (backfill, healthcheck).

## Buffer gate (F6) — kiểm quá khứ
`research/ops/kline_gate_buffer_rebuild.py build` từ feature gate audit (`~/claude_master/1003/kdiv/kdiv_gate_{242,vis}_*.csv.gz`,
04-01→06-30), sp HO26 K24, mốc 2026-06-30 23:00: hai buffer n = 3 109 176 r / 129 549 tick, first 04-01 23:00, arm 04-08 23:00,
armed; q_242 = 0,011087, q_vis = 0,010642; tỉ số q mỗi 6 h (30 ngày cuối) p1 0,950 / p50 0,967 / p99 1,0005; mốc 05-15: 1,000.
Buffer thật đang chạy (đọc bản sao 14:04): live K16 q 0,006511, shadow #1 K16 0,009113, shadow #2 K24 0,009145, cả 3 first 10-01 13:00.

## Healthcheck (F7)
`kline_rest_check_242.py --dry-run` 13:54 (trước sửa): `FAIL cells=100 lech=17 (17.00%)`, `WOULD_SEND`; tg.env parse OK (không in).
