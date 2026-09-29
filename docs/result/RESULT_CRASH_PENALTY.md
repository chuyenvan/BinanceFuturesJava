# RESULT_CRASH_PENALTY — ĐỘ BỀN R4 & G2 khi PHẠT THẬT giá vào leg "sập" (E2)

Ngày: **2026-09-29**. Pre-reg: **`docs/prereg/PREREG_CRASH_PENALTY.md`** (commit **`cca1e7ed`**, chốt **TRƯỚC** khi
chạy; **KHÔNG sửa thiết kế** sau khi thấy số). Driver: `research/analysis/reset_rule_crashpen_driver.py` (commit
**`fda12ae2`**). JSON: `docs/result/crash_penalty.json`. Code §2: commit **`efd85d6d`** (worktree RIÊNG
`/home/ubuntu/wt_crashpen`, base `2b4dcbd3` + GDV2 + key `SIM_CRASH_ENTRY_PENALTY`), jar sha256
**`d944bea5f90a3c2cc4fa5bd45ee488b168459a9782719e909f5eb11f3c95ce89`**.

**Tuân thủ (cứng):** sim **TRÊN KAGGLE** (bundle `sim-x1-2021-bundle`, `TICKER_SOURCE=file`, dataset jar
`sim-jar-crashpen`, `sim_end_date=20251231`) · **0 sim Oracle** · DEV ≤ **2025-12-30** (2026 = HOLDOUT, KHÔNG dùng)
· **KHÔNG chạm** 242/production/ONNX/LIVE · thuần Kaggle + Python offline · `nice -n 10`.

Nền chung mọi arm: `profiles/r4_kg0_k16_f015_g155.properties` (KEEPLEG0, nhịp 1′, CONC_CAP 15 %, phí base
0,1116 %/vòng). **G2** = R4 + `SIM_GATE_ROLLING_MODE=ratio`, `SIM_GATE_ROLLING_PCT=0.99995083`, `SIM_GATE_ROLLING_DAYS=90`.
**Phạt** áp vào **giá vào** của leg entry khi nến **quyết định** có `bar_ret = (close−open)/open ≤ −1 %` (đúng mốc sim,
KHÔNG dùng nến chứa fill).

---

## 0. KẾT LUẬN (một dòng)

> **KHÔNG arm nào còn "sống" (PASS cả 4 tầng §9) ở cả hai mức phạt.** `R4` mất **T4** ngay ở mức điểm (`+0,69 %`, Calmar
> 1,498 < 0,90×1,676 = 1,509) và mất sâu hơn ở biên trên (`+1,50 %`, Calmar 1,348; UW vọt lên **222** ngày, sát trần 250).
> `G2` mất **T3** ở cả hai mức (TSloss% `+2,81 pp` @điểm, `+3,76 pp` @biên trên — vượt trần `+2,5 pp`) và **thêm T4** ở
> biên trên (Calmar 1,504 < 1,509). ⇒ **R4 KHÔNG bền ở biên trên CI95** (§7.2 = FALSE) và **G2 NHẠY hơn R4** (§7.3, G2
> FAIL ở tầng sớm hơn/hụt nhiều hơn). Đây là **stress giả định** (n=27 nhóm sập, thiếu power), **KHÔNG rescore, KHÔNG
> chọn/tune tham số**.

---

## 1. CỔNG KIỂM HỢP LỆ (parity) — ĐẠT

| cổng | yêu cầu (jar MỚI chạy trên Kaggle) | đo được | kết |
|---|---|---|---|
| **Parity R4** (`cp-r4-parity`, key phạt vắng) | `md5(printDone)=06fd6e9aa9c916945b2cf12310b337ff`, n 2027, eq 104 489 | md5 **06fd6e9aa9c916945b2cf12310b337ff**, n **2027**, eq **104 489** | **PASS** |
| **Parity G2** (`cp-g2-parity`) | `md5(printDone)=853aaa086be7d2d811162879df0653f6`, n 2509, eq 131 374 | md5 **853aaa086be7d2d811162879df0653f6**, n **2509**, eq **131 374** | **PASS** |

⇒ Key `SIM_CRASH_ENTRY_PENALTY` vắng ⇒ **byte-identical** (không dịch bit nào); `[CRASH-PENALTY]` chỉ in khi penalty > 0.

## 2. BẢNG CHÍNH — 4 TẦNG §9 (baseline = **R4 gốc** `cp-r4-parity`)

`k=4` ⇒ `inflate = √(2·ln 4) = 1,6651`. As-is: phí base + phạt đã nằm TRONG artifact (qua giá vào), KHÔNG điều chỉnh thêm.
Calmar_MTM = CAGR / |maxDD phút|. Ngưỡng T4 = `0,90 × Calmar_R4 = 1,5087`.

