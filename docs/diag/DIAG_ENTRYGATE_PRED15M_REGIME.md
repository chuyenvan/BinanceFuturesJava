# DIAG_ENTRYGATE_PRED15M_REGIME — phan bo predReturn15M, tinh doi xung cua gate, regime tang/giam, cua so UW dai nhat

> **Gioi han cua tai lieu nay** (doc truoc khi dung): day la phan tich **MO TA (descriptive)**,
> chi doc du lieu da co, **KHONG pre-reg, KHONG sua `.java`, KHONG them flag, KHONG chay sim moi,
> KHONG push**. Moi so o day mo ta **co che da xay ra tren DEV**, khong phai bang chung de tune.
> Bat ky y tuong sua nao sinh ra tu day **van phai pre-reg rieng** va xac nhan tren holdout 2026.
> Nguon du lieu: `pred.bin` / `market.bin` (`/home/ubuntu/wfo_ds_x1_2021/`, manifest da verify md5),
> `printDone.csv` + `sim.out` cua `X1_GS_T170_2021` (profile `x1_gs_t170.properties`,
> md5 printDone `efb793e2468ca3a7318da0f0ad23d4fc`, n=1089), `CLOSES_1H.bin`
> (`/home/ubuntu/java/fsrun/`, BE `[ts>i8,sym>i2,c>f4]`), `symbol_map.csv` (BTCUSDT = symId 1).

2026-09-17.

---

## 1. `predReturn15M` la gi

- **Field**: `AiPredictionData.predReturn15M` (`src/main/java/.../ai_ml/onnx/AiPredictionData.java:11`).
- **Model sinh ra no**: XGBoost regressor, target `futureReturn15M` -> ONNX
  `Model_Regressor_Return15M.onnx`. Doc tu `OnnxInferenceManager.java:40,50`
  (`this.p15M = new SinglePredictor(modelDir, "futureReturn15M", "Regressor")`),
  33 feature V3FULL (cung thu tu model train).
- **Sinh the nao**: `GenerateGate15mV2Predictions.java` (TASK-043) replay 1 phut / mui ten, generate
  tai **moi moc `ts % 15min == 0`**, ghi set Aerospike `ai_pred_market_gate_wfo` -> export thanh
  `pred.bin`. Verify 3 moc tham chieu (0.006784 / 0.007545 / 0.006802).
- **Nhan cua model (label)** `futureReturn15M` = **trung binh "max upside potential" trong 15 phut
  toi cua ro "potential losers"** — tinh o `RunFullDataCollection.calculateBasketMaxPotential`
  (`RunFullDataCollection.java:94,101-135`): moi coin trong basket lay
  `(maxHigh - entry)/entry` trong 15 phut toi, roi **trung binh cong**. Basket =
  `HistoryManager.findPotentialLosers` (`HistoryManager.java:477-507`): top-60 coin co
  `dropFromPeak = (close - maxPrice15m)/maxPrice15m < -0.001`, sap theo do sut giam dan.
- **Don vi**: phan tram dang fraction (0.0068 = 0.68%). Vi label la **max over high** nen no
  **gan nhu luon >= 0** (khong phai "return co dau" — xem muc 2).
- **Noi luu**: `pred.bin` `[count:int][ts:long][predReturn15M:float][predRisk4H:float]`
  (`WfoDataset.java:26,354`, BE). Cot `pred15m` trong `printDone.csv` la gia tri nay tai luc entry.
- **KHONG nham lan**: day la **prediction cap MARKET (ro losers)**, khong phai prediction tung coin;
  con `symbolPred` la score selector tung coin (kha nang thang, `1 - P(win)`), dua tren funding/OI.

---

## 2. Phan bo `predReturn15M` (pred.bin, n = 2,500,260, 2021-03-31 -> 2025-12-31)

| thong so | gia tri |
|---|---|
| min / max | **0.00202** (0.20%) / **0.12261** (12.26%) |
| ti le am / =0 / duong | **0% / 0% / 100%** |
| NaN | 0 |
| p1 / p5 / p25 | 0.00284 / 0.00328 / 0.00442 |
| p50 / p75 / p95 / p99 | 0.00545 / 0.00673 / 0.00960 / 0.01308 |
| mean / std | 0.00585 / 0.00249 |

