# HO2026_NOTF — sensitivity HO 2026 trên universe không TradFi, không INDEX (2026-10-29)

Prereg: `docs/prereg/PREREG_HO2026_NOTF.md` (96164b72) + `PREREG_HO2026_NOTF_ADDENDUM_TECH.md` (T1–T5; T4 = 6b9ccd33, T5 = adf5bb57) + ADDENDUM-3 (84d819ff, D5 nguyên văn).
Kết quả này là **sensitivity**, KHÔNG phải holdout mới: HO 2026 và các số trong `HO2026_TRADFI_AUDIT.md` (06d6edea) đã được nhìn trước khi chốt prereg.

## 0. TL;DR

| Luật | Kết quả trên A1 (bỏ TF+INDEX ở mọi tầng) |
|---|---|
| **D1** HO4 E0 (k24-s) | W9 và H1 vẫn **PASS** (8/8 seed > 0); Q3 vẫn **FAIL** (0/8 seed > 0, tệ hơn A0 1/8) ⇒ verdict "HO4 vững với TF", **không đổi** |
| **D2** X14 | **CONFIRM giữ**: mean ΔPnL(x14−k24-b) = **+3 547,5/seed**, **8/8 seed ≥ 0**, mean ΔmaxDD = **−0,000002 pp** ≥ −1 pp |
| **D3** Vật chất | **VẬT CHẤT**: ΔROI_W9 = **+3,28 pp** (k24-s) và **+3,33 pp** (x14), vượt ngưỡng 1,0 pp ⇒ **phải phát hành lại GOLIVE_QUARTERLY 2026 và ECMEAS H theo A1** |
| **D4** Q3 | Chỉ mô tả: Q3 A1 xấu hơn A0 −1,70 pp (k24-s), −1,30 pp (k24-b/x14), 0/8 seed dương. Không dùng làm bằng chứng nâng hạng |
| **D5** (mô tả) | TF bị bỏ: 238 leg / −6 084 (k24-s W9, 8 seed); leg thay thế: 1 473 leg / **+43 634**; leg crypto mất: 1 194 leg / +28 277; leg chung đổi +5 770 ⇒ Δ realized +27 210 |

Điểm chính: bỏ TF **không** làm hỏng verdict H1/W9 mà còn **cải thiện** ROI W9/H1 (+3,3/+5,2 pp ở k24-s), nhưng **Q3 xấu thêm** (−1,7 pp). Vì |ΔROI_W9| > 1 pp, các con số go-live 2026 phải tính lại theo A1.

## 1. Hạ tầng, bảo mật, cổng A0'

- **Jar (dùng cho A1):** k24-s/k24-b dùng jar STUB `ho2026-notf-sim-jar` sha256 `877d9ffa…` (build từ `df021437`, đúng nguồn jar gốc b7c89f09); x14 dùng `sim-jar-tsx` `cc0f9d11…`; exporter dùng `ho2026-notf-jar-exp` `a485880c…` (build từ `0594986e`).
- **Bảo mật (kiểm lại trên bản tải từ Kaggle, không chỉ local):**
  - `ho2026-notf-jar-exp/sim.jar` — sha256 `a485880cf329ae043b03608faa827f39f1a1baf5c6043308bf526b0735c65167`, `jar_sec_check` **ok=true** (other 0, max run 44, com/binance 0).
  - `ho2026-notf-sim-jar/sim.jar` — `877d9ffade1daac377cb6aea1f070f57de23e5b44b03cd39e024f13ae8baf883`, **ok=true**.
  - `sim-jar-tsx/sim.jar` — `cc0f9d11ef6b865e9070e79b3111f6786ca7008a8c4a3a28571f54322e1b1dfe`, **ok=true**.
  - Không dùng dataset `ho4p1-jar-exp` (FAIL sec) và `sim-jar-nsel` (403).
