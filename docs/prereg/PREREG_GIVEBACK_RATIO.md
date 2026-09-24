# PREREG_GIVEBACK_RATIO — he so gap trailing `TS_GIVEBACK_RATIO` = 1 / 2 / 5 (moc 0.5)

Viet **TRUOC** khi push kernel nao (chot 2026-09-24). **Khong sua thiet ke sau khi thay ket qua.**
Nen: **KEEPLEG0** (`t170_flat_keepleg0` = `x1_gs_t170` + `DCA_GRID 1,1,1,1 / 6.0`).
**Vong thu 11 truc EXIT** (10 vong truoc NULL — xem `RESULT_TAIL_LEVER`, `RESULT_EXIT_HIGH_N`,
`RESULT_TRAIL_HINGE`, `RESULT_TRAIL_LADDER`, `RESULT_PEAK_CLOSE`, `RESULT_SL_7_TO_3`,
`RESULT_ARM3_3NEN`).

## 0. Cau hoi (nguyen van owner)

> *"`TS_GIVEBACK_RATIO 0.5` test cai nay voi 1 2 5 xem sao"*.

⇒ **CHI doi DUY NHAT `TS_GIVEBACK_RATIO`** ∈ {1, 2, 5}; moc = **0.5** (da co: `kg0-g170`).
Khong doi key nao khac, khong doi code, khong chay HPO.

---

## 1. BUOC 0 — `TS_GIVEBACK_RATIO` co phai "marker validate" lam `exit(2)` khong? (KET QUA: **KHONG**)

Doc code (khong suy dien):

| # | cho | noi dung |
|---|---|---|
| 1 | `Configs.java:173-175` | `TS_GIVEBACK_RATIO = Cfg.get("TS_GIVEBACK_RATIO")` (env) **else** `properties.get(...)` (profile) **else** `0.5f`. ⇒ **key PROFILE binh thuong**, doc luc static-init. |
| 2 | `Configs.java:839` | `TS_GIVEBACK_RATIO` nam trong **`KNOWN_PROPS`** = danh sach key code THUC SU doc tu `config.properties`. Day la **allowlist**, khong phai blacklist: key **CO** trong allowlist ⇒ **khong bao** ("key khong ai doc"). `exit(2)` o day chi xay ra khi `CONFIG_STRICT=1` **VA** co key LA trong `config.properties` — `TS_GIVEBACK_RATIO` **khong roi vao** truong hop do. |
| 3 | `Configs.java:864-874` | danh sach marker THAT (`exit(2)` im lang) chi gom **`SIM_TS_GIVEBACK`** (chi nhan `1`) va **`SIM_BREAKER_MODE`** (chi nhan `OFF`) — **khong co** `TS_GIVEBACK_RATIO`. |
| 4 | `Cfg.auditProfile()` (`Cfg.java:163-181`) | bao key trong **profile** ma khong ai doc; `TS_GIVEBACK_RATIO` **duoc doc** (muc 1) ⇒ nam ngoai danh sach canh bao. |

**Ket luan BUOC 0:** `TS_GIVEBACK_RATIO` **KHONG** phai marker validate. Duong dung la **override qua PROFILE**
(kernel `kaggle_sim` ghi `prof_run.properties`; `TRADING_PREFIX` da chan `TS_*` qua env ⇒ khong dat env).
⇒ **Khong can sua Java, khong can `mvn package` lai**; van `mvn -o package` mot lan de xac nhan build sach.

---

## 2. Co che (doc tu code, khong suy dien)

`TradeUtils.java:52-58` (`trailFromCap`) — duong trailing **DUY NHAT**:

```
gap  = min(peak * TS_GIVEBACK_RATIO, maxGap)
rate = round((peak - gap) / 0.005) * 0.005      # SL = entry*(1+rate)
```

- `maxGap` = `TS_MAX_GAP_WEAK = 0.03f` khi `pNoPump > TS_PNOPUMP_WEAK_THR (0.29)` **hoac `pNoPump == null`**;
  nguoc lai `TS_MAX_GAP = 0.08f` (`Configs.java:140-141`, `TradeUtils.java:40-46`, ban le `0.29`:
  `Configs.java:443-444`).