Theo nam:

| nam | n | mean | p50 | frac>0 | p5 | p95 |
|---|---|---|---|---|---|---|
| 2021 | 396,420 | 0.00667 | 0.00585 | 1.000 | 0.00463 | 0.01086 |
| 2022 | 525,600 | 0.00564 | 0.00529 | 1.000 | 0.00344 | 0.00904 |
| 2023 | 525,600 | **0.00433** | 0.00408 | 1.000 | 0.00285 | 0.00657 |
| 2024 | 527,040 | 0.00552 | 0.00522 | 1.000 | 0.00362 | 0.00823 |
| 2025 | 525,600 | **0.00731** | 0.00704 | 1.000 | 0.00463 | 0.01063 |

**Ket luan muc 2**: `predReturn15M` **KHONG he lech ve phia am** — no **khong bao gio am**, phan bo
le phai (max 12.26% nhung median chi 0.545%). Gia thuyet user "predReturn15M chi nam muc THAP =
thi truong GIAM" **sai o muc ban chat**: bien nay khong mang dau am/duong cua thi truong, no la
**"do lon cua con bat day du doan trong 15 phut toi"** (luon >= 0).

---

## 3. `EntryGate` dung no the nao

`src/main/java/.../tradecore/EntryGate.java` (99 dong, L7):

```
thr(symbolPred) = thrBase * max(DYN_MIN, (symbolPred / SCORE_BASE) * DYN_MULT) * gateScale
PASS  <=>  !(predReturn15M < thr)          // tuc predReturn15M >= thr (truong hop khong NaN)
```

- `DYN_MIN = 0.26787`, `SCORE_BASE = 0.15`, `DYN_MULT = 1.28760` — **hang so** (EntryGate.java:44-48).
- `gateScale` = `GATE_DYN_SCALE` (profile), hoac `CURRENT_REGIME_SCALE` neu `GATE_REGIME_ADAPTIVE` (OFF).
- `thrBase` = `Configs.MIN_MOMENTUM_15M`.
- Profile **T170** (`profiles/x1_gs_t170.properties`): `SIM_MIN_MOMENTUM_15M=0.008`,
  `SIM_GATE_DYN_SCALE=1.70`. => `thr` tu **0.008*0.26787*1.7 = 0.00364 (0.36%)** (khi symbolPred
  nho, chay floor) den **~0.052 (5.2%)** (symbolPred = 0.4439, max do duoc).
- **Nhanh khong qua selector** (`symbolPred == null`: BIG_DOWN / DCA_LEVEL1 / leg market-signal):
  `threshold` tra `thrBase` (0.008) **khong nhan gate scale** (EntryGate.java:80).
  `AIRejectFilter.entryGate` (`AIRejectFilter.java:60-63`): `sp = predictSymbolTrade ? symbolPred : null`.

**Tinh doi xung — tra loi truc tiep**:

- Day la **cong LONG-ONLY momentum**: cho vao **CHI KHI `predReturn15M` CAO** (>= nguong duong
  0.36%..5.2%), **tu choi khi THAP**. Nguong **tang don dieu** theo `symbolPred`.
- **KHONG co nhanh doi xung nao cho phep vao khi `predReturn15M` THAP.** Gia thuyet user
  "gate chi bat muc THAP / thi truong GIAM, chua bat muc CAO / TANG" la **NGUOC so voi code**:
  gate **bat muc CAO** (tin hieu bat day manh), khong bao gio bat muc THAP.
- Vi `PASS = !(x < thr)` la **ham don dieu khong giam** theo `predReturn15M`: `predReturn15M` cang
  cao cang de qua, **gate khong the chan `predReturn15M` o vung cao** (mat hoa hoc, khong can du lieu).

---

## 4. Hanh vi thuc te (gate cho qua theo predReturn15M)

- `sim.out` (T170): `[GATE] scale=1.7 base=0.008 n_cand=17925650 n_pass=841` => **pass rate
  841/17,925,650 = 0.00469%** (cuc ky chon loc).