- **Cổng A0'(a):** `a0p-x26-q1` MANIFEST **137/137** file trùng md5 với `ho4p1-x26-q1`.
- **Cổng A0'(b)** (md5 printDone, seed 42, trên artefact gốc):
  - `a0p2-k24-s-s42` = `6989a3128daa249372be802fb06a8c27` = `ho4-k24-s-s42` ✔ (jar STUB)
  - `a0p2-k24-b-s42` = `7cc8864ca12bdd69f0165c9c9d5c74c5` = `ho4-k24-b-s42` ✔ (jar STUB)
  - `a0p-x14-s42` = `bb609455e02aaf30ed8afc31342329e2` = `tsx-ho-x14-s42` ✔ (jar tsx)
  - Lần chạy đầu `a0p-k24-s-s42` bằng jar tsx ra md5 của k24-b (`pen=False`) — đúng như ADDENDUM_TECH-2 (jar tsx thiếu `SIM_CRASH_ENTRY_PENALTY`), giữ làm hồ sơ, không dùng.
- **Chạy lại hạ tầng:** 1 lần duy nhất `nt-k24-b-s123` (COMPLETE nhưng `result.json` tải về không parse được), cfg y hệt, md5 cuối `7da38ae5…`. Không đổi tham số nào.

## 2. 24 kernel A1 — trạng thái và kiểm độc lập

Tất cả COMPLETE, đã kiểm **độc lập** (script `verify_nt.py`, không dùng lại `q.check`): metadata Kaggle (dataset jar đúng, kernel source `nt-tk26`/`nt-chain-y26`, không dính jar FAIL), source CFG (seed, pred md5 theo seed, base `22f69456…`, override đúng từng key, `SIM_END_DATE=20261001`, `ticker_min_days=2099`, UNSEAL), `result.json` (jar sha256 theo cấu hình, mapper 863, n>0, ok), log (`TICKER_HO4P1 ok=273 bad=0 miss=0 extra=0 other=0`, `FUND_HO4_OK`+selfcheck, `[CRASH-PENALTY]` đúng, `[TSX] extHours=336 extDays=18` chỉ ở x14, `HOLDOUT_UNSEAL DUNG`), printDone md5, 0 leg X trong 2026, và đoạn `< 20251224` **trùng từng dòng** với run gốc cùng seed/phí. Tất cả **PASS**.

| Cấu hình | Kernel (8 seed 42,7,13,21,99,123,777,2024) | md5 printDone (s42 / s7 / s13 / s21 / s99 / s123 / s777 / s2024) |
|---|---|---|
| k24-s | `nt-k24-s-s*` | 3419c54b / f4167196 / d3d805b8 / 459d879c / ddf57c2e / 87e00613 / 6b0d5b54 / e4644f47 |
| k24-b | `nt-k24-b-s*` | 3c439114 / 63473fcb / 3324a59e / a5fd353b / f67cb3ea / 7da38ae5 / c626a25f / 83987eb0 |
| x14 | `nt-x14-s*` | 235a491a / 799c8053 / 20895307 / 6f0c87bf / 490e9236 / e1f75912 / 2d89db61 / a821c7de |

## 3. Validate V1–V5

- **V1 PASS.** `nt-v1` ok=true, 12/12 ngày: 0 ô X trong ticker A1, cùng tập phút, 0 ô lệch, số ô A1 = số ô tham chiếu ngoài X (773k–776k ô/ngày); `universe_by_month` q1/q2/q3 ∩ X = ∅; `nt-tk26` md5 **273/273** khớp exporter từng ngày; 3 kernel exporter đều nhúng X (230, md5 `6e296227…`, MDT không nằm trong X) và `in_uni` có `s not in EXCL`.
- **V2 PASS.** Tái dựng độc lập ALT_EW "all" từ `a2v2` khớp `ew_2026.npz` **437 750/437 750 phút, max|Δ| 4,86e-17**; biến thể noTFIDX (chỉ `n_cr`) cho đúng **18 ngày** §2; chuỗi `SIM_LOSER_TS_EXT_DAYS` trong 8 kernel x14 đúng 18 ngày đó; `[TSX] extDays=18`.
- **V3 PASS (diễn giải: cửa sổ 2026).** 24/24 kernel có **0 leg ∈ X** trong 2026 (đếm cả leg mở/đóng qua 2026). Đoạn DEV (≤2025-12-31) giữ nguyên byte nên còn leg X (DEFI/BTCDOM 2021–2024) **giống hệt A0**; lý do và số liệu ghi ở ADDENDUM_TECH-3 §T5 — đọc V3 theo nghĩa toàn bộ printDone sẽ mâu thuẫn với §2.
- **V4 PASS.** MTM: `miss=0, nofile=0, fail=0` (772 file giá, 692 cache, 71 tải, 9 404 settle-tail có xử lý); 48/48 run `eqcheck.final_ok=true`, `upd_vs_result=true`; `orig_reproduced=true` — số A0 tái lập **HO4_RESULT_A.json** và `tsx/ho/ho_mtm.json` trong 1e-6 tương đối.
- **V5 PASS.** Parity từng seed: jar sha256 đúng cấu hình, override đúng, pred md5 theo seed, `TICKER_HO4P1 ok=273`, FUND selfcheck, mapper 863, penalty 0,01675 (chỉ k24-s), UNSEAL; x14 có `[TSX] extHours=336`; đoạn DEV trùng từng dòng với run gốc cùng seed/phí (24/24).

