# RESULT_MODEL_RULER — THƯỚC ĐÁNH GIÁ **MODEL** (ranker), tách khỏi thước HỆ THỐNG (sim)

**Ngày:** 2026-09-25 · **Nhánh:** `module` · **Trạng thái:** ĐO XONG (offline, KHÔNG train, KHÔNG sim)
**Tiền đăng ký (chốt TRƯỚC khi chạy):** `docs/prereg/PREREG_MODEL_RULER.md` — commit **`cc22253`**
**Code:** `research/analysis/model_ruler.py` · JSON đầy đủ: `/home/ubuntu/.cache/ruler_validate.json`
· **(AMEND §10)** `ruler_bins_4h.json` · `ruler_bins_72h.json` · `ruler_bins_econ72h.json` (cache per-tick `/tmp/model_ruler_out/`)
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

> ⚠️ **CẬP NHẬT 2026-09-25 (đọc kèm §13):** mục **7.1 dưới đây ĐÃ HẾT HIỆU LỰC** — phiên song song đã
> **tải bins thô của 4 arm retrain** từ kernel output Kaggle ⇒ `M1/M2/M3` **tính được cho mọi arm**
> (§13.1–§13.2). Mục **7.2** (funding) **giữ nguyên**. Mục 72h: xem **§13.4** (không arm nào có điểm 72h).

1. ~~**M5/M6/M7/M8/M9/M10 (AUC, pairwise, decile, gross, net) chỉ có cho `45deploy`.**~~ **(HẾT HIỆU LỰC
   từ §13)** 4 arm retrain ~~**không giữ bins**~~ — nay **có** bins thô.
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

---

## 10. AMEND — KẾT QUẢ THEO **CỔNG MỚI** (M1′/M2′/M3′, h ∈ {4h, 72h}) — sau khi **ĐÓNG G-1** bằng BINS THÔ

**Trạng thái:** ĐO XONG (thuần Python offline: **KHÔNG** train, **KHÔNG** sim, **KHÔNG** job).
**Tiền đăng ký:** `PREREG_MODEL_RULER.md` **§12** (commit `214c420`) + **§12.9** (commit `b37b548`).
**JSON:** `/home/ubuntu/.cache/ruler_bins_4h.json` · `ruler_bins_72h.json` · `ruler_bins_econ72h.json`
(cache per-tick: `/tmp/model_ruler_out/`). **KHÔNG** chạm ONNX/LIVE/2026 · **KHÔNG** push.

> **GHI RÕ (để không "hai bản số"):** trong cùng ngày có **2 phiên chạy song song** cùng vòng này. **§13**
> (dưới, của phiên kia) báo **cùng bộ số** theo bố cục khác; **§10 này** bổ sung 3 thứ §13 chưa có:
> `auc8c` (bản sửa của M1′ — **đã đo**), decile **GỘP** từng arm (M3(a)), và **kiểm kinh tế cross-horizon
> cho cả 6 arm**. Hai bản **khớp nhau**; **KHÔNG xóa** bản nào (giữ lịch sử).

### 10.0 CỔNG PROVENANCE (phải PASS mới đọc số)

| # | cổng | kết quả |
|---|---|---|
| **G6** | bins THÔ của 4 arm retrain | **CÓ** — tải từ **kernel output** Kaggle (`kaggle kernels output`, 80 file / **4,65 GB**): `V0/V1/V5` ← `g015p2-stage2-featvar-gpu`; `A44/A45` ← `g015p2-arm44-gpu`. **Chỉ tải artifact đã có** — không train/sim/job |
| **G7** | RAW từ bins **tái lập đúng số đã công bố** (6 chữ số) | `A45` −0,051061/+0,110850 · `A44` −0,049096/+0,107775 · `V0` −0,047526/+0,105444 · `V1` −0,052018/+0,109101 · `V5` −0,051858/+0,108477 — **trùng khít** per-tick parquet kernel ✓ |
| **G8** | coverage | **6/6** arm `n_tick = 140.238`, `ts` khớp khít từng dòng ✓ |
| **G9** | CI | block-72h, 2000 rep, seed 20260905; **k = 2** (2 ứng viên `A44`,`V0`) ⇒ `inflate(2)` = **1,177410**; 1,21 chỉ in tham chiếu ✓ |
| **G10** | T1/T2 (thước) | **T2 `max\|Δ\| = 0,0`** trên cả chỉ số mới (`auc8`, `lift8/12/16`, `dec_rho_lab`); **T1** `lift8` shuffled = −3,9e−7, `ic` = +8,1e−6 ✓ |
| **G11** | **ĐIỂM 72h** | **KHÔNG TỒN TẠI**: `z[:,0..2]` = NaN **100 %** ở **MỌI** bins (deploy 18 fold + 5 arm × 16 fold) — xem §10.5 |

