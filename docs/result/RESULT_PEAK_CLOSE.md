# RESULT_PEAK_CLOSE — F3 (dinh trailing do bang **CLOSE** thay vi HIGH) tren SIM THAT (Kaggle, T170, DEV)

Chot truoc: `docs/prereg/PREREG_PEAK_CLOSE.md` (commit `1fcabe4`). Code: commit `dca07ce`.
Tien le: `docs/result/RESULT_EXIT_FIT.md` (harness offline, `eb4c0de`) — F3 la ung vien DUY NHAT con lai.
**Khong push.** Sim **chi tren Kaggle** (khong chay Java tren Oracle — shadow active).

## 0. KET LUAN (doc truoc)

**NO-GO / KHONG HON.** Tren sim that, F3 **khong** tai hien duoc muc +20,6% cua harness:
- **Tang theo tung lenh: CO, nhung KHONG y nghia** — `meanP` 5,244 → **5,994** (+14,3%, CI block-72h
  chua 0), `mP|SM` 7,642 → **9,044** (+1,403, **ngoai CI cung huong TOT**).
- **Nhung TONG thi KHONG hon — hoi te hon:** F3 **mat 50 lenh** (1089 → **1039**, vi giu lenh lau hon
  nen 1 symbol bi chiem lau hon / it slot hon) ⇒ `SumPnL` 76 070 → **75 812** (−259 USDT),
  **equity 111 070 → 110 811 (−0,23%)**, CAGR 29,27% → 29,20%.
- **Dong thoi XAU di co y nghia:** `TSloss%` 9,73 → **11,45** (+1,72 diem %, **ngoai CI cung huong XAU**).
- **Capture ratio (nhom song lon) TANG** — dac biet `peak >= 100%`: capture trung vi 0,262 → **0,385**,
  con cach dinh luc thoat 112,3 → **94,3** diem % — **nhung SumPnL cua chinh nhom do LAI GIAM**
  (15 906 → 13 399, CI [−6 057, −208] *). Tuc la **lai chuyen tu nhom nay sang nhom khac**, khong phai
  cai thien tong the (cung hinh dang "tai phan phoi" cua `RESULT_TRAIL_HINGE`/`RESULT_TRAIL_LADDER`).
- Theo **tieu chi da chot** (`>=2` rate ngoai CI cung huong TOT **VA** `0` rate XAU ngoai CI **VA** het
  rang buoc cung): **dat 1/5 rate tot, 1/5 rate xau** ⇒ **KHONG GO**.
- Rang buoc cung (`RISK_APPETITE`): **PASS ca 2 chan** (F3: maxDD −8,87%, UW 164, quy xau nhat −0,16%,
  khong nam am, tap trung 6,98%).
- **Huong F3 nay DONG.** Khong de xuat tich hop, khong de xuat them slot. Ket luan nay **khong** xoa
  gia tri cua chan doan `RESULT_EXIT_FIT` (exit tai phan phoi) — no **xac nhan manh hon**: ngay ca
  thay doi *hinh dang thong tin* (bo HIGH khoi arm+trailing) cung khong vuot baseline trong sim that.

## 1. BUOC 0 — F3 da fit la gi (tai hien DUNG, khong tu dien giai)

Doc `research/exitfit/exit_engine.py` + `OrderTargetInfoTest` + `SimulatorMarketLevelTicker1MStopLoss`:
**dung 3 diem doi, khong gi khac** (chi tiet o `docs/prereg/PREREG_PEAK_CLOSE.md` §1):

| # | cho | baseline `high` | F3 `close` |
|---|---|---|---|
| 1 | cong ARM (simulator :1018) | `ticker.maxPrice >= priceEntry*(1+armRate)` | `ticker.priceClose >= ...` |
| 2 | `updateStatusNew` (dat SL lan dau) | `calRateLossMax(ticker.maxPrice)` | `calRateLossMax(ticker.priceClose)` |
| 3 | `updateTPSL` (ratchet) | `calRateLossMax(ticker.maxPrice)` | `calRateLossMax(ticker.priceClose)` |

Giu nguyen 100%: `gap = min(peak x 0.5, cap 0.03/0.08 theo symbolPred)`, `step` 0.005, ratchet
`priceSLNew > priceSL && > priceEntry` (bat bien SL>entry), `minPrice=close` khi arm/ratchet,
`BLOCK_INTRABAR_LOOKAHEAD`, khop `min(priceSL, open)`, loser time-stop 168h, delist guard, `mergeOrder`,
arm 0.07. `maePeak` **khong doi** (van HIGH; do-luong-only).

## 2. BUOC 1 — Code + jar + test

