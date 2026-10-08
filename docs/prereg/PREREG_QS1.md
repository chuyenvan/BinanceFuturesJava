# PREREG QS1 — quiet sleeve dạng GIỎ (đánh giá OFFLINE)

Ngày: 2026-10-08. Nền: QS0 (d6cccf80; lưới 13990401), script dự kiến `research/analysis/qsleeve_q1.py`.
Commit này được tạo TRƯỚC khi tính bất kỳ số nào của QS1. Nội dung "Thiết kế" + "Luật" dưới đây chép NGUYÊN VĂN từ MASTER; không đổi sau khi thấy số.
Không sim Java, không Kaggle, không sửa Java, không chạm 242/shadow, không mở ~/kaggle_sim/out/nsel-*.

### Thiết kế (1 cấu hình duy nhất, chọn trước = ô giữa lưới QS0, không phải ô tốt nhất)
- Độc lập với sổ hệ chính: "phút yên" t ⇔ gate core offline (K24, pct 0,999950829, 90 ngày, như gate_offline) KHÔNG có pass nào trong [t−24h, t). Không dùng vị thế của hệ chính.
- Tín hiệu: R(t) = max r trên top-24 tại t. Kích hoạt khi R(t) ≥ Q(t) = phân vị 0,9995 của R trên CÁC PHÚT YÊN trong 90 ngày trước t (causal; cần ≥30 ngày phút yên tích luỹ, trước đó không kích hoạt).
- Giỏ: 5 coin r cao nhất tại t trong top-24, loại coin có volume quote nến quyết định < 100 000 USDT (lấy coin kế tiếp); mỗi chân notional bằng nhau; vào ở close nến quyết định.
- Khử trùng: không kích hoạt giỏ mới trong 6h sau giỏ trước; 1 coin không vào lại trong 24h (coin bị loại ⇒ lấy coin kế tiếp).
- Thoát: proxy QS0 (luật thoát core, KHÔNG DCA), từng chân độc lập. Phí theo cấu hình sim. Stress: chân vào nến quyết định close/open−1 ≤ −1% chịu +1,675%.
- Vốn: sleeve = 10% tổng vốn; mỗi giỏ = 20% vốn sleeve (2% tổng); tối đa 5 giỏ mở cùng lúc (vượt ⇒ bỏ, đếm).
- Danh mục ghép: return ngày = 0,9 × return ngày MTM của nền (gqsf-* 8 seed, phí gốc) + 0,1 × return ngày sleeve (PnL ngày MTM của sleeve / vốn sleeve, không lãi kép). So với nền 1,0×. Bản stress: nền dùng stress post-hoc như gkf_rescore (ghi rõ), sleeve dùng stress chân.
- Đối chứng bắt buộc: 1000 lần bốc ngẫu nhiên các phút yên (cùng số giỏ mỗi tháng, cùng luật khử trùng/giỏ/thoát) ⇒ phân phối ROI giỏ đối chứng; p một phía = tỉ lệ đối chứng ≥ sleeve.
- Seed: tín hiệu dùng pred.bin theo 8 seed (42/7/13/21/99/123/777/2024, như gqsf); báo theo seed và gộp.
- Cửa sổ DEV 2022-01-01 → 2025-12-31 +07.

### Luật GO DEV (cần TẤT CẢ)
- L1: ROI giỏ stress trung bình gộp 8 seed > 0 VÀ cận dưới bootstrap cụm theo ngày 95% > 0; ≥ 6/8 seed có trung bình > 0.
- L2: vượt đối chứng phút yên ngẫu nhiên: p một phía < 0,05 (gộp seed).
- L3: ≥ 3/4 năm có ROI giỏ stress trung bình > 0.
- L4: Calmar ngày danh mục ghép (2022–25, MTM ngày, bản stress) trung bình 8 seed ≥ Calmar nền 1,0× VÀ tương quan return ngày sleeve vs nền ≤ 0,5.
- Thiếu 1 ⇒ NO-GO: không mở holdout, dừng.
### Holdout (CHỈ khi DEV GO; cùng cấu hình, không sửa gì)
- Cửa sổ 2026-01-01 → ngày dữ liệu cuối có sẵn (≤ 2026-09-30). Luật: ROI giỏ stress trung bình > 0 VÀ đối chứng p < 0,10. Không tính danh mục ghép trên holdout (không mở kết quả hệ chính 2026). Ghi rõ đây là lần dùng holdout cho câu hỏi sleeve.
- Kỳ vọng khai trước (MASTER): DEV ~80–130 giỏ/năm/seed; P(DEV GO) ~20%; P(holdout xác nhận | DEV GO) ~50%.

### Tự kiểm khai trước (BƯỚC 1)
- Proxy tái lập số QS0 ở 1 ô lưới (K24, 0,9995, không giỏ) trong ±0,05pp.
- "Phút yên" định nghĩa mới trùng ≥ 90% với định nghĩa QS0 (tuổi leg0 ≥24h) — báo số.
- Không lookahead: Q(t) chỉ dùng dữ liệu < t; kiểm bằng assert.
