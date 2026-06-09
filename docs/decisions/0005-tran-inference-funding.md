# ADR-0005: Không tinh chỉnh inference funding trên một node — scale ngang hoặc đổi engine

- **Ngày:** 2026-06-09
- **Trạng thái:** đã chấp nhận
- **Bối cảnh phát sinh:** reconcile tài liệu + đo bằng `FundingInferenceBenchmark`

## Vấn đề
Inference của funding classifier đang bị xem là chỗ cần "tối ưu config" để tăng tốc walk-forward optimization. Cần chốt: tinh chỉnh ONNX/threads trên một node, hay đi hướng khác?

## Các lựa chọn đã cân nhắc (đều đã đo bằng FundingInferenceBenchmark)
1. **Tinh chỉnh trên một node 4 core** — batching, intraOp > 4, optimization = ALL, chạy song song nhiều luồng. Kết quả: tất cả ≤ 1.1x. Trần ~2.7k rows/s.
2. **Scale ngang nhiều worker** — queue theo tháng đã hỗ trợ sẵn.
3. **Đổi engine** — GPU FIL / Treelite.

## Quyết định
Ngừng tinh chỉnh ONNX/threads cho inference funding trên một node. Muốn nhanh ~10x: scale ngang nhiều worker, hoặc đổi engine (GPU FIL / Treelite).

## LÝ DO (vì sao không lặp lại vòng tinh chỉnh này)
Model là tree-ensemble 262MB. Đo thực tế trên 4 core Kaggle cho trần ~2.7k rows/s, và mọi tinh chỉnh trên-node (batch / intraOp>4 / opt=ALL / chạy song song) đều ≤ 1.1x. Nút thắt là bản chất tree-ensemble lớn trên CPU ít core, KHÔNG phải cấu hình runtime. Tiếp tục chỉnh threads/ONNX là yak-shaving: lợi ≤1.1x, không xứng công. Ghi lại để session sau không đốt thời gian lặp lại vòng tinh chỉnh đã chứng minh vô ích.

## Hệ quả
- Nếu inference funding là chỗ gate tốc độ WFO → giải bằng scale ngang / đổi engine, không bằng tuning node.
- CLAUDE.md nên có một dòng ràng buộc cứng trỏ về ADR này.
