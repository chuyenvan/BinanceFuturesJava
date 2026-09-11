# PREREG_FLATGATE — do chien luoc GATE PHANG (cai 242 dang chay that) tren 48 thang

> **Commit TRUOC khi chay.** Khong sua file nay sau khi thay so. Null co tinh thong tin.
> Nen: `docs/AUDIT_GATE_DYN_PARITY.md` (3a36f02) muc 5.2 huong **C**.
> Khung cham: `docs/PREREG_X1.md` muc 4-7 + `docs/AGENT_RUNBOOK.md` muc 0.

## 0. DOC TRUOC — day KHONG phai mot ung vien adopt

Run nay **khong** de tim chien luoc tot hon. No de tra loi mot cau hoi da mo tu audit:
**chien luoc dang chay THAT tren 242 (gate PHANG 0.008, khong dyn) co gia tri lich su gi
tren 48 thang?** Ket qua **khong duoc** dung de "chon gate phang" du no co thang. Neu no
thang ro thi do la **bat ngo can audit them**, khong phai giay phep doi gate (muc 7).

Ly do ton tai: audit 3a36f02 chung minh sim LUON goi `checkSignalDynamic` cho
`PREDICT_SYMBOL_TRADE` (`SimulatorMarketLevelTicker1MStopLoss.createOrder:964-965`) con live
**bo qua** no khi `SELECTOR_RANK_TOPK>0` (`DetectEntrySignal2TradeNormal:656`, commit `311bb29`).
`dyn_thr = 0.008 * max(0.26787, symbolPred/0.15 * 1.28760)`; `symbolPred` top-8 = 0.25-0.35
=> nguong sim 0.0172-0.0240 = **2.1-3.0 lan** nguong phang. Do offline: **95.62%** slot top-8
ma gate phang cho qua thi gate dyn CHAN; tren so giay 242 07-11/09: **77/78** entry bi chan.
=> `X1_C3_FULL_PARITY_R` (equity 111,428 / n 2,266) la so cua chien luoc **CO** gate dyn;
so giay 242 la chien luoc **gate PHANG — CHUA TUNG duoc backtest**. Run nay lap khoang trong do.

## 1. CAU HOI (mot cau, khong them)

Tren cung dataset / cung bins / cung cua so 2022-01-01..2025-12-31 / cung moi tham so khac,
**doi DUY NHAT gate tang 2 tu dong (dyn) sang phang (flat 0.008)** thi 5 rate chat luong,
rang buoc cung theo nam, va co hoc (nhip vao lenh, von khoa, vi the mo) doi the nao so voi
`X1_C3_FULL_PARITY_R`?

## 2. CO CHE — key moi `SIM_GATE_DYN_BYPASS`

- Doc qua `Cfg.getOr("SIM_GATE_DYN_BYPASS", "0")` (cong Cfg bat buoc, `tools/check_cfg_gateway.sh`).
  Tien to `SIM_` => la **tham so giao dich** => phai khai trong profile, khong duoc dat qua env.
- Hang so: `Configs.GATE_DYN_BYPASS`.
- **Khong khai / `0` = TAT**: nhanh `checkSignalDynamic` giu nguyen => **byte-identical HEAD**.
- **`1` = BAT**: trong `createOrder`, voi `levelChange == PREDICT_SYMBOL_TRADE`, KHONG goi
  `checkSignalDynamic` nua, de `filterResult` roi xuong `checkSignal(predict)` = nguong phang
  `thres15M(t)` = `SIM_MIN_MOMENTUM_15M` = **0.008**. Day la **dung** duong live rank-mode.
- Pham vi: chi tang 2 cua sleeve `PREDICT_SYMBOL_TRADE`. `BIG_DOWN` da o ngoai khoi `if`,
  `DCA_LEVEL1` va moi leg khac van di `checkSignal` nhu cu => **khong doi**.
- Tang 1 selector (`maxThres`/`SELECTOR_RANK_TOPK`) **khong cham**. Bins, dataset, exit,
  sizing, DCA, breaker **khong cham**.
- `TickDecisionLog` khong doi: `D_GATE_REJECT` van ghi o dung cho cu (chay khi `TICKLOG=1`,
  mac dinh TAT o ca hai run => khong anh huong byte-identical).

## 3. DUNG MOT BIEN THE — `X1_C3_FULL_FLATGATE`

`profiles/x1_c3_full_flatgate.properties` = **ban sao y nguyen** `profiles/x1_c3_full.properties`
+ **mot dong** `SIM_GATE_DYN_BYPASS=1`. Khong them/bot key nao khac.
Khong sweep, khong bien the phu => khong co bai toan multiple-comparison (k=1).

