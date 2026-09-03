# PREREG_TICKLOG — tien dang ky LOG QUYET DINH TUNG TICK CHO TUNG RUN

Chot luc: 2026-09-03, **TRUOC khi sua mot dong code Java nao** va **TRUOC khi tinh bat ky
hieu / CI nao o tang tick**. Neu thu tu commit nguoc lai => moi so o tang nay VOID.

Pham vi: **CHI DEV (2022-01-01 .. 2024-06-30)**. KHONG cham VALIDATION (2024-07-15..2025-12-31),
KHONG cham HOLDOUT 2026. KHONG rebuild bins, KHONG rebuild file OI, KHONG sua
`/home/ubuntu/predwf_map_s1a2/`.

Ly do ton tai: `docs/PAIRED_CALIB.md` §6.2 va `docs/PREREG_GS.md` §12.2 chot rang
**khong ton tai log quyet dinh theo tick cho TUNG run**: `sim.out` chi co 911 dong `Update`
theo ngay, con pool tick `/home/ubuntu/ledger/` **doc lap voi config** (hai run chi khac
exit/sizing/concurrency cho rank-IC y het). Vi vay `PREREG_GS.md` §11.2 khong the thoa cho
gene exit/sizing/concurrency. File nay tien dang ky **ha tang do** de lap cho trong do, va
tien dang ky **phep do** dung de tra loi: ha tang do co mua duoc suc phan biet hay khong.

---

## 1. DON VI MOT DONG LOG va DIEM CHEN TRONG LUONG

Doc code truoc khi chot (`SimulatorMarketLevelTicker1MStopLoss.java`,
`OrderTargetInfoTest.java`, `AIRejectFilter.java`, `BudgetManagerSimple.java`):

- Vong ngoai = **NGAY**; vong trong = **PHUT** (`time2Tickers` 1440 phut/ngay).
- Selector (`time2SymbolPred`) la **luoi 15 PHUT** (`WfoDataset.java:123`, xac nhan bang
  do khoang cach ts trong `predict_wf_*.bin` = 900000 ms). Nen "tick quyet dinh vao lenh"
  = moc 15 phut, KHONG phai moc 1 phut.
- Exit chay **moi phut** cho moi cum dang mo (`startUpdateOldOrderTrading`).

Vi vay **ba** loai dong log, ba stream rieng, khong tron:

| stream | don vi mot dong | diem chen (ham / vi tri) |
|---|---|---|
| `cand.bin` | **mot (tick, symbol) duoc XET de vao lenh** | (a) vong `for (chosenCands)` trong khoi "FUNDING FEE" cua `simulatorWithInitEntry` — ghi 2 quyet dinh chan som `ALREADY_OPEN` / `NO_TICKER`; (b) **truoc TUNG `return` som** trong `createOrder(...)` va tai diem thanh cong (sau `orders.add(order)`) — ghi ly do bi chan hoac `ENTERED` |
| `pos.bin` | **mot (phut, cum dang mo)** — trang thai exit sau khi engine da cap nhat phut do | trong vong `for (short runningSymbolId : currentIds)`, **NGAY SAU** `startUpdateOldOrderTrading(...)` tra ve. Cum vua bi dong => `symbol2OrderRunning[id] == null` => ghi mot dong `CLOSED` |
| `tick.bin` | **mot moc 15 phut** — tong hop danh muc + kich thuoc pool | cuoi phan xu ly moi phut (sau `logByProcessTime(..., "Done budget data", time)`), chi khi `time % 900000 == 0` |

Ly do chon dung ba diem nay:
1. `createOrder` la noi **duy nhat** co du ly do bi chan (pred null / gate / budget / tier /
   grid). Ghi o ngoai thi mat ly do; ghi trong `AIRejectFilter` thi mat cac ly do khac.
2. `startUpdateOldOrderTrading` la noi **duy nhat** exit duoc quyet dinh. Ghi SAU khi no tra
   ve moi thay duoc trang thai **da cap nhat** (arm/trail/SL moi).
