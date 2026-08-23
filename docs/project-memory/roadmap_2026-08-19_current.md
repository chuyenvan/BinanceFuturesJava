# ROADMAP HIỆN TẠI — 2026-08-19
Thay thế roadmap_v1_release_and_nuoi_pivot_2026-08-16. Bối cảnh: v1 engine ĐÃ chạy live (bot 242);
phiên 17–19/08 tập trung xác thực live↔backtest + tìm gốc "vào lệnh liên tục" + đóng hướng gate.

## VỊ TRÍ HIỆN TẠI (1 dòng)
Live bot đang chạy = engine v1. Entry logic + giá + feature đã xác thực KHỚP backtest. Đang ở giai đoạn
**reconcile hành vi live (shadow-mode) + debug over-entry + quyết định đòn bẩy exit/tail**. Gate đã hết dư địa.

## ĐÃ ĐÓNG (closed)
1. **Gate label optimization — HẾT DƯ ĐỊA.** old5m (basketMaxGain 15m @5m) = 12660 là trần. net-all thua mọi threshold
   (đỉnh 11475); label 24h thua đều (max24h p10/p05/p03 = 8239/7591/6527). Momentum dài non-stationary (OOS AUC ~0.5).
   → KHÔNG đổi gate. Đòn bẩy nằm ở exit/tail, không phải gate. (docs: gate_24h_label_verdict, gate_ab_5m_windowbug)
2. **Giải phẫu maxdd.** Edge selector THẬT (99% pump, mfe1d +21%). "Ăn ít" = lỗi EXIT không gặt (+21% có sẵn).
   "Đuôi lớn" = SẬP ĐƠN-COIN fat-tail (LUNA/Terra + meme mới list pump-rồi-chết), KHÔNG phải basket-đỉnh;
   burst không tệ hơn, re-entry cuối an toàn hơn đầu (bác giả thuyết). (doc: maxdd_anatomy_tail_singlecoin)
3. **Live↔backtest reconcile (phần lớn).** Gate ✅ (WFO fold_20 RAW, pred khớp). Selector ✅ OI 45/45
   (ComputeOiFeat2Live242 đã là thread trong ingestor, push 691/vòng — KHÔNG còn NaN). Giá entry ✅ = close nến 1m
   (slippage ~0%, không "lấy high"). Exit = env 0.05. NUMBER_ENTRY_EACH_SIGNAL=4 chỉ cho leg bigdown, selector không dùng.
   (docs: live30_audit_findings, runbook_live_242 rev3)
4. **Trailing signal test.** Selector per-coin pred > gate market pred cho gap (AUC 0.601 vs 0.521, corr −0.43). (doc: trailing_selector_vs_gate_pred)

## ĐANG CHẠY (in progress)
5. **Shadow-mode trên live** (deploy 19/08): bot log `would-BUY`, KHÔNG đặt lệnh thật; 75 vị thế cũ vẫn quản lý.
   Mục đích: đối chiếu nhịp vào-lệnh-ý-định của live vs backtest AN TOÀN (không tiền thật) để tìm gốc "vào lệnh liên tục".
   Toggle: env SHADOW_NO_PUSH. (đang verify dòng would-BUY đầu tiên)
6. **Multiplier sweep (toan_ky)** trên Oracle: tìm TS_PROFIT_MULTIPLIER blended. Đỉnh sơ bộ ~mult 1.5 (arm ~7.5%) <<
   live 5.21847 (26%). ⚠️ arm là knob KÉM NHẠY trên blended (bull áp đảo che crash) — cảnh báo đừng chốt thẳng số blended.
   + close-mode sweep (peak vs current SL) chờ sau.

## TIẾP THEO (next — cần user chốt scope)
7. **Debug full luồng backtest "vào lệnh liên tục"**: đếm từng khâu/tick (gate pass → selector topK → dedup → budget → vào)
   ở cả live-shadow lẫn backtest; so tần suất (backtest ~1.2 lệnh/ngày vs live ?). Nghi TP nhanh recycle → re-enter mỗi tick.
8. **Quyết định exit/tail (đòn bẩy chính, có evidence):**
   - (a) Trailing đọc selector pred thay gate pred cho gap.
   - (b) HARD catastrophic-stop theo entry (~−15/−18%) cắt sập đơn-coin — hiện SL chỉ arm khi +26% lãi nên coin sập
        thẳng không có stop. Lưu ý A2: lệnh dip ~3.5h trước khi pump 12h → hard stop phải > ngưỡng dip thường.
   - (c) Arm SL theo REGIME (crash arm sớm ~12.5%, bull arm muộn) thay vì 1 con mult chung.
   - A/B sim ghép (a)+(b)+(c) trên full-range → đo net P&L + maxdd trước khi mở lại push lệnh.
9. **Filter chất lượng coin (selector-side)**: loại/giảm size coin mới list <N ngày, thanh khoản thấp — chỗ DUY NHẤT
   selection cứu được đuôi (LUNA/meme).

## TRACK 2 / TỒN
- Sizing theo regime xấu nhất, kill-switch, monitor coverage (lịch sử label-merge-bug mất 29% dòng âm thầm).
- Pipeline inference liên tục feed Aerospike/file cho live (WFO hiện batch tới 2026-07).
- 5m/1m grid (fix OOM). DCA v2 market-gated (hiện off).

## NGUYÊN TẮC
- Live = tiền thật, READ-ONLY trừ khi user duyệt. Mở lại push lệnh CHỈ sau khi shadow reconcile sạch + A/B exit dương.
- Không đổi gate (hết dư địa). Mọi cải tiến P&L tập trung exit/tail + lọc coin.