| arm | n | equity | CAGR % | ddPhút % | UW (ngày) | q* % | top-1 % | conc % | Calmar_MTM | T1 | T2 | T3 | T4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **cp-r4-parity** (R4 gốc) | 2 027 | 104 489 | 27,53 | −16,42 | 164,7 | 21,7 | 19,38 | 5,30 | **1,676** | PASS | PASS | ref | ref |
| **cp-g2-parity** (G2 gốc) | 2 509 | 131 374 | 34,18 | −17,99 | 128,9 | 23,9 | 17,46 | 4,09 | **1,900** | PASS | PASS | PASS | PASS |
| `cp-r4-p069` (R4 @0,69 %) | 1 992 | 96 721 | 25,35 | −16,93 | 164,7 | 20,4 | 19,10 | 5,13 | 1,498 | PASS | PASS | PASS | **FAIL** |
| `cp-r4-p150` (R4 @1,50 %) | 1 969 | 90 335 | 23,46 | −17,40 | **222,1** | 18,3 | 20,33 | 5,10 | 1,348 | PASS | PASS | PASS | **FAIL** |
| `cp-g2-p069` (G2 @0,69 %) | 2 491 | 118 176 | 31,06 | −18,03 | 128,9 | 20,7 | 18,31 | 4,01 | 1,723 | PASS | PASS | **FAIL** | PASS |
| `cp-g2-p150` (G2 @1,50 %) | 2 493 | 105 542 | 27,81 | −18,49 | **221,4** | 17,8 | 19,65 | 3,98 | 1,504 | PASS | PASS | **FAIL** | **FAIL** |

**Đọc FAIL từng tầng (chi tiết số trong `crash_penalty.json`):**

- **T1 (rào rủi ro) — PASS tất cả.** maxDD phút/năm ≤ 40 % (xấu nhất −18,49 %), UW ≤ 250 (max 222,1), qmin ≥ −20 %
  (xấu nhất −1,74 %), **0 năm âm** mọi arm, conc ≤ 15 % (max 5,13 %). Nhưng UW **cà 222 ngày** ở cả hai arm `p150`
  (so 164,7 của R4 gốc) ⇒ *áp lực trần 250* rõ hơn hẳn khi phạt nặng.
- **T2 (độ bền) — PASS tất cả.** q* ≥ 15 % (min 17,8) · top-1 % ≤ 25 (max 20,33).
- **T3 (non-inferiority vs R4 gốc).** `win%`: R4 vars trong trần (`−0,54 pp` / `−1,31 pp`); G2 vars vượt/tiệm cận
  (`−1,57 pp` / **`−2,40 pp`** < −2,0). `TSloss%`: R4 vars `+0,47 pp` / `+1,28 pp` (trong trần +2,5);
  **G2 vars `+2,81 pp` / `+3,76 pp` VƯỢT trần** ⇒ **G2 FAIL T3 ở cả hai mức**.
- **T4 (mục tiêu vs R4 gốc).** Calmar ≥ 1,5087: R4 `1,498` (−0,70 %) và `1,348` (−10,6 %) ⇒ **FAIL**; G2 `1,723` PASS,
  `1,504` **hụt 0,0044 (−0,3 %) ⇒ FAIL sát nút**. conc ≤ R4 (5,30) đạt ở mọi arm.

**Hệ quả then chốt:** R4 mất T4 **ngay ở mức điểm** (`0,0069`) — biên rất mỏng (Calmar còn **89,3 %** mức nền). G2 có
mức Calmar nền cao hơn (1,900 vs 1,676) nên **vẫn qua T4** ở mức điểm, nhưng **mất T3** (TSloss% vượt trần) — tức cái mất
của G2 nằm ở **chất lượng lệnh (SL rate)**, không phải ở Calmar.

## 3. ÁP LUẬT KẾT LUẬN (§7) — chốt TRƯỚC, không đổi sau khi thấy số

**(1) Edge "sống" ở mức phạt P ⇔ arm PASS cả 4 tầng so R4 gốc.** → **KHÔNG** arm nào sống ở cả hai mức:
- `+0,69 %`: R4 FAIL T4 (Calmar 1,498 < 1,509) · G2 FAIL T3 (TSloss +2,81 pp > +2,5).
- `+1,50 %`: R4 FAIL T4 (1,348) · G2 FAIL T3 (win −2,40 pp, TSloss +3,76 pp) **và** T4 (1,504 < 1,509).

**(2) R4 bền ⇔ R4 @1,50 % vẫn PASS 4 tầng.** → **FALSE**: Calmar 1,348 vs mức tối thiểu 1,509; UW 222 ngày. R4 chỉ
"sống sót" tới mức điểm nếu nới đúng 1 tầng (T4), và bản thân mức điểm đã **hụt T4 0,7 %** — coi như **biên CI95 là quá
sức** cho R4.

