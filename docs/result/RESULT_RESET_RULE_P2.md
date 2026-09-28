# RESULT_RESET_RULE_P2 — SIM KAGGLE k=5 (R0–R4, nhịp 1') @`base 0,112` và `stress 0,150` (%/vòng)

Ngày: **2026-09-29** (D3, `PLAN_OPENCLAW_ADDENDUM_20260928.md` §D3). Pre-reg: **`docs/prereg/PREREG_RESET_RULE_P2.md`**
(**commit `45c285d`**, chốt **TRƯỚC**; sau đó **không sửa thiết kế**). Công cụ chấm: `research/analysis/reset_rule_score.py`
(D2, **dùng lại nguyên**) qua driver mỏng `research/analysis/reset_rule_p2_driver.py`. JSON: `docs/result/reset_rule_p2.json`.

**Tuân thủ:** sim chạy **TRÊN KAGGLE** (bundle `chuyendinh/sim-x1-2021-bundle`, `TICKER_SOURCE=file`) · **KHÔNG** chạy Java/sim
trên Oracle · **KHÔNG** sửa Java (mọi knob đã có) · **KHÔNG** chạm production/`242`/ONNX/LIVE · **KHÔNG** push file dữ liệu ·
**DEV ≤ 2025-12-31** (mốc cuối `20251230`) · output tool nhỏ · **0 run/0 train trên Oracle**.

---

## 0. KẾT LUẬN (5 dòng)

1. **Parity PASS:** `p2-r0-legacy` (`KEEPLEG0 + CONC_CAP 15%`, cost legacy) **md5 `99e42b75`**, `n 1085`, equity `103083`
   — **byte-identical** với `kg0-g170`/`FG_KEEPLEG0` (neo Kaggle của cửa sổ T170).
2. **@base:** T1 5/5 · T2 5/5 · T3 4/5 · T4 **1/5**. **@stress:** y hệt (**T1 5/5 · T2 5/5 · T3 4/5 · T4 1/5**) — hạ/đổi phí **KHÔNG lật** trạng thái tầng nào.
3. **CÓ ĐÚNG 1 ARM QUA CẢ 4 TẦNG: `R4`** (`SIM_F_BASE ×0,5`, `K=16`, `gate 1.55`) — qua cả `@base` và `@stress`;
   `Calmar_MTM` 1,676 / 1,655 ≥ `B*` 1,661 / 1,643; `n = 2 027 = 1,87× B*`; `conc 5,30 % ≤ 7,11 %`.
4. Vì luật kết luận = "ứng viên qua cả 4 tầng ⇒ chọn `Calmar_MTM` cao nhất", **`R4` là ứng viên DUY NHẤT**
   ⇒ **KHÔNG giữ nguyên `B*`**; nhưng biên `Calmar` của `R4` trên `B*` **rất mỏng (+0,7…+0,95 %)** ⇒ cần Phase 3/4 trước khi tin.
5. Dự báo MASTER **LỆCH 2/3**: `R2` KHÔNG vượt `UW 250` (222,2 ngày) mà **FAIL tầng 3**; `R4` **KHÔNG** FAIL tầng 3
   mà **PASS cả 4 tầng**. Dự báo `R1/R3` qua T1–T3 + `n ×1,4–2,2` + `Calmar ≈ B* ±15 %` thì **KHỚP**.

## 1. THIẾT LẬP (11 run, 0 run trên Oracle)

Nền chung: `KEEPLEG0` (`DCA_GRID_WEIGHTS=1,1,1,1`, `DCA_GRID_SCALE=6.0`) + `CONC_CAP_PERCOIN_ENABLED=1`/`PCT=0.15`,
nhịp 1' (`SIM_ENTRY_SAMPLE_MIN=1` = no-op). Profile `x1_gs_t170`; cửa sổ `20210701..20251230`; `jar_sha256 2c2f8aef…`
(**giống hệt** `kg0-g170`/`kg0-cap` ⇒ cùng binary). 5 arm × 2 mức phí + 1 run R0 legacy:

