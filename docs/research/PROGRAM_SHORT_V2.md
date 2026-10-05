# PROGRAM_SHORT_V2 — Xây SHORT như LONG (state-gate → selector → exit → sim 1m → engine), chấm bằng P(squeeze)

Ngày 2026-10-02 · MASTER: Claude (Fable 5.1) · Owner: Uni · Branch `module`.
Thay thế mọi vòng SHORT 0-sim rời rạc trước (13 vòng NULL/NO-GO, xem `docs/audit/AUDIT_SHORT_REVIEW_20261002.md`).

## 0. Giả thuyết owner (ghi nguyên ý, chốt TRƯỚC khi đo)
Alt có chu kỳ tăng ngắn. (i) Alt LỚN ăn theo BTC: dài/ngắn tuỳ BTC. (ii) Phần lớn alt còn lại là "rác": pump/dump mạnh
trong một khoảng khi được chọn làm **guồng thanh khoản** (liquidity rotation); ngoài ra theo regime thị trường thì chỉ tăng ngắn;
**phần lớn thời gian ở trạng thái xả dần ⇒ giảm là chính**. ⇒ Một gate bắt được coin ĐANG thuộc tập "xả dần" (không trong guồng
thanh khoản, không trong regime tăng) là gate đủ tốt cho short.

Phần đã có bằng chứng (không đo lại): alt drift âm h365, excess-kurt +370/+1964/+878 (ALT_REGIME_WAVES); ZigZag 25%: up-leg median
18d < bleed-leg 24d, pump median +54%/leg (SHORT_STATE_DEFS). Phần CHƯA được trả lời đúng cách: gate trạng thái đủ sắc để
kéo **P(squeeze)** xuống mà vẫn giữ bleed hay không — SHORT_STATE test thô (ngày, 4 ngưỡng, 24h, không selector/exit), và
90% drift tập B là beta rổ alt (audit F9).

## 1. Số quyết định (áp dụng mọi pha)
Short thua không vì thiếu bleed mà vì đuôi phải. Mọi pha chấm bằng bộ 4 số trên cùng cửa sổ giữ T:
- `bleed`  = mean/median `retEnd_T` (âm là tốt), theo năm.
- `pSQ10`, `pSQ20` = P(`maxFav_T` ≥ +10% / +20%) (xác suất bị squeeze; 1h closes ⇒ cận DƯỚI, ghi rõ).
- `netproxy_T` = E[−retEnd_T | không SL]·(1−pSQ10) − (0,10+0,002)·pSQ10 − 0,112% + funding THẬT của chính coin trong T (short nhận khi rate>0; cắt tại thời điểm SL nếu SL).
- `cover` = % coin-ngày DEV thuộc trạng thái (gate không có tác dụng nếu cover < 3%).
Ngưỡng kinh tế cố định: cần `netproxy_7d` > +0,5%/lệnh (≈ 4,5× phí) để còn chỗ cho slippage/liquidation chưa mô hình.

