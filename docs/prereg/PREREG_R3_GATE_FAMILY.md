# PREREG_R3_GATE_FAMILY — họ biến thể gate R3 (+ R2 làm mượt p15) — MASTER duyệt 2026-11-10

Trạng thái: **PRE-REG, MASTER chốt §8 ngày 11-10, commit TRƯỚC sàng P1** (nháp đầu sha256 960a4189 viết trước khi thấy S4). Ứng viên v1.3; KHÔNG đổi v1.2/go-live (go-live ưu tiên 1).
Nguồn thiết kế: `~/claude_master/res1109/r3_gate/PHA0.md` (R3), `~/claude_master/res1109/r2_predsmooth/PHA0.md` (R2), MASTER chốt 11-10.
Người viết: agent Opus R3. Code Java (nếu Pha 1): Opus, key mặc định OFF, unit test, OFF byte-identical.

## 0. Khai báo trung thực (viết SAU khi thấy những gì sau — HARKing)
- GATE_SMART p0a (c9d7deb0): bảng PnL/leg theo r/q (26,5/34,4/40,0/29,6/36,6), theo burst, hạng, năm — ĐÃ XEM. Không tiêu chí/tham số nào dưới đây chọn từ bảng này; tầng sâu ×>1 bị loại vì bảng không đơn điệu (S1 FALSE).
- R3 probe (`r3_probe.json`, chỉ đếm): pass dồn cụm (52 % khoảng cách phút pass ≤15′), r/q trung vị 1,15, ACF p15, Jaccard top-0,1 % p15 vs mean5/mean15 = 0,63/0,49.
- R2 proxy timing (`proxy_1109.log`, không PnL): mean15/mean60/mean240 trễ trung vị 9′/34′/92′, Jaccard phút 0,52/0,28/0,11.
- S4 GATE_SMART: kernel `gsm-s4-fwd` (push lại 11-10 03:32Z) — **chưa chấm khi viết nháp này**. G5 phụ thuộc S4 theo luật cố định §2 (không phụ thuộc độ lớn kết quả).
  - CẬP NHẬT sau nháp đầu (sha256 960a4189, viết TRƯỚC khi thấy S4): S4 = FALSE (commit kết quả GATE_SMART_S4) ⇒ G5 TIER-DOWN LOẠI theo luật §2; họ còn tối đa 4 arm (G1–G4).
- Đường đã đóng liên quan: ENTRY_CONFIRM FAIL (trễ vào = mất đoạn bật đầu), R4_CADENCE (selector 15′: Calmar −24 %), GATE_ABLATION H60 NO-GO, QUOTA_DIAG D4, BURST_COOLDOWN, GATE_VZ NO-GO, GKF/K32/N_DEEP (thêm lệnh ⇒ lệnh mới kém + chen chỗ).

## 1. Câu hỏi
Đổi THỐNG KÊ quyết định của gate (làm mượt p15, gộp khung) hoặc TRẠNG THÁI quyết định (latch) hoặc ÁNH XẠ theo mức (tầng dưới size nhỏ) có cải thiện Calmar MTM so với B0 hay không, trong một họ duy nhất kiểm soát đa kiểm định.

## 2. Arm (tham số CỐ ĐỊNH, không quét lưới; đổi bất kỳ ⇒ addendum có hash TRƯỚC khi chạy)
Ký hiệu B0: cell (t, c) = phút t (key `ticker.startTime`, nến 1′ vừa đóng) × coin c trong top-24 theo sp (loại coin đang giữ trước gate); p15(t) market-level;
`fac = max(0,26787, sp/0,15·1,2876)`, gs = 1,55; `r = p/(fac·gs)` float32; q_h = phần tử k = floor(pct·(m−1)) của buffer r trong [h−90d, h), tính đầu giờ, warm-up 7d (`GateRatioBuffer.java:42-82`);
PASS ⇔ `!(p < q·fac·gs)`; skipFull trước gate; pct = `Float.parseFloat("0.999950829")`. Mọi arm giữ nguyên các thành phần không nêu.
Tín hiệu làm mượt `p̃` chỉ dùng trong nhánh PREDICT_SYMBOL_TRADE (tính r, nạp buffer, so ngưỡng). DCA_LEVEL1 (ngưỡng 0,008 phẳng), điều kiện "có pred" của leg, BIG_DOWN: GIỮ p15 điểm.
Cửa sổ causal: tập phút τ ∈ [t−W+1, t] (gồm t, theo thời gian thật, không theo chỉ số); chỉ p15 đã có tại t; thiếu > 20 % phút ⇒ cell KHÔNG có p̃ ⇒ không nạp buffer, không pass (fail-closed, sim = live). Trung bình cộng float64 rồi ép float32 (một quy tắc cho sim/live/offline).