| tag (kernel `chuyendinh/sim-…`) | arm | cost | size | K | gate | equity | n | md5 `printDone` |
|---|---|---|---|---|---|---|---|---|
| `p2-r0-legacy` | R0 | legacy | 0.03 | 8 | 1.70 | 103 083 | 1 085 | **`99e42b75`** |
| `p2-r0-base` | R0 | base | 0.03 | 8 | 1.70 | 126 108 | 1 086 | `d297ce6b` |
| `p2-r0-stress` | R0 | stress | 0.03 | 8 | 1.70 | 124 685 | 1 086 | `d4725990` |
| `p2-r1-base` | R1 | base | 0.015 | 16 | 1.70 | 98 153 | 1 739 | `899ba89d` |
| `p2-r1-stress` | R1 | stress | 0.015 | 16 | 1.70 | 97 271 | 1 739 | `5fee7400` |
| `p2-r2-base` | R2 | base | 0.015 | 32 | 1.70 | 112 414 | 2 876 | `16358da2` |
| `p2-r2-stress` | R2 | stress | 0.015 | 32 | 1.70 | 111 081 | 2 876 | `7a59f19f` |
| `p2-r3-base` | R3 | base | 0.0099 | 24 | 1.70 | 87 088 | 2 344 | `1b8f928f` |
| `p2-r3-stress` | R3 | stress | 0.0099 | 24 | 1.70 | 86 417 | 2 344 | `aee70072` |
| `p2-r4-base` | R4 | base | 0.015 | 16 | 1.55 | 104 489 | 2 027 | `06fd6e9a` |
| `p2-r4-stress` | R4 | stress | 0.015 | 16 | 1.55 | 103 351 | 2 027 | `84402b57` |

Chi phí: `total = RATE_FEE + 2·SLIPPAGE_RATE` (`Configs.java:901-902`) — `base` `0.000982+2·0.000067=0,1116 %/vòng`;
`stress` `0.000982+2·0.000259=0,1500 %/vòng`; `legacy` (không khai) `0,800 %/vòng`. **Không sửa Java.**

## 2. KIỂM HỢP LỆ (cổng DỪNG — PASS hết)

| kiểm | kết quả |
|---|---|
| **Parity R0 @legacy** | `md5 = 99e42b75` · `n = 1085` · `equity = 103083` ⇒ **PASS** (= `kg0-g170`/`FG_KEEPLEG0`; `jar_sha256` khớp) |
| **Neo Kaggle cửa sổ T170** | `R0-legacy` equity **103 083** = neo file-source đã công bố (bản Oracle+file `X1_GS_T170_2021` = 111 070 cho `x1_gs_t170`; neo `c2b_min 60395` là profile/cửa sổ KHÁC, không dùng) |
| **`gross MAX < U_MAX 0,60`** | MAX `gross` = **55,9 %** (`R2`); `R0 51,0 · R1 48,0 · R3 46,7 · R4 48,0` ⇒ **không arm nào chạm `U_MAX`** ⇒ throttle `clamp(1−U/0,60)` ≈ 1, `U_MAX` **KHÔNG bind ngầm** |
| **Số lệnh bị chặn** | `[CONC-PC] SUMMARY blocked=0` ở **CẢ 11 run** (trần per-coin 15 % **không chặn leg nào**); `[GATE] n_cand/n_pass`: R0 `17,92 M/838` · R1 `35,70 M/1491` · R2 `70,95 M/2628` · R3 `53,38 M/2096` · R4 `35,49 M/1819` (K vs gate giải thích bậc `n_cand`) |

## 3. BẢNG 4 TẦNG @`base` = 0,112 %/vòng

`ddPhut` = maxDD **MTM phút** (năm xấu nhất = 2025; `= total` cho mọi arm ở đây). `Calmar_MTM = CAGR/|ddPhut|`.
`B* = R0` (mỗi mức phí tự so với R0 cùng mức). `inflate(k)` tầng 3 = **`inflate(5)=1,7941`**.

| arm | n | equity | CAGR % | ddPhut % | UW ngày | q* % | top-1 % | conc % | gross % | Calmar | T1 | T2 | T3 | T4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **R0** = `B*` | 1 086 | 126 108 | 32,97 | −19,85 | 147,2 | 24,2 | 20,72 | 7,11 | 51,0 | 1,661 | PASS | PASS | **ref** | ref |
| **R1** | 1 739 | 98 153 | 25,76 | −16,64 | 147,2 | 25,1 | 19,13 | 3,81 | 48,0 | 1,548 | PASS | PASS | PASS | **FAIL** |
| **R2** | 2 876 | 112 414 | 29,61 | −20,96 | 222,2 | 19,5 | 19,94 | 3,69 | 55,9 | 1,413 | PASS | PASS | **FAIL** | FAIL |
| **R3** | 2 344 | 87 088 | 22,46 | −14,84 | 164,7 | 25,3 | 16,94 | 2,70 | 46,7 | 1,514 | PASS | PASS | PASS | **FAIL** |
| **R4** | 2 027 | 104 489 | 27,53 | −16,42 | 164,7 | 21,7 | 19,38 | 5,30 | 48,0 | 1,676 | PASS | PASS | PASS | **PASS** |

