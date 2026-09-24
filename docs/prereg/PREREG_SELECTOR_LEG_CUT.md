# PREREG_SELECTOR_LEG_CUT — cắt / giới hạn leg SELECTOR: có giải phóng khóa symbol cho BIG_DOWN + DCA không?

Viet **TRUOC** khi chay bat ky bien the nao (chot 2026-09-23). **Khong sua thiet ke sau khi thay ket qua.**
Nguon: brief cua Uni 2026-09-23 + `docs/result/RESULT_COST_LIQUIDITY.md` (so lieu T170 theo level).

## 0. Cau hoi + gia thuyet

Trong T170 (`X1_GS_T170_2021`, DEV 2021-07-01..2025-12-31, 1089 lenh):

| level | n lenh | meanP |
|---|---:|---:|
| `PREDICT_SYMBOL_TRADE` (leg do **selector** dan dat) | **821 (75,4%)** | **+57,39** |
| `BIG_DOWN` (leg market-signal) | 248 | +65,54 |
| `DCA_LEVEL1` | **20** | **+635,06** |

Gia thuyet: leg selector **chiem het khóa symbol** (`symbolLocked` = `activeRunningIds`) nen `BIG_DOWN`
va `DCA_LEVEL1` — hai nhom co `meanP` CAO hon — khong the vao lenh. Cat/gioi han leg selector =>
**giai phong khoa cho BIG_DOWN/DCA** => he tot hon ve CHAT LUONG (`meanP`) va RUI RO.

**KHONG phai cau hoi chi phi**: `c*` cua T170 = +5,244%, selector = +4,221% (`RESULT_COST_LIQUIDITY`) ⇒
chi phi khong phai nut that. Day la cau hoi **PHAN BO VON / KHOA SYMBOL**.

## 1. Co che trong code (kiem TRUOC, ghi ro file:dong)

Entry cua sim nam o `research/SimulatorMarketLevelTicker1MStopLoss.java`, 3 duong doc lap trong 1 tick:

| # | duong | dong | level ghi ra | co bi khoa symbol khong |
|---|---|---|---|---|
| 1 | **market-signal** `symbol2BUY = getTopSymbolArray(...)` → `createOrderBUY(..., levelChange, ...)` | `:333-353` | `BIG_DOWN` | CO (`isSymbolRunning`) |
| 2 | **DCA** `symbolDcaLevel` + `isDcaAlt` | `:355-372`, `:375-380` | `DCA_LEVEL1` | CO |
| 3 | **SELECTOR** `symbol2Pred = time2SymbolPred.get(time)` → `selectCands` → vong `createOrderBUY(..., PREDICT_SYMBOL_TRADE, ...)` | **`:384-431`** (khoi `if (symbol2Pred != null)`), `selectCands` o `:668-687` | `PREDICT_SYMBOL_TRADE` | CO |

### 1.1 🔴 DINH CHINH QUAN TRONG: `SELECTOR_ONLY_ENTRY` KHONG phai cong tac cua leg selector

- `Configs.java:367` `SELECTOR_ONLY_ENTRY` duoc dung o **duy nhat mot cho**: `SimulatorMarketLevelTicker1MStopLoss.java:346`
  → `if (!Configs.SELECTOR_ONLY_ENTRY) { for (short symbolId : symbol2BUY) createOrderBUY(..., levelChange, ...) }`.
  `symbol2BUY` la san pham cua `getTopSymbolArray(numberOrder, ...)` — tuc **leg market-signal**; `levelChange`
  trong T170 **chi con `BIG_DOWN`** (`MarketBigChangeDetector.getMarketStatus1M` `:174-184` — BIG_UP/SMALL_UP/
  SMALL_DOWN_15M da bi xoa, con dung 1 nhanh).
- ⇒ **`SELECTOR_ONLY_ENTRY=1` TAT leg `BIG_DOWN`, KHONG phai leg selector** (xac nhan doc lap boi
  `docs/experiment/T2_FULLFLOW.md:37-41`, `docs/experiment/L1_SHADOW_C3.md:87,108`, `docs/design/C2B_SPEC.md:477`).
- ⇒ **KHONG duoc dung `SELECTOR_ONLY_ENTRY` cho V1.** Neu dung nham se "cat" dung nhom `meanP` cao nhat
  (BIG_DOWN) va giu lai nhom thap nhat (selector) — nguoc hoan toan gia thuyet, va ket qua se bi dien giai sai.
- ⇒ **Trong code KHONG ton tai cong tac cat leg selector.** Khong co `DISABLE_PREDICT_SYMBOL` song
  (chi con trong `Configs.java.bak_cfg`), khong co flag nao gate khoi `:384-431`. **V1 phai them flag moi.**

### 1.2 `SELECTOR_RANK_TOPK` (`Configs.java:362-363`, profile `x1_gs_t170.properties` = `8`)

