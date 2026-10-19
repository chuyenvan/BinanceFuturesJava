# PREREG_BOOK_HEDGE_AUDIT — kiểm lại toàn bộ họ BOOK_HEDGE (BTC/ETH/ZIL/DYN/BIGCOIN) bằng harness đã sửa

Ngày 2026-10-19 tối (MASTER). Commit TRƯỚC khi chạy lại. Chỉ đo offline; KHÔNG thêm công cụ mới — chỉ chấm lại các arm đã có.

## 0. Lỗi phát hiện khi review (MASTER tự nhận phần của mình)
1. **Harness sai so với chính pre-reg** (lỗi gốc ở `book_hedge.py` của MASTER, các bản sau kế thừa): công thức
   `hp(m) = −h·N(m−1)·(e^{r(m)}−1)` = giữ **notional cố định, cân lại MỖI PHÚT** miễn phí; pre-reg ghi "cân lại mỗi khi N đổi".
   Short notional-cố-định là chiến lược bám xu hướng (thêm short khi giá giảm, mua lại khi giá tăng): phóng đại lãi ở đợt sập
   và thu nhỏ lỗ ở đợt bơm, và không trả phí cho phần cân lại ngầm. Với coin sụp −99 % thì sai số khổng lồ.
2. **DYN chọn `LUNAUSDT` vào giỏ tháng 2022-05** (đúng luật point-in-time, nhưng nhân với lỗi 1): short LUNA cân lại mỗi phút
   ⇒ lãi gấp nhiều lần notional. Hedge PnL DYN năm 2022 +15,99k so với ZIL +1,98k, BTC +0,44k ⇒ nghi chủ yếu từ LUNA.
   Không mô phỏng việc Binance huỷ niêm yết/settle LUNA perp (13/05/2022) hay ADL.
3. **8 seed KHÔNG phải 8 lịch sử thị trường**: tương quan ngày giữa seed 0,975 (SEED_BLEND) ⇒ CI99 theo seed đo nhiễu mô hình,
   không đo bất định đường giá. Hiệu ứng DD chủ yếu đến từ 2022 (LUNA, FTX) = 1 năm gấu.
4. **Kiểm định bội**: 10 công cụ × 2 h = 20 arm sau khi thấy kết quả; ZIL chọn từ screen 2024 (nằm trong cửa sổ đo);
   LINK đề xuất sau khi xem 6 coin.

## 1. Harness sửa (H2)
- Sự kiện E = phút N đổi ∪ phút đổi trọng số giỏ (đầu tháng với DYN). Tại sự kiện e: notional mục tiêu T_c = h·w_c·N(e),
  số lượng q_c = T_c / P_c(e); giữ q_c tới sự kiện kế. PnL phút m = −q_c·(P_c(m) − P_c(m−1)).
- Phí tại sự kiện: (0,05 % + impact) × |T_c(e) − q_c,cũ·P_c(e)| (đúng lượng thực giao dịch, gồm phần trôi giá).
- Coin hết dữ liệu (huỷ niêm yết) ⇒ giá đứng yên, vị thế giữ tới sự kiện kế (không mô phỏng settle/ADL — ghi giới hạn).
- Funding bỏ qua (như cũ). V0: harness cũ tái lập số đã công bố (BTC h0,5 DD22 −17,81; ZIL −11,62; DYN −11,34) ±0,01pp.

## 2. Arm chấm lại (cố định, không thêm)
BTC, ETH, ZIL, LINK, ADA, DOGE, XRP, BNB, SOL, DYN (giỏ đúng như `dyn_sel.json`), DYN_noLUNA (bỏ LUNA khỏi 2022-05, chia đều 4 coin còn lại)
× h ∈ {0,5; 1,0}.

## 3. Tiêu chí "TIỀM NĂNG" (chốt trước; cả 4 phải đạt)
- C1: luật GO gốc trên harness sửa (DD22 nông ≥ 5pp ở ≥ 7/8 seed, ΔCalmar CI99 > 0, ΣPnL giảm ≤ 50 %).
- C2 (bất định đường giá): bootstrap khối 20 ngày, 2000 lần, ghép cặp trên equity ngày trung bình 8 seed từ 2022-01-01:
  P(ΔCalmar > 0) ≥ 0,90 VÀ P(ΔmaxDD > 0) ≥ 0,90.
- C3 (không tạo nguồn DD mới): cửa sổ 2023-01-01 → hết: maxDD hedge không sâu hơn nền quá 2pp (trung bình 8 seed).
- C4 (chi phí thực): C1 vẫn đạt khi thêm impact 25 bps trên lượng giao dịch hedge.
- Đạt cả 4 ⇒ "TIỀM NĂNG — đáng xác nhận 1 lần HO4 2026"; nếu nhiều arm đạt, ứng viên HO4 = arm có ADV 2024 ≥ 100 M USD/ngày
  và trung vị bootstrap ΔCalmar cao nhất. Không arm nào đạt ⇒ đóng họ BOOK_HEDGE ở mức overlay.
- Mô tả kèm: DD/lợi suất theo năm, hedge PnL theo năm, phần đóng góp của LUNA trong DYN.
