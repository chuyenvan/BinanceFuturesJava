# RESULT_EXIT_FIT — Replay harness offline + fit cong thuc gap thoat (T170, DEV)

Chot truoc: `docs/PREREG_EXIT_FIT.md` (commit `cb9078f`). Vong nay **thuan Python, khong chay Java/sim**
(khong dung slot Oracle). DEV 2021-07..2025-12. **Khong push.**

## 0. KET LUAN (doc truoc)

1. **Harness parity: PASS** — replay thuan Python tai hien **dung** duong thoat T170 (`printDone.csv`
   md5 `efb793e2468ca3a7318da0f0ad23d4fc`, n=1089 leg): **status 100%**, **thoi diem thoat 100% trung phut**,
   **gia chot 99.82% (nguong 95%)**, **PnL khong-funding: lech trung vi 0.0000 USDT, max |Δ| = 0.027 USDT**.
   => harness **dung de do**, moi ket luan duoi day dung tren no.
2. **Fit: NULL** theo dung tieu chi da chot (policy chon tren TRAIN phai co CI block-ngay tren TEST
   **khong chua 0**). Policy duoc chon tren TRAIN (F3 — dinh do bang **CLOSE**) **tot hon ca hai tap**
   (TRAIN +6.5%, TEST **+20.6%** net/trade) nhung **CI rong, chua 0** ⇒ **chua du ket luan**, khong duoc
   coi la "hon" va **khong** de xuat tich hop.
3. **17 policy da thu** (1+9+6+1); **1/16** policy co CI khong chua 0 tren TEST va policy do **TE HON**
   (F1_0.02_0.15: −9.4/trade) ⇒ khong co bang chung nao ung ho "fit so ra cong thuc tot hon".
4. Huong di tiep: **co** — nhung chi con **1 cua hep** (F3 = bo HIGH, dung CLOSE cho ca arm va dinh);
   moi thu khac (doi so, doi tran, doi hinh dang ham, dua ATR vao) deu **NULL/te hon**. Xem §4.

## 1. BUOC 1 — Replay harness + cong parity

### 1.1 Cong cu (repo, dung lai duoc)

| file | viec |
|---|---|
| `research/exitfit/exit_engine.py` | **engine** replay (state machine thoat) + tick/normalize + policy interface |
| `research/exitfit/build_cache.py` | doc `ticker_YYYYMMDD.bin.gz` (jbin, thuan Python) → cache nen ngoai repo |
| `research/exitfit/parity.py` | cong parity vs `printDone.csv` (P0) → `parity_detail.csv` |
| `research/exitfit/fit.py` | 17 policy × TRAIN/TEST + bootstrap block-ngay |

**Cach dung** (khong can JVM, khong can Aerospike):

```
cd research/exitfit
python3 build_cache.py     # 1 lan: ~5 phut/4 core, doc 617 ngay ticker -> /home/ubuntu/exitfit/cache
python3 parity.py          # 10 giay, in PASS/FAIL theo nguong da chot
python3 fit.py             # ~2 phut, ghi fit_results.pkl + fit_table.csv + fit_summary.txt
```

Trung gian **ngoai repo** tai `/home/ubuntu/exitfit/` (resume duoc: `build_cache.py` bo qua part da co;
`fit.py` luu tung policy). Sua 1 cho duy nhat neu doi profile: cac hang so o dau `exit_engine.py`.

### 1.2 Pham vi tai hien (doc code TRUOC khi viet)

`SimulatorMarketLevelTicker1MStopLoss.startUpdateOldOrderTrading` :930-1030 · `OrderTargetInfoTest`
`updateStatusNew` :178-215 / `updateTPSL` :245-266 / `trailRate` :367-383 · `TradeUtils.trailFromCap` :45-52 ·
`ClientSingleton.normalizePrice` :217-237 · profile `profiles/x1_gs_t170.properties`
(arm 0.07, `SIM_TS_GIVEBACK=1`, `SIM_LOSER_TIME_STOP_HOURS=168`, `TS_GIVEBACK_RATIO=0.5`,
`SIM_APPLY_FUNDING/SIM_FUNDING_MARK=true`, `TS_MAX_GAP 0.08 / TS_MAX_GAP_WEAK 0.03`, `TS_CAP_STRONG_RANK=0`).