- `Configs.TS_PEAK_MODE` (`high` mac dinh / `close`, doc qua `Cfg`, gia tri khac => `validatePeakMode()` exit 2);
  `TradeUtils.peakPrice(ticker)` dung o **ca 3 diem** tren; profile moi `profiles/x1_gs_t170_close.properties`
  (= `x1_gs_t170` + 1 dong `TS_PEAK_MODE=close`).
- Build jar tren Oracle (`mvn -o package -DskipTests`, **khong chay sim tren Oracle**) ⇒
  `sha256 = 70066fca33d347c3b6212dfd613f3a6694ca3684e7aece188790b183dfba24ff`.
- Unit test: `PeakCloseTest` **3/3 PASS** (mac dinh `high`, helper tra `maxPrice`) + `TrailLadderTest`
  **5/5 PASS**. `tools/check_cfg_gateway.sh` = OK.

## 3. BUOC 2 — CONG PARITY (jar MOI) — **PASS byte-identical**

| chan | profile | override | printDone md5 | n lenh | equity cuoi |
|---|---|---|---:|---:|---:|
| `pc-par` | `x1_gs_t170` (nguyen ban) | — | **`efb793e2468ca3a7318da0f0ad23d4fc`** | 1089 | 111 070 |
| `pc-part` | `x1_gs_t170` | `SIM_TRAIL_TRACE=1` | **`efb793e2468ca3a7318da0f0ad23d4fc`** | 1089 | 111 070 |
| tham chieu (`KAGGLE_SIM_48M.md`, Oracle `X1_GS_T170_2021`) | | | `efb793e2...` | 1089 | 111 070 |

=> Che do `high` **byte-identical** voi jar moi; `SIM_TRAIL_TRACE` khong doi ket qua.
Log xac nhan dung che do: `[PEAK-CLOSE-CFG] mode=high close=false` (par) / `mode=close close=true` (F3).

## 4. BUOC 3 — Chan F3 tren Kaggle + cham diem

Chan: profile `x1_gs_t170_close` + `SIM_TRAIL_TRACE=1`, `SIM_END_DATE=20251231`, bundle
`sim-x1-2021-bundle`, jar `sim-jar-peakclose`, `TICKER_SOURCE=file`, symbol mapper 863 (>= 800).
`printDone` md5 F3 = `131344677a956a0af495391a954cfa31` (n=**1039**) — **khac** parity (dung, co thay doi).

### 4.1 (a) 5 RATE CHAT LUONG (theo LEG, toan bo cua so)

| tag | n | win% | TSloss% | mP\|SM | mP\|SL | meanP |
|---|---:|---:|---:|---:|---:|---:|
| parity (T170) | 1089 | 88,25 | 9,73 | 7,642 | −16,992 | 5,244 |
| **F3 (peak=close)** | **1039** | 88,07 | **11,45** | **9,044** | −17,585 | **5,994** |
| Δ | **−50** | −0,18 | **+1,72** | **+1,40** | −0,59 | **+0,75** |

### 4.2 (a2) CI block-72h (2000 rep, seed `20260905`, anchor `2021-07-01`) cua hieu `F3 − parity`

| rate | Δ | CI @x1.21 (legacy) | CI @1,0000 (inflate k=1) | ngoai CI | huong |
|---|---:|---|---|---:|---|
| `win%` | −0,181 | [−1,545, +0,951] | [−1,328, +0,735] | − | - |
| `TSloss%` | **+1,720** | **[+0,611, +2,775]** | **[+0,798, +2,587]** | **Y** | **XAU** |
| `mP\|SM` | **+1,403** | **[+0,309, +2,714]** | **[+0,518, +2,506]** | **Y** | **TOT** |
| `mP\|SL` | −0,593 | [−2,174, +0,832] | [−1,913, +0,571] | − | - |
| `meanP` | +0,750 | [−0,224, +1,794] | [−0,049, +1,619] | − | - |

**=> rate ngoai CI (ca 2 do rong) cung huong TOT = 1/5 | XAU ngoai CI = 1/5.**
Tieu chi GO doi `>=2` TOT **va** `0` XAU ⇒ **KHONG GO** (thieu 1 rate TOT, va co 1 rate XAU).

### 4.3 (b) RANG BUOC CUNG (RISK_APPETITE) — **PASS ca 2**

| tag | equity cuoi | CAGR% | maxDD% | UW | quy xau nhat% | tap trung 1 coin% | PASS |
|---|---:|---:|---:|---:|---:|---:|---|
| parity | 111 070 | 29,27 | −11,84 | 92 | −0,92 | 9,77 | **PASS** |
| F3 | 110 811 | 29,20 | **−8,87** | **164** | −0,16 | **6,98** | **PASS** |

Theo nam (maxDD% / UW / ret%):

