# PREREG_EXIT — Pre-registration thi nghiem E1 (loser time-stop horizon)

Ngay viet: 2026-09-04. Branch: `module`. Code SHA khi pre-register: `f5e8d8e`.

File nay duoc viet va commit TRUOC khi chay bat ky sim nao cua batch E1. Moi tieu chi,
nguong va quy tac quyet definh duoi day la CHOT — khong duoc sua sau khi thay ket qua.

## 1. Gia thuyet co hoc

Time-stop 168h la kenh mat tien lon nhat cua C2b. 15.2% lenh (147/970) thoat qua no,
voi lo trung binh -19% tren DEV va -25% tren VAL.

Do offline (`docs/E0_EXIT_CF.md`) cho thay nhom nay chet vi mot ly do duy nhat: chung
KHONG BAO GIO CHAY.

- 66.6% chua tung vuot +3% lai.
- maxFav median chi 1.83%, va dat duoc ngay o gio thu 4.
- Chi 8.8% tung dat >= 5%.

Nghia la sau vai gio dau, thong tin da day du: cum nay khong co dong luong. Giu chung
them 96 gio nua khong tao them co hoi nao, chi lam lo sau hon.

Chi phi cua viec cat ngan bi chan tren boi ground truth: chi **6.68%** lenh thang
(55/823) co `time_order` > 72h. Tuc du cat xuong 72h, phan lenh thang bi hy sinh
khong the vuot qua ~6.7%.

## 2. Runs: dung 4, khong hon

Bien duy nhat duoc doi: `SIM_LOSER_TIME_STOP_HOURS` ∈ {168, 120, 96, 72}.

Nen: C2b (`profiles/c2b_min.properties`, arm 0.07, `DCA_GRID_SCALE=1.5`). Khong doi
bat ky tham so nao khac.

| Tag | TS_H |
|---|---|
| `X168_parity` | 168 |
| `X120` | 120 |
| `X96` | 96 |
| `X72` | 72 |

Mot dataset build dung chung cho ca 4 run (doi tham so exit khong lam doi dataset).

## 3. Parity gate

Run `X168_parity` PHAI byte-identical voi `/home/ubuntu/java/devrun/C2b`:

- equity `b:60390`
- 970 lenh
- md5 cua `storage/printDone.csv` = `8f7afdfb27b15f5b6d4c886700def93c`

Neu KHONG khop: DUNG toan bo batch, bao cao, va KHONG chay 3 run con lai.

Ngoai le da biet truoc: neo `60390` ung voi `TICKER_SOURCE=aerospike`. Neu ket qua ra
`60395` thi day la `TICKER_SOURCE=file` — ghi nhan va bao cao, KHONG coi la fail parity.

## 4. Tieu chi PRIMARY

Ca hai tieu chi deu la rate tren hang tram lenh, nen `n_eff` lon va it nhieu.

- **P1**: `mean(profit | status=STOP_LOSS_DONE)` phai bot am di khi TS_H giam, va phai
  don dieu qua chuoi 168 -> 120 -> 96 -> 72.
- **P2**: so lenh `STOP_MARKET_DONE` khong duoc giam qua **10%** so voi parity, tuc
  tu 823 khong duoc tut xuong duoi **741**. Ground truth du bao muc giam khoang
  ~6.7%; nguong 10% la bien an toan quanh du bao do.

## 5. Rang buoc CUNG

Vi pham bat ky dieu nao la LOAI, bat ke equity cao den dau:

- maxDD <= 15%
- khong co nam nao am

## 6. Equity KHONG phai tieu chi

Equity duoc bao cao nhung KHONG duoc dung de chon. Ly do dinh luong:

- `sd(Δ CAGR)` cho mot thay doi tham so exit = 2.57pp.
- `E[max nhieu]` cua 50 phep thu = +7.2pp.
- DEV da chay khoang 125 run.

Voi bien do nhieu nhu vay, mot khac biet equity vai pp khong phan biet duoc voi may
man. Noi thang: **equity cao hon ma P2 vi pham = LOAI.**

## 7. Quy tac quyet dinh (chot truoc khi chay)

Chon TS_H **NGAN NHAT** thoa dong thoi: P1, P2, va ca hai rang buoc cung.

Neu khong TS_H nao thoa P2 thi huong nay chet. Quota 4/4 da dung het. CAM them bien
the horizon nao khac.

## 8. Ghi chu thuc thi (viet truoc khi chay, khong phai ket qua)

Ba phat hien ky thuat truoc khi chay, ghi lai de minh bach:

1. **Co che dat tham so.** `Cfg` (src/main/java/com/binance/chuyennd/tradecore/Cfg.java)
   fail-fast exit 2 khi da co `TRADING_PROFILE` ma van con env mang tien to `SIM_`
   (tru cac key trong `INFRA_KEYS`). `SIM_LOSER_TIME_STOP_HOURS` khong nam trong
   `INFRA_KEYS`, nen KHONG the dat qua env. Da xac thuc bang `DumpConfig`: profile +
   env => rc=2. Vi vay TS_H duoc dat TRONG profile: `X168_parity` dung
   `profiles/c2b_min.properties` (da san TS_H=168), ba run con lai dung ban copy
   `profiles/e1_x120.properties`, `e1_x96.properties`, `e1_x72.properties` — moi ban
   chi khac DUNG mot dong `SIM_LOSER_TIME_STOP_HOURS`. Day la doi co che dat tham so,
   khong phai doi tham so nao khac.
2. **Key co duoc doc.** `Cfg.get("SIM_LOSER_TIME_STOP_HOURS")` -> `Configs.LOSER_TIME_STOP_HOURS`
   (Configs.java:469), duoc dung tai SimulatorMarketLevelTicker1MStopLoss.java:644-646.
   `DumpConfig` xac nhan gia tri doi theo profile (168 / 120). Khong phai key tro.
3. **Rui ro parity da biet truoc khi chay.** Baseline C2b chay ngay 2026-09-03 00:21
   tren dataset `/home/ubuntu/wfo_ds_c2` — dataset do KHONG con ton tai. Ngoai ra jar
   hien tai (mtime 2026-09-03 22:51) moi hon luc chay C2b, va `sim.out` cua C2b khong
   co dong `[CFG] profile=`, tuc C2b chay o duong legacy (doc env, khong dung
   `TRADING_PROFILE`). `X168_parity` se chay tren dataset build lai va o duong profile.
   Neu parity fail, day la ba nghi pham co san — va theo muc 3, batch DUNG.
