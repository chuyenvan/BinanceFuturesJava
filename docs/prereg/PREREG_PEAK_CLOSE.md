# PREREG_PEAK_CLOSE — Xac nhan F3 (dinh trailing do bang **CLOSE** thay vi HIGH) bang 1 sim tren Kaggle

Viet **TRUOC** khi do (chot 2026-09-23). **Khong sua thiet ke sau khi thay ket qua.**
Tien le: `docs/result/RESULT_EXIT_FIT.md` (commit `eb4c0de`) + harness `research/exitfit/` (commit `8f3194f`)
— fit 17 policy gap tren tap leg T170: **16/17 <= baseline**; chi **F3** (dinh = **CLOSE**) tot hon
(**TEST net/lenh 77.53 -> 93.54 = +20.6%**, SumPnL +20.7%, capture >=20% 0.628 -> 0.643) nhung
**CI TEST [−14.43, +37.64] CHUA 0** => theo dung protocol cu = **chua du ket luan, khong tich hop**.
Pre-reg nay chot cach **xac nhan F3 bang 1 chan SIM THAT tren Kaggle** (khong dung harness nam ngoai).

---

## 0. Cau hoi

Co che exit hien tai (T170, incumbent): arm `+7%`; `gap = min(maxProfit x TS_GIVEBACK_RATIO(0.5),
maxGap)`; `maxGap` = tran phang `TS_MAX_GAP_WEAK=0.03` (khi `pNoPump > TS_PNOPUMP_WEAK_THR=0.29`
hoac chua co `pNoPump`) nguoc lai `TS_MAX_GAP=0.08`; ratchet **lien tuc**; `step` lam tron `0.005`;
bat bien **SL luon > entry**; loser time-stop `168h` tu leg dau; `BLOCK_INTRABAR_LOOKAHEAD=true`.
**Dinh** (dung cho CONG ARM va de tinh gap) = **HIGH cua nen 1m** (`ticker.maxPrice`).

> **Cau hoi:** bo HIGH ra khoi **ca arm lan dinh** (dung **CLOSE** nen 1m) — keo dai lenh — **co lam
> ket qua TOT HON co y nghia** khong, xet tren **5 rate chat luong + CI block-72h**, dong thoi
> **khong vi pham rang buoc cung** va **khong lam rate nao XAU di co y nghia**?

---

## 1. BUOC 0 — DINH NGHIA CHINH XAC cua F3 (doc lai code, KHONG tu dien giai)

Doc `research/exitfit/exit_engine.py` (`Policy(peak_mode="close")`, nhanh `peak = c if ... else h`)
+ `src/main/java/.../OrderTargetInfoTest.java` (`updateStatusNew` :178-215, `updateTPSL` :245-266)
+ `SimulatorMarketLevelTicker1MStopLoss.java` (`startUpdateOldOrderTrading` :1005-1010).
**F3 da fit = dung 3 diem doi, KHONG gi khac:**

| # | cho | baseline (`high`) | **F3 (`close`)** |
|---|---|---|---|
| 1 | cong ARM (simulator) | `ticker.maxPrice >= priceEntry*(1+armRate)` | `ticker.priceClose >= ...` |
| 2 | `updateStatusNew` (dat SL lan dau) | `rateLoss = calRateLossMax(ticker.maxPrice)` | `calRateLossMax(ticker.priceClose)` |
| 3 | `updateTPSL` (ratchet SL) | `rateLoss = calRateLossMax(ticker.maxPrice)` | `calRateLossMax(ticker.priceClose)` |

**Giu NGUYEN 100%** (khong doi): cong thuc gap `min(peak x 0.5, cap)` + cap 0.03/0.08 theo
`symbolPred` (FIX_B1) · `step` lam tron 0.005 (`TrailFromCap`) · ratchet guard `priceSLNew > priceSL`
**VA** `priceSLNew > priceEntry` (bat bien SL>entry) · `minPrice` reset = close khi arm/ratchet ·
`BLOCK_INTRABAR_LOOKAHEAD` (khong khop noi nen dat SL) · khop SL = `min(priceSL, bar.open)` ·
loser time-stop 168h (anchor `clusterFirstLegTime`) → `min(open, close)` · delist guard ·
`mergeOrder` (entry binh quan, reset `minPrice`/`priceSL`) · arm rate 0.07 · funding/sizing/entry
**khong doi mot dong**.
**KHONG doi** `maePeak` (van HIGH, do-luong-only; chi tham gia quyet dinh khi `SIM_COND_EXIT_HOURS>0`
= TAT o T170). **Khong** doi bat ky tham so so/hinh dang ham gap nao khac.

---

## 2. BUOC 1 — Code (flag `TS_PEAK_MODE`)

- `Configs.TS_PEAK_MODE` (doc qua `Cfg`: profile > env; da co `TRADING_PROFILE` thi KHONG dat duoc
  qua env — fail-fast nhu moi key `TS_*`) nhan **`high`** (mac dinh, khong khai bao) hoac **`close`**.
  Gia tri khac => `validatePeakMode()` **exit 2** (khong am tham roi ve default).
- `TradeUtils.peakPrice(ticker)` = `TS_PEAK_CLOSE ? ticker.priceClose : ticker.maxPrice` — dung o
  **ca 3 diem** o §1 => che do `high` **byte-identical** (cung mot phep doc field cu).
- Profile moi `profiles/x1_gs_t170_close.properties` = **ban sao nguyen** `x1_gs_t170.properties`
  + 1 dong `TS_PEAK_MODE=close` (khac 1 key duy nhat).
