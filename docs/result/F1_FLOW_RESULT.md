# F1_FLOW — KET QUA

Pre-reg: `docs/prereg/PREREG_F1_FLOW.md` (commit `576e6c2`, viết TRƯỚC run đầu tiên).
Chấm: `research/analysis/f1_flow.py` + `qret_ladder.py` + `fsrun/qret.py` (3 nguồn khớp nhau).
4 run, 1 dataset dùng chung, không có run thứ 5.

## 1. Parity gate — PASS

| | md5 `printDone.csv` | equity cuối | n lệnh |
|---|---|---|---|
| neo `C2b` | `8f7afdfb27b15f5b6d4c886700def93c` | 60,390 | 970 |
| `F1_parity` | `8f7afdfb27b15f5b6d4c886700def93c` | 60,390 | 970 |

Byte-identical. `F1_parity` khai báo tường minh `SIM_F_BASE=0.03` mà vẫn ra đúng
baseline ⇒ đường ống bù `F_BASE` không tự nó làm lệch kết quả. Batch hợp lệ để chạy tiếp.

## 2. KIỂM SOÁT C1 — HỢP LỆ

`mean(tổng margin đang mở / equity)` theo ngày, ngưỡng ±20% so với `F1_parity`:

| Tag | C1 | lệch vs parity | |
|---|---|---|---|
| `F1_parity` | 0.0615 | +0.0% | OK |
| `F1_k16` | 0.0641 | **+4.1%** | OK |
| `F1_k24` | 0.0642 | **+4.4%** | OK |
| `F1_k32` | 0.0640 | **+4.0%** | OK |

Cả 3 biến thể lệch ≤ +4.4%, xa ngưỡng ±20%. **Phép bù `K × F_BASE = 0.24` giữ được
tổng exposure ⇒ so sánh HỢP LỆ, được phép phán quyết.**

Lệch +4% là hệ quả của throttle phi tuyến `(1 − U/U_MAX)` như đã cảnh báo ở pre-reg
mục 11, nhưng biên độ quá nhỏ để đảo bất kỳ kết luận nào dưới đây.

## 3. SANITY vị thế — thao tác CÓ tác dụng

| Tag | K | vị thế đồng thời TB | n lệnh | margin/lệnh (med) |
|---|---|---|---|---|
| `F1_parity` | 8 | 2.86 | 970 | 969 |
| `F1_k16` | 16 | 5.35 | 1,659 | 481 |
| `F1_k24` | 24 | 7.59 | 2,255 | 332 |
| `F1_k32` | 32 | 9.78 | 2,779 | 253 |

Tăng đơn điệu 2.86 → 9.78. **K LÀ đòn bẩy dòng thật**, không phải param trơ, và gate
không bind. Nhánh "K không phải đòn bẩy" của pre-reg KHÔNG kích hoạt.

## 4. PRIMARY — `sd(daily equity return)` + Sharpe

n = 910 quan sát ngày mỗi run.

| Tag | K | `sd(daily)` | `mean(daily)` | Sharpe |
|---|---|---|---|---|
| `F1_parity` | 8 | **0.008098** | 0.000632 | **1.491** |
| `F1_k16` | 16 | **0.007581** | 0.000490 | 1.234 |
| `F1_k24` | 24 | **0.007113** | 0.000416 | 1.117 |
| `F1_k32` | 32 | **0.006913** | 0.000355 | 0.980 |

`sd` **giảm đơn điệu theo K** — đúng như pre-reg dự đoán. Kênh phương sai của giả
thuyết đa dạng hoá ĐÚNG.

Nhưng đó là phần duy nhất đúng. `mean(daily)` giảm NHANH HƠN NHIỀU:

- `sd` giảm **−14.6%** (0.008098 → 0.006913)
- `mean` giảm **−43.8%** (0.000632 → 0.000355)

⇒ **Sharpe giảm đơn điệu 1.491 → 0.980 (−34%).** Dự đoán "Sharpe tăng" SAI.

## 5. Ràng buộc CỨNG — 3/3 biến thể bị LOẠI

| Tag | maxDD (≤15%) | underwater (≤120d) | năm âm | quý < −5% | |
|---|---|---|---|---|---|
| `F1_parity` | −13.12% | 93d | không | không | **PASS** |
| `F1_k16` | **−17.24%** | **195d** | không | không | **LOẠI** |
| `F1_k24` | **−16.94%** | **227d** | **2022: −1.28%** | không (−4.39%) | **LOẠI** |
| `F1_k32` | **−16.63%** | **254d** | **2022: −1.75%** | không (−4.96%) | **LOẠI** |

Xác nhận độc lập bằng `fsrun/qret.py`: underwater 93 / 195 / 227 / 254 ngày, khớp
tuyệt đối với `f1_flow.py`.

**Nghịch lý cần nêu rõ:** `sd(daily)` TỐT LÊN nhưng maxDD và underwater XẤU ĐI mạnh,
ở tổng exposure gần như không đổi. Nghĩa là drawdown của hệ KHÔNG do biên độ dao động
ngày gây ra, mà do **tốc độ hồi phục**. Đa dạng hoá làm mỗi ngày êm hơn nhưng làm
mean/ngày sụt 44%, nên hố sâu tương đương mất GẤP 2.7 LẦN thời gian để lấp
(93d → 254d). maxDD và underwater là hai thứ K làm hỏng, không phải cải thiện.