3. `tick.bin` o moc 15 phut de moi dong `cand.bin` co dung mot dong `tick.bin` lam mau so.

**Rang buoc bat buoc:** moi diem chen la **read-only** — khong doi bien trang thai nao, khong
doi luong dieu khien, khong them/bo `return`. Vong `for (chosenCands)` doi tu for-each sang
for-chi-so **chi** de lay `rank`; day la phep lap y het tren `ArrayList`.

---

## 2. COT — va gene ma tung cot phuc vu

Nhi phan, **big-endian**, ban ghi **rong co dinh**, ghi qua `GZIPOutputStream`. Khong CSV
(xem §3). Moi file co header 16 byte: magic `TKLG` + version int + recordLen int + recCount
placeholder (ghi lai luc `close()`).

### 2.1 `cand.bin` — 32 byte/dong

| offset | cot | kieu | phuc vu gene nao |
|---|---|---|---|
| 0 | `ts` | long | truc ghep cap (BAT BUOC) |
| 8 | `symbolId` | short | truc ghep cap (BAT BUOC) |
| 10 | `rank` | short | **selector**: TOPK, thu tu xep hang trong tick (−1 = khong phai leg selector) |
| 12 | `decision` | byte | **tat ca**: 0 ENTERED, 1 ALREADY_OPEN, 2 NO_TICKER, 3 NO_PRED, 4 GATE_REJECT, 5 NO_BUDGET, 6 TIER3_DCA_BLOCK, 7 GRID_EXHAUSTED, 8 TOPK_CUT |
| 13 | `levelChange` | byte | **selector/DCA**: tach leg selector vs DCA vs BIG_DOWN |
| 14 | `legIdx` | byte | **sizing/DCA**: cum dang o bac nao |
| 15 | (pad) | byte | can bien 4 byte cho cac float sau |
| 16 | `score` | float | **selector**: diem selector (`symbolPred`), NaN neu leg khong co |
| 20 | `dynThr` | float | **gate**: NGUONG DONG da tinh cho dung score nay tai tick nay |
| 24 | `predRet15m` | float | **gate**: dai luong bi so voi `dynThr` (`predict.predReturn15M`) |
| 28 | `price` | float | **exit/sizing**: gia vao thuc te (`ticker.priceClose`) |

`decision=8 TOPK_CUT` chi duoc ghi khi bat `SIM_TICKLOG_POOL=1` (mac dinh **OFF**): no la
**toan pool** bi top-K loai, khong phai symbol duoc xet. Xem §3.

### 2.2 `pos.bin` — 32 byte/dong

| offset | cot | kieu | phuc vu gene nao |
|---|---|---|---|
| 0 | `ts` | long | truc ghep cap |
| 8 | `symbolId` | short | truc ghep cap |
| 10 | `flags` | byte | bit0 `armed` (`priceSL != null`), bit1 `closedThisMinute`, bit2 con mo cuoi ky |
| 11 | `status` | byte | `OrderTargetStatus.ordinal()` — **exit**: TP/SL/STOP_MARKET |
| 12 | `legCount` | byte | **sizing/DCA** |
| 13 | (pad) x3 | — | can bien |
| 16 | `entry` | float | **exit**: gia entry cum (da binh quan) |
| 20 | `lastPrice` | float | **exit**: gia dong nen phut do => tinh duoc unrealized moi phut |
| 24 | `maePeak` | float | **exit**: DINH that cua cum => do `arm` va `giveback` |
| 28 | `priceSL` | float | **exit**: SL hien tai (NaN neu chua arm) |

`quantity` KHONG nam trong dong nay: no la hang so cua cum giua hai lan DCA va lay duoc tu
`printDone.csv` + `legCount`; ghi lai moi phut la lang phi 4 byte × 2.5M dong. Doi lai, dai
luong tinh tu `pos.bin` la **ROI** (`lastPrice/entry − 1`), khong phai USD; USD lay tu
`tick.bin`.

