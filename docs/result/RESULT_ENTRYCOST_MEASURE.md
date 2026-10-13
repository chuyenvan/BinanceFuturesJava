# RESULT_ENTRYCOST_MEASURE — kỳ vọng K24+skipFull với chi phí vào THỰC (bucket EXEC), 8 seed DEV + HO4 W9 — chỉ ĐO

Ngày 2026-10-13 (GMT+7). Pre-reg `docs/prereg/PREREG_ENTRYCOST_MEASURE.md` **48ff35a5** (commit trước kernel đầu tiên 06:47). Không chọn/tune, không đổi cấu hình; KHÔNG chấm GO/NO-GO (pre-reg không có luật GO). JSON máy `docs/result/RESULT_ENTRYCOST_MEASURE.json`; chẩn đoán phụ `docs/result/entrycost_measure_overlap.json`. Script `research/analysis/ecm_{q,mtm_d,mtm_h,score,overlap}.py` (chạy tại `~/claude_master/1013/ecm`).
Ràng buộc đã giữ: 0 Java sim trên Oracle, 0 chạm 242/shadow/systemd, 0 Binance REST (giá H = Binance Vision qua cache có sẵn, 0 tải mới), Kaggle ≤ 2 kernel song song toàn tài khoản (kiểm `running()` trước mỗi push), nền KHÔNG chạy lại.

## 0. Tóm tắt số (rủi ro trước)
1. **(D) DEV 2021-07→2025-12, 8 seed:** bucket thực ΣPnL **105 358 ± 4 471** (ROI/35k 301,0%), CAGR22 MTM **36,08 ± 1,15%**, maxDD MTM phút 2022–25 **−22,59 ± 1,35%** (tệ nhất −24,67%, S21), Calmar22 **1,604 ± 0,142**. So phí gốc: ΔΣPnL **−4 689** CI95 [−6 069; −3 309] (0/8 seed > 0), ΔCAGR22 **−0,87 pp** [−1,18; −0,57], ΔmaxDD **−0,05 pp** [−0,07; −0,02], ΔCalmar −0,043. So stress 1,675%: ΔΣPnL **+35 913** [+34 290; +37 537] (8/8), ΔCAGR22 **+8,45 pp** [+7,89; +9,02], ΔCalmar +0,392. ⇒ bucket nằm ~91% quãng stress → phí gốc theo CAGR22 (8,45 / 9,32 pp).
2. **(H) HO4 W9 2026-01→09, 8 seed:** bucket ΣPnL **13 586 ± 3 442** [7 347..18 633], ROI MTM E1/E0 **9,68 ± 2,36%**, maxDD MTM phút **−5,74 ± 0,59%** (tệ nhất −6,81%, S777), Calmar năm hoá 2,344. **E0 (báo, không quyết): mean > 0, 8/8 seed > 0 ⇒ ĐẠT.** Δ vs phí gốc: ROI −0,51 pp [−0,86; −0,16], ΔmaxDD +0,01 pp; vs stress: ROI +0,80 pp [−0,17; +1,78] (5/8), ΔmaxDD +0,04 pp.
3. **Q3 2026 (quý mù duy nhất của HO4) vẫn âm:** bucket ΣPnL −2 847 [−9 315..+4 512], 2/8 seed > 0 (phí gốc −1 965, stress −2 420). Chi phí vào thực không đổi dấu Q3.
4. **maxDD gần như KHÔNG phụ thuộc mô hình chi phí vào** (D: −22,59 / −22,55 / −22,86; H: −5,74 / −5,75 / −5,77) — đáy DD do sự kiện thị trường (2022), không do chi phí vào. Chi phí vào chỉ ăn vào lợi suất.
5. **Chi phí vào trực tiếp (log Java):** D **4 065 ± 141 USD/seed** (1,15 USD/chân; 2022–25 = 3 766 USD, ≈ 2,4× ước P0 điểm của EXEC 1 555 vì bucket = CI_trên); H 2026 **934 ± 43 USD** (2,05 USD/chân — margin lớn hơn do equity cao hơn). ΔΣPnL vs gốc lớn hơn chi phí trực tiếp (D 115%, H 125%) — hiệu ứng lãi kép/đường đi sổ lệnh.
6. **Rủi ro chính:** (a) H không độc lập (HO4 đã dùng làm holdout; W9 chứa H1 đã nhìn ở HO26), chỉ Q3 là mù; (b) 3 biến thể chạy trên 3 jar khác nhau (bucket 246087fb, gốc D 0944841c, stress D + cả nền H b7c89f09) — parity off chỉ có ở D seed 42; H không có parity off (chẩn đoán trùng lệnh 94,9–98,7% ≈ D 95,9–97,8%, §2); (c) ΣPnL tuyệt đối ở H phụ thuộc equity đầu 2026 (size theo equity) ⇒ Δ ΣPnL H vs stress (+4 324) phần lớn là chênh vốn đầu kỳ, ROI MTM mới là so sánh không thang; (d) CI là paired t qua 8 seed cùng dữ liệu — không phải bất định thị trường/ngoài mẫu; (e) hiệu chuẩn bucket từ DEV 2022–25 (EXEC, V1 FAIL biên phút) áp ra 2021 và 2026 là ngoại suy.

