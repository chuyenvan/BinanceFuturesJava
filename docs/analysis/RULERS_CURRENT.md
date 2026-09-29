# RULERS_CURRENT — Bộ thang đo đang hiệu lực + RÀO CỨNG + Luật CI (tổng hợp 2026-09-26)

Mục đích: một chỗ để owner **chốt điều chỉnh**, sau khi phát hiện *"alpha hiện sống bằng ĐUÔI"*.
Nguồn: đọc **doc + code** (`file:line`), không theo trí nhớ.

---

## 1. TẦNG A — thước MODEL (chọn model, **KHÔNG** nhìn PnL/equity)

| mã | thang | ghi chú |
|---|---|---|
| **M1′** | `auc8` (AUC@top8) | bản đúng `auc8c` (sửa lỗi đếm 2 lần) |
| **M2′** | `lift8` **và** `lift12` **và** `lift16` | **cả 3** phải OK |
| **M3′** | decile: `dec_rho_lab` (+ `dec_mono`), `D10−D1` cùng dấu | |
| phụ | `rank-IC`, `prec8`, `auc`, `pacc` | chỉ tham khảo |
| ngưỡng | `h ∈ {4h, 72h}` | |

- **Luật chốt:** **≥ 2/3** thang có Δ > 0 **ngoài CI** vs **CẢ 2 đối chứng bắt buộc** (retrain `A45 − 45deploy`, nhiễu `V5 − V1`).
- Cờ **"FAIL HẸP"**: chỉ **báo cáo**, **không tự nới ngưỡng**.
- Code: `research/analysis/model_ruler.py:83` (`RAW_METRICS`), `:90` (`MAIN_METRICS`).

## 2. TẦNG B — thước HỆ THỐNG / SIM (**5 rate**)

`n` · **`win%`** · **`TSloss%`** · **`mP|SM`** · **`mP|SL`** · **`meanP`** (+ `mMargin`)
Code: `research/analysis/x1_rates.py:22`.

- **Luật bằng chứng:** **≥ 2 rate ngoài CI** cùng hướng **TỐT**.
- CI: bootstrap **block-72h**, **2000 rep**, seed **20260905**, `inflate(k)` (không hardcode).
- ⚠️ **Tất cả 5 rate này đều là MEAN-based** ⇒ 1–2 leg đuôi có thể quyết định.

## 3. TẦNG TIỀN — PnL **luật thoát** (`y = gross` của arm +7% → ratchet → TS 168h)

`ic` · `pacc` · `dec_mono` · `dec_rho` · **`glift8`** · **`netm8`** (+ `auc8c`)
Chỉ số quyết định: **net trên 1 đơn vị gross-exposure**.

- **Luật:** "có giá trị tiền" chỉ khi Δ vs **cả 2** đối chứng **ngoài CI** ở `f = 0,006`, **dưới trần gross 70%**.
- ⚠️ Cũng **mean-based** ⇒ đã bị đuôi chi phối (bỏ top-5% ⇒ PnL âm).

## 4. 🔴 RÀO CỨNG (veto — **không phải** bằng chứng)

| rào | giá trị **hiện hành** | ghi chú |
|---|---|---|
| `maxDD` (theo năm) | **≤ 40%** | nới từ ≤30% (owner: *"30 hay 40 đều ok… đánh 1x"*) |
| `UW` (ngày) | **≤ 250** | nới từ ≤200 |
| quý xấu nhất | **≥ −20%** | nới từ −15% |
| **0 năm âm** | **CỨNG, tuyệt đối** | *"năm âm thì trade làm gì"* |
| tập trung 1 coin | **≤ 15%** (CỨNG) | `CONC_CAP_PERCOIN` |
| **trần gross exposure** | **70% (CỨNG)** | owner 26/09 05:35; bind theo từng tick ⇒ size **0,83×** |
| phí chuẩn nghiên cứu | **0,6%/vòng** | owner 26/09 05:35 |
| ⚠️ *chưa có* | **tập trung LỢI NHUẬN** (top-1%/5% lệnh) | **lỗ hổng lớn nhất hiện tại** |

Nguồn: `docs/runbooks/RISK_APPETITE.md:134-136`, §6, §7.3 (MTM mốc phút), §8.

## 5. LUẬT BẰNG CHỨNG DÙNG CHUNG

