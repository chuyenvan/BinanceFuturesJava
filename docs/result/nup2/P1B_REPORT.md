# NUP2 Pha 1b — chấm điểm & chọn factorial (2026-10-27)

Tag: `nup-{b1,b2,b3,b4,b5,a7}-{a1,s7,s21,s99}`. Trạng thái Kaggle: 23 DONE, 1 FAILED (`nup-a7-s21`).
Nguồn số: `docs/result/nup2/{runs.csv,arms_p1b.csv,frontier_p1b.csv,match_p1b.csv,notional_p1b.csv}`,
MTM `~/claude_master/nup2_wk/eq_parquet.npz` (missing = 0), extras `~/claude_master/nup2_wk/extras.csv`.
Mốc B0 dùng **4 seed a1/s7/s21/s99** (không dùng −22,833 của 8 seed).

## 1. A7 s21 FAILED — nguyên nhân

- `result.json`: `java_rc=-9`, `secs=7201.2` (> trần 7200), `n_trades=0`, `date_last=20210823`
  (mới chạy 2021-07-01 → 2021-08-23), log dừng ở `Update 20210823`.
- Đây là **timeout 7200 s**, không phải lỗi mạng/Kaggle tạm thời ⇒ theo TASK_nup2 §1:
  **A7 không đo được, loại khỏi tập ứng viên, KHÔNG rerun**.
- Dị dạng hạ tầng: kernel s21 dùng `jar_sha256=66740305…` — đúng sha của **jar A7 bản NUP cũ**
  (artefact `~/kaggle_sim/out/nup-a7-a1_NUPFAIL_1026`, cũng rc=-9 / 7200.8 s / cùng sha).
  3 seed a1/s7/s99 dùng đúng `ce4bcc17…`. Tức kernel s21 lấy phải version dataset cũ (bản chậm),
  không phải A7 chậm. Nếu MASTER muốn có đủ 4 seed thì phải pin dataset version rồi đo lại;
  tuy nhiên A7 3-seed đã có ΣPnL ×B0 = 0,792 < 0,80 nên **dù đo được cũng không lọt X/Y**.
- Số 3 seed A7 (để mô tả): xem bảng §2.

## 2. Bảng Pha 1b (median 4 seed; A7 = 3 seed)

| arm | seed | cụm/năm | ×B0 | ΣPnL | ×B0 | stress ×B0 | maxDD med | maxDD tệ | Calmar | G1 | G2 | G3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B0 | 4 | 721,1 | 1,000 | 112 466,8 | 1,000 | 1,000 | −22,47 | −24,66 | 1,716 | – | – | – |
| B1 | 4 | 724,1 | 1,004 | 48 349,3 | 0,430 | 0,431 | −15,50 | −17,57 | 1,437 | ✗ | ✗ | ✓ |
| B2 | 4 | 722,8 | 1,001 | 118 963,5 | 1,062 | 1,063 | −24,76 | −26,34 | 1,602 | ✗ | ✓ | ✓ |
| B3 | 4 | 723,9 | 1,001 | 82 288,2 | 0,726 | 0,728 | −19,86 | −22,53 | 1,598 | ✗ | ✗ | ✓ |
| B4 | 4 | 721,3 | 1,000 | 139 238,1 | 1,239 | 1,240 | −25,86 | −28,56 | 1,687 | ✗ | ✓ | ✓ |
| B5 | 4 | 721,1 | 1,000 | 112 466,8 | 1,000 | 1,000 | −22,47 | −24,66 | 1,716 | ✗ | ✓ | ✓ |
| A7 | 3 | 1 013,5 | 1,388 | 89 528,9 | 0,792 | 0,776 | −24,25 | −24,57 | 1,440 | ✓ | ✗ | ✓ |

- **B5 = bản sao B0 bit-exact về số** (mọi cột 1,000) ⇒ xác nhận `SIM_MIN_MOMENTUM_15M` không đi vào
  ngưỡng PREDICT ở chế độ ratio gate. Giữ làm dữ liệu, **không xếp hạng / không factorial / không Pha 3**.
