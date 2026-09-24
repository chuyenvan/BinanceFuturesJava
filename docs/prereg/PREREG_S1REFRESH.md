# PREREG_S1REFRESH — refresh S1 ranker cutoff 2025-09-28 → 2025-12-31 (KHÔNG chạm holdout 2026)

- Mục tiêu: đưa S1 live từ model stale (cutoff 20250928) về cutoff 20251231 = đúng mép kết thúc DEV/sim (SIM_END_DATE=20251231). Đây là refresh VẬN HÀNH theo protocol WFO, KHÔNG phải thí nghiệm tìm alpha. Holdout 2026 giữ nguyên tuyệt đối (không train trên bất kỳ dòng nào có ts >= 2026-01-01).
- Cổng TÁI LẬP (reproduction gate) — chạy TRƯỚC: dùng chính pipeline retrain để tái tạo model cutoff 20251001 đã có manifest (/home/ubuntu/s1_model/s1a2x1_cut20251001.{json,onnx}). Điều kiện đạt: spearman rank giữa prediction tái tạo và prediction gốc trên tập OOS = 1.000000 (hoặc >=0.99999), max|delta| < 1e-6. NẾU KHÔNG ĐẠT → DỪNG, báo cáo, KHÔNG vá để cho qua.
- Train model mới cutoff 20251231 CHỈ SAU khi cổng tái lập đạt. Ra artifact {json,onnx} + manifest sha256 tại /home/ubuntu/s1_model/s1a2x1_cut20251231.*
- Kiểm tra tính toàn vẹn model mới: số record khớp kỳ vọng, không NaN/inf trong prediction, phân phối prediction (mean/std) không lệch bất thường so với model cũ.
- Validate top-K (READ-ONLY, MÔ TẢ, không phải go/no-go): trên cửa sổ chung 2025-10-01..2025-12-31, so top-8 của model mới vs model cũ mỗi tick: %overlap trung bình, spearman thứ hạng. Chỉ để hiểu model thay đổi bao nhiêu. KHÔNG dùng để tune.
- Tiêu chí ứng viên deploy shadow (quyết định cuối là của USER, không phải bạn): (a) cổng tái lập đạt; (b) toàn vẹn model mới đạt; (c) probe parity live-vs-onnx top-8 = 100% (kiểu S1RankerLive 6800/6800) NẾU probe khả thi trong phiên này. Đủ 3 → ghi "ứng viên deploy", DỪNG, chờ user.
- NGOÀI phạm vi: train trên data 2026; retrain net015/x26 (vướng trainer source); mọi thao tác trên 242; deploy live.
- Luật cứng: không tune tham số; cổng fail thì DỪNG + báo.
