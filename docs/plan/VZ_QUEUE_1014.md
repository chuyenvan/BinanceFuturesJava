# VZ_QUEUE_1014 — hàng đợi việc tuần tự cho OpenClaw (MASTER 2026-10-14)

Chạy SAU việc đang làm (chuyển YAML PREREG_VZ_B4 + commit), TUẦN TỰ Q1 → Q6, SONG SONG với nạp dữ liệu Phase 1 (Phase 1 được ưu tiên đĩa/kernel). Luật chung như `docs/plan/VZ_E1_TASKS.md` (chỉ 2024 cho khám phá; ledger; config biến thể commit TRƯỚC khi đo; không 242/shadow; Kaggle ≤ 2 kernel; logging; trailer). Code/kết quả trên branch `research/vz-e1` (worktree `~/claude_master/vz_e1_wt`). Mỗi Q xong: commit + 1 dòng báo vào `docs/research/VZ_QUEUE_STATUS.md` (Q, trạng thái, commit, số chính). Lỗi/điều kiện dừng ⇒ ghi trạng thái BLOCKED kèm lý do rồi CHUYỂN sang Q kế tiếp không phụ thuộc (Q2, Q3, Q4 độc lập nhau).

Phí thật (owner 10-14): tài khoản **VIP 0** ⇒ USDⓈ-M maker 0,02 %, taker 0,05 % mỗi chiều; trả bằng BNB giảm 10 % (0,018 % / 0,045 %).

## Q1 — kiểm và sửa giả định phí (ưu tiên cao nhất)
1. Đọc sim: `SimulatorMarketLevelTicker1MStopLoss` + `OrderTargetInfoTest.calTp` (repo module) — `SIM_RATE_FEE` (0,000982 trong ho4p1-c2) bị nhân 1 lần hay 2 lần trên notional? Trích file:dòng. Kết luận: 0,000982 là phí MỘT chiều hay KHỨ HỒI.
2. Nếu là khứ hồi ⇒ E1 đang trừ `2 × 0,000982` là trừ phí GẤP ĐÔI. Sửa `e1_core`: tham số `fee_roundtrip` (mặc định = cách sim tính, đúng theo bước 1). Tính lại MỌI bảng mức net của T3–T9 (không đổi định nghĩa/biên/biến thể). Kiểm: spread giữa nhóm phải trùng bản cũ (sai lệch chỉ do làm tròn, ≤ 1e-9) — nếu không trùng ⇒ dừng báo. Ledger: ghi "tính lại chi phí, 0 phép thử mới".
3. Bảng kịch bản phí (cho owner): khứ hồi taker/taker 0,10 %; taker/taker BNB 0,09 %; maker vào + taker ra 0,07 % / BNB 0,063 % — net trung bình của sự kiện crash 2024 ở 60′/240′/24h theo từng kịch bản (chỉ mô tả).
4. PREREG_VZ_B4: thêm mục "Addendum 1 (trước khi chạy xác nhận)": công thức phí sửa theo bước 1; luật GO dựa trên spread nên không đổi. Commit TRƯỚC khi chạy xác nhận.

## Q2 — lọc tuổi symbol trên chân của hệ (2024, ≤ 4 biến thể)
- Dữ liệu `e1_t9_legs_2024.parquet` (6 709 chân, có tuổi symbol). Nhóm tuổi tại thời điểm vào: 0–7 / 8–30 / 31–90 / > 90 ngày / không rõ.
- Biến thể: (1) net hold-to-exit theo nhóm tuổi; (2) net 240′ theo nhóm tuổi; (3) "loại chân tuổi ≤ 30 ngày": ΣPnL net, n, trung bình mỗi chân của phần bị loại vs phần giữ; (4) như (3) với ngưỡng ≤ 7 ngày.
- Báo kèm số chân và % ΣPnL đến từ coin ≤ 30 ngày (cần biết hệ có phụ thuộc listing mới không). Không gọi GO.

## Q3 — chi phí vào theo phút-trong-giờ (mô tả, 0 phép thử alpha)
- Nguồn: kết quả chi phí từng chân của EXEC (2c812222, DEV 2022–25: P0/VWAP vs close_M). Tìm file per-leg trong output EXEC (`~/claude_master/*/exec*`, docs/result/EXEC_RESULT.md §tệp). Nếu đã bị xoá ⇒ BLOCKED, KHÔNG tải lại aggTrades (Phase 2 chưa mở).
- Bảng: chi phí vào (bps) theo phút-trong-giờ của t_dec: nhóm {:00}, {:15,:30,:45}, {:01–:02 sau mốc}, còn lại; và theo bucket NC/C1/C2/C4. Trung vị, p90, CI bootstrap theo ngày.
- Câu hỏi: hệ vào ở giây 6 có bị đắt hơn quanh các mốc 15′ (burst algo, Kim & Hansen 2026 arXiv 2607.09426) không.

## Q4 — họ H-F: imbalance tại mốc 15′ → return 4–12 h (2024, ≤ 8 biến thể)
- Sự kiện: mỗi mốc :00/:15/:30/:45 × mỗi symbol active với quote_volume phút mốc ≥ 50 000 USDT. Imbalance phút mốc `imb = 2·taker_buy_quote/quote_volume − 1`.
- Outcome: log ret từ close phút mốc tới +4h, +12h; net chi phí NC + phí khứ hồi (theo Q1). Thước: IC Spearman cắt ngang mỗi mốc (trung bình + CI bootstrap theo ngày) và spread quintile trên − dưới.
- 8 biến thể (chốt config trước): {chỉ :00, mọi mốc 15′} × {4h, 12h} × {imb thô, imb − imb TB 15′ trước}.
- Bản gốc dùng 10 giây đầu từ dữ liệu trade; ở đây là xấp xỉ 1 phút ⇒ ghi rõ giới hạn. Không gọi GO.

## Q5 — báo cáo
- Thêm §6c vào `docs/result/VZ_EXPLORE_2024.md`: kết quả Q1 (kết luận phí + bảng kịch bản), Q2, Q3, Q4; tổng phép thử mới; tối đa 2 ứng viên mới kèm cơ chế/rủi ro (không GO). Cập nhật ledger.

## Q6 — xác nhận B4 (chỉ khi lake có đủ 2022, 2023, 2025 + lookback 30 ngày năm trước, và Q1.4 đã commit)
- Chạy đúng một lần: `e1_confirm.py --prereg docs/prereg/PREREG_VZ_B4.md --years 2022,2023,2025`. Báo theo luật GO + md5 output. Không chạy biến thể khác. Nếu lake chưa đủ: để trạng thái WAITING, kiểm lại mỗi khi một năm Phase 1 xong.
