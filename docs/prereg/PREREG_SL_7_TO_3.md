# PREREG — "SL CUNG 7% -> 3%" tren NEN PRODUCTION (FLATGRID KEEPLEG0)

Chot **TRUOC** khi chay bat ky sim moi nao. Ngay 2026-09-24. Branch `module`.
Nguon yeu cau (owner): *"thu day cai SL cung tu 7% xuong 3% xem ket qua the nao"*.
Sim chay **tren Kaggle CPU kernel** (`docs/runbooks/KAGGLE_SIM.md`). **KHONG** Java/sim tren Oracle
(Oracle chi duoc `mvn -o package`). **KHONG** `claude-run`/Claude Code. **KHONG** push.
DEV only: cua so `2021-07-01 .. 2025-12-31` (**KHONG** cham 2026/holdout/242/shadow_c3).

---

## 0. Su that PHAI dung: KHONG co "SL cung 7%" trong baseline

Da doc code o HEAD (`grep`, khong suy dien lai):

| tham so | o dau | nghia THAT | gia tri baseline |
|---|---|---|---|
| `SIM_RATE_PROFIT_STOP_MARKET` | `Configs.java:806`, profile `x1_gs_t170`/`t170_flat_keepleg0` | **NGUONG ARM cua trailing** (+7%): cum chi duoc vao nhanh trailing/`updateStatusNew` khi `maxPrice >= entry*(1+RATE_PROFIT_STOP_MARKET)`. **KHONG phai stop-loss.** | **0.07** |
| `SIM_PRE_ARM_SL` | `Configs.java:437` + `PreArmSlUtils.java` | **SL CUNG THAT su truoc arm** tren `firstEntryPrice` (bat bien qua DCA): gia tri **AM** = cat o `-X%`; `0` = **TAT** (mac dinh) | **0 (TAT)** |
| `SIM_HARD_SL_PCT` | — | **key CU DA CHET o HEAD** (khong con lan `Cfg.get` nao); X2 da viet lai thanh `SIM_PRE_ARM_SL` | — |

⇒ Con so **7%** ma owner nhin thay la **ARM**, khong phai SL. Vi vay vong nay do **CA HAI nghia**
chu khong doan y owner:

- **(V1) arm 7% -> 3%**: `SIM_RATE_PROFIT_STOP_MARKET=0.03`
- **(V2) SL cung -3% truoc arm**: `SIM_PRE_ARM_SL=-0.03`
- **(V3) ca hai**: `SIM_RATE_PROFIT_STOP_MARKET=0.03` + `SIM_PRE_ARM_SL=-0.03`
- **(V4) [moc so sanh truc tiep]** SL cung **-7%** truoc arm: `SIM_PRE_ARM_SL=-0.07`
  (de co dung "con so 7%" cua owner duoi dang SL cung)

`PreArmSlUtils`: chi `preArmSl < 0` moi bat; `stopLevel = firstEntryPrice*(1+preArmSl)`;
nen nao co `bar.minPrice <= stopLevel` thi dong ngay tai `min(stopLevel, min(open, close))`
(chan look-ahead). Nhanh nay chay **TRUOC** cong profit-arm va truoc LOSER_TIME_STOP/COND_EXIT.
`SIM_LOSER_TIME_STOP_HOURS=168` **giu nguyen** o ca 5 chan.

---

## 1. Ky luat: day la vong thu 9 tren TRUC EXIT

8 vong truoc **deu NULL** tren truc exit: hinge · ladder · peak-close · 17 policy · 20 policy ·
cap 10/30 · GD92xexit · high-N x exit. Ngoai ra da do truc SL cung tren **nen khac** (khong phai
KEEPLEG0): `X2_S20/S30` (pre-arm SL -20%/-30%, nen C3, 2022-2025) => **NULL** (cat duoi nhung
`win%` giam ngoai CI, `medloser` dong tai dung muc cat, UW doi cho tu 2025 sang 2022);
`X3_B` (pre-arm SL -50%) => **NULL**; `SL_ADAPT_HARDSL` (-8% theo rank, nen T100) => 3/5 rate
**XAU** ngoai CI. Vong nay khac o cho: **nen KEEPLEG0** (cau hinh production dang chay) +
**cua so 2021-07..2025-12** + do **CA HAI** nghia cua "7%" + cham bang **MTM moc phut**.

**KHONG** duoc vien dan lai: neu ket qua NULL thi ket luan NULL va **danh so vong**; neu co tin hieu
thi **de xuat** buoc tiep, **KHONG tu tich hop**.

---

## 2. Nen, num, thang do — KHOA TRUOC

**Nen (base) = KEEPLEG0** = `prof_x1_gs_t170` + **DUNG 2 dong** `DCA_GRID_WEIGHTS=1,1,1,1`,
`DCA_GRID_SCALE=6.0` (= `t170_flat_keepleg0`; `diff` hai file = dung 2 dong nay + 2 dong
`CONC_CAP_PERCOIN_*` da chung minh la **no-op byte-identical** tren nen nay,
`docs/result/RESULT_GATESCALE_KEEPLEG0.md` §1).

Bundle `chuyendinh/sim-x1-2021-bundle` (= `wfo_ds_x1_2021`, `leakFreeFrom=2021-07-01`),
`sim_end_date=20251231`, **jar mac dinh cua bundle** (= jar da tao ra `t170-x1-2021` md5
`efb793e2`), khong `jar_ds`. Bundle la **snapshot chi co 3 profile** ⇒ bien the dien dat bang
**override tren `x1_gs_t170`**; kernel ghi `out/<tag>/prof_run.properties` lam bang chung.