| Arm | Định nghĩa | Tham số | Ghi chú |
|---|---|---|---|
| A0 | B0 = sim hiện tại `n4f-b0-*` | — | đối chứng, không chạy lại |
| G1 MEAN15 | p̃ = mean p15 trên [t−14, t], cần ≥12/15 | W=15 (chân trời nhãn p15) | R2 A1 |
| G2 MEAN60 | như G1, [t−59, t], cần ≥48/60 | W=60 | R2 A2; prior âm (trễ 34′) |
| G3 MTF-OR | 2 khung w∈{1,15}: s₁ = p15(t), s₁₅ = p̃ của G1; mỗi khung 1 buffer riêng (nạp cùng tập cell), q_w riêng; pct_w = float32(1 − 0,5·(1 − pct_f32)) cho CẢ hai khung; PASS ⇔ ∃w: `!(s_w < q_w·fac·gs)` | c = 0,5 cố định (MASTER chốt 11-10, trước khi thấy số); mỗi khung ½ quota ⇒ hợp ∈ [0,5; 1]× B0; KHÔNG hiệu chỉnh theo đếm | pct_w = 0,99997541… (float32) |
| G4 LATCH | t* = phút gần nhất < t có ≥1 PASS theo luật B0 (sự kiện notePass, sau skipFull). Nếu 0 < t − t* ≤ 15′: cell pass nếu `!(p15 < (0,9f·q)·fac·gs)`; ngoài cửa sổ: luật B0. Pass do latch KHÔNG gia hạn t*. Buffer/q y B0 | T = 15′, h = 0,10 | trạng thái t* phải persist (live: file cạnh persist gate; thiếu/hỏng ⇒ latch tắt, fail-closed) |
| G5 TIER-DOWN | tầng 0: luật B0, size ×1; tầng −1: `0,85·q ≤ r < q` (float32, cùng buffer/q) ⇒ pass với size ×0,5 | 0,85; ×0,5 | **ĐÃ LOẠI**: S4 GATE_SMART = FALSE (commit 69d2f168, `docs/result/GATE_SMART_S4.md`) ⇒ không chạy P1/Pha 1, không tính vào Holm |

**Loại trước (lý do):** MEAN240 — proxy trễ 92′, Jaccard phút 0,11, chỉ 10/72 đợt; trùng bài học ENTRY_CONFIRM/R4_CADENCE. MAX15 — cùng giả thuyết "giữ cửa mở sau spike" với G4 (thừa, G4 định nghĩa tường minh hơn). EWMA — proxy nằm giữa MEAN15/MEAN60. MTF-AND — xác nhận khung chậm = trễ vào (ENTRY_CONFIRM FAIL). Size tăng theo độ sâu — S1 FALSE; size là đòn bẩy tuyến tính (ISO_RISK/B15). Ngưỡng theo regime — S2 FALSE, GATE_VZ NO-GO. Quota theo số pass — B0 đã là quota ~143 ô/90d; QUOTA_DIAG D4, BURST_COOLDOWN thua; nếu cần thì chạy GATE_STAB V2 CAP5 (29beac99) riêng.

