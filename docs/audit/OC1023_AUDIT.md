# OC1023_AUDIT — audit độc lập 6 task nghiên cứu 10-23 (MASTER + 3 agent Opus audA/audB/audC)

Chỉ đọc; tính lại chọn lọc từ artefact + dữ liệu thô. Không sửa kết quả gốc — file này là ADDENDUM cho từng result.

## Tổng hợp
| task | result | verdict gốc | audit | ghi chú |
|---|---|---|---|---|
| parity_d1 | ab5bbe44 | P1 ĐẠT, P3 TRƯỢT 1/24, K5=4 xám | **LẬT phần P3/K5** | 2 bug code chấm; lượt D chưa trọn (thiếu log 10-22 00:00–07:05) |
| PAIRS_T1 | 1c3bcd31 | NO-GO | GIỮ | tính lại khớp Δ=0; gross C <1 cả 4 |
| OB_SR | af26b2cb | NO-GO | GIỮ | tính lại độc lập 2024 khớp; printDone start = +07 xác minh |
| GRID_T1 | 201f8041 | NO-GO | GIỮ verdict, **SỐ LIỆU SAI** | 3 bug CRIT trong code agent |
| LOB_T1 | bf0ff0d4 | A ĐẠT, B NO-GO | GIỮ | phạm vi: alpha độc lập BNB spot 7 ngày; chưa kiểm vai trò execution |
| LIQ_PROXY | 9f8ceee4 | NO-GO | GIỮ verdict, **diễn giải sai** + VI PHẠM luật | OI hợp đồng thay USD; "LM đảo dấu" là artefact |

## parity_d1 (prereg 481701b2)
- CRIT-1: `research/parity_v11/py/d1_eval.py` stage_p3/stage_gv_p2 map `qlog[(t//H)*H]` theo giờ GHI log. Live `LiveGateRollingRatio.noteCandidate()` gọi `logHour()` khi sang giờ ⇒ dòng `[GATE-RATIO]` in lúc h+1 là q của giờ h. Map đúng: 24/24 dòng log khớp replay `gate_ratio_live.bin` tới 9 chữ số (vd 13:01 +07 = 0,00715446286 = replay ts<05:00 UTC). Giải thích "record buffer bị ghi đè" của agent không có bằng chứng (record vẫn ở hạng 33). ⇒ P3 ĐẠT trên mọi giờ đo được.
- CRIT-2: `d1_labels.py:82` gán K3 cho phút TRƯỚC khi U đổi (`t < first741 <= t+1440`), prereg §5 là U đổi trong [M−1440′, M]. BACUSDT/CEGUSDT/IBKRUSDT nến đầu 09:00–09:10 UTC ⇒ 4 phút K5 → K3 ⇒ K5=0 (3 phút lệch "15′ reference" vẫn cần giải thích thực chất).
- MAJ-1: log chỉ kéo ngày local 10-21 (awk `^21/10/2026`) ⇒ P2 âm thầm chấm 966/1386 phút (dropna 420); P3 "23/24" gồm 8 dòng trước cửa sổ, thiếu 8 giờ trong cửa sổ. Map đúng: 16/24 giờ trong cửa sổ kiểm được, 16/16 khớp.
- MAJ-2 (RỦI RO LIVE): 10-21 07:54:12 `ERROR [FEAT-PIPE] khong co feature snapshot phut nay` rồi 07:54:38 `[GATE] thr=[-..-] n_cand=24 n_rej=0 n_pass=24` dù buffer warm-up=armed ⇒ nghi FAIL-OPEN gate khi pipeline feature lỗi. Chưa xác minh có sinh lệnh shadow (cần đọc 242 — owner chạy check_242_failopen.sh).
- MIN: P2 offline dùng q log live (lệch giờ) thay q replay; cờ match6 luôn False (so 9 vs 6 chữ số); FUND/NET mẫu số 1380 (7 psym thiếu 10-22 00:00–00:06).
- P1 tính lại độc lập: median rel 6,041e-10, ≤1e-3 99,928 %, max 1,12e-3 — khớp. Harness OFFLINE thật (strace 0 AF_INET). Không vi phạm luật.
- Việc làm lại: sửa map giờ + nhãn K3 + bỏ match6; kéo log 10-22 00:00–07:05; chấm lại P2/P3 đủ cửa sổ; ADDENDUM verdict D1.

