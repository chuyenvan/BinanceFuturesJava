# PREREG_PARITY_V12_DRY — ADDENDUM 12: nhãn SẠCH-T (tạm) cho G-MICRO, chấm lại bắt buộc ở lượt M (2026-11-06)

Quyết định MASTER. **Khai:** viết SAU khi đã thấy nhãn 11-04, TRƯỚC nhãn của mọi ngày sau 11-04. Nhãn 11-04 (r4n) là
"KHÔNG ĐO ĐƯỢC (một phần) + XÁM", §5 = SẠCH. Các phép P1/P1m/S1-I/S1-m/GV-I/P2/P3/CTL đều ĐẠT, GATE log 1440/1440.
TSX = KHÔNG ĐO ĐƯỢC (vision=nan). Phần "+ XÁM" đến từ **K5 = 1440 phút**, nguồn S1V (top-24 khác tập ở mọi phút),
**không phải từ funding**.

## 1. SẠCH-T
Một ngày là **SẠCH-T** khi đủ TẤT CẢ:
1. Phép cơ học đều ĐẠT: P1, P1m, S1-I, S1-m, GV-I, P2, P3, CTL; GATE log n_pass đủ (k/k phút, k > 0).
2. §5 ngày sạch = SẠCH (mọi kiểm §5, gồm §5.5 collectData), pull242 COMPLETE.
3. Không có lớp phủ V12 nào hạ nhãn: không restart/deploy/swap, có exchangeInfo PIT, tập coin đang giữ khớp [GATE-PRE], R4–R6 PASS.
4. Phần chưa ĐẠT **chỉ** là:
   - (a) funding sơ bộ (chờ Vision monthly, câu "so bo cho phan funding" trong nhãn), và/hoặc
   - (b) TSX = KHÔNG ĐO ĐƯỢC do Vision nan.
   Không được có thêm XÁM nào khác, gồm **K5 > 0** (ADD2/ADD3 v11).

## 2. G-MICRO (sửa ADD11 §4 (i)/(ii))
- (i) đếm SẠCH **hoặc** SẠCH-T. (ii) "ngày SẠCH trọn vẹn trên r4q" cũng tính SẠCH-T. Smoke 24 h giữ nguyên.
- TRƯỢT ở bất kỳ phép cơ học nào: dừng đếm như ADD11 §3.

## 3. Chấm lại bắt buộc ở lượt M
- Mọi ngày SẠCH hoặc SẠCH-T mang cờ `needs_M_regrade = true`. Khi có Vision monthly (lượt M) thì chấm lại đầy đủ những ngày này
  (funding chính thức, TSX).
- Kết quả lượt M là điều kiện của **G-PILOT**, không phải G-MICRO. Có ngày nào TRƯỢT ở lượt M thì **chặn pilot**, MASTER chẩn đoán.
- `docs/result/parity_v12_gmicro.json` ghi danh sách `needs_M_regrade`.

## 4. Không đổi
- Tiêu chí từng phép đo, luật jar/PREMARKET (ADD11 §2), ngày swap XÁM, Nhóm K (ADD9).