## 1. Cấu hình + kernel
| mục | giá trị |
|---|---|
| nền | `PARITY["ho4p1-c2"]` = B0OV + `SELECTOR_RANK_TOPK=24` + `GATE_QUOTA_SKIP_WHEN_FULL=true`, phí gốc legacy, artefact HO4-P1 (Vision; pred 8 seed `arts.json`, ticker 273/273, funding rebuild) |
| biến thể duy nhất | `SIM_ENTRY_COST_MODE=bucket` NC 0.0007 · C1 0.0018 · C2 0.0019 · C4 0.0032; `SIM_CRASH_ENTRY_PENALTY` không khai |
| jar | dataset `chuyendinh/sim-jar-ecost`, sha256 **246087fb606c5307c407a442062d677832ef29fd3bfb81d6eb7516aa075754cf**, code b58e05c9 (module 7caa968b); không build jar mới |
| template | `ho4p1_queue.template()` (guard NOWRITE_HOST / SYMBOL_MAPPER_PREFLIGHT / TICKER_HO4P1 / FUND_HO4) |
| (D) | SIM_END 20251231, không unseal. Seed 42 = **dùng lại `ec-s-s42`** (smoke 7caa968b; md5 printDone d1d804beefe011b4cb74832b91311cc7, n 3529 — scorer tính lại md5 từ file, khớp). 7 kernel mới `sim-ecm-d-s{7,13,21,99,123,777,2024}` |
| (H) | SIM_END 20261001, `HOLDOUT_UNSEAL` chỉ trong extra_env (y `ho4p1_queue` pha 1 k24-b). 8 kernel `sim-ecm-h-s{42,7,13,21,99,123,777,2024}`; bundle `sim-ho26a-bundle`, market `CHAIN` Vision |
| chạy | 15 kernel, mỗi kernel 1 version (0 retry, 0 ERROR), COMPLETE, 1 877–3 058 s; push 06:47 → xong 12:32; queue `ecm_q.py` (≤ 2 kernel toàn tài khoản) |

## 2. Kiểm hợp lệ (pre-reg) — ĐẠT hết
| kiểm | kết quả |
|---|---|
| `[ENTRY-COST] SUMMARY mode=bucket` mọi kernel bucket | 16/16 (15 mới + ec-s-s42); legsTotal == số dòng printDone 16/16; nền 32/32 KHÔNG có dòng SUMMARY |
| 12/12 check sim (ok, jar, mapper, ov, ov_log, pred, n, tk, fund, market, pen, unseal) | 16/16 run bucket đều 12/12 true |
| jar sha giống nhau | 16/16 = 246087fb… (result.json jar_sha256 == check) |
| tái lập seed 42 (D) | n 3529 & md5 d1d804be… ĐẠT |
| scorer tự kiểm | **323/323** (E MTM phút cuối vs equity_final ≤ 0,01% 48/48; equity_final = 35 000 + Σpnl 24/24 D; n_rows == n_trades 48/48; nền D trùng NSEL_RESULT_B cagr22/maxdd22/calmar22 8/8; nền H W9 + Q3 trùng HO4_RESULT_A (n, ΣPnL, ROI, maxDD) 32/32; Vision fetch fail 0, phút-chân thiếu giá H 0; D 903/178 418 383 = 5e-6) |
| MTM nền chạy lại | ecm_mtm_d/h trên 24+24 run cho số nền **byte-identical** bản chỉ-nền trước khi có kernel bucket (17/17 D, 16/16 H) |
| nhất quán D↔H (thêm) | equity đầu 2026 của `ecm-h-s*` = 35 000 + ΣPnL `ecm-d-s*`/ec-s-s42 **8/8 chính xác** (đoạn DEV của run H trùng run D) |
| chẩn đoán trùng lệnh (phụ, không phải thước) | bucket vs gốc cùng seed, (sym, start): D 0,959–0,978; H 0,949–0,987; symbol chỉ-một-bên ≤ 4 (D) / ≤ 1 (H) ⇒ không thấy lệch riêng 2026 do jar |