### 10.1 MỨC — 5 arm × 3 chỉ số chính (RAW, nhãn train `y = retEnd_4h > 0,015`, 140.238 tick)

| arm | vai trò | **M1′ `auc8`** (`§12.1`) | **M1′ `auc8c`** (bản ĐÚNG) | **M2′ `lift@8`** | **M2′ `lift@12`** | **M2′ `lift@16`** | **M3(b) `dec_rho_lab`** | `ic` (PHỤ) |
|---|---|---|---|---|---|---|---|---|
| `45deploy` | **MỐC** | 0,623932 | 0,613944 | +0,110510 | +0,099856 | +0,091935 | +0,461524 | −0,051110 |
| `A45` | đối chứng **retrain** | 0,624411 | 0,614428 | +0,110850 | +0,100345 | +0,092180 | +0,461195 | −0,051061 |
| `A44` | **ỨNG VIÊN 1** | 0,618747 | 0,608819 | +0,107775 | +0,097269 | +0,089608 | +0,448348 | −0,049096 |
| `V0` | **ỨNG VIÊN 2** | 0,612618 | 0,602825 | +0,105444 | +0,095284 | +0,087695 | +0,438940 | −0,047526 |
| `V1` | tham chiếu (OFI thật) | 0,618866 | 0,609135 | +0,109101 | +0,099456 | +0,092306 | **+0,470669** | −0,052018 |
| `V5` | đối chứng **nhiễu** | 0,617625 | 0,607936 | +0,108477 | +0,099064 | +0,092055 | +0,470235 | −0,051858 |

- **M1′ (`auc8`)** > 0,5 ở **mọi** arm ⇒ top-8-vs-phần-còn-lại **có** skill (thấp hơn `auc` whole-tick 0,6685 — đúng như dự đoán **Q8**). **Thứ tự các arm KHÔNG đổi** khi dùng `auc8c`.
- ⚠️ **M1′ — KHAI BÁO LỖI KỸ THUẬT (đo được, không che):** công thức `auc8` chốt ở §12.1 **có lỗi**: cặp `(pos∈T, neg∈T)` được **cộng 2 lần ở tử số** (1 lần qua `nbel` của `pos∈T`, 1 lần qua `pabv` của `neg∈T`) nhưng **chỉ đếm 1 lần ở mẫu số** (`den8`) ⇒ `auc8` **không phải AUC hợp lệ và CÓ THỂ > 1**. Chứng minh (dữ liệu tổng hợp 12 coin, 6 ca): `auc8` = 0,6875 / **1,1852** / 0,6552 … trong khi bản đúng = 0,4688 / 0,8148 / 0,4828. Trên dữ liệu thật (`K=8` trên ≈255 coin/tick) khối `(T,T)` chỉ chiếm ≈ 1 % mẫu số ⇒ lệch ≈ −0,010 (thấy rõ ở bảng trên) và **không đổi thứ tự**. **Đã thêm `auc8c` = bản ĐÚNG** (mỗi cặp hợp lệ đếm đúng 1 lần, tie = 0,5; verify khớp tính tay 6/6 ca) và **đo song song**; **KHÔNG sửa luật GO** (vẫn dùng M1′ như đã chốt) — §10.2/§10.3 báo **cả hai** để thấy kết luận **không phụ thuộc** bản nào.
- **M2′**: `lift@8 > lift@12 > lift@16 > 0` ở **mọi** arm (đúng **Q9**).
- **M3(a) — decile GỘP trên NHÃN TRAIN: PASS ở MỌI arm** (ρ = **+1,0000**; dốc `D10−D1` = +0,15835 (`45deploy`) · +0,15834 (`A45`) · +0,16105 (`V1`) · +0,16117 (`V5`) · +0,15162 (`A44`) · **+0,14878 (`V0`)**) — đúng **Q10**. **Nhưng** gộp trên `retEnd` **liên tục**: ρ = **−0,1394** (`45deploy`), −0,5030 (`A45`), −0,0545 (`A44`), −0,0909 (`V0`), −0,8667 (`V1`), −0,7576 (`V5`) ⇒ **nhãn nhị phân xếp được, ĐỘ LỚN kết quả thì KHÔNG** (khớp `pacc` 0,4817–0,4835 < 0,5 và `pacc` của v1 = 0,4821).