## 4. Kết quả (scorer HO4 `ho4_score_a`/`ecm_mtm_h`, giá close 1m Vision; ROI/maxDD % MTM)

| Cấu hình | Cửa sổ | A0 ROI | A0 maxDD | A0 ΣPnL | A0 seed>0 | A1 ROI | A1 maxDD | A1 ΣPnL | A1 seed>0 | ΔROI pp | ΔmaxDD pp |
|---|---|---|---|---|---|---|---|---|---|---|---|
| k24-s | W9 | 8,88 | −5,77 | 9 262 | 8/8 | **12,16** | **−5,72** | 12 663 | 8/8 | **+3,28** | +0,05 |
| k24-s | H1 | 9,55 | −5,54 | 11 682 | 8/8 | **14,79** | −5,67 | 17 127 | 8/8 | **+5,24** | −0,13 |
| k24-s | Q3 | −0,59 | −4,29 | −2 420 | 1/8 | **−2,29** | −4,53 | −4 463 | 0/8 | **−1,70** | −0,24 |
| k24-b | W9 | 10,19 | −5,75 | 14 758 | 8/8 | 13,38 | −5,79 | 19 336 | 8/8 | +3,19 | −0,05 |
| k24-b | H1 | 9,90 | −5,58 | 16 723 | 8/8 | 14,55 | −5,74 | 23 412 | 8/8 | +4,65 | −0,16 |
| k24-b | Q3 | 0,27 | −4,07 | −1 965 | 2/8 | −1,03 | −4,16 | −4 076 | 0/8 | −1,30 | −0,08 |
| x14 | W9 | 12,49 | −5,71 | 18 105 | 8/8 | **15,82** | −5,79 | 22 883 | 8/8 | **+3,33** | −0,09 |
| x14 | H1 | 12,20 | −5,58 | 20 117 | 8/8 | **17,02** | −5,74 | 27 048 | 8/8 | **+4,82** | −0,16 |
| x14 | Q3 | 0,27 | −4,07 | −2 012 | 2/8 | −1,03 | −4,16 | −4 165 | 0/8 | −1,30 | −0,08 |

(ROI, maxDD, ΣPnL là trung bình 8 seed; legs trung bình/seed: k24-s W9 454,4 → 459,5; x14 W9 454,4 → 461,4.)

**Theo seed — ROI (%) W9 / H1 / Q3**

| Seed | k24-s A0 | k24-s A1 | x14 A0 | x14 A1 |
|---|---|---|---|---|
| 42 | 10,65 / 9,42 / 1,12 | 10,58 / 13,24 / −2,35 | 13,00 / 10,72 / 2,06 | 13,89 / 15,15 / −1,09 |
| 7 | 7,85 / 8,92 / −0,98 | 12,67 / 16,00 / −2,87 | 11,87 / 11,63 / 0,22 | 18,74 / 18,98 / −0,20 |
| 13 | 9,45 / 11,24 / −1,61 | 10,13 / 12,34 / −1,96 | 14,27 / 13,90 / 0,33 | 14,02 / 15,07 / −0,92 |
| 21 | 10,62 / 10,28 / 0,31 | 14,78 / 17,75 / −2,53 | 14,15 / 13,16 / 0,88 | 17,89 / 19,26 / −1,15 |
| 99 | 9,71 / 5,51 / 3,98 | 13,45 / 14,69 / −1,08 | 15,02 / 10,02 / 4,54 | 15,62 / 15,97 / −0,30 |
| 123 | 9,62 / 11,07 / −1,31 | 13,93 / 15,56 / −1,42 | 12,35 / 13,07 / −0,64 | 17,76 / 18,41 / −0,55 |
| 777 | 5,30 / 9,47 / −3,81 | 10,48 / 14,74 / −3,71 | 8,41 / 12,32 / −3,48 | 14,05 / 16,97 / −2,50 |
| 2024 | 7,82 / 10,48 / −2,41 | 11,24 / 13,98 / −2,40 | 10,84 / 12,77 / −1,71 | 14,60 / 16,35 / −1,50 |
| **mean** | **8,88 / 9,55 / −0,59** | **12,16 / 14,79 / −2,29** | **12,49 / 12,20 / 0,27** | **15,82 / 17,02 / −1,03** |

