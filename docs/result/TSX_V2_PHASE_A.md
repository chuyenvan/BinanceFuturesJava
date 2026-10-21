# TSX_V2 Phase A — replay engine + trần trên (oracle) + hồ sơ hồi phục (2026-10-22)

CHỈ MÔ TẢ + dựng công cụ; chưa chọn/không chạy biến thể nào. DEV 2021-07→2025-12, 8 seed. Không dùng HO 2026, không 2020, không 242, không REST.
Script `research/tsx_v2/` (prep, engine, common, validate, phase_a, md_a); dữ liệu ra `docs/result/tsx_v2/phaseA/` (`validate.json`, `phaseA.json`, `phaseA_clusters.csv`). Cache (không commit): `~/claude_master/tsx_v2/cache/` (cửa sổ giá 998 × 50 401 phút float32).

## A1. Replay engine
- Đơn vị = cụm (sym, giờ đóng) chạm mốc 168h (tuổi ≥ 168h+1'): X14 4 323 cụm, P0 (`gqsf-*`) 4 324 cụm. Leg/giá vốn/qty lấy từ printDone; mô phỏng từng phút từ leg đầu, chép `startUpdateOldOrderTrading` @a8690d46 :1000-1110 + `OrderTargetInfoTest` (updateStatusNew/updateTPSL/trailRate/accrueFundingMark) + `TradeUtils.trailFromCap` + `Utils.calPriceTarget`/`normalizePrice`: thứ tự trong tick = cập nhật giá+funding → time-stop (chỉ khi chưa arm; hoãn nếu ngày UTC ∈ cờ ∧ tuổi ≤ trần) → arm (high ≥ E·1,07 và (high−E)/E > 0,07, float32) → trailing (SL = floor_tick(E·(1+round((r−min(r,0,03))/0,005)·0,005)), ratchet, khớp khi minPrice ≤ SL tick sau, giá min(SL, open)). Cắt time-stop tại min(open, close). Leg DCA gộp SAU update cùng tick (entry TB float32). Funding mark: Σ rate × qty cụm × close tick đầu tiên ≥ mốc settle. PnL = Σ q(tp−e) − 0,001116·q·e − funding.
- Giá: Vision 1m (`vz_e1/raw`, `gvz/k2021`); funding: Vision fundingRate tháng (`~/vz/out/funding`); tick size: `exchange_info_pin.json` (md5 5a815948, cùng file kernel Kaggle).
- Giới hạn có chủ đích: leg DCA chỉ biết tới thời điểm thoát của run nguồn (X14). Biến thể thoát SỚM hơn ⇒ bỏ leg sau đó (đúng); biến thể giữ LÂU hơn ⇒ trạng thái đóng băng (không DCA mới) — chỉ xảy ra ở A2(b)/H504 và B4. X14 DEV: 0 leg DCA sau khi arm; DCA sau 168h hiếm (~2 cụm/seed).

### Validate (PASS)
| Kiểm | Kết quả |
|---|---|
| Cờ base tính lại từ `edge_attr/index.npz` | 214 ngày, chuỗi khoảng + sha = `flags.json` (c79ef302) |
| X14, **cụm hoãn** (luật X14) — status / phút thoát / PnL (≤1e-3·max(\|PnL\|,1)) | **1 364/1 364 = 100 %** (sai PnL p99 1,3e-4 USD) |
| P0, cụm bị cắt 168h (luật P0) | **4 299/4 299 = 100 %** |
| X14 toàn bộ 4 323 cụm chạm mốc | status 100 %, PnL 100 %, phút thoát 99,86 % (6 cụm = STRAX 2024-03-22 ở 6 seed: sim thiếu 2 nến, thoát 168h+3' thay 168h+1', PnL vẫn khớp 5e-6) |
| P0 toàn bộ 4 324 cụm | như trên (cùng 6 cụm STRAX) |
| Số cụm hoãn / cắt-sau-hoãn mỗi seed vs Java `[TSX]` (parity.json) | 8/8 khớp tuyệt đối (174/149, 172/153, 165/143, 173/155, 179/153, 174/153, 162/132, 165/145) |
| Tập cụm hoãn vs `deferred_clusters.csv` (DEEP) | 1 364 = 1 364, giao 1 364 |
Hai quy ước được XÁC ĐỊNH bằng validate (không phải tune): (i) `normalizePrice` theo tick size bật (tắt ⇒ cụm hoãn chỉ khớp 96,5 %); (ii) sim KHÔNG có dữ liệu funding cho LIT (mọi cụm LIT trong 16 run funding = 0) ⇒ replay đặt funding LIT = 0 (luật tự động: sym có funding = 0 ở mọi cụm > 168h). Trước khi áp (ii): cụm hoãn khớp 98,4 % (22 cụm LIT lệch funding), P0 99,4 %.

## A2. Trần trên (oracle — KHÔNG thực thi được, chỉ đo chỗ trống)
Định nghĩa cố định trước khi tính: H504 = hoãn MỌI ngày tới 504h (arm/trailing như sim); oracle = max(PnL nếu cắt tại tick bất kỳ trong [mốc 168h, min(thoát H504, 504h+1')], PnL thoát H504). "cut" = cắt ở 168h (luật P0 trên leg X14). ΔPnL direct, cộng theo cụm, chia 8 seed (bỏ qua lãi kép/slot).

(a) Cụm X14 hoãn (170,5/seed):
| | Δ/seed |
|---|---|
| X14 thực (so cut 168h) — "direct" | **+6 559** |
| Oracle so cut 168h | +22 210 |
| **Oracle so X14 (chỗ trống còn lại)** | **+15 650** |
| H504 (giữ tới 504h bất kể cờ) so X14 | +4 479 |

Theo năm mốc (X14 direct / oracle−X14): 2021 +327/+1 352 · 2022 +2 759/+4 398 · 2023 +685/+1 454 · 2024 +1 206/+3 277 · 2025 +1 582/+5 169.

Đợt (định nghĩa cố định: khoảng liên tiếp của tập cờ rộng nhất thr −0,25/lookback 45 — bao trùm mọi ô B4 — nối khoảng cách ≤ 3 ngày; 25 đợt DEV):
| Đợt | cụm hoãn/seed | X14 direct | oracle − X14 | H504 − X14 |
|---|---|---|---|---|
| 2021-12-05..2022-01-01 | 25,2 | +327 | +1 352 | +873 |
| 2022-01-06..2022-03-16 | 15,1 | +770 | +715 | +336 |
| 2022-04-27..2022-07-06 (LUNA+Celsius) | 41,5 | +1 625 | +2 555 | +6 |
| 2022-11-10..2022-12-23 (FTX) | 32,6 | +364 | +1 128 | +44 |
| 2023-03-09..2023-03-13 | 10,0 | +685 | +1 454 | +1 261 |
| 2024-04-13..2024-05-24 | 16,6 | +1 456 | +1 928 | −969 |
| 2024-06-18..2024-07-26 (06/2024) | 8,8 | **−249** | +1 349 | +158 |
| 2024-12-19..2025-03-24 | 8,1 | +1 129 | +2 017 | +1 241 |
| 2025-10-11..2025-12-31 | 12,5 | +453 | +3 152 | +1 530 |

(b) Cụm chạm 168h chưa arm ở ngày OFF (X14 cắt ngay; 367,5/seed): giữ H504 so cut **−8 254/seed** (2021 +1 033 · 2022 −578 · 2023 +405 · 2024 −3 764 · 2025 −5 350); oracle so cut +39 643. Riêng ngày OFF sát ngưỡng (dd ∈ (−0,30; −0,27], 61/seed): H504 **+1 113**, oracle +6 623. Theo đợt (H504−cut): 2021-09 +1 341, 2023-06-10..20 +1 378, 06/2024 +1 024, 2024-12..2025-03 −1 623, 2025-10..12 −1 979, còn lại |Δ| < 1,1k. Lưu ý: H504 ở đây không có DCA mới (đóng băng) ⇒ không phải phản thực đầy đủ.

(c) Beta vs idiosyncratic. Định nghĩa (cố định trước khi tính; dùng lại ở B2): loss = 1 − P_mark/F (F = giá leg đầu, P_mark = min(open, close) nến mốc), mkt = 1 − exp(EW(mark) − EW(t0)) (ALT_EW giảm cùng kỳ từ leg đầu tới mốc), ρ = loss/mkt (loss ≤ 0 ⇒ ρ = 0; mkt ≤ 0 ⇒ ρ = +∞). Nhóm mô tả (cắt điểm khác B2): beta ρ ≤ 1, trung gian 1 < ρ ≤ 3, idio ρ > 3 hoặc ALT_EW không giảm.
| Nhóm | cụm hoãn/seed | X14 direct | oracle−X14 | cụm OFF/seed | H504−cut (OFF) | oracle−cut (OFF) |
|---|---|---|---|---|---|---|
| beta | 52,0 | +1 375 | +2 728 | 54,9 | −841 | +3 037 |
| trung gian | 96,4 | +4 946 | +10 309 | 89,6 | −4 502 | +9 908 |
| idio | 22,1 | +238 | +2 613 | 223,0 | −2 911 | +26 698 |

## A3. Hồ sơ thời gian hồi (cụm hoãn, đường H504)
- Giờ từ 168h tới PnL tốt nhất: p10 21 · p25 80 · **median 186** · p75 287 · p90 318h. Phân bố/seed: 0–24h 20,5 · 24–72h 17,9 · 72–168h 35,3 · 168–336h 96,9 (57 %). Đỉnh nằm ngay ở mốc chỉ 1,8 %.
- Tertile độ sâu dd ALT_EW ngày trước mốc: sâu [−0,57; −0,355] median t_best 216h, X14 direct +2 547; giữa [−0,355; −0,327] 205h, +3 087; nông (sát ngưỡng) [−0,327; −0,308] 173h, **+925**.
- Tertile tốc độ sập (Δlog ALT_EW 7 ngày trước mốc): nhanh [−0,68; −0,18] direct +3 258, oracle-gain +10 246; giữa +1 807; chậm/hồi (≥ −0,15) +1 494.
- Tertile ρ: [0; 1,01] median t_best 130h, direct +1 401; [1,01; 1,44] 223h, +2 329; [1,44; 42] 197h, +2 882; ρ = ∞ (ALT_EW không giảm từ leg đầu tới mốc — vào lệnh sau đáy) 12,5 cụm/seed.
- Spearman (n = 1 364): t_best ~ dd −0,11, ~ tốc độ −0,09, ~ ρ +0,02; oracle-gain ~ loss +0,28, ~ ρ +0,15, ~ tốc độ −0,14. Quan hệ yếu; không có biến đơn nào tách rõ cụm hồi sớm/muộn.

## Đọc (mô tả, in-sample)
1. Engine tái lập sim tuyệt đối trên mọi cụm hoãn và mọi cụm bị cắt 168h ⇒ đủ tin để chấm biến thể exit SAU 168h bằng replay (bỏ qua lãi kép/slot).
2. Chỗ trống lý thuyết còn lớn (oracle − X14 ≈ +15,7k/seed, gấp 2,4 lần direct X14) nhưng oracle cần biết trước; điểm tốt nhất phân tán rộng (median 186h, 57 % rơi vào 168–336h sau mốc) ⇒ một luật thoát đơn giản khó bắt.
3. Giữ ở ngày OFF nói chung xấu (−8,3k/seed) — xác nhận vai trò của cờ; ngoại lệ là ngày OFF sát ngưỡng (+1,1k).
4. Theo ρ, X14 direct KHÔNG tập trung ở nhóm "beta": nhóm ρ cao (1,44–42) đóng góp direct lớn nhất ⇒ thông tin này đã thấy trước prereg B2 (ghi nhận nhiễm, B2 dự kiến bất lợi).
5. Đợt 06/2024 vẫn là đợt duy nhất X14 direct âm (−249/seed trên phân đợt mới).