## 3. Nguồn nền (KHÔNG chạy lại) + thước
| cửa sổ | biến thể | run | nguồn số đã công bố (md5 file) |
|---|---|---|---|
| D | phí gốc | `gqsf-a1`, `gqsf-s{7,13,21,99,123,777,2024}` (jar 0944841c) | `RESULT_GATE_QUOTA_SKIPFULL.md` 9c4cd7ce / `gate_skipfull.json` 773e4007; MTM `docs/audit/COVERAGE_M2_BASE_20261009.json` 2c11d1ce (tái lập đúng 36,95 / −22,55 / 1,647) |
| D | stress 1,675% | `nsel-nen-s*` (jar b7c89f09) | `COVERAGE_M2_BASE_20261009.json` 2c11d1ce, `NSEL_RESULT_B.json` 17f44a54 (tái lập 27,63 / −22,86 / 1,212) |
| H | phí gốc / stress | `ho4-k24-b-s*` / `ho4-k24-s-s*` (jar b7c89f09) | `docs/result/ho4/HO4_RESULT_A.json` d32c16c7 (436aea1e), `HO4_RESULT_B.json` 813fa3b0 (4e417a60) |

Thước (giống hệt cho 3 biến thể trong cùng cửa sổ):
- **ΣPnL** = Σ pnl dòng printDone có `end` trong cửa sổ; **n** = dòng có `start` trong cửa sổ (mọi chân). **ROI/35k** = ΣPnL / 35 000.
- **(D)** cửa sổ toàn run 2021-07-01 → 2025-12-31: ΣPnL, n, ROI/35k, CAGR (35 000 → 35 000 + ΣPnL, 1 645 ngày). **MTM phút** = thước `nsel_score_b` / COVERAGE_M2 (`ecm_mtm_d.py`): realized ghi tại phút `end` + unrealized q·(close1m − entry); giá = ticker sim (zip `wfo-ticker-2021-2025`, chỉ có 2022–25) ⇒ CAGR22/maxDD22/Calmar22 = 2022-01-01 → 2025-12-31. 2021H2 chỉ có MTM ngày 07:00 (b+unP dòng `Update` sim.out).
- **(H)** = hàm `ho4_score_a.py` (scorer A HO4, `ecm_mtm_h.py`): giá close 1m Binance Vision (cache 669 file, sha256 `.CHECKSUM`), đuôi settle `ho4p1_excl26`; W9 [2026-01-01, 10-01) +07; ROI = E1/E0 − 1; maxDD đỉnh reset đầu cửa sổ; Calmar = CAGR năm hoá / |maxDD|; quý Q1/Q2/Q3 đỉnh reset đầu quý.
- **Δ ghép cặp** = bucket − nền cùng seed: mean ± sd [min..max], số seed Δ > 0, CI95 paired t (df 7, t 2,3646).
- Chân/USD theo bucket = dòng Java `[ENTRY-COST] SUMMARY` (D, toàn run) và `YEAR 2026` (H, chân vào 2026-01→09).

## 4. Lệch / bổ sung so với pre-reg (khai đủ)
1. Seed 42 (D) dùng lại output `ec-s-s42` (pre-reg cho phép nếu tái lập md5) — đã xác nhận md5/n từ file.
2. CAGR (D) báo hai bản: toàn run 2021-07→2025 (realized) và CAGR22 MTM phút 2022–25; maxDD/Calmar MTM phút chỉ 2022–25 vì không có ticker 1m 2021 trên Oracle (2021 dùng MTM ngày 07:00, đánh giá THẤP DD: chênh phút − ngày 2022–25 trung bình −6,90 pp).
3. CI95 paired t và chẩn đoán trùng lệnh (§2) là phần THÊM (mô tả), viết trước khi đọc số bucket đầy đủ, không đổi thước pre-reg.
4. Nguồn giá MTM khác nhau giữa 2 cửa sổ (D ticker sim, H Vision) — y nguồn của số nền đã công bố; trong một cửa sổ 3 biến thể cùng nguồn.
5. Worktree/nhánh: commit trên `research/ecost-measure` (`~/claude_master/1013/em_wt`). Worktree `~/claude_master/1013/ecm_wt` (nhánh `result/entrycost-measure`, 0 commit, tạo ở lần chạy trước) để nguyên, không dùng.
6. Không có lệch nào khác: không đổi key/cost/seed/cửa sổ, không thêm biến thể, không chạy lại nền.

## 5. Bảng số (sinh máy: `ecm_score.py`, md5 json 0894561c)

### (D) DEV 2021-07-01 → 2025-12-31 — mean ± sd [min..max] qua seed