| tag | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| parity | −2,46 / 37 / +12,21 | −11,84 / 72 / +19,58 | −2,73 / 63 / +34,96 | −6,60 / 92 / +32,14 | −4,23 / 52 / +32,71 |
| F3 | −2,63 / 44 / +9,24 | −8,87 / 73 / +18,99 | −2,56 / 65 / +38,03 | −6,66 / 119 / +37,45 | −7,28 / **164** / **+28,47** |

Khong nam nao am; maxDD moi nam <= 12% (tran 30%); UW F3 len **164** (tran 200, van PASS nhung
manh hon parity 92 — he qua co hoc cua giu lenh lau hon).

### 4.4 (c) CAPTURE RATIO — nhom dinh `maePeak HIGH >= 20% / 50% / 100%` (LEG, `trailTrace.csv`)

Mau so `peak` = `maePeak` = dinh **HIGH GIA THAT** tu leg dau — **CUNG** cho ca 2 chan.
`%trailing` = thoat bang trailing (`STOP_MARKET_DONE`) = "bi cat som"; capture = `ratePct/peakPct`.

**peak >= +20%**

| tag | n (/% tong) | %trailing | %SL | med_capture | mean_capture | agg_capture | med_gap_pp | SumPnL | pnl/leg |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| parity | 123 (11,3%) | 98,4 | 1,6 | 0,662 | 0,596 | 0,462 | 8,14 | 51 997 | 422,7 |
| **F3** | **160 (15,4%)** | 98,1 | 1,9 | **0,663** | **0,628** | **0,532** | 8,74 | **60 519** | 378,2 |

**peak >= +50%**

| tag | n (/% tong) | %trailing | %SL | med_capture | mean_capture | agg_capture | med_gap_pp | SumPnL | pnl/leg |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| parity | 29 (2,7%) | 93,1 | 6,9 | 0,406 | 0,420 | 0,353 | 64,70 | 23 049 | 794,8 |
| **F3** | **30 (2,9%)** | 90,0 | 10,0 | **0,466** | **0,469** | **0,413** | **60,31** | 20 196 | 673,2 |

**peak >= +100%**

| tag | n | %trailing | %SL | med_capture | mean_capture | agg_capture | med_gap_pp | SumPnL | pnl/leg |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| parity | 21 | 90,5 | 9,5 | 0,262 | 0,308 | 0,307 | 112,34 | 15 906 | 757,4 |
| **F3** | 21 | 85,7 | 14,3 | **0,385** | **0,374** | **0,372** | **94,30** | **13 399** | 638,0 |

**[POST-HOC — khong phai tieu chi chot]** CI block-72h cho nhom song lon (`*` = CI khong chua 0;
nhom CHON theo dinh da xay ra ⇒ co post-selection):

| nhom | n_var / n_base | `d_capture` | `d_SumPnL` |
|---|---:|---|---|
| >=20% | 160 / 123 | +0,032 [−0,022, +0,078] | +8 521 [−1 684, +19 045] |
| >=50% | 30 / 29 | +0,049 [−0,055, +0,115] | −2 853 [−8 839, +2 403] |
| >=100% | 21 / 21 | +0,066 [−0,025, +0,147] | **−2 507 [−6 057, −208]** * |

**Doc cho dung:** F3 **giu duoc nhieu hon so voi dinh** (capture trung vi tang o ca 3 nhom, ro nhat
o >=100%: 0,262 → 0,385; con cach dinh luc thoat 112 → 94 diem %) — nhung **SumPnL cua nhom >=100%
GIAM co y nghia**, va o >=20% phan **ngoai** nhom (peak < 20%) mat
`(75 812 − 60 519) − (76 070 − 51 997) = −8 779 USDT` ⇒ **tai phan phoi**, khong phai cai thien.

### 4.5 (d) PnL / EQUITY — bao RIENG (KHONG dung de chon)

| tag | equity cuoi | Δ | SumPnL toan bo | PnL/leg | meanP | CAGR | maxDD | UW | tap trung |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| parity | 111 070 | — | 76 070 | 69,85 | 5,244 | 29,27% | −11,84% | 92 | 9,77% |
| F3 | 110 811 | **−0,23%** | 75 812 | 72,97 | 5,994 | 29,20% | −8,87% | 164 | 6,98% |

Theo `level` (SumPnL / meanP / win% / TSloss%):

| level | parity | F3 |
|---|---|---|
| BIG_DOWN (248) | 16 254 / 4,786 / 88,71 / 8,47 | 17 046 / 5,851 / 89,92 / 10,89 |
| DCA_LEVEL1 | 20 → 12 701 / 52,888 / 80,0 / 10,0 | **19** → 10 210 / 63,301 / 89,5 / 15,8 |
| PREDICT_SYMBOL_TRADE | 821 → 47 115 / 4,221 / 88,31 / 10,11 | **772 (−49)** → 48 555 / 4,630 / 87,44 / 11,53 |

