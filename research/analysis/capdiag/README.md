# capdiag — chan doan "hap thu cong suat" + "thuoc do cho exit" (2026-09-23)

Thuan Python offline (khong JVM). Pre-reg: `docs/PREREG_CAPACITY_DIAG.md` (commit `aedf535`).
Ket qua: `docs/RESULT_CAPACITY_DIAG.md`.

| file | viec |
|---|---|
| `parse_simout.py` | doc series NGAY (`b:`, `m:`, `max:`, `run:`)+ dong `[GATE] n_cand/n_pass` tu `logs/sim.out` cua 8 chan -> `/home/ubuntu/capdiag/simout_series.json` |
| `capacity.py` | VIEC A: `U = margin/equity`, so ngay binding, slot mo dong thoi, pass rate cong AI |
| `metrics.py` | VIEC C: thuoc CU (win%/TSloss%/meanP) + thuoc MOI (SumPnL/CAGR/maxDD/Calmar/Sortino/turnover/capture) -> `metrics.json` |
| `rank.py` | xep hang 2 thuoc + Kendall tau + liet ke cap dao dau |
| `ticklog_parse.py` | doc lai DOC LAP `cand.bin.gz` (32B/row) cua TICKLOG de xac nhan phan ra theo LY DO |

Chay: `python3 parse_simout.py && python3 capacity.py && python3 metrics.py && python3 rank.py`
(+ `python3 ticklog_parse.py R5_TL R6_TL` neu co `/home/ubuntu/tick/`).

Trung gian ngoai repo: `/home/ubuntu/capdiag/` (`simout_series.json`, `metrics.json`).