**Lý do FAIL (bám rào):**
- **T3 `R2`**: `win% −2,40 pp` (< −2,0) **và** `TSloss% +3,04 pp` (> +2,5) — thêm lệnh hạng 17–32 ở nhịp 1' **làm loãng chất lượng**.
- **T4 `R1`/`R3`**: `Calmar_MTM 1,548 / 1,514 < 1,661 (B*)` — dù `n` đạt (1,60× / 2,16×) và `conc` tốt hơn `B*`.
- 0 năm âm · `qmin` ≥ −2,23 (≥ −20) · `q*` 19,5–25,3 (≥ 15) · `top-1` 16,9–20,7 (≤ 25) · bỏ top-3 episode > 0 (mọi arm) — **không vi phạm**.

## 4. BẢNG 4 TẦNG @`stress` = 0,150 %/vòng — **KHÁC `base` ở đâu?**

| arm | n | equity | CAGR % | ddPhut % | UW ngày | q* % | top-1 % | conc % | gross % | Calmar | T1 | T2 | T3 | T4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **R0** = `B*` | 1 086 | 124 685 | 32,63 | −19,86 | 147,2 | 23,9 | 20,86 | 7,12 | 51,0 | 1,643 | PASS | PASS | **ref** | ref |
| **R1** | 1 739 | 97 271 | 25,51 | −16,66 | 147,2 | 24,8 | 19,26 | 3,80 | 48,0 | 1,531 | PASS | PASS | PASS | **FAIL** |
| **R2** | 2 876 | 111 081 | 29,27 | −21,04 | 222,2 | 19,3 | 20,11 | 3,69 | 55,9 | 1,392 | PASS | PASS | **FAIL** | FAIL |
| **R3** | 2 344 | 86 417 | 22,25 | −14,88 | 222,1 | 24,9 | 17,07 | 2,70 | 46,7 | 1,496 | PASS | PASS | PASS | **FAIL** |
| **R4** | 2 027 | 103 351 | 27,22 | −16,44 | 222,1 | 21,4 | 19,54 | 5,30 | 48,0 | 1,655 | PASS | PASS | PASS | **PASS** |

**`@stress` ≠ `@base` ở đâu:** **KHÔNG một trạng thái tầng nào đổi** (T1 5/5 · T2 5/5 · T3 4/5 · T4 1/5, y hệt `base`).
Chỉ **độ lớn** đổi nhẹ: `equity` −0,5…−1,2 %; `CAGR` −0,23…−0,32 pp; `q*` −0,3…−0,5 pp; `ddPhut` +0,01…+0,04 pp;
`Calmar` −0,02…−0,03; `UW` **không đổi** ở R0/R1/R2, **tăng ở R3/R4** (164,7 → **222,1** ngày).
**Tầng 3 giống hệt byte** (`win%`/`TSloss%`/`mP|SM`/`mP|SL` trên **`profit` %** — bất biến chi phí, đúng như khai ở pre-reg §2).

## 5. ĐỐI CHIẾU DỰ BÁO MASTER GHI TRƯỚC (`PLAN…RESET` §Phase 2)

| # | dự báo | thực đo | kết |
|---|---|---|---|
| (2) | **R1/R3 qua T1–T3**, `n ×1,4–2,2`, `Calmar_MTM ≈ B* ±15 %` | R1: T1–T3 PASS, `n 1,60×`, Calmar 1,548 (−6,8 % vs 1,661) · R3: T1–T3 PASS, `n 2,16×`, Calmar 1,514 (−8,8 %) | **KHỚP** |
| (3) | **R2 rủi ro `UW > 250`** | `UW = 222,2` ngày (**< 250**) ⇒ T1 PASS; `R2` chết ở **T3** (`win% −2,40`/`TSloss% +3,04`) + T4 | **LỆCH** (cơ chế sai) |
| (4) | **R4 FAIL tầng 3** | `R4` **PASS cả T1–T4** (T3: `win% −1,53`/`TSloss% +2,17` trong trần) | **LỆCH** |

`Calmar_MTM` so `B*` (điểm): `@base` R1 −6,8 % · R2 −14,9 % · R3 −8,8 % · **R4 +0,95 %**;
`@stress` R1 −6,8 % · R2 −15,3 % · R3 −9,0 % · **R4 +0,71 %**. Tỷ lệ `n/B*` (1086): R1 1,60 · R2 2,65 · R3 2,16 · **R4 1,87**.

## 6. (5) CÓ ARM NÀO QUA CẢ 4 TẦNG KHÔNG?

