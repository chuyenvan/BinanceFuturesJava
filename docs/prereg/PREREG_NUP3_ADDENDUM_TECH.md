# PREREG_NUP3 — ADDENDUM TECH (chi tiet ky thuat khi code sleeve) — 2026-10-26

Prereg goc: `docs/prereg/PREREG_NUP3.md` (MASTER chot o c2b4c462, sha256 `f600be0a…`). Addendum nay KHONG doi co
che, arm, nguong hay seed. No ghi lai cach hien thuc tung cau chu trong prereg va cac cho phai DIEN GIAI / LECH ky
thuat, kem file:dong Java. Viet va commit TRUOC khi push kernel do dau tien. Chua co so PnL/IC nao duoc tinh.

Code: branch `research/nup3-sleeve` (tach tu `research/nup-tier2` a221bf80), worktree `~/src_nup3`, commit **c80d87c2**.
Jar (PrivateConfig STUB) sha256 `b269f96b782275a8089bbae1532f8c68e1aab18cba602bf02ee2a64b3adda051`.
Duong dan Java duoi day tuong doi `src/main/java/com/binance/chuyennd/`; `Sim` = `research/SimulatorMarketLevelTicker1MStopLoss.java`.

## T1. Key (mac dinh TAT => byte-identical)
`tradecore/Configs.java:179-193` (khai bao), `:944-952` (doc qua Cfg/profile):
`SLEEVE_ENABLED=false`, `SLEEVE_PCT=0.99985`, `SLEEVE_SIZE_MULT=1.0`, `SLEEVE_U_MAX=0.35`, `SLEEVE_ARM=V0|V1|V2`,
`SLEEVE_BURST_N=10`, `SLEEVE_BURST_MIN=60`, `SLEEVE_MKT_FLAG_FILE`. Gia tri dung o Pha 1 = dung so prereg.

## T2. Co che hai so trong mot sim (cach giu bat bien so nen)
- Sim chi co MOT bo field so lenh. Them `Sim.Book` (`Sim:1337`) + `enterSleeve/exitSleeve` (`Sim:1622-1634`): doi tham
  chieu `allOrderDone, symbol2OrdersEntry, symbol2OrderRunning, activeRunningIds/Count`, bo dem log (tsx*, entry*,
  orderKeyCollisions, concPerCoinBlocked) va `BudgetManagerSimple` thread-local (`research/BudgetManagerSimple.java:99-102`).
- Pha sleeve chay **CUOI moi tick, SAU toan bo so nen** (`Sim:488-489`, than ham `Sim:1663-1737`): (1) exit/cap nhat cum
  sleeve bang CHINH `startUpdateOldOrderTrading`; (2) DCA theo level va (3) DCA alt bang CHINH `DcaProcessor.getDCA` +
  `createOrder`, cung dieu kien voi nen (chi tren cum sleeve); (4) mo lenh sleeve moi; (5) delist + `updateBalance`
  cung nhip gio/ngay (`isPrintBalance=false` de khong sinh dong `Update … b:` ma kernel parse cho so nen).
- So nen KHONG doc state sleeve. Dong duy nhat cua nen cham toi sleeve la ghi do luong (moc leg dau cum + dem overlap,
  `Sim:2256`, `Sim:1648-1661`), khong vao quyet dinh nao cua nen.
- `tsxDeferred` bo `final` de doi tham chieu theo so (`Sim:119-120`); noi dung/hanh vi nen khong doi.

## T3. Ung vien sleeve (prereg §2 "Ung vien")
- Ghi nhan trong nhanh gate REJECT cua so nen (`Sim:2027-2029` -> `Sim:1637-1646`): CHI `PREDICT_SYMBOL_TRADE`, khong
  phai DCA-signal, co `symbolPred` va `selRank` (tuc nam trong top-K cua tick), va `GateRollingRatio.tier2Pass` = qua q2.
- q2 = phan vi `SLEEVE_PCT` tren CUNG buffer r, tinh MOT lan/gio boi co che TIER2 (`addAndQuery2`, ADDENDUM C cua NUP):
  bat bang `SLEEVE_ENABLED` trong `ai_ml/onnx/entry/GateRollingRatio.java:110-127`, KHONG bat `GATE_TIER2_ENABLED` (nen
  khong co leg tier2; bat ca hai => fail-fast). `addAndQuery2` cho q1 y het `addAndQuery` (q2 chi doc ban sao scratch).
  `tier2Pass` (`GateRollingRatio.java:186`) chi doc, khong nap r, khong notePass/quota (unit test `Nup3SleeveGateTest`).