- Unit test `PeakCloseTest` (mac dinh = `high`, helper tra `maxPrice`); `TrailLadderTest` phai van PASS.
- Build jar tren Oracle `mvn -o package -DskipTests` (**KHONG chay sim tren Oracle** — shadow active).

## 3. BUOC 2 — CONG PARITY (bat buoc, chot TRUOC)

Flag **OFF** (`x1_gs_t170` nguyen ban, KHONG override `TS_PEAK_MODE`) voi **jar MOI**:
`printDone.csv` phai **byte-identical** `md5 = efb793e2468ca3a7318da0f0ad23d4fc` (**n=1089 leg**,
cua so `20210701..20251231`) — cung chan giong `docs/runbooks/KAGGLE_SIM_48M.md`.
Chay them 1 chan y het + `SIM_TRAIL_TRACE=1` (do-luong-only, KHONG them cot vao printDone) => md5
**phai van** `efb793e2`. **Bat ky khac => DUNG, bao RO, khong doc ket qua F3.**

## 4. BUOC 3 — Chan F3 + cham diem (chot TRUOC)

**Chan:** 1 kernel Kaggle, profile `x1_gs_t170_close`, `SIM_TRAIL_TRACE=1`, `SIM_END_DATE=20251231`,
bundle `sim-x1-2021-bundle`, jar `sim-jar-peakclose` (jar MOI cua §2), `TICKER_SOURCE=file`.
DEV only (`2021-07-01..2025-12-31`), **khong 2026**.

### 4.1 Tieu chi (chot TRUOC)
- **5 rate chat luong** (theo LEG, toan bo tap): `win%`, `TSloss%`, `mP|SM` (meanP cua leg
  `STOP_MARKET_DONE`), `mP|SL`, `meanP` — so **F3 vs parity (T170 goc)** tren cung cua so.
- **CI block-72h, 2000 rep, seed `20260905`, anchor `2021-07-01`**, cho hieu `F3 − parity` cua tung
  rate, o **HAI do rong**: `x1.21` (legacy, muc brief yeu cau) va `inflate(k=1)=1.0` (chuan hoa
  `sqrt(2 ln k)`, `docs/audit/AUDIT_CI_INFLATE_STANDARDIZATION.md`; round nay chi **1 ung vien** vs
  baseline => `k=1`). **"Ngoai CI" chi tinh khi ngoai o CA HAI do rong** (x1.21 la do rong hon =>
  la dieu kien chat hon; dung no lam chot). HUONG: `win%`/`mP|SM`/`mP|SL`/`meanP` **tang** = TOT;
  `TSloss%` **giam** = TOT.
- **Rang buoc cung** (`docs/runbooks/RISK_APPETITE.md`): `maxDD`/nam `<= 30%`; `UW <= 200` ngay; **khong nam
  am**; quy xau nhat `>= -15%`; **tap trung 1 cum <= 15% equity**. Do tu `sim.out` + `printDone.csv`.
- **Capture ratio** cho nhom dinh **>= 20% / >= 50% / >= 100%** (theo LEG, tu `trailTrace.csv`;
  `peak` = `maePeak` = dinh HIGH GIA THAT tu leg dau — **cung mau so cho ca 2 chan**): so lenh,
  **% bi cat som** (phan bo `STOP_MARKET_DONE` / `STOP_LOSS_DONE` = exit reason), `profit/peak`
  (capture trung vi + trung binh + `mean(rate)/mean(peak)`), `SumPnL`. So **parity vs F3**.
- **PnL/equity** bao **RIENG** (equity cuoi, CAGR, SumPnL, meanP) — **KHONG** dung de chon.

### 4.2 Ket luan (chot TRUOC)
- **GO (ung vien, KHONG tich hop)** chi khi **DONG THOI**: (a) `>= 2` rate chat luong **ngoai CI
  cung huong TOT** (o CA HAI do rong), (b) **0** rate **XAU ngoai CI**, (c) **het** rang buoc cung.
- **Neu rate KHONG doi nhung capture tang** => ghi ro **"CHUA DU KET LUAN"** + bao so capture
  (day la output quan trong de owner quyet), **khong** tuyen bo hon.
- Ket qua duong (neu co) van la **UNG VIEN** — can **forward** xac nhan. **Khong tu tich hop vao
  code san xuat.** Ket qua am => ghi ro huong F3 da dong.

## 5. Gioi han (ghi TRUOC, khong phai loi chinh minh sau)
1. Kaggle sim luon `TICKER_SOURCE=file` (neo 1 lenh/970 lech aerospike — KHONG anh huong so
   **giua 2 chan** vi ca hai deu `file` tren cung bundle/cung cua so).
2. `maePeak` (mau so capture) **khong** doi theo F3 => capture la "phan dinh HIGH GIA THAT giu duoc",
   dung cho ca 2 chan; **nhung F3 co dinh thap hon nen capture se thap hon ve co hoc** — do la
   **he qua cua thiet ke**, phai doc kem `meanP`.
3. Nhom `peak >= 100%`: o tap T170/harness chi `n=1` (TRAIN) / `0` (TEST) => **rong, khong ket luan**.
4. CI bootstrap **block-72h** (khong phai block-ngay nhu harness) => so CI o day **khong** so sanh
   truc tiep duoc voi `[−14.43, +37.64]` cua `RESULT_EXIT_FIT.md` §2.
5. 1 chan F3 = **1 diem do**; khong quet tham so F3 (khong fit them gi).