### 2.3 `tick.bin` — 32 byte/dong

| offset | cot | kieu | phuc vu gene nao |
|---|---|---|---|
| 0 | `ts` | long | truc ghep cap |
| 8 | `poolSize` | short | **selector**: kich thuoc pool tick (mau so cua rank-IC) |
| 10 | `nPassAbs` | short | **gate/selector**: so coin qua tran ung vien tuyet doi |
| 12 | `nCand` | short | **selector**: so ung vien THUC SU duoc xet (= `chosenCands.size()`) |
| 14 | `nActive` | short | **concurrency**: so cum dang mo |
| 16 | `balanceBasic` | float | **sizing**: von co so (mau so cua budget) |
| 20 | `profitRealized` | float | **tat ca**: PnL da thuc hien luy ke |
| 24 | `unrealClose` | float | **tat ca**: Σ qty·(close − entry) tai tick (mark-to-market) |
| 28 | `marginRunning` | float | **sizing/concurrency**: von dang bi chiem |

`equity(t) = balanceBasic + profitRealized + unrealClose` — **day la cot xuong song cua phep
do o §6**. `marginRunning` phuc vu gene sizing/breaker.

**Cot bi BO co y** (khong phuc vu phep do nao trong §6, nen khong ghi): ten symbol dang chuoi
(da co `symbolId` + mapper), `predict` day du (23 field — chi `predReturn15M` vao gate),
`marketData` (rateUp/rateDown — khong phai gene cua wave nay), `volume`, `rateChange`,
`profitMin`, `minPrice`, `tickerOpen`.

---

## 3. UOC LUONG DUNG LUONG — chot TRUOC khi code

Do dac (khong doan) tu `/home/ubuntu/predwf_map_s1a2/` (10 file, 403,940,914 byte, 26 byte/rec):

| dai luong | gia tri do duoc |
|---|---|
| khoang cach hai tick selector | **900,000 ms (15 phut)** |
| so tick selector / quy (file 90 ngay) | **8,640** = 90 × 96 |
| so tick selector tren DEV | **87,456** = 911 × 96 |
| so phut DEV | **1,311,840** = 911 × 1440 |
| pool/tick (2023Q1) | min 139, trung vi 149, max 166 |
| pool/tick (2024Q2) | 2,256,504 / 8,640 = **261** |
| **TOAN POOL DEV (cross-product)** | **15,536,189 ban ghi** (= 403,940,914 / 26) |
| dong thoi trung binh (do tu `printDone.csv` C2b: Σ gio giu 40,031h / span 21,462h) | **1.87 cum** |

Uoc luong dung luong, **truoc nen**:

| stream | so dong | byte/dong | thoi |
|---|---|---|---|
| `tick.bin` | 87,456 | 32 | **2.8 MB** |
| `cand.bin` (TOPK=8, `SIM_TICKLOG_POOL=0`) | 87,456 × 8 = 699,648 | 32 | **22.4 MB** |
| `pos.bin` (moi PHUT, dong thoi 1.87) | 1,311,840 × 1.87 ≈ 2,453,000 | 32 | **78.5 MB** |
| **TONG mac dinh** | | | **≈ 104 MB thoi, ≈ 30-45 MB sau gzip** |
| `cand.bin` neu bat `SIM_TICKLOG_POOL=1` | 15,536,189 | 32 | **+497 MB thoi (≈ +150 MB gzip)** |
| **TONG voi POOL=1** | | | **≈ 601 MB thoi, ≈ 180-200 MB gzip** |

**Muc tieu cung 1.5 GB/run: DAT, du 15x o che do mac dinh va 7x o che do POOL=1.**

### 3.1 DINH CHINH de bai — "cross-product hang chuc GB" la SAI