**(3) G2 nhạy hơn R4 ⇔ ΔCalmar(G2@P) < ΔCalmar(R4@P) cùng P, hoặc G2 FAIL 4 tầng trước R4.**

| mức phạt | ΔCalmar R4 (so nền) | ΔCalmar G2 (so nền) | tầng FAIL | kết |
|---|---|---|---|---|
| `+0,69 %` | **−0,179** | −0,177 | R4 → T4 · G2 → **T3** | G2 FAIL **tầng sớm hơn** ⇒ **G2 nhạy hơn** |
| `+1,50 %` | −0,328 | **−0,396** | R4 → T4 · G2 → T3 **+** T4 | ΔG2 < ΔR4 **và** FAIL nhiều hơn ⇒ **G2 nhạy hơn** |

⇒ **KẾT LUẬN §7.3: G2 NHẠY hơn R4** với cùng mức phạt (đúng cả hai nhánh điều kiện ở mức biên trên; ở mức điểm là do
G2 sụp ở tầng sớm hơn). Lưu ý G2 **vẫn có Calmar/tổng ROI tuyệt đối cao hơn R4** ở mọi mức — "nhạy hơn" nghĩa là
**độ dốc suy giảm lớn hơn**, không phải kém hơn tuyệt đối.

## 4. BẢNG NĂM (§5) + SỐ LEG BỊ PHẠT/NĂM (§6)

Năm (calendar, GMT+7). `n` = số leg VÀO · `ROI %` = return equity năm · `TSloss %` = % leg vào năm đó kết thúc
`STOP_LOSS_DONE` · `maxDD %` = maxDD MTM phút trong năm · `#phạt` = số leg bị phạt trong năm (log `[CRASH-PENALTY] byYear`).
Nền `R4`/`G2` không có `#phạt` (key vắng).

**R4 gốc (`cp-r4-parity`)** — Calmar 1,676 · n 2 027

| năm | n | ROI % | TSloss % | maxDD % |
|---|---|---|---|---|
| 2021 | 247 | 8,59 | 14,98 | −11,58 |
| 2022 | 357 | 17,85 | 15,13 | −13,08 |
| 2023 | 224 | 29,63 | 14,73 | −3,83 |
| 2024 | 580 | 40,53 | 11,38 | −11,00 |
| 2025 | 619 | 28,06 | 10,18 | −16,42 |

**R4 @0,69 % (`cp-r4-p069`)** — Calmar 1,498 · n 1 992 · **#phạt 927** {2021:109, 2022:166, 2023:133, **2024:275, 2025:244**}

| năm | n | ROI % | TSloss % | maxDD % | #phạt |
|---|---|---|---|---|---|
| 2021 | 244 | 7,95 | 15,57 | −11,67 | 109 |
| 2022 | 347 | 16,52 | 15,56 | −13,02 | 166 |
| 2023 | 221 | 27,90 | 14,48 | −3,83 | 133 |
| 2024 | 568 | **37,49** | 12,32 | −11,46 | **275** |
| 2025 | 612 | **24,94** | 10,46 | −16,93 | 244 |

**R4 @1,50 % (`cp-r4-p150`)** — Calmar 1,348 · n 1 969 · **#phạt 920** {2021:108, 2022:168, 2023:131, **2024:275, 2025:238**}

| năm | n | ROI % | TSloss % | maxDD % | #phạt |
|---|---|---|---|---|---|
| 2021 | 241 | 6,17 | 17,01 | −11,77 | 108 |
| 2022 | 352 | 17,35 | 15,34 | −12,55 | 168 |
| 2023 | 219 | 28,56 | 15,53 | −3,83 | 131 |
| 2024 | 559 | **31,84** | 13,42 | −11,59 | **275** |
| 2025 | 598 | **22,23** | 11,20 | −17,40 | 238 |

**G2 gốc (`cp-g2-parity`)** — Calmar 1,900 · n 2 509

| năm | n | ROI % | TSloss % | maxDD % |
|---|---|---|---|---|
| 2021 | 435 | 18,36 | 16,32 | −11,66 |
| 2022 | 423 | 10,26 | 20,09 | −17,99 |
| 2023 | 529 | 51,72 | 17,20 | −4,35 |
| 2024 | 591 | 43,52 | 11,34 | −10,96 |
| 2025 | 531 | 32,09 | 7,72 | −15,52 |

**G2 @0,69 % (`cp-g2-p069`)** — Calmar 1,723 · n 2 491 · **#phạt 1106** {2021:172, 2022:202, 2023:226, **2024:267, 2025:239**}