- Không arm nào qua G1: các lever B không tăng số cụm (đều ×1,00); A7 (3 seed) qua G1 nhưng trượt G2.
- B1/B2/B3/B4 là lever đổi size/capacity nên "số cụm" gần như đứng yên; chúng là lever rủi ro/PnL,
  không phải lever tăng lệnh.

## 3. Notional leg0 & cảnh báo "lẫn size" (B1–B4, A7)

`notional_p1b.csv`. B0 leg0 median = 798,4 USD; cluster notional max = 7 195,9 USD.

| arm | leg0 median (USD) | ×B0 (median) | ×B0 (ghép cặp seed) | cluster notional max | ×B0 | DCA leg/cụm | skipFull |
|---|---|---|---|---|---|---|---|
| B1 | 374,4 | 0,469 | 0,470 | 1 865,5 | 0,259 | 65,5 | 0 |
| B2 | 808,4 | 1,013 | 1,006 | 10 658,8 | **1,481** | 186,5 | 17 973 |
| B3 | 591,4 | **0,741** | 0,745 | 3 950,6 | **0,549** | 102,5 | 0 |
| B4 | 980,0 | **1,227** | 1,227 | 8 628,2 | 1,199 | 64,0 | 0 |
| A7 | 667,8 | 0,836 | 0,814 | 5 992,9 | 0,833 | 75,0 | 921 |

- **B3 "lẫn size"**: lý thuyết 6 bậc đều ⇒ leg0 = 0,667×B0, đo được **0,741×**; đồng thời tổng notional
  cụm max chỉ **0,549×B0** (không giữ ngân sách/cụm). Vì leg0 to hơn lý thuyết nhưng tổng cụm lại nhỏ hơn,
  phần giảm DD/PnL của B3 chủ yếu là hiệu ứng size, **không phải nhịp DCA thuần**.
- **B4 "lẫn size"**: `SIM_U_MAX` ×1,25 làm throttle `1−U/U_MAX` nới ra ⇒ leg0 **1,227×B0**, không phải
  chỉ tăng capacity. PnL +23,9% và DD −3,4 pp đến từ size, không từ thêm lệnh (cụm/năm ×1,000).
  skipFull 0 (từ 80,5) — đúng hướng capacity.
- **B2 vi phạm validate ngân sách**: cluster notional max 1,481×B0 > trần 1,02×; DCA leg/cụm 3,06×;
  skipFull 17 973. "Nhịp DCA ×0,67" đã làm tăng mạnh ngân sách/cụm ⇒ không đúng ngữ nghĩa prereg.
- **B1** leg0 0,469× — nằm sát dưới biên validate [0,47; 0,53] (thiếu 0,001); PnL ×0,430.
- **A7** (3 seed): 1 277 leg tier2/cửa sổ (median), PnL tier2 median 4 700 USD
  (~3,7 USD/leg) — tier2 là lệnh biên, không kéo PnL.

## 4. Bảng E và chọn X/Y (PREREG §3, sửa theo MASTER_FIX §2)

Ứng viên lever đơn: A1, A2, A3, A5, A7, B1, B2, B3, B4. Loại A4/A6 (tổ hợp), B5 (không key),
A7 (không đo được). E = (cụm/năm ÷ B0 − 1) / max(0,5; |ΔmaxDD| pp).

