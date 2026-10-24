# SHORTVOL_T0 — tầng 0: VRP BTC/ETH + proxy bán straddle 7 ngày, chồng rủi ro với X14: KẾT QUẢ

- Prereg: `docs/prereg/PREREG_SHORTVOL_T0.md`, commit **73a23fae**, sha256 `33aed30f3e11472c9cb2619f28b4db73e4c617a3962375bf6c52c2df2db0ab95`. Commit trước mọi VRP/PnL.
- Code: `research/shortvol_t0/` (sv_fetch_dvol, sv_prep, sv_run, sv_indep, sv_valid). Artefact: `docs/result/shortvol_t0/` (run.json, log).
- Dữ liệu DVOL Deribit **không commit** (Membership Terms cl. 2.10 "personal use only", cấm publish/forward). sha256 CSV 1D: BTC `f5ec5da44c0f10ffe3b880d5fd9bbbb67c7fa99caa779a831fefa6b698fcad60`, ETH `b80b0de9f411dcf78d7d411298f77bac7b4757da36630c500352adc5eeafe6d8`. Tải lại bằng `sv_fetch_dvol.py`.

## Verdict: **NO-GO ⇒ ĐÓNG short-vol** (BTC trượt V3)

| Tiêu chí | BTC | ETH (kèm) |
|---|---|---|
| V1 VRP30 > 0 ≥ 3/4 năm, mean > 0, CI95 cận dưới > 0 | **Đạt** | Trượt |
| V2 straddle net mean > 0 ≥ 3/4 năm, Sharpe ≥ 0,8 | **Đạt** (0,92) | Trượt |
| V3 đối chứng bỏ tuần X14 gần đây vẫn đạt V2 | **TRƯỢT** (Sharpe 0,24) | Trượt |
| V4 DD gộp 80/20 ≥ DD X14 − 3 điểm, cả 2 kỳ | Đạt | Trượt |

Ý nghĩa: có VRP thật (BTC), nhưng phần lãi short-vol **dồn vào các tuần ngay sau khi X14 vào lệnh** (sau sập, IV cao rồi xẹp). Bỏ các tuần đó thì còn mean 0,26 %/tuần trên tuần có bán, Sharpe 0,34 ⇒ không có VRP "đều tay ngoài lúc sập". VRP còn đang co lại: BTC VRP30 2025 chỉ +1,6 điểm, straddle 2024–25 chỉ +0,18 / +0,24 %/tuần.

## Bảng số chính

### VRP (điểm vol; DVOL tại 00:00 UTC ngày t − RV 5′ cửa sổ tương lai)
| | BTC | ETH |
|---|---|---|
| VRP30 mean cả kỳ (n = 1 431) | **+5,49** | +2,22 |
| CI95 block-bootstrap tháng | [+2,73; +8,34] | [−1,60; +6,21] |
| VRP30 2022 / 2023 / 2024 / 2025 | +10,56 / +4,20 / +5,26 / +1,64 | +7,82 / +2,48 / +1,94 / **−3,87** |
| % ngày VRP30 > 0 | 68,9 % | 58,8 % |
| DVOL TB / RV30 TB | 57,0 / 51,5 | 69,7 / 67,5 |
| VRP7 mean (lệch kỳ hạn, mô tả) 2022/23/24/25 | +12,5 / +6,4 / +6,1 / +2,7 | +10,2 / +4,6 / +3,7 / −1,4 |

### Proxy bán straddle ATM 7 ngày (208 tuần, % S0 / tuần, net phí 0,024 %×2 + slippage 5 % premium)
| | BTC | BTC đối chứng (V3) | ETH | ETH đối chứng |
|---|---|---|---|---|
| mean/tuần | **+0,677 %** | +0,127 % | −0,026 % | −0,573 % |
| Sharpe tuần ×√52 | **0,92** | **0,24** | −0,03 | −0,73 |
| mean 2022 / 2023 / 2024 / 2025 | +1,67 / +0,62 / +0,18 / +0,24 | +0,44 / +0,13 / −0,28 / +0,23 | +0,25 / +0,87 / −0,40 / −0,83 | −0,80 / −0,05 / −1,01 / −0,43 |
| maxDD (cộng dồn 1x notional) | −35,3 % | −34,9 % | −75,0 % | −84,2 % |
| tỉ lệ tuần lãi / payoff ratio | 67,3 % / 0,67 | (103 tuần bán) 63,1 % / 0,66 | 60,1 % / 0,66 | 55,3 % / 0,54 |
| tuần tệ nhất | −19,57 % | −18,78 % | −32,86 % | −32,86 % |
| p1 / p5 / p50 / p95 | −18,7 / −8,6 / +2,1 / +6,5 | | −23,3 / −13,1 / +1,7 / +7,2 | |