Da tai hien: arm theo `high` nen 1m · `gap = min(peak×0.5, cap)` + lam tron buoc 0.005 · ratchet **lien tuc**
(guard `priceSLNew>priceSL` VA `>entry`) · `BLOCK_INTRABAR_LOOKAHEAD=true` (khong khop noi nen arm) ·
khop SL → `min(priceSL, bar.open)` · **loser time-stop 168h** tu leg dau (anchor `clusterFirstLegTime`) →
`STOP_LOSS_DONE` tai `min(open,close)` · delist guard (khong cap nhat >2 ngay) · gom **leg → cum**
(`mergeOrder`: entry binh quan, `minPrice` reset = close, `priceSL` reset null) · so hoc **float32** +
`normalizePrice` (BigDecimal FLOOR theo tick tu `/home/ubuntu/java/exchange_info_pin.json`).

### 1.3 Ket qua parity (n=1089 leg)

| chi tieu | nguong da chot | **dat duoc** |
|---|---|---|
| `status` trung khop | ≥ 99.0% | **100.00%** |
| thoi diem thoat trung PHUT | ≥ 97.0% | **100.00%** |
| thoi diem thoat lech ≤ 2 phut | ≥ 99.0% | **100.00%** |
| gia chot `tp` (sai so ≤ 1 tick) | ≥ 95.0% | **99.82%** |
| PnL khong-funding: trung vi \|Δ\| | ≤ 0.02 USDT | **0.0000** |
| PnL khong-funding: \|Δ\| ≤ 1 USDT | ≥ 95.0% | **100.00%** |

**VERDICT: PASS.** 2 leg lech 1 tick (NEIRO, MELANIA…) la ca **bien FLOOR** (float32 hai ben nam 2 phia
moc tick) — khong phai loi logic; tong |Δ| PnL toan tap = **0.028 USDT**.
Luu y ve funding: replay **khong** tinh funding (khong co nguon rate offline); parity so `pnl + funding`
cua CSV (identity `pnl = base − funding`) nen funding **tu triet tieu** — do la ly do trung vi Δ = 0.

## 2. BUOC 2 — Fit co ky luat (chot TRUOC, 17 policy)

Split theo gio GMT+7: **TRAIN 2022-01..2023-12 (n=316 cum)**, **TEST 2024-01..2025-12 (n=604)**,
burn-in 2021-07..12 (n=149, khong dung chon). Don vi = **cum** (= 1 lenh vao, gom ca leg DCA;
1069 cum / 1089 leg). Moi policy chi doi **HAM GAP** (arm 0.07, dinh HIGH, ratchet lien tuc, 168h giu nguyen).

| policy | TRAIN net/tr | TEST net/tr | TEST SumPnL | win% | TSloss% | cap≥20% | cap≥50% | Δ TEST (vs P0) | CI block-ngay |
|---|---|---|---|---|---|---|---|---|---|
| **F3 dinh=CLOSE** | 77.17 | **93.54** | 56496 | 90.4 | 9.9 | 0.643 | 0.569 | **+16.01** | **[−14.43, +37.64]** |
| F1 0.02+0.15p | 75.43 | 68.10 | 41134 | 89.6 | 8.4 | 0.572 | 0.185 | −9.43 | [−21.65, −0.02] |
| F1 0.01+0.15p | 74.68 | 69.17 | 41777 | 89.6 | 8.4 | 0.409 | 0.199 | −8.36 | [−20.94, +1.52] |
| F1 0.02+0p | 73.77 | 70.38 | 42510 | 89.6 | 8.4 | 0.250 | 0.214 | −7.15 | [−19.96, +3.25] |
| F1 0.005+0.15p | 73.19 | 71.11 | 42947 | 89.6 | 8.4 | 0.388 | 0.206 | −6.42 | [−18.35, +4.07] |
| F2 c=0.5 k=240 | 72.69 | 72.07 | 43528 | 89.6 | 8.4 | 0.253 | 0.214 | −5.46 | [−19.24, +5.82] |
| F1 0.005+0p | 72.62 | 72.39 | 43723 | 89.6 | 8.4 | 0.244 | 0.214 | −5.14 | [−19.15, +6.33] |
| F1 0.01+0p | 72.50 | 71.59 | 43238 | 89.6 | 8.4 | 0.242 | 0.214 | −5.94 | [−19.90, +5.44] |
| **P0 (baseline)** | 72.46 | 77.53 | 46827 | 89.6 | 8.4 | 0.628 | 0.594 | 0 | — |
| F2 c=0.75 k=60 | 72.44 | 70.24 | 42426 | 89.1 | 8.4 | 0.261 | 0.184 | −7.29 | [−21.16, +4.80] |
| F2 c=0.5 k=60 | 72.11 | 71.13 | 42964 | 89.2 | 8.4 | 0.266 | 0.199 | −6.40 | [−19.93, +5.08] |
| F2 c=0.75 k=240 | 72.04 | 71.55 | 43216 | 89.6 | 8.4 | 0.249 | 0.214 | −5.98 | [−20.18, +5.96] |
| F2 c=1 k=240 | 71.85 | 70.43 | 42540 | 89.6 | 8.4 | 0.246 | 0.214 | −7.10 | [−21.49, +4.81] |
| F2 c=1 k=60 | 71.73 | 69.73 | 42115 | 89.1 | 8.4 | 0.297 | 0.169 | −7.80 | [−21.75, +3.93] |
| F1 0.02+0.3p | 70.63 | 80.00 | 48320 | 89.6 | 8.4 | 0.568 | 0.524 | +2.47 | [−5.17, +12.68] |
| F1 0.01+0.3p | 69.85 | 73.72 | 44526 | 89.6 | 8.4 | 0.551 | 0.478 | −3.81 | [−11.35, +2.53] |
| F1 0.005+0.3p | 68.23 | 70.92 | 42839 | 89.6 | 8.4 | 0.517 | 0.432 | −6.60 | [−15.17, +1.08] |

