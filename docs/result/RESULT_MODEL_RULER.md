# RESULT_MODEL_RULER — THƯỚC ĐÁNH GIÁ **MODEL** (ranker), tách khỏi thước HỆ THỐNG (sim)

**Ngày:** 2026-09-25 · **Nhánh:** `module` · **Trạng thái:** ĐO XONG (offline, KHÔNG train, KHÔNG sim)
**Tiền đăng ký (chốt TRƯỚC khi chạy):** `docs/prereg/PREREG_MODEL_RULER.md` — commit **`cc22253`**
**Code:** `research/analysis/model_ruler.py` · JSON đầy đủ: `/home/ubuntu/.cache/ruler_validate.json`
**Chi phí:** 0 quota Kaggle, 0 job Oracle — thuần Python offline (3 lần chạy RAW ~310 s/lần + 1 lần AGG vài giây)
**KHÔNG** chạm ONNX/`NUM_FEATURES`/`extractFeatures45`/`shadow_c3` · **KHÔNG** chạm 2026/`HoldoutSeal` · **KHÔNG** push

---

## 0. TRẢ LỜI NGẮN

1. **Đã xây được thước model tách khỏi thước hệ thống**: `research/analysis/model_ruler.py`, 12 chỉ số
   (M1–M12), chạy được trên **1 model HOẶC 1 bộ bins**, 2 chế độ RAW (có bins) / AGG (per-tick parquet).
