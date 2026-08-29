# Audit lệnh LIVE 4h đầu (lệnh thật) vs backtest — 2026-08-21 09:45 +07

Kéo log 242 (`/home/chuyennd/java/v_t_m/logs/full.log`) qua git-ssh (port 2222, key id_rsa_chuyennd). Go-live lệnh thật 06:14; audit cửa sổ 06:15→09:40 (16 lệnh thật).

## KẾT LUẬN: KHÔNG phát hiện bug/vênh mới. Cơ chế khớp backtest. Vênh duy nhất còn lại là 3 thay đổi cố ý hôm nay + concurrent-position chưa đo.

## Số liệu verify
| Hạng mục | Kết quả | vs backtest |
|---|---|---|
| Lệnh thật (post 06:14) | 16 | — |
| Shadow would-BUY (pre 06:14) | 83 | — |
| Distinct ticks có entry | 10 | — |
| Coins/tick | max 3 (5 tick×1, 4 tick×2, 1 tick×3) | ✅ ≤ K5, **0 vi phạm cap** |
| Same coin multi-leg CÙNG tick | 0 | ✅ không over-leg 1 tick |
| Dedup | "BudgetManager: Remove symbol trade success [ONG]" trước mỗi re-entry | ✅ khớp symbolLocked |
| Giá entry | = close nến 1m signal-minute, KHỚP TUYỆT ĐỐI | ✅ 0% slippage |
| pred-gap | active (Renew SL gap −2.5/−3% ban đầu) | thay đổi hôm nay |
| arm 15% | active (SL arm ~15% rồi trail lên 33%) | thay đổi hôm nay |
| Concurrent positions | 65 (pre) → 77 (now) | ⚠️ chưa đo backtest |

## Price parity re-confirm (độc lập vs Binance fapi)
- ONG signal 09:29 → Binance 1m close **0.13508** = entry log 0.13508. Khớp từng chữ số.
- ONG signal 08:44 → Binance 1m close **0.12693** = entry log 0.12693. Khớp.
→ Live vẫn lấy đúng close nến signal-minute, không lấy high, slippage 0%. (Tái xác nhận live30_audit.)

## Ca ONGUSDT ×5 — làm rõ (trả lời trực tiếp "còn vênh gì")
ONG pump 0.08→0.145 (+~80%) sáng nay. Bot vào 5 lần giá TĂNG dần:
06:15 @0.07997 · 07:30 @0.10831 · 08:00 @0.11166 · 08:45 @0.12693 · 09:30 @0.13508.
**Nhưng KHÔNG phải pyramid/DCA-up tích luỹ.** Mỗi leg ĐÓNG (BudgetManager Remove ONG: 07:28, 07:49, 08:31, 09:29, 09:44) TRƯỚC khi vào lại tick sau. Cơ chế = **trailing-stop đóng winner → dedup mở khoá → re-enter tick kế khi giá vẫn leo**. Tại 1 thời điểm chỉ ~1 leg ONG mở. Tất cả 5 leg đóng CÓ LÃI (trailing SL trên giá vốn: leg cuối SL 0.14597 > entry 0.13508).
→ **Xác nhận nhận định user: không có DCA-up ở live.** Đây là re-entry churn trên coin đang pump, ĐÚNG cơ chế backtest (maxdd_anatomy A5: re-entry-run tồn tại trong backtest). Không phải bug. Hôm nay ONG leo suốt nên không "kẹt"; rủi ro "kẹt" chỉ hiện nếu leg cuối re-enter ngay trước dump (tail re-entry-run, giống backtest).

## Ghi chú kỹ thuật
- Trailing exit dùng **Binance Stop-Loss Algo (STOP_MARKET) treo trên sàn** ("Create Stop Loss Algo ONGUSDT qty ... price ..."). Đây là stop-treo NHÌN THẤY được — liên quan lo ngại MM-quét-SL của user; tuy nhiên đây là stop TRAILING theo lãi (arm rồi trail lên), không phải SL cố định dưới entry.

## Vênh THẬT còn lại (không phải bug, cần xử lý)
1. **Baseline backtest đã lệch live.** Live nay chạy arm 15% + pred-gap; canonical backtest = arm 26% + no pred-gap. → "live vs backtest" KHÔNG còn apples-to-apples cho tới khi cập nhật baseline backtest sang arm15+predgap. Đây là reconciliation gap thật hiện tại (do 3 thay đổi cùng lúc hôm nay).
2. **Concurrent positions = 77** (gồm vị thế legacy từ thời shadow, pre-go-live đã 65). Backtest concurrent-max CHƯA đo (open item #5 live30_audit). Đây là divergence rủi ro duy nhất chưa định lượng — nên chạy sim đếm active-order max để so.
3. Audit này là parity CƠ CHẾ (cap/giá/dedup/re-entry), KHÔNG phải reconcile P&L số-với-số trên cùng cửa sổ (cần chạy sim trên data hôm nay; WFO hiện batch tới 2026-07).

## Việc đề xuất
- Cập nhật baseline backtest = arm15 + pred-gap để so tiếp cho đúng.
- Chạy sim đếm concurrent-position max vs 77 để đóng open item #5.
- Theo dõi re-entry-run leg-cuối: nếu leg cuối của một run dính dump → đó là chỗ "kẹt" (đúng tail đã bàn), cân nhắc chống-đuổi-đỉnh (cấm re-enter nếu giá > entry-run-đầu × (1+chase_limit)).