Bang xep theo **TRAIN** (cot chon). Bang day du: `/home/ubuntu/exitfit/fit_table.csv`.
**Tong so policy da thu = 17** (multiplicity). Nhom dinh `peak ≥ 100%`: **n=1 (TRAIN) / 0 (TEST)** ⇒ **khong
du de ket luan** (o cap≥100% = nan la dung: khong co lenh nao).

### 2.1 Doc bang
- **F1 (gap = a + b×peak)**: moi bien the deu **te hon P0** o TRAIN *va* TEST, rieng `b=0.30` xap xi P0.
  Gap **lon hon** (b cao) = nuoi lau hon, khong giup; gap **nho hon** (a nho, b=0) = cat som, **hai**.
- **F2 (gap = c×ATR_k)**: **16/16 cau hinh deu < P0** tren TEST (−5 → −8/trade). ATR khong phai tin hieu
  tot hon `0.5×peak` — cung huong voi `RESULT_TRAIL_HINGE`/`RESULT_TRAIL_LADDER` (doi ham gap ⇒ tai phan phoi).
- **F3 (dinh = CLOSE thay vi HIGH)**: khac hoan toan ve **co che** (arm cung theo close): TRAIN +4.7,
  TEST **+16.0/trade (+20.6%)**, win% 89.6 → 90.4, TSloss% 8.4 → 9.9, SumPnL 46827 → 56496.

### 2.2 Kiem tra them cho F3 (POST-HOC — chi de doc, KHONG dung de chon)
| nam | P0 net/tr | F3 net/tr | Δ | CI block-ngay (post-hoc) |
|---|---|---|---|---|
| 2021 (burn-in) | 28.51 | 28.58 | +0.1 | — |
| 2022 | 36.20 | 35.26 | −0.9 | — |
| 2023 | 127.14 | 140.38 | +13.2 | — |
| 2024 | 73.24 | 83.44 | +10.2 | [+1.34, +22.32] |
| 2025 | 81.26 | 102.32 | +21.1 | [−42.29, +51.85] |

F3 duong o **4/5 nam**; rieng 2024 CI khong chua 0. Nhung **TEST gop (2024+2025) chi co 54 block-ngay**
(entry tap trung vao vai chuoi ngay bien dong) nen CI gop rong — do la ly do F3 "chua du ket luan".
Nguyen nhan co che (causal, khong look-ahead): peak do bang close luon thap hon peak do bang high ⇒ SL
thap hon ⇒ giu lenh **lau hon** ⇒ `avg_peak` 0.121→0.140 va `avg_exit_rate` 0.048→0.058, doi lai
TSloss% tang nhe (8.4→9.9).

## 3. Tra loi cau hoi cua owner

> "co nen do tren du lieu roi ra cong thuc khong?"

**CO — va da do xong: khong ra duoc cong thuc nao HON baseline co y nghia.**
- Do tren **17 cong thuc** dang `gap(peak, ATR)` va ca huong "bo HIGH" ⇒ **NULL** (16/17 ≤ P0, 1 hinh thuc
  moi F3 hon ve diem nhung **CI chua 0**).
