# PREREG_INGEST_QUICKFIX — tiêu chí 72h cho bản vá nhanh collectData (giai đoạn 2a)

Chốt 2026-10-30, TRƯỚC khi viết code. Nhánh `fix/ingest-quickfix` rẽ từ **0a57ea3f** (= mã của jar collectData đang chạy trên 242,
md5 `cb02d85e4f045c6cbdc8d94c18e188f1`, trùng bit với `~/claude_master/1012/gp_wt/target/binance-java-sdk-1.2.4.jar` build 10-12 22:02:27,
worktree sạch). Thiết kế đầy đủ: `docs/plan/INGESTOR_HYBRID.md` (2b). Ngưỡng dưới đây KHÔNG sửa sau khi thấy số; đổi = addendum.

## Phạm vi vá (chỉ 3 việc)
1. Watchdog lệch giá: KHÔNG restart JVM; WARN + Telegram (≤1 tin/30′) + metric. Restart lịch 12h thành cờ `INGEST_SCHEDULED_RESTART_HOURS` (jar mặc định 12 = như cũ; script deploy đặt 0).
2. Bỏ pass settle REST mọi symbol: WS `x=true` là nguồn chính; REST chỉ cho symbol thiếu final lúc +`KLINE_EARLY_REST_SEC` (4 s), kiểm lại các ô REST/thiếu ở +30 s, cộng đối soát mẫu 25 symbol/phút xoay vòng (lệch ⇒ ghi đè + đếm). Bỏ luật "WS suy giảm >50 % ở giây 2 ⇒ REST mọi symbol".
3. Mọi REST tới `fapi.binance.com` của JVM collectData đi qua ngân sách cứng ≤300 weight/60 s (tự đếm, cửa sổ trượt), đọc header `X-MBX-USED-WEIGHT-1M`; 429/418 ⇒ cooldown ngay theo `Retry-After`.
Không đụng: `changeInitialLeverage`, schema ghi, mapper, logic OI/funding (chỉ đi qua ngân sách).

## Đối chứng (7 ngày trước deploy, đo từ log 242)
- Restart JVM: 10-24→10-30 ≈ 21 lần do lệch giá (10-30: 15) + ~2/ngày lịch 12h. 1 lần -1003 (10-30 03:47:59).
- REST klines/phút: 752 nền (`rest_klines_calls_last_min=752`), 1 100–1 500 khi restart. Ước tổng collectData ~950 weight/phút.

## Tiêu chí ĐẠT trong 72h sau deploy (tất cả)
| # | Chỉ số | Nguồn đo | Ngưỡng |
|---|---|---|---|
| Q1 | Restart JVM collectData (dòng `Restart:`/PID đổi) | log 242, `run/*.pid` | **0** |
| Q2 | Độ phủ nến 1m: mỗi phút record `kline_1m_opt` có đủ mọi symbol đang subscribe (đo ở ≥+3′) | `ing_qf_check.py` (Oracle, chỉ đọc 242) quét 100 % phút | **100 %** phút đủ (thiếu = symbol có ở phút trước và sau nhưng vắng) |
| Q3 | Sai so REST final: 30 symbol × 60 phút mỗi giờ (≈130k ô/72h) | `ing_qf_check.py`, ≤40 weight/giờ từ Oracle | **0 ô** (float32 ≤1 ulp) |
| Q4 | Weight REST tự đếm của collectData | dòng `[REST-BUDGET]` mỗi phút | max ≤ **300**; trung bình ≤ **200** (kỳ vọng 100–170) |
| Q5 | Header `X-MBX-USED-WEIGHT-1M` (cả IP 242, gồm LEGACY) | `[REST-BUDGET] hdr_max` | p99 phút ≤ **800** (kỳ vọng ≤ 400; đối chứng ~1 300) |
| Q6 | HTTP 429 / 418 / body -1003 | `[REST-BUDGET]`, log | **0** |
| Q7 | `price_realtime` đứng: khoảng giữa 2 lần ghi giá liên tiếp | `[REST-BUDGET] price_gap_max_ms` | ≤ 5 000 ms ở ≥ 99,9 % phút; không phút nào > 15 000 ms |
| Q8 | Đối soát mẫu: ô WS-final bị REST sửa | `[KLINE-INGEST] recon_diff_ws` | **0** (ô REST-sớm được sửa thì đếm, không gate) |
| Q9 | LEGACY sống | v_t_m PID không đổi; `positionRisk` mỗi phút; không lớp ERROR mới | đạt |

Kết luận: ĐẠT tất cả ⇒ giữ; vi phạm Q1, Q3, Q6, Q9 ⇒ TRƯỢT (rollback, sửa, đo lại 72h mới); thiếu số đo ⇒ XÁM (kéo dài 72h).

## Điều kiện ROLLBACK ngay (script `rollback_ingest_qf.sh <TS>`, 1 lệnh)
Bất kỳ: JVM collectData restart/chết ngoài kế hoạch; phút thiếu symbol không tự lành sau 3′; 418/429/-1003; `price_gap_max_ms` > 15 000;
header > 1 800 ở bất kỳ phút nào; v_t_m log lỗi đọc `kline_1m_opt`/`price_realtime` mới phát sinh; `[OI-GUARD-2]` kích hoạt; RSS collectData > 4,5 GB.
Rollback = khôi phục jar + env backup rồi restart collectData (như mọi `fix_*.sh`).

## Rủi ro đã biết
- Bỏ restart 12h ⇒ lần đầu collectData chạy >12h: Binance ngắt WS ở mốc 24h, `KlineWsClient` tự mở lại (backoff 5 s); phút đó symbol thiếu được REST +4 s lấp (trong ngân sách). RSS theo dõi Q-rollback.
- WS chết toàn bộ: lấp ≤ ~250 symbol/phút do trần 300 ⇒ phủ ở +6 s giảm trong lúc WS chết, phủ ở +3′ vẫn đủ (Q2 đo ở +3′).
- Ô REST-sớm của process cũ chưa kịp kiểm lại khi đổi jar: chỉ áp cho symbol thiếu WS (hiếm); pass khởi động kiểm phút thiếu 30′ gần nhất.
