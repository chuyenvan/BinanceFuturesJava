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


## ADDENDUM 1 (2026-10-31, vòng QF2 — viết TRƯỚC code QF2; lý do: A1_QF_REPORT FAIL 1 CRIT/3 MAJ/7 MIN, md5 e93febb6)
Thay thế các dòng tương ứng ở trên; dòng không nhắc tới giữ nguyên. Jar e75c4a65 KHÔNG deploy.

**Thiết kế ngân sách (đổi):** weight IP tự đếm (cửa sổ trượt 60 s, trần 300) chia lane: PRICE (`ticker/price`) dùng tới 300 —
dành riêng 60 weight mà KLINE/LOW không được chạm; KLINE (`klines` limit<100: REST sớm, kiểm lại, đối soát) tới 240, KHÔNG chờ
(hết chỗ ⇒ để phút sau, không xếp hàng chặn); LOW (premiumIndex, exchangeInfo, klines limit≥100 = repair/roller, watchdog 24hr cũ) tới 160.
`/futures/data/*` (OI/LS/taker) KHÔNG vào weight IP: bucket riêng ≤150 request/60 s (hạn mức sàn 1 000/5′).

**Chứng minh vòng OI:** 752 symbol × 5 endpoint = 3 760 request/vòng. Ở trần 150/phút ⇒ ≥25,1′; throttle 250 ms + độ trễ HTTP
quan sát ~100–200 ms ⇒ tốc độ tự nhiên 130–170/phút ⇒ vòng 25–29′. Mỗi symbol được gọi mỗi ~30′ (cùng thứ tự); limit=8 × 5′ phủ 40′
⇒ biên ≥10′ (≥2 điểm 5m). Nếu vòng >30′ thì vòng sau bắt đầu ngay ⇒ khoảng cách = thời lượng vòng; ngưỡng an toàn ≤35′ (biên 5′).
Tiêu chí mới **O1**: thời lượng vòng OI (log `sweep_ms`) ≤ 35′ ở 100 % vòng; ≥1 vòng/30′.

**Q2 (đổi, đo được thật):** mỗi phút M, sau pass +30 s, dòng `[KLINE-COVER] phut=M chua_chot=K` đếm symbol mà ô M chưa là
WS-final và chưa được REST kiểm lại; cùng dòng báo `chua_chot_truoc=K'` cho phút M−2 (≥+90 s). ĐẠT: K' = 0 ở 100 % phút
(trừ phút trong cửa sổ khởi động 5′); K>0 được phép nhưng phải về 0 trước +3′. Thêm: mọi phút có record `kline_1m_opt`.
**Q3 (đổi nguồn):** so 242 với **Vision daily** (data.binance.vision) cho 30 symbol × 1 440 phút mỗi ngày UTC đủ (không gọi REST
fapi từ Oracle). 0 ô lệch.
**Q4 (tính lại có OI):** weight IP tự đếm (KHÔNG gồm futures/data): TB ≤ 150, max ≤ 300; kỳ vọng TB 80–130
(giá 40, premiumIndex 20, watchdog 2, đối soát 25, REST sớm/kiểm lại ~0–40). futures/data: max ≤ 150 req/60 s.
**Q5:** header `X-MBX-USED-WEIGHT-1M` theo phút GIỜ SÀN (header `Date`): p99 ≤ 800.
**Q7 (đổi):** tuổi giá theo nhịp ghi: `price_gap_max_ms` ≤ 5 000 ở ≥ 99,9 % phút sau khi repair khởi động xong; không phút nào > 15 000.
**Tự cứu (mới, cố định):** watchdog tuổi giá trong JVM kiểm mỗi 5 s: tuổi > **X = 15 s** ⇒ WARN + Telegram (≤1/10′);
tuổi > **Y = 90 s liên tục** ⇒ restart JVM có kiểm soát (giây 08–20), tối đa **1 lần/giờ** (mốc lưu file run/), ân hạn 180 s sau khởi động.
Supervisor: các loop chính chết vì Throwable ⇒ dựng lại (backoff 1→30 s), đếm `loop_restarts`.
**Q1 (làm rõ):** 0 restart JVM do lệch giá/lịch; restart do watchdog tuổi giá = vi phạm Q1 (TRƯỢT) nhưng là hành vi an toàn đúng.
**Q10 (mới):** `loop_restarts` ≤ 3/72h; WS: mỗi kết nối xoay chủ động ở mốc lệch nhau (20h + i×25′), phát hiện im lặng ≤ 15 s.

**Bộ nhớ:** collectData chạy `-Xmx2g` tường minh (JAVA_TOOL_OPTIONS; bằng trần ergonomic hiện tại, RSS 2,2 GB). Rollback khi:
RSS > **3,2 GB**, hoặc có `OutOfMemoryError` trong log, hoặc MemAvailable 242 < **600 MB** (242 RAM 7,8 GB, avail ~2,1 GB).

**Kiểm sau deploy (đổi, MAJ-3):** bỏ so `Total ≥ PRE_TOTAL`. Chờ dòng `repair khoi dong xong` rồi kiểm: 2 dòng `[KLINE-COVER]`
liên tiếp có `chua_chot_truoc=0`; `price_gap_max_ms` ≤ 5 000 trên các dòng sau repair; 0 dòng 418/429/ban; LEGACY PID + log tươi;
PAUSE watchdog đã gỡ.

**ADD-1b (2026-10-31, cùng vòng, TRƯỚC code — tính lại số học, chưa có số đo nào):** KLINE tối đa 240 weight/60 s ⇒ lỗ lớn
(WS chết, N symbol thiếu) cần ≥ N/240 phút để kiểm lại. (a) REST sớm +4 s chỉ chạy khi số symbol thiếu ≤ `KLINE_EARLY_REST_MAX`
(=60); lớn hơn ⇒ chỉ đánh dấu, để pass +30 s (nến đã settle, mỗi call limit đủ phủ mọi phút thiếu của symbol đó, weight 1) xử lý —
tránh tốn 2 call/symbol (REST sớm chưa settle rồi kiểm lại). Live đọc lại 3 phút gần nhất mỗi tick (KFIX-B) nên nhận bản sửa.
(b) Q2 thay câu "phải về 0 trước +3′": lỗ ≤ 200 symbol ⇒ `chua_chot` về 0 trước +3′; lỗ N > 200 ⇒ trước +(⌈N/200⌉ + 1)′
(N = 752 ⇒ ≤ 5′). Phút bình thường: `chua_chot_truoc` (+90 s) = 0. Ô bị bỏ kiểm sau 30 pass lỗi (`bo_kiem`) tính là TRƯỢT Q2.

**ADD-1c (2026-10-31, cùng vòng, TRƯỚC khi chạy bất kỳ test/số đo QF2 nào):** khi viết kịch bản test phát hiện hạn mức LỒNG NHAU ở ADD1
(KLINE ≤240 tính cả weight của LOW/PRICE) cho phép LOW đầy (repair khởi động) bỏ đói KLINE (còn ~40/phút ⇒ lỗ 752 mất ~19′).
Đổi sang hạn mức RIÊNG, tổng = 300: **PRICE 60** (giá ~40/phút + watchdog 2), **KLINE 200** (không chờ), **LOW 40** (premiumIndex 20,
roller, exchangeInfo, repair). Pass kiểm lại xếp **ô cũ nhất trước**. Ngưỡng Q2/ADD-1b (⌈N/200⌉+1 phút) khớp KLINE 200. Mọi tiêu chí khác giữ.