ΔX14 = x14 − k24-b trên A1: W9 +3 547,5/seed (8/8 ≥ 0); ΔmaxDD trung bình −0,000002 pp. Trên A0: +3 347,9/seed.

## 5. D1–D5

- **D1 (k24-s, E0 = mean ΣPnL_S > 0 và ≥6/8 seed > 0):** A1 W9 12 663 (8/8) PASS; H1 17 127 (8/8) PASS; Q3 −4 463 (0/8) FAIL. Cùng verdict với A0 (W9/H1 PASS, Q3 FAIL) ⇒ **"HO4 vững với TF"**. Số go-live nếu dùng A1: W9 +12,16 % ROI, H1 +14,79 % (A0: 8,88 / 9,55).
- **D2 (x14 trên A1):** mean ΔPnL **+3 547,5/seed** > 0, **8/8 seed ≥ 0**, mean ΔmaxDD **−0,000002 pp** ≥ −1 pp ⇒ **CONFIRM giữ** (luật §7 TS_MKT_EXT y nguyên; scorer tsx cũng cho CONFIRM, defer-cluster 10–14/seed).
- **D3:** |ΔROI_W9| = 3,28 pp (k24-s) và 3,33 pp (x14) > 1,0 pp ⇒ **có vật chất**; ΔmaxDD_W9 trong ±0,09 pp. ⇒ **phát hành lại GOLIVE_QUARTERLY 2026 và ECMEAS H theo A1**.
- **D4:** Q3 chỉ mô tả — A1 −1,70 pp (k24-s), −1,30 pp (k24-b/x14) so A0, 0/8 seed > 0. Q3 vẫn FAIL; không dùng để nâng hạng.
- **D5 (mô tả, gộp 8 seed; pnl realized theo `start`, khớp audit: A0 k24-s W9 = 74 096):**

| Cấu hình | Cửa sổ | TF bỏ (leg / PnL) | Leg thay thế (leg / PnL) | Crypto mất (leg / PnL) | Leg chung (n / ΔPnL) | Δ realized |
|---|---|---|---|---|---|---|
| k24-s | W9 | 238 / −6 084 | 1 473 / **+43 634** | 1 194 / +28 277 | 2 203 / +5 770 | +27 210 |
| k24-s | H1 | 221 / −7 530 | 908 / +50 937 | 542 / +19 526 | 1 570 / +4 710 | +43 651 |
| k24-s | Q3 | 17 / +1 446 | 565 / −7 303 | 652 / +8 752 | 633 / +1 061 | −16 440 |
| k24-b | W9 | 236 / −8 183 | 1 492 / +60 029 | 1 198 / +37 800 | 2 203 / +6 214 | +36 626 |
| k24-b | H1 | 220 / −10 229 | 915 / +68 031 | 547 / +30 190 | 1 561 / +5 631 | +53 699 |
| k24-b | Q3 | 16 / +2 046 | 577 / −8 002 | 651 / +7 610 | 642 / +584 | −17 074 |
| x14 | W9 | 236 / −6 367 | 1 488 / +64 504 | 1 196 / +38 514 | 2 203 / +5 865 | +38 223 |
| x14 | H1 | 220 / −8 458 | 911 / +72 672 | 545 / +30 808 | 1 561 / +5 304 | +55 626 |
| x14 | Q3 | 16 / +2 091 | 577 / −8 168 | 651 / +7 705 | 642 / +561 | −17 404 |