- printDone: **821 entry `PREDICT_SYMBOL_TRADE`** (qua gate) + **248 BIG_DOWN** + **20 DCA_LEVEL1**
  (bypass gate, symbolPred null). `pred15m` cua 821 entry gate: **min 1.06%, p25 1.83%, p50 2.51%,
  p75 3.62%, max 11.73%** — kiem chung: **100% thoa `pred15m >= thr`** (thr p50 = 1.99%, max 5.18%).
- `symbolPred` 821 entry: min 0.0286, p50 0.1705, max 0.4439.

Bang bucket (pred15m -> ti le xuat hien trong tap candidate vs tap da qua gate):

| bucket pred15m | pred.bin (candidate) | gate entry (n) | gate entry (%) |
|---|---|---|---|
| [0.000, 0.004) | 16.6% | 0 | 0% |
| [0.004, 0.006) | 45.8% | 0 | 0% |
| [0.006, 0.008) | 25.3% | 0 | 0% |
| [0.008, 0.010) | 8.3% | 0 | 0% |
| [0.010, 0.015) | 3.37% | 103 | 12.6% |
| [0.015, 0.020) | 0.37% | 157 | 19.1% |
| [0.020, 0.030) | 0.15% | 270 | 32.9% |
| [0.030, 0.050) | 0.06% | 223 | 27.2% |
| [0.050, 0.200) | 0.02% | 68 | 8.3% |

**Doc bang**: trong 2.5M candidate, **89.4% co pred15m >= 0.36%** (floor), nhung chi **3.98% >= 1.0%**
va **0.23% >= 2.0%**. Gate **KHONG BAO GIO cho qua pred15m < 1.0%**; ti le cho qua **tang don dieu**
theo pred15m. => **gate chan o vung THAP, khong chan o vung CAO.** Gia thuyet user nguoc.

---

## 5. Regime (BTC 30d return) — so lenh / PnL / gate / meanP / win%

Dinh nghia regime (dung `CLOSES_1H.bin`, BTCUSDT symId=1, 30d return tai luc entry):

- **TANG (UP)**: BTC 30d return >= +10%
- **GIAM (DOWN)**: BTC 30d return <= -10%
- **DI NGANG (FLAT)**: con lai

Phan bo BTC 30d return tai 1089 entry: min -32.7%, p25 -12.9%, p50 -2.2%, p75 +6.2%, max +54.5%.

| regime | n | PnL (USDT) | meanP% | win% | gate (n / PnL) | bypass (n / PnL) |
|---|---|---|---|---|---|---|
| UP | 219 | **+23,380** | **6.61** | **92.7** | 165 / +17,715 | 54 / +5,664 |
| DOWN | 344 | +14,847 | 4.01 | 85.8 | 295 / +7,981 | 49 / +6,866 |
| FLAT | 526 | **+37,844** | 5.49 | 88.0 | 361 / +21,418 | 165 / +16,426 |

Theo regime x level:

| regime | level | n | PnL | meanP% | win% |
|---|---|---|---|---|---|
| UP | PREDICT_SYMBOL_TRADE | 165 | +17,715 | 6.91 | 92.1 |
| UP | BIG_DOWN | 54 | +5,664 | 5.69 | 94.4 |
| DOWN | PREDICT_SYMBOL_TRADE | 295 | +7,981 | 2.74 | 85.4 |
| DOWN | BIG_DOWN | 40 | +2,815 | 5.40 | 90.0 |
| DOWN | DCA_LEVEL1 | 9 | +4,050 | 39.25 | 77.8 |
| FLAT | PREDICT_SYMBOL_TRADE | 361 | +21,418 | 4.20 | 88.9 |
| FLAT | BIG_DOWN | 154 | +7,775 | 4.31 | 86.4 |
| FLAT | DCA_LEVEL1 | 11 | +8,651 | 64.04 | 81.8 |

**Ket luan muc 5**: he **co loi o CA 3 regime**, va **regime UP co meanP cao nhat (6.61%) + win cao
nhat (92.7%)**. Gate **KHONG chan o pha TANG** — no vao **nhieu nhat va chat nhat** o pha UP
(meanP gate 6.91%). => "he bo lo song TANG vi gate chan" **khong dung**.

