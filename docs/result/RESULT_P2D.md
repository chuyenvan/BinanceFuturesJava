# RESULT P2-D — điểm REX S1 trên các lệnh sim K24+skipFull (MASTER 2026-10-17)

- **Pre-reg:** `docs/prereg/PREREG_P2D.md` (1428ed6e).
- **Code:** `research/p2d/p2d.py`.
- **Output:** `~/claude_master/p2d/` gồm `p2d_result.json`, `p2d.log` và `p2d_trades_a1_C1.parquet`.

## Kiểm dữ liệu
- **Múi giờ sim là UTC+7.** Đã xác minh bằng giá: 19/20 lệnh có giá vào khớp chính xác close nến 1m Vision tại `start − 7h`. Nếu không phát hiện điểm này, việc ghép điểm REX theo ngày sẽ lệch tới 7 giờ, có thể gây lookahead.
- **Độ phủ thấp hơn ngưỡng đã khai.** Chỉ 57 % lệnh DEV có điểm REX (ngưỡng V2 là 85 %). 43 % lệnh K24 rơi vào coin ngoài universe REX: thanh khoản < 20M/ngày hoặc niêm yết < 60 ngày. Vẫn chạy theo pre-reg.

## VERDICT: **NO-GO** — G1, G3, G4, G5 trượt; chỉ G2 và G6 đạt

### Bảng DEV 2022–2024 (seed A1, model C1, profit = ROI % trên margin)
| Bucket | n | mean | median | win | SL | Σpnl $ | pnl/lệnh |
|---|---|---|---|---|---|---|---|
| NA (ngoài universe REX) | 940 | **4,81** | 5,50 | 0,87 | 0,15 | 36 942 | 39,3 |
| Q1 (REX xếp thấp nhất) | 643 | 2,58 | 5,50 | 0,83 | 0,19 | 16 641 | 25,9 |
| Q2 | 246 | 3,53 | 5,50 | 0,83 | 0,18 | 6 882 | 28,0 |
| Q3 | 150 | 3,42 | 5,50 | 0,83 | 0,19 | 3 174 | 21,2 |
| Q4 | 123 | 4,85 | 5,99 | 0,86 | 0,23 | 3 224 | 26,2 |
| Q5 | 100 | 3,31 | 6,00 | 0,82 | 0,21 | 2 146 | 21,5 |

### Thống kê chính và độ bền
| Phép kiểm | Kết quả |
|---|---|
| Δ = Q1 − (Q2…Q5), DEV | −1,15 điểm ROI, CI [−2,90; +0,54]: chưa có ý nghĩa thống kê |
| Theo năm 2022 / 2023 / 2024 | −4,42 / −0,39 / −1,09 (cùng dấu) |
| VAL 2025 | **+0,49**, CI [−5,2; +5,9]: hiệu ứng mất |
| 8 seed | Δ âm ở 8/8 seed (−0,93 … −1,86), nhưng cận trên CI < 0 chỉ ở 3/8 (cần 6/8) |
| Model C3 / C7 | Δ −0,96 / −0,75, CI đều chứa 0 |
| Tercile vol | thấp +0,39 · giữa −0,87 · cao −2,45 ⇒ hiệu ứng chỉ nằm ở coin vol cao |
| Veto vol đơn giản (top 20 % vol30) | Δ −0,75, Σpnl của nhóm bị loại vẫn +15,9k ⇒ cũng không đáng dùng |

## Diễn giải
1. **K24 vốn vào chủ yếu đúng loại coin mà REX xếp thấp.** 51 % lệnh có điểm rơi vào Q1. Điều này hợp lý, vì crash-buy mua coin vol cao đang sập.
2. **Lệnh Q1 vẫn LÃI.** Σpnl +16,6k, chiếm 24 % lãi DEV. Tính theo $/lệnh thì Q1 (25,9 $) không kém nhóm còn lại (24,9 $); ROI % thấp hơn nhưng margin lớn hơn.
   - ⇒ Veto Q1 sẽ **mất tiền**, trừ khi slot được nhả ra và lấp bằng lệnh tốt hơn. Muốn biết thì phải sim, và với Δ không có ý nghĩa thống kê thì không đáng tốn một vòng sim.
3. **Nhóm lãi nhất là NA:** coin ngoài universe REX (thanh khoản thấp, mới niêm yết), mean ROI 4,8 % ở DEV và 5,6 % ở VAL.
   - Một phần edge của crash-buy nằm ở vùng mà selector theo mặt cắt thanh khoản không nhìn tới.
   - Đây là chỉ báo rủi ro thanh khoản/capacity cho go-live, không phải tín hiệu để cải tiến.
4. Dấu âm nhất quán ở mọi seed và mọi model, nhưng độ lớn khoảng 1 điểm ROI, chỉ có ở coin vol cao, và biến mất năm 2025. Đây là kết luận chắc chắn, không phải NO-GO do phân tích mỏng: **REX không cải thiện được việc chọn coin của K24.**

Ledger cộng 1.