Cột "leg chung ΔPnL" là phần dư (leg cùng khoá nhưng khác entry/qty do path); thêm vào để tổng phân rã khớp Δ realized. D5 không dùng để quyết.

## 6. Bất thường / giới hạn

- **Cơ chế của +3,3 pp W9 CHƯA GIẢI THÍCH đầy đủ:** phân rã D5 cho thấy slot TF giải phóng sinh leg crypto mới lãi lớn (+43,6k/8 seed) trong khi leg crypto bị mất cũng lãi (+28,3k) và leg chung tăng +5,8k; chưa tách được phần nào do slot, phần nào do market/gate/Tool1/ALT_EW đổi. Không có ablation trong prereg.
- **Q3 xấu thêm −1,7 pp** (audit ước −0,2 pp khi chỉ bỏ leg TF): leg thay thế ở Q3 lỗ −7,3k. CHƯA GIẢI THÍCH chi tiết; Q3 vốn FAIL ở cả hai universe.
- D5 là realized theo `start`, không phải MTM; chỉ mô tả. A0 D5 khớp audit từng số (238 leg / −6 084; tổng W9 74 096) — kiểm chéo tốt.
- V3 đọc theo cửa sổ 2026 (ADDENDUM_TECH-3 §T5); nếu MASTER muốn đọc literal toàn printDone thì V3 sẽ FAIL vì §2 buộc giữ DEV nguyên byte — cần MASTER xác nhận cách đọc.
- Khác biệt gốc đã có (không do NOTF): `tsx-ho-x14-s123` có 4 010 leg so `ho4-k24-b-s123` 4 012 (khác 2 leg trong 2026 do x14 kéo dài time-stop), DEV trùng byte.
- Mọi số A1 dùng đúng 1 lần chấm; không tune gì sau khi thấy số.

## 7. Artefact & dung lượng

- Ảnh chụp số: `~/claude_master/ho_tradfi_wk/notf_score.json`, `notf_mtm.json`, `verify_nt.json`, `v5_dev.json`, `res/*.json`, `score_out.log`.
- Script: `research/ho2026_notf/notf_score.py`, `research/ho2026_notf/verify_nt.py` (commit cùng tài liệu này).
- Tải về trong task: 3 dataset jar 286 MB (kiểm sec) + JSON nhỏ; có 408 MB tải nhầm `nt-x26-q1` đã xoá ngay. Đã xoá toàn bộ bản tải tạm (`sec_verify/`, `v1out/`, `/tmp/nt_kmd`, `/tmp/nt_fetch.py`) sau khi lấy số; dữ liệu lớn vẫn trên Kaggle.

## ĐÍNH CHÍNH (2026-10-30)

1. **V3 — định nghĩa đã đổi sau khi kernel fail.** Dòng V3 ở §3 ("PASS, diễn giải cửa sổ 2026") chỉ đúng theo định
   nghĩa **đã sửa ngày 10-28 11:13** (`x_legs_2026 == 0`). Theo **nguyên văn prereg §4** (`x_legs == 0` trên toàn bộ
   printDone) thì **V3 = FAIL** (24/24 kernel có 2–5 leg X ở đoạn DEV). Toàn bộ bằng chứng, mốc thời gian và đánh giá
   trung thực ở `docs/prereg/PREREG_HO2026_NOTF_ADDENDUM_TECH-4.md` §T6. **Cần MASTER phê chuẩn cách đọc 2026.**
2. **Cổng A0'(c) PASS** — chain hạ nguồn với X = ∅ tái lập đúng pred md5 gốc 8/8 seed và 17/17 file MANIFEST:
   `docs/result/HO2026_NOTF_A0PC.md`.
3. **Đọc lại cơ chế +3,3 pp**: `HO2026_NOTF_MECH.md` §3.1 (ĐÍNH CHÍNH: 7,4 % là mean |Δqty| trên nhóm đổi; equity
   tại giờ vào +1,7 % ⇒ lãi kép ~1/3; bỏ "87 %"; V1 là đẳng thức kế toán) và `HO2026_NOTF_EPISODE.md`
   (ΔROI theo tháng, độ nhạy bỏ tháng 6 / 06-02..06, bootstrap khối ngày).
