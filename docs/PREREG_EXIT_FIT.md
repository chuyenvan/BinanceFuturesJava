# PREREG_EXIT_FIT — Do HAM GAP THOAT tu DU LIEU (replay harness offline, thuan Python)

Viet **TRUOC** khi lam bat ky buoc nao (chot 2026-09-23). **Khong sua thiet ke sau khi thay ket qua.**
Nguon: brief Uni 2026-09-23 (*"co nen do tren du lieu roi ra cong thuc khong"*) + tien le
`docs/RESULT_TRAIL_HINGE.md` (doi tran PHANG ⇒ NULL) + `docs/RESULT_TRAIL_LADDER.md` (doi HINH DANG
ham gap sang bac thang ⇒ NULL).

## 0. Cau hoi

Exit hien tai = arm `+7%` + `gap = min(peak × TS_GIVEBACK_RATIO(0.5), maxGap)`, `maxGap` = tran PHANG
`TS_MAX_GAP_WEAK=0.03` (yeu, `pNoPump>0.29`) / `TS_MAX_GAP=0.08`; ratchet LIEN TUC; dinh = **HIGH** nen 1m.
Hai lan thu doi CON SO va doi HINH DANG (bac thang) deu NULL ⇒ cau hoi: **co the FIT cong thuc gap truc
tiep tu du lieu khong, va neu co thi co hon baseline out-of-sample khong?**

## 1. Rang buoc (chot)

1. **Khong** dung claude-run/Claude Code. 2. **Khong** chay Java/sim tren Oracle ⇒ vong nay **thuan
Python offline** (khong can sim). 3. DEV only (`2021-07..2025-12`), **khong 2026**. 4. Ket qua trung gian
ghi ra **ngoai repo** (`/home/ubuntu/exitfit/`) de resume duoc. 5. **Khong push**.

## 2. BUOC 1 — Replay harness + CONG PARITY (chot TRUOC)

### 2.1 Du lieu vao
- Lenh: `devrun/X1_GS_T170_2021/storage/printDone.csv` (n=**1089** leg) — CHI dung `sym/start/end/status/
  entry/quantity/pnl/funding/symbolPred/level` (khong dung tham so nao khac).
- 1m OHLC: `kaggle_data_hpo/daily/ticker_YYYYMMDD.bin.gz` (**cung nguon `TICKER_SOURCE=file`** ma sim
  T170 da doc) doc bang `research/analysis/jbin.py` (parser Java-serialization thuan Python da co).
  Truong duoc xac minh bang thuc nghiem: tuple = `(startTime, HIGH, LOW, close, open, totalUsdt)`.
- Tick size: `/home/ubuntu/java/exchange_info_pin.json` (cung file pin sim da dung).
- Profile T170 (`profiles/x1_gs_t170.properties`): arm `SIM_RATE_PROFIT_STOP_MARKET=0.07`,
  `SIM_TS_GIVEBACK=1`, `SIM_LOSER_TIME_STOP_HOURS=168`, `TS_GIVEBACK_RATIO=0.5`,
  `SIM_APPLY_FUNDING=true`, `SIM_FUNDING_MARK=true`, `DCA_GRID_ENABLED=true`; `TS_MAX_GAP=0.08`,
  `TS_MAX_GAP_WEAK=0.03`, `TS_PNOPUMP_WEAK_THR=0.29`, `TS_CAP_STRONG_RANK=0` (mac dinh).

### 2.2 Engine replay (mo phong dung duong thoat T170)
Leg → **cum** theo `(sym, end)`: cac leg cung `sym` va cung `end` la mot cum (sim chi cho 1 cum/symbol).
Trang thai cum: `priceEntry` (binh quan theo volume khi merge), `quantity` (tong), `minPrice`, `maePeak`,
`priceSL` (reset ve `null` khi merge — dung code), `timeStart` (= leg cuoi), `clusterFirstLegTime`
(= leg dau), `symbolPred` (leg dau khac null dau tien — FIX_B1), `status`.

Moi nen 1m `t > timeStart` cua symbol (bo qua nen thieu):
1. `updatePriceByKlineSimple`: `lastPrice=close`; `minPrice=min(minPrice, low)`; `maePeak=max(maePeak, high)`;
   `timeUpdate=t`.
2. **LOSER TIME-STOP**: `priceSL==null` va `t-anchor > 168h` (`anchor=clusterFirstLegTime||timeStart`)
   ⇒ `STOP_LOSS_DONE`, gia chot `min(open, close)`.
3. **Cong arm**: `high >= entry×(1+0.07)` **hoac** `priceSL != null`:
   - `updateStatusNew`: neu `priceSL==null`: `rateLoss=(high-entry)/entry`; `rateLoss > 0.07` ⇒
     `rateSL=trailRate(rateLoss)`, `priceSL=normalizeFloor(entry×(1+rateSL))`, `minPrice=close` ⇒ **return**
     (`BLOCK_INTRABAR_LOOKAHEAD=true`, khong khop noi nen). Nguoc lai (da co SL): `minPrice <= priceSL` ⇒
     `priceSL>entry ? STOP_MARKET_DONE : STOP_LOSS_DONE`, gia chot `min(priceSL, open)`.
   - dong cum neu status != REQUEST; khong thi `updateTPSL`: `rateLoss >= 0.07` ⇒ ratchet khi
     `priceSLNew > priceSL` **va** `priceSLNew > entry` (bat bien SL>entry), `minPrice=close`.