- **Dien giai D1 — ung vien bi tu choi vi so nen day.** Profile B0 co `GATE_QUOTA_SKIP_WHEN_FULL=true`: khi U nen >= U_MAX,
  `AIRejectFilter.entryGate` tra REJECT ma KHONG goi `threshold` (`ai_ml/onnx/entry/AIRejectFilter.java:83-85`). Day van
  la "bi gate nen tu choi" nen ung vien nay DUOC xet cho sleeve (y do "ngan sach rieng chua viec gianh von"). Khi do q2
  dung la gia tri cache gio gan nhat (co the cua gio truoc neu trong gio chua co lan `threshold` nao) — van nhan qua.
  Dem rieng `cand_book_full`, `opened_book_full` trong `storage/sleeve_summary.json` de MASTER thay ty trong.
- **Dien giai D2 — "K sleeve = 24/dot".** Hieu la K top-rank cua MOI tick selector (giong `SELECTOR_RANK_TOPK=24` cua
  nen, quy uoc cap-then-skip): ung vien sleeve chi lay tu 24 coin dau cua tick; coin dang giu (nen hoac sleeve) bi bo
  qua. KHONG co tran rieng "so cum sleeve moi / dot song". Neu MASTER y khac => phai sua truoc Pha 2.

## T4. Dieu kien MO tung arm (prereg §3) — `Sim:1524-1529`, ap trong `Sim:1739-1778`
- Thu tu kiem: symbol doc quyen (`sleeveSymbolFree`) -> dieu kien arm -> `createOrder` (sizing/tier/grid/per-coin cap).
- V0: khong dieu kien.
- V1: dem moc leg DAU cum (cum moi cua nen HOAC sleeve, moi loai leg mo cum ke ca BIG_DOWN) co gio mo trong
  `[t-60', t)` — nua mo, leg mo tai chinh phut t (ca nen lan sleeve) KHONG tinh, giong S0 (`searchsorted left`).
  `burstCount` `Sim:1511-1522`; khong mo khi so dem >= 10.
- V2: co phut dung san, nhan qua (T7); chi mo khi phut t nam trong mot khoang co. `flagAt` `Sim:1503-1508`.

## T5. Sizing / throttle / U (prereg §2 "Sizing", "Equity")
- `TradeUtils.managerBudgetSleeve` (`tradecore/TradeUtils.java:145-163`) = CUNG cong thuc `managerBudget`
  (`TradeUtils.java:125-140`): `budget = E * F_BASE * clamp(1 - U_s/U_S_MAX, 0, 1) / ladder`, `U_s >= U_S_MAX => null`.
  Sau do y het nen: `tierMultiplier`, ty le bac grid DCA (`Sim:2143`), x `SLEEVE_SIZE_MULT` (`Sim:2168`), tran per-coin
  0,15 tinh tren leg SLEEVE cua coin / E (`Sim:2196`).
- **Dien giai D3 — equity sizing sleeve.** `E` = equity CHUNG = `equityNow()` cua nen (cung nhip gio voi sizing nen, B3)
  + (realized + unrealized) cua sleeve (`Sim:1577-1583`, `Sim:2098-2104`). U_s = margin sleeve / E. So nen van size
  tren equity RIENG cua no (bat buoc de giu bat bien). He qua: neu sleeve lo, `U_nen_max*E_nen + U_S_MAX*E_chung` co the
  > E_chung => do va bao (T8), khong chan.
- Gate leg DCA cua sleeve: so nen goi `aiRejectFilter.entryGate(sp=null)` <=> `!(p15 < EntryGate.threshold(MIN_MOMENTUM_15M,
  null))` (`AIRejectFilter.java:93-98`). Sleeve dung DUNG bieu thuc do qua `EntryGate.pass` ma khong goi aiRejectFilter
  (khong cham bo dem cua nen) — `Sim:1990-1997`. BIG_DOWN khong co o sleeve (sleeve chi mo tu ung vien PREDICT).
- **Lech ky thuat L1 — tier cua sleeve.** `CoinRankManager.getCoinTier` goi `checkAndUpdate` (cap nhat ranking theo nhip
  goi). Neu sleeve goi o phut ma nen khong goi, trang thai ranking nen doc ve sau se khac B0. Sleeve dung `peekCoinTier`
  (`tradecore/CoinRankManager.java:100-113`, goi tai `Sim:2082-2084`): STATIC rank => goi `getCoinTier` (ham theo thoi gian);
  dong => doc tier hien tai, khong cap nhat. Tier chi anh huong luat "TIER_3 khong DCA" (TIER_FLAT=1 => he so size = 1).

## T6. Symbol, DCA, exit, overlap (prereg §2 "Symbol", "Gioi han khac")
- Sleeve KHONG mo symbol nen hoac sleeve dang giu (`Sim:1739-1752`). Nen KHONG xet vi the sleeve.
- DCA va exit (trailing, time-stop 168h, TS_MKT_EXT X14) = CHINH ham nen tren cum sleeve; cum sleeve con mo cuoi ky xu
  ly theo CHINH quy uoc vong "add all order running to done" cua nen (`Sim:1814-1843`).
- Overlap = so lan nen mo cum MOI tren symbol ma sleeve dang giu (`overlap_base_opens_sleeve_sym`). Trong sim hai so
  cung ton tai (live one-way se gop — prereg §7).