**CÓ — đúng một arm: `R4`** (`×0,5`, `K=16`, `gate 1.55`), và **qua ở CẢ hai mức phí**:
`T1` (ddPhut −16,42 % ≤ 40; UW 164,7/222,1 ≤ 250; qmin −0,94; 0 năm âm; conc 5,30 ≤ 15; gross 48,0 ≤ 70) ·
`T2` (`q* 21,7`; `top-1 19,4`; bỏ top-3 episode > 0) ·
`T3` (non-inferior vs `R0`: `win% −1,53 pp`, `TSloss% +2,17 pp`, `mP|SM`/`mP|SL` trong CI) ·
`T4` (`Calmar 1,676/1,655 ≥ B* 1,661/1,643`; `n 2 027 ≥ 1 411,8`; `conc 5,30 ≤ 7,11`).
⇒ Theo **LUẬT KẾT LUẬN đã chốt**, **không giữ nguyên `B*`**; `R4` là ứng viên duy nhất qua cả 4 tầng
(nên cũng tự động là "Calmar cao nhất trong nhóm qua").

**CẢNH BÁO (không tự sửa luật):** biên `R4 > B*` ở T4 **rất mỏng** (`Calmar +0,95 % @base`, `+0,71 % @stress`);
`R4` còn bị `gate 1.55` **nới nhẹ** — đúng vùng D2 đã cảnh báo "1,55 vẫn non-inferior nhưng sát biên". ⇒ **chưa go-live**:
cần Phase 3 (episode jackknife/bootstrap/episode-cluster) + Phase 4 (HOLDOUT 2026 một lần) trước.

**MỨC NÀO BỎ + LÝ DO (theo số của lượt chấm này):**
- **BỎ `R2`** (`K=32`): **FAIL T3 cả 2 mức phí** (`win% −2,40 pp`, `TSloss% +3,04 pp`) — nhiều lệnh hơn nhưng **loãng chất lượng**;
  `Calmar` thấp nhất nhóm (1,39–1,41); biên giới `B*` đã hạ.
- **BỎ `R1`/`R3`**: qua **T1–T3** (chất lượng non-inferior, `n` 1,6–2,2×) nhưng **FAIL T4** vì `Calmar_MTM` **thấp hơn `B*` 6,8–9,0 %**
  ⇒ theo luật T4 (đòi ≥ `B*`) **không phải ứng viên**, dù là "nhiều cược nhỏ cùng chất lượng" đúng ý owner.
- **GIỮ `R4`** làm ứng viên (xem cảnh báo trên).
- **Không bỏ rào nào** ở lượt này: cả 6 rào T1, 3 rào T2 đều **không bind** với 5 arm (trừ T3/T4 có phân biệt thật).

## 7. HẠN CHẾ (khai rõ)

1. **`R4` thắng do T4 là điểm, không có significance**: `Calmar` hơn `B*` chưa tới 1 %; `n` lớn là thật nhưng `n_eff` (episode) chưa đo.
2. **`@stress` không đổi verdict** (đúng dự đoán D2: tầng 3 bất biến phí); `stress` chỉ kiểm bền độ lớn, không phải cổng mới.
3. **T3 chỉ 4 chỉ số `profit` (%)** — `meanP` bỏ (trùng đại số); `mP|SM`/`mP|SL` **0/5 FAIL** (CI đã nở `inflate(5)=1,79`).
4. **MTM phút** chỉ có giá **đóng nến 1m** (không tick/không `low`) ⇒ **cận dưới**; 1 quan sát lịch sử, không CI.
5. Công cụ D2 **dùng lại nguyên** — banner trong log vẫn in "RESET_RULE_P1" (hardcode); driver chỉ đặt `TAGS`, `B_STAR=R0-cùng-phí`,
   `k=5`; logic 4 tầng/CI/MTM **không đổi**. Không viết lại thuật toán.
6. Mọi số là **mô tả quá khứ DEV (≤ 2025-12-30)**, không phải cam kết forward; **chưa chạm HOLDOUT 2026**.

## 8. TÁI LẬP

```bash
cd /home/ubuntu/src/BinanceFuturesJava
# 11 run Kaggle (xem pre-reg §1-2); driver chấm lại:
python3 research/analysis/reset_rule_p2_driver.py base   --workers 4 --json /tmp/rr_p2_base.json   # ~6-8 phut (MTM phut)
python3 research/analysis/reset_rule_p2_driver.py stress --workers 4 --json /tmp/rr_p2_stress.json
# input: kaggle_sim/out/p2-{r0..r4}-{base,stress} + p2-r0-legacy (printDone.csv + logs/sim.out) + kaggle_data_hpo/ticker_*.bin.gz
```

## 9. COMMIT

- Pre-reg: **`45c285d`** (`docs/prereg/PREREG_RESET_RULE_P2.md`).
- Kết quả: commit này (`RESULT_RESET_RULE_P2.md` + `reset_rule_p2.json` + `reset_rule_p2_driver.py`).
- Kaggle: 11 kernel `chuyendinh/sim-p2-r{0..4}-{legacy,base,stress}` (+ `sim-p2-r4-stress`).