2. **Thước tự nói lại được `GIỮ 45`?** — **CÓ, ở đúng chỗ quan trọng nhất** (V-A):
   `A44` vs `{45deploy, A45}` ⇒ **KEEP/NULL** (Δlift@8 **âm, ngoài CI** vs **cả hai** đối chứng). Thước
   **tái lập CHÍNH XÁC** con số đã công bố của vòng ARM44 (`Δrank-IC(A44−A45) = +0,001965`;
   `Δlift@8 = −0,003075`) và **tự kết luận KHÔNG đổi model** — tức không cần tới SIM để nói "A44 không
   phải ranker tốt hơn". `V0` (cắt 45→21) cũng **KEEP**.
   **Nhưng CÓ 1 lỗi trong CHÍNH pre-reg của tôi** (V-C, viết sai phép kiểm bẫy OFI) ⇒ bản "nguyên văn"
   trả `KHONG`; sau khi **khai báo rõ và sửa phép kiểm** (V-C' = `V5 − V1`) thì trả `CO`. Chi tiết §5.
3. **Phát hiện quan trọng nhất cho câu hỏi của chủ dự án** (đo trên bản deploy 45, 140.238 tick 2022+):
   - `AUC` (câu hỏi **nhị phân** *"coin nào sắp bơm >1,5 %/4h"*) = **0,6685** ⇒ **CÓ skill thật**.
   - `pairwise accuracy` (đúng câu chủ dự án: `P(score_A > score_B | kết quả_A > kết quả_B)`) = **0,4821**
     ⇒ **KHÔNG có skill** (thấp hơn 0,5 = *đoán ngẫu nhiên*), tức **điểm cao KHÔNG** kéo theo **kết quả lớn hơn**.
   - `gross@8 = +0,000148` (mốc cả tick `−0,000062`) nhưng **`net@8 = −0,007852`** ⇒ sau chi phí round-trip
     0,008, **top-8 theo `P(win)` là ÂM ở horizon 4h**.
   ⇒ Điểm của model là **công cụ GATE (nhị phân)**, **KHÔNG** phải công cụ XẾP HẠNG theo kết quả. Nên
   "train rồi ghép vào hiện trạng" đúng là **đo CALIBRATION**, không đo skill — **khớp lo ngại của chủ dự án**.

---

## 1. CỔNG / PROVENANCE (phải PASS mới đọc số)

| # | cổng | kết quả |
|---|---|---|
| **G1** | RAW tái lập được AGG của kernel | `45deploy` tính **RAW từ bins** cho `rank-IC = −0,051110`, `lift@8 = +0,110510` — **trùng khít 6 chữ số** với per-tick parquet của kernel (`arm44_ruler45.py`) ✓ |
| **G2** | ghép cặp được | **6 arm** đều `n_tick = 140.238`, **`ts` trùng khít từng dòng** (T3 = `True` cho cả 6) ✓ |
| **G3** | nhãn | `/home/ubuntu/label_15m` (20 file `.pb`, `39.623.937` dòng `retEnd_4h` notna), `THR = 0,015`, tick ≥ 2 coin ✓ |
| **G4** | CI | block-72h, `NREP = 2000`, `seed = 20260905` — **import `c3_rates`/`stage2_score.block_boot_mean`**, không viết lại; `k = 1` ⇒ **in ra `inflate(1) = 1,0`**; độ rộng quyết định = `LEGACY = 1,21` (hằng số repo) ✓ |
| **G5** | chi phí | `0,002 + 2×0,003 = 0,008` — **theo CODE** (`Configs.java:103 RATE_FEE=0.002f` đã là 2 chân + `:117 SLIPPAGE_RATE=0.003f` ×2; khớp `HPOFitnessCalculatorV4:164`). **Cảnh báo:** comment `Configs.java:164` cộng nhầm thành 0,010 — không dùng comment. |

---

## 2. BỘ CHỈ SỐ (M1–M12) — đo trên **bản deploy 45** (RAW, 140.238 tick, 16 fold, 255,2 coin/tick)

| # | chỉ số | giá trị (RAW) | CI block-72h | CI ×1,21 (legacy) |
|---|---|---|---|---|
| M1 | `rank-IC` (Spearman/tick) | **−0,051110** | [−0,054290, −0,047833] | [−0,054958, −0,047145] |
| M2 | `\|rank-IC\|` | **0,141418** | [0,138580, 0,144289] | [0,137984, 0,144892] |
| M3 | `lift@8` (K=8) | **+0,110510** | [+0,104917, +0,115944] | [+0,103742, +0,117085] |
| M4 | `precision@8` | **0,286710** | [0,280645, 0,292654] | [0,279371, 0,293902] |
| M5 | `AUC` within-tick (nhị phân) | **0,668537** | [0,663102, 0,674067] | [0,661961, 0,675229] |
| M6 | `pairwise accuracy` `P(s_A>s_B\|y_A>y_B)` | **0,482131** | [0,480996, 0,483303] | [0,480757, 0,483549] |
| M7 | `decile monotonicity` (`Σρ(decile, mean_y)`; tỉ lệ cặp kề không giảm) | **−0,021778**; **0,495939** | [−0,032233, −0,011131] | [−0,034429, −0,008896] |
| M8 | `gross@8` (mốc cả tick = **−0,000062**; `gross_lift@8` = **+0,000209**) | **+0,000148** | [−0,000473, +0,000774] | [−0,000603, +0,000905] |
| M9 | `net@8` = `gross@8 − 0,008` | **−0,007852** | [−0,008473, −0,007226] | [−0,008603, −0,007095] |
| M10 | `net_lift@8` (nhãn net, `retEnd−0,008 > 0,015`) | **+0,118805** | [+0,113285, +0,124143] | [+0,112126, +0,125264] |
| M11 | `drift` = mean(8 fold đầu) − mean(8 fold cuối) | `lift@8` **−0,042895**; `IC` **+0,010563** | — (mô tả) | — |
| M12 | theo FOLD / theo NĂM | xem bảng dưới | — | — |

**Theo NĂM — `lift@8` / `IC`** (UTC+7, khớp `TZ=+7h` của trainer):

| arm | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|
| `45deploy` | 0,0552 / −0,0417 | 0,1229 / −0,0500 | 0,1127 / −0,0564 | 0,1513 / −0,0564 |
| `A44` | 0,0551 / −0,0403 | 0,1190 / −0,0488 | 0,1088 / −0,0530 | 0,1483 / −0,0543 |
| `V0` | 0,0520 / −0,0384 | 0,1146 / −0,0481 | 0,1077 / −0,0507 | 0,1474 / −0,0529 |
| `V1` | 0,0613 / −0,0465 | 0,1213 / −0,0509 | 0,1087 / −0,0528 | 0,1452 / −0,0579 |

- **Chiều (`hướng đầu`) — GHI RÕ:** `rank-IC` **ÂM ở MỌI arm, MỌI năm**; "tốt hơn" ⇒ **\|IC\| LỚN HƠN**.
  `lift@8` dương; "tốt hơn" ⇒ lớn hơn. Hai chiều này **KHÔNG** luôn cùng hướng (xem §4, hệ `V*`).
- **Drift:** `lift@8` **giảm 0,0429** (8 fold đầu → 8 fold cuối); `IC` **mạnh lên 0,0106**. Đây là drift
  **theo fold** (số coin/tick tăng dần 2022→2025) — **mô tả, không có luật quyết định**.
- `dec_mono = 0,4959` (< 0,5 = tung đồng xu) và `dec_rho = −0,0218` ⇒ **quan hệ score↔kết quả KHÔNG đơn điệu**
  ⇒ ruler **không** chỉ nhìn top-1/top-8: cả thang decile đều không xếp được theo độ lớn kết quả.

---

## 3. VALIDATE TRÊN 5 ARM (+ tham chiếu `V1`)

| arm | là gì | `rank-IC` [CI] | `\|IC\|` | `lift@8` [CI] | `precision@8` | drift `lift@8` |
|---|---|---|---|---|---|---|
| `45deploy` | MỐC (bản deploy) | −0,051110 [−0,0543,−0,0478] | 0,1414 | **+0,110510** [+0,1049,+0,1159] | 0,28671 | −0,0429 |
| `A45` | **đối chứng C1** (retrain 45) | −0,051061 [−0,0541,−0,0478] | 0,1411 | +0,110850 [+0,1053,+0,1163] | 0,28705 | −0,0416 |
| `A44` | **ỨNG VIÊN 1** (−`rvol15m`) | −0,049096 [−0,0521,−0,0459] | 0,1352 | +0,107775 [+0,1024,+0,1132] | 0,28398 | −0,0415 |
| `V0` | **ỨNG VIÊN 2** (21 keeper) | −0,047526 [−0,0504,−0,0445] | 0,1304 | +0,105444 [+0,1001,+0,1108] | 0,28164 | −0,0442 |
| `V5` | **đối chứng C2** (21+5 thật+5 nhiễu) | −0,051858 [−0,0551,−0,0483] | 0,1388 | +0,108477 [+0,1032,+0,1136] | 0,28468 | −0,0358 |
| `V1` | tham chiếu (21+5 thật) | −0,052018 [−0,0553,−0,0485] | 0,1395 | +0,109101 [+0,1039,+0,1143] | 0,28530 | −0,0356 |

---

## 4. Δ SO VỚI **CẢ HAI** ĐỐI CHỨNG (`*` = ngoài CI **cả hai** độ rộng; ghép cặp 140.238 tick)

| so sánh | Δ`lift@8` [CI] | Δ`\|IC\|` | Δ`IC` (dấu) | đọc |
|---|---|---|---|---|
| `A44 − 45deploy` (chính) | **−0,002735** [−0,003666,−0,001747] `*` | **−0,005904** `*` | +0,002014 | A44 **XẤU hơn cả hai thước** |
| `A44 − A45` (C1) | **−0,003075** [−0,004005,−0,002141] `*` | **−0,005487** `*` | +0,001965 | **tái lập đúng số đã công bố** |
| `A45 − 45deploy` (V-D: nền nhiễu retrain) | +0,000340 [−0,000332,+0,001004] | −0,000417 `*` | +0,000050 | nền nhiễu **nhỏ** ⇒ Δ của A44 là THẬT, không phải nhiễu máy |
| `V0 − 45deploy` (chính) | **−0,005065** [−0,006192,−0,003856] `*` | **−0,007682** `*` | +0,003584 | V0 **XẤU hơn** |
| `V0 − V5` (C2) | **−0,003032** [−0,004504,−0,001456] `*` | **−0,017668** `*` | +0,004332 | V0 **XẤU hơn** cả đối chứng nhiễu |
| `V5 − V1` (**bước nhiễu thuần**) | −0,000624 [−0,001334,+0,000065] | +0,000263 | +0,000160 | **KHÔNG ngoài CI** ⇒ cột nhiễu **không thêm gì** ⇒ đối chứng nhiễu ĐÚNG chức năng |
| `V1 − V0` (OFI thật) | +0,003656 [+0,002038,+0,005181] `*` | +0,017405 `*` | −0,004491 | OFI thật **có** thêm tín hiệu trên `lift@8` |
| `V1 − 45deploy` / `V5 − 45deploy` | −0,001409 / −0,002033 (KHÔNG ngoài CI) | **+0,009723 `*`** / **+0,009986 `*`** | −0,000907 / −0,000748 | 🔴 **hai thước MÂU THUẪN**: `\|IC\|` nói V1/V5 TỐT HƠN deploy ngoài CI, `lift@8` nói KHÔNG |

🔴 **HẠN CHẾ ĐO ĐƯỢC, PHẢI NÓI RÕ:** trong họ `V*`, **`|IC|` và `lift@8` bất đồng** (V1/V5 thắng deploy
ở `|IC|` ngoài CI nhưng thua/ngang ở `lift@8`). Luật §5 đã chốt TRƯỚC là dùng **`lift@8` làm chỉ số chính**
⇒ kết luận theo luật, **nhưng** bất đồng này là **cùng loại bất đồng** đã gây ra chuyện "SIM vs thước xếp
hạng" ở vòng ARM44 ⇒ **thước này CHƯA phải một chỉ số duy nhất, đừng bán nó như vậy.**

---

## 5. LUẬT §5 + TỰ KIỂM (kết quả thật, kể cả chỗ tôi SAI)

### 5.1 Verdict

| mã | kiểm | kết quả |
|---|---|---|
| **V-A** | `A44` vs {`45deploy`, `A45`} | **KEEP (NULL)** — `lift8_gt_ctrl1/2 = False`, `ic_worse_ctrl1/2 = True` |
| **V-B** | `V0` vs {`45deploy`, `V5`} | **KEEP (NULL)** |
| **V-C** | **nguyên văn pre-reg §7**: `V5` (nhiễu) có "thắng" `V0` ngoài CI không? | 🔴 **FAIL theo nguyên văn** (`Δlift@8 = +0,003032` **ngoài CI cả hai**) — **nhưng phép kiểm này TÔI VIẾT SAI** (xem 5.2) |
| **V-C'** | **sửa**: bước nhiễu THUẦN `V5 − V1` có thêm tín hiệu không? | **PASS** (`Δlift@8 = −0,000624`, **không** ngoài CI) |
| **V-D** | nền nhiễu retrain `A45 − 45deploy` | `Δlift@8 = +0,000340` (**không** ngoài CI); `Δ\|IC\| = −0,000417` (ngoài CI, rất nhỏ) |
| **V-E** | T1 + T2 | **PASS** |

**Kết luận validate — nói cả hai bản:**
- Bản **nguyên văn pre-reg §7**: `GIỮ 45` **KHÔNG** được tự nói lại (vì V-C FAIL).
- Bản **sau khi sửa V-C (khai báo rõ)**: `GIỮ 45` **ĐƯỢC** tự nói lại (`V-A ∧ V-B ∧ V-C' ∧ V-E` đều PASS).
- **Không thay đổi luật §5** và **không xoá** V-C nguyên văn: cả hai bản đều nằm trong JSON
  (`reproduces_KEEP45_as_written = false`, `reproduces_KEEP45_after_VC_fix = true`) + in ra stdout của tool.

### 5.2 LỖI CỦA TÔI trong pre-reg (khai báo, KHÔNG sửa lén)

`V5 = V0 + 5 cột THẬT (idx 45–49) + 5 cột NHIỄU (idx 50–54)` (`featuresets/fs_v9_31.json`: `base_keepers`
= 21 keeper, `appended_real = [45..49]`, `appended_noise = [50..54]`) ⇒ **`V5 ⊇ V1 ⊇ V0`**.
Vậy "`V5 > V0`" **KHÔNG** phải phép kiểm bẫy OFI — nó trộn cả 5 cột thật + 5 cột nhiễu; `V5 > V0` là
**đúng như mong đợi**. Phép kiểm bẫy OFI phải là **bước nhiễu THUẦN** `V5 − V1` (hoặc `V5 vs V1`):
**`Δlift@8 = −0,000624 [−0,001334, +0,000065]` ⇒ không ngoài CI** ⇒ nhiễu **không** "thắng" ⇒ **thước
không dính bẫy OFI**. (Đối chiếu: `V1 − V0 = +0,003656*` = OFI thật CÓ thêm tín hiệu.)
⇒ Bẫy OFI **đã bị chặn**; lỗi là ở **phép kiểm tôi viết**, không ở thước. Ghi vào `PREREG_..._v?` cho vòng sau.

### 5.3 T1/T2/T3 — thước có phân biệt được không (và có đo đúng thứ cần đo không)

| test | kết quả |
|---|---|
| **T2 — bất biến theo RANK** (quantile→uniform và `logit`, cùng thứ tự) | **`max-abs-delta = 0,00e+00` trên CẢ 11 chỉ số (kể cả AUC/pairwise/decile/gross/net)** ⇒ **PASS tuyệt đối**. ⇒ Thước đo **THỨ TỰ**, **KHÔNG** đo scale/calibration ⇒ đúng công cụ để **tách Tầng A khỏi việc re-calibrate gate ở Tầng B**. |
| **T1 — xáo score trong từng tick** | `lift@8 = −0,0000004` ✓, `IC = +0,0000081` ✓, `AUC = 0,499937` ≈ 0,5 ✓, `pacc = 0,500003` ✓ ⇒ thước **thấy được** khi mất tín hiệu. **NHƯNG `\|IC\|` xáo = 0,054105 ≠ 0** ⇒ **dự đoán Q2 của tôi SAI một phần**: `\|IC\|` có **sàn nhiễu** `E\|IC\| ≈ 1/√(n−1) ≈ 0,06` (vì `\|mean\|` ≠ `mean\|·\|`). ⇒ **M2 chỉ dùng được dưới dạng Δ**, không được đọc như "bằng 0". |
| **T3 — coverage** | `ts` khớp khít `45deploy` cho cả 6 arm ✓ |

---

## 6. HAI TẦNG + ĐỀ XUẤT RUNBOOK

### 6.1 Tầng A (thước model) — dùng khi nào

Trả lời **"tập feature mới có phải RANKER tốt hơn không"** bằng `model_ruler.py`. **KHÔNG** dùng
equity/PnL/`n` (đó là Tầng B). Chạy RAW khi có bins (đủ M1–M10); chạy AGG khi chỉ có per-tick parquet
(M1–M4 — đủ để ra quyết định theo luật §5).

```
python3 research/analysis/model_ruler.py ruler --name <TAG> --bins <dir> [--self-tests] --out <j> --per-tick <p>
python3 research/analysis/model_ruler.py ruler --name <TAG> --ticks <perfold_ticks.parquet>
python3 research/analysis/model_ruler.py validate [--reuse] --out <j>   # 6 arm + 2 doi chung + T1/T2/T3
```

### 6.2 Tầng B (sim) — ràng buộc bắt buộc

SIM **chỉ** chạy cho model **đã qua Tầng A**, VÀ **phải RE-CALIBRATE gate theo scale score của model mới**.
*Lý do đo được*: gate dùng **multiset `P(win)`** của tick ⇒ đổi model ⇒ đổi phân phối ⇒ đổi `dyn_thr` ⇒ đổi
số lệnh. Bằng chứng có sẵn trong repo: `G5_VALUE_LABELS` (đổi nhãn ⇒ `p_mean 0,2268 vs 0,4642` ⇒ admit
×5,05, `win%` −8,04 pp). ⇒ So sim giữa 2 model **khác scale score** mà **không** re-calibrate = **đo
calibration**, KHÔNG đo skill — đúng cái "thiên kiến" chủ dự án nói.

### 6.3 Vì sao SIM và thước xếp hạng CÓ THỂ mâu thuẫn (cơ chế, không phải nhiễu)

`RESULT_ARM44` §0 đã ghi: **sim lấy THỨ TỰ coin từ S1**, model chỉ cấp **multiset `P(win)` cho gate**.
⇒ Thứ tự của **chính model** (thứ mà `rank-IC`/`lift@8` đo) **hầu như không vào sim**. Vậy "SIM nói A44 ≥ A45"
và "thước xếp hạng nói A45 > A44" **đo hai đối tượng khác nhau** ⇒ mâu thuẫn là **cấu trúc**, không phải mâu
thuẫn số liệu. *Hệ quả:* muốn thước model có nghĩa cho hệ thống, phải nói rõ hệ thống dùng model để
**gate** hay để **xếp hạng** — và nếu chỉ để gate thì thước đúng phải là **ruler của CƠ CHẾ GATE**
(`g5_proxy.py` — admission bất biến theo multiset), không phải `rank-IC`.

### 6.4 ĐỀ XUẤT RUNBOOK (đã áp — commit riêng `docs/runbooks/AGENT_RUNBOOK.md` §0 mục 12)

> **12. THƯỚC CHỌN MODEL = MODEL RULER (Tầng A); SIM = kiểm HỆ THỐNG (Tầng B).** Câu hỏi "tập feature mới
> có tốt hơn không" PHẢI trả lời bằng `research/analysis/model_ruler.py` (rank-IC/lift@8/prec@8/AUC/pairwise/
> gross-net, offline, không train/không sim), KHÔNG bằng equity/PnL. SIM chỉ chạy cho model **đã qua Tầng A**
> VÀ **phải re-calibrate gate theo scale score mới**; thước model bất biến với biến đổi tăng nghiêm ngặt
> của score (T2) nên không bị "thưởng" vì hợp hiện trạng.

