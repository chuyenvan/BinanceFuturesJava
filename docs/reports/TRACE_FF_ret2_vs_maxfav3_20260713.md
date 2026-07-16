# TraceData2Test — ret2 vs maxfav3 (data _ff forward-fill, 2026-07-13)

Backtest verify trên dataset `_ff` (funding forward-fill per-minute đã fix), config permissive breaker-OFF, SIM_END_DATE=20260601. Đây là bản trace MỚI NHẤT trên data đã sửa bug.
(Dòng `NoSuchFileException: logs/nohup.out` đầu mỗi file là traceLog phụ thiếu path — vô hại, bảng trace bên dưới đầy đủ.)

## Tóm tắt phân bổ theo nguồn (All: avg / số lệnh / tổng $)

| Nguồn | maxfav3 | ret2 |
|---|---|---|
| DCA_LEVEL1 | 2767 lệnh · **+24.907$** | 2781 lệnh · **+39.996$** |
| BIG_DOWN | **145** lệnh · +555$ | **136** lệnh · +767$ |
| BIG_UP | 183 · +794$ | 272 · +1.237$ |
| PREDICT_SYMBOL_TRADE (selector) | **28.972** lệnh · **−20.800$** | **15.718** lệnh · **−2.993$** |
| SMALL_DOWN_15M | 13.343 · −11.067$ | 19.534 · −18.039$ |
| SMALL_UP | 5.579 · −7.060$ | 8.929 · −9.070$ |

Ghi chú: đây là sim permissive full-history (KHÔNG phải walk-forward). Ở lăng kính này ret2 nhỉnh hơn (DCA lãi hơn, selector ít lỗ hơn). Ở lăng kính WFO chuẩn (walk-forward, config production) thì maxfav3 tốt hơn (WFE 0.596 vs 0.307). Hai lăng kính khác nhau — WFO mới là thước đo out-of-sample đáng tin.

---

## MAXFAV3 — full TraceData2Test

```
Big: HNTUSDT BUY 20240528 14:11 3014
Big: 1INCHUSDT BUY 20240101 07:25 7044
Big: CTSIUSDT BUY 20231224 10:49 3911
Big: ICXUSDT BUY 20231109 21:16 2151
Big: WAVESUSDT BUY 20231223 07:10 6947
Big: IDUSDT BUY 20231030 19:17 2582
Big: DOTUSDT BUY 20230219 20:20 3189
Big: MINAUSDT BUY 20231024 09:06 2214
Big: MTLUSDT BUY 20241126 13:07 2278
Big: ZRXUSDT BUY 20241118 21:58 2598

2021 0.0 -1415.2295 7151.564-> 5736.3345
2022 -1415.2295 -12495.99 1520.6543-> -9560.106
2023 -12495.99 -3805.351 2164.7634-> 10855.402
2024 -3805.351 -5240.4165 5105.1377-> 3670.0718
2025 -5240.4165 -27342.787 1515.6027-> -20586.768
2026 -27342.787 0.0 -30129.303-> -2786.5156

Top ngày lỗ:
20260531  -24469
20260103  -3941
20240528  -2246
20260425  -1757
20210519  -493
20230404  -94
20251218  -90
20220527  -84
20240101  -81
20241209  -78
20230211  -51

2021  Margin: 34673  UnProfitMin: -14231  ProfitMin:  -708  Big:   0/  0  Big_False:   0  Slow_Big_Buy:   0/ 16  UnPnl: -1415  5736   0.16
2022  Margin: 34361  UnProfitMin: -13136  ProfitMin:  -706  Big:   0/  0  Big_False:   0  Slow_Big_Buy:   0/ 48  UnPnl: -12495 -9560  -0.27
2023  Margin: 31643  UnProfitMin: -14415  ProfitMin: -1885  Big:   0/  6  Big_False:   0  Slow_Big_Buy:   6/ 21  UnPnl: -3805  10855  0.31
2024  Margin: 34656  UnProfitMin: -13048  ProfitMin: -2342  Big:   0/  4  Big_False:   1  Slow_Big_Buy:   4/ 37  UnPnl: -5240  3670   0.1
2025  Margin: 34726  UnProfitMin: -29789  ProfitMin:  -225  Big:   0/  0  Big_False:   0  Slow_Big_Buy:   0/128  UnPnl: -27342 -20586 -0.59
2026  Margin: 34689  UnProfitMin: -29771  ProfitMin: -30132  Big:   0/  0  Big_False:   0  Slow_Big_Buy:   0/ 41  UnPnl: 0    -2786  -0.08

DCA_LEVEL1            => All: 6.197   2767  24907   2021: 19.315  642 12070$  2022: 15.827  488  7453$  2023: 21.222  155  6287$  2024: 10.754  685  8721$  2025: -24.357  490 -8632$  2026: -5.529  307  -993$
BIG_UP                => All: 2.074    183    794   2021:  0.794   63    55$  2022:  1.089   22     4$  2023:  2.192   28   210$  2024:  2.344   57   355$  2025:  8.507   13   168$
BIG_DOWN              => All: 1.215    145    555   2021: -0.716   30   -96$  2022:  1.109   13    21$  2023:  2.563   50   526$  2024:  1.059   52   104$
SMALL_DOWN_15M        => All: 0.341  13343 -11067   2021:  0.434 4784 -3516$  2022:  0.175 3209 -4137$  2023:  0.915  964    50$  2024:  0.579 3209 -2017$  2025: -0.701 1177 -1446$
SMALL_UP              => All: 0.126   5579  -7060   2021:  0.151 2033 -2996$  2022:  0.079 1624 -2479$  2023:  0.507  336  -245$  2024:  0.523 1140  -688$  2025: -1.112  446  -650$
PREDICT_SYMBOL_TRADE  => All: 0.085  28972 -20800   2021:  0.704 4059 -1476$  2022:  0.016 2218 -3038$  2023:  0.486 2168  -969$  2024:  0.358 8766 -9337$  2025: -0.392 11761 -5978$
```