| | nen | bien the |
|---|---|---|
| tag devrun | `X1_C3_FULL_PARITY_R` | `X1_C3_FULL_FLATGATE` |
| profile | `x1_c3_full.properties` | `x1_c3_full_flatgate.properties` |
| gate tang 2 (PST) | `checkSignalDynamic` (dyn) | `checkSignal` (phang 0.008) |
| moi thu con lai | | **giong het** |

Neo nen: `devrun/X1_C3_FULL_PARITY_R/storage/printDone.csv` md5 **`2478e90d4e6147bf4cc64f75967ef47d`**
(ca file, 2,267 dong ke header); bo header md5 `e13bc39e625b8d2ceebb7b9194f7f4f0`; n = **2,266** lenh;
equity cuoi (b+unP) **111,428**.
Cua so **2022-01-01..2025-12-31**, dataset `/home/ubuntu/wfo_ds_x1` (dung lai, KHONG build lai),
bins `predwf_map_s1a2_x1` (16 fold) — **khong doi**.

## 4. CONG NGHIEM THU — chay TRUOC khi doc bat ky so nao cua FLATGATE

Jar moi phai chung minh key TAT = khong doi hanh vi:

1. Build `mvn -DskipTests -o package`, `tools/check_cfg_gateway.sh` phai OK.
2. Chay jar **moi** voi profile **`x1_c3_full.properties`** (khong khai key) -> dir
   `devrun/X1_C3_FULL_FLATOFF`.
3. `cmp` phan **bo header** cua `FLATOFF/storage/printDone.csv` voi `PARITY_R/...` phai **rc=0**,
   va `md5sum` ca file phai **khop `2478e90d...`**.
4. FAIL => **DUNG**, khong chay FLATGATE, bao cao.

Va mot cong nguoc chieu: `printDone.csv` cua FLATGATE phai **KHAC** `PARITY_R`
(md5 giong = key khong an => run vo nghia).

## 5. CHAM DIEM — co dinh truoc

### 5.1 Rate + CI khoi 72h x1.21 (`x1_rates.py`)
`python3 research/analysis/x1_rates.py X1_C3_FULL_PARITY_R X1_C3_FULL_FLATGATE`
- 5 rate chat luong: `win%` · `TSloss%` · `mean(profit|STOP_MARKET)` · `mean(profit|STOP_LOSS)` ·
  `mean(profit)`. `n` va `mean(margin)` la bien **KIEM SOAT/co hoc**, KHONG phai bang chung.
- CI: paired block-72h bootstrap, 2000 rep, seed 20260905, nhan **1.21** (`docs/PREREG_CI.md`).
- Bao **toan cua so** va **tung nam** 2022/2023/2024/2025. Khong cherry-pick nam.

### 5.2 Rang buoc cung — TUYET DOI, tung nam (`x1_rates.py` muc `hard_by_year`)
`maxDD <= 15%` · `underwater <= 120 ngay` · **khong nam nao am** · **khong quy nao < -5%**.
Vo bat ky muc nao o bat ky nam nao = **vo rang buoc**, khong tune, khong doi nguong.

### 5.3 d CAGR tren equity NGAY mark-to-market (`research/analysis/ci_flatgate.py`)
Khuon `research/analysis/ci_bookcap.py`, giu nguyen: equity ngay = `b + unP` doc tu
`logs/sim.out` (ban ghi cuoi trong ngay), moving-block circular bootstrap **block 21 ngay**
(kiem do ben o 10 va 42), **2000 rep**, **seed 20260903**, `CAP0 = 35000`.
**k = 1 bien the khoa truoc** => `sqrt(2 ln 1) = 0` la nguong VO NGHIA, **khong dung**.
Thay vao do: bao **`d CAGR` + CI95 hai phia** (percentile 2.5/97.5) toan cua so va tung nam.
`maxDD`/`underwater` la **QUAN SAT**, khong bootstrap (`PREREG_CI` 2.5).

### 5.4 CO HOC — bao bat buoc, dan nhan "mo ta, khong phai tieu chi"
- **so lenh/nam** va **entries/ngay** (moc doi chieu: `PARITY_R` = 1.37 entry PST/ngay;
  so giay 242 07-11/09 = **17.0 entry/ngay**).
- **vi the mo max / p90** theo nam, **von khoa** (notional mo / equity).
- **collapse-day** = ngay co >= 4 lenh dong `STOP_LOSS_DONE` (dinh nghia `DEV_COLLAPSE_CHECK`).
- **pnl ngay te nhat** + ngay do, theo nam.

## 6. QUY TAC DOC — CHOT TRUOC KHI THAY SO

