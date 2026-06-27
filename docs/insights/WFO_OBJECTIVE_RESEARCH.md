# Hàm mục tiêu cho WFO — cách quant/pro làm & cái gì áp dụng được cho bot này

> Mục đích: trả lời câu "giới quant chuyên nghiệp làm hàm mục tiêu (fitness/objective) cho
> walk-forward thế nào, mình áp dụng được gì". Viết để BÀN, không phải để chốt. Mọi đề xuất phải
> validate bằng số (A/B/C qua FitnessBaselineTool) trước khi tin.
>
> Bối cảnh bot (quyết định cái gì dùng được): **long-only, leverage 1, martingale/DCA, KHÔNG hard
> stop-loss, thoát bằng trailing chỉ khi có lãi.** Cửa sổ WFO = 3 tháng. Hệ quả: win-rate cao giả
> tạo, rủi ro nằm ở ĐUÔI (cú sập hiếm + nhồi vô hạn), không ở tần suất thắng.

---

## 1. NGUYÊN TẮC CHUNG GIỚI QUANT DÙNG (và cái nào hợp bot này)

### 1.1. KHÔNG tối ưu lợi nhuận thô (net profit) — ai cũng đồng ý
Tối ưu net profit → chọn ra chiến lược nhồi to, may rủi, cong nhất ở đuôi. Mọi sách quant
(Pardo "Design Testing and Optimization of Trading Systems", Tomasini, Robert Carver) đều bảo:
**tối ưu một số ĐÃ ĐIỀU CHỈNH RỦI RO.** → bot này ĐÚNG là phải tránh net profit (đã làm: V4 dùng Calmar).

### 1.2. Các "objective function" chuẩn họ hay dùng (xếp theo độ phổ biến)
| Tên | Công thức gọn | Đo cái gì | Hợp bot DCA này? |
|---|---|---|---|
| **Sharpe** | mean(return) / std(return) | lãi/độ-dao-động (phạt cả dao động lên) | ⚠️ kém hợp — phạt cả lãi đột biến lên; DCA hay lãi giật cục |
| **Sortino** | mean(return) / std(chỉ-return-âm) | lãi/dao-động-XẤU (chỉ phạt giảm) | 🟢 hợp hơn Sharpe — bot long-only chỉ sợ chiều giảm |
| **Calmar / MAR** | CAGR / maxDrawdown | lãi/sụt-sâu-nhất | 🟢 RẤT hợp — đuôi là rủi ro chính, đang dùng |
| **Profit Factor** | tổng-lãi / tổng-lỗ | chất lượng từng lệnh | 🟡 phụ trợ tốt, KHÔNG nên là mục tiêu chính (martingale làm PF đẹp giả) |
| **CPC / SQN / K-ratio** | biến thể kết hợp | độ "mượt" đường vốn | 🟡 nâng cao, để sau |

→ **Đồng thuận giới quant cho chiến lược không-stop, đuôi-nặng như bot này: Calmar (hoặc MAR) là
mục tiêu chính, Sortino là phụ trợ/kiểm chứng.** Đúng hướng V4 đang đi. KHÔNG cần phát minh lại.

### 1.3. CỐT LÕI họ làm mà mình CHƯA: phạt sự KHÔNG ỔN ĐỊNH giữa các cửa sổ
Đây là phần quan trọng nhất cho câu hỏi của bạn. Pro không chỉ nhìn 1 con số tổng. Họ đo **độ ổn
định của chính metric đó across time**:
- **Equity curve linearity / R² của đường vốn**: fit đường thẳng vào log-equity, R² càng gần 1 =
  đường vốn càng đều (không gập ghềnh). Rất phổ biến (Carver, nhiều CTA dùng).
- **Tỷ lệ cửa sổ con dương** (rolling window % positive): vd "≥X% số tháng/quý phải dương".
- **WFE (Walk-Forward Efficiency) = PnL_OOS / PnL_IS**: đo overfit. <0.3 = overfit nặng, ≥0.5 tốt.
  Đây là metric ĐẶC TRƯNG của WFO mà ROADMAP đã ghi.

→ Đây chính là chỗ V4 còn yếu (Calmar toàn-kỳ, constraint %năm-dương bị TẮT ở cửa sổ 3 tháng).

---

## 2. CÁI GÌ ÁP DỤNG ĐƯỢC NGAY (đề xuất cụ thể, vừa đủ)

Không đập đi xây lại. Vá V4 theo đúng 3 ý pro hay dùng, hợp cửa sổ 3 tháng:

### 2.1. Đổi đơn vị ổn định NĂM → THÁNG (sửa lỗ hổng constraint bị tắt)
- V4 hiện: constraint "%năm-dương ≥80%" chỉ áp khi ≥2 năm → cửa sổ 3 tháng KHÔNG kích hoạt.
- Sửa: trong cửa sổ ngắn, dùng **% THÁNG dương** (3 tháng → 3 điểm; ví dụ ≥2/3 tháng dương).
  Đây là "rolling window % positive" của giới quant, hạ về đơn vị tháng.