---

## 7. MỤC **KHÔNG ĐỌC ĐƯỢC** (ghi rõ — không che)

1. **M5/M6/M7/M8/M9/M10 (AUC, pairwise, decile, gross, net) chỉ có cho `45deploy`.**
   4 arm retrain (`A45/A44/V0/V1/V5`) **không giữ bins** (kernel chỉ tải về per-tick parquet ~30 MB, không
   tải ~5 GB bins) ⇒ **Δ giữa các arm chỉ có M1–M4**. Đây là **khoảng trống hạ tầng kernel**, KHÔNG phải lỗi
   thước. **Cách bịt (đề xuất, chưa làm):** kernel ghi thêm 1 parquet per-`(tick,coin)` **score+label** đã
   nén (chỉ cần `ts,sym,p,y`) ⇒ mọi Δ sau này có đủ M5–M10.
2. **Funding CHƯA trừ** trong M9/M10: không có chuỗi funding-rate local (crawler gọi API ⇒ ngoài phạm vi
   offline). Đối chứng: sim/WFO của repo **mặc định** `APPLY_FUNDING_FEE=false` (comment `Configs.java:130`:
   ~0,9 % PnL, maxDD không đổi). ⇒ Số net ở đây là net **"ex-funding"**.
3. **Không có `pacc` cho 4 arm retrain** (cần score+label thô) ⇒ **câu hỏi ruột của chủ dự án
   (`P(score_A > score_B | kết quả_A > kết quả_B)`) mới chỉ trả lời được cho bản deploy** — và câu trả lời
   là **0,4821 (< 0,5)**.
