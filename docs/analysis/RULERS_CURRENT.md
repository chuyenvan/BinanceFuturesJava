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
