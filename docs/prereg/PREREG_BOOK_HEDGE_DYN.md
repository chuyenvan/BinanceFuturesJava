# PREREG_BOOK_HEDGE_DYN — chọn công cụ hedge ĐỘNG theo thời điểm (owner yêu cầu 10-19)

Ngày 2026-10-19. **Commit TRƯỚC khi chạy.** Đây là lần thử **THỨ TƯ** trong họ BOOK_HEDGE
(1 BTC → NO-GO; 2 ETH → NO-GO; 3 ZIL chọn cứng → GO nhưng là *chọn sau khi thấy kết quả*) ⇒ **THĂM DÒ**,
không thăng hạng trên DEV; chỉ được xác nhận **1 lần** trên HO4 2026 với cấu hình đã chốt ở đây.

## Vấn đề với bản ZIL
ZIL được chọn vì **đứng đầu screen 2024** — tức chọn công cụ sau khi nhìn dữ liệu của chính giai đoạn đo.
Đó là **selection bias** (giống D2 của audit B4). Cơ chế động dưới đây loại bỏ điều đó: **mỗi tháng chỉ dùng
dữ liệu QUÁ KHỨ** để chọn công cụ, không dùng thông tin tương lai.

## Luật chọn động (chốt cứng, không điều chỉnh sau khi xem kết quả)
1. **Universe mỗi tháng**: coin có (a) ≥ 60 ngày dữ liệu trong **90 ngày trước** ngày chọn, (b) median
   quote_volume ngày ≥ **10 triệu USD** trong 90 ngày đó; loại `BTCUSDT`, `ETHUSDT`, stablecoin (`*USD*` pegged),
   `BTCDOMUSDT`; lấy **top 30 theo thanh khoản**.
2. **Điểm số**: **corr Pearson** của return ngày (log, close cuối ngày UTC) của coin với **return ngày của book**
   trên **90 ngày trước** ngày chọn. Return book = trung bình 8 seed của return equity MTM phút (chỉ dùng dữ liệu đã qua).
3. **Chọn**: **top k = 5** coin theo điểm số; **weight bằng nhau 1/5**.
4. **Rebalance**: **đầu mỗi tháng** (00:00 UTC ngày 1). Giữ nguyên trong tháng (không đổi giữa tháng).
5. **Hedge**: short `h × N_open × Σ w_i · r_i(t)`; `h ∈ {0,5; 1,0}`.
6. **Phí**: taker **0,05 % × h × |ΔN|** trên **tổng** notional hedge (chia đều cho 5 leg theo weight);
   **bỏ qua funding** (như BTC/ETH/ZIL). Không mô phỏng impact ở bước này (đã có addendum capacity riêng).
7. **Không fallback**: nếu tháng nào < 5 coin đủ điều kiện ⇒ dùng số coin sẵn có (weight 1/n), ghi lại.

## Luật GO (y nguyên BOOK_HEDGE, không đổi)
**GO ⟺** (DD nông hơn ≥ 5pp ở **≥ 7/8 seed**) **VÀ** (`ΔCalmar_mean − 3,499483·SE > 0`) **VÀ** (`ΣPnL` giảm **≤ 50 %**).
Winner = Calmar22 cao nhất trong các arm GO.

## Báo cáo bắt buộc (để phát hiện overfit)
- Bảng arm như BOOK_HEDGE (CAGR22/DD22/Calmar22/UW22/ΣPnL/DD LUNA/ΔCalmar CI99/GO).
- **Chuỗi lựa chọn**: mỗi tháng chọn 5 coin nào; tần suất xuất hiện của từng coin (top 10); số lần đổi thành viên/tháng.
- **So sánh**: base (không hedge) · DYN h0,5/h1,0 · ZIL cứng h0,5/h1,0 · BTC · ETH.
- **Kiểm chống nhìn trước**: chạy lại với cửa sổ 30 và 180 ngày (chỉ báo kèm, KHÔNG đổi luật GO) để xem kết quả có phụ thuộc cửa sổ không.
- **Turnover/participation** của basket (5 leg) so với ADV từng coin.

## Giới hạn đã biết
- 5 leg ⇒ phí và số lệnh tăng so với 1 leg; universe alt hẹp (≥10 M/ngày) nên basket có thể trùng nhau nhiều tháng.
- Kết quả **thăm dò**; nếu GO, chỉ chuyển HO4 2026 **một lần** với `h` cố định (winner), cửa sổ 90 ngày, k=5.