Chi ba ket luan duoi day duoc phep. Khong co lua chon thu tu.

| ket luan | dieu kien |
|---|---|
| **A. Gate phang TE HON RO** | `d CAGR` CI95 **tren < 0** (toan cua so), **HOAC** vo rang buoc cung muc 5.2 o bat ky nam nao ma nen `PARITY_R` khong vo |
| **B. Khong phan biet duoc** | CI95 cua `d CAGR` chua 0 **VA** ca hai qua/vo rang buoc nhu nhau **VA** < 2 rate chat luong ngoai CI cung huong |
| **C. Gate phang TOT HON RO** | `d CAGR` CI95 **duoi > 0** **VA** qua toan bo rang buoc cung 4/4 nam **VA** >= 2 rate chat luong ngoai CI cung huong |

**Neu ra C**: ghi la **BAT NGO CAN AUDIT THEM**, KHONG adopt, KHONG doi gate, KHONG sua sim.
Ly do: (i) day la phep do MO TA mot chien luoc dang chay, khong phai ung vien da qua pre-reg
lua chon; (ii) gate phang cho qua ~23 lan so co hoi entry nen ket qua se bi chi phoi boi
**ngan sach/`isSymbolRunning`** chu khong phai chat luong tin hieu — mot co che chua duoc
mo hinh hoa la "edge"; (iii) 2025 (regime mot chieu) co the mot minh keo ca cua so.
=> C chi mo ra mot job audit moi, master chot.

**Neu ra A hoac B**: ghi ro, va van **KHONG** tu sua sim/live. Quyet dinh huong A/B cua audit
muc 5.2 la cua master.

## 7. DU DOAN GHI TRUOC (bat buoc, de kiem chinh minh)

Ghi 2026-09-11, truoc khi chay:

1. **Ket luan se la A (te hon ro).** Xac suat toi dat: **~75%** A / ~20% B / ~5% C.
2. **`n` tang manh**: doan **8-15 lan** so lenh cua `PARITY_R` (2,266 -> ~18,000-34,000).
   Co so: slot dyn/flat = 23x offline, nhung ngan sach + `isSymbolRunning` + gop leg se cat
   bot; nhip live do duoc la **12x**. Doan nay la bien KIEM SOAT, khong phai bang chung.
3. **`mMargin` GIAM manh** — lap lai dung pattern da thay o `5MGRID` va `K12`:
   "nhieu lenh hon => von chia nho hon => `mMargin` tut". Doan giam **>= 60%**.
4. **`win%` giam va `TSloss%` tang**: gate phang lay ca duoi 4% duoi cung cua phan phoi `p15`,
   la phan chua tung co bang chung edge. Doan `win%` **-4..-10pp**, `TSloss%` **+4..+10pp**.
5. **Rang buoc cung VO o >= 2 nam**, kha nang cao nhat o **2022** (bear) va **2025**
   (universe no 2.2 lan, `DEV_COLLAPSE_CHECK` da do 2025 co `pnl_SL/pnl_SM = 86%`).
6. **Von khoa va vi the mo tang manh** => equity bi giam do nam giu, khong do exit.
7. Neu 2025 mot minh duong con 2022-2024 am thi doc la **regime**, khong phai edge.

## 8. CAM / KHONG LAM

Khong push. Khong sua selector, bins, dataset, cua so. Khong tune sau khi thay so.
Khong xoa devrun cua nguoi khac. Khong cham 242, khong deploy. Khong mo holdout 2026.
Python dung `logging`, Java dung SLF4J. Khong chay song song voi JVM khac tren Oracle.

## 9. TAI LAP

```
cd /home/ubuntu/src/BinanceFuturesJava && mvn -DskipTests -o package && tools/check_cfg_gateway.sh
# cong nghiem thu (key TAT)
bash research/pipeline/x1/run_flatgate.sh FLATOFF
# bien the
bash research/pipeline/x1/run_flatgate.sh FLATGATE
python3 research/analysis/x1_rates.py X1_C3_FULL_PARITY_R X1_C3_FULL_FLATGATE
python3 research/analysis/ci_flatgate.py X1_C3_FULL_FLATGATE
```
Env run (y `runx` cua `research/pipeline/x1/run_x1_sim.sh`):
`WFO_DATA_DIR=/home/ubuntu/wfo_ds_x1 WFO_SMART_CACHE=1 SIM_END_DATE=20251231
EXCHANGE_INFO_PATH=/home/ubuntu/java/exchange_info_pin.json TRADING_PROFILE=<profile>`,
`java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx16g -cp target/binance-java-sdk-1.2.4.jar
com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss`.