- `peak` = **HIGH nen 1m hien tai** (`TS_PEAK_MODE` default `high`, `Configs.java:496-498`;
  `TradeUtils.peakPrice` `TradeUtils.java:30-32`).
- Nguong **ARM** = `RATE_PROFIT_STOP_MARKET = 0.07` (`calRateMinWithPredReturn15MForTradingStop`,
  `TradeUtils.java:107-113`; `LiveProfileC3.armRate` tra `def` khi `LIVE_PROFILE != c3_shadow`).
  ⇒ moi buoc ratchet (ke ca buoc dat SL dau o `OrderTargetInfoTest.java:189-193`) chi xay ra khi **peak >= 7%**.
- `updateTPSL` (`OrderTargetInfoTest.java:250-268`) chi **nang** SL khi `priceSLNew > priceEntry`
  ⇒ bat bien "**SL khong bao gio duoi entry**"; `gap >= peak` ⇒ `rate <= 0` ⇒ **khong doi SL**.

### 2.1 ⭐ DU DOAN KHOA TRUOC (ghi TRUOC khi chay)

`maxGap` bat dau chan khi `peak > maxGap / ratio`:

| ratio | nguong chan (WEAK 3%) | nguong chan (STRONG 8%) |
|---|---|---|
| **0.5** | `peak > 6%` | `peak > 16%` |
| **1** | `peak > 3%` | `peak > 8%` |
| **2** | `peak > 1.5%` | `peak > 4%` |
| **5** | `peak > 0.6%` | `peak > 1.6%` |

**Vi ARM o +7% ⇒ moi buoc ratchet co `peak >= 7%`:**

- **WEAK** (`pNoPump > 0.29` hoac null, `maxGap=0.03`): `0.07*0.5 = 0.035 > 0.03` ⇒ **moc 0.5 DA bi chan**;
  ratio 1/2/5 cung bi chan ⇒ **gap = 0.03 Y HET** cho ca 4 chan.
- **STRONG** (`maxGap=0.08`): moc 0.5 chua chan o `peak ∈ [7%,16%)` ⇒ `gap = 0.5*peak` (3.5%…8%);
  ratio >= 1 ⇒ `gap = min(peak*ratio, 0.08) = 0.08` **gan het** ⇒ **trail LONG hon (SL thap hon)**.
  `peak >= 16%` ⇒ ca 4 chan deu `gap = 0.08` ⇒ **trung nhau**.
- **1 vs 2 vs 5**: khac nhau chi o `peak ∈ (7%, 8%)` STRONG, ma o do **ca hai deu cho `rate <= 0`
  ⇒ khong doi SL** (`gap = peak` ⇒ `rate = 0`; `gap = 0.08` ⇒ `rate < 0`) ⇒ **ket cuc GIONG NHAU**.

> **DU DOAN: ratio 1 / 2 / 5 GAN NHU TRUNG NHAU (co the byte-identical o phan lon leg) va gan nhu
> KHONG khac moc; khac biet chi tap trung o nhom leg STRONG co `peak` trong [7%, 16%)**
> (moc 0.5: SL +3.5%…+8%; 1/2/5: SL ~0%…, trail long hon) ⇒ neu co khac, huong la
> **`TSloss%` giam / `hold` dai hon / `mP|SM` giam (tra loi nhieu hon)** tren so it leg.
> **PHAI kiem du doan nay BANG SO** (muc 3: so leg khac nhau thuc su), khong chi dua vao cong thuc.

---

## 3. Cong chan parity (BAT BUOC, lam TRUOC khi tin bat ky so nao)

1. **Moc** = `kg0-g170` = `sl3-base` (`kaggle_sim/out/kg0-g170`): `printDone.csv` md5
   **`99e42b75cf1a2142f9cd14dc72e371ba`**, **n = 1,085**, **equity = 103,083**, jar `2c2f8aef`,
   mapper **863**, `prof_run.properties` co `TS_GIVEBACK_RATIO=0.5`.
   Moc nay **da co san** (khong chay lai): chi doc lai md5/n/equity.
