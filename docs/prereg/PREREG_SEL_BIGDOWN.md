# PREREG_SEL_BIGDOWN — doi cach chon 2 coin cua leg BIG_DOWN (theo drop 1-phut, causal), trigger giu nguyen

Viet TRUOC khi chay bat ky sim nao. Khong sua sau khi thay ket qua.
Tu `docs/design/DESIGN_ROLLING_BIGDOWN.md` (06dadd3) + duyet cua user 2026-09-16.

## 0. Vi sao huong nay
- Truc SIZING (`docs/result/RESULT_BD_SIZE_ADAPT.md`, commit `a34083a`) da NULL: size theo severity chi
  rescale `pnl/leg`, khong doi chat luong (`meanP`/`TSloss%`) va khong doi rui ro. Nay sang truc
  **SELECTION** cung leg BIG_DOWN.
- Hien tai leg BIG_DOWN chon coin bang
  `MarketBigChangeDetector.getTopSymbolArray(2, ...)` tren `predict2Symbol` = TreeMap<Float,Short>
  cua `time2SymbolPred.get(time)` (score pNoPump TANG dan -> lay score THAP nhat = "de pump nhat").
  Gia thuyet: trong nhung phut thi truong BAN THAO MANH (`rateDownAvg < -0.03157`), chon coin "de
  pump nhat" co the KHONG phai chon coin dang ROT sau nhat (bounce ngay gan day nhat). Thu nay chi
  DOI NGUON tin hieu xep hang (tu pNoPump -> drop 1-phut), giu NGUYEN moi thu khac.

## 1. Thiet ke
### 1.1 Trigger: GIU NGUYEN
`MarketBigChangeDetector.getMarketStatus1M` khong doi mot dong. So leg BIG_DOWN duoc ky vong
**van = 248** (cong chan drift). `numberOrder = Configs.NUMBER_ENTRY_EACH_SIGNAL = 2` khong doi.
`getTopSymbolArray` (trong `MarketBigChangeDetector`) KHONG duoc sua — giu nguyen ham.

### 1.2 Drop 1-phut cua coin i tai t (causal)
```
drop_i(t) = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen)
          = (priceClose - priceOpen) / priceOpen        # am = dang rot
```
Cung cong thuc `calMarketData` dang dung de tinh `rateChange` tung coin (nghia la KHONG them
feature extractor nao). `ticker = symbol2Ticker[symbolId]` tai chinh phut t (bar 1M da dong tai
t) => chi dung du lieu <= t, causal Y HET duong baseline dang chon coin (baseline cung doc
`symbol2Ticker` tai t). Khong can previous-price/lastPrice map.

### 1.3 Universe + bo loc (GIU NGUYEN semantics cua `getTopSymbolArray`)
- Universe = tap symbol trong `predict2Symbol` (TreeMap<Float,Short> build tu `time2SymbolPred.get(time)`).
- Loc: (1) skip `symbolLocked` (cac id dang chay); (2) `symbol2Ticker[symbolId] != null`.
- `Utils.isTickerAvailable(ticker)` van duoc ap NGUYEN o vong lap `createOrderBUY` phia sau
  (khong doi). Nghia la neu chon phai coin co ticker != null nhung khong available, lenh van bi
  bo qua y het baseline.
- Nhung bien the moi chi DOI thu tu xep hang TRONG universe nay, van chon **toi da 2 coin/tick**.

### 1.4 Ba bien the (k=3, chot truoc, khong them sau)
Tie-break deterministic: moi phep sap xep dung khoa phu `symbolId` (tang) de pha hoa (identical float).
`rankP` = vi tri (1-based) theo `pNoPump` TANG (rankP=1 la pNoPump thap nhat = "de pump nhat"),
`rankD` = vi tri (1-based) theo `drop` TANG (rankD=1 la drop am nhat = rot sau nhat).

| tag | che do | cach chon 2 coin |
|---|---|---|
| SEL_DROP | drop | 2 coin co `drop_i(t)` AM NHAT (rot sau nhat) |
| SEL_MIX | mix | 2 coin co TONG HANG nho nhat: `rankP + rankD` (pNoPump tang + drop am truoc) |
| SEL_DROP_TOP8 | drop_top8 | shortlist pNoPump top-8 (rankP<=8), roi chon 2 coin rot sau nhat trong do |

