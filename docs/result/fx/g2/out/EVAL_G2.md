# EVAL_G2 (TRAIN 1975-01-01..2005-12-31 [in-sample]; WFO 2006-01-01..2019-12-31)

Excess return vs USD cash at 0; swap from OECD rates m-1 net of 1 %/yr margin. Sharpe on daily returns.

| config | TRAIN Sharpe [in-sample] | TRAIN 75-89 Sharpe [in-sample] | TRAIN 90-05 Sharpe [in-sample] | WFO Sharpe | WFO CAGR | WFO maxDD | H1 Sharpe | H2 Sharpe | 06-08 | 09-12 | 13-19 | WFO turnover/yr | WFO % filtered |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L1-F0 | 0.296 [in-sample] | 0.351 [in-sample] | 0.245 [in-sample] | -0.177 | -1.32% | 27.45% | -0.074 | -0.341 | 0.460 | -0.460 | -0.341 | 13.177 | 0.00% |
| L1-V10 | 0.321 [in-sample] | 0.374 [in-sample] | 0.275 [in-sample] | -0.164 | -1.29% | 27.68% | -0.079 | -0.304 | 0.496 | -0.478 | -0.304 | 13.764 | 10.81% |
| L1-V20 | 0.313 [in-sample] | 0.381 [in-sample] | 0.251 [in-sample] | -0.146 | -1.13% | 25.45% | -0.042 | -0.312 | 0.458 | -0.401 | -0.312 | 13.237 | 0.53% |
| L3-F0 | 0.307 [in-sample] | 0.512 [in-sample] | 0.128 [in-sample] | -0.028 | -0.42% | 26.35% | 0.215 | -0.428 | 0.698 | -0.148 | -0.428 | 7.061 | 0.00% |
| L3-V10 | 0.368 [in-sample] | 0.564 [in-sample] | 0.198 [in-sample] | 0.040 | 0.04% | 26.71% | 0.303 | -0.368 | 0.824 | -0.091 | -0.368 | 7.869 | 13.78% |
| L3-V20 | 0.326 [in-sample] | 0.521 [in-sample] | 0.154 [in-sample] | 0.001 | -0.22% | 25.32% | 0.260 | -0.418 | 0.699 | -0.073 | -0.418 | 7.203 | 0.87% |
| L12-F0 | 0.491 [in-sample] | 0.563 [in-sample] | 0.429 [in-sample] | -0.341 | -2.51% | 37.71% | -0.455 | -0.178 | 0.215 | -0.968 | -0.178 | 4.195 | 0.00% |
| L12-V10 | 0.556 [in-sample] | 0.758 [in-sample] | 0.384 [in-sample] | -0.391 | -3.03% | 43.42% | -0.568 | -0.129 | 0.229 | -1.155 | -0.129 | 5.306 | 18.03% |
| L12-V20 | 0.530 [in-sample] | 0.631 [in-sample] | 0.443 [in-sample] | -0.306 | -2.36% | 37.21% | -0.417 | -0.144 | 0.218 | -0.876 | -0.144 | 4.422 | 1.26% |
| C-F0 | 0.445 [in-sample] | 0.555 [in-sample] | 0.351 [in-sample] | -0.010 | -0.29% | 24.21% | 0.050 | -0.111 | 0.696 | -0.452 | -0.111 | 8.476 | 0.00% |
| C-V10 | 0.523 [in-sample] | 0.660 [in-sample] | 0.408 [in-sample] | 0.025 | -0.07% | 24.04% | 0.068 | -0.043 | 0.793 | -0.491 | -0.043 | 9.502 | 14.46% |
| C-V20 | 0.470 [in-sample] | 0.585 [in-sample] | 0.371 [in-sample] | 0.026 | -0.05% | 21.66% | 0.096 | -0.087 | 0.697 | -0.366 | -0.087 | 8.619 | 0.87% |

Selected (max TRAIN Sharpe [in-sample]): **L12-V10**
Median of 12 configs on WFO: {"sharpe": -0.08693590905634291, "cagr": -0.007728085576535759, "maxdd": 0.26534394479559137, "calmar": -0.030084034280016644}
Main control (circular block shift, per ccy, k in [12, n-12]): {"n": 1000, "seed": 20261127, "n_ge": 483, "p": 0.4835164835164835, "real_sharpe_wfo_only": -0.3816226846386458, "real_sharpe_fullrun": -0.3914839140852568, "median": -0.3947706704088304, "p95": 0.04642284426256222}
Secondary (mo ta) iid random signs: {"label": "mo ta", "n": 1000, "n_ge": 568, "p": 0.5684315684315684, "median": -0.32671566205328145}
Secondary (mo ta) buy-hold equal weight: TRAIN [in-sample] Sharpe 0.048 / WFO Sharpe -0.073
Secondary (mo ta) F0 same L L12-F0 WFO Sharpe -0.341
Drop best 5% months (WFO): {"n_dropped": 9, "n_months": 168, "total_ret_rest": -0.5483799208948532}
Cost x2 (WFO): Sharpe -0.543 CAGR -4.08%
Value filter improves Sharpe vs F0 in both WFO halves (mo ta, ngoai tieu chi): {"L1-V10": false, "L1-V20": true, "L3-V10": true, "L3-V20": true, "L12-V10": false, "L12-V20": true, "C-V10": true, "C-V20": true}

| criterion | pass |
|---|---|
| D1 | False |
| D2 | False |
| D3 | False |
| D4 | False |
| D5 | False |
| D6 | False |

**Ket luan: KHONG DAT**