## 6. PHÁN QUYẾT — NULL, đóng hướng

Quy tắc đã chốt: *chọn K có `sd(daily)` thấp nhất TRONG SỐ các run thoả C1 + toàn bộ
ràng buộc cứng.*

- Thoả C1: cả 4 run.
- Thoả ràng buộc cứng: **chỉ `F1_parity` (K=8)** — tức chính baseline.
- Tập ứng viên sau khi lọc: **RỖNG** (không có biến thể K>8 nào sống sót).

⇒ **Giữ `SELECTOR_RANK_TOPK=8`. Không đổi gì. Đóng hướng F1.**

`K=32` có `sd` thấp nhất nhưng bị LOẠI ở ràng buộc cứng, nên điều khoản "mút của grid"
KHÔNG áp dụng — không có lý do mở pre-reg mới để đi xa hơn 32. Đi xa hơn chỉ làm
`mean` sụt tiếp và underwater dài thêm.

**Giả thuyết "hệ thiếu dòng cơ hội, không thiếu edge" bị BÁC BỎ.** Dòng cơ hội nới
được thật (2.86 → 9.78 vị thế), tổng exposure giữ được thật (C1 +4%), nhưng kết quả
xấu đi đơn điệu trên mọi tiêu chí trừ `sd`. Hệ không thiếu dòng — **hệ thiếu edge ở
các rank sâu.**

## 7. Cơ chế: vì sao mean sụt — bằng chứng RATE

Đây là phần có n lớn nhất, đáng tin nhất (970 → 2,779 lệnh):

| Tag | K | n lệnh | **TSloss%** | **meanP** | medP |
|---|---|---|---|---|---|
| `F1_parity` | 8 | 970 | **15.2%** | **3.48** | 5.50 |
| `F1_k16` | 16 | 1,659 | **18.3%** | **3.00** | 5.50 |
| `F1_k24` | 24 | 2,255 | **20.1%** | **2.77** | 5.50 |
| `F1_k32` | 32 | 2,779 | **21.7%** | **2.50** | 5.50 |

`medP` = **5.50 ở CẢ 4 run, không đổi**: lệnh THẮNG ở rank sâu tốt ngang lệnh thắng ở
rank nông. Cái đổi là **tỉ lệ CHẾT bằng time-stop: 15.2% → 21.7%** (+6.5pp, đơn điệu).

⇒ Lệnh thêm vào từ rank 9–32 không tệ hơn khi thắng, mà **thường xuyên không bao giờ
chạy hơn** — rơi đúng vào nhóm time-stop 168h đã mô tả ở `docs/experiment/E0_EXIT_CF.md`.

**Độ sâu rank CÓ mang thông tin**: thứ tự của S1 phân tách được `TSloss%` một cách
đơn điệu trên vài nghìn lệnh. Đây là metric RATE, n lớn — khác hẳn các so sánh equity
single-realization. (Lưu ý phạm vi: đây là ĐỘ SÂU của cùng một selector, KHÔNG phải
câu hỏi "selector variant" đã chốt VOID ở `docs/analysis/SELECTOR_LADDER_Q.md`. Không mở lại.)

## 8. Equity — KHÔNG PHẢI TIÊU CHÍ

Dán nhãn theo luật cứng số 3. Báo cáo để đầy đủ, KHÔNG dùng để phán quyết
(`sd(ΔCAGR)` = 2.57pp, `E[max nhiễu]` N=50 = +7.2pp, DEV đã ~125 run).

| Tag | equity cuối | tổng |
|---|---|---|
| `F1_parity` | 60,390 | +72.5% |
| `F1_k16` | 53,232 | +52.1% |
| `F1_k24` | 49,931 | +42.7% |
| `F1_k32` | 47,279 | +35.1% |

Hướng của equity trùng hướng của Sharpe và của `TSloss%`, nên nó không đổi kết luận
nào — nhưng kết luận ở mục 6 dựa trên `sd`/ràng buộc cứng/`TSloss%`, không dựa vào đây.

## 9. Rủi ro còn lại

- 4 run đều là **single realization trên DEV**. Ràng buộc cứng (maxDD/underwater) mà
  phán quyết dựa vào vẫn là đại lượng n_eff nhỏ — đây là lý do phán quyết là "đóng
  hướng", KHÔNG phải "đã chứng minh K=8 tối ưu". K=8 giữ nguyên vì là status quo,
  không phải vì thắng một phép kiểm định.
- Kết quả này làm **rộng thêm** vênh `K=8 (sim)` vs `K=5 (live)` ở `QUEUE.md` Q6 mục 4:
  đã có bằng chứng `TSloss%` xấu đi theo độ sâu rank, nên K live thấp hơn K sim là
  lệch có hướng, cần đóng.
- KHÔNG chạy VAL. KHÔNG push.