De bai chot "nếu ghi cả cross-product thì sẽ hàng chục GB — không được". **Sai o codebase nay.**
Nguyen nhan: de bai gia dinh tick = 1 phut. Luoi selector la **15 phut**, nen cross-product chi
la 15.5M dong (**0.50 GB nhi phan / ~1.1 GB CSV**), khong phai hang chuc GB. Ghi ro de khong ai
thiet ke qua bao thu vi mot con so sai. Ba co che giam **van duoc giu** (chung dung vi ly do
khac, khong phai vi dung luong):

1. **Chi ghi symbol THUC SU duoc xet** (`chosenCands`, K=8) — mac dinh. Ly do that: cac symbol
   bi top-K loai KHONG co quyet dinh nao de do o tang exit/sizing; ghi chung chi lam loang.
   Muon do gene selector/TOPK thi bat `SIM_TICKLOG_POOL=1` (co gia 497 MB, van trong tran).
2. **Nhi phan co dinh + gzip** thay CSV — 32 byte/dong thay ~70; giam ~2.2x truoc nen.
3. **`quantity` khong ghi lai moi phut** (§2.2) — giam 4 byte × 2.45M dong.

### 3.2 Chan cung ve dia
`df -h /` con **19G** va co agent khac dang chay. Truoc moi run co bat log: neu `Avail < 6G`
thi **DUNG**, khong chay. Sau moi buoc: `du -sh /home/ubuntu/tick/<TAG>`. `wfo_ds_*` tam xoa
ngay sau moi run.

---

## 4. CO BAT/TAT — qua cong Cfg, khai trong profile

Bon key, doc **duy nhat** qua `com.binance.chuyennd.tradecore.Cfg.get(...)` (KHONG
`System.getenv` truc tiep — `tools/check_cfg_gateway.sh` kiem):

| key | mac dinh | y nghia |
|---|---|---|
| `SIM_TICKLOG` | (khong khai) = **OFF** | `1` = bat. OFF => moi diem chen la mot `if (false)` |
| `SIM_TICKLOG_DIR` | `/home/ubuntu/tick` | thu muc goc; log ra `<DIR>/<SIM_TICKLOG_TAG>/` |
| `SIM_TICKLOG_TAG` | `run` | ten thu muc con |
| `SIM_TICKLOG_POOL` | `0` | `1` = ghi ca pool bi top-K loai (decision 8) |
| `SIM_TICKLOG_POS_EVERY_MIN` | `1` | thua thot `pos.bin` (1 = moi phut) |

Tien to `SIM_` nam trong `Cfg.TRADING_PREFIXES` => khi da dat `TRADING_PROFILE` thi cac key nay
**bat buoc** khai trong profile (dat qua env se fail-fast exit 2, dung y). Profile
`profiles/c2b_ticklog.properties` = `profiles/c2b.properties` + 3 dong ticklog; hai profile
khac nhau DUNG o cac dong ticklog va khong dong nao khac.

Ghi log dung **writer nhi phan rieng co buffer** (`BufferedOutputStream` 1 MB ->
`GZIPOutputStream`), KHONG di qua logger dong-theo-dong. SLF4J chi dung cho thong bao van hanh:
mo file, dong file, so dong da ghi, loi. **CAM** `System.out` / `System.err` /
`printStackTrace` trong code moi.

---

## 5. CONG NGHIEM THU — hai phan, khong dat thi DUNG

1. **Tat co => byte-identical baseline C2b.** `tools/run_c2b_dev.sh` voi
   `profiles/c2b.properties`; `cmp -s <(tail -n +2 A) <(tail -n +2 B)` tren `printDone.csv`;
   equity cuoi **60390**; `TICKER_SOURCE=aerospike`.
2. **Bat co => CUNG byte-identical `printDone.csv`.** Cung lenh `cmp`, profile
   `profiles/c2b_ticklog.properties`. Day la phan quan trong nhat: neu bat log ma ket qua doi
   thi code da can thiep vao luong quyet dinh => phai sua, khong duoc ghi chu "sai so nho".
