# PREREG — CHẤM LẠI P12 (ngưỡng rào) + P5 (rate/MTM)  ·  chốt TRƯỚC khi lập bảng đối chiếu

- Ngày: **2026-09-28** · HEAD khi chốt: `1329afd` · nhánh `module`
- Nguồn: `Claude outputs/AUDIT_20260928_B_bugs.md` §5 **P12** (§1 lỗi #25) và §5 **P5** (§1 lỗi #31, #32);
  §4 "độ tin cậy khối NULL".
- Phạm vi: **offline Python**, dùng lại output có sẵn (`kaggle_sim/out/<tag>/storage/printDone.csv`,
  `kaggle_sim/out/<tag>/logs/sim.out`, `intradaydd/series.npz`). **0 train · 0 sim · 0 Java.**
  DEV ≤ 2025-12-31. **KHÔNG chạm 2026 / 242 / ONNX / production.**

## 0. LUẬT BÁO CÁO (KHÓA — không đổi sau khi thấy số)

1. Chỉ báo cáo **ĐỔI** hay **KHÔNG ĐỔI** verdict. Không diễn giải lại, không mở ứng viên mới.
2. "Verdict" = **ô PASS/FAIL đã công bố** của (doc × cấu hình) đối với **rào cứng** (P12) hoặc
   **(rào cứng · (a) · (b′))** (P5). Không tính "verdict" cho các chỉ số phụ (CAGR, equity, n).
3. Ngưỡng/k/định nghĩa **khóa trước** ở §1–§3. Không nới/siết sau khi thấy số.
4. Cái gì không đo được offline thì ghi **KHÔNG ĐO ĐƯỢC**, không suy diễn thành PASS/FAIL
   (trừ ước lượng MTM có ghi rõ nhãn `[SUY LUẬN]`).

---

## 1. VIỆC 1 — P12: chấm lại verdict đã chấm bằng `x1_rates.py` với **sai ngưỡng**

### 1.1 Bối cảnh (định nghĩa cửa sổ)
`research/analysis/x1_rates.py:24-40` (commit `beaccba`, 2026-09-26 23:23) ghi rõ:
trước `beaccba`, **mặc định** khẩu vị của `x1_rates.py` là **`current` = 30/200/−15**, trong khi
khẩu vị owner đã chốt là **`latest` = 40/250/−20** (`docs/runbooks/RISK_APPETITE.md` §6–§8).
⇒ Mọi verdict rào cứng in ra bằng **mặc định** trong khoảng đó **chặt hơn ngưỡng owner**.

**Cửa sổ chấm lại (khóa):** các doc/artifact mà **lần sửa cuối nằm trong 2026-09-24 → 2026-09-26**
(theo `git log` — gồm cả commit tổ chức lại `docs/` `37fd502` 09-24 20:55) **và** đang mang một
verdict rào cứng **in bằng `x1_rates.py` với `--appetite current`** (in hoa/thường) **hoặc** bằng
mặc định `current` khi đó. Phạm vi hẹp hơn (chỉ doc *mới sinh* trong 09-24→09-26) báo cáo **riêng**.

### 1.2 Công cụ + ngưỡng (khóa)
- Tái lập đúng `x1_rates.hard_by_year` (`x1_rates.py:129-152`) trên chuỗi equity **NGÀY**
  (`logs/sim.out` dòng `Update ... => b:... unP:...`): theo **từng năm** `maxDD` (`cummax` trong năm),
  `UW` (số ngày âm liên tục dài nhất trong năm), `ret_nam`, `quy_min`; **và** theo **toàn kỳ**
  (`c3_rates.stats` — doc vòng in cột `UW` toàn kỳ).
- **A = `current` 30/200/−15 · B = `latest` 40/250/−20** (0 năm âm CỨNG; conc 1 coin ≤15% CỨNG —
  `x1_rates` KHÔNG đo conc, ghi chú riêng; gross 70% không đo ở đây).
- Verdict rào = **PASS** khi & chỉ khi **mọi** ràng buộc đúng ở **cả** cách đọc theo-năm **và** toàn-kỳ.
- **Dự đoán ghi trước:** mọi flip (nếu có) sẽ là **FAIL→PASS** và **chỉ** do `UW ∈ (200, 250]`
  (đây là khoảng duy nhất mà `latest` nới). MaxDD `∈ (30,40]` và `quy ∈ [−20,−15)` cũng có thể sinh flip.

### 1.3 Đầu ra (khóa)
Bảng `doc:line → verdict cũ → verdict mới → lý do đổi (UW/maxDD/quy)`. Đếm **số ô ĐỔI**.

---

## 2. VIỆC 2 — P5: chấm lại 4 vòng bằng **rate chuẩn `profit` %** + **maxDD/UW MTM phút**

### 2.1 Arm (khóa — dùng lại output có sẵn trong `/home/ubuntu/kaggle_sim/out/`, KHÔNG chạy sim mới)
| vòng | arm (nhãn → tag) |
|---|---|
| EXIT_STRUCT | A0=`cd-sel15` · A1=`xs-a1` · A2=`xs-a2` · A3=`xs-a3` |
| SHAPE1 | S0=`cd-sel15` · S1=`sh1-s1-sl05` · S2=`sh1-s2-sl03k16` · S3=`sh1-s3-ts8` · S4=`sh1-s4-sl03` |
| FAMILY2 | N0=`cd-sel15` · N1=`tp-n1` · N2=`tp-n2` · N3=`tp-n3` · N4=`tp-n4` |
| SIZE_COUNT | B0=`cd-sel15` · B1=`sc-b1` · B2=`sc-b2` · B3=`sc-b3` · B4=`sc-b4` |
→ **19 ô arm** (16 tag duy nhất; `cd-sel15` là nền dùng chung 4 vòng).

### 2.2 Rate (khóa) — sửa lỗi #31
- **Chuẩn `profit` %** (`c3_rates.rates`, `c3_rates.py:94-109`), đọc trên cột **`profit`**:
  `win%` · `TSloss%` · `mP|SM` · `mP|SL` · `mMargin`. **KHÔNG tính `meanP`** (đồng nhất thức đại số,
  `RESULT_RATE_REDUNDANCY` §9.2 = 408/408).
- Đồng thời chạy **bản CŨ trên cột `pnl` USDT** (`size_count_score.py:142-153`) để **đối chiếu tái lập**
  (bản cũ phải khớp số đã công bố), **không** dùng bản cũ để ra verdict.

### 2.3 Rào (a)/(b′) + 4 thước chuẩn (khóa) — định nghĩa **nguyên văn** `ofi_reorient_rulers.point()`
`net = pnl` (USDT); `o = sort(net)` giảm dần; `k1=ceil(0,01n)`, `k5=ceil(0,05n)`, `k50=ceil(0,5n)`:
- **(a)** `share_top1_pct = o[:k1].sum()/Σnet·100 ≤ 15%` **và** `Σnet > 0`
- **(b′)** `bottom_half_sum = o[k50:].sum() > 0`
- **4 thước chuẩn:** `wl_ratio = mean(thắng)/−mean(thua)` · `tf_5 = o[k5:].mean()` ·
  `loss_mean = −mean(thua)` · `conc_5 = o[:k5].sum()/Σnet`
- `q*` = q nhỏ nhất (bước 0,5%) sao cho `o[ceil(q/100·n):].sum() ≤ 0`.

### 2.4 maxDD/UW — MTM MỐC PHÚT (khóa + giới hạn đã biết)
- `intradaydd/series.npz` **chỉ có 4 nền**: `T170 · KEEPLEG0 · T100 · GD92` (12 khoá `c_/l_/r_`).
  Dữ liệu ticker 1 phút trên Oracle **đã mất** (`kaggle_data_hpo` chỉ còn `daily`) ⇒ **KHÔNG tính được
  MTM phút cho 16 tag của 4 vòng**.
- **Ghi trước:** `s3_intraday`/`intraday_dd` đo MTM phút **xấu hơn chuỗi NGÀY**: maxDD
  `T170 −8,12 · KEEPLEG0 −8,75 · T100 −10,13 · GD92 −7,76` pp (trung bình **−8,7 pp**); UW phút ≈ UW ngày
  trừ nền UW-bound lệch nền tảng (`T170 +52 ngày`).
- ⇒ Áp **hệ số dịch −8,7 pp** lên maxDD năm cho 16 tag, nhãn rõ `[SUY LUẬN]`, **và** báo cáo song song
  verdict theo chuỗi NGÀY (đúng như doc vòng đã in). UW giữ nguyên chuỗi NGÀY (UW-bound ≈ nhau).
- Rào cứng vẫn là `latest`: `maxDD ≤ 40%/năm` · `UW ≤ 250` · `quy ≥ −20%` · **0 năm âm** · **conc 1 coin ≤ 15%**.

### 2.5 Đầu ra (khóa)
`arm → verdict cũ → verdict mới` cho **(rào · (a) · (b′))**, ghi rõ đổi vì `rate` / `MTM` / `rào` nào.

---

## 3. VIỆC 3 — câu phải trả lời (khóa)
(1) P12: bao nhiêu verdict ĐỔI, liệt kê. (2) P5: bao nhiêu arm ĐỔI verdict, liệt kê.
(3) Có kết luận nào **ĐẢO** (PASS→FAIL hay ngược) không — nếu có, cái nào **nghiêm trọng nhất**.
(4) Khối NULL hiện tại **còn vững** không; **đề xuất 1–3 vòng nên chạy lại** (ưu tiên).

## 4. MỤC BỎ (khóa)
- KHÔNG đo `meanP` (đồng nhất thức) · KHÔNG dùng rate trên cột `pnl` để ra verdict.
- KHÔNG tính MTM phút cho 16 tag (không có dữ liệu) — chỉ ước lượng có nhãn.
- KHÔNG chấm lại tier MODEL/money-ruler (ngoài phạm vi P12/P5).
- KHÔNG mở lại ứng viên; KHÔNG đụng 2026/242/ONNX/production.