- `SEL_DROP_TOP8` shortlist = `min(Configs.BD_SEL_TOPK=8, n)` coin dau theo pNoPump tang (an toan:
  giu universe cua selector, chi doi 2 coin duoc chon).
- Neu universe < 2 coin hop le => chon it hon (y het baseline khi khong du 2 ticker).

### 1.5 Code/flag (moi, default OFF => byte-identical)
- `Configs`: `BD_SEL_MODE` ("off"/"drop"/"mix"/"drop_top8", default "off") + `BD_SEL_TOPK` (default 8,
  chi dung cho drop_top8). KHONG final.
- Class moi `tradecore/BdSelection.java` (thuan tinh toan + so hang, khong IO): ham
  `select(int period, KlineObjectSimple[] symbol2Ticker, Set<Short> symbolLocked,
  TreeMap<Float,Short> predict2Symbol)` tra `Set<Short>`. Tra ve RONG khi mode=off.
- Hook CHI trong nhanh BIG_DOWN cua `SimulatorMarketLevelTicker1MStopLoss` (thay cach dung
  `symbol2BUY` khi `levelChange == BIG_DOWN && mode != off`). Cac levelChange khac + mode off:
  y het cu (goi `getTopSymbolArray` nhu truoc).
- Log 1 lan mode hieu dung o cuoi sim (giong `[BD-SIZE-ADAPT]`).
- KHONG sua feature extractor / `MarketBigChangeDetector` / `isDcaAlt` / `calMarketData` / gene HPO /
  so coin (=2). Cong parity: flag OFF => khong cap phat, khong nhanh nao chay => `printDone.csv`
  **byte-identical** `efb793e2…`.

## 2. Tieu chi (chot TRUOC)
**PRIMARY (chat luong rieng leg BIG_DOWN, khong lan entry)** — so sanh tung bien the vs parity tren
tap `level == BIG_DOWN`: `pnl/leg`, `meanP`, `TSloss%`. Thang khi **>=2/3 rate NGOAI CI**
(khoi 72h x1.21, 2000 resample, seed co dinh `20260905`) CUNG HUONG TOT
(pnl/leg TANG, meanP TANG, TSloss% GIAM).
**CHAN (bat buoc pass)**:
1. `n leg BIG_DOWN == 248` (khong doi so ve; neu khac => bao ro, khong duoc dien giai la "thang").
2. Tap trung: max % equity 1 coin **khong tang** so voi parity.
3. Rang buoc cung tren equity THAT (`sim.out`): maxDD tung nam khong xau hon parity qua +3pp;
   khong nam am; UW khong xau hon parity qua +30 ngay.
4. Rate TOAN BO leg (win%/TSloss%/meanP): khong rate nao XAU ngoai CI.
**MULTIPLICITY**: k=3 bien the x 3 rate PRIMARY; nguong thang dung he so B4 `sqrt(2 ln 3) = 1.4823`
khi so tren cung mot khung. Khong chon theo equity.
**QUYET DINH**: chon bien the manh nhat PASS het chan; neu khong bien the nao dat => NULL, giu T170.
**FOLLOW-UP**: neu SELECTION thang => stage 2 (pre-reg MOI) moi chay lai sizing tren nen selection thang.

## 3. Quy trinh
1. Code `BdSelection` + `Configs` + hook (default OFF). Build jar Oracle.
2. **Cong 1**: chay parity (flag OFF, profile goc `x1_gs_t170`) => md5 `efb793e2…` byte-identical.
3. Chay 3 bien the tren `wfo_ds_x1_2021`, `TICKER_SOURCE=file`, `SIM_END_DATE=20251231`, profile
   clone `x1_gs_t170` + key moi (`BD_SEL_MODE`).
4. Cham: tach leg BIG_DOWN tu `printDone.csv` (`level == BIG_DOWN`); rate + CI bootstrap khoi 72h;
   hard-constraint tu `sim.out`; tap trung theo margin/coin.
5. Ghi `docs/result/RESULT_SEL_BIGDOWN.md`, commit (KHONG push).

## 4. Pham vi
DEV 2021-07..2025-12 (`wfo_ds_x1_2021`). KHONG 2026 (seal). KHONG sua trigger/live/isDcaAlt/
calMarketData/gene HPO/`MarketBigChangeDetector`. KHONG push. Khong tune sau khi thay so.