### 10.2 Δ vs **CẢ HAI** ĐỐI CHỨNG (ghép cặp theo tick; `*` = ngoài CI cả hai độ rộng)

| so sánh | Δ`auc8` | Δ**`auc8c`** | Δ`lift8` | Δ`lift12` | Δ`lift16` | Δ`dec_rho_lab` |
|---|---|---|---|---|---|---|
| `A44 − A45` (C1 retrain) | −0,005665`*` | −0,005609`*` | **−0,003075`*`** | −0,003076`*` | −0,002572`*` | −0,012847`*` |
| `A44 − 45deploy` (MỐC) | −0,005185`*` | −0,005125`*` | −0,002735`*` | −0,002587`*` | −0,002328`*` | −0,013177`*` |
| `V0 − V5` (C2 nhiễu) | −0,005007`*` | −0,005111`*` | −0,003032`*` | −0,003779`*` | −0,004360`*` | −0,031295`*` |
| `V0 − 45deploy` (MỐC) | −0,011313`*` | −0,011119`*` | −0,005065`*` | −0,004572`*` | −0,004241`*` | −0,022584`*` |
| `A45 − 45deploy` (nền nhiễu retrain) | +0,000480 | +0,000484 | +0,000340 | +0,000488 | +0,000245 | −0,000329 |
| `V5 − V1` (bước nhiễu THUẦN) | −0,001241 | −0,001199 | −0,000624 | −0,000392 | −0,000251 | −0,000433 |
| `V1 − V0` (OFI thật) | +0,006248`*` | +0,006310`*` | +0,003656`*` | +0,004171`*` | +0,004611`*` | +0,031729`*` |
| `V5 − 45deploy` | −0,006306`*` | −0,006008`*` | −0,002033 | −0,000793 | +0,000119 | +0,008711`*` |
| `V1 − 45deploy` | −0,005065`*` | −0,004809`*` | −0,001409 | −0,000401 | +0,000370 | +0,009145`*` |

- **C1 (retrain)**: nền nhiễu `A45 − 45deploy` **KHÔNG ngoài CI** ở **cả 5** chỉ số (lớn nhất = +0,000488 của `lift12`) ⇒ mọi Δ của ứng viên là **THẬT**, không phải nhiễu máy. **C2 (nhiễu)**: bước nhiễu thuần `V5 − V1` **KHÔNG ngoài CI** ⇒ đối chứng nhiễu **đúng chức năng**; `V1 − V0 = +0,003656*` ⇒ OFI thật **có** thêm tín hiệu.
- **Đọc thẳng:** ứng viên **XẤU hơn cả hai** đối chứng ở **cả 5** chỉ số (kể cả `auc8c`), và **XẤU hơn ở MỌI mức K**, không phải chỉ K=8.
- **Kiểm THÊM (không nằm trong cặp đối chứng đã khai báo — chặt hơn):** `A44 − V5` = `auc8` +0,001121 / `lift8` −0,000701 / `lift12` −0,001795`*` / `lift16` −0,002447`*` / `dec_rho_lab` −0,021888`*`; `V0 − A45` = **cả 5 âm và ngoài CI**. ⇒ **đổi cặp đối chứng thế nào cũng KHÔNG GO.**

### 10.3 LUẬT GO (h=4h cần ≥ 2/3) + **FAIL HẸP**

| ứng viên | cặp đối chứng (khai báo §12.3) | **M1′** | **M2′** | **M3′** | **đạt/3** | h=4h | **fail hẹp** |
|---|---|---|---|---|---|---|---|
| `A44` | `{A45` (retrain), `45deploy` (mốc)`}` | fail | **fail (K8,K12,K16 đều fail)** | fail | **0/3** | **NOT GO** | **KHÔNG** (3/3 mức K fail) |
| `V0` | `{V5` (nhiễu), `45deploy` (mốc)`}` | fail | **fail (K8,K12,K16 đều fail)** | fail | **0/3** | **NOT GO** | **KHÔNG** (3/3 mức K fail) |

