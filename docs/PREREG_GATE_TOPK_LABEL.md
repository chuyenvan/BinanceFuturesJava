# PREREG_GATE_TOPK_LABEL — Huong A: gate label = ket cuc THAT cua top-K S1

> Pre-register **TRUOC khi train/chay**. Commit cung dot nay tren `module`.
> Kiem chung: sau khi chay KHONG sua thiet ke; neu NULL => ghi NULL, khong bia so.
> **KHONG push.** DEV only (khong 2026). Cau hinh CU phai tai lap byte-identical.

---

## 0. Mot cau

Train lai **gate G015** tren nhan = **ket cuc that cua chinh cac trade ma S1 chon** (top-K
coin theo S1 tai moi tick, ket cuc tinh bang `g1lite` — trailing-stop + time-stop 72h), thay
cho nhan hien tai `retEnd_4h > 0.015` tren **full pool**. Muc tieu: gate hoc "coin nay, khi
duoc giao dich that (top-K S1), co thang khong?" thay vi "coin nay tang 1.5% trong 4h?".

Dong co (commit `2e3bef8`, `d39f015`): gate target **lech** selector. Gate G015 nhan 4h full
pool; selector S1 toi uu top-K theo `g1lite` 72h. Trong `map_s1a2` thu tu gate bi bo — gate chi
con kenh **LOC/HIEU CHUAN** (multiset `p` trong tick). => Train gate tren ket cuc that cua tap
trade thuc se **dong bo hieu chuan** gate voi thu selector dang giao dich.

**Gioi han can noi ro ngay tu dau**: huong nay doi **hieu chuan/do chat** cua gate, KHONG doi
thu tu chon coin (thu tu do S1 quyet dinh). Khac huong B (doi horizon) da chet vi B la "do chat"
thuan tuy ma khong dong bo target; huong A dong bo **target + population** ve dung tap trade.

---

## 1. Dinh nghia label CHINH XAC

### 1.1 Population (tap duoc train + predict)

Tai moi **tick 15m** `t` trong khung WFO (muc 4), lay **top-K coin theo score S1**:

```
S1 score = cot "score" cua pred_s1a2x1*.parquet  (score THAP = tot; score = -pred ranker)
top-K     = K coin co score thap nhat trong tick t  (rank(method="first", ascending) <= K)
K = 8     # khop SELECTOR_RANK_TOPK=8 trong profiles/x1_gs_t170.properties
```

Nguon score S1 (OOS, leak-free, da chot o cac vong S1 truoc):
- `pred_s1a2x1.parquet`     : 2022-01..2025-12 (16-fold X1, 17349 tick, 620 sym)
- `pred_s1a2x1_y21.parquet` : 2021-07..2021-12 (934 tick, 129 sym) — mo rong DEV 2021

=> S1 score phu **lien tuc** 2021-07 -> 2025-12 (khong overlap, 128 sym chung). Top-K tinh
RIENG trong tung tick (moc soi voi so coin co score trong tick do).

### 1.2 Ket cuc that (outcome)

Cho moi (tick, coin) trong top-K, ket cuc = `g1lite` doc tu `cand_dev_x1.parquet` (join theo
`ts,sym`):

```
g1lite = maxFav_72h - min(0.5 * maxFav_72h, 0.08)   neu maxFav_72h >= 0.05
       = retEnd_72h                                   neu maxFav_72h <  0.05
```

`g1lite` la **trailing-stop + time-stop xap xi** (arm 5%, giveback 0.5 cap 8%, horizon/time-stop
72h) — chinh la metric ma S1 toi uu (`research/pipeline/ledger.py:40`). Day la "ket cuc that" theo
dung nghia pipeline hien hanh.

> **Khai ro gioi han xap xi**: sim thuc te (`x1_gs_t170.properties`) exit voi
> `SIM_RATE_PROFIT_STOP_MARKET=0.07` (arm 7%) + `SIM_LOSER_TIME_STOP_HOURS=168` (time-stop 168h),
> `TS_GIVEBACK_RATIO=0.5`. `g1lite` dung arm 5% + 72h => la **xap xi**, khong phai bit-exact voi
> sim. Chon `g1lite` vi: (a) la metric S1 da toi uu (dong bo target), (b) co san cho toan pool,
> (c) la "tan cung" ma toan bo pipeline selector dang dung. Neu can chinh xac hon sau nay => dung
> `path_labels.g1_replay` (mo phong exit tren closes gio, nhung chi co o tap lay mau).

### 1.3 Label binary

```
y = (g1lite > 0)   # 1 = thang (net outcome duong), 0 = thua
```

Base rate do truoc (probe doc lai artifact, chua train): top-K win rate **≈ 0.80** (2022-2024:
0.794 / 0.825 / 0.820). Dung cho `scale_pos_weight`.

---

## 2. Features — GIU NGUYEN 45 cot (KHONG doi)

Giong het `g015_net_train.py` (`NF=45`): 40 cot Tool1 (15m candle features per-coin) + 5 OI
(`oi_delta24h, oi_z, ls_global, ls_toptrader, taker_buy`). **Khong** them/bot feature, khong
feature-group. Chi doi **label + population**.

Nguon feature (env giong trainer goc):
- `T1_DIR=/home/ubuntu/ds_feat15m` (Tool1, 15m grid)
- `OI_FILE=/home/ubuntu/claudedata/oi/oi_percoin_full.bin`, `MAP_CSV=.../symbol_map.csv`
- `SEL1M_CODE=/home/ubuntu/sel1m_code` (`tool1_col`, `funding_label_pb`)