| chỉ số | bucket thực | phí gốc | stress 1,675% |
|---|---|---|---|
| n chân (2021-07→2025) | 3 543 ± 59 [3 440..3 657] | 3 551 ± 57 [3 464..3 666] | 3 528 ± 49 [3 452..3 628] |
| ΣPnL USD (2021-07→2025) | 105 358 ± 4 471 [99 661..111 203] | 110 047 ± 5 392 [104 379..118 362] | 69 445 ± 4 065 [63 991..74 969] |
| ROI/35k % | 301,0 ± 12,8 [284,7..317,7] | 314,4 ± 15,4 [298,2..338,2] | 198,4 ± 11,6 [182,8..214,2] |
| CAGR 2021-07→2025 % (realized, 4,50 năm) | 36,11 ± 0,96 [34,87..37,36] | 37,10 ± 1,13 [35,91..38,83] | 27,46 ± 1,10 [25,97..28,94] |
| CAGR 2022–25 % (MTM phút) | 36,08 ± 1,15 [34,62..37,89] | 36,95 ± 1,37 [35,58..39,31] | 27,63 ± 1,47 [25,67..29,72] |
| maxDD MTM phút 2022–25 % | -22,59 ± 1,35 [-24,67..-20,14] | -22,55 ± 1,37 [-24,67..-20,05] | -22,86 ± 0,98 [-24,69..-21,59] |
| Calmar MTM 2022–25 | 1,604 ± 0,142 [1,443..1,881] | 1,647 ± 0,161 [1,453..1,961] | 1,212 ± 0,108 [1,060..1,377] |
| maxDD MTM ngày 07:00 2021-07→2025 % (phụ) | -15,99 ± 1,72 [-18,17..-12,32] | -15,78 ± 1,71 [-18,11..-12,21] | -16,54 ± 1,66 [-18,41..-13,27] |

**Δ ghép cặp seed (bucket − nền)**: mean ± sd [min..max], số seed Δ>0, CI95 paired t (df k−1)

| chỉ số | bucket − phí gốc | bucket − stress |
|---|---|---|
| n chân (2021-07→2025) | -8 ± 10 [-24..12] · 1/8 · CI95 [-17; 1] | 15 ± 22 [-22..43] · 6/8 · CI95 [-4; 34] |
| ΣPnL USD (2021-07→2025) | -4 689 ± 1 651 [-7 159..-2 370] · 0/8 · CI95 [-6 069; -3 309] | 35 913 ± 1 942 [33 068..38 754] · 8/8 · CI95 [34 290; 37 537] |
| ROI/35k % | -13,4 ± 4,7 [-20,5..-6,8] · 0/8 · CI95 [-17,3; -9,5] | 102,6 ± 5,5 [94,5..110,7] · 8/8 · CI95 [98,0; 107,2] |
| CAGR 2021-07→2025 % (realized, 4,50 năm) | -0,99 ± 0,33 [-1,47..-0,51] · 0/8 · CI95 [-1,27; -0,72] | 8,65 ± 0,48 [7,96..9,38] · 8/8 · CI95 [8,25; 9,05] |
| CAGR 2022–25 % (MTM phút) | -0,87 ± 0,36 [-1,42..-0,25] · 0/8 · CI95 [-1,18; -0,57] | 8,45 ± 0,67 [7,33..9,42] · 8/8 · CI95 [7,89; 9,02] |
| maxDD MTM phút 2022–25 % | -0,05 ± 0,03 [-0,09..-0,00] · 0/8 · CI95 [-0,07; -0,02] | 0,26 ± 0,59 [-0,01..1,73] · 7/8 · CI95 [-0,23; 0,76] |
| Calmar MTM 2022–25 | -0,043 ± 0,021 [-0,080..-0,010] · 0/8 · CI95 [-0,060; -0,026] | 0,392 ± 0,071 [0,343..0,563] · 8/8 · CI95 [0,332; 0,451] |
| maxDD MTM ngày 07:00 2021-07→2025 % (phụ) | -0,21 ± 0,20 [-0,46..-0,01] · 0/8 · CI95 [-0,38; -0,05] | 0,54 ± 0,39 [0,16..1,21] · 8/8 · CI95 [0,22; 0,87] |

### (H) HO4 W9 2026-01-01 → 10-01 — mean ± sd [min..max] qua seed