4. **Delist guard** (moi 60'): `timeUpdate < t-2 ngay` ⇒ `STOP_LOSS_DONE` tai `lastPrice`.
- `trailRate` baseline = `trailFromCap`: `gap=min(peak×0.5, maxGap)`, `rate=peak-gap`, lam tron buoc `0.005`.
- `normalizeFloor` = `floor(price/tickSize)×tickSize` (BigDecimal floor, scale = tick scale) — nhu
  `ClientSingleton.normalizePrice`. So hoc float **float32** (numpy) cho moi buoc.
- PnL 1 leg: `qty×(priceTP-entry) − qty×entry×0.002 − qty×entry×0.003×2 − funding` (`funding` lay tu CSV).
- Ngay thieu <1440 phut bi sim SKIP ⇒ harness cung SKIP.

### 2.3 Cong PARITY (PASS/FAIL, chot TRUOC)
So tung **leg** (n=1089). So sanh replay vs `printDone.csv`:
| chi tieu | nguong PASS |
|---|---|
| `status` trung khop | ≥ **99.0%** so leg |
| thoi diem thoat (phut) trung khop tuyet doi | ≥ **97.0%** so leg |
| thoi diem thoat lech <= **2 phut** | ≥ **99.0%** so leg |
| gia chot `priceTP` (`tp`) trung khop (sai so <= 1 tick) | ≥ **95.0%** so leg |
| PnL **khong funding** (`pnl + funding` cua CSV vs replay): trung vi \|Δ\| | **≤ 0.02 USDT** |
| PnL **khong funding**: ti le \|Δ\| ≤ 1.0 USDT | ≥ **95.0%** so leg |

**Neu BAT KY dong nao FAIL ⇒ DUNG, bao RO, KHONG fit tren harness sai.** Mismatch duoc liet ke ra file
ngoai repo, co phan loai ly do (khong duoc sua nguong sau khi xem).

## 3. BUOC 2 — Fit co ky luat (chot TRUOC)

### 3.1 Split (theo `start` cua leg, gio GMT+7)
- **TRAIN** = `2022-01-01 .. 2023-12-31`; **TEST** = `2024-01-01 .. 2025-12-31`.
- `2021-07..2021-12` = **burn-in**, KHONG dung de chon (chi bao cao tham khao). Khong tron TEST vao bat cu
  buoc chon nao.

### 3.2 Ho policy (moi policy chi doi HAM GAP; arm=0.07, ratchet lien tuc, dinh HIGH, 168h, SL>entry giu nguyen)
| ma | cong thuc | tham so | so luong |
|---|---|---|---|
| `P0` | `gap = min(peak×0.5, 0.03/0.08 theo pNoPump)` (baseline) | — | 1 |
| `F1a_b` | `gap = min(peak×0.5, a + b×peak)` | `a∈{0.005,0.01,0.02}` × `b∈{0,0.15,0.30}` | 9 |
| `F2c_k` | `gap = min(peak×0.9, c×ATR_k)`; `ATR_k` = trung binh `(high-low)/close` cua `k` nen **truoc** nen hien tai (causal) | `c∈{0.5,0.75,1.0}` × `k∈{60,240}` | 6 |
| `F3` | nhu `P0` nhung dinh do bang **CLOSE** (max close tu entry; arm cung theo close-max) | — | 1 |

⇒ **Tong so policy se thu = 17** (1+9+6+1). Bao cao multiplicity = **17**. Khong them policy nao sau khi
xem TEST (neu them ⇒ ghi ro la post-hoc, khong tinh la ket qua).

### 3.3 Chon policy + bao cao
- Chon tren **TRAIN** theo `net/trade` (cao nhat), hoa bang `SumPnL`. **Khong** dung TEST de chon.
- Bao cao **out-of-sample** (TEST) cho policy duoc chon: n leg, net/trade, meanP, win%, TSloss%,
  capture ratio theo nhom dinh (`peak >= 20% / 50% / 100%`), va `SumPnL`.
- Bao cao them **ca 17 policy tren TEST** (minh bach multiplicity; cong bo ro day la bang day du, khong
  phai bang de chon).

### 3.4 Ket luan (chot TRUOC)
- "**Hon co y nghia**" = policy duoc chon (theo TRAIN) co `net/trade` TEST > `P0` VA CI bootstrap theo
  **block ngay** (1000 rep, seed `20260923`, block = 1 ngay) cua hieu `policy − P0` **khong chua 0**.
- Neu hon ⇒ de xuat **1 sim xac nhan tren Kaggle** (ghi ro can profile/jar/bundle nao), **khong** tu tich hop.
- Neu khong hon ⇒ **NULL**, ket luan co nen di tiep huong fit hay khong.

## 4. Gioi han da biet (ghi TRUOC, khong phai loi chinh minh sau)
1. Replay **khong** mo phong lai entry/sizing/von: dung dung tap leg cua T170 ⇒ `SumPnL` la **tong PnL
   cac leg**, KHONG phai duong equity (khong compound, khong doi so lenh).
2. **Funding** bi loai khoi moi so sanh (nguon rate funding khong co offline; xem §2.2). Funding phu thuoc
   thoi diem dong lenh nen khac biet giua cac policy la bac 2 — sai so nay duoc bao cao.
3. Replay bo qua moi co che entry (`SIM_GATE_DYN_SCALE`, selector, budget) — khong lien quan duong thoat.
4. Parity chi manh bang **tap leg T170**; harness la tai san dung lai duoc, khong phai bang chung cho
   profile khac.