- **"fail hẹp" KHÔNG xảy ra** ở round này: cả 2 ứng viên fail **cả 3** mức `K` và **cả** M1′/M3′, nên **không** phải "chỉ 1 trong 3 mức K" ⇒ ghi "fail **RỘNG**", **KHÔNG** nới ngưỡng (`n_K_fail = 3`, `flag = false` trong JSON).
- **Bền với bản sửa M1′:** dùng `auc8c` (bản ĐÚNG) thì `A44` fail M1′ (`Δ` = −0,005609`*` vs `A45`, −0,005125`*` vs `45deploy`) và `V0` fail M1′ (`Δ` = −0,005111`*` vs `V5`, −0,011119`*` vs `45deploy`) ⇒ **vẫn 0/3 ⇒ NOT GO**. Kết luận **KHÔNG phụ thuộc** việc dùng bản nào của M1′.
- 3 arm còn lại (`A45`, `V1`, `V5`) **không phải ứng viên** của round (không có quyết định đổi mốc); số của chúng ở §10.1 để đối chiếu.

### 10.4 M5–M10 (AUC / pairwise / decile / gross-net) giờ có **cho MỌI arm** (G-1 ĐÃ ĐÓNG)

| arm | `auc` (whole-tick) | `pacc` `P(s_A>s_B\|y_A>y_B)` | `dec_rho` (y liên tục) | `dec_mono` | `gross@8` | **`net@8`** (−0,008) | `net_lift@8` |
|---|---|---|---|---|---|---|---|
| `45deploy` | 0,668537 | 0,482131 | −0,021778 | 0,495939 | +0,000148 | **−0,007852** | +0,118805 |
| `A45` | 0,668671 | 0,482139 | −0,021705 | 0,495329 | +0,000210 | −0,007790 | +0,118822 |
| `A44` | 0,663915 | 0,482894 | −0,021145 | 0,495665 | +0,000170 | −0,007830 | +0,115832 |
| `V0` | 0,658897 | 0,483466 | −0,022040 | 0,495527 | +0,000198 | −0,007802 | +0,112415 |
| `V1` | 0,672532 | 0,481744 | −0,021111 | 0,495267 | +0,000110 | −0,007890 | +0,115479 |
| `V5` | 0,672086 | 0,481819 | −0,021565 | 0,495906 | +0,000009 | −0,007991 | +0,114997 |

⇒ Phát hiện của v1 **đúng cho MỌI arm**, không phải riêng bản deploy: điểm cao ⇒ **có** cho câu hỏi **nhị phân** (`auc` 0,659–0,673), **KHÔNG** cho câu hỏi **độ lớn** (`pacc` 0,4817–0,4835 < 0,5), và **`net@8` ÂM** ở mọi arm (−0,00779…−0,00799) ⇒ top-8 theo `P(win)` **không** sống nổi chi phí round-trip 0,008 ở horizon 4h. **Thước đo THỨ TỰ, không đo lợi nhuận** — đúng lý do Tầng A không được nhìn PnL.

### 10.5 h = 72h: **KHÔNG ĐÁNH GIÁ ĐƯỢC** (đo, không suy đoán) + kiểm KINH TẾ cross-horizon

1. **Cổng 72h ⇒ NA.** `z[:,2]` (slot 72h) = **NaN 100 %** ở **mọi** bins ⇒ **KHÔNG arm nào có điểm 72h** ⇒ điều kiện **(ii)** của luật GO ("h=72h không chỉ số nào Δ<0 ngoài CI") **KHÔNG ĐÁNH GIÁ ĐƯỢC** ở round này. Lý do = **thiếu hạ tầng** (trainer ghi thẳng 3 NaN — `g015_net_train_add.py` `write_bin`), **KHÔNG** phải "số xấu". Vì vậy round này **không** được cấp GO **và** cũng **không** bị chặn bởi (ii).
2. **Bịa số đã bị chặn:** code **không** lấy `p4h` thay cho điểm 72h (slot toàn NaN ⇒ bỏ arm, in "KHÔNG ĐÁNH GIÁ ĐƯỢC").
3. **Kiểm KINH TẾ cross-horizon** (điểm **4h** × nhãn **`retEnd_72h`**, `n_tick = 140.237`) — **KHÔNG PHẢI cổng**, chỉ để trả lời "mượn điểm 4h cho 72h được không":

| arm | `auc8` (4h score × nhãn 72h) | `lift8` | `ic` |
|---|---|---|---|
| `45deploy` | **0,479113** | **−0,014062** | −0,085570 |
| `A45` | 0,480754 | −0,012891 | −0,085090 |
| `A44` | 0,482885 | −0,012176 | −0,082474 |
| `V0` | 0,481411 | −0,012426 | −0,081944 |
| `V1` | 0,479138 | −0,014235 | −0,095697 |
| `V5` | 0,477441 | −0,015150 | −0,094953 |

