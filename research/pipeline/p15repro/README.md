# p15 / `pred.bin` tai lap — scripts bang chung (2026-09-28)

Doc lap: `docs/result/RESULT_PREDBIN_REPRO.md`, pre-reg `docs/prereg/PREREG_PREDBIN_REPRO.md`.
Run bang venv: `/home/ubuntu/envs/xgb-env/bin/python <script>` (can `onnxruntime`, `xgboost`, `scipy`, `pandas`).

| script | viec | ket qua chot |
|---|---|---|
| `s1_identify.py` | doc `pred.bin` (big-endian) + join voi cac CSV ung vien | `pred.bin` ≡ `claudedata/wfo_gate_pred.csv` (corr 1,00000) |
| `s2_repro.py` | predict 21 fold `wfo_models` + `gate_ab_full/models/label_oldbasket` tren `fs_full.csv` / `gate15m_v2_full.csv` | corr 0,487 / 0,483 — THAT BAI |
| `s3_gatedataset.py` | nhu tren voi store `gate_dataset_full.csv.gz` | corr per fold 0,04–0,75 (mean 0,43) |
| `s4_pin.py` | grid `pred.bin`, so voi `label_oldbasket.csv`, so 2 bo model | 0 trung lap; 2 bo model cho ket qua **giong het** |
| `s5_scan.py` | quet nhieu model dir tren cua so fold 18 | tat ca ~0,68; `label_ret15m` 0,35 |
| `s6_fresh.py` | RETRAIN fold 18 (store hien tai, hyperparam tai lieu) vs `pred.bin` | **pearson 0,99347 / spearman 0,995254**, p50 0,009000 vs 0,009004 |
| `s7_fresh_all.py` / `s7b.py` / `s7c.py` | retrain toan bo 19 fold DEV | **19/19 pearson 0,9918–0,99786** (chia 3 dot chay) |
| `s8_foldscan.py` | quet 21 model dong bang tren cua so 2025Q4 | max = **fold_20 = 0,76214** = con so 0,762 cua `RESULT_P15_SOURCE` §3.4 |
| `s9_gen.py` | doi chieu `.bak_20260711_2333` + cap `gatemodels_v4v5`/`wfo_gate_pred_v4v5_*` | `.bak` cho **cung** so ⇒ cung the he; cap v4v5 cung 0,25–0,55 |
| `s10_storediff.py` | so 33 feature giua 4 store + corr model tren tung store | **max\|dF\| = 0.000e+00** tren ca 4 store |

Ket luan: store **khong** mat; **retrain** tai lap `pred.bin` (19/19 fold ≥0,99); bo `.onnx` dong bang tren dia
**khong phai** the he san xuat (khong biet thuoc the he nao — thieu log/sha).