| chỉ số | bucket thực | phí gốc | stress 1,675% |
|---|---|---|---|
| n chân (start∈W9) | 456 ± 30 [406..490] | 455 ± 30 [403..488] | 454 ± 27 [406..484] |
| ΣPnL W9 USD | 13 586 ± 3 442 [7 347..18 633] | 14 758 ± 3 266 [8 700..19 001] | 9 262 ± 1 896 [5 695..11 247] |
| ROI/35k % | 38,8 ± 9,8 [21,0..53,2] | 42,2 ± 9,3 [24,9..54,3] | 26,5 ± 5,4 [16,3..32,1] |
| ROI MTM E1/E0 % | 9,68 ± 2,36 [5,02..12,94] | 10,19 ± 2,20 [5,67..12,58] | 8,88 ± 1,80 [5,30..10,65] |
| CAGR năm hoá % | 13,17 ± 3,25 [6,78..17,67] | 13,87 ± 3,03 [7,66..17,18] | 12,06 ± 2,47 [7,15..14,49] |
| maxDD MTM phút % | -5,74 ± 0,59 [-6,81..-5,08] | -5,75 ± 0,50 [-6,67..-5,14] | -5,77 ± 0,47 [-6,74..-5,13] |
| Calmar MTM (CAGR năm hoá/|maxDD|) | 2,344 ± 0,681 [0,995..3,147] | 2,457 ± 0,652 [1,150..3,124] | 2,123 ± 0,538 [1,061..2,641] |
| Sharpe ngày | 1,90 ± 0,50 [1,05..2,59] | 1,99 ± 0,47 [1,16..2,57] | 1,81 ± 0,44 [1,11..2,56] |

**Δ ghép cặp seed (bucket − nền)**: mean ± sd [min..max], số seed Δ>0, CI95 paired t (df k−1)

| chỉ số | bucket − phí gốc | bucket − stress |
|---|---|---|
| n chân (start∈W9) | 2 ± 2 [-1..4] · 6/8 · CI95 [0; 3] | 2 ± 7 [-15..8] · 6/8 · CI95 [-4; 8] |
| ΣPnL W9 USD | -1 172 ± 468 [-1 799..-368] · 0/8 · CI95 [-1 563; -780] | 4 324 ± 1 866 [1 652..7 956] · 8/8 · CI95 [2 764; 5 884] |
| ROI/35k % | -3,3 ± 1,3 [-5,1..-1,1] · 0/8 · CI95 [-4,5; -2,2] | 12,4 ± 5,3 [4,7..22,7] · 8/8 · CI95 [7,9; 16,8] |
| ROI MTM E1/E0 % | -0,51 ± 0,42 [-0,97..0,35] · 1/8 · CI95 [-0,86; -0,16] | 0,80 ± 1,17 [-0,27..3,23] · 5/8 · CI95 [-0,17; 1,78] |
| CAGR năm hoá % | -0,70 ± 0,58 [-1,34..0,49] · 1/8 · CI95 [-1,19; -0,22] | 1,11 ± 1,62 [-0,37..4,48] · 5/8 · CI95 [-0,24; 2,46] |
| maxDD MTM phút % | 0,01 ± 0,16 [-0,15..0,33] · 2/8 · CI95 [-0,12; 0,14] | 0,04 ± 0,22 [-0,33..0,34] · 5/8 · CI95 [-0,15; 0,22] |
| Calmar MTM (CAGR năm hoá/|maxDD|) | -0,112 ± 0,097 [-0,208..0,084] · 1/8 · CI95 [-0,193; -0,032] | 0,222 ± 0,286 [-0,066..0,831] · 7/8 · CI95 [-0,017; 0,461] |
| Sharpe ngày | -0,09 ± 0,07 [-0,17..0,06] · 1/8 · CI95 [-0,14; -0,03] | 0,10 ± 0,29 [-0,11..0,74] · 4/8 · CI95 [-0,14; 0,34] |

### (D) theo năm — mean qua seed (ΣPnL theo end, n theo start; ROI/maxDD = MTM phút, đỉnh reset đầu năm; 2021 = 07-01→12-31, MTM NGÀY 07:00 vì không có ticker 1m 2021)