- Đối chứng: 105/208 tuần bị bỏ (có leg X14 union 8 seed mở trong 7 ngày trước 08:00 thứ Hai). 105 tuần bị bỏ của BTC mang trung bình ≈ +1,09 %/tuần; 103 tuần còn lại +0,26 %/tuần.
- Premium TB 6,35 % S0 (BTC), payoff TB 5,31 %; phí sàn 0,048 % (trần 10 % premium không bị chạm lần nào).
- Độ nhạy slippage (mô tả) BTC: 2 % ⇒ mean +0,87 %, Sharpe 1,18; 10 % ⇒ mean +0,36 %, Sharpe 0,49, **2024 và 2025 âm**. ETH: 2 % ⇒ Sharpe 0,22; 10 % ⇒ −0,44.

### Chồng rủi ro với X14 (median seed s2024, equity tuần MTM, tuần neo 00:00 UTC thứ Hai)
| | 2022–23 | 2024–25 | cả kỳ |
|---|---|---|---|
| corr(PnL straddle BTC, r X14) | +0,11 | −0,14 | +0,01 |
| maxDD X14 một mình | −12,9 % | −3,0 % | −12,9 % |
| maxDD gộp 80 % X14 + 20 % straddle BTC | −11,0 % | −4,6 % (−1,6 điểm) | −11,0 % |
| Sharpe X14 / gộp | 2,17 / 2,48 | 2,87 / 2,71 | 2,48 / 2,55 |
| maxDD gộp với ETH | −13,6 % | **−14,1 %** (−11 điểm) | |

- Tổng PnL straddle BTC trong 143 tuần X14 có leg (giao tuần bán): +40,4 % (TB +0,28 %/tuần); 65 tuần không leg: +100,5 % (TB +1,55 %/tuần). Lưu ý: định nghĩa "có leg" này đồng thời (không causal), khác với lọc causal của V3.
- 10 tuần tệ nhất BTC: 8/10 trùng tuần X14 có leg (tỉ lệ nền 143/208 = 69 %, nên không dồn rõ hơn nền); 3/10 rơi vào tuần bị lọc V3.
- V4 từng seed X14 (mô tả): BTC 2022–23 đạt 8/8; 2024–25 đạt 7/8 (a1: −6,3 % vs −3,0 %, lệch −3,3 điểm). ETH 2024–25 trượt 8/8.

### Đuôi (BTC; ETH trong run.json)
| tuần (thứ Hai) | PnL | biến động S | DVOL | X14 tuần |
|---|---|---|---|---|
| 2023-03-13 (tệ nhất) | −19,57 % | +25,7 % | 58,9 | +0,09 % |
| 2024-02-26 | −19,08 % | +24,8 % | 55,2 | +5,20 % |
| 2024-07-29 (05/08) | −18,78 % | −24,3 % | 52,7 | 0,00 % |
| 2023-01-09 | −18,37 % | +22,8 % | 42,8 | +2,32 % |
| LUNA 2022-05-09 | −4,47 % (hạng 34) | −11,6 % | 68,6 | −8,58 % |
| FTX 2022-11-07 | −12,36 % (hạng 6) | −18,3 % | 56,8 | −6,77 % |
| 2025-10-06 (10/10) | −2,63 % (hạng 45) | −6,6 % | 38,0 | +9,78 % |

5/10 tuần tệ nhất BTC là tuần **tăng** mạnh (2023-03-13, 2024-02-26, 2023-01-09, 2024-11-04, 2023-06-19) (short straddle thua cả hai phía). ETH tệ nhất 2025-05-05 (+39,7 %) −32,9 %.

