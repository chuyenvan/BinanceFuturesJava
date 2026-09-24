# PREREG_TICK_BLOCK — chan ca LUOT (tick) khi luot YEU: co giam duoc exposure khong?

Viet **TRUOC** khi chay bat ky bien the nao (chot 2026-09-23). **Khong sua thiet ke sau khi thay ket qua.**
Commit file nay PHAI co truoc commit code va truoc moi chan Kaggle (`docs/runbooks/AGENT_RUNBOOK.md` luat 2).

## 0. Cau hoi + vi sao khac "chan coin"

Bang chung da co (`docs/result/RESULT_D3D4_FILTER_SIM.md` §2, `docs/result/RESULT_SELECTOR_LEG_CUT.md` §6):

- Moi filter **cap-COIN** deu **vo hieu ve exposure**: D3 loc **4.942 candidate** nhung net chi mat
  **109 lenh** (45x). Ly do: bo qua 1 candidate thi budget/rank chuyen sang **candidate ke tiep** trong
  cung tick => thanh phan coin doi, **so lenh THAY DOI RAT IT**.
- ⇒ Muon **giam exposure that su**, phai chan **ca LUOT**: khi luot bi chan thi **khong con
  candidate nao** trong luot do duoc vao lenh (khong co gi de "thay the").
- Phu hop phat hien **edge nam o TIMING**: `RESULT_HARNESS_CONTROL.md` §3 B-SECONDARY — tai **dung
  phut MOM15 fire**, mot **symbol NGAU NHIEN** an **+2,0044%** (ALL) / **+1,0405%** (DEV) sau phi;
  A-PRIMARY tru B-SECONDARY chi con **+0,26 diem %** cho phan "chon coin". ⇒ Chon coin gan nhu khong
  them gi; **thoi diem** moi la truc.

Cau hoi cua vong nay: **chan toan bo luot o nhung luot YEU co lam TANG chat luong lenh / giam exposure
khong?** Day **KHONG** phai cau hoi chi phi (`c*` T170 = +5,244% — `RESULT_COST_LIQUIDITY`).

## 1. DINH NGHIA "LUOT YEU" — CHOT TRUOC (khong quet nguong, 1 muc cho moi chi so)

### 1.0 Gia thuyet nen + huong (chot TRUOC, co ly le truy nguon)

> **Gia thuyet H1 (huong chot):** edge cua lenh LONG la **hieu ung THOI DIEM** tap trung o nhung phut
> **xả/bán thao dien rong** (broad flush) — bang chung da cong bo `RESULT_HARNESS_CONTROL.md` §3
> (B-SECONDARY +2,00% o ALL / +1,04% o DEV, harness da duoc hieu chuan positive-control §1).
> ⇒ Nhung luot **KHONG co ap luc ban rong** ("**luot nguoi**") **khong co timing edge**; lenh vao o do
> la **nhieu**.

⇒ **Voi CA BA chi so, "nhom te nhat" = nhom NGUOI** (nhanh it ap luc ban nhat):
`rateDownAvg`/`rateDown15MAvg` **it am nhat** (truc tiep: "calm"), `breadth` **thap nhat** (gian tiep:
it coin rớt manh).

Ghi ro de trung thuc: gia thuyet **doi lap** (H0': "luot nong moi yeu" — vao lenh giua luc thi truong
xả la bat dao roi) **KHONG duoc kiem** trong vong nay, va **khong duoc chay sau** khi thay so. No la mot
pre-reg RIENG cho vong sau neu ket qua nay am.

### 1.1 Ba chi so (k = 3, moi chi so MOT muc cat 25%, KHONG quet)

| # | mode | chi so `x(t)` | nguon | tinh CAUSAL tai thoi diem quyet dinh | te nhat = | luat chan |
|---|---|---|---|---|---|---|
| **V1** | `DEPTH` | `rateDownAvg` (trung binh 100 rate 1M **am nhat**) | `market.bin` (`time2MarketData`), **dung nguyen** gia tri sim da doc | co (la field cua phut t) | it am nhat | chan khi **`x >= Q0.75`** |
| **V2** | `BREADTH` | `100 × #{1M return <= -3%} / #{ticker con song, gia hop le}` | tinh TRONG tick tu `symbol2Ticker` (cung nguon `calMarketData` dung) | co | thap nhat | chan khi **`x <= Q0.25`** |
| **V3** | `DROP15M` | `rateDown15MAvg` (do sau drawdown 15M, TB 100 rate max-to-now) | `market.bin` | co | it am nhat | chan khi **`x >= Q0.75`** |

- `1M return = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) = (close-open)/open` (dung quy uoc
  cua `MarketBigChangeDetector.calMarketData`). `rateDownAvg`/`rateDown15MAvg` la **so AM**, cang am =
  cang nong.
- **V2 loc ticker "con song"** giong `calMarketData`: bo ticker `null`, bo `!Utils.isTickerAvailable(ticker)`,
  bo symbol co ten nam trong `Constants.diedSymbol` (tra ten qua `SimpleSymbolMapper`). Khong backfill,
  khong bia gia.
