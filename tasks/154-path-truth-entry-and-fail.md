---
id: 154
status: NEEDS_HUMAN
depends_on: []
touches_live_process: false
writes_242_data: false
resource: oracle
checkpoint: true
max_retry: 2
report: docs/reports/154.md
require_review: true
---

# TASK-154 [PATH-TRUTH] — Đo PATH 1m thật: (A) precision SL-1% chính xác cho Entry + (B) hồi-phục-từ-lỗ cho Fail

## Bối cảnh (vì sao cần)
Task 153 (Kaggle, xấp xỉ) cho thấy: selector có edge to ở "chạm +3%" (A) nhưng edge gần như biến mất ở
"chạm +3% mà không bị SL+1% quét trước" (B, edge chỉ 1–5đ%). NHƯNG B của 153 là XẤP XỈ dùng max/min cả cửa
sổ (không biết −1% xảy ra TRƯỚC hay SAU +3%) → **thiên lệch BI QUAN** (đếm nhầm cả −1%-sau-khi-đã-+3%,
lúc đó SL đã khóa, thành fail). Phải đo bằng PATH 1m TUẦN TỰ thật để kết luận dứt điểm.

Cùng tool path 1m này đo luôn tầng Fail (ý tưởng Uni): từ điểm đang lỗ, xác suất hồi phục là bao nhiêu.

## Mục tiêu (1 câu)
Đọc ticker 1m thật, mô phỏng path tuần tự để đo chính xác: (A) tỉ lệ "chạm +3% mà SL+1% KHÔNG bị quét
trước" theo selector vs random; (B) thống kê hồi-phục-từ-điểm-lỗ làm nền cho chiến lược DCA/SL tầng Fail.

## Scope
**Trong scope:**
### Phần A — Entry precision path-chính-xác (quyết định hướng chọn-coin)
1. Với các điểm entry (dùng score selector predict_wf, top-5/kỳ) trên tập test WFO, đọc path 1m tới H giờ.
2. Mô phỏng ĐÚNG cơ chế: đi tuần tự từng nến 1m — chạm +1% thì arm SL cứng +1%; nếu sau đó rớt xuống
   dưới +1% TRƯỚC khi chạm +3% = **fail (SL quét)**; nếu chạm +3% trước = **success**. (Path thật, không
   phải max/min cửa sổ.)
3. So selector vs random baseline (5 coin ngẫu nhiên/kỳ, seed cố định). H ∈ {4h, 24h, 72h}.
4. So thẳng với xấp xỉ B của 153 để lượng hóa "xấp xỉ bi quan bao nhiêu".

### Phần B — Fail recovery statistics (nền cho tầng 3, dữ liệu lớn)
5. Lấy mẫu LỚN điểm "đang lỗ" — KHÔNG random mù toàn universe (153 cảnh báo lệch phân phối): lấy các
   điểm entry-fail THẬT (coin selector chọn nhưng KHÔNG chạm +3%) HOẶC random-có-điều-kiện (coin vừa
   pump rồi tụt). Từ mỗi điểm lỗ −Y%, đọc path 1m tiếp theo tới H giờ.
6. Đo, phân theo độ sâu lỗ {−5%, −10%, −15%, −20%, −30%} × H {24h, 72h, 168h}:
   - P(hồi về hòa vốn), P(hồi về +1%), P(hồi +3%).
   - Độ sâu lỗ TIẾP theo trước khi hồi (để biết DCA cần chịu tới đâu).
   - Kỳ vọng PnL cuối nếu: (i) giữ nguyên, (ii) DCA 1 lần ở −Y%, (iii) cắt lỗ ngay.
7. **Pre-register verdict Fail:** DCA đáng dùng nếu P(hồi hòa vốn trong 72h | lỗ −15%) ≥ 60% VÀ độ sâu lỗ
   tiếp theo (p90) ≤ 40%. Nếu P thấp / đuôi sâu → SL tốt hơn DCA ở mức đó.

**Ngoài scope:** KHÔNG train model. KHÔNG đổi code trading. Đây là tool ĐO read-only (như CarryEdgeProbe).
Code >80 dòng cho tool đo là chấp nhận (nó là analyzer, không phải logic trading).

## Pre-register (Phần A — ghi TRƯỚC)
- Label +3%/SL-1% "đáng train selector mới" nếu path-thật cho ≥1 horizon: edge (selector−random) ≥ 10đ%.
- Nếu path-thật vẫn < 10đ% mọi horizon → xác nhận 153: chọn-coin KHÔNG thêm giá trị cho cơ chế này →
  báo Desktop chuyển framework §3 (sleeve khác) / §6.

## HÀNG RÀO
- Đọc ticker 1m từ Aerospike (read-only) hoặc bin có sẵn — KHÔNG ghi 242. Tool riêng, KHÔNG đụng jar sim.
- setsid nohup. Path 1m nhiều dữ liệu → chú ý OOM (chunk, đừng load hết vào RAM). SLF4J.
- Cách ly thư mục `/home/ubuntu/team_path/`.

## Acceptance criteria
- [ ] Phần A: bảng H×{selector,random,edge} path-CHÍNH-XÁC + so với xấp xỉ 153 (chênh bao nhiêu).
- [ ] Phần A verdict: label +3%/SL-1% có đáng train không (path thật).
- [ ] Phần B: bảng recovery P(hồi) × độ-sâu-lỗ × H + kỳ vọng 3 hành động (giữ/DCA/cắt).
- [ ] Phần B verdict pre-register: DCA vs SL đáng ở mức lỗ nào.
- [ ] Ghi rõ nguồn ticker 1m + số mẫu mỗi ô.

---
## (Code điền) Kết quả
## (Code điền) Phát hiện ngoài scope
## (Code điền) Quyết định phát sinh