- Khong co ham gap nao **p-value/CI** dat. Ket qua **xac nhan chan doan cu**: exit hien tai **tai phan phoi**,
  tran PHANG 0.03/0.08 va ratchet 0.5 da "du tot"; **doi so khong an**. F1 (**doi so**) va F2 (**dua ATR vao**)
  deu **am** ⇒ dong y voi `RESULT_TRAIL_HINGE` (0.05/0.12 ⇒ NULL) va `RESULT_TRAIL_LADDER` (bac thang ⇒ NULL):
  **khong con du dia cho 1 tham so don le nao o khu vuc nay**.
- **Cua duy nhat con sang**: thong tin **TRONG NEN** (dinh nen do bang **close** thay vi **high**). Day khong
  phai "fit so" ma la **bo 1 nguon nhieu** (bong nen = high 1m) ra khoi ca ARM lan dinh. Muc +20% TEST neu
  that thi dang gia, nhung **voi 604 lenh/54 block-ngay thi khong du de ket luan** ⇒ theo dung protocol:
  **khong tich hop, khong tuyen bo hon**.

## 4. De xuat buoc tiep (neu owner muon chi 1 slot)

1 sim xac nhan tren **Kaggle** (khong chay Java tren Oracle), dung cho **F3** — vi day la policy duy nhat
co dau **duong o CA TRAIN va TEST** va la thay doi **hinh dang thong tin** chu khong phai 1 con so:
- **Can gi**: jar HEAD + bundle `sim-x1-2021-bundle` + profile `x1_gs_t170` + `SIM_END_DATE=20251231`,
  `TICKER_SOURCE=file` (dung tien le `docs/KAGGLE_SIM_48M.md`), va **1 profile moi** `x1_gs_t170_close`:
  them flag `TS_PEAK_MODE=close` (**chua co trong code — phai viet**: trong `updateStatusNew`/`updateTPSL`
  thay `ticker.maxPrice` bang `max close` tu leg dau; default OFF ⇒ byte-identical, kem 1 cong parity
  T170 md5 `efb793e2` nhu moi lan truoc).
- **Uu tien thap hon** (chi 2/16 policy duong nhe): `F1 0.02+0.30p` (Δ TEST +2.47, CI [−5.17,+12.68]) —
  khong dang 1 slot.
- **KHONG nen** lam tiep: (a) fit them so/hinh dang ham gap (da 3 lan NULL), (b) dua `ATR` vao gap (16/16 am).

## 5. Gioi han (ghi TRUOC trong pre-reg, khong phai loi chinh minh sau)
1. Replay **khong** mo phong lai entry/sizing/von ⇒ `SumPnL` la **tong PnL tung lenh**, KHONG phai equity
   (khong compound/doi so lenh). Vi vay **khong** duoc doc F3 nhu "+20% CAGR".
2. **Funding bi loai** khoi moi so sanh (khong co nguon rate offline). Funding phu thuoc thoi diem dong
   lenh nen chenh giua cac policy la bac 2; tong funding cua tap T170: TEST −951 USDT, TRAIN −1123 USDT
   (dau am = long NHAN) ⇒ bo qua no **khong** doi thu tu.
3. Nhom **peak ≥ 100%** rong (n=0/1) ⇒ khong ket luan duoc ve "song lon" — dung nhu canh bao o
   `RESULT_TRAIL_LADDER`.
4. Moi so **POST-HOC** (theo nam §2.2, CI tung nam) chi de doc, **khong** duoc dung de chon policy.

## 6. Commit (khong push)
- `cb9078f` — prereg `docs/PREREG_EXIT_FIT.md` (chot truoc khi do).
- `8f3194f` — harness `research/exitfit/*` (exit_engine.py, build_cache.py, parity.py) + CONG PARITY PASS.
- commit CUOI cua vong nay (subject *result(exit-fit): NULL*, xem `git log --oneline -1`) — `research/exitfit/fit.py` + tai lieu nay (BUOC 2/3).

Tai san dung lai duoc: `research/exitfit/` (thuan Python, khong JVM) + cache nen ngoai repo
`/home/ubuntu/exitfit/` (`bars.pkl` 290MB, `clusters.json`, `fit_results.pkl`, `fit_table.csv`,
`fit_summary.txt`, `parity_detail.csv`); `cache/part_*.pkl` + `need_*.json` da don (build lai ~5 phut).