---

## RET2 — full TraceData2Test

```
Big: ZILUSDT BUY 20231224 23:05 6661
Big: IDUSDT BUY 20231030 19:09 2845
Big: LUNAUSDT BUY 20220511 20:29 2135
Big: SKLUSDT BUY 20231120 07:02 3412
Big: BANANAS31USDT BUY 20260304 05:38 2637
Big: MELANIAUSDT BUY 20260601 06:59 3397
Big: C98USDT BUY 20260601 06:59 3143
Big: HEMIUSDT BUY 20260601 06:59 2112
Big: MINAUSDT BUY 20231024 02:08 2564
Big: 1000RATSUSDT BUY 20240629 13:54 2431
Big: 1INCHUSDT BUY 20240101 07:09 7221

2021 0.0 -680.661 7683.9966-> 7003.3354
2022 -680.661 -8459.031 665.52264-> -7112.8477
2023 -8459.031 -676.2312 2864.6448-> 10647.444
2024 -676.2312 -1541.5204 7696.131-> 6830.842
2025 -1541.5204 -12457.326 4652.7734-> -6263.032
2026 -12457.326 0.0 -11665.129-> 792.19727

Top ngày lỗ:
20260531  -10461
20220513  -1461
20260103  -720
20260425  -675
20210519  -490
20221109  -76
20241218  -69
20220215  -64
20231120  -59
20221108  -56
20220121  -55

2021  Margin: 33841  UnProfitMin: -12276  ProfitMin:  -874  Big:   0/  0  Big_False:   0  Slow_Big_Buy:   0/  8  UnPnl: -680   7003   0.2
2022  Margin: 33930  UnProfitMin: -12350  ProfitMin: -1740  Big:   0/  1  Big_False:   0  Slow_Big_Buy:   0/ 38  UnPnl: -8459 -7112  -0.2
2023  Margin: 26643  UnProfitMin: -10616  ProfitMin: -1175  Big:   0/  4  Big_False:   0  Slow_Big_Buy:   4/ 14  UnPnl: -676   10647  0.3
2024  Margin: 33833  UnProfitMin: -8762   ProfitMin: -1767  Big:   0/  2  Big_False:   0  Slow_Big_Buy:   2/ 16  UnPnl: -1541  6830   0.2
2025  Margin: 34682  UnProfitMin: -17025  ProfitMin:  -660  Big:   0/  0  Big_False:   0  Slow_Big_Buy:   0/ 86  UnPnl: -12457 -6263  -0.18
2026  Margin: 34654  UnProfitMin: -18247  ProfitMin: -11680  Big:   0/  4  Big_False:   0  Slow_Big_Buy:   4/ 29  UnPnl: 0    792    0.02

DCA_LEVEL1            => All: 15.005  2781  39996   2021: 20.716  608 10130$  2022: 11.126  392  6889$  2023: 22.842   99  5185$  2024: 13.866  384  8337$  2025: 12.238 1119  7615$  2026: 19.515  179  1838$
BIG_UP                => All:  2.81    272   1237   2021:  2.25    74   376$  2022:  1.028   25    -3$  2023:  1.469   25   116$  2024:  1.851   47    84$  2025:  4.439  101   662$
BIG_DOWN              => All: 1.366    136    767   2021: -0.24    21   -32$  2022:  2.293   13   147$  2023:  2.599   48   644$  2024:  0.595   40   -26$  2025:  0.893   14    34$
PREDICT_SYMBOL_TRADE  => All: 0.733  15718  -2993   2021:  0.996 3112  1373$  2022:  0.295 1473 -1463$  2023:   1.39  707   558$  2024:  0.907 3591  -689$  2025:  0.548 6835 -2772$
SMALL_DOWN_15M        => All: 0.306  19534 -18039   2021:  0.488 4933 -3049$  2022:  0.159 3433 -4837$  2023:  1.018  937   396$  2024:  0.566 3110 -1916$  2025:  0.045 7121 -8632$
SMALL_UP              => All: 0.241   8929  -9070   2021:  0.207 2049 -2926$  2022:  0.217 1712 -2180$  2023:  0.697  315  -103$  2024:  0.766 1031  -205$  2025:  0.091 3822 -3653$
```