- **V3 la alias market-level cua tin hieu dang chay live** (`MOM15 = rateDown15MAvg < -0,028`,
  `RESULT_HARNESS_CONTROL.md` §6.1).
- Neu `marketData == null` tai phut do ⇒ `x` khong xac dinh ⇒ **khong chan** (va khong ghi vao cua so).

### 1.2 Nguong cat — CAUSAL, don dieu, khong nhin tuong lai

- Cua so = **30 ngay lich TRUOC** (moi phut da xu ly cua cac ngay `D-30 .. D-1`).
- Nguong `Q` duoc **tinh lai 1 lan moi ngay UTC**, tai phut dau tien cua ngay `D`, tu du lieu **cua cac
  ngay TRUOC D**. Du lieu cua chinh ngay `D` **khong bao gio** vao nguong cua no.
- **Warm-up**: chua du **20.160 mau hop le** (~14 ngay) thi **khong chan** (nguong = null).
- Vi cua so sim bat dau `2021-07-01`, chan thuc te bat dau tu khoang `2021-07-15`.
- Muc cat **25% co dinh cho ca 3 chi so**; **KHONG quet** 20/30/33/40…; **KHONG** chon lai huong sau khi
  thay so.

### 1.3 Pham vi chan = TOAN BO LUOT (khong phai chi 1 leg)

Tai phut `t` bi chan, **ca 4 duong vao lenh** deu bi chan (khong duong nao duoc thay the):

| # | duong (file:dòng, `SimulatorMarketLevelTicker1MStopLoss.java`) | level | bi chan? |
|---|---|---|---|
| 1 | market-signal `symbol2BUY` (`:334-353`) | `BIG_DOWN` | **CO** |
| 2 | DCA trong khoi `levelChange` (`:355-360`) | `DCA_LEVEL1` | **CO** |
| 3 | DCA khoi `isDcaAlt` (`:365-380`) | `DCA_LEVEL1` | **CO** |
| 4 | SELECTOR `time2SymbolPred` (`:384-431`, gom nhanh `DCA_SIGNAL_GATE`) | `PREDICT_SYMBOL_TRADE` | **CO** |

**KHONG** chan: vong cap nhat/thoat lenh dang mo (`:214-241`), `logByProcessTime`, cap nhat balance,
`TickDecisionLog`, `dsReserved` bookkeeping (chi la dat truoc, khong tao lenh). => Chan luot
**khong the** lam doi mot quyet dinh **thoat** nao.

### 1.4 Co moi + profile key (chot TRUOC ten key)

| key | mac dinh | nghia |
|---|---|---|
| `SIM_TICK_BLOCK_IND` | *(khong khai = OFF)* | `DEPTH` \| `BREADTH` \| `DROP15M` |
| `SIM_TICK_BLOCK_PCT` | `25` | kich thuoc duoi bi chan (%) |
| `SIM_TICK_BLOCK_WIN_DAYS` | `30` | do dai cua so cuon (ngay) |
| `SIM_TICK_BLOCK_MIN_SAMPLES` | `20160` | warm-up (so mau hop le toi thieu) |
| `SIM_TICK_BLOCK_DROP1M` | `-0.03` | nguong "rớt manh" cho V2 |

**OFF (key khong khai)** ⇒ `tickBlocked` luon `false` ⇒ **khong mot dong nao doi** ⇒ byte-identical
(day la cong parity cua §3). Moi key `SIM_*` la **tham so GIAO DICH** (dat qua profile, env se fail-fast
theo `Cfg`).

## 2. Cong chan (BUOC 0, bat buoc) — lam TRUOC

T170 nguyen ban (`profile x1_gs_t170`, bundle `sim-x1-2021-bundle`, `SIM_END_DATE=20251231`,
`TICKER_SOURCE=file`) phai ra `printDone.csv` md5 **`efb793e2468ca3a7318da0f0ad23d4fc`** (n=1089).
Khong dat ⇒ **DUNG, khong chay bien the** (chay tren nen sai se ra so vo nghia khong bao loi).
Vi vong nay **co doi CODE**, cong phai chay **bang jar MOI** voi co OFF (§3.1).

## 3. Chan chay (k = 3 bien the + 2 cong)

| tag | mode | doi gi |
|---|---|---|
| `tickblk-par` | OFF | **jar MOI**, `SIM_TICK_BLOCK_IND` khong khai ⇒ md5 phai `efb793e2…` |
| `tickblk-depth` | `DEPTH` | `SIM_TICK_BLOCK_IND=DEPTH` |
| `tickblk-breadth` | `BREADTH` | `SIM_TICK_BLOCK_IND=BREADTH` |
| `tickblk-drop15` | `DROP15M` | `SIM_TICK_BLOCK_IND=DROP15M` |

Cung bundle, cung cua so (`SIM_END_DATE=20251231`), DEV `2021-07-01..2025-12-31`, **KHONG dung 2026**
(seal). Tat ca chay **tren Kaggle CPU kernel** (khong chay Java sim tren Oracle — `shadow-c3` dang chay),
**khong** `claude-run`/Claude Code, **khong push**.

