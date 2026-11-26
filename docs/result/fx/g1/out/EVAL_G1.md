# EVAL_G1 (TRAIN 1994-01-01..2005-12-31 [in-sample]; WFO 2006-01-01..2019-12-31)

Excess return vs USD cash at 0 (strategy already nets the rate differential). Sharpe on daily returns.

| config | TRAIN Sharpe [in-sample] | TRAIN CAGR [in-sample] | TRAIN maxDD [in-sample] | WFO Sharpe | WFO CAGR | WFO maxDD | WFO Calmar | H1 Calmar | H2 Calmar | WFO skew_m | WFO worst_m | WFO %pos_yr | WFO turnover/yr | WFO %gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| k2_OFF | 0.758 [in-sample] | 2.73% [in-sample] | 6.40% [in-sample] | -0.021 | -0.33% | 22.72% | -0.014 | -0.001 | -0.053 | -0.777 | -8.24% | 57.14% | 1.200 | 0.00% |
| k2_FXVOL_q80_N3 | 0.963 [in-sample] | 2.74% [in-sample] | 7.84% [in-sample] | 0.003 | -0.07% | 13.46% | -0.005 | 0.010 | -0.039 | -0.640 | -5.93% | 50.00% | 3.351 | 23.74% |
| k2_FXVOL_q90_N3 | 0.875 [in-sample] | 2.77% [in-sample] | 6.26% [in-sample] | 0.122 | 0.46% | 15.19% | 0.030 | 0.078 | -0.034 | -0.179 | -5.93% | 57.14% | 2.929 | 14.79% |
| k2_FXVOL_q80_N10 | 0.804 [in-sample] | 2.28% [in-sample] | 5.95% [in-sample] | -0.077 | -0.39% | 16.17% | -0.024 | -0.035 | -0.035 | -0.657 | -5.93% | 50.00% | 3.706 | 27.88% |
| k2_FXVOL_q90_N10 | 0.761 [in-sample] | 2.42% [in-sample] | 6.21% [in-sample] | -0.153 | -0.82% | 23.28% | -0.035 | -0.027 | -0.083 | -0.691 | -5.80% | 50.00% | 2.668 | 14.05% |
| k2_VIX_q90_N3 | 0.820 [in-sample] | 2.40% [in-sample] | 6.22% [in-sample] | -0.085 | -0.43% | 17.31% | -0.025 | 0.100 | -0.120 | -0.141 | -4.43% | 35.71% | 4.996 | 23.88% |
| k3_OFF | 0.629 [in-sample] | 1.96% [in-sample] | 7.53% [in-sample] | -0.013 | -0.17% | 18.56% | -0.009 | 0.008 | -0.050 | -0.586 | -5.36% | 57.14% | 0.556 | 0.00% |
| k3_FXVOL_q80_N3 | 0.793 [in-sample] | 1.96% [in-sample] | 8.64% [in-sample] | 0.076 | 0.19% | 8.33% | 0.023 | 0.067 | -0.030 | -0.538 | -3.72% | 57.14% | 3.023 | 23.74% |
| k3_FXVOL_q90_N3 | 0.758 [in-sample] | 2.10% [in-sample] | 5.43% [in-sample] | 0.151 | 0.48% | 10.44% | 0.046 | 0.134 | -0.055 | -0.091 | -3.72% | 50.00% | 2.521 | 14.79% |
| k3_FXVOL_q80_N10 | 0.717 [in-sample] | 1.81% [in-sample] | 6.74% [in-sample] | -0.069 | -0.26% | 10.76% | -0.024 | -0.003 | -0.060 | -0.541 | -3.72% | 42.86% | 3.404 | 27.88% |
| k3_FXVOL_q90_N10 | 0.636 [in-sample] | 1.78% [in-sample] | 7.20% [in-sample] | -0.076 | -0.33% | 13.60% | -0.024 | 0.020 | -0.078 | -0.592 | -3.84% | 50.00% | 2.338 | 14.05% |
| k3_VIX_q90_N3 | 0.561 [in-sample] | 1.41% [in-sample] | 7.24% [in-sample] | -0.071 | -0.28% | 14.22% | -0.020 | 0.139 | -0.109 | -0.511 | -3.80% | 42.86% | 4.628 | 23.88% |

Selected (max TRAIN Sharpe [in-sample]): **k2_FXVOL_q80_N3**
Median of 12 configs on WFO: {"sharpe": -0.04470904301014145, "cagr": -0.002700121926633714, "maxdd": 0.14702844858838615, "calmar": -0.016992830118128317}
Control buy-hold (TRAIN [in-sample] / WFO): 0.122 / -0.073
Control no-gate k2_OFF WFO Sharpe: -0.021
Control random: {"n": 500, "seed": 20261126, "n_ge": 37, "p": 0.07584830339321358, "real_sharpe": 0.0033131192976197823, "rand_median": -0.32923237300544367, "rand_p95": 0.07039173119726384}
Drop best 5% months (WFO): {"n_dropped": 9, "n_months": 168, "total_ret_rest": -0.20083260685510196}
Cost x2 (WFO): Sharpe -0.201 CAGR -0.92%
D5: selected gated config k2_FXVOL_q80_N3 vs k2_OFF

| criterion | pass |
|---|---|
| D1 | False |
| D2 | False |
| D3 | True |
| D4 | False |
| D5 | True |
| D6 | False |
| D7 | False |

**Ket luan: KHONG DAT**

ERRATA3 K5 (mo ta, ngoai tieu chi): k2_FXVOL_q80_N3 with carry at holding-month rates: TRAIN [in-sample] Sharpe 0.953; WFO Sharpe 0.002 CAGR -0.08% maxDD 13.46%

ERRATA1 H1 (descriptive only): WFO excluding 97 FRED/ECB-flagged days: Sharpe 0.119 CAGR 0.39% maxDD 10.45%