Vi population chi la ~55k dong (top-K 2021-2024, muc 4), feature build **chi trich cho nhung
(ts,sym) top-K** (light), KHONG build full pool (~84M dong) — tranh OOM. Duong full-pool (build_matrix
memmap) de nguyen cho tai lap parity, khong dung o day.

---

## 3. Model & hyperparam (GIU NGUYEN g015_net_train.py)

```
XGBClassifier(n_estimators=400, max_depth=5, learning_rate=0.05,
              subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
              scale_pos_weight=(1-pos)/pos, eval_metric="auc",
              tree_method="hist", random_state=42)
```

`pos` = base rate cua top-K fold do (≈ 0.80). Device cpu (khong GPU; Oracle CPU). `n_jobs=-1`.

---

## 4. WFO / fold

Cung khung nhu sim (2022-01..2024-12, 10 cut) — khop `x1_gs_t170` va `predwf_map_s1a2_x1`:

```
CUTS = 20220101 20220401 20220701 20221001 20230101 20230401 20230701 20231001 20240101 20240401
OOS  = 3 thang sau moi cut; PURGE = 72h; TZ = +7h
train fold i = top-K rows co ts < cut_i - 72h
OOS   fold i = top-K rows co cut_i <= ts < cut_i + 3thang
Bo fold neu len(train) < 5000 hoac OOS rong.
```

- Train fold 0 (cut 20220101) dung S1 y21 (2021-07..2021-12) — khoang ~7500 dong top-K.
- Top-K population 2021-2024 tong **≈ 53k dong** (probe: 2022=23408, 2023=4080, 2024=18064 + y21).
- **Purge nested S1 vs gate**: S1 score da la OOS leak-free cua tung S1 fold (3 thang, purge 72h).
  Gate chi doc score S1 => khong leak nguoc vao S1 train. Kiem `assert ts max train < cut - purge`.

---

## 5. Cach danh gia (OFFLINE truoc, sim sau neu pass)

### 5.1 Offline (chay duoc ngay, khong can JVM)

Tren population top-K OOS (2022-2024), so **AUC + rank-IC** cua `p_gate` voi `y=(g1lite>0)`:

- **Baseline (gate CU, net015)**: probe da do = **AUC 0.573 / rank-IC 0.100** (n=45560,
  per-year 0.553/0.551/0.591; within-tick rank-IC 0.077). Day la moc "gate cu da lech target".
- **Gate A (train top-K label)**: OOS AUC theo tung fold (WFO, khong leak). Neu
  **AUC_A > AUC_cu** (cung population top-K OOS) => gate A dong bo target hon.

**Nguong ra quyet dinh tiep (sim)**: gate A phai **AUC OOS > 0.573 + margin** va rank-IC > 0.10
(tren cung top-K OOS, WFO sach). Neu khong => NULL, giu gate cu.

### 5.2 Sim (BLOCKED trong dot nay — xem muc 8)

Neu pass 5.1: build bins `predwf_G015_topk` (10 file) -> `c4_build_map` vs S1 -> `ExportWfoDataset`
(funding.bin) -> sim, doi chieu T170 (`printDone.csv` md5 `efb793e2468ca3a7318da0f0ad23d4fc`),
cham 5 rate + CI (bootstrap block-72h, `inflate(k)` theo `x1_rates.py --k`, 2000 rep, seed
20260905) + chan cung `RISK_APPETITE` (maxDD<=30, UW<=200, khong nam am, quy>=-15, 1 coin<=15%).

---

## 6. Toi da bien the

k=2. Neu AUC_A pass: bien the thu 2 co the la **K khac** (vd K=5, khop edge5 cua ledger) hoac
**nguong y** (g1lite > 0.03 thay > 0). Chi 1 bien the sau khi da chay xong bien the chinh; pre-reg
bo sung truoc khi chay bien the 2.

---

## 7. Parity (tai lap byte-identical)

Cau hinh CU (`x1_gs_t170`) phai tai lap `printDone.csv` md5 `efb793e2468ca3a7318da0f0ad23d4fc`
(1089 lenh). **Khong** dung thanh cong cua vong nay — day la luat canh gac doc lap cho bat ky
thay doi nao cham sim.

---

## 8. 🔴 Blocker da biet TRUOC khi chay (khong tu xu ly)

1. **JVM slot Oracle bi chiem** boi `BinanceOrderTradingManager` (pid 1198675, start 2026-09-20
   00:12) — `AGENT_RUNBOOK` bay #4: 1 slot JVM, `pgrep java` phai rong. **KHONG duoc dung/kill**
   tien trinh song. => khong chay duoc `ExportWfoDataset` (build funding.bin) lan sim tren Oracle.
2. **Kaggle khong chay duoc bien the bins** (`docs/KAGGLE_SIM.md` muc 6): sim Kaggle doc dataset
   DA BUILD; doi bins can build `funding.bin` (JVM) + upload dataset rieng — van can JVM o buoc
   build. => bien the A (doi bins) khong di duoc duong Kaggle.

=> **Dot nay chi lam duoc muc 5.1 (offline)**. Sim/parity **DUNG + bao RO**, khong bia so.

---

## 9. Khong lam

Khong push. Khong cham 2026/`HOLDOUT_UNSEAL`. Khong sua `g015_net_train.py` (artifact ghim sha).
Khong dung/kill tien trinh song. Khong train tren 2025/2026 (DEV only).