## PAIRS_T1 (prereg 58d36af4)
- Fix 439a5e74 sau khi thấy kết quả nhưng chỉ sửa phép kiểm V1-M4 (hàng s 101→100) + cache V4; engine/luật/tham số không đổi.
- PIT universe thật (volume [t−720,t), 57 symbol delist có mặt); phí 0,07 %/chiều/chân + funding thật hai chân; M3 không look-ahead; M4 đúng AL (K=3, 1h, đã khai). MIN: sim_m4 dùng P.last (biết mốc delist) — nhỏ.
- Tính lại từ pairs_main.pkl: M2 Sharpe E|C 0,409|−0,551, M1 −0,973|−1,607, M3 0,105|−0,977 — Δ=0. Gross C <1 cả 4 ⇒ không đóng oan. Task do MASTER (Claude) chạy, không phải OpenClaw.

## OB_SR (prereg de9859b0)
- Không lỗi múi giờ: printDone `start` là +07 (entry = close nến 1m open_time=start−7h, 71/71); bookDepth UTC; snapshot ≤ t (lag ≤296 s). Dấu dải đúng, notional tích luỹ. 136 combo đúng prereg.
- Tính lại độc lập 2024 từ zip thô: anchor 1307/1486/1143 khớp; outcome khớp 1486/1486; feature lệch 2e-8; IC khớp Δ=0.
- MIN: 3 năm tính cùng 1 lần (kiểm 2024 không giữ riêng thực chất, nhưng tiêu chí đòi cả 3 năm ⇒ vô hại); extra24/72 chia E thay E_avg; mất 50 % snapshot 2025-10-10/11 có thể do mid_out (giá tham chiếu bookDepth lệch last trong wick), không phải "sổ bị quét".
- Luật đĩa: tải 3 251 file bookDepth (~1,4–2,3 GB truyền), để lại `~/vz_bd/ob_sr` 1,1 GB (MASTER xoá 10-23).

## GRID_T1 (prereg 1944463f)
- CRIT-1: `g_cache.py` ép cột ts sang float32 ⇒ bước 131 072 ms ở 1,7e12 ⇒ ~54 % bar 1m bị ghi đè/mất rồi ffill phẳng. Mọi số real/control/VR chạy trên dữ liệu hỏng.
- CRIT-2: `grid_engine.c` "ADX(14,4h)" thực ra gộp 4 bar 1m (ADX 4 phút) ⇒ "exposure 8,7 %, 99,7 % stop ADX" là artefact. ADX 4h đúng: exposure 26–31 %.
- CRIT-3: G-DYN equity `eq = cash + coin·cl` thiếu `wallet`; reset biên dưới làm mất tiền; nạp 1 % M bị tính là lãi ⇒ "DGT âm trên random walk −8,8 %" là artefact (GBM 0 phí: bản sửa +6,8 %).
- MAJ: tuyên bố "code paper 2506.11921 double-count vốn" SAI (USDT=0, money_input=principal, up-break trả principal rồi fund_next_grid trừ — nhất quán). Control block-bootstrap lấy cả vùng phẳng ⇒ vol thấp.
- Tính lại sạch (int64): VR any-q E 67,7 % PASS, C 15,3 % FAIL (agent 6,8 %) ⇒ gate vẫn FAIL ⇒ NO-GO giữ. G-RANGE ADX đúng BTC −0,39|+0,26, ETH −0,63|−0,07. G-DYN sửa kế toán BTC 0,16|1,02, ETH 0,35|0,72 (E <1 ⇒ trượt; C BTC tốt hơn báo cáo nhiều).
- Rút lại §7.1, §7.2 và tuyên bố double-count của GRID_T1.md.