## 3. Ràng buộc baseline
- A0 = B0 sim hiện tại `n4f-b0-*` (K24 + skipFull + X14, A1, KILLSW_A40, cấu hình y hệt; pred gate 8 seed `pred_s{42,7,13,21,99,123,777,2024}` md5 482f764e/37982fd9/258bc7d9/6b3aff7f/0b5df665/635f1f59/b2231aa8/43abd92a).
- Sim LAI S1 (`selection_mismatch_1109`): bins S1 chỉ có ở tick gate cũ mở; tick khác xếp theo net015 (10–31 % leg PREDICT). **Giả định**: ảnh hưởng mọi arm như nhau. Không chắc chắn — arm đổi phút pass có thể rơi vào tick lai khác tỉ lệ ⇒ BẮT BUỘC báo tỉ lệ leg PREDICT ở tick net015 theo arm; lệch > 5 pp so A0 ⇒ ghi cờ, kết luận arm đó là "có điều kiện".
- **Mọi arm GO chỉ được triển khai sau khi B0 "như live" (R1-A3 S1FULL) được xác nhận**; nếu R1-A3 đổi baseline đáng kể (theo tiêu chí của R1), arm GO phải chạy lại ghép cặp 8 seed trên baseline A3 trước khi vào v1.3.

## 4. Sàng P1 (Oracle, `gate_offline`, CHỈ ĐẾM — cấm mở pnl/profit/equity/MTM)
- Input: 8 `pred_s*` của n4f-b0 (tải từ Kaggle, kiểm md5 §3), held = printDone `n4f-b0-s*` cột (sym, start, end, level). Xấp xỉ đã biết của gate_offline (held, ticker stale, tie sp) giữ nguyên.
- Mỗi arm × seed, DEV 2022-01-01..2025-12-31 (+07): (i) Jaccard tập PHÚT pass (≥1 cell pass) vs A0 cùng seed; (ii) quota = số cell pass (G5: Σ size) và số phút pass, tổng DEV và theo năm, tỉ lệ so A0; (iii) mô tả: trễ đợt (như R2 proxy), phân bố r/q.
- Luật (cố định, MASTER chốt 11-10): (a) Jaccard tập phút pass, median 8 seed ≥ 0,90 ⇒ LOẠI arm (khác B0 quá ít, dưới MDE). (b) **Quota** = tổng số CELL pass DEV 2022–25; tỉ lệ arm/A0, median 8 seed, ngoài [0,75; 1,25] ⇒ **LOẠI arm**: không chạy Pha 1 và KHÔNG được chỉnh tham số để kéo quota về (số phút pass và theo năm chỉ báo cáo). Áp cho mọi arm.
- Arm còn lại sau P1 = m (dùng cho Holm). Ghi `p1_r3.json` + commit TRƯỚC khi push Kaggle.

## 5. Pha 1 (Kaggle sim)
- 8 seed gate ghép cặp với `n4f-b0-*` cùng seed; DEV 2021-07-01→2025-12-31 (chấm 2022–2025), HO 2026-01-01→2026-09-30 (đã dùng nhiều lần ⇒ chỉ yêu cầu cùng dấu).
- Hợp lệ (trước khi chấm): G0 jar mới key OFF byte-identical `n4f-b0-s42` (printDone + log GATE-RATIO); MTM `gvz_mtm.py` import trước, `missing == 0`; số pass sim vs P1 offline báo cáo (lệch > 3 % ghi, không hiệu chỉnh); jar_sec_check (không key, không PrivateConfig thật).
- **Futility sau 4 seed (42/7/21/99 chạy trước):** arm có ≥2/4 seed ΔCalmar ≤ 0 ⇒ DỪNG (không thể đạt ≥7/8). Chỉ xem ΔCalmar của chính arm đó.
- Metric: Calmar MTM, CAGR22, maxDD MTM, UW dài nhất, lệnh/năm, PnL/lệnh, theo năm; crowd-out (ghép leg theo (sym, phút)); tỉ lệ leg tick net015 (§3).
- **Tiêu chí GO (tất cả):**
  1. Mean ΔCalmar MTM DEV ghép cặp > 0, t ghép cặp một phía, Holm trên m arm còn sau P1 (α = 0,05).
  2. ≥ 7/8 seed ΔCalmar > 0.
  3. Mean ΔmaxDD MTM DEV ≥ −2 pp (không sâu hơn 2 pp).
  4. ≥ 3/4 năm DEV (2022–2025) có mean ΔPnL ghép cặp > 0.
  5. HO 2026: mean ΔROI cùng dấu với ΔCalmar DEV.