| năm | ΣPnL bucket | ΣPnL gốc | ΣPnL stress | Δ b−gốc (seed>0) | Δ b−stress (seed>0) | n b/gốc/stress | ROI MTM b/gốc/stress % | maxDD b/gốc/stress % | chân bucket NC/C1/C2/C4 | USD bucket NC/C1/C2/C4 (Σ) |
|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | 5 917 | 6 213 | 4 346 | -296 · CI95 [-367; -226] (0/8) | 1 571 · CI95 [1 294; 1 847] (8/8) | 583/585/572 | 16,9/17,7/12,4 | -6,80/-6,74/-7,39 | 368/109/75/31 | 112/86/67/33 (299) |
| 2022 | 3 127 | 3 454 | 1 687 | -327 · CI95 [-507; -147] (1/8) | 1 439 · CI95 [959; 1 920] (8/8) | 619/621/618 | 7,7/8,4/4,3 | -22,36/-22,32/-22,43 | 389/121/66/44 | 118/103/61/50 (332) |
| 2023 | 28 773 | 29 586 | 22 512 | -813 · CI95 [-1 022; -604] (0/8) | 6 261 · CI95 [5 810; 6 712] (8/8) | 757/761/763 | 64,9/66,0/54,3 | -6,18/-6,08/-7,39 | 426/142/118/71 | 213/219/190/198 (819) |
| 2024 | 33 614 | 34 867 | 21 014 | -1 253 · CI95 [-2 001; -505] (0/8) | 12 601 · CI95 [11 114; 14 087] (8/8) | 844/844/839 | 46,6/47,2/33,6 | -12,28/-12,13/-12,64 | 459/185/116/84 | 331/394/254/280 (1 259) |
| 2025 | 33 927 | 35 926 | 19 886 | -1 999 · CI95 [-2 728; -1 270] (0/8) | 14 042 · CI95 [13 128; 14 955] (8/8) | 740/740/737 | 32,0/33,0/23,6 | -17,97/-17,92/-19,75 | 422/136/108/75 | 398/383/293/282 (1 356) |

### (H) theo quý 2026 — mean qua seed (ΣPnL theo end, n theo start; ROI/maxDD MTM phút Vision, đỉnh reset đầu quý)

| quý | ΣPnL bucket [min..max] | ΣPnL gốc | ΣPnL stress | Δ b−gốc (seed>0) | Δ b−stress (seed>0) | seed bucket>0 | n b/gốc/stress | ROI MTM b/gốc/stress % | maxDD b/gốc/stress % |
|---|---|---|---|---|---|---|---|---|---|
| Q1 | 6 528 [3 840..9 068] | 6 425 | 4 810 | 103 · CI95 [-314; 520] (4/8) | 1 718 · CI95 [1 369; 2 067] (8/8) | 8/8 | 132/131/132 | 4,66/4,45/4,61 | -5,44/-5,58/-5,54 |
| Q2 | 9 904 [7 661..11 510] | 10 297 | 6 871 | -393 · CI95 [-629; -157] (1/8) | 3 033 · CI95 [2 126; 3 939] (8/8) | 8/8 | 162/160/160 | 5,16/5,23/4,71 | -3,31/-3,34/-3,51 |
| Q3 | -2 847 [-9 315..4 512] | -1 965 | -2 420 | -881 · CI95 [-1 155; -608] (0/8) | -427 · CI95 [-1 696; 842] (3/8) | 2/8 | 162/164/163 | -0,33/0,27/-0,59 | -4,31/-4,07/-4,29 |

### Chân + chi phí vào USD theo bucket (bản bucket; mean ± sd qua seed)

| cửa sổ | nguồn log | chân NC | chân C1 | chân C2 | chân C4 | USD NC | USD C1 | USD C2 | USD C4 | Σ USD | USD/chân |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D | SUMMARY (2021-07→2025-12) | 2 064 ± 40 [2 006..2 152] | 693 ± 15 [671..723] | 482 ± 9 [468..497] | 305 ± 9 [289..315] | 1 173 ± 50 [1 113..1 241] | 1 184 ± 38 [1 134..1 241] | 865 ± 36 [805..919] | 843 ± 45 [768..907] | 4 065 ± 141 [3 879..4 299] | 1,15 ± 0,05 [1,10..1,25] |
| H | YEAR 2026 (entry 2026-01→09) | 361 ± 29 [311..395] | 40 ± 4 [34..47] | 28 ± 3 [21..32] | 28 ± 5 [21..37] | 499 ± 36 [440..534] | 136 ± 17 [109..169] | 106 ± 15 [79..131] | 192 ± 28 [157..249] | 934 ± 43 [880..976] | 2,05 ± 0,08 [1,97..2,17] |

**E0 trên H (bucket, báo, không quyết)**: mean ΣPnL W9 = 13 586; seed > 0 = 8/8 ⇒ ĐẠT.


### Từng run