| hạng | arm | cụm/năm | ×B0 | ΣPnL | ×B0 | maxDD med | ΔDD pp | hữu ích | E |
|---|---|---|---|---|---|---|---|---|---|
| 1 | A2 | 1 855,6 | 2,564 | 110 786 | 0,927 | −27,79 | −5,32 | ✓ | **0,294** |
| 2 | A1 | 1 330,8 | 1,839 | 89 413 | 0,789 | −25,86 | −3,39 | ✗ (PnL < 0,80) | 0,248 |
| 3 | A3 | 924,3 | 1,280 | 118 158 | 1,023 | −25,29 | −2,81 | ✓ | **0,099** |
| 4 | B1 | 724,1 | 1,004 | 48 349 | 0,430 | −15,50 | +6,97 | ✓ (luôn hữu ích) | 0,001 |
| 5 | B2 | 722,8 | 1,001 | 118 964 | 1,062 | −24,76 | −2,29 | ✗ | 0,001 |
| 6 | B3 | 723,9 | 1,001 | 82 288 | 0,726 | −19,86 | +2,62 | ✗ | 0,000 |
| 7 | B4 | 721,3 | 1,000 | 139 238 | 1,239 | −25,86 | −3,38 | ✗ | 0,000 |
| 8 | A5 | 721,1 | 1,000 | 112 467 | 1,000 | −22,47 | 0,00 | ✗ (NO-OP) | 0,000 |
| – | A7 | – | – | – | – | – | – | không đo được | – |

**X = A2** (gate 0,99985). **Y = A3** (TOPK 32). Hai key khác nhau (`SIM_GATE_ROLLING_PCT` vs `SELECTOR_RANK_TOPK`).
Factorial 2³ trên {X=A2, Y=A3, B1}: 4 ô mới `xy`, `xb1`, `yb1`, `xyb1` × 4 seed → `plan_f2b.json` (16 run).
**Chưa push f2b** (theo lệnh dừng).

## 5. Validate

- **V1 PASS**: 23/23 run `java_rc=1`, `ok=true`, `jar_sha256` đúng (B* = cc0f9d11; A7 = ce4bcc17),
  `prof_run.properties` chỉ khác B0 đúng tập key của arm (`extra`/`wrong` rỗng).
- **V2 PASS**: ΣPnL 16 quý 2022–25 = ΣPnL DEV_2022_25, lệch max 2,9e-11 USD; ΣPnL 4 năm = total, lệch 0.
- **V3 PASS**: MTM missing = 0 cho cả 23 tag; B0 4-seed maxDD median −22,474 trùng
  `quarterly_x14_by_seed.csv`.
- **V4 PASS**: `independent_check.py nup-b2-s7 s7` — độc lập csv/datetime: n_cl 2 887, n_leg 3 071,
  n_entry 657, PnL 117 055,73; diff = 0 / 0 / 0 / 9e-11.
- **V5 (NUP2)**:
  - B2/B3 "số leg DCA/cụm và tổng notional/cụm max ≤ 1,02×B0": B3 ✓ (0,549×), **B2 ✗ (1,481×)**.
  - B4 skipFull giảm: ✓ (0 vs 80,5).
  - B1 notional leg0 ∈ [0,47;0,53]: **0,469 — sát biên dưới, coi như đạt nhưng thiếu 0,001**.
- Bug sửa trong lúc chấm: join `tier2.csv` ↔ `printDone.csv` sai vì printDone lưu `sym` **không** có hậu tố
  `USDT`. Trước sửa `pnl_tier2 = 0`; sau sửa (strip `USDT$`) khớp 100% (A7 a1: 1 389 leg, 11 534 USD).
  Chỉ ảnh hưởng cột mô tả tier2 của A7, không ảnh hưởng xếp hạng/E.

## 6. Lệch thiết kế

1. A7 không đo được (s21 timeout; kernel lấy jar cũ 66740305 thay vì ce4bcc17) → loại khỏi ứng viên.
2. B5 chạy nhưng loại khỏi xếp hạng (prereg §2 + MASTER_FIX §1); số liệu xác nhận NO-OP.
3. B2 không đạt validate ngân sách/cụm (1,481× > 1,02×) dù vẫn được chấm E (không hữu ích).
4. B3/B4 lẫn size như cảnh báo §3; B3 leg0 đo được 0,741× (không phải 0,667× lý thuyết).
5. A2 dùng 4 seed (không dùng 8 seed Pha 2 NUP) theo MASTER_FIX §2; B0 DD mốc 4 seed = −22,474.