## 5. VI SAO harness (+20,6%) KHONG chuyen duoc sang sim — co che

Harness `RESULT_EXIT_FIT` giu **nguyen tap 1089 leg** (no replay duong thoat tren leg DA CO, khong
mo hinh lai entry). Sim that **khong** giu duoc tap do: moi symbol chi co **1 lenh chay** mot luc
(`symbol2OrderRunning`) + sizing theo equity (FIX_B3) + ngan sach/so slot ⇒ **giu lenh lau hon = chiem
symbol lau hon = it lenh moi hon**. Do la ly do toan bo phan tang theo tung lenh bi triet tieu:

| | harness (ly thuyet, tap leg co dinh) | **sim that (F3 vs parity)** |
|---|---|---|
| net/lenh | +20,6% | `meanP` +14,3% (CI chua 0) |
| so lenh | 1089 (co dinh) | **1039 (−50 = −4,6%)** |
| tong | +20,7% SumPnL | **SumPnL −259 USDT · equity −0,23%** |

=> Bai hoc lap lai (lan 4): **phan tich duong thoat tach roi entry KHONG du** — phai do tren sim
co tuong tac entry (slot/symbol/budget). Day la ket qua **co gia tri nhat** cua vong nay.

## 6. Tra loi cau hoi cua owner

> *"F3 (dinh = CLOSE) co hon baseline khong?"*

**KHONG.** Tren sim that: 1 rate TOT ngoai CI (`mP|SM` +1,40) nhung 1 rate **XAU ngoai CI**
(`TSloss%` +1,72), 5 rate con lai khong doi; **tong equity/SumPnL hoi giam** (−0,23% / −259 USDT)
vi **mat 50 lenh**; capture ratio nhom song lon **tang** nhung **SumPnL chinh nhom do giam** ⇒ la
**tai phan phoi**, khong phai cai thien. Theo dung tieu chi da chot = **NO-GO**. Ket qua la **am**
(F3 da dong), khong phai "chua du ket luan" — rate **co** doi va doi **theo ca 2 huong**.

**De xuat:** khong tich hop, khong cap them slot Kaggle cho huong nay. Ownership tam giu **T170**.
Huong con lai trong khu vuc exit/arm deu da NULL (xem `RESULT_EXIT_FIT` §3-4); muon tien thi phai
doi tang khac (entry/gate/sizing), noi du lieu phan giai manh hon.

## 7. Gioi han (ghi truoc trong pre-reg, khong phai loi chinh minh sau)
1. Kaggle sim chay `TICKER_SOURCE=file` (neo lech 1 lenh/970 vs aerospike) — **khong** anh huong so
   **giua 2 chan** (cung bundle/cua so/che do).
2. Chan F3 co **1039** lenh vs parity **1089** ⇒ CI so tren **thong ke theo cum/khoi**, khong ghep
   tung leg; hieu "mat 50 lenh" la **mot phan ket qua**, khong phai nhieu do.
3. `maePeak` (mau so capture) khong doi theo F3 ⇒ capture thap hon ve co hoc **khong** xay ra o day
   (capture F3 *cao hon*), nhung nhom la **hau-chon** theo dinh da xay ra.
4. CI o day la **block-72h** ⇒ **khong** so truc tiep voi `[−14.43, +37.64]` (block-ngay) cua harness.
5. 1 chan F3, khong quet tham so F3.

## 8. Chi phi / thoi gian Kaggle

| | |
|---|---|
| Chan chay | 3 kernel SONG SONG (`sim-pc-par`, `sim-pc-part`, `sim-pc-close`) — 3/5 slot |
| Push -> COMPLETE | ~21 phut (par/part) · ~33 phut (close) |
| JVM (Kaggle) | 1 240,3s / 1 239,3s / **1 631,5s** |
| Chi phi | **0** (Kaggle CPU kernel khong tinh quota) |

## 9. Commit (khong push) + tai san dung lai

- `1fcabe4` — prereg `docs/prereg/PREREG_PEAK_CLOSE.md`.
- `dca07ce` — code: `Configs.TS_PEAK_MODE` + `TradeUtils.peakPrice` + 3 diem goi + profile
  `x1_gs_t170_close.properties` + `PeakCloseTest`.
- commit CUOI cua vong nay (subject *result(peak-close): NO-GO*, xem `git log --oneline -1`) —
  `research/analysis/peakclose_run.py` + `peakclose_score.py` + tai lieu nay.

Tai san: `/home/ubuntu/kaggle_sim/out/{pc-par,pc-part,pc-close}/` (printDone + sim.out +
`trailTrace.csv`) + `peakclose_score.json`; dataset Kaggle `chuyendinh/sim-jar-peakclose` (jar +
profile F3); bundle `sim-x1-2021-bundle` tai dung.