⇒ **Không mượn được, ở MỌI arm:** `auc8 < 0,5` và `lift8 < 0` ⇒ chọn top-8 theo điểm 4h rồi **giữ 72h** là **kém hơn mức trung bình của tick** ⇒ muốn có cổng 72h **phải train đầu 72h RIÊNG**.

### 10.6 KẾT LUẬN: `GIỮ 45` **CÒN ĐÚNG**, và bây giờ đúng vì **SỐ ĐO** (không vì NA)

1. **`GIỮ 45` CÒN ĐÚNG** — trên **cả 3** chỉ số chính (M1′/M2′/M3′) và **cả 3** mức `K`, `A44` và `V0` đều **xấu hơn** *cả hai* đối chứng, **ngoài CI**: `A44` 0/3 · `V0` 0/3 ⇒ **NOT GO** (không đổi mốc).
2. **Điểm khác biệt so với bản chạy thiếu bins:** các ô `NA` ở phiên chạy không có bins **đã được lấp bằng số thật** — kết luận **không đổi**, nhưng bây giờ nó là **số đo** chứ không phải "không đọc được".
3. **G-1 đã đóng** (M5–M10 + `lift@12/16` cho mọi arm); **G-2 mở rộng hơn dự kiến** (72h thiếu ở **cả** `45deploy`) ⇒ điều kiện (ii) phải chờ **đầu 72h**, xem §10.7.
4. **Việc chưa làm (đề xuất):** (a) train **đầu 72h** + ghi vào slot 3 của bins; (b) `g5_proxy.py` làm thước Tầng-A-song-song cho **cơ chế GATE**.

### 10.7 ĐỀ XUẤT: đưa `retEnd_72h` + nhãn 72h vào pipeline (KHÔNG tự làm — cần train, ngoài phạm vi vòng này)

- **NHÃN 72h ĐÃ CÓ, KHÔNG cần sinh mới:** `/home/ubuntu/label_15m/*.pb` có `retEnd_72h` + `nBars_72h` (meta: `hStepsMinutes=[240,720,1440,4320]`, `hNames=[4h,12h,24h,72h]`); `funding_label_pb.read_label(usecols=["retEnd_72h","nBars_72h"])` đọc được ngay.
- **CÁI THIẾU LÀ ĐIỂM:** `write_bin` (`g015_net_train_add.py`) ghi `>qh4f` với 3 NaN ⇒ **sửa 2 chỗ**: (1) thêm `--label-h` cho `load_labels`/`load_features` (`col = "retEnd_%dh" % h`, `NEED = h*60/15`, lọc `nBars_%dh`), (2) `write_bin(..., slot)` ghi điểm vào đúng slot (`p` cho 4h, `z[:, h−1]` cho 12/24/72h). **PURGE** đã là 72h (`PURGE_STEPS=288`) nên **không** phải đổi cửa sổ chống leak.
- **Sim dùng được ngay:** `s3_funding.py --horizon 3` (`WfoDataset.horizonIdx`: 0=4h…3=72h) ⇒ không phải sửa Java.
- **Kỳ vọng phải khai báo TRƯỚC khi chạy:** base rate 72h ≈ **0,3932** (so 0,1849 của 4h) ⇒ `lift@K` **sẽ nhỏ hơn** và `Δ` **nhỏ hơn** ⇒ luật ≥2/3 **không** nới ngưỡng; và **`net@8`(72h)** phải báo kèm (chi phí 0,008 là hằng số, horizon dài hơn ⇒ "cửa sổ" lớn hơn).
- **Đề xuất thay cho "bịt G-1" kiểu cũ:** giữ bins (đã chứng minh tải được 4,65 GB trong **95 s**, ~50 MB/s) ⇒ **không** cần thêm parquet per-`(tick,coin)` nữa.

---

# 13. AMEND §12 — KẾT QUẢ (h=4h, **RAW cho CẢ 5 arm**, luật GO của owner)