| chan | tag | override THEM (ngoai KEEP) | nghia |
|---|---|---|---|
| **moc + parity** | `sl3-base` | — (khong override) | `t170_flat_keepleg0` |
| **V1** | `sl3-v1-arm03` | `SIM_RATE_PROFIT_STOP_MARKET=0.03` | arm 7% -> 3% |
| **V2** | `sl3-v2-sl3` | `SIM_PRE_ARM_SL=-0.03` | SL cung -3% truoc arm |
| **V3** | `sl3-v3-both` | ca hai dong tren | arm 3% + SL cung -3% |
| **V4** | `sl3-v4-sl7` | `SIM_PRE_ARM_SL=-0.07` | SL cung -7% truoc arm |

**CONG PARITY (BAT BUOC, dieu kien doc ket qua):** `sl3-base` (khong override) phai co
`printDone.csv` md5 **`99e42b75cf1a2142f9cd14dc72e371ba`** · **n = 1,085** · equity **103,083**
(= Oracle `java/devrun/FG_KEEPLEG0`). Khac ⇒ **DUNG, bao RO, khong doc tiep.**
Doi chieu phu: `SIM_PRE_ARM_SL=0` (OFF) phai **byte-identical** voi truoc X2 — da co unit test
`PreArmSlTest`; tren chan V1 (khong bat SL cung) so dong `PREARM_SL sym=` trong `logs/sim.out`
**phai = 0**.

---

## 3. Cham — KHOA TRUOC

1. **5 rate chat luong** = `win%` · `TSloss%` · `mP|SM` (`mean profit | STOP_MARKET_DONE`) ·
   `mP|SL` · `meanP`. So voi **moc `sl3-base`**, bootstrap **block-72h, 2000 rep, seed 20260905**
   (`c3_rates`/`gd92xexit_score`). "Ngoai CI" (quyet dinh) = ngoai **CA HAI** do rong:
   `x1.21` legacy **VA** `inflate(k)=sqrt(2 ln k)` voi **k = 4** = **1.665109** (4 ung vi V1..V4;
   baseline khong tinh). Huong TOT: `win% ↑` · `TSloss% ↓` · `mP|SM ↑` · `mP|SL ↑` · `meanP ↑`.
   Bao them so rate XAU.
2. **`maxDD` + `UW` tren MTM MOC PHUT** (BAT BUOC, `RISK_APPETITE.md` §7.3): tai tao theo dung
   cach `docs/result/RESULT_INTRADAY_DD.md` (`equity_mtm(m) = 35,000 + realized(m) + unP(m)`, mark
   `priceClose` 1m; `UW` quy doi phut/1440). **Bat buoc tai kiem truoc khi bao cao** (V1/V3/V4/V5
   cua RESULT_INTRADAY_DD: `CAP0+Σpnl` vs `b_final`; `equity_mtm(00:00Z)` vs `b+unP` in ra,
   nguong tuong doi ≤ 0.05% equity; `min_chay(unP_low)` vs `unPMin` in ra). **Dung lai cache**
   `series.npz` neu co; chi tinh lai chan nao thieu. Bao **ca** so NGAY de doi chieu.
3. **Rao cung `RISK_APPETITE.md` §7** — theo **nam** LAN **toan ky**:
   `maxDD <= 40%` · `UW <= 250` · `quy xau nhat >= -20%` · **khong nam am** · `conc <= 15%`.
   Phu: khau vi CU `30% / 200 / -15%`. `maxDD`/`UW` lay tu **MTM moc phut** (muc 2);
   `quy`/`conc`/`ret` theo chuoi daily artifact (dung khuon `kg0_score`).
4. **Bang PnL CHI TIET THEO NAM** (n · PnL USDT · ret% · maxDD · UW · qmin% · equity) cho
   **moc + V1 + V2 + V3 + V4**.
5. `n` · `hold` (median, gio) · `turnover` (leg/ngay) · `Σfunding/ΣPnL` · **`TSloss%`**
   (du kien **TANG MANH** khi SL cung bat: moi cu cat truoc arm duoc ghi nhan `STOP_LOSS_DONE`)
   · so dong `PREARM_SL` trong log (co che co BIND that khong).
6. **PnL/equity bao rieng, KHONG dung de chon** (uu tien owner: nhieu lenh / on dinh / dai han).

---

## 4. Luat quyet dinh — KHOA TRUOC

**GO** cho mot bien the chi khi dong thoi:
(a) **>= 2 rate ngoai CI cung huong TOT** (ngoai **ca hai** do rong, vs moc `sl3-base`);
(b) **het rao cung §7** (theo nam VA toan ky, do bang MTM moc phut);
(c) **0 rate XAU ngoai CI**.

Nguoc lai ⇒ **NULL**: ghi ro, **danh so vong** (vong 9 truc exit), **khong** ket luan mo ho,
**khong** tu tich hop vao profile/engine. Neu co tin hieu (du chua du GO) ⇒ noi ro + **de xuat**
buoc do tiep theo, khong tu lam.

Khong duoc doi: thang do, danh sach chan, k=4, cua so, cach do maxDD, luat quyet dinh —
sau khi da chay. Khong them/bo chan sau khi thay so. Khong "cai thien" tham so cua chan thang.

---

## 5. Chi phi / nguon

- Kaggle CPU kernel, **chi phi 0**; 5 chan **chay SONG SONG** (slot toan account = 5), 1 vong.
  Neu slot < 5 ⇒ chay 2 vong nhung **KHONG** doi thu tu uu tien. Kaggle hong ⇒ **DUNG, bao RO**.
- `mvn -o package` (neu code doi — vong nay **khong doi code**, chi override tham so da co).
- Ket qua: `docs/result/RESULT_SL_7_TO_3.md`; runner `research/analysis/sl3_run.py`;
  scorer `research/analysis/sl3_score.py`; MTM `research/analysis/sl3_intraday.py`.
- Commit (**KHONG push**).