## T7. Co W_mkt cho V2 (`research/nup3/build_mkt_flag.py`)
- Dinh nghia DUNG S0: `flag(t)=1 <=> expm1(sum ew_r bar mo luc [t-1440', t-1']) <= -0,08`; bar thieu tren luoi = 0,
  cua so khong co bar => 0. t = moc MO bar, UTC epoch ms (= `ticker.startTime`; da kiem GRASS 2025-11-21 07:36 UTC close
  0,4799 = entry printDone B0 "20251121 14:36" +07).
- Nguon: `edge_attr/index.npz` (2021-07-01 00:01 → 2025-12-31 23:59) + `ew_2026.npz` chi phan >= 2026-01-01 UTC.
  Co dau tien duoc danh gia: 2021-07-02 00:01 UTC (truoc do khong co co => V2 khong mo; sim con dang warm-up gate 7 ngay).
- File `nup3_mkt_flag.csv` (khoang `[start_ms,end_ms)` gop): 2 121 khoang, 91 482 phut co; md5 `f3435d9b…`.
  Kiem: ts int64, bat phut, so phut danh gia = luoi - 1439 (2 760 480), tong do dai khoang = so co; doi chieu DOC LAP
  (tong truc tiep tren mang tho) 12 295 phut (moi bien khoang +-1' + 5 000 ngau nhien) lech 0; doi chieu `s0.EW` lech 0 phut.
- Nap vao sim: dataset Kaggle private `nup3-mkt-flag`, key `SLEEVE_MKT_FLAG_FILE=nup3_mkt_flag.csv` (sim tim theo ten file
  trong `/kaggle/input`, `Sim:1456-1475`); loader kiem bat phut, tang chat, khong chong/ke (`Sim:1478-1500`), log so khoang +
  so phut co (fail-fast neu thieu/rong).

## T8. Do luong (khong quyet dinh) — `Sim:1780-1812`, ghi `storage/sleeve_summary.json`
- U tong moi tick = Σ qty·close (nen + sleeve) / (von + realized nen + realized sleeve + unrealized@close). Bao max, thoi
  diem, so tick > 1,0 (`u_total_fail_ticks`; > 0 => FAIL ky thuat theo prereg). Kem ban margin@entry / equity.
- maxDD MTM gop @bar.low (bao cao tham khao; thuoc do chinh thuc van la pipeline NUP ADDENDUM B, missing = 0), so vi the max.
- `storage/sleeve_cand.csv`: moi ung vien qua q2 + quyet dinh (OPEN / SKIP_HELD_BASE / SKIP_HELD_SLEEVE / SKIP_BURST /
  SKIP_NOFLAG / NOT_OPENED).

## T9. Nhan book trong printDone (prereg §2 "Gan nhan")
- `printDone.csv` = MOI dong nen (y het B0: cung thu tu, cung byte) + SAU DO cac dong sleeve, nhan `book=sleeve` o cot cuoi
  KHONG TEN cua header (header ket thuc bang dau phay) => so cot giu nguyen (`Sim:1572-1574`, `Sim:1845-1867`).
  Loc `grep -v book=sleeve` phai ra dung file B0 (cong G-INV).
- `result.json` cua kernel: `n_trades` dem CA HAI so; `equity_final/b_final` CHI la so nen (dong `Update`). Pipeline cham
  phai tach theo cot book.

## T10. Cong va ha tang
- G-OFF: `SLEEVE_ENABLED=false` khai TUONG MINH trong profile, jar moi, seed a1/s7 => md5 printDone = `tsx-x14-a1`
  (`dc62609b…`) / `tsx-x14-s7` (`622b03e2…`).
- G-INV: chay Pha 1 `nup3-v0-a1` CHINH la cong G-INV (cung cau hinh, khong chay trung). Orchestrator chi push 11 kernel Pha 1
  con lai khi G-OFF a1, G-OFF s7 va G-INV deu PASS; them 1 kernel smoke V2 ngan (`nup3-smk-v2`, a1, toi 20210731) chi de kiem
  nap file co tren Kaggle (khong dung cho so).
- Overrides = dung profile/override B0 (`tsx_driver.B.OV_BASE` + TS_MKT_EXT 336h + ngay X14) + key sleeve. `timeout_s`
  kernel 10 800 (B0 7 200) vi sleeve them tinh toan — chi ha tang.

## T11. Rui ro da biet (ghi de khong tu lua)
- **Ky xac nhan V2 (2021H2) nam trong MOI run DEV** (sim chay 2021-07-01 → 2025-12-31). Seed Pha 1 (a1, s7, s21, s99) la tap
  con cua 8 seed G4. Khi cham Pha 1 phai cat ky 2022–25 va KHONG nhin 2021H2 (nhat la V2) truoc Pha 2.
- Suite test cua repo (chay boi `mvn package`) co test co san thu ket noi Aerospike (226 bi tu choi; ghi 242 bi
  `Live242WriteGuard` chan). Khong phai code NUP3.