## Validation
- **V1v** PASS: ts int64; 2 105 280 nến 1m/symbol, ts duy nhất, bước 60 000 ms; 288 return 5′/ngày, 1 440 return 1m/ngày (assert); 208 tuần (2022-01-03 → 2025-12-22, đều thứ Hai); 1 431 ngày VRP30 (2022-01-01 → 2025-12-01). 0 phút ffill.
- **V2v** PASS: `sv_indep.py` (đọc lại raw parquet + JSON DVOL thô, không import pipeline): VRP30 2023 BTC 4,201434615324 vs 4,201434615324, Δ = 4,4e-14; PnL 10 tuần 2023-01-02 → 2023-03-06, max |Δ| = 6,9e-17.
- **V3v** PASS (kiểm tay BTC): 2022-05-09: P = 0,8·0,6859·√(7/365)·33 512 = 2 546,56; phí 2×8,043; slip 127,33; payoff |29 611,2 − 33 512| = 3 900,8 ⇒ −1 497,6/33 512 = −4,469 % ✓. 2023-06-05: P 1 238,59, payoff 1 028,9 ⇒ +0,503 % ✓. 2025-10-06: P 5 188,99, payoff 8 113,9 ⇒ −2,628 % ✓. S0/S_T khớp raw parquet, σ khớp nến DVOL 1h 23:00 Chủ nhật (= 00:00 thứ Hai). ETH cùng 3 tuần khớp (assert).
- **V4v** PASS: RV30 TB BTC 5′ 51,5 / 1m 52,0 / daily 49,2 (tỉ số 1,01 / 0,95); ETH 67,5 / 68,6 / 66,5.
- **V5v** PASS: DVOL 1D BTC/ETH 1 491/1 491 ngày, ts đều 00:00 UTC, 0 trùng, 0 thiếu; close 1D = close nến 1h 23:00 cùng ngày (1 491/1 491). Không thấy spike giả: |giá trị 00:00 − median ±3h| > 5 điểm chỉ 1 ngày mỗi coin (BTC 2023-08-18, ETH 2022-11-10, đều là ngày sập thật), không ngày nào > 10.

## Lệch thiết kế (đã ghi trong prereg §6)
1. Không cần ffill: BTC/ETH không thiếu phút nào; các lỗ đã biết (2022-02-26 …) là lỗ vũ trụ symbol (139 → 91). Phút n_trades = 0 / inactive: BTC 308, ETH 213 (nến phẳng, return 0 ⇒ RV hơi thấp, không đáng kể).
2. DVOL không commit (điều khoản Deribit), chỉ script + sha256 + thống kê.
3. Tuần X14 neo 00:00 UTC (lệch 8 h so với tuần straddle 08:00).
4. VRP30 dừng t = 2025-12-01, tuần cuối 2025-12-22 (không dùng 2026).
5. Leg X14 = mọi dòng printDone (cả PREDICT_SYMBOL_TRADE), union 8 seed.

## Rủi ro / điểm nghi ngờ
- **Proxy lạc quan.** σ = DVOL 30 ngày, không phải IV 7 ngày. Không có skew, không có bid/ask Binance, không có basis Deribit→Binance, không tính phí exercise 0,015 % (≈ 0,015 % S0/tuần, nhỏ so với mean 0,68 %). Tầng 1 thật gần như chắc chắn tệ hơn: ở slippage 10 % thì BTC 2024–25 đã âm.
- **Lọc V3 rộng.** Dùng mọi dòng printDone của 8 seed nên lọc bỏ 50 % số tuần. Một định nghĩa hẹp hơn (chỉ BIG_DOWN) có thể cho số khác. Đã khoá trong prereg nên **không thử** (sẽ là tune sau khi thấy kết quả).
- **V4 đạt nhưng mong manh.** DD X14 tuần 2024–25 chỉ −3,0 % (lấy mẫu tuần làm mượt; DD ngày ở TREND_T1 là −6,4 %). Straddle 1x notional có lỗ tuần đơn lẻ −19,6 %, maxDD riêng −35 %. Một seed (a1) đã trượt V4.
- Lỗ đuôi có ở **cả hai phía**: 5/10 tuần tệ nhất là tuần tăng mạnh. Vì vậy short-vol không chỉ chồng với sập mà còn dễ vỡ trong các đợt squeeze lên.
- Chưa giải thích: không có.

## HO 2026
Không chạy (thiết kế để HO sau; NO-GO nên không cần).