- Phụ (chỉ báo cáo, KHÔNG làm cổng): DSR Sharpe ngày MTM với N_trials = số biến thể gate đã sim trong ledger (đếm khi commit; ước ≥ 25); CI bootstrap khối 30d; crowd-out.
- Nhiều GO ⇒ chọn ΔCalmar lớn nhất; không thêm arm/không đổi tham số sau khi thấy số.
- MDE (suy đoán): sd Δ ghép cặp CAGR22 ≈ 2,4 pp (GQSF) ⇒ ~3,8 pp với Holm m=4; sd Δ Calmar ghép cặp chưa đo (suy đoán 0,1–0,2 ⇒ MDE ≈ 0,2–0,35). Prior: ĐÓNG là khả năng cao.

## 6. Hiện thực
- Key sim mới (mặc định OFF): `SIM_GATE_P15_SMOOTH=mean:W:minCov` (G1/G2), `SIM_GATE_MTF=1,15` + `SIM_GATE_MTF_C=0.5` (G3), `SIM_GATE_LATCH=15:0.9` (G4), `SIM_GATE_TIER=0.85:0.5` (G5, cần hệ số size theo leg). Áp ở `AIRejectFilter.entryGate` nhánh `sp != null`; `GateRatioBuffer` không đổi thuật toán (G3 dùng 2 instance).
- Test bắt buộc: OFF byte-identical; lookahead (đổi p15 tại t+1 không đổi p̃(t), không đổi pass tại t); quy tắc ≥80 %; latch không tự gia hạn; pct_w float32.

## 7. Compute (ước) — thứ tự Kaggle: S4 → R1-A3 → arm R3; go-live ưu tiên 1
- P1 Oracle: tải pred 8 seed ~350 MB + printDone; gate_offline RSS ~3,2 GB, ~30 s/arm/seed ⇒ ~30 min, qua `flock oracle_heavy.lock` (không lồng). Đĩa < 1 GB.
- Code + test + jar: 1–2 phiên Opus; build Oracle `LIVE_IS_SHADOW_HOST=true mvn -o`.
- Kaggle: 1 kernel DEV+HO ≈ 1,1 h (n4f-b0-s7 3 220 s). 4 arm × 8 seed = 32 kernel ≈ 35 kernel-h ⇒ ~18 h wall (2 kernel); G5 +8 ≈ +4,5 h; G0 +1; MTM ~3 h. Futility có thể cắt ~40 %. Tối đa 2 kernel song song, kiểm trước mỗi lần đẩy.

## 8. Quyết định MASTER 11-10 (chốt trước khi thấy số P1)
1. G3: c = 0,5 cố định.
2. G4 giữ pct gốc; luật quota ±25 % ⇒ LOẠI áp cho mọi arm (§4), không chỉnh tham số.
3. G1/G2 hiện thực bằng key Java (DCA_LEVEL1 giữ p15 điểm), không thay `pred.bin`.
4. G5 loại (S4 FALSE, 69d2f168). Họ tối đa 4 arm (G1–G4) trước P1.

## 9. Rủi ro
Thiếu sức thống kê; overfit (mỗi arm 1 bộ tham số, Holm, HO, DSR); lệch live/sim (pct_w float32; cửa sổ p15 cần p15 mỗi phút — live restart/hở phút phải rehydrate W phút từ file `storage/data/prediction` hoặc ai_pred_1m (chỉ đọc); latch persist); buffer/seed gate phải dựng lại cho arm thắng (seed gst1030, buffer live); parity dry (3c7dae05 + ADD) phải thêm cột p̃/q_w/t*; mọi thay đổi = reset cửa sổ parity; sim lai S1 (§3).
