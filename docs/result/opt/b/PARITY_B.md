# PARITY_B - engine Python vs ledger sim Java a8690d46 (baseline arm 0.07 / giveback 1.0 / cap 0.03 / TS 168 / X14 336)

```
{
 "n_total": 20881,
 "cat_counts": {
  "ok": 20881
 },
 "n_tested": 20881,
 "n_open_at_window_end": 0,
 "pct_all3": 100.0,
 "pct_all3_over_all_clusters": 100.0,
 "pct_minute": 100.0,
 "pct_price": 100.0,
 "pct_status": 100.0,
 "by_status_ledger": {},
 "by_reason_engine": {},
 "by_year": {},
 "by_tick_known": {},
 "by_dca": {},
 "by_x14ext_hold": {},
 "minute_only_wrong": 0,
 "price_only_wrong": 0,
 "dmin_quantiles": {},
 "by_seed": {
  "c0s123": {
   "n": 3516,
   "pct_all3": 100.0
  },
  "c0s13": {
   "n": 3392,
   "pct_all3": 100.0
  },
  "c0s42": {
   "n": 3402,
   "pct_all3": 100.0
  },
  "c0s7": {
   "n": 3521,
   "pct_all3": 100.0
  },
  "r1a3_a1": {
   "n": 3559,
   "pct_all3": 100.0
  },
  "r1a3_s7": {
   "n": 3491,
   "pct_all3": 100.0
  }
 },
 "pnl_absdiff_ledgerfund_q": {
  "0.0": 0.0,
  "0.5": 4.25537109549623e-07,
  "0.9": 3.237304682102149e-06,
  "0.99": 1.0244140639770194e-05,
  "1.0": 8.193359371944098e-05
 },
 "delist_window": {
  "n_cluster_seed": 197,
  "cat": {
   "ok": 197
  },
  "n_unique": 65,
  "excluded": []
 },
 "pnl": {
  "ledger_funding_absdiff": {
   "0.5": 4.25537109549623e-07,
   "0.95": 3.930664064455414e-06,
   "0.99": 1.0244140639770194e-05,
   "1.0": 8.193359371944098e-05
  },
  "vision_funding_absdiff": {
   "0.5": 4.279785130734126e-07,
   "0.95": 4.077148446413048e-06,
   "0.99": 1.3281250039653969e-05,
   "1.0": 3.8578384570312494
  }
 },
 "funding": {
  "n": 20881,
  "abs_usdt": {
   "0.5": 1.627655010771889e-09,
   "0.95": 6.954956077720453e-08,
   "0.99": 5.299072292075428e-07,
   "1.0": 3.8578314781188965
  },
  "rel_capital": {
   "0.5": 1.9710547953952367e-12,
   "0.95": 8.7626845342479e-11,
   "0.99": 5.377127963834817e-10,
   "1.0": 0.003845458139735576
  },
  "rel_abs_pnl": {
   "0.5": 2.8158161858722455e-11,
   "0.95": 1.3568184108940973e-09,
   "0.99": 8.999065995706342e-09,
   "1.0": 0.06934276090351803
  },
  "pct_rel_capital_gt_1e-6": 0.3687562856185049,
  "n_rel_capital_gt_1e-6": 77,
  "max_ret_pp": 0.3845458139735576,
  "sum_fund_l": -15123.491399515371,
  "sum_fund_e": -15094.380994005725,
  "big_ledger_zero": 77,
  "big_engine_zero": 0,
  "big_by_sym": {
   "LIT": 77
  },
  "big_by_year": {
   "2022": 34,
   "2021": 31,
   "2023": 12
  },
  "big_rows": [
   {
    "seed": "c0s123",
    "sym": "LIT",
    "t_first": 1667880780000,
    "t_end_l": 1669695240000,
    "fund_l": 0.0,
    "fund_e": 3.8578314781188965,
    "capital": 1003.21765,
    "rel_cap": 0.003845458139735576
   },
   {
    "seed": "c0s13",
    "sym": "LIT",
    "t_first": 1667880780000,
    "t_end_l": 1669695240000,
    "fund_l": 0.0,
    "fund_e": 3.1886229515075684,
    "capital": 829.192,
    "rel_cap": 0.003845457929535703
   },
   {
    "seed": "r1a3_s7",
    "sym": "LIT",
    "t_first": 1667880780000,
    "t_end_l": 1669695240000,
    "fund_l": 0.0,
    "fund_e": 3.0744035243988037,
    "capital": 799.4896,
    "rel_cap": 0.0038454578075797405
   },
   {
    "seed": "c0s7",
    "sym": "LIT",
    "t_first": 1667880780000,
    "t_end_l": 1669695240000,
    "fund_l": 0.0,
    "fund_e": 3.1952123641967773,
    "capital": 830.9056,
    "rel_cap": 0.0038454577321380156
   },
   {
    "seed": "c0s42",
    "sym": "LIT",
    "t_first": 1667880780000,
    "t_end_l": 1669695240000,
    "fund_l": 0.0,
    "fund_e": 3.3486030101776123,
    "capital": 870.79443,
    "rel_cap": 0.003845457544069973
   },
   {
    "seed": "r1a3_a1",
    "sym": "LIT",
    "t_first": 1667880780000,
    "t_end_l": 1669695240000,
    "fund_l": 0.0,
    "fund_e": 3.1366379261016846,
    "capital": 815.6736,
    "rel_cap": 0.0038454572099693857
   },
   {
    "seed": "r1a3_a1",
    "sym": "LIT",
    "t_first": 1631028300000,
    "t_end_l": 1631034360000,
    "fund_l": 0.0,
    "fund_e": -0.49313268065452576,
    "capital": 132.00279,
    "rel_cap": 0.0037357746806300513
   },
   {
    "seed": "c0s7",
    "sym": "LIT",
    "t_first": 1631028300000,
    "t_end_l": 1631034360000,
    "fund_l": 0.0,
    "fund_e": -0.49313268065452576,
    "capital": 132.00279,
    "rel_cap": 0.0037357746806300513
   },
   {
    "seed": "c0s13",
    "sym": "LIT",
    "t_first": 1631028300000,
    "t_end_l": 1631034360000,
    "fund_l": 0.0,
    "fund_e": -0.49313268065452576,
    "capital": 132.00279,
    "rel_cap": 0.0037357746806300513
   },
   {
    "seed": "c0s42",
    "sym": "LIT",
    "t_first": 1631028300000,
    "t_end_l": 1631034360000,
    "fund_l": 0.0,
    "fund_e": -0.49313268065452576,
    "capital": 132.00279,
    "rel_cap": 0.0037357746806300513
   },
   {
    "seed": "c0s123",
    "sym": "LIT",
    "t_first": 1631028300000,
    "t_end_l": 1631034360000,
    "fund_l": 0.0,
    "fund_e": -0.49313268065452576,
    "capital": 132.00279,
    "rel_cap": 0.0037357746806300513
   },
   {
    "seed": "r1a3_s7",
    "sym": "LIT",
    "t_first": 1631028300000,
    "t_end_l": 1631034360000,
    "fund_l": 0.0,
    "fund_e": -0.49313268065452576,
    "capital": 132.00279,
    "rel_cap": 0.0037357746806300513
   },
   {
    "seed": "c0s13",
    "sym": "LIT",
    "t_first": 1636680120000,
    "t_end_l": 1637284980000,
    "fund_l": 0.0,
    "fund_e": 1.5199613571166992,
    "capital": 632.229,
    "rel_cap": 0.002404131030238567
   },
   {
    "seed": "c0s7",
    "sym": "LIT",
    "t_first": 1638593580000,
    "t_end_l": 1639267200000,
    "fund_l": 0.0,
    "fund_e": 0.7616008520126343,
    "capital": 414.91998,
    "rel_cap": 0.0018355367027941972
   },
   {
    "seed": "c0s13",
    "sym": "LIT",
    "t_first": 1638593580000,
    "t_end_l": 1639267200000,
    "fund_l": 0.0,
    "fund_e": 0.6810758709907532,
    "capital": 371.05,
    "rel_cap": 0.001835536641937079
   },
   {
    "seed": "r1a3_s7",
    "sym": "LIT",
    "t_first": 1638593580000,
    "t_end_l": 1639267200000,
    "fund_l": 0.0,
    "fund_e": 0.6592512726783752,
    "capital": 359.15997,
    "rel_cap": 0.0018355366069285931
   },
   {
    "seed": "c0s123",
    "sym": "LIT",
    "t_first": 1638593580000,
    "t_end_l": 1639267200000,
    "fund_l": 0.0,
    "fund_e": 0.6539832949638367,
    "capital": 356.29,
    "rel_cap": 0.0018355364870297696
   },
   {
    "seed": "r1a3_a1",
    "sym": "LIT",
    "t_first": 1638593580000,
    "t_end_l": 1639267200000,
    "fund_l": 0.0,
    "fund_e": 0.663766622543335,
    "capital": 361.61996,
    "rel_cap": 0.0018355364635938099
   },
   {
    "seed": "c0s42",
    "sym": "LIT",
    "t_first": 1638593580000,
    "t_end_l": 1639267200000,
    "fund_l": 0.0,
    "fund_e": 0.663766622543335,
    "capital": 361.61996,
    "rel_cap": 0.0018355364635938099
   },
   {
    "seed": "r1a3_s7",
    "sym": "LIT",
    "t_first": 1631034360000,
    "t_end_l": 1631521680000,
    "fund_l": 0.0,
    "fund_e": 0.2707214951515198,
    "capital": 168.0987,
    "rel_cap": 0.001610491307496844
   },
   {
    "seed": "r1a3_a1",
    "sym": "LIT",
    "t_first": 1631035380000,
    "t_end_l": 1631509500000,
    "fund_l": 0.0,
    "fund_e": 0.2601403594017029,
    "capital": 170.6757,
    "rel_cap": 0.0015241792440382719
   },
   {
    "seed": "c0s123",
    "sym": "LIT",
    "t_first": 1631035380000,
    "t_end_l": 1631509500000,
    "fund_l": 0.0,
    "fund_e": 0.2601403594017029,
    "capital": 170.6757,
    "rel_cap": 0.0015241792440382719
   },
   {
    "seed": "c0s7",
    "sym": "LIT",
    "t_first": 1631035380000,
    "t_end_l": 1631509500000,
    "fund_l": 0.0,
    "fund_e": 0.2601403594017029,
    "capital": 170.6757,
    "rel_cap": 0.0015241792440382719
   },
   {
    "seed": "c0s13",
    "sym": "LIT",
    "t_first": 1631035380000,
    "t_end_l": 1631509500000,
    "fund_l": 0.0,
    "fund_e": 0.2601403594017029,
    "capital": 170.6757,
    "rel_cap": 0.0015241792440382719
   },
   {
    "seed": "c0s42",
    "sym": "LIT",
    "t_first": 1631035380000,
    "t_end_l": 1631509500000,
    "fund_l": 0.0,
    "fund_e": 0.2601403594017029,
    "capital": 170.6757,
    "rel_cap": 0.0015241792440382719
   }
  ]
 },
 "coverage": {
  "arm": 17647,
  "ratchet_ge1": 12406,
  "ratchet_ge3": 7103,
  "sl_gap_fill_open_lt_sl": 1153,
  "time_stop": 3222,
  "time_stop_168h_exact": 2368,
  "x14_deferred_any": 1014,
  "x14_deferred_then_time": 854,
  "x14_expired_504h": 317,
  "dca_2leg": 244,
  "dca_3leg": 48,
  "dca_4leg": 6,
  "dca_then_arm": 152,
  "delist": 12,
  "tick_unknown": 1279,
  "sl_below_entry": 0
 }
}
```