Doc o `selectCands` (`:668-687`): `TOPK > 0` ⇒ `chosenCands = K phan tu DAU cua symbol2Pred` (da sort TANG
theo pNoPump) — **bo han tang 1 (absolute maxThres/nPass)**. `TOPK <= 0` ⇒ cutoff tuyet doi
`maxThres = PREDICT_SYMBOL_RATE_MAX_THRESHOLD (0,15) × AI_DYNAMIC_MAX (2,14135) = 0,32120`.
⇒ Giam `SELECTOR_RANK_TOPK` la **giam do phu** leg selector, dung nghia "GIOI HAN".

### 1.3 `time2SymbolPred` den tu DAU (quan trong cho duong Kaggle)

`SimulatorMarketLevelTicker1MStopLoss.java:882` `time2SymbolPred = ds.funding` (WfoDataset doc tu
`funding.bin` trong `WFO_DATA_DIR`). Dong thoi `BIG_DOWN` cung dung `extractPredict2Symbol(time2SymbolPred.get(time))`
(`:325`) ⇒ **khong the "lam rong predictions" de cat selector**: lam vay se giet luon ca BIG_DOWN.
Va theo `docs/runbooks/KAGGLE_SIM.md` §6, bins KHONG di qua duong Kaggle (bin da nuong vao `funding.bin` tu luc build)
⇒ **bien the phai la bien the CODE hoac bien the PROFILE**, khong phai bien the bins.

## 2. Cong chan (BUOC 0 — lam TRUOC, bat buoc)

Truoc khi chay bat ky bien the: **tai lap parity T170 tren Kaggle**. Cau hinh T170 nguyen ban
(`profile x1_gs_t170`, bundle `sim-x1-2021-bundle`, `SIM_END_DATE=20251231`) phai ra
`printDone.csv` md5 **`efb793e2468ca3a7318da0f0ad23d4fc`**, n=1089, `diff` = 0 dong so voi ban Oracle
`X1_GS_T170_2021`. Neu khong tai lap duoc ⇒ **DUNG, khong chay bien the** (chay tren dataset sai se ra
ket qua vo nghia ma khong bao loi).

## 3. Bien the (k = 2, chot TRUOC, khong them sau)

| tag | co che | thay doi | ky vong co che |
|---|---|---|---|
| `PARITY` | — | `x1_gs_t170` nguyen ban | md5 `efb793e2…`, n=1089 |
| `CUT` (V1) | **CAT HAN leg selector** | flag MOI `SELECTOR_LEG_CUT=1` → `:385` thanh `if (symbol2Pred != null && !Configs.SELECTOR_LEG_CUT)`. Khong cham dong nao khac | 821 lenh selector = 0; `BIG_DOWN`/`DCA_LEVEL1` **tang** (gia thuyet giai phong khoa) |
| `TOPK3` (V2) | **GIOI HAN do phu** | profile key `SELECTOR_RANK_TOPK` 8 → 3 (khong doi code) | selector 821 → it hon; khoa it hon |

- **V3 (uu tien nhuong khoa cho BIG_DOWN/DCA) KHONG duoc chay** trong vong nay: doi lich uu tien trong
  vong lap tick la thay doi lon hon (thu tu `createOrderBUY` giua 3 duong), rui ro cao hon nhieu so voi
  nguon chung con lai, va V1/V2 da tra loi dung cau hoi chinh. Neu V1/V2 ra tin hieu => vong MOI se
  pre-reg V3. Ghi ro o day de khong bi coi la "them bien the sau khi thay so".
- Ca hai bien the chay tren **cung bundle** voi parity (`sim-x1-2021-bundle`), **cung cua so**
  (`SIM_END_DATE=20251231`), `TICKER_SOURCE=file`, DEV 2021-07..2025-12. **KHONG dung 2026** (seal).
- `CUT` can jar moi ⇒ jar rieng duoi dataset `chuyendinh/sim-jar-selcut` (95MB) + tham so `jar_ds` moi
  cua `tools/kaggle_sim.py`; kernel in `JAR_SHA256=`. `TOPK3` chi doi profile ⇒ chay tren jar cu
  (phai verify `JAR_SHA256` == oracle jar dang dung cho parity).

### 3.1 Cong parity RIENG cho jar V1 (bat buoc)

Jar moi + `SELECTOR_LEG_CUT` default `false` ⇒ `printDone.csv` phai **byte-identical** `efb793e2…`
(giong het cong parity cua `PREREG_SEL_BIGDOWN` muc 1). Chi khi cong nay PASS moi chay `CUT`.

## 4. Cham diem (chot TRUOC)

### 4.1 5 rate chat luong + n (toan bo leg), vs `PARITY`