**Ngày:** 2026-09-25 · **Pre-reg:** `214c420` (§12 amend, TRƯỚC khi đọc số bộ mới) + `b37b548` (§12.9 đóng G-1/G-2)
**JSON:** `/home/ubuntu/.cache/ruler_bins_4h.json` · `.../ruler_bins_4h_fresh.json` (bản fresh, có đường decile gộp)
**Bối cảnh:** giữa chừng, **phiên song song** (`agent:main:main`) tải **bins thô 4 arm retrain** từ kernel
output Kaggle (80 file / 4,65 GB — chỉ tải artifact, không train/không sim) ⇒ **G-1 (mục §7.1 v1) hết
hiệu lực**: `M1/M2/M3` giờ tính được cho **mọi** arm, kết quả là **số đo thật** chứ không còn NA.
2 lỗi chặn mà tôi sửa trong file dùng chung: (i) `go_rule` `KeyError 'state'` (khối `fail_hep` không có
khoá `state`) — bản sửa tương đương của phiên song song cũng đã áp; (ii) nhánh `--reuse` đòi **cả** cache
biến thể khi `--skip-selftest` ⇒ crash — nay chỉ đòi khi bật self-tests.

## 13.1 BA CHỈ SỐ CHÍNH theo arm (h=4h, nhãn train `retEnd_4h > 0,015`, 140.238 tick, 16 fold, 255,2 coin/tick)

| arm | **M1 `AUC@top8`** [CI block-72h] | **M2** `lift@8` / `@12` / `@16` | **M3(b)** ρ per-tick (nhãn train) | **M3(a)** ρ gộp / dốc |
|---|---|---|---|---|
| `45deploy` | **0,623932** [0,615858; 0,631675] | +0,110510 / +0,099856 / +0,091935 | **+0,461524** [0,447019; 0,475590] | **+1,0000** / **+0,15835 PASS** |
| `A45` (C1) | 0,624411 [0,616292; 0,632256] | +0,110850 / +0,100345 / +0,092180 | +0,461195 [0,447040; 0,475407] | +1,0000 / +0,15834 PASS |
| `A44` | 0,618747 [0,610659; 0,626679] | +0,107775 / +0,097269 / +0,089608 | +0,448348 [0,434200; 0,462608] | +1,0000 / +0,15162 PASS |
| `V0` | 0,612618 [0,604206; 0,620617] | +0,105444 / +0,095284 / +0,087695 | +0,438940 [0,424357; 0,453664] | +1,0000 / +0,14878 PASS |
| `V1` | 0,618866 [0,610855; 0,626860] | +0,109101 / +0,099456 / +0,092306 | +0,470669 [0,456172; 0,484663] | +1,0000 / +0,16105 PASS |
| `V5` (C2) | 0,617625 [0,609694; 0,625639] | +0,108477 / +0,099064 / +0,092055 | +0,470235 [0,455821; 0,484029] | +1,0000 / +0,16117 PASS |

- 🔴 **M3(a) KHÔNG phân biệt được arm nào** — **cả 6 arm đều ρ = +1,0000** và dốc dương ⇒ ngưỡng `>0,8`
  **không có tác dụng chọn lọc** ở bộ dữ liệu này; phần **quyết định của M3 là (b)**. (Ghi rõ vì luật §12.1
  viết M3 = (a) ∧ (b) — kết quả cho thấy (a) gần như luôn PASS ở họ model này.)
- **Q9 ĐÚNG**: `lift@8 > lift@12 > lift@16` ở **mọi** arm (tín hiệu nhọn nhất ở đúng K=8, tắt dần).- **Q8 ĐÚNG**: `AUC@top8 = 0,6239` ∈ dải dự đoán 0,55–0,80, và **thấp hơn** `AUC` whole-tick (0,6685)
  — đúng như đã khoá trước (mẫu số của M1 dồn trọng số vào cặp `P\T × N∩T` = vùng model sai).

> 🔴 **ERRATA (2026-09-25, do PHIÊN SONG SONG `agent:main:main` phát hiện — nhận lỗi, không che):**
> công thức `auc8` ở §13.1 **của tôi bị ĐẾM TRÙNG**: cặp `(pos ∈ T, neg ∈ T)` được cộng **2 lần ở tử số**
> (một lần qua `pos∈T`, một lần qua `neg∈T`) nhưng **chỉ 1 lần ở mẫu số** (`den8`) ⇒ về nguyên tắc `auc8`
> **có thể > 1** trên dữ liệu nhỏ. Bản sửa = `auc8c` (chỉ tính cặp `(T,T)` một lần) do phiên song song thêm vào
> `model_ruler.py` (kèm bằng chứng tổng hợp ở §10.1 của họ). **Ảnh hưởng đọc số:** độ lệch ước lượng
> `≈ |P∩T|·|N∩T|·0,5 / den8 ≈ 0,009` ⇒ **KHÔNG đổi bất kỳ verdict nào** (Δ của `A44`/`V0` đều bất lợi
> ≥ 0,005 ở **cả 3** chỉ số, và độ lệch gần như chung cho mọi arm) — **nhưng con số M1 tuyệt đối/Δ ở §13.1–13.2
> phải được THAY bằng bản `auc8c`** khi phiên song song chạy lại xong. `M2`/`M3` **không** bị ảnh hưởng.