### 3.1 Cong parity RIENG cho jar moi (bat buoc)
Jar moi + co OFF ⇒ `printDone.csv` phai **byte-identical** `efb793e2468ca3a7318da0f0ad23d4fc`.
Chi khi cong nay PASS moi doc so cua 3 bien the. Kernel in `JAR_SHA256=` (luu vao `result.json`).

## 4. Cham diem (chot TRUOC)

### 4.1 PRIMARY — 5 rate chat luong (toan bo leg), moi bien the vs `tickblk-par`
`n`, `win%`, `TSloss%`, `mP|SM` (mean profit lenh `STOP_MARKET_DONE`), `mP|SL` (lenh `STOP_LOSS_DONE`),
`meanP`. "Tot" = `win%`/`mP|SM`/`mP|SL`/`meanP` **TANG**, `TSloss%` **GIAM** (`docs/runbooks/RISK_APPETITE.md`).

### 4.2 CI (chot TRUOC — bao CA HAI do rong)
Bootstrap **block-72h**, paired resample theo block, **2000 rep**, **seed `20260905`**
(`research/analysis/c3_rates.py`: `BLOCK_H=72`, `NREP=2000`, `SEED=20260905`), neo block CO DINH
`2021-07-01` cho moi arm (nhu `selcut_score.py`). Hai do rong:

1. **`x1.21`** — he so **cu**, muc brief yeu cau (rong hon `inflate(3)` nen la PRIMARY chat hon);
2. **`inflate(3) = sqrt(2 ln 3) = 1,4822`** — he so chuan hoa cho **k = 3 ung vien**
   (`docs/audit/AUDIT_CI_INFLATE_STANDARDIZATION.md`).

`rate ngoai CI` chi duoc tinh khi ngoai CI o **CA HAI** do rong. **KHONG** chon do rong theo ket qua.

### 4.3 Rang buoc CUNG (`docs/runbooks/RISK_APPETITE.md`, do tu `sim.out` + `printDone.csv`)

| rang buoc | nguong |
|---|---|
| maxDD theo NAM | **<= 30%** |
| UW (ngay underwater dai nhat) | **<= 200** |
| quy xau nhat | **>= -15%** |
| nam am | **KHONG** (tuyet doi) |
| tap trung 1 coin | **<= 15% equity** (`conc_max`: tong margin cum / equity ngay mo, quy uoc `selcut_score.py`) |

### 4.4 Do exposure (cau hoi chinh cua vong nay)

- **% luot bi chan** = so phut bi chan / so phut da xu ly (counter `[TICKBLK]` trong `sim.out`).
- **So lenh mat**: (a) **net** = `n(parity) - n(bien the)`; (b) **gross** = so lenh cua parity co
  `start` roi vao **phut bi chan** (doi chieu file `storage/tickblk_blocked_min.csv` do sim ghi).
- Bang theo level (`PREDICT_SYMBOL_TRADE` / `BIG_DOWN` / `DCA_LEVEL1` / ALL): n, SumPnL, meanP, win%, TSloss%.
- **PnL/equity bao RIENG** (equity cuoi, CAGR, tong PnL) — **KHONG dung de chon**.

## 5. Luat ket luan (chot TRUOC, khong noi)

> **GO** cho mot bien the ⇔ **>= 2/5 rate ngoai CI (ca hai do rong) theo huong TOT** **VA** het rang buoc
> cung **VA** **khong rate nao XAU ngoai CI** (ca hai do rong).
> Chi "it PnL hon / equity thap hon" ⇒ **NULL** (khong duoc dien giai la "tot hon").
> Neu **chi 1 bien the** dat ⇒ **UNCONFIRMED** — khong ap dung (chua hoi tu giua cac chi so).
> Neu **0 bien the** dat ⇒ **NULL / NO-GO**, giu T170.
> KHONG duoc: doi muc cat, doi huong, doi chi so, doi pham vi chan, them bien the sau khi thay so.

## 6. Tai nguyen du kien

4 chan Kaggle (3 bien the + 1 cong jar), chay song song (tran 5 slot). Do dai tham chieu vong
`selcut` tren cung bundle: JVM 750–1.280s/chan, kernel ~25–35′/chan. **Chi phi 0** (CPU kernel khong
tinh quota). V2 `BREADTH` quet them ~900 ticker/phut ⇒ du kien **+1-2 phut JVM** (do va ghi lai).

## 7. Vat lieu vong nay KHONG dung (ghi de khong bi coi la bo sot)

- **Khong chay 2026** (seal), khong chay VALIDATION rieng, khong rebuild bins, khong sua
  `predwf_map_s1a2_x1`, khong doi exit/sizing/gate.
- **Khong** kiem H0' ("luot nong moi yeu") o vong nay.
- **Khong** ket luan ve HPO/tham so (muc cat 25% la **chot truoc**, khong phai nguong toi uu).
