# PREREG_BD_SIZE_ADAPT — size leg BIG_DOWN theo do sau (rolling severity), trigger giu nguyen

Viet TRUOC khi chay bat ky sim nao. Khong sua sau khi thay ket qua.
Tu `docs/design/DESIGN_ROLLING_BIGDOWN.md` (06dadd3) + duyet cua user 2026-09-16 "ok lam di".

## 0. Vi sao huong nay (khong phai nguong rolling)
- Trigger BIG_DOWN hien tai `rateDownAvg < MS_DOWN_BIG_AVG (-0.03157)` — CO DINH; da chung minh
  KHONG the lam rolling: dang `mean_N-k*std_N` cho 166x-495x trigger (9/9 FAIL) vi skew -14.9 /
  excess-kurtosis +2401; quantile rolling cuc doan khong uoc luong duoc (p~5.4e-5, ~2 mau/cua so).
- `AUDIT_BIGDOWN_DECOMPOSE_READJUDICATE` muc 1+3: gia tri BIG_DOWN cua T170 den tu **SIZING**
  (pnl/leg 46.6 -> 53.3 -> **65.5** USD, +41% tu CUNG 248 leg/124 tick/54 ngay; gate chat => throttle
  cao => moi leg duoc cap budget lon hon). **=> thu nghiem nay dat size theo do sau, KHONG doi trigger.**
- Luu y doi chieu `QUEUE` Q5 (sizing dong): Q5 ket luan sizing TOAN CUC khong doi chat luong tung
  lenh. Bai nay khac: sizing **CO DIEU KIEN theo severity cua rieng leg BIG_DOWN** (khong doi
  F_BASE/U_MAX/DCA_GRID_SCALE). Neu ket qua chi doi thang do ma khong doi chat luong/n rui ro ->
  ghi NULL dung nhu Q5.

## 1. Thiet ke
### 1.1 Trigger: GIU NGUYEN
`MarketBigChangeDetector.getMarketStatus1M` khong doi mot dong. So leg BIG_DOWN duoc ky vong
**van = 248** (cong chan drift).

### 1.2 Severity (causal, tinh TRONG Java tu chinh market TreeMap)
```
thr   = MS_DOWN_BIG_AVG = -0.03157          # nguong trigger, khong doi
x(t)  = rateDownAvg tai phut trigger
qmin(D) = min(rateDownAvg) tren [D-N, D)    # N=120 ngay lich TRUOC D, causal, KHONG gom D
sev(t)  = clamp( (thr - x(t)) / (thr - qmin(D) + eps), 0, 1 )     # 0 = vua cham nguong, 1 = sau nhat N ngay
```
`qmin` tinh TRONG Java MOT LAN tu chinh `time2MarketData: TreeMap<Long, MarketDataObject>` cua sim
(khong CSV, khong Python): `dayMin[D] = min(rateDownAvg)` qua cac phut cua ngay lich D (cung cach
sim key ngay = `floorDiv(ms, 86400000)`, tien le `RegimeSchedule.scaleForTime`);
`qmin(D) = min(dayMin[D-N .. D-1])`. `eps = 1e-6`. Nguon du lieu: cung `time2MarketData` sim dang
doc (WFO_DATA_DIR) — khong can file phu.

### 1.3 Ba bien the (k=3, khong them sau khi thay so)
`sizeMult` chi ap cho leg co `levelChange == BIG_DOWN`, nhan vao budget SAU tier/trong so grid:

| tag | che do | sizeMult | y nghia |
|---|---|---|---|
| BD_DOWN50 | giam khi sau | `clamp(1 - 0.50*sev, 0.50, 1.00)` | an toan: cuc doan => nua size |
| BD_DOWN25 | giam nhe | `clamp(1 - 0.25*sev, 0.75, 1.00)` | an toan nhe |
| BD_UP50 | tang khi sau | `clamp(1 + 0.50*sev, 1.00, 1.50)` | falisification: neu sau = co hoi |

Doi chung: **parity** (flag OFF) = `X1_GS_T170_2021` md5 `efb793e2468ca3a7318da0f0ad23d4fc`, n=1089.

### 1.4 Code/flag (moi, default OFF => byte-identical)
- `Configs`: `BD_SIZE_ADAPT` ("off"/"down50"/"down25"/"up50") + `BD_SIZE_ADAPT_N` (default 120).
- Class moi `tradecore/BdSizeAdapt.java` (build lich day->qmin 1 lan tu chinh market TreeMap, `floorEntry`), CHI goi tu
  `SimulatorMarketLevelTicker1MStopLoss.createOrder` (duong SIM). Khong cham
  `MarketBigChangeDetector` / `isDcaAlt` / `calMarketData` / gene HPO.
- Cong parity: flag OFF => khong cap phat cau truc => `printDone.csv` **byte-identical** `efb793e2…`.

## 2. Tieu chi (chot TRUOC)
**PRIMARY (chat luong rieng leg BIG_DOWN, khong lan entry)** — so sanh tung bien the vs parity:
`pnl/leg BIG_DOWN`, `meanP` leg BIG_DOWN, `TSloss%` leg BIG_DOWN. Thang khi **>=2/3 rate ngoai CI**
(khoi 72h x1.21) CUNG HUONG TOT.
**CHAN (bat buoc pass)**:
1. `n leg BIG_DOWN == 248` (khong doi so ve; neu khac => bao ro, khong duoc dien giai la "thang").
2. Tap trung: max % equity vao 1 coin **khong tang** so voi parity.
3. Rang buoc cung tren equity THAT (`sim.out`, khong dung duong tong hop): maxDD tung nam khong xau
   hon parity qua +3pp; khong nam am (parity khong co); UW khong xau hon parity qua +30 ngay.
4. Rate TOAN BO leg (win%/TSloss%/meanP): khong rate nao XAU ngoai CI.
**MULTIPLICITY**: k=3 bien the + 3 rate PRIMARY => ghi ro; nguong thang dung he so B4
`sqrt(2 ln 3) = 1.4823` khi so tren cung mot khung. Khong chon theo equity.
**QUYET DINH**: chon bien the manh nhat PASS het chan; neu khong bien the nao dat -> NULL, giu T170.

## 3. Quy trinh
1. `BdSizeAdapt` build lich day->qmin 1 lan TRONG Java tu chinh market TreeMap (khong Python/CSV).
2. Code + build jar Oracle. **Cong 1**: chay parity (flag OFF) => md5 `efb793e2…` byte-identical.
3. Chay 3 bien the tren `wfo_ds_x1_2021`, `TICKER_SOURCE=file`, `SIM_END_DATE=20251231`, profile
   clone `x1_gs_t170` + key moi.
4. Cham: tach leg BIG_DOWN tu `printDone.csv` (`level == BIG_DOWN`); rate + CI; hard-constraint tu
   `sim.out`; tap trung tu `printDone` (margin theo coin).
5. Ghi `docs/result/RESULT_BD_SIZE_ADAPT.md`, commit. Xoa artifact tam.

## 4. Pham vi
DEV 2021-07..2025-12 (`wfo_ds_x1_2021`). KHONG 2026 (seal). KHONG sua trigger/live/isDcaAlt/
calMarketData/gene HPO. KHONG push. Khong tune sau khi thay so.