## 2. Pha & kill-criterion (mỗi pha có pre-reg riêng, commit TRƯỚC khi đo; fail ⇒ dừng chương trình)
| Pha | Việc | Chấm | KILL nếu |
|---|---|---|---|
| 0A | **State map** per-coin causal: LIQ (guồng thanh khoản), BTCF (alt lớn theo BTC), BLEED (xả dần), FLAT. Định nghĩa cố định §3. Đo 4 số theo trạng thái × T∈{3,7,14}d × năm | bảng trạng thái; thời lượng chu kỳ (kiểm ý "ngắn") | KHÔNG trạng thái nào có cover ≥3% và `netproxy_7d` > +0,5% ở ≥3/4 năm (2022–2025) với CI block-7d (k = số trạng thái×T, inflate √(2 ln k)) ngoài 0 |
| 0B | **Squeeze-predictability của model long**: S1 score / pNoPump / p15 dự báo `maxFav_7d ≥ 10%` toàn universe, AUC + decile theo năm OOS | AUC_year, pSQ10 decile-0 vs toàn bộ | chỉ thông tin; không kill — quyết định dùng làm feature/gate chống squeeze ở Pha 1 |
| 1 | **Selector short** (Kaggle GPU, WFO như G015): label path-aware `y=1[retEnd_T ≤ −thr ∧ maxFav_T ≤ E]` trong tập BLEED (∪ trạng thái qua 0A); feature = 45 long + feature trạng thái (§3) + (0B nếu có ích); T, thr, E chốt 1 bộ từ 0A | rank-IC WFO theo năm; decile-top: bleed & pSQ10 | IC ≤ +0,03 hoặc không dương 4/4 năm; hoặc decile-top pSQ10 không thấp hơn tập BLEED ≥30% tương đối |
| 2 | **Sim 1m first-hit** (Python `short_fullchain_sim.py` mở rộng): gate 0A + top-K selector + exit = {trailing xuống g, SL +s, time-stop T} — ĐÚNG 1 lưới nhỏ pre-reg (≤6 ô), funding exact, phí 0,112% | §9-tương-đương per-trade + equity sổ short (MTM phút) | net ≤ 0 ngoài CI raw & inflate, hoặc < 3/4 năm, hoặc pSQ10 thực > 10% |
| 3 | **Engine Java** sleeve SELL gated OFF theo `PLAN_SHORT_ENGINE_20261002.md`; parity md5 650c386f giữ nguyên khi OFF; sim Kaggle sổ long R4 + short sleeve theo §9 MTM | §9 đầy đủ | §9 T1/T4 FAIL vs B0 |
Owner chỉ quyết sau Pha 2. Không nhảy pha. Không "thử thêm biến thể" sau khi thấy số (amend chỉ TRƯỚC khi đo).

## 3. Định nghĩa trạng thái Pha 0A (cố định; causal; theo coin-ngày d, chỉ dùng dữ liệu ≤ d)
Nguồn: ticker ngày toàn universe (close, quoteVolume), 1h closes (`CLOSES_1H.bin`) cho maxFav, funding store, OI nếu có (phụ), BTC ngày.
- `hi60 = max(close[d-60..d])`, `lo60 = min(close[d-60..d])`; `run_up = hi60/lo60 − 1`; `age_hi = d − argmax` (ngày từ đỉnh 60d); `dd_hi = close/hi60 − 1`.
- `tsh = turnover share` = quoteVol_d / Σ_universe quoteVol_d; `tsh_z = (log tsh_d − mean log tsh[d-90..d-1]) / sd` (z so với CHÍNH NÓ) ; `tsh_rank = rank cross-section của tsh_z`.
- `beta60` = β(ret_coin, ret_BTC) OLS 60 ngày; `tier` = tercile quoteVol trung bình 30d (LỚN/VỪA/NHỎ) cross-section.
- `bull` = BTC close > SMA50 BTC (regime thị trường thô, 1 định nghĩa, không quét).
Trạng thái (ưu tiên theo thứ tự; mỗi coin-ngày đúng 1 trạng thái):
1. **LIQ** (đang trong guồng thanh khoản): `tsh_z ≥ 1,5` HOẶC (`run_up ≥ 0,5` VÀ `age_hi ≤ 10`).
2. **BTCF** (alt lớn theo BTC): `tier = LỚN` VÀ `beta60 ≥ 0,8`.
3. **BLEED** (xả dần): `run_up ≥ 0,3` VÀ `age_hi ∈ [11, 60]` VÀ `dd_hi ≤ −0,15` VÀ `tsh_z ≤ 0` (thanh khoản đã rút).
4. **FLAT**: còn lại.
Biến thể cho phép (k=2, khai TRƯỚC): BLEED′ = BLEED ∧ ¬bull. Không ngưỡng nào khác được đổi sau khi thấy số.
Thời lượng chu kỳ: phân phối độ dài run LIQ và BLEED (ngày), theo tier — để kiểm trực tiếp mệnh đề "chu kỳ tăng ngắn".

## 4. Ràng buộc chung
DEV 2022-01-01..2025-12-31 (2021 chỉ warm-up chỉ báo); 2026 niêm phong. 0 Java trên Oracle; train chỉ Kaggle; 1 job nặng/lúc
(lock `~/claude_master/1002/oracle_heavy.lock`). Không chạm 242. Không sửa `.java` tới Pha 3. Python `logging`. Không push dữ liệu.
Mọi pha: pre-reg commit → đo → RESULT (bảng từng điều kiện PASS/FAIL) → MASTER verify → owner.
