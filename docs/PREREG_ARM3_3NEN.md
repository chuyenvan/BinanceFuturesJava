# PREREG — ARM 7% -> 3% tren 3 NEN (6 chan) + BANG THEO NAM

Chot **TRUOC** khi chay bat ky sim moi nao. Cua so **DEV 2021-07-01..2025-12-31** (khong cham 2026).

## 0. Cau hoi (nguyen van owner)

> *"toi muon giam arm 7% hien tai ve 3% do lai voi KEEPLEG0 va T100, GD92 nua vay la 6 cai chay di
> roi gui full ket qua cua 6 cai theo nam co ca so lenh va total pnl"*

⇒ Do **1 tham so duy nhat `SIM_RATE_PROFIT_STOP_MARKET`** (nguong **ARM** cua trailing — KHONG phai
stop-loss; xem `RESULT_SL_7_TO_3.md` §1) o 2 muc **7%** (moc) vs **3%** (arm3) tren **3 nEN**.

## 1. 6 chan = 3 nEN × 2 MUC

| # | nEN | profile | muc ARM | tag | nguon |
|---|---|---|---|---|---|
| A1 | **KEEPLEG0** | `t170_flat_keepleg0` (= `x1_gs_t170` + DCA_GRID 1,1,1,1 / 6.0) | 0.07 | `kg0-g170` | da co |
| A2 | **KEEPLEG0** | nhu tren | **0.03** | `sl3-v1-arm03` | da co |
| B1 | **T100** | `x1_c3_full` (+`SIM_TRAIL_TRACE=1`) | 0.07 | `hn-t100` | da co |
| B2 | **T100** | nhu tren | **0.03** | `hn-t100-arm3` | **CHAY MOI** |
| C1 | **GD92** | `x1_c3_full`(+TRACE, `SIM_GATE_ROLLING_PCT=0.92`, `DAYS=90`) ≡ `archive/x1_gd92` | 0.07 | `hn-g92` | da co |
| C2 | **GD92** | nhu tren | **0.03** | `hn-g92-arm3` | **CHAY MOI** |

**CHI DOI DUY NHAT `SIM_RATE_PROFIT_STOP_MARKET`.** Tuyet doi **khong** bat `SIM_PRE_ARM_SL`,
**khong** doi bat ky key nao khac. Doi chieu: `grep -v SIM_RATE_PROFIT_STOP_MARKET` tren
`prof_run.properties` cua cap (Xi, X2) phai **giong het** (tru tag).

`archive/x1_gd92.properties` == `x1_c3_full.properties` + 2 dong `SIM_GATE_ROLLING_*` (da `diff`).

## 2. CONG PARITY — BAT BUOC PASS truoc khi doc ket qua

Doi tuong: **3 MOC** (muc 0.07) phai tai lap **dung** ban da co.

| cong | tag | md5 `printDone.csv` | n | equity |
|---|---|---|---|---|
| P-A | `kg0-g170` | **`99e42b75cf1a2142f9cd14dc72e371ba`** | 1,085 | 103,083 |
| P-B | `hn-t100` | **`dc16e4da6ff6cb7b8d41c592bc3d9c45`** | 2,559 | 121,770 |
| P-C | `hn-g92` | `cd913759ecd4bf50adab2b818eaf9525` | 2,632 | 133,944 |

P-C phai co log **`[GATE-ROLL]` BAT** (`pct=0.92 W=90d`). Khac ⇒ **DUNG, bao RO**.

`jar_sha256`: A1/A2 = `2c2f8aef…` (module, `kg0-g170`+`sl3-*` cung 1 jar).
B1/B2/C1/C2 = `bb282f40…` (`sim-jar-exithighn` = module `b50833f` + cherry-pick `-n 1db0613`,
co `GateRollingThreshold`). ⇒ **B2/C2 phai chay cung jar `bb282f40`** de so sanh voi moc cua chinh nEN.
Khong merge `gd92-recheck`; build xong `git checkout -- src/` tra `module` nguyen trang.

## 3. TAI SU DUNG (khong chay lai vo ich)

- `A1` = `kaggle_sim/out/kg0-g170` (md5 khop `99e42b75…`, `== sl3-base`) ⇒ tai su dung.
- `A2` = `kaggle_sim/out/sl3-v1-arm03` (n 1,503 / eq 79,773, `RESULT_SL_7_TO_3.md`) ⇒ tai su dung
  (cung profile+jar voi A1).
- `B1` = `hn-t100`, `C1` = `hn-g92` ⇒ tai su dung.

## 4. OUTPUT CHINH — BANG 6 CHAN THEO NAM (bat buoc)

Mot bang 6 dong, cot: `2021..2025` × (`n`, `PnL`) + `TONG n` + `TOTAL PnL` + `equity cuoi`.
Cot phu bat buoc: `arm dung`, `win%`, `TSloss%`, `maxDD`, `hold`.
PnL theo nam lay tu `pnl` (realized) trong `printDone.csv` theo nam cua `start`; khoa bang `equity` cuoi nam.

## 5. CHAM PHU

- **5 rate** (win% / TSloss% / mP|SM / mP|SL / meanP) cua **arm3 vs MOC CUA CHINH NEN**
  (`B2 vs B1`, `C2 vs C1`, `A2 vs A1`), CI **block-72h, 2000 rep, seed 20260905**, anchor
  **2021-07-01**; doc **ca hai do rong** (legacy `x1.21` + chuan hoa `inflate(k)`).
  `k=3` (3 nEN) ⇒ `inflate(3)=1.482304`. **"NGOAI CI" = ngoai o CA HAI do rong.**
  `XAU` = ngoai CI **cung huong xau**; `TOT` = ngoai CI cung huong tot.
- **Rao cung `RISK_APPETITE.md` §7** (ban hien hanh): `maxDD` nam **<= 40%**, quy xau nhat
  **>= -20%**, `UW` **<= 250** ngay, tap trung 1 coin **<= 15%**, khong nam am; kiem **CA theo nam
  LAN toan ky**. `maxDD`/`UW` do tren **MTM MOC PHUT** (§7.3), so daily chi de doi chieu.
- `Σfunding/ΣPnL`, `hold`, `turnover`.

## 6. LUAT KET LUAN

- `arm3` **HON** moc tren 1 nEN neu: >= 2 rate ngoai CI **cung huong TOT** **VA** 0 rate `XAU`
  **VA** khong lam nEN do FAIL rao cung (hoac khong lam xau them).
- Neu khong dat ⇒ ghi ro **NULL / khong hon** cho nEN do.
- **Equity/CAGR KHONG phai tieu chi chon** (uu tien "nhieu lenh on dinh", dai han).

## 7. KY LUAT

DEV only (2021-07-01..2025-12-31), **khong cham 2026**. **Khong push.** Khong chay Java/sim tren
Oracle (**Kaggle**, chi phi 0). Khong `claude-run`. Pre-reg nay commit **TRUOC** khi push kernel.
Output: `docs/PREREG_ARM3_3NEN.md` + `docs/RESULT_ARM3_3NEN.md` + script/profile. Commit, khong push.