| cửa sổ | biến thể | seed | tag | md5 printDone | n | ΣPnL | maxDD MTM phút % (D: 2022–25) | Calmar MTM | jar |
|---|---|---|---|---|---|---|---|---|---|
| D | bucket thực | 42 | `ec-s-s42` | `d1d804be` | 3529 | 106 622 | -22,22 | 1,622 | 246087fb |
| D | bucket thực | 7 | `ecm-d-s7` | `2815cfa4` | 3542 | 100 802 | -22,79 | 1,528 | 246087fb |
| D | bucket thực | 13 | `ecm-d-s13` | `42865f11` | 3549 | 109 832 | -23,01 | 1,608 | 246087fb |
| D | bucket thực | 21 | `ecm-d-s21` | `eaf41b0a` | 3546 | 104 396 | -24,67 | 1,443 | 246087fb |
| D | bucket thực | 99 | `ecm-d-s99` | `5524f4fd` | 3657 | 109 045 | -21,46 | 1,727 | 246087fb |
| D | bucket thực | 123 | `ecm-d-s123` | `55605415` | 3558 | 99 661 | -23,21 | 1,492 | 246087fb |
| D | bucket thực | 777 | `ecm-d-s777` | `d768da3f` | 3440 | 111 203 | -20,14 | 1,881 | 246087fb |
| D | bucket thực | 2024 | `ecm-d-s2024` | `0a3ee036` | 3526 | 101 305 | -23,25 | 1,533 | 246087fb |
| D | phí gốc | 42 | `gqsf-a1` | `ad26fd55` | 3541 | 111 079 | -22,21 | 1,661 | 0944841c |
| D | phí gốc | 7 | `gqsf-s7` | `eca3d5da` | 3557 | 104 828 | -22,75 | 1,565 | 0944841c |
| D | phí gốc | 13 | `gqsf-s13` | `6cde6eb3` | 3554 | 113 146 | -22,92 | 1,642 | 0944841c |
| D | phí gốc | 21 | `gqsf-s21` | `c3b73549` | 3550 | 106 766 | -24,67 | 1,453 | 0944841c |
| D | phí gốc | 99 | `gqsf-s99` | `bda37221` | 3666 | 116 012 | -21,41 | 1,790 | 0944841c |
| D | phí gốc | 123 | `gqsf-s123` | `74c83292` | 3565 | 104 379 | -23,17 | 1,536 | 0944841c |
| D | phí gốc | 777 | `gqsf-s777` | `bf91d854` | 3464 | 118 362 | -20,05 | 1,961 | 0944841c |
| D | phí gốc | 2024 | `gqsf-s2024` | `1b2af031` | 3514 | 105 806 | -23,19 | 1,572 | 0944841c |
| D | stress 1,675% | 42 | `nsel-nen-s42` | `3d79927b` | 3517 | 70 640 | -22,27 | 1,239 | b7c89f09 |
| D | stress 1,675% | 7 | `nsel-nen-s7` | `50463d96` | 3508 | 65 653 | -22,84 | 1,161 | b7c89f09 |
| D | stress 1,675% | 13 | `nsel-nen-s13` | `e74bb158` | 3529 | 73 609 | -23,00 | 1,265 | b7c89f09 |
| D | stress 1,675% | 21 | `nsel-nen-s21` | `a218908c` | 3529 | 66 010 | -24,69 | 1,060 | b7c89f09 |
| D | stress 1,675% | 99 | `nsel-nen-s99` | `344014de` | 3628 | 74 969 | -21,59 | 1,377 | b7c89f09 |
| D | stress 1,675% | 123 | `nsel-nen-s123` | `13643b25` | 3515 | 63 991 | -23,28 | 1,103 | b7c89f09 |
| D | stress 1,675% | 777 | `nsel-nen-s777` | `8044621b` | 3452 | 72 449 | -21,87 | 1,318 | b7c89f09 |
| D | stress 1,675% | 2024 | `nsel-nen-s2024` | `752f6e75` | 3548 | 68 238 | -23,33 | 1,175 | b7c89f09 |
| H | bucket thực | 42 | `ecm-h-s42` | `1942efa8` | 406 | 15 700 | -5,15 | 2,931 | 246087fb |
| H | bucket thực | 7 | `ecm-h-s7` | `fd36a725` | 490 | 12 127 | -5,72 | 2,119 | 246087fb |
| H | bucket thực | 13 | `ecm-h-s13` | `12ad6a5b` | 456 | 15 977 | -6,21 | 2,422 | 246087fb |
| H | bucket thực | 21 | `ecm-h-s21` | `fab4711a` | 485 | 14 620 | -5,29 | 2,700 | 246087fb |
| H | bucket thực | 99 | `ecm-h-s99` | `dfd9d4cb` | 430 | 18 633 | -5,62 | 3,147 | 246087fb |
| H | bucket thực | 123 | `ecm-h-s123` | `0d0c0f2a` | 446 | 12 849 | -5,08 | 2,555 | 246087fb |
| H | bucket thực | 777 | `ecm-h-s777` | `59b81e03` | 452 | 7 347 | -6,81 | 0,995 | 246087fb |
| H | bucket thực | 2024 | `ecm-h-s2024` | `d647c8db` | 487 | 11 435 | -6,03 | 1,887 | 246087fb |
| H | phí gốc | 42 | `ho4-k24-b-s42` | `7cc8864c` | 403 | 17 196 | -5,14 | 3,124 | b7c89f09 |
| H | phí gốc | 7 | `ho4-k24-b-s7` | `c09b8ba5` | 488 | 13 438 | -5,71 | 2,289 | b7c89f09 |
| H | phí gốc | 13 | `ho4-k24-b-s13` | `d10d96e1` | 453 | 16 799 | -6,05 | 2,553 | b7c89f09 |
| H | phí gốc | 21 | `ho4-k24-b-s21` | `ca27d690` | 481 | 16 052 | -5,62 | 2,745 | b7c89f09 |
| H | phí gốc | 99 | `ho4-k24-b-s99` | `9fe76b2d` | 427 | 19 001 | -5,61 | 3,063 | b7c89f09 |
| H | phí gốc | 123 | `ho4-k24-b-s123` | `c9f97a82` | 447 | 14 648 | -5,18 | 2,763 | b7c89f09 |
| H | phí gốc | 777 | `ho4-k24-b-s777` | `e021060a` | 452 | 8 700 | -6,67 | 1,150 | b7c89f09 |
| H | phí gốc | 2024 | `ho4-k24-b-s2024` | `5c0476bd` | 486 | 12 225 | -5,99 | 1,967 | b7c89f09 |
| H | stress 1,675% | 42 | `ho4-k24-s-s42` | `6989a312` | 406 | 11 247 | -5,49 | 2,641 | b7c89f09 |
| H | stress 1,675% | 7 | `ho4-k24-s-s7` | `a8f20075` | 482 | 7 898 | -5,89 | 1,807 | b7c89f09 |
| H | stress 1,675% | 13 | `ho4-k24-s-s13` | `b4d3b21b` | 449 | 10 266 | -6,01 | 2,137 | b7c89f09 |
| H | stress 1,675% | 21 | `ho4-k24-s-s21` | `903dfb7e` | 482 | 10 724 | -5,53 | 2,615 | b7c89f09 |
| H | stress 1,675% | 99 | `ho4-k24-s-s99` | `f65bce89` | 445 | 10 677 | -5,70 | 2,317 | b7c89f09 |
| H | stress 1,675% | 123 | `ho4-k24-s-s123` | `8019a46b` | 441 | 9 519 | -5,13 | 2,546 | b7c89f09 |
| H | stress 1,675% | 777 | `ho4-k24-s-s777` | `9948b2b5` | 446 | 5 695 | -6,74 | 1,061 | b7c89f09 |
| H | stress 1,675% | 2024 | `ho4-k24-s-s2024` | `cf8ea475` | 484 | 8 070 | -5,70 | 1,858 | b7c89f09 |

