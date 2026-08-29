# KHUNG GIẢI PHÁP — Cây chiến lược, test, tiêu chí, ĐIỂM DỪNG (2026-07-11)

> Mục đích: thay whack-a-mole bằng một cây HỮU HẠN các kiến trúc chiến lược. Mỗi nhánh có giả thuyết,
> một test RẺ, tiêu chí pass pre-register, chi phí. Đi từ rẻ+EV-cao → đắt. **Đi hết cây mà không nhánh
> nào pass → kết luận thẳng: kiến trúc/năng lực không đủ cho 20%/năm, DỪNG.** Quyết định thuộc Uni.

## 0. Vị trí hiện tại (trung thực)

- **CHƯA đạt** 20%/năm. Cấu hình tốt nhất ~5%/năm. Phải thừa nhận.
- **Đã có (không phải số 0):** sửa rò rỉ/đo-lường (mọi kết luận cũ dựa trên số leaky đã bị bác);
  xác định ràng buộc = TẦN SUẤT; loại 4 nhánh chết (exit-rule, sizing, carry, triple-barrier).
- **Chẩn đoán gốc:** return = tần_suất × edge/kèo × vốn/kèo − phí. Chỉ **tần suất** còn là ràng buộc.

## 1. Chẩn đoán quyết định (test RẺ nhất, làm TRƯỚC mọi thứ)

**Câu hỏi sinh-tử:** hệ nằm im 60% thời gian vì (A) edge thật sự HIẾM (thị trường không cho cơ hội) hay
(B) bộ lọc gate/selector QUÁ CHẶT (cơ hội có nhưng ta tự bỏ)?
- **Test:** nới dần ngưỡng gate + label lỏng (0.01|72h — ĐANG CHẠY) → đo: thêm kèo thì thêm LÃI hay thêm LỖ?
- **Pass (B, sửa được):** nới phễu → nhiều quý có trade hơn VÀ vẫn dương → nhánh 2/3 đáng đầu tư.
- **Fail (A, gần trần):** nới phễu → thêm kèo toàn lỗ → edge thật sự hiếm → nghiêng thẳng về §6 (dừng/chấp nhận).

Đây là bản lề: kết quả quyết định ta leo tiếp hay dừng.

## 2. NHÁNH — Khai thác sleeve ĐÃ CHẠY (mean-reversion / DCA) [EV cao nhất, ÍT khai thác nhất]

- **Bằng chứng bị bỏ quên:** trong MỌI test, `DCA_LEVEL1` (mua capitulation toàn thị trường, chốt hồi)
  là thành phần **dương bền nhất** (+5295, dương mọi năm). Ta đã dành 2 ngày sửa sleeve YẾU (pump selector)
  mà **lơ sleeve KHỎE** ngay trước mắt.
- **Giả thuyết:** biến mean-reversion thành sleeve CHÍNH — thị trường sập → mua, hồi → bán, tần suất cao
  hơn pump hiếm. Crypto mean-revert sau panic là quy luật bền.
- **Test rẻ:** đo `DCA_LEVEL1` đứng riêng (tắt PST) + nới trigger capitulation (độ sâu sập, funding âm
  cực đoan, cascade thanh lý) → tần suất + PnL + bậc thang. 1-2 sim Java, rẻ.
- **Pass:** DCA-primary cho nhiều quý dương hơn + CAGR cao hơn pump-primary với maxDD chịu được.

## 3. NHÁNH — Sleeve thứ 2 phi tương quan (cho quý phẳng)

- **Giả thuyết:** danh mục 2 sleeve ít tương quan mới cho "đều mọi quý" (không sleeve đơn nào làm được).
- **Ứng viên** (carry ĐÃ LOẠI — price nuốt):
  - 3a. **Trend-following trên BTC/ETH majors** — chế độ tradeable nhiều hơn alt-pump, thanh khoản sâu.
  - 3b. **Short-side momentum trong downtrend** — cần short (đổi kiến trúc), ăn đúng quý pump-sleeve chết.
- **Test rẻ:** backtest-lite sleeve majors-trend trên data giá có sẵn → %quý dương, tương quan với pump sleeve.
- **Pass:** sleeve mới dương ở ≥50% quý mà pump sleeve nằm im, tương quan < 0.3.

## 4. NHÁNH — Mở phễu cùng edge cũ (widen funnel)

- **Đang chạy:** `0.01|72h|pump` (label lỏng + horizon dài + feature pump). Đây CHÍNH là test §1.
- **Test:** Java confirm candidate → bậc thang. Pass = nhiều quý trade hơn + vẫn dương.
- **Biến thể rẻ nếu pass:** nới thêm gate threshold, giảm lọc thanh khoản, mở rộng universe.

## 5. NHÁNH — Regime-switch (chọn sleeve theo chế độ)

- **Giả thuyết:** 1 bộ phân loại regime (vol BTC, breadth, funding tổng, ΔOI) → chạy sleeve phù hợp:
  momentum lúc bull, mean-reversion lúc chop, cash/short lúc bear.
- **Điều kiện:** chỉ đáng làm khi §2 + §3 cho ≥2 sleeve dương ở regime khác nhau. Nếu chỉ có 1 sleeve tốt
  thì regime-switch vô nghĩa.
- **Test:** phân loại regime thô + gán sleeve tốt nhất mỗi regime, đo bậc thang tổng.

## 6. ĐIỂM DỪNG (pre-register)

Đi theo thứ tự §1 → §2 → §3 → §4 → §5. **Nếu:**
- §1 fail (nới phễu chỉ thêm lỗ) VÀ §2 fail (DCA-primary không hơn) VÀ §3 fail (không sleeve 2 phi tương quan)
  → **kết luận: universe long-only-perp này cho trần ~5%/năm, KHÔNG đạt 20%. Dừng, hoặc Uni chấp nhận 5%.**
- Không tự lừa bằng cách overfit thêm — mỗi nhánh đo trên WFO/bậc thang leak-free, pre-register trước.

## 7. Thứ tự thực thi (rẻ→đắt, song song được)

| Ưu tiên | Nhánh | Test | Chi phí | Trạng thái |
|---|---|---|---|---|
| 1 | §1/§4 funnel | 0.01\|72h\|pump → Java | 1 kernel + 1 sim | ĐANG CHẠY |
| 2 | §2 DCA-primary | DCA riêng + nới trigger | 2 sim Java | chờ duyệt |
| 3 | §3a majors-trend | backtest-lite | 1 kernel | chờ duyệt |
| 4 | §3b short-side | cần đổi kiến trúc | lớn | chờ §1-3 |
| 5 | §5 regime-switch | chỉ khi ≥2 sleeve tốt | trung bình | điều kiện |

**Nếu bảng này đi hết mà không pass → §6 dừng.** Đây là cam kết trí tuệ: không kéo dài vô hạn.
