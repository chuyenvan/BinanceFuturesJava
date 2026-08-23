# Trailing gap: selector per-coin pred vs gate market pred — 2026-08-19

## Câu hỏi (user)
Trailing weak/strong-gap hiện dùng **market gate predReturn15M** (1 giá trị cho cả mớ coin) để quyết gap 3%/8%.
User: nên dùng **selector pred per-coin** thì hợp lý hơn. Test bằng agent (data test, không rebuild).

## Setup
119,260 entry gate-fired (2022-01→2025-12, OOS), join: (a) market gate predReturn15M tại entry ts,
(b) selector per-coin pred tại (ts, symbol) từ predwf_G015x26e. So khả năng dự báo CONTINUATION per-coin.
⚠️ predwf_G015x26e chỉ populate horizon 4h (idx0); 12h/24h/72h = NaN. Nên selector test = P(coin maxFav≥6% trong 4h).

## KẾT QUẢ — selector per-coin THẮNG áp đảo
AUC (dự báo continuation per-coin, N=119,260):
| pred | ret24h>0 | ret72h>0 | maxFav24≥6% | maxFav72≥6% |
|---|---|---|---|---|
| GATE market pred15M | 0.500 | 0.521 | 0.510 | **0.441 (anti)** |
| SEL per-coin 4h | **0.573** | **0.601** | **0.562** | **0.672** |

Spearman (continuous):
| pred | retEnd_24h | retEnd_72h | maxFav_72h | maxAdv_72h |
|---|---|---|---|---|
| GATE | 0.025 | 0.078 | −0.027 | 0.031 |
| SEL | **0.149** | **0.199** | **0.229** | **0.116** |

Decile (điểm mấu chốt): SEL decile ĐƠN ĐIỆU sạch — bottom→top P(retEnd72>0) 0.563→0.846, maxFav_72h 0.204→0.447
(2.2×), maxAdv_72h −0.132→−0.089 (coin SEL cao drawdown ÍT hơn ~33%). GATE decile PHẲNG/non-monotone —
retEnd72 ~0.09-0.11 mọi decile, **maxAdv_72h phẳng ~−0.12 mọi decile = ZERO phân biệt downside**.

**Phát hiện thêm: corr rank GATE vs SEL = −0.43 (ÂM).** Hai pred bất đồng có hệ thống → market-pred hiện tại không
chỉ yếu hơn mà còn có thể **đẩy gap SAI chiều** per-coin (nới gap cho coin thực ra dễ đảo).

## VERDICT
Market gate pred **gần như không có skill per-coin** (AUC≈0.50, 1 horizon 0.44 anti-predictive, maxAdv phẳng).
Áp nó cho gap từng coin = hằng số coin-blind. Selector per-coin **rank được cả upside (nới gap) lẫn downside (siết gap)**
— đúng cái switch weak/strong đang cố quyết. **Wiring selector per-coin pred vào trailing gap + ratchet là ĐÚNG.**

## CAVEAT
1. Chỉ có horizon 4h của selector trong build này; 24h/72h selector (khớp exit-path 72h hơn) chưa test — có thể còn tốt hơn.
2. Đây là test SIGNAL-POWER, KHÔNG phải P&L sim A/B. Chứng minh input tốt hơn, chưa lượng hóa lãi net. Bước xác nhận:
   sim A/B trên 2025Q4_crash (feed coin pred vào trailing) — CHƯA làm (né conflict RAM với sweeps đang chạy).
3. Calibration: SEL emit XÁC SUẤT (mean 0.83), switch live threshold một RETURN pred ở 0.004 → khi wiring phải
   re-calibrate ngưỡng theo percentile SEL, KHÔNG dùng literal 0.004.
4. Join tol: gate ±2min, selector ±16min backward; entry = g008 pathstats (gate-fired), gần nhưng không byte-identical với live traded.

## Bước tiếp đề xuất
- (xác nhận) Sim A/B: thêm flag feed coin-pred vào calRateLossDynamicBuy/calRateMin, chạy 2025Q4_crash + 1 bull, so net PnL/DD.
- (nếu OK) Wiring live: TS weak/strong + ratchet dùng SEL per-coin percentile thay market predReturn15M; re-calibrate ngưỡng.
- Scripts agent: /tmp/f3.py trên Oracle; inputs entry_pathstats_g008.csv, wfo_gate_pred.csv, predwf_G015x26e/*.bin.