4. **2 fold 2021H2 giống nhau tuyệt đối ở mọi arm** (di sản cách dựng bins) ⇒ mọi so sánh chỉ nói về
   **16 fold OOS 2022+**.
5. **`|IC|` có sàn nhiễu ~0,054** (T1) ⇒ chỉ đọc dạng Δ; **và `|IC|` bất đồng `lift@8` trong họ `V*`** ⇒
   thước **chưa** là một con số duy nhất.

---

## 8. DỰ ĐOÁN KHOÁ TRƯỚC — ĐỐI CHIẾU

| # | dự đoán | kết quả |
|---|---|---|
| Q1 | T2 PASS tuyệt đối | **ĐÚNG** (`max-abs-delta = 0,00e+00`) |
| Q2 | T1: `lift@8` shuffled ≈ 0 và ngoài CI | **ĐÚNG** (−0,0000004). **Phần `\|IC\| ≈ 0` SAI** — sàn nhiễu 0,054 (ghi rõ §5.3) |
| Q3 | V-A KEEP: `Δlift@8(A44−A45) < 0` ngoài CI | **ĐÚNG** (−0,003075 **trùng khít** số đã công bố) |
| Q4 | V-B KEEP | **ĐÚNG** |
| Q5 | V-C PASS (`V5` không tốt hơn `V0` ngoài CI) | **SAI theo nguyên văn** (do **tôi viết sai phép kiểm**); **PASS** sau khi sửa thành `V5−V1` (§5.2) |
| Q6 | `A45 − 45deploy` ≈ 0 | **ĐÚNG** (`Δlift@8 = +0,000340`, không ngoài CI) |
| Q7 | `net@8 < gross@8` đúng ≈ 0,008, dấu/kết luận không đổi | **ĐÚNG** (`+0,000148` → `−0,007852`, hiệu đúng 0,008; verdict không đổi) |