3. **Phu (khong bat buoc, nhung se bao cao):** hai run cua §6 (`R5_arm7` / `R6_arm8`) chay lai
   voi co BAT phai cho `printDone.csv` byte-identical voi ban da luu ngay 2026-09-02.

---

## 6. PHEP DO O TANG TICK — chot TRUOC khi thay ket qua

### 6.1 Cap duoc do
`R5_arm7` vs `R6_arm8` (**exit thuan**, arm 7% vs 8%). Chon vi `PAIRED_CALIB.md` §3 da do cap
nay o **ca hai** tang cu voi cung seed: equity `MDE80 = 3.607 pp` (block 21 ngay),
tung lenh `MDE80 = 3.282 %/nam` (khoi 72h) — ti le 0.91, tuc **khong phan biet duoc**.
Do la diem so de danh bai.

### 6.2 Phuong phap — theo `docs/PREREG_CI.md`, khong doi mot chu
- Khoi **72h wall-clock** chinh; do ben o **24h** va **168h** (`PREREG_CI` §3.1).
- `N_REP = 2000`, `SEED = 20260903`, `numpy.random.default_rng(SEED)`, resample lai tu seed cho
  tung (cap, do dai khoi) (`PREREG_CI` §2.4).
- Moving-block **circular**, mot danh sach chi so khoi dung **Y NGUYEN cho ca hai run**
  (ghep cap bat buoc, `PREREG_CI` §2.3). CI95 = phan vi 2.5/97.5 (percentile, khong BCa).
- `MDE80 = (z_0.975 + z_0.80) * sd_boot = 2.80158 * sd_boot`.
- **maxDD KHONG bootstrap** (`PREREG_CI` §2.5). Rang buoc maxDD giu o tang equity, doc lap.

### 6.3 Dai luong CHINH `E1` — va mot DU DOAN duoc ghi truoc
`E1 = pnlsum_tick`: tai moi tick 15 phut `t`, `eq(t) = balanceBasic + profitRealized +
unrealClose` (cot cua `tick.bin`); luong `f(t) = eq(t) − eq(t−1)`, `f(t_0) = eq(t_0) − 35000`.
Thong ke khoi `S_b = Σ_{t in b} f(t) / 35000`. `d = mean_b(S_b^A) − mean_b(S_b^B)`, quy ve
`%/nam` bang `× (8760/72) × 100 = × 121.667 × 100` (dung cong thuc `pnlsum` cua
`PREREG_PAIRED.md` §8 — hop le vi E1 chuan hoa theo VON, khong theo notional; xem canh bao
`PAIRED_CALIB` §3.3).

**DU DOAN GHI TRUOC (falsifiable):** `S_b` la **tong luong theo khoi**, va tong luong tren mot
khoi **khong phu thuoc tan so lay mau ben trong khoi** (`Σ f(t)` telescope ve `eq(cuoi khoi) −
eq(dau khoi)`). Vi vay lay mau 15 phut thay vi 1 ngay **khong** them thong tin cho E1, va
`MDE80(E1)` du kien **nam trong ±25%** cua tang equity **khi so o CUNG do dai khoi**. Neu ket qua
lech xa hon thi phai truy nguyen (ke toan realized/unrealized lech, hay loi ghi log), KHONG
duoc doc la "tang tick nhay hon".

### 6.4 DOI CHUNG BAT BUOC `E0` — tang equity o CUNG do dai khoi 72h
`PAIRED_CALIB` so `MDE80` tang equity o **block 21 ngay** voi tang tung lenh o **khoi 72h**.
Hai do dai khoi khac nhau => con so 0.91 lan lon **hai** nguyen nhan (tan so lay mau vs gia dinh
phu thuoc chuoi). Vi vay bat buoc bao cao **ba** con so cho cung mot cap:

| ma | tang | don vi lay mau | do dai khoi |
|---|---|---|---|
| `E0a` | equity CAGR (`PREREG_CI` §2) | 1 ngay | **21 ngay** (tien dang ky cu) |
| `E0b` | equity, **cung dai luong tong luong nhu E1** | 1 ngay | **72h** (doi chung do dai khoi) |
| `E1` | tick | **15 phut** | **72h** |

Ket luan "ha tang tick co mua duoc suc phan biet" **chi** duoc phat bieu tu `E1` vs `E0b`
(cung do dai khoi). `E1` vs `E0a` bao cao kem de doi chieu voi `PAIRED_CALIB`, nhung **khong**
duoc dung lam bang chung cai thien.

### 6.5 Dai luong PHU `E2` — cai duy nhat tang tick lam duoc ma tang equity khong
`E2 = roimean_tick`: tai moi tick, `roi_r(t) = mean_c (lastPrice_c(t)/entry_c − 1)` tren cac cum
dang mo (tu `pos.bin`, thua thot ve luoi 15 phut); thong ke khoi = **trung binh theo tick trong
khoi** (khoi khong co cum nao mo => bo khoi do o CA HAI run, dem so khoi bi bo). Dai luong nay
**doc lap voi so lenh va voi sizing**, va no do dung thu ma gene exit dieu khien: chat luong cua
so lenh DANG MO tai moi thoi diem. Don vi la ROI, **khong** quy ve %/nam duoc, nen `E2`
**khong** duoc so truc tiep voi `MDE80` cua `E0a` — bao cao `d`, CI95, `sd`, `t`.

### 6.6 LUAT DOC — chot truoc
- **Cai thien that** = `MDE80(E1) < 0.75 × MDE80(E0b)` **va** `E1` nhat quan dau voi `E0b`.
- **Khong cai thien** = ti le `MDE80(E1)/MDE80(E0b)` trong `[0.75, 1.33]`.
- **Te hon** = ti le > 1.33.
- Bat ky ket qua nao trong ba muc tren **deu duoc bao cao nguyen trang**. Ket qua "khong cai
  thien" la ket qua **co gia tri**: no noi ha tang nay khong nen dau tu them, va phai duoc ghi
  thang chu khong duoc doi dai luong de tim con so dep.
- **KHONG** duoc chon do dai khoi sau khi xem ket qua. **KHONG** duoc doi dai luong chinh (E1)
  sau khi xem ket qua. Neu `E2` dep hon `E1` thi do la **de nghi cho pre-reg sau**, khong phai
  phan quyet cua lan nay.

---

## 7. CAI NAY KHONG LAM / GIOI HAN DA BIET

1. **Khong noi gi ve VALIDATION/HOLDOUT.** Moi so in-sample DEV.
2. **Khong thay the rang buoc maxDD** (`PAIRED_CALIB` §9.2 / `PREREG_PAIRED` §9.2): maxDD la
   tinh chat cua duong equity, khong mot dai luong tick nao ghi nhan duoc no.
3. **Khong sua `PREREG_GS.md` §11.2**, khong mo lai nhanh nao, khong doi diem uoc luong nao
   trong `AUDIT_APPLIED.md` / `CI_REAUDIT.md` / `PAIRED_CALIB.md`.
4. **Log nay khong lam tang so CUOC DOC LAP.** No lam tang **tan so lay mau**. Hai thu khac
   nhau; §6.3 ghi ro du doan hau qua cua su khac nhau do.
5. **Khong dung cho WFO/HPO da luong.** `TickDecisionLog` co state static (rank ngu canh,
   writer) => chi hop le cho MOT sim don luong. Bat trong WFO nhieu sample = ket qua log rac.
   Ghi ro trong javadoc; khong them khoa (khoa se lam cham vong nong).
6. **`pos.bin` khong co `quantity`** (§2.2) => moi dai luong tu `pos.bin` la ROI, khong phai USD.
   Muon USD thi dung `tick.bin`.