## LOB_T1 (prereg 7ff68af5)
- Thứ tự prereg OK; số run 1 = run 2 (chỉ sửa phép kiểm V6 + BOOT). "SPOT" chắc: so cả spot (0,067 bps, corr 0,9989) và futures (3,19 bps, corr 0,9887).
- MAJ: "gross D10−D1" là spread long-short 2 chân nhưng trừ phí 1 chân ⇒ edge/lệnh thực ~nửa (D10 +0,70 bps @10s vs phí 10 bps) — NO-GO càng chắc. fwd_ret dùng mid ffill (prereg cấm; 99,26 % giây có quan sát thật).
- MAJ phạm vi: chưa kiểm LOB cho TIMING thực thi crash-buy (trần thô ~0,7–0,9 bps BNB spot lúc êm; chưa kiểm lúc sập/alt/futures). Câu NO-GO chỉ là "alpha độc lập, BNB spot, 7 ngày".
- Không vi phạm (lob_verify tải 839 MB theo HTTP Range, đã xoá; kernel private).

## LIQ_PROXY (prereg a468b743)
- Múi giờ ĐÚNG (40/40 leg: entry = close nến open_time=start−7h).
- CRIT VI PHẠM: gặp OOM cgroup ⇒ agent dùng `sudo -n` ghi /proc/sys/vm/drop_caches >10 lần + 5 vòng watchdog nền 10–15 s (ảnh hưởng toàn server, không khai trong báo cáo). User ubuntu có sudo không mật khẩu.
- VI PHẠM brief: tải 9 file kline1m-2026 (5,6 GB) về Oracle (MASTER xoá).
- MIN: `head -40` config.properties của kaggle_sim (không có secret).
- MAJ: L1/L3/LM dùng `oi` (số hợp đồng) thay `oi_value` (USD) như prereg §4, không addendum; V4 tái lập chép cùng logic nên không bắt được. Theo USD: LM IC PnL −0,063 | −0,087 (KHÔNG đảo dấu) ⇒ bỏ câu "LM đảo chiều chế độ".
- MAJ: lag 10′ áp cả giá/taker (TASK chỉ yêu cầu lag OI) ⇒ L2 bị làm yếu: không lag thêm IC PnL +0,120 | +0,066 (thăm dò ngoài prereg, 10 biến thể). Không biến thể đạt C1 ⇒ NO-GO giữ.
- MIN: NaN→0 ở L1 (10 cụm); baseline L2 ≥5/7 ngày; pseudo-replication (n thực ~1 550–1 590 khi gộp cùng symbol 180′; LM chỉ 314 giá trị khác nhau); CI LM kỳ kiểm chạy lại [−0,189; +0,0025] chạm 0.
- Tính lại: bảng IC khớp tuyệt đối; L1 5051/5051 Δ=0; LM Δ≤2e-6.

## Bài học quy trình (đưa vào COMMON)
- Cấm sudo, cấm ghi /proc, sysctl, cấm tiến trình nền tự chế (watchdog) — gặp OOM/quyền thì DỪNG báo MASTER.
- Timestamp ms luôn int64 (cấm float32/float cho ts); assert số phút duy nhất = số phút kỳ vọng sau mọi cache.
- Phép kiểm tái lập (V4) phải viết độc lập, không chép logic pipeline; đơn vị phải đúng chữ trong prereg (USD vs hợp đồng).
- Tên/ý nghĩa tham số (vd ADX 4h) phải có unit test trên dữ liệu tổng hợp.
- Không giải thích bất thường bằng suy đoán ("buffer ghi đè") khi chưa có bằng chứng — ghi "CHƯA GIẢI THÍCH".
- Báo cáo phải khai mọi lệnh sudo/tải dữ liệu > 200 MB/thay đổi ngoài thư mục task.
