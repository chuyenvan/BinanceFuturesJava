# PREREG_BOOK_HEDGE — short BTC perp theo phơi nhiễm long đang mở để giảm DD của K24+skipFull

Ngày 2026-10-19. Chỉ ĐO offline (overlay) trên run có sẵn — không sim mới, không đổi 242/shadow, không REST. Commit TRƯỚC khi chạy.

## 0. Bối cảnh
Owner muốn giảm rủi ro bằng thêm lệnh, không tăng size. SEED_BLEND (dd2b6c1f), N_DEEP, NSEL, breadth T170 đều cho thấy:
thêm lệnh LONG cùng tín hiệu không giảm DD vì DD là một nhân tố sập chung (tương quan ngày giữa mô hình 0,975).
Lệnh duy nhất có thể giảm nhân tố đó là lệnh có phơi nhiễm NGƯỢC: short BTC perp chạy song song với book long.
Tiền lệ: 09-20 overlay hedge BTC trên T170 (hệ cũ) — đo ICC/power, ra NULL về power; CHƯA đo DD/Calmar, CHƯA đo trên K24.
EDGE_ATTR: β alt EW 0,85, ~1/3 PnL là beta hồi phục ⇒ hedge sẽ cắt lợi nhuận; câu hỏi là có cắt DD nhiều hơn không.

## 1. Dữ liệu (cố định)
- 8 run OFF `gqsf-*` (printDone). MTM nền: `gvz_mtm.py` (Vision, missing = 0).
- Return phút BTC: `~/claude_master/edge_attr/index.npz` (bt_ts, bt_r = log-return close 1m BTCUSDT, Vision).

## 2. Định nghĩa
- N(m) = Σ quantity × entry của các chân long đang mở tại phút m (mở từ nến quyết định m0 tới m1, như MTM).
- Hedge arm H_h: short BTC notional h × N, cân lại mỗi khi N đổi (mỗi lần vào/ra chân). PnL phút m:
  −h · N(m−1) · (exp(r_btc(m)) − 1). Phí taker 0,05 % × h × |ΔN| mỗi lần cân. Funding BỎ QUA (thường có lợi cho short
  trong năm tăng — giả định bảo thủ về PnL, ghi rõ).
- Equity hedge(m) = equity MTM nền(m) + ΣPnL hedge tới m. h ∈ {0,5; 1,0} (cố định, không quét thêm).
- Chỉ số trên đường equity phút (cùng cách cho nền và hedge): maxDD 2022→hết (DD22) và toàn kỳ; CAGR22 từ equity cuối ngày
  2022-01-01 → ngày cuối; Calmar22 = CAGR22/|DD22|; UW22 (ngày dài nhất dưới đỉnh); ΣPnL; DD theo năm.

## 3. Kiểm hợp lệ (PASS trước khi đọc)
- V1: nền (h = 0) tái lập dd_mtm22 của ISO_RISK OFF sai lệch ≤ 0,01pp 8/8 seed.
- V2: không có phút BTC thiếu trong lúc N > 0 quá 0,1 % số phút có vị thế (thiếu ⇒ return 0, báo số).

## 4. Luật (chốt trước)
- GO cho arm H_h nếu: DD22 nông hơn nền ≥ 5,0pp ở ≥ 7/8 seed VÀ ΔCalmar22 trung bình > 0 với CI99 (t df7, 3,4995) > 0
  VÀ ΣPnL giảm ≤ 50 %.
- Winner = arm GO có Calmar22 cao nhất. Không có GO ⇒ đóng hướng hedge BTC cho K24 (ở mức overlay).
- Mô tả kèm: tương quan ngày book vs BTC, DD đợt LUNA (2022-05) và FTX (2022-11), PnL hedge theo năm.

## 5. Giới hạn
- CI theo seed KHÔNG phản ánh bất định đường giá (một lịch sử); vài đợt sập quyết định DD.
- Overlay bỏ qua tương tác với sizing (equity lớn/nhỏ hơn đổi size các lệnh sau) — bậc 1.
- GO ⇒ cần pre-reg port live (lệnh short BTC song song, margin riêng, vận hành) + HO4 2026 (cần kline 2026) trước mọi quyết định.