---

## 9. KẾT LUẬN

1. **Có thước model dùng lại được**, tách khỏi sim, bất biến rank (T2), có null control thật (T1),
   tái lập được số của kernel (G1) — **và tự nói lại `GIỮ 45`** ở V-A/V-B.
2. **A44 và V0 KHÔNG phải ranker tốt hơn** (`lift@8` xấu hơn **cả hai** đối chứng, ngoài CI; `|IC|` cũng xấu hơn)
   ⇒ **"GIỮ 45" có căn cứ ở Tầng A**, không cần viện tới SIM. Nền nhiễu retrain nhỏ (+0,000340) ⇒ khác biệt là thật.
3. **Câu hỏi gốc của chủ dự án đã có số**: điểm cao ⇒ **CÓ** cho câu hỏi nhị phân (`AUC 0,6685`) nhưng
   **KHÔNG** cho câu hỏi độ lớn kết quả (`pacc 0,4821`), và `net@8 = −0,007852` ⇒ **đừng dùng thước này
   thay thế việc kiểm hệ thống, và đừng dùng sim để "chứng minh" model tốt hơn**.
4. **Việc tiếp (đề xuất, chưa làm):**
   (a) kernel ghi thêm parquet `(ts,sym,p,y)` ⇒ mở khoá M5–M10 cho mọi arm;
   (b) patch `PREREG_MODEL_RULER.md` → v2 sửa V-C (`V5−V1`) + ghi sàn nhiễu `|IC|`;
   (c) nếu muốn thước có nghĩa cho **gate**: dùng `g5_proxy.py` (admission bất biến) làm thước Tầng A-song-song.

**File:** `research/analysis/model_ruler.py` · `docs/prereg/PREREG_MODEL_RULER.md` · `docs/result/RESULT_MODEL_RULER.md`
· JSON: `/home/ubuntu/.cache/ruler_validate.json` (KHÔNG commit — artifact ngoài repo).