2. **"Chi 1 key doi"**: `prof_run.properties` cua 3 chan MOI phai khac moc **DUNG 1 key**
   `TS_GIVEBACK_RATIO` (0.5 → 1/2/5). Khac them key nao (ngoai duong mount
   `WFO_FUNDING_PRED_DIR` — chi la duong dan mount Kaggle) ⇒ **DUNG, bao RO**.
3. Moi kernel moi phai co `Loaded Symbol Mapper: 863 symbols` (guard da co trong `kaggle_sim`);
   thieu ⇒ kernel `exit 2`, khong doc so.
4. Khong push. Khong chay Java/sim tren Oracle (Oracle chi `mvn -o package`). Sim tren **KAGGLE**.
   Kaggle hong ⇒ **DUNG, bao RO**.

## 4. Chan (k = 3 ung vien moi; moc KHONG tinh)

| tag | `TS_GIVEBACK_RATIO` | ghi chu |
|---|---|---|
| `kg0-g170` | 0.5 | **MOC** (da co) |
| `gb-r1` | **1** | moi |
| `gb-r2` | **2** | moi |
| `gb-r5` | **5** | moi |

Nen `prof_x1_gs_t170` + override `DCA_GRID_WEIGHTS=1,1,1,1`, `DCA_GRID_SCALE=6.0` (= KEEPLEG0) +
`TS_GIVEBACK_RATIO=<ratio>`. Bundle `sim-x1-2021-bundle`, **khong `jar_ds`** (jar bundle = `2c2f8aef`
= **cung jar** voi moc). Cua so **DEV 2021-07-01..2025-12-31**, `TICKER_SOURCE=file`, chi phi 0.

## 5. Cham diem (chot TRUOC)

1. **Bang 4 chan** (0.5 / 1 / 2 / 5): `n` · `win%` · `TSloss%` · `meanP` (+`mP|SM`,`mP|SL`) · `hold` ·
   `equity` cuoi · **`maxDD` + `UW` tren MTM MOC PHUT** (`RISK_APPETITE` §7.3, tai dung
   `research/analysis/intraday_dd.py`; **dung lai cache `series.npz` neu co**).
2. **5 rate + CI block-72h, 2000 rep, seed 20260905** paired vs MOC, o **CA HAI** do rong
   (`x1.21` legacy + `inflate(3) = 1.482304`). `rate NGOAI CI` = ngoai **ca hai** do rong.
   Ket qua gan nhan `TOT` / `XAU` (chieu theo `docs/runbooks/RISK_APPETITE.md`).
3. ⭐ **DO SO LEG THUC SU KHAC NHAU** giua cac chan: so leg **co khoa `(sym, start, end, status, pnl)`
   KHAC nhau** giua 0.5 vs 1 vs 2 vs 5 (va giua **1 vs 2 vs 5**) ⇒ **kiem du doan "gan nhu trung nhau"
   bang so**, khong bang cong thuc.
4. **BANG PnL THEO NAM + TOTAL PnL** cho **ca 4 chan** (n va PnL USDT ro rang) + equity cuoi.
5. **Rao cung `RISK_APPETITE` §7** theo nam **LAN** toan ky: `maxDD` nam <= 40% · quy xau nhat >= -20% ·
   `UW` <= 250 ngay · tap trung 1 coin <= 15% · **khong nam am** (`maxDD`/`UW` = **MTM MOC PHUT**).

## 6. LUAT (chot TRUOC)

- **GO** chi khi: **>= 2 rate ngoai CI cung huong TOT** + **het rao cung §7** + **0 rate XAU ngoai CI**.
- Nguoc lai ⇒ **NULL**, noi ro. Ghi ro: **day la vong thu 11 truc EXIT**.
- **PnL/equity bao RIENG, KHONG dung de chon chan** (bai hoc `RESULT_SEL_BIGDOWN`).
- Khong push; khong cham 2026; khong `claude-run`.

## 7. Dau ra

`docs/prereg/PREREG_GIVEBACK_RATIO.md` (file nay) + `docs/result/RESULT_GIVEBACK_RATIO.md` + runner
`research/analysis/gb_run.py` + scorer `research/analysis/gb_score.py` +
MTM moc phut `research/analysis/gb_intraday.py`. Commit **KHONG push**.