| năm | n | ROI % | TSloss % | maxDD % | #phạt |
|---|---|---|---|---|---|
| 2021 | 425 | 14,99 | 17,41 | −11,73 | 172 |
| 2022 | 424 | 9,33 | 20,75 | −18,03 | 202 |
| 2023 | 525 | **47,54** | 18,86 | −4,76 | 226 |
| 2024 | 591 | **39,89** | 12,69 | −11,46 | **267** |
| 2025 | 526 | **30,13** | 8,56 | −16,52 | 239 |

**G2 @1,50 % (`cp-g2-p150`)** — Calmar 1,504 · n 2 493 · **#phạt 1103** {2021:173, 2022:199, 2023:231, **2024:266, 2025:234**}

| năm | n | ROI % | TSloss % | maxDD % | #phạt |
|---|---|---|---|---|---|
| 2021 | 419 | 13,26 | 18,38 | −11,85 | 173 |
| 2022 | 423 | 7,45 | 21,75 | −18,13 | 199 |
| 2023 | 531 | **43,03** | 19,77 | −5,38 | 231 |
| 2024 | 587 | **35,43** | 13,46 | −11,59 | **266** |
| 2025 | 533 | **27,92** | 9,76 | −17,15 | 234 |

**Đọc bảng năm:**

- **Năm nhạy phạt nhất = 2024** (số leg sập cao nhất: R4 **275**, G2 **266–267**; kế đó 2025). ROI 2024 sụt mạnh nhất:
  R4 40,53 → **37,49** → **31,84**; G2 43,52 → **39,89** → **35,43**. Năm 2023 cũng sụt (R4 29,63→27,90→28,56;
  G2 51,72→47,54→43,03) do n nhiều + nhiều lệnh sập.
- **TSloss% xấu đi theo mức phạt** rõ ở G2 (2025: 7,72 → 8,56 → 9,76; 2023: 17,20 → 18,86 → 19,77); R4 TSloss%
  biến động nhẹ hơn, ít nhạy hơn.
- **#phạt ≈ 44–47 % số leg VÀO** ở mọi arm (chiến lược vào nhiều trên nến đỏ 1m) ⇒ phạt "đều 1 mức" chạm ~nửa sổ lệnh,
  nhưng vì mức phạt nhỏ (0,69 %/1,50 %) nên tác động tổng ~vài pp ROI/năm.

## 5. HẠN CHẾ (khai trước, đúng §8 pre-reg)

1. `n=27` nhóm sập (`RESULT_LATENCY_FILL`) ⇒ **CI thiếu power**; vòng này chỉ là **stress giả định**, KHÔNG đo lại
   chi phí thật, KHÔNG rescore.
2. Phạt **đều 1 mức** cho mọi leg sập (không phân biệt độ sâu `bar_ret`); xấp xỉ đã khai.
3. `quantity = budget/entry` giảm khi vào đắt hơn ⇒ hiệu ứng bậc 2 (đúng margin cố định); đây là một phần lý do `n`/
   đường equity dịch (R4 2027→1992/1969), không chỉ do bỏ lệnh.
4. MTM phút chỉ có giá đóng nến 1m (cận dưới); 1 quan sát lịch sử, không CI.
5. Kết luận nhạy cảm chỉ cho **cặp (R4, G2)** này; G2 = GDV2 W90 nói riêng.
6. **T4 hụt sát nút** (R4@p069 −0,70 %; G2@p150 −0,3 %) ⇒ đọc như "ngưỡng 0,90×Calmar" nhạy; không nên coi là "FAIL
   chắc chắn" mà là "mất biên an toàn". Quyết định vận hành (nếu có) phải dựa trên §7, KHÔNG tune tham số từ task này.
7. `efd85d6d` (code §2) nằm trong **worktree riêng** `/home/ubuntu/wt_crashpen`, **chưa** trên nhánh `module`; tái lập cần
   worktree + dataset jar `sim-jar-crashpen`. (Việc port code sang `module` là task riêng, như đã làm với GDV2/E1.)

## 6. TÁI LẬP

```bash
# jar: worktree wt_crashpen @ efd85d6d -> mvn -o package -> dataset sim-jar-crashpen (sha d944bea5…)
# 6 kernel (đã chạy, xem PREREG §9):
#   cp-r4-parity cp-g2-parity cp-r4-p069 cp-r4-p150 cp-g2-p069 cp-g2-p150
python3 research/analysis/reset_rule_crashpen_driver.py --json docs/result/crash_penalty.json
# -> PARITY_R4=True PARITY_G2=True ; JSON: docs/result/crash_penalty.json
```

Artefact Kaggle (output): `/home/ubuntu/kaggle_sim/out/cp-*/{storage/printDone.csv, logs/sim.out, result.json}`.