## 13.2 Δ SO VỚI **CẢ HAI** ĐỐI CHỨNG (ghép cặp 140.238 tick; `*` = ngoài CI **cả hai** độ rộng)

| so sánh | Δ`auc8` (M1) | Δ`lift@8/12/16` (M2) | Δ`ρ_lab` (M3b) |
|---|---|---|---|
| **`A44 − A45`** (C1 retrain) | **−0,005665** `*` [−0,007689;−0,003674] | **−0,003075\* / −0,003076\* / −0,002572\*** | **−0,012847** `*` [−0,014797;−0,010926] |
| **`A44 − 45deploy`** (MỐC) | **−0,005185** `*` | **−0,002735\* / −0,002587\* / −0,002328\*** | **−0,013177** `*` |
| **`V0 − V5`** (C2 noise) | **−0,005007** `*` | **−0,003032\* / −0,003779\* / −0,004360\*** | **−0,031295** `*` |
| **`V0 − 45deploy`** (MỐC) | **−0,011313** `*` | **−0,005065\* / −0,004572\* / −0,004241\*** | **−0,022584** `*` |
| `A45 − 45deploy` (nền nhiễu **retrain**) | +0,000480 (không) | +0,000340 / +0,000488 / +0,000245 (**không**) | −0,000329 (không) |
| `V5 − V1` (**bước nhiễu THUẦN** — bẫy OFI) | −0,001241 (**không**) | −0,000624 / −0,000392 / −0,000251 (**không**) | −0,000433 (**không**) |
| `V1 − 45deploy` (OFI thật vs MỐC) | **−0,005065** `*` | −0,001409 / −0,000401 / +0,000370 (**không**) | **+0,009145** `*` |

- **Nền nhiễu retrain & bước nhiễu thuần đều ~0, KHÔNG ngoài CI ở CẢ 3 chỉ số chính** ⇒ (i) khác biệt của
  `A44`/`V0` là **thật**, không do máy; (ii) **không dính bẫy OFI** (nhiễu không "thắng"), và **đối chứng
  nhiễu đúng chức năng**.
