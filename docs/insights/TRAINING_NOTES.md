# Nguyên tắc TRAIN (rút từ TASK-026 gate) — áp cho MỌI train (026 gate, 039 funding)

## 1. ĐỘ PHỦ DỮ LIỆU — kiểm TRƯỚC khi kết luận model/feature
**Bài học cốt lõi:** một metric thấp có thể do dữ liệu/đoạn regime, KHÔNG phải feature kém. Phải kiểm coverage trước khi đổ lỗi feature.

- Trước khi đánh giá: in phân phối label + biến động (std) theo thời gian (quý/năm) và **map mỗi fold walk-forward vào regime** nó rơi vào.
- Walk-forward chia theo thời gian → mỗi val-fold là MỘT đoạn regime. Fold rơi vào **sideway** (đi ngang) sẽ có 1 lớp áp đảo → metric phân loại thấp dù feature ổn.
- **Bằng chứng 026:** fold2 = 2023-03→2024-04 (sideway, FLAT 74%, std 0.032) → macro-F1 **0.287** (thấp nhất). fold3 = 2024→2025 (động, std 0.045) → **0.35** (cao nhất). Càng động model càng tách tốt ⇒ điểm trung bình bị đoạn sideway kéo xuống.

## 2. NHÃN CỐ ĐỊNH KHÔNG CÔNG BẰNG GIỮA REGIME
- Ngưỡng cố định (vd ret_24h ±3%) lệch theo vol: 2023 std 0.032 → ±3% ≈ 1.4σ (UP/DOWN cực hiếm, FLAT 74%); 2021 std 0.06 → ±3% ≈ 0.5σ (cân hơn).
- **Dùng nhãn ADAPTIVE: ±k·σ** với σ = rolling std backward (no-leak, cửa sổ kết thúc trước t−horizon) → 3 lớp cân ở mọi regime, so feature mới công bằng.

## 3. ĐÁNH GIÁ GATE = BỘ LỌC, không phải phân loại đều
- macro-F1 toàn cục gây hiểu nhầm (bị sideway kéo). Bổ sung:
  - **per-regime** (đánh giá riêng đoạn động vs sideway).
  - **lift theo decile P** (khi model tự tin, return thực tế có tách khỏi base-rate không).
  - **precision@confidence** (P_up/P_down > ngưỡng → tỉ lệ đúng vs base).
- Gate chỉ cần đúng ở **đuôi tự tin**; dùng dạng ngưỡng xác suất, không argmax 3 lớp.

## 4. Áp cho 039 (funding selector) y hệt
Kiểm coverage regime của tập funding (đặc biệt crash 2022) + cân nhắc nhãn adaptive + đánh giá per-regime/lift, trước khi kết luận model/feature.

## 5. HORIZON nhãn phải khớp thời gian giữ lệnh (rút thêm từ 026)
- Horizon NGẮN dễ dự báo hơn (4h: macro-F1 0.353, std giữa fold 0.003) nhưng return spread nhỏ + KHÔNG khớp holding (DCA giữ nhiều ngày).
- Horizon DÀI (24h) khó hơn (0.318) nhưng spread lớn hơn.
- Dùng horizon ngắn như **chẩn đoán** (feature có lực không), nhưng chọn horizon **khớp thời gian giữ lệnh thực tế** cho production. 026 chốt **12h**.
