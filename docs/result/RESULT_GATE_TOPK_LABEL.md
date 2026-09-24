# RESULT_GATE_TOPK_LABEL — Huong A: gate label = ket cuc that top-K S1

Pre-reg: `docs/prereg/PREREG_GATE_TOPK_LABEL.md` (commit `70e8d8f`, `module`).
Baseline: gate CU G015 (`net015`, `retEnd_4h>0.015` full pool) — bins `/home/ubuntu/claudedata/predwf_G015x26`.
**Vong nay CHI lam duoc OFFLINE (probe AUC). Sim + parity BLOCKED (muc 4). Khong push.**

---

## 0. Ket luan mot cau

**NULL o tang sim; OFFLINE cho cai tien NHE + KHONG DONG NHAT.** Gate A (train tren ket cuc that
cua top-K S1, `y=(g1lite>0)`) co AUC OOS **0.590 vs 0.563** cua gate cu tren CUNG population
top-K — tot hon **7/10 fold, +0.027 tong**, nhung **2024 kem hon** (−0.012). Muc cai tien qua nho
va khong nhat quan de ket luan "tot hon"; khong the chay sim (muc 4) de cham 5 rate + CI + chan
cung. => **NULL (can't conclude)**.

---

## 1. OFFLINE — bang AUC OOS tren population top-K (WFO 10 cut, purge 72h, khong leak)

Train: chi tren top-K S1 (K=8) moi tick; nhan `y = (g1lite>0)` (base rate ~0.80). 45 feature
GIU NGUYEN. XGBClassifier giu hyperparam g015_net_train. Gate cu = `p0` cua net015 join vao
CUNG tap top-K OOS (do chua apple-to-apple).

| fold | cut | n_train | n_oos | base_y | AUC_new | AUC_old |
|---|---:|---:|---:|---:|---:|
| 0 | 20220101 | 7400 | 7616 | 0.773 | **0.613** | 0.504 |
| 1 | 20220401 | 14944 | 10320 | 0.816 | **0.629** | 0.553 |
| 2 | 20220701 | 25344 | 1928 | 0.758 | 0.521 | 0.552 |
| 3 | 20221001 | 27328 | 3560 | 0.792 | **0.678** | 0.671 |
| 4 | 20230101 | 30896 | 1976 | 0.849 | **0.556** | 0.537 |
| 5 | 20230401 | 32864 | 608 | 0.739 | **0.610** | 0.504 |
| 6 | 20230701 | 33440 | 352 | 0.804 | 0.618 | 0.623 |
| 7 | 20231001 | 33832 | 1120 | 0.830 | **0.679** | 0.638 |
| 8 | 20240101 | 34912 | 6512 | 0.836 | 0.565 | 0.568 |
| 9 | 20240401 | 41456 | 2768 | 0.785 | 0.551 | 0.562 |
| **TONG** | | | **36760** | 0.804 | **0.590** | **0.563** |

Theo nam (AUC): 2022 **0.628** vs 0.553 (+0.075); 2023 **0.596** vs 0.551 (+0.045);
2024 0.552 vs **0.564** (−0.012).

Doc: ket cuc top-K 2022-2023 duoc gate A phan biet tot hon ro ret; 2024 gate A **kem hon**.
Base rate cao (0.80) + AUC ~0.59 => ca hai gate chi phan biet "thang/thua" YEU tren tap top-K
(dau vao top-K da gan nhu dong nhat "coin tot" do S1 loc). Cai tien chua du manh de qua nguong
pre-reg (muc 5.1: can "> 0.573 + margin" DONG NHAT, khong chi 2/3 nam).

Artifact: `/home/ubuntu/gate_topk/{predict_wf_*.bin x10, summary.json}`. Script:
`research/pipeline/g5/gate_topk_train.py` (self-contained, 2.0 phut, exit 0).

---

## 2. Gioi han cua phep do offline (khai ro, khong suy dien)

1. **Circular nhung sach**: gate A train tren `g1lite>0` va cham tren `g1lite>0` (OOS, WFO
   purge 72h, khong leak). No PHAI tot hon gate cu (train target khac) tren target cua chinh no.
   Cai dang noi la MUC cai tien: chi +0.027, khong phai +0.15.
2. **`g1lite` la xap xi** cua exit that (arm 5% vs `SIM_RATE_PROFIT_STOP_MARKET=0.07`, 72h vs
   `SIM_LOSER_TIME_STOP_HOURS=168`). Khong phai bit-exact voi sim.
3. **OOD o tang inference**: gate A chi train tren top-K (44k dong). Khi du vao sim, `map_s1a2`
   can `p` cho TOAN bo pool (gate cu train full pool). Gate A se OOD cho coin ngoai top-K —
   chua do duoc vi sim block. Day la rui ro thiet ke da ghi o pre-reg muc 1.1/8.

---

## 3. ⚠️ Cai chua do duoc (sim) — la TIEU CHI QUYET DINH that su

5 rate + CI (bootstrap block-72h `inflate(k)`, 2000 rep, seed 20260905), chan cung
`RISK_APPETITE` (maxDD<=30, UW<=200, khong nam am, quy>=-15, 1 coin<=15%), so lenh. **Khong co
so nao** trong vong nay vi khong chay duoc sim.

---

## 4. 🔴 Blocker (khong tu xu ly)

1. **JVM slot Oracle bi chiem** boi `BinanceOrderTradingManager` (pid 1198675, start 2026-09-20
   00:12). `AGENT_RUNBOOK` bay #4: 1 slot JVM, `pgrep java` phai rong. **KHONG duoc dung/kill**
   tien trinh song => khong chay `ExportWfoDataset` (build funding.bin) lan sim tren Oracle.
2. **Kaggle khong chay bien the bins** (`docs/runbooks/KAGGLE_SIM.md` muc 6): sim Kaggle doc dataset DA
   BUILD; doi bins can build `funding.bin` (JVM) + upload dataset rieng — van can JVM o buoc
   build. => huong A (doi bins) khong di duoc duong Kaggle.

=> Parity (tai lap byte-identical `efb793e2…`) va sim deu KHONG chay duoc trong dot nay.

---

## 5. Chi phi / thoi gian

- Claude Code opus: viet + chay script ~6 phut wall (train 10 fold XGB tren 44k dong ~2 phut CPU).
- Kaggle: **0** (khong push kernel nao — sim block truoc khi can Kaggle).
- Oracle CPU: train 10 fold ~2 phut, build feature 4 nam Tool1 + OI ~1 phut.

## 6. Khong lam

Khong push, khong cham 2026/`HOLDOUT_UNSEAL`, khong sua `g015_net_train.py` (artifact ghim sha),
khong dung/kill tien trinh song, khong train 2025/2026.
