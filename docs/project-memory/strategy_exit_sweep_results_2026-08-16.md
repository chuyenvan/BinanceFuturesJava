# Exit-param sweep (net) — Gate 0 ĐÓNG (2026-08-16)

Công cụ: `ExitParamSweepProbe` — sim thật `SimulatorMarketLevelTicker1MStopLoss` (slippage 0.3% + funding) trên `wfo_ds_G015x26e` (2021-2026 liên tục), không fanout/train lại. ⚠️ genome DEFAULT (không HPO) → số RELATIVE (hình dạng), không phải PnL canonical.

## MAX_GAP (trailing giveback width) — PHẲNG
0.05=19,245 | 0.08=19,676 | 0.15=19,876 | 0.30=20,856 | 0.60=20,652 | 1.0=20,549. Swing <9% qua dải 20×. **Trailing width là đòn bẩy gần chết.**

## RATE_PROFIT_STOP (profit-stop) — NHẠY, có ĐỈNH + VÁCH
| RATE | Total | hold median | ddMtm | %>7d | trades |
|---|---|---|---|---|---|
| 0.02 (lướt chặt) | +17,171 | 56' | 24.6% | 2.8% | 4684 |
| **0.05 (default)** | **+19,676 ĐỈNH** | 701' (~12h) | 30.6% | 13.0% | 2686 |
| 0.10 (nuôi lỏng) | **−4,587 SỤP** | 6135' (4.3d) | 44.5% | 43.5% | 741 |
| 0.20 | (chạy nốt, kỳ vọng tệ hơn) | | | | |

Curve inverted-U có vách: **đỉnh đúng RATE_PROFIT=0.05 (config hiện tại)**. Lỏng hơn → giữ lệnh nhiều ngày → ăn trọn "dump dài" → PnL ÂM.

## KẾT LUẬN GATE 0 (đóng dứt điểm)
1. **Exit của config hiện tại ĐÃ Ở ĐỈNH.** Không có tweak exit đáng cho v1. Giữ RATE_PROFIT=0.05, MAX_GAP mặc định.
2. **Tranh luận lướt↔nuôi khép lại bằng data**: over-nuôi (giữ lâu) = thảm hoạ (−4.6k, hold 4.3d), đúng lo ngại đuôi trái (maxAdv −40% ở path analysis). Raw-path phóng đại nuôi vì bỏ qua việc giữ lâu ăn trọn dump + so với strawman thoát-4h.
3. **Đính chính chuỗi phân tích**: raw-path (nuôi 10×, SAI) → MAX_GAP sweep (phẳng) → RATE_PROFIT sweep (nhạy, đỉnh tại default). Kết cục: **moderate hiện tại là tối ưu**, không chặt hơn không lỏng hơn.
4. Exit-tuning KHÔNG còn ở Track 2 nữa — coi như đã giải quyết. v1 giữ nguyên exit.

## Ý nghĩa v1
Đơn giản hoá v1: không cần đổi/tune exit. Trọng tâm v1 dồn vào Gate 1 (wire selector mới vào live engine + feature service + reconcile), không phải chiến lược exit.