- **≥ 2** chỉ số/rate **ngoài CI** cùng hướng tốt · vs **CẢ 2** đối chứng (retrain + nhiễu cùng NaN-mask)
- CI: block-72h · 2000 rep · seed 20260905 · `inflate(k) = sqrt(2·ln k)`
- **Multi-seed:** hiệu ứng phải vượt CI ở **≥ 3 seed** (bẫy #7 `AGENT_RUNBOOK`)
- Mọi so sánh phải **cùng nguồn hạ tầng** (Kaggle ↔ Kaggle, Oracle ↔ Oracle)

## 6. VẤN ĐỀ + ĐIỀU CHỈNH ĐỀ XUẤT (chờ owner chốt)

**Vấn đề:** *mọi* thang ở tầng B và tầng tiền đều **mean-based**; rào cứng **không** có thang nào chặn **tập trung lợi nhuận**. Bằng chứng: leg bị chặn mang **82–114%** tổng PnL · **top-1% lệnh = 24–41%** lãi · **bỏ top-5% ⇒ PnL ÂM**.

| # | điều chỉnh đề xuất | trạng thái |
|---|---|---|
| 1 | **Thêm 7 thang tail-robust**: winsor-mean `[p1,p99]`/`[p5,p95]` · trim-mean 1%/5% · median+sign-test · tail-free sum (loại top-1/5/10%) · concentration (Herfindahl, %PnL top-1/5%) · IC bền (winsorised + IC **trung vị** theo tick) · downside | đang đo — `PREREG_TAIL_ROBUST_RULERS.md` |
| 2 | **Siết luật ≥2**: chỉ tính **thang tail-robust**; thang mean-based **hạ xuống mức BÁO CÁO** | chờ chốt |
| 3 | **Thêm 2 rào cứng mới**: ① `%PnL từ top-1% lệnh ≤ X%` ② **`tail-free PnL` (loại top-5%) > 0** | chờ chốt **X** |
| 4 | **Làm mịn CI**: block 24/72/168 · NREP 2000/5000 · ≥2 seed · báo **tỷ số độ rộng CI / điểm** để loại thang không phân giải được | đang đo |
| 5 | **Hạ cấp** `meanP` / `mP|SM` / `mP|SL` / `ic` / `glift8` / `netm8` về **báo cáo**, không làm cổng quyết định | chờ chốt |

**Cần owner chốt đúng 3 điều:** (a) **X%** cho rào #3-① · (b) **`tail-free PnL > 0` có thành rào CỨNG không** · (c) **hạ cấp thang mean-based về báo cáo** — có/không.

---

## 7. OWNER CHỐT — 2026-09-26 23:11 (cập nhật RÀO + thang đo)

- **(a) RÀO CỨNG MỚI:** `%PnL đến từ top-1% lệnh` **≤ 15%** (owner chốt `15%`).
- **(b) RÀO CỨNG MỚI:** **tail-free PnL: BỎ TOP-20% lệnh ⇒ PnL vẫn phải DƯƠNG**
  *(mạnh hơn đề xuất ban đầu là top-5%)*.
  ⚠️ **Hệ quả phải nói rõ và kiểm bằng số:** hiện **bỏ top-5% đã ÂM** (T100/GD92) ⇒ **mọi biến thể hiện có
  gần như chắc chắn FAIL rào này** ⇒ dưới rào mới, **không cấu hình nào đủ điều kiện go-live**.
  Đang kiểm định lượng ở vòng riêng (`RESULT_RATE_REDUNDANCY`): bỏ 5% / 10% / 20%, từng năm + toàn kỳ.
- **(c) ĐANG CHỜ:** hạ cấp thang *mean-based* về mức **báo cáo** (không làm cổng quyết định), kèm câu hỏi
  **các rate có TRÙNG NHAU không** (`n` · `win%` · `TSloss%` · `mP|SM` · `mP|SL` · `meanP`) — nếu có cặp
  trùng/phụ thuộc đại số thì luật *"≥2 rate ngoài CI"* **không còn là 2 bằng chứng độc lập**. Đang phân tích.

**⇒ Luật bằng chứng sẽ đổi thành:** *"≥2 thang **TAIL-ROBUST** + **KHÔNG trùng lặp** ngoài CI vs cả 2 đối chứng"*.

---

## 8. OWNER CHỐT LẠI — 2026-09-26 23:17: **NÂNG rào tail-free lên 50%** (thay §7-(b))

Nguyên văn: *"cần cứng, chấp nhận làm lại từ đầu. **20% với tôi vẫn rủi ro lắm**, nếu được để **50%** rồi không ra mới hạ nó xuống."*

- **(b′) RÀO CỨNG (thay thế (b)):** **bỏ TOP-50% lệnh ⇒ PnL vẫn phải DƯƠNG.**
- **Ý nghĩa tương đương (phải ghi rõ để không hiểu sai):** bỏ top-50% > 0 ⟺ **tổng NỬA DƯỚI lệnh > 0**
  ⇒ gần với **"lệnh TRUNG VỊ phải có lãi"** (median leg > 0), không chỉ "lãi không phụ thuộc vài leg".
- **(a) giữ nguyên:** `%PnL đến từ top-1% lệnh ≤ 15%`.
- ⚠️ **Hệ quả đã biết trước:** bỏ top-**5%** đã ÂM (T100/GD92) ⇒ bỏ top-**50%** sẽ **âm rất sâu**
  ⇒ **mọi biến thể hiện có FAIL** ⇒ **go-live bị CHẶN cho tới khi có nguồn lãi không-đuôi**.
- **Đổi bản chất mục tiêu:** từ *"tối ưu hệ thống hiện tại"* sang *"tìm CẤU TRÚC LÃI không phụ thuộc đuôi"*
  (hệ quả: các luật kiểu arm +7% → trailing, ăn bằng vài leg lớn, **không thể** thoả rào này).
- **Cơ chế thoát đã thoả thuận trước:** nếu **không cấu hình nào ra** ⇒ owner **hạ rào**; đây **không** tính là thất bại.

---

## 9. KẾT QUẢ KIỂM TRÙNG LẶP RATE (`RESULT_RATE_REDUNDANCY`, `8ddc173`) + **SỬA SAI §6**

### 9.1 🔴 SỬA SAI §6 (câu "bỏ top-5% ⇒ PnL ÂM" là **SAI**)
Số đúng (448 run DEV ≤2025-12-31, 1800 ô run×năm): **bỏ top-5% VẪN DƯƠNG** (+2.771 T100 · +14.794 GD92).
**Ngưỡng gãy thật `q*`** (bỏ bao nhiêu % thì PnL = 0): **5,5% (T100) · 7,0% (GD92) · 19,0% (KEEPLEG0/T170)**.
⇒ Cảnh báo vẫn đúng về bản chất (lãi tập trung ở ~5–19% lệnh đầu), nhưng **con số "5%" em nói trước đó là bịa** — đã sửa.

### 9.2 TRÙNG LẶP (đo, có `file:line`)
- Định nghĩa: `c3_rates.py:94-109` (`n :102` · `win% :103` · `TSloss% :104` = **SL = dừng lỗ cứng ≈ nhóm LỖ** · `mP|SM :105` = **SM = trailing vào vùng lãi ≈ nhóm THẮNG** · `mP|SL :106` · `meanP :107` · `mMargin :108`).
- **Đồng nhất thức đại số:** `meanP ≡ (1−TSloss%/100)·mP|SM + (TSloss%/100)·mP|SL` — đúng **tuyệt đối (≤1e-15) trên 408/408** run ⇒ **`meanP` KHÔNG mang thông tin mới**.
- **Cặp `|ρ|≥0,9` DUY NHẤT: `win%` ↔ `TSloss%`** (Pearson **−0,992**, Spearman −0,930) ⇒ **không phải 2 bằng chứng độc lập**.
- **Độc lập THẬT:** `mP|SM` · `mP|SL` · `mMargin`; `n` **không phải rate** (quy mô mẫu + mẫu số chung).
- ⇒ **Bộ rate tối thiểu: `{TSloss% · mP|SM · mP|SL}` (+ `mMargin` = 4)**. **Luật siết lại:**
  *"≥2 rate ngoài CI, **tối đa 1 rate** thuộc nhóm tần suất `{win%, TSloss%}`, **KHÔNG tính `meanP`**"*.
- **Bỏ/hạ về báo cáo:** `meanP` (trùng đại số) · `win%` (ρ −0,99) · `n` (không là rate).

### 9.3 Rào (a) `≤15%` và (b) `bỏ top-20% > 0` — kết quả
- **(a) 1/8 PASS**: `kg0-q998-15m` **12,91%**; còn lại 20,70–40,85% (**T100 40,85 tệ nhất**, `KEEPLEG0` 23,74).
- **(b) 4/8 PASS** (dương MỎNG): `q998-15m` +5.848 · `q998` +4.180 · `q999` +2.901 · `q995` +772.
  **ÂM:** `KEEPLEG0` −1.575 · `T170` −1.723 · `GD92` −61.183 · `T100` −76.850.
- **PASS CẢ (a)+(b): DUY NHẤT `kg0-q998-15m`** — nhưng nhịp 15′ **không tái lập nhịp live 1′** (0,255 vs 0,660 entry/ngày; tỷ lệ 0,440 < 0,60) + CAGR **11,08%** vs 27,14% ⇒ **dưới rào mới: KHÔNG cấu hình nào đủ go-live**.
- ⚠️ Chưa đo được `sel15`/`all15` (chỉ có `kernel-metadata.json` + `run.py`, **không có artifact output cục bộ**).

---

## 10. OWNER CHỐT **BỘ THƯỚC CHUẨN** — 2026-09-27 05:22 (owner: *"Ok"*)

### 10.1 Bộ 4 THƯỚC CHUẨN (dùng cho MỌI vòng từ nay — KHÔNG đổi nữa)
```
wl_ratio  ·  tf_5  ·  loss_mean  ·  conc_5          (dự bị: median)
```
- **`tf_5`** = net/leg sau khi **bỏ top-5% leg** · **`loss_mean`** = độ lớn lỗ trung bình
- **`wl_ratio`** = tỷ số mean-thắng / mean-thua · **`conc_5`** = tập trung PnL ở top-5% leg
- **`median`** = dự bị (không bắt buộc báo cáo, dùng khi cần kiểm chéo)
- **BỎ khỏi bộ chuẩn:** các thước còn lại của **cụm vị trí** (đã chứng minh trùng `tf_5`: `wmean_p1p99` · `wmean_p5p95` · `tmean_1` · `tmean_5` · `tf_1` · `tf_10`) · `sign_frac` (**≡ `win%`**, ρ 0,999) · `conc_1` (trùng `conc_5` ở cấp run) · `ic_wmean`/`ic_med` (**chưa chấm được**: `pred15m` là 1 feature cố định, cần điểm đối tượng căn pool)

### 10.2 Bộ RATE giữ lại (`RESULT_RATE_REDUNDANCY`)
`{ TSloss% · mP|SM · mP|SL · mMargin }` với luật **siết**:
> **≥2 rate ngoài CI · TỐI ĐA 1 rate** thuộc nhóm tần suất `{win%, TSloss%}` · **KHÔNG tính `meanP`** (đồng nhất thức đại số, 408/408)

### 10.3 RÀO hiện hành (đầy đủ)
| nhóm | rào |
|---|---|
| **MỚI (owner 26/09)** | **(a)** `%PnL từ top-1% lệnh ≤ 15%` · **(b′)** **`bỏ top-50% lệnh` ⇒ PnL vẫn phải DƯƠNG** (CỨNG; cơ chế thoát: không cấu hình nào ra thì owner hạ rào) |
| **CŨ (appetite `latest`)** | maxDD ≤ 40%/năm · UW ≤ 250 ngày · quý xấu nhất ≥ −20% · **0 năm âm (CỨNG)** · **conc 1 coin ≤ 15% (CỨNG)** · **trần gross 70% (CỨNG)** · phí chuẩn **0,6%/vòng** |
| **Luật bằng chứng** | ≥2 chỉ số ngoài CI cùng hướng tốt vs **CẢ 2** đối chứng (retrain + nhiễu) · block-72h · 2000 rep · seed 20260905 · `inflate(k)` · multi-seed ≥3 |

### 10.4 HỆ QUẢ SỐ HỌC đang treo (để không quên)
- Với bộ thước + rào trên: **chưa cấu hình nào đủ go-live** (rào (a) giết 7/8; (b′) giết 8/8 — `RESULT_TAIL50_RULER_REDUNDANCY.md`).
- **Nhịp:** con số hay được trích (**CAGR ~27%**) là con số **1′ cho tất cả** — **KHÔNG phải** con số live. Cấu hình **đúng thiết kế live** (`sel15`: selector 15′ + BIG_DOWN/DCA 1′) = **CAGR ~17,3%** (`RESULT_SIM_CADENCE_MATCH.md`).
  ⇒ **Còn 1 câu owner chưa chốt: live giữ 15′ hay đổi sang 1′** (đổi ⇒ phải sửa `ENTRY_GRID_MIN=15L`, `DetectEntrySignal2TradeNormal.java:988` — **đụng production, cần duyệt riêng**).

---

## 11. ERRATA QUAN TRỌNG — **TRẦN GROSS 70 % KHÔNG BIND** & **BỎ kết luận "size 0,83×"** (`RESULT_GROSS_ASYMMAP`, `42a48cd`)

- **2 công thức `gross` cùng dạng** `100 × (%equity/lệnh) × (số vị thế đồng thời)`, nhưng **khác nguồn `d`**:
  - MỚI (`size_count_score.py`) lấy `Σ margin_leg_đang_mở(t)/equity(t)` ⇒ **1,74 % TB / 49,53 % MAX**
  - CŨ (`cap70_fee06.py`) lấy **`d` từ POOL ỨNG VIÊN** (`d_mean 24,409`) trong khi ledger thật `d_mean = 0,531` ⇒ **lệch 46,0×**
  - Trên **cùng** `cd-sel15`: `G_old[ledger]` = **1,06 % / 48,0 %** ⇒ **khớp định nghĩa mới** ⇒ **định nghĩa ĐÚNG = ledger**
- ⇒ 🔴 **ĐÍNH CHÍNH**: câu *"`K=12` phá trần ⇒ size phải co 0,83×"* (dùng ở §10.3 / `RISK_APPETITE.md` §8) **là SAI** — nó dựa trên `gross_max[pool](K=8)=84 %>70`. Gross **thật** ở K=8 chỉ **48–49,5 %** (< `U_MAX=0,60`) ⇒ **BỎ kết luận đó**.
  *(Chỉ **14/461** run cũ vượt 70 % theo **cả 2** định nghĩa — trần chỉ bind ở họ đó.)*
- **Quét 461 run** (`RESULT_GROSS_ASYMMAP`): **PASS (a) = 3/461** · **PASS (b′) = 0/461** (TF50 max −174) · **PASS cả hai = 0**
- **`asym`**: min **0,261** (`R2_trail`) · **32 run `asym<1`** nhưng **tất cả** win-rate 29–42 %, top-1 **35–96 %**, TF50<0 ⇒ **fail cả (a) và (b′)**. Pipeline `x1_gs_t170`: min **0,705** (`sl3-v2-sl3`, **lỗ**), median **3,03**
  ⇒ **`asym<1` + PnL DƯƠNG BỀN: CHƯA TỒN TẠI** — *đã thử, không phải chưa thử*
- **Cấu trúc kéo `asym` xuống**: win-rate thấp ≤45 % · **cắt lỗ sớm/ngắn** (`PRE_ARM_SL −0,03` ⇒ 0,705) · `loss_mean` nhỏ (corr `asym~loss_mean` **−0,47**, `~sign%` **+0,25**)
- **3 giá trị CHƯA THỬ** (đề xuất sim mới): ① `SIM_PRE_ARM_SL=−0,05` · ② `SIM_PRE_ARM_SL=−0,03` + `SELECTOR_RANK_TOPK=16` · ③ `SIM_LOSER_TIME_STOP_HOURS=8`

---

## 12. OWNER CHỐT LẠI RÀO — 2026-09-28 15:51: `(b′)` **HẠ TỪ 50% → 25%**

Nguyên văn: *"a. giữ 15%  b giảm 50% về 25 nhé"*
- **(a)** `%PnL từ top-1% lệnh ≤ 15%` — **GIỮ NGUYÊN**.
- **(b′)** **bỏ TOP-25% lệnh ⇒ PnL vẫn phải DƯƠNG** *(thay cho bỏ top-50%)*. Đây là **cơ chế thoát đã thoả thuận trước** ("không ra mới hạ nó xuống") — dùng đúng lúc, và **không tính là thất bại**.
- **Ý nghĩa (vẫn phải ghi rõ để không hiểu sai):** bỏ top-25% > 0 = **75% lệnh còn lại (kể cả nhóm yếu) vẫn phải có lãi ròng**.
- **Mốc tham chiếu đã đo** (từ `RESULT_TAIL50_RULER_REDUNDANCY` `76cc051`):
  bỏ **20%**: 4/8 dương (`q998-15m` +5.848 · `q998` +4.180 · `q999` +2.901 · `q995` +772) · bỏ **30%**: **1/8** (`q998-15m` +2.328) · bỏ **50%**: **0/8**.
  ⇒ **mức 25% nằm giữa 20% và 30%** ⇒ **phải đo lại đúng 25%** (không suy diễn nội suy).
- Hệ quả cần nhớ: rào **(a) = 15%** vẫn **giết** các arm `q995/q998/q999` (vì (a) của chúng ≈ **20,7–23,5%**) ⇒ tổ hợp (a)=15% + (b′)=25% **có thể vẫn không mở được cấu hình nào deploy được** — đang đo để chốt bằng số.

**ĐÃ ĐO (2026-09-28, `RESULT_TAIL25`):** sanity `TF(20/30 %)` **khớp tuyệt đối `76cc051`**. **Bỏ-25 % = 1/8 dương** = `kg0-q998-15m` (+4.002; CI raw95 [−2.140,+9.199] **chứa 0**). **PASS cả (a)+(b′) = duy nhất `kg0-q998-15m`** — **nhưng trượt bài kiểm nhịp (0,440<0,60) + CI chứa 0 ⇒ KHÔNG deploy được**. ⇒ **dưới (a)=15 % + (b′)=25 % KHÔNG cấu hình nào go-live**; 2 lựa chọn ở `RESULT_TAIL25` §5.

---

## 13. RESET 2026-09-28/29 — **LUẬT 4 TẦNG** thay "superiority" + `(a)/(b′)`; **CHI PHÍ THẬT**; KẾT LUẬN **GIỮ `B*`**

Nguồn: `PLAN_OPENCLAW_BASELINE_RESET_20260928.md` + `PLAN_OPENCLAW_ADDENDUM_20260928.md` (MASTER); **owner duyệt** ("Ok tiếp đi", 2026-09-28 22:38). Thực thi D0–D5.

### 13.1 CHI PHÍ THẬT (`RESULT_COST_TRUTH`, `d059cc3`) — **BỎ `0,8 %/vòng` làm chi phí**
- Sim **vào ở CLOSE nến 1 PHÚT** (`SimulatorMarketLevelTicker1MStopLoss.java:1372`); ra ở `priceClose`/`min(open,close)`. ⇒ chi phí sim ĐÚNG = **`fee + spread(±impact)`**, **KHÔNG** phải slip.
- Trên **991 chân THẬT**: slip CÓ DẤU ≈ 0 cho **mọi** loại leg (CI chứa 0); **riêng leg VÀO LÚC SẬP = +1,675 %/chân** (CI [+0,90,+2,67], n=37) = **LOOK-AHEAD của "vào ở close"**, **KHÔNG** phải phí thị trường.
- **3 mức: `base 0,112` · `stress 0,150` · `legacy 0,800` (%/vòng)**. Key có sẵn, gated: `SIM_RATE_FEE` + `SIM_SLIPPAGE_RATE` (default = byte-identical).

### 13.2 LUẬT MỚI (thay §7/§8 + `(a)/(b′)` + luật "superiority")
**4 tầng:** (1) **RÀO RỦI RO** (maxDD **MTM phút** ≤40 %/năm · UW ≤250 · quý xấu ≥−20 % · 0 năm âm · conc 1 coin ≤15 %) · (2) **RÀO ĐỘ BỀN** (`q* ≥15 %` · `top-1 % lệnh ≤25 %` · **bỏ top-3 EPISODE** ⇒ ΣPnL >0) · (3) **NON-INFERIORITY** vs `B*` (win% ≥ −2,0pp · TSloss% ≤ +2,5pp) · (4) **MỤC TIÊU** (`Calmar_MTM ≥ B*` · `n ≥1,3×B*` · `conc ≤ B*`).
**BỎ khỏi luật** (đo **0/20 bind**, `RESULT_RESET_RULE_P1`): trần **gross ≤70 %** (max thực 59,7 %) · `mP|SM%`/`mP|SL%` tầng 3 (CI quá rộng) · "bỏ top-3 episode" trong tầng 2.
**`(a)/(b′)` = BỎ**: chứng minh toán học **bất khả thi** với lợi nhuận ~chuẩn (`(b′)` cần Sharpe năm ≈**8,1**; `(a)@15 %` cần ≈**3,6**) — khớp số đo: `(a)@15 %` chỉ **3/452** arm (0 bền), book U1 **210–382 %**.

### 13.3 KẾT QUẢ 3 vòng
- **D2** `a7016b0` (chấm lại 20 artifact cũ): tự kiểm KEEPLEG0/cd-sel15 **12/12 khớp** + MTM phút KEEPLEG0 **−19,96 %/UW 147,2** khớp `RESULT_INTRADAY_DD`; **T4 0/20 ⇒ giữ `B*`**; hạ phí lật **T1 6 / T2 2**, **KHÔNG lật** verdict "nới gate = rác".
  ⚠️ **Caveat**: công thức hậu kiểm `net_leg = pnl + (0,008−c)·notional` **lệch ~8,6 %** vs sim thật (bỏ compounding) ⇒ dùng **số D3** cho `@base`.
- **D3** `47a9d90` (sim Kaggle k=5, 11 run): `R0` parity **md5 `99e42b75` PASS**; **`R4` (size ×0,5 · K=16 · gate 1.55 · nhịp 1') = arm DUY NHẤT qua CẢ 4 TẦNG**, ở **cả `base` và `stress`** (Calmar 1,676 vs `B*` 1,661; n 2027 = 1,87×). `R2` FAIL T3 · `R1/R3` FAIL T4 · blocked=0 · gross MAX 55,9 %.
- **D5** `911ad42` (độ bền `R4`): **T1 episode jackknife = FAIL** (`Calmar_còn(3)` 2,70 < `B*` 4,15) ⇒ **TRẢ VỀ GIỮ `B*`**; T2 PASS nhưng **CI chênh `R4−B*` chứa 0** (biên +0,7…0,95 % = **NHIỄU**), chênh CAGR −5,62pp/ΣPnL −21 510 **âm ngoài CI**.

### 13.4 TRẠNG THÁI CHỐT (cập nhật 2026-09-29)
- **Không cấu hình nào thay được incumbent `B*` về CHẤT LƯỢNG** (P3: `R4` không hơn `B*`, thua CAGR) ⇒ **production KHÔNG đổi**
  (incumbent production vẫn `B*` = KEEPLEG0 + nhịp 1' + CONC_CAP 15 %); **KHÔNG tiêu `HOLDOUT_UNSEAL`** (2026 vẫn đóng).
- **OWNER CHỐT 2026-09-29** (hoàn tất việc treo (i)/(ii) + đổi baseline):
  1. **(i) Chính thức hoá luật 4 tầng §13.2** vào `docs/runbooks/RISK_APPETITE.md` §9 (thay "superiority" + `(a)/(b′)`).
  2. **(ii) `(a)/(b′)` gỡ khỏi mọi pre-reg mới** — bỏ hẳn (bất khả thi toán học: Sharpe năm ≈ 8,1 / ≈ 3,6).
  3. **Baseline nghiên cứu MỚI = `R4`** (owner chọn vì ưu tiên số lệnh; R3 loại vì kém rõ): KEEPLEG0 + CONC_CAP 15 % +
     `SIM_F_BASE=0.015` + `SELECTOR_RANK_TOPK=16` + `SIM_GATE_DYN_SCALE=1.55` + nhịp 1' + phí base —
     `docs/decisions/DECISION_BASELINE_R4.md` + `profiles/r4_kg0_k16_f015_g155.properties` (md5 `06fd6e9a…`).
  4. **T4 đổi: ƯU TIÊN SỐ LỆNH** — `n` là mục tiêu chính; `Calmar_MTM ≥ 0,90×baseline`; `conc ≤ baseline`.
     **Chỉ áp vòng MỚI, KHÔNG hồi tố P2/P3.**
- ⚠️ Quyết định là **KHẨU VỊ** (ưu tiên `n ×1,87`, DD −16,4 vs −19,9, conc 5,3 vs 7,1), **KHÔNG phải "win"**:
  `R4` KHÔNG hơn `B*` về Calmar (CI chứa 0) và THUA về CAGR (−5,62pp ngoài CI).
- **Track B: CHẾT** — "edge" `+0,074 %/ngày` = **artifact stop −10 %** (quyền chọn miễn phí); bỏ stop ⇒ chênh `+0,006 %/ngày`,
  CI [−0,034,+0,045] **chứa 0** (`RESULT_TRACKB_REDFLAGS`, `7f6e46d`).
- **Câu treo còn lại**: **live giữ 15' hay đổi 1'** (đổi ⇒ sửa `ENTRY_GRID_MIN` = đụng production).