- 🔴 **`V1 − 45deploy` MÂU THUẪN**: `auc8` **xấu hơn** ngoài CI nhưng `ρ_lab` **tốt hơn** ngoài CI (lift thì
  ngang) ⇒ **thước vẫn chưa cho một thứ tự duy nhất**; ghi rõ, không che. (Đây là lý do luật cần "cả 2/3 +
  không chỉ số nào xấu ở 72h" — nhưng ở 72h lại không đo được, xem §13.4.)

## 13.3 LUẬT GO — KẾT QUẢ

| ứng viên | M1 | M2 | M3 | PASS | **GO (h=4h)** | `fail_hẹp` |
|---|---|---|---|---|---|---|
| **`A44`** (bỏ `rvol15m`) vs {`A45`, `45deploy`} | **fail** | **fail** (fail **cả 3** mức K) | **fail** | **0/3** | **NOT GO** | False |
| **`V0`** (cắt 45 → 21) vs {`V5`, `45deploy`} | **fail** | **fail** (fail **cả 3** mức K) | **fail** | **0/3** | **NOT GO** | False |

⇒ **Q11 ĐÚNG** (và nặng hơn dự đoán: fail **cả 3** mức K của M2 chứ không chỉ K=8); **Q12 ĐÚNG**.
⇒ `GIU 45` được **tự nói lại**, và lần này bằng **số đo RAW đầy đủ**, không còn phụ thuộc AGG.

## 13.4 h = 72h — **KHÔNG ĐÁNH GIÁ ĐƯỢC** (đo được, không phải suy đoán)

Đo trực tiếp `z[:,0..2]` của **mọi** thư mục bins: **NaN 100 %** (`45deploy` 16 fold + 5 arm × 16 fold;
`p` (4h) thì 0,0000 % NaN). ⇒ **KHÔNG arm nào có ĐIỂM 72h** (trainer ghi thẳng 3 NaN vào `write_bin`) ⇒
**điều kiện (ii) của luật GO KHÔNG ĐÁNH GIÁ ĐƯỢC**, và **Q13 không kiểm được**.
**Không thay thế bằng điểm 4h** (làm vậy là bịa số) — phiên song song đã chặn đúng ở code.
**Hệ quả đọc luật (ghi rõ):** round này chỉ đánh giá được **điều kiện (i)**. Vì (i) đã **0/3** nên (ii)
**không thể** đảo ngược kết luận ⇒ **NOT GO** vẫn đứng vững. **Nhưng** nếu tương lai có ứng viên PASS (i),
thì luật **vẫn không thể cấp GO** khi thiếu (ii) — cần **hoặc** train model 72h (ngoài phạm vi Tầng A /
cần owner quyết), **hoặc** owner sửa luật. Đây là **khoảng trống hạ tầng**, không phải số xấu.

## 13.5 KINH TẾ (báo kèm theo §12.2, **KHÔNG** dùng cho luật GO) — `45deploy`

| chỉ số | giá trị | CI |
|---|---|---|
| `gross@8` (mốc cả tick = **−0,000062**) | **+0,000148** | [−0,000473; +0,000774] |
| `net@8` = `gross@8 − 0,008` | **−0,007852** | [−0,008473; −0,007226] |
| `AUC` whole-tick (nhị phân) | **0,668537** | [0,663102; 0,674067] |
| `pairwise P(s_A>s_B \| y_A>y_B)` (liên tục) | **0,482131** (< 0,5) | [0,480996; 0,483303] |
| decile gộp trên `retEnd` (gross) | ρ = **−0,1394**, dốc **−0,00008** | — |

🔴 **Cặp số quan trọng nhất của cả vòng** (trả lời trực tiếp câu hỏi chủ dự án): cùng một model, cùng tick —
- **Nhãn train**: đường decile gộp **đơn điệu hoàn hảo** D1→D10 = `0,1099 → 0,2682` (ρ=+1,0000, dốc +0,1584);
- **Kết quả thật (`retEnd`)**: dốc D10−D1 = **−0,00008** (gần như **phẳng**), ρ gộp **−0,1394**.
⇒ Model **xếp hạng rất tốt theo XÁC SUẤT TRÚNG**, và **gần như KHÔNG xếp hạng được theo ĐỘ LỚN kết quả**.
Điểm cao ⇒ coin dễ "bơm >1,5 %" hơn, **KHÔNG** ⇒ coin lãi nhiều hơn; sau chi phí 0,008 thì top-8 **âm**.

## 13.6 ĐỐI CHIẾU DỰ ĐOÁN KHOÁ TRƯỚC (bộ mới)

| # | dự đoán | kết quả |
|---|---|---|
| Q8 | `0,55 < AUC@top8 < 0,80`, không hứa hơn whole-tick | **ĐÚNG** (0,6239 < 0,6685) |
| Q9 | `lift@8 ≥ lift@12 ≥ lift@16` | **ĐÚNG** (mọi arm) |
| Q10 | M3(a) PASS trên nhãn train NHƯNG ρ âm trên `retEnd` | **ĐÚNG** (ρ_lab=+1,0000 vs ρ gộp `retEnd` = −0,1394) |
| Q11 | `A44`/`V0` fail `K=8` của M2 | **ĐÚNG** (fail **cả 3** mức K) |
| Q12 | NOT GO cả hai | **ĐÚNG** (0/3 cả hai) |
| Q13 | `lift@8(72h) > 0` nhưng nhỏ hơn 4h | **KHÔNG KIỂM ĐƯỢC** (không tồn tại điểm 72h) |

## 13.7 VIỆC TIẾP (đề xuất)

1. **Bịt 72h**: muốn dùng được điều kiện (ii) thì phải **có model 72h** (train — ngoài phạm vi Tầng A,
   cần owner duyệt) — hoặc owner **sửa luật** cho khớp hạ tầng hiện có. **Không** thay bằng điểm 4h.
2. **Kinh tế cross-horizon** (điểm 4h × nhãn `retEnd_72h`) đã có cờ `--label-horizon` — chạy như **báo cáo
   kinh tế**, **không** áp luật GO.
3. **Ghi vào pre-reg vòng sau**: (a) M3(a) **không phân biệt** (cả 6 arm ρ=1,0) ⇒ cân nhắc bỏ (a) hoặc
   thay bằng ngưỡng chặt hơn; (b) `V1 − 45deploy` cho **hai tín hiệu ngược chiều** ⇒ cần luật hoà giải
   TRƯỚC khi dùng thước để đổi model.