---

## 6. Cua so UW dai nhat cua T170 — CHINH XAC tu equity that (sim.out)

Equity = `b + unP` (BalanceManagerSimple.java:215; log hang ngay `Update YYYYMMDD 07:00 => b:... unP:...`).
Chuoi 1644 ngay (2021-07-01 -> 2025-12-30). Final equity 111,070; max 114,641 (2025-11-08);
maxDD -11.84% (2022-11-10).

**Cua so underwater dai nhat**: `2024-04-10` -> `2024-07-10` (**92 ngay**), depth -6.6%,
peak truoc do 72,229 (2024-04-09).

**BTC trong cua so do** (CLOSES_1H, daily/1h close):

| moc | BTC | ngay |
|---|---|---|
| peak (truoc UW) | **71,786** | 2024-04-09 |
| dau cua so | 68,663 | 2024-04-10 |
| **DAY thap nhat** | **53,923** | 2024-07-05 |
| cuoi cua so | 57,658 | 2024-07-10 |

=> BTC **GIAM** tu ~71.8k ve day ~53.9k (-21.5%) roi hoi ve 57.7k. **KHONG phai "70k -> 120k".**

**Doi chieu nhan dinh user** ("doan BTC tang tu 70k len 120k"):

- Cua so **70k -> 120k** (BTC tang) thuc chat la **2025-03 -> 2025-10**: BTC 90,113 (03-04) ->
  day 74,781 -> dinh 125,986 -> 111,744 (10-11) (day la noi dung `docs/diag/DIAG_UW_WINDOW_202503_202510.md`
  da phan tich). Nhung voi **T170 hien tai (x1_gs_t170, flat gate 1.7)** cua so nay **KHONG phai UW
  dai nhat**: equity 2025-03-03 = 97,000, roi **phuc hoi new-high 97,384 ngay 2025-04-08** (UW chi
  **35 ngay**), sau do tang deu 97,440 -> 98,939 -> 110,885 (10/2025).
- => **Nhan dinh user SAI**: cua so UW dai nhat cua T170 la **2024 Q2 (BTC GIAM 71k->54k->58k)**,
  khong phai "BTC tang 70k->120k". (Luu y: `DIAG_UW_WINDOW_202503_202510.md` goi file nay la
  "RG_A_T170" nhung profile thuc la `x1_gs_t170.properties`, PROFILE_HASH `0d0fa22158b1d8c0`,
  cung `[GATE] scale=1.7 base=0.008 n_cand=17925650 n_pass=841`, cung final `b:111070` — la
  CUNG MOT run. So "221 ngay UW" trong doc do toi nay la theo **mot duong equity khac**
  ("duong tong hop" / realized-PnL tich luy), khong phai equity that `b+unP` tu sim.out.)

**Gate lam gi trong cua so UW dai nhat (2024-04-10 -> 2024-07-10)**:

- 80 lenh trong 92 ngay: **56 gate (PREDICT_SYMBOL_TRADE)** + **24 BIG_DOWN** (bypass). Khong DCA.
- Tong PnL **-186 USDT** (gan hoa von): gate 56 lenh **-551.5** (meanP +2.19%, win 76.8%),
  BIG_DOWN 24 lenh **+365.9** (meanP +3.77%, win 87.5%).
- Gate **KHONG chan** — no cho qua 56 lan trong 92 ngay. Lo den tu **mot so alt sup rieng le**
  trong khi BTC giam: CKB -41.76%, LEVER -46.39%, ATA -32.23%, TNSR -25.37%, BB -28.00%,
  ORDI -25.91%, BEL -21.02%, OM -23.10% (cac lenh nay deu qua gate, pred15m ~1.6%-3.9%).

---

## 7. KET LUAN — gia thuyet user dung / sai

**Sai ca hai ve** (huong cua gate + cua so UW), nhung cau hoi goc ("tai sao T170 co chu ky UW dai")
la cau hoi that va dang duoc tra loi dung huong.