`n`, `win%`, `TSloss%`, `mP|SM` (mean profit cua lenh `STOP_MARKET_DONE`), `mP|SL` (lenh `STOP_LOSS_DONE`),
`meanP`. "Tot" = `win%`/`mP|SM`/`mP|SL`/`meanP` **TANG**, `TSloss%` **GIAM** (theo `docs/runbooks/RISK_APPETITE.md`).

### 4.2 CI (chot TRUOC, hai do rong — bao CA HAI)

Bootstrap **block-72h**, paired resample theo block, **2000 rep**, **seed `20260905`**
(`research/analysis/c3_rates.py`: `BLOCK_H=72`, `NREP=2000`, `SEED=20260905`).
No rong CI bao **ca hai**:

1. `x1.21` — he so **cu**, la muc brief yeu cau, **rong hon** `inflate(2)` ⇒ **PRIMARY (chat hon)**;
2. `inflate(2) = sqrt(2 ln 2) = 1,1774` — he so chuan hoa theo
   `docs/audit/AUDIT_CI_INFLATE_STANDARDIZATION.md` (k = 2 ung vien so voi parity).

`rate ngoai CI` chi duoc tinh khi ngoai CI o **CA HAI** do rong (khong chon do rong theo ket qua).

### 4.3 Rang buoc CUNG (theo `docs/runbooks/RISK_APPETITE.md`, do tu `sim.out` + `printDone.csv`)

| rang buoc | nguong |
|---|---|
| maxDD theo NAM | **<= 30%** |
| UW (ngay underwater dai nhat) | **<= 200** |
| quy xau nhat | **>= -15%** |
| nam am | **KHONG** (tuyet doi) |
| tap trung 1 coin | **<= 15% equity** (`conc_max` theo `conc_grid.py`: tong margin cum / equity ngay mo) |

### 4.4 Cau hoi chinh phai tra loi BANG SO

So lenh + `SumPnL` + `meanP` cua `BIG_DOWN` va `DCA_LEVEL1` **truoc - sau** tung bien the. Day la
phep do TRUNG TAM (gia thuyet giai phong khoa). Bao cao ca so lenh theo level (821/248/20 → ?).

### 4.5 Bao cao rieng (KHONG dung de chon)

PnL/equity cuoi, CAGR, maxDD, UW, phan bo theo nam, `pnl/leg`. **Khong chon bien the theo equity**
(bai hoc `RESULT_SEL_BIGDOWN`: `DROP` +28% end-equity nhung 0/3 rate ngoai CI ⇒ NULL).

## 5. Ky luat ket luan (chot TRUOC)

**GO** chi khi **ca ba**:
1. **>= 2** trong 5 rate (§4.1) **ngoai CI** o **CA HAI** do rong (§4.2) va **CUNG huong TOT**;
2. **het rang buoc cung** (§4.3);
3. **khong rate nao XAU ngoai CI** (khong co rate di nguoc huong tot mot cach co y nghia thong ke).

- Neu chi "it PnL hon" (hoac it lenh hon) ma khong co rate nao ngoai CI ⇒ ghi ro **NULL** (khong phai cai thien).
- Neu ket qua phu thuoc **1 bien the** (vd chi `CUT` dat, `TOPK3` khong) ⇒ ghi **UNCONFIRMED**, khong ap dung.
- Multiplicity: k = 2 ⇒ `inflate(2) = 1,1774` dung trong `x1.21` (rong hon) ⇒ nguong da du chat.
- **Khach quan**: `CUT` phai cat dung leg selector ⇒ tu-kiem **n `PREDICT_SYMBOL_TRADE` == 0** o bien the `CUT`
  (neu > 0 ⇒ flag khong duoc ap ⇒ ket qua VO HIEU, bao ro, khong dien giai).

## 6. Quy trinh + tai nguyen

1. Cong chan BUOC 0 (§2) tren Kaggle.
2. Commit pre-reg nay TRUOC khi chay bien the.
3. V1: them `Configs.SELECTOR_LEG_CUT` (default false) + 1 dieu kien o `:385`; `mvn -o package` tren Oracle
   (build, KHONG chay sim Java tren Oracle); day jar len Kaggle dataset rieng; cong parity jar moi (§3.1).
4. V2: profile clone `x1_gs_t170` + `SELECTOR_RANK_TOPK=3`.
5. Chay **tuan tu** tren Kaggle (5 slot/account, 12h kill/kernel, chi phi 0). Ghi ro so kernel + wall-clock da dung.
6. Cham theo §4; ghi `docs/result/RESULT_SELECTOR_LEG_CUT.md`; commit (**KHONG push**); don file tam.

## 7. Pham vi + cam ket

DEV 2021-07-01..2025-12-31 (`wfo_ds_x1_2021`). **KHONG** dung 2026 (seal). **KHONG** `claude-run`/Claude Code.
**KHONG** chay sim Java tren Oracle (job `shadow-c3` dang chay — chi build jar). **KHONG push**.
Khong tune sau khi thay so. Khong sua trigger/gate/exit/DCA cua T170.