## 20 ca lech dau tien (chi tiet)

## PnL (cum khop)
```
{
 "ledger_funding_absdiff": {
  "0.5": 4.25537109549623e-07,
  "0.95": 3.930664064455414e-06,
  "0.99": 1.0244140639770194e-05,
  "1.0": 8.193359371944098e-05
 },
 "vision_funding_absdiff": {
  "0.5": 4.279785130734126e-07,
  "0.95": 4.077148446413048e-06,
  "0.99": 1.3281250039653969e-05,
  "1.0": 3.8578384570312494
 }
}
```

## Funding: engine (rate Vision, cong thuc sim C11) vs ledger (nguon sim: Aerospike)
```
{
 "n": 20881,
 "abs_usdt": {
  "0.5": 1.627655010771889e-09,
  "0.95": 6.954956077720453e-08,
  "0.99": 5.299072292075428e-07,
  "1.0": 3.8578314781188965
 },
 "rel_capital": {
  "0.5": 1.9710547953952367e-12,
  "0.95": 8.7626845342479e-11,
  "0.99": 5.377127963834817e-10,
  "1.0": 0.003845458139735576
 },
 "rel_abs_pnl": {
  "0.5": 2.8158161858722455e-11,
  "0.95": 1.3568184108940973e-09,
  "0.99": 8.999065995706342e-09,
  "1.0": 0.06934276090351803
 },
 "pct_rel_capital_gt_1e-6": 0.3687562856185049,
 "n_rel_capital_gt_1e-6": 77,
 "max_ret_pp": 0.3845458139735576,
 "sum_fund_l": -15123.491399515371,
 "sum_fund_e": -15094.380994005725,
 "big_ledger_zero": 77,
 "big_engine_zero": 0,
 "big_by_sym": {
  "LIT": 77
 },
 "big_by_year": {
  "2022": 34,
  "2021": 31,
  "2023": 12
 }
}
```

## Do phu nhanh engine (so cum-seed that khop di qua)
```
{
 "arm": 17647,
 "ratchet_ge1": 12406,
 "ratchet_ge3": 7103,
 "sl_gap_fill_open_lt_sl": 1153,
 "time_stop": 3222,
 "time_stop_168h_exact": 2368,
 "x14_deferred_any": 1014,
 "x14_deferred_then_time": 854,
 "x14_expired_504h": 317,
 "dca_2leg": 244,
 "dca_3leg": 48,
 "dca_4leg": 6,
 "dca_then_arm": 152,
 "delist": 12,
 "tick_unknown": 1279,
 "sl_below_entry": 0
}
```

## Cum delist (thang sau huy niem yet = khong co nen; work/delist_months.json)
```
{
 "n_cluster_seed": 197,
 "cat": {
  "ok": 197
 },
 "n_unique": 65,
 "excluded": []
}
```