1. **"predReturn15M chi nam muc THAP = thi truong GIAM" — SAI.** Bien nay **luon >= 0** (0.20%..
   12.26%, median 0.545%), la **do lon con bat day du doan**, khong phai dau tang/giam. Va **gate
   cho vao khi predReturn15M CAO** (>= 0.36%..5.2%), **tu choi khi THAP** — **nguoc** hoan toan so
   voi tri nho cua user.
2. **"gate bat doi xung khien bo lo song TANG" — SAI.** Gate la cong **LONG-ONLY momentum**, vao
   **CHI khi tin hieu bat day manh**. Thuc te regime **UP co meanP cao nhat 6.61% + win 92.7%**,
   gate vao nhieu nhat o pha UP. Gate **khong chan** song tang.
3. **"UW dai nhat la doan BTC tang 70k->120k" — SAI.** UW dai nhat cua T170 la **2024-04-10 ->
   2024-07-10 (92 ngay), BTC GIAM 71.8k -> 53.9k -> 57.7k**.

**Nguyen nhan chinh cua UW dai nhat** (tu du lieu, khong phai gate): danh muc **long ALT, khong co
BTC beta**; trong pha BTC giam (2024 Q2) mot so **alt chon bi sup rieng le** (CKB -41.76%,
LEVER -46.39%, ATA -32.23% ...) xoa sach cac lenh thang nho. Gate khong phai thu pham — no van cho
qua 56 lenh trong 92 ngay, chi la cac lenh do **khong co loi the khi BTC giam manh**.

**Cac kha nang nguyen nhan khac (dau hieu, chua phai ket luan)**:

- **(a) Selector chon top-8 coin theo pNoPump / potential-losers** (anti-pump) => long vao cac coin
  dang sut, de gap "dao bay" trong pha giam. *Chua kiem rieng o day* (can xem thu tu rank + IC).
- **(b) Exit arm 0.07 + TS giveback 0.5** cat som nhip hoi => chot lai it, khong du bu cho cac
  con sup. *Da thay o C3_BASELINE (phan bo winner med ~5%) nhung chua quy rieng cho cua so UW nay.*
- **(c) BIG_DOWN bypass gate** — nhung o cua so UW nay BIG_DOWN **CO loi** (+365.9), la **nguon lai**,
  khong phai nguyen nhan lo.
- **(d) time-stop 168h** giet vi the chet cham (cung la cai cat lo, khong phai nguon lo moi).
- **(e) Khong co BTC beta** — moi truong "BTC-led" la xau nhat cho danh muc long-alt (da neu o
  `DIAG_UW_WINDOW_202503_202510.md` muc 6).

---

## 8. Neu muon sua — cac huong (khong de xuat con so)

| huong | can gi | rui ro | bang chung can de ket luan |
|---|---|---|---|
| (1) Loc alt theo beta/BTC (giam long coin khong theo BTC) | them feature beta, threshold | co the bo mat coin "bay" rieng le co loi lon | IC cua beta voi PnL lenh + ablation tren DEV, xac nhan holdout |
| (2) Giam thi hai alt sup (SL chac hon / cap DD) | sua exit/SL | cat som => giam meanP winner | phan bo loser trong cua so giam + meanP|SL sau sua |
| (3) Tang vai tro BIG_DOWN (bat day) | co che bat day manh hon | bat day sai => lot dao | so BIG_DOWN da co loi o 2 cua so (2024Q2 + 2025) |
| (4) Gate theo regime BTC (UP/not-up) | pre-reg scale per regime | fit regime tren DEV | da co `PREREG_REGIME_GATE.md`; xem ket qua RG_* |
| (5) Xem lai selector (pNoPump) | pre-reg rank/cutoff | doi dinh huong danh muc | rank-IC theo PnL, khong chi P(win) |

**Luu y chot**: (2)/(3)/(4) deu phai **pre-reg rieng**; moi con so o day sinh tu **chinh cua so DEV**
da nhin nen khong duoc dung de tune truc tiep.

Co-Authored-By: Claude (subagent) — phan tich mo ta, khong pre-reg, khong push.