### Tự kiểm scorer: 323/323 đạt

Phụ: maxDD MTM phút − maxDD MTM ngày 07:00 (cùng run, cùng cửa sổ): H W9 -1,71 ± 0,89 [-3,47..-0,76] pp; D 2022–25 -6,90 ± 0,60 [-8,60..-6,25] pp — MTM ngày đánh giá THẤP DD, chỉ dùng cho 2021H2.


## 6. Tái lập
```
cd ~/claude_master/1013/ecm
setsid nohup python3 ecm_q.py > ecm_q.out 2>&1 < /dev/null &     # 15 kernel, state.json + res/<tag>.json (12 check)
python3 ecm_mtm_h.py ecm_mtm_h.json <24 tag H>                    # MTM phút Vision (ho4_score_a)
python3 ecm_mtm_d.py ecm_mtm_d.json <24 tag D>                    # MTM phút ticker sim (nsel_score_b)
python3 ecm_score.py ecm_score.json ecm_score.md                  # bảng + 323 tự kiểm
python3 ecm_overlap.py ecm_overlap.json                           # chẩn đoán phụ
```
md5: ecm_score.json 0894561cb38793dbbfb4f3609d2f5198 (= RESULT_ENTRYCOST_MEASURE.json) · ecm_mtm_d.json 518b0833 · ecm_mtm_h.json 0ef166ee · ecm_overlap.json 52c837f4. Script: ecm_q.py e4f783f7 · ecm_mtm_d.py 08b7c5e3 · ecm_mtm_h.py 2425a1ab · ecm_score.py 23378016 · ecm_overlap.py 6ee6cdc1.