### 2.2. Đưa độ-mượt-đường-vốn vào MỤC TIÊU (không chỉ Calmar thô)
Hai lựa chọn, chọn 1:
- **(A) Calmar × Sortino-chuẩn-hóa** (nhân hệ số): giữ Calmar gốc, nhân thưởng nếu lãi đều theo
  ngày. Sortino đã tính sẵn trong V4 (chỉ chưa dùng). Rẻ nhất.
- **(B) Calmar × R²(equity)**: thưởng đường vốn thẳng. Cần tính R² log-equity theo ngày — thêm code
  vừa phải. "Chuẩn sách" hơn nhưng tốn hơn.
→ Nghiêng (A) trước (tái dùng Sortino có sẵn), nâng lên (B) nếu (A) chưa đủ phân biệt.

### 2.3. Giữ nguyên cái đang đúng
- Constraint maxDD ≤65% (đuôi) — giữ.
- Constraint %lệnh-giữ>7d ≤2% (giam vốn) — giữ.
- Tách constraint khỏi mục tiêu (chống HPO luồn lách) — giữ, đây là điểm V4 làm rất đúng.

---

## 3. RỦI RO ĐẶC THÙ BOT NÀY MÀ METRIC CHUẨN KHÔNG BẮT ĐƯỢC ⚠️

Đây là phần quan trọng phải nhớ — quant chuẩn giả định có stop-loss, bot này thì KHÔNG:

1. **maxDD trong backtest BỊ HIỂU NHẸ** (ROADMAP Bước 3 hoãn): chưa có margin-call thật, tài khoản
   thật có thể đã cháy ở mức DD đó. → Calmar nhìn đẹp hơn thực tế. Mọi ngưỡng phải để biên an toàn.
2. **DCA làm Profit Factor + win-rate đẹp giả**: thắng nghìn lệnh nhỏ, thua vài cú ôm chết. → tuyệt
   đối KHÔNG dùng PF/win-rate làm mục tiêu chính.
3. **Cửa sổ 3 tháng quá ngắn để thấy đuôi**: cú sập lớn hiếm (vài lần/5 năm). Một cửa sổ 3 tháng
   "đẹp" KHÔNG có nghĩa an toàn — nó chỉ chưa gặp sập. → đây là LÝ DO bản thân WFO (nhiều cửa sổ +
   WFE + %cửa-sổ-dương) quan trọng hơn con số 1 cửa sổ. Hàm mục tiêu 1 cửa sổ KHÔNG gánh được việc này.

→ Hệ quả tư duy: **hàm mục tiêu 1 cửa sổ chỉ cần "đủ tốt" để xếp hạng tham số TRONG cửa sổ đó. Việc
chống overfit/đuôi là nhiệm vụ của TẦNG WFO (nhiều cửa sổ, WFE, % cửa sổ OOS dương), không phải của
hàm mục tiêu.** Đừng nhồi mọi thứ vào 1 công thức.

---

## 4. ĐỀ XUẤT CHỐT (để bàn)

**Tầng hàm mục tiêu (mỗi cửa sổ 3 tháng):** V4 + 2 vá nhỏ:
1. %tháng-dương thay %năm-dương (constraint, ≥2/3 tháng).
2. Mục tiêu = Calmar × (1 + w·Sortino_norm), w nhỏ (vd 0.2–0.3) — thưởng đều đặn nhẹ, Calmar vẫn gốc.

**Tầng WFO (nhiều cửa sổ) — nơi gánh chống-overfit:** tiêu chí PASS chốt TRƯỚC khi nhìn:
- WFE = PnL_OOS / PnL_IS ≥ 0.5 (tốt), < 0.3 = overfit → loại.
- % cửa sổ OOS dương ≥ 70%.
- maxDD OOS xấu nhất trong ngưỡng.
- độ ổn định tham số qua các cửa sổ (gene không nhảy loạn).

**Validate hàm mục tiêu mới TRƯỚC khi dùng:** chạy lại FitnessBaselineTool (A=AI / B=no-filter /
C=placebo) — hàm mới phải vẫn xếp A > B và A > C. Nếu đảo → hàm hỏng, sửa. KHÔNG tin mù.

---

## 5. NGUỒN (thực hành quant phổ biến, để bạn tra thêm)
- Robert Pardo — *The Evaluation and Optimization of Trading Strategies* (kinh điển về WFO, WFE).
- Robert Carver — *Systematic Trading* (đường vốn mượt, không over-optimize, R² equity).
- Ernie Chan — *Quantitative Trading* / *Algorithmic Trading* (Sharpe/Sortino, tránh data-mining bias).
- Tomasini & Jaekle — *Trading Systems* (walk-forward, robustness).
- Cộng đồng retail: r/algotrading, QuantConnect forum — đồng thuận "tối ưu Sharpe/Sortino/Calmar,
  validate out-of-sample, nghi ngờ mọi thứ đẹp in-sample".

> ⚠️ Đây là tổng hợp NGUYÊN TẮC từ thực hành phổ biến, KHÔNG phải trích dẫn nguyên văn. Con số ngưỡng
> (w, %tháng, WFE) là điểm KHỞI ĐẦU hợp lý — phải tinh chỉnh bằng số thật của bot, không thần thánh hóa.
