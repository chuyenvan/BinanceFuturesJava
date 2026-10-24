# PREREG_PARITY_V11_WINDOW — ADDENDUM 2 (MASTER, 2026-10-24)

Áp cho mọi lượt D chấm SAU commit này (10-23 phần offline khi Vision có, 10-24 trở đi). Ngưỡng P1/P2/P3/TSX/S1-I/GV-I/CTL KHÔNG đổi.

## Lý do (ghi trung thực)
- ADDENDUM 1 (fea9fb97) do MASTER thiết kế quá hẹp: K1′ đòi log nêu TÊN symbol bị ghi đè — log 242 chỉ in bộ đếm `reread_overwritten` ⇒ K1′ không thể xảy ra; K6 chỉ nhận hoán đổi hạng kề nhau ⇒ bỏ sót 2 cơ chế float32/float64 đã quan sát (tie-split, score-only). Hệ quả: 10-22 XÁM (K5 = 416), D1 áp lại K′ có K5 = 375.
- Điều tra (D2, 997444d5) đã xác định nguyên nhân 416 phút: 9 phút mức thị trường nằm trong cửa sổ `[LIVE-KLINE]` có `reread_overwritten` > 0; 407 phút S1-V là tie-split / score-only với top-24 trùng tập + trùng thứ tự 1440/1440. K3′ drop-one đã chạy thật: 0 phút do universe.
- ADDENDUM này được viết SAU khi thấy số 10-22 ⇒ verdict 10-22 giữ nguyên là XÁM trong sổ; nhãn theo ADDENDUM 2 cho 10-21/10-22 chỉ ghi kèm, đánh dấu "relabel hậu kiểm".

## Thay đổi
1. **K1″** (thay K1′): phút lệch mức thị trường hoặc feature nến được tính K1″ nếu (a) nằm trong khoảng [W_start − 20′, W_end + 10′] của một cửa sổ log `[LIVE-KLINE]` có `reread_overwritten` > 0, VÀ (b) phép thay nến (dùng nến Vision cho các symbol có nến khác nhau giữa live-buffer suy ra và Vision trong khoảng đó) tái lập được giá trị live trong dung sai P1. Thiếu (b) ⇒ K5.
2. **K6′** (thay K6, chỉ mô tả, không tính K5): lệch S1-V khi top-K (24) trùng TẬP và trùng THỨ TỰ, và thuộc một trong: hoán đổi kề nhau; tie-split (một phía hoà hạng, phía kia tách) với |Δscore| ≤ max(1e-6·|score|, 1e-7); score-only (feature khớp dung sai, score ONNX lệch ≤ max(1e-6·|score|, 1e-7)). Top-24 khác tập hoặc thứ tự ⇒ K5.
3. **Việc code (đưa vào P0 C14, v1.2):** log `[LIVE-KLINE]` in danh sách symbol bị reread/overwrite (≤ 20 tên + tổng) để K1 kiểm được trực tiếp. Không đụng v1.1 đang chạy.
4. Kiểm lại S1-I của D1 với tập LEGACY đúng (đọc `[LEGACY] managed 44` từ log, như D2) — báo kèm lượt chấm kế tiếp.
5. Giữ báo cáo tích luỹ r/q ≥ 0,9 / ≥ 0,8.
