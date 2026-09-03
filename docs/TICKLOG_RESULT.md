# TICKLOG_RESULT — ket qua ha tang log quyet dinh tung tick + do suc phan biet

Ngay: 2026-09-03. Pham vi: **CHI DEV (2022-01-01 .. 2024-06-30)**. KHONG cham VALIDATION
(2024-07-15..2025-12-31), KHONG cham HOLDOUT 2026. KHONG rebuild bins / file OI, KHONG sua
`/home/ubuntu/predwf_map_s1a2/`.

Tien dang ky: **`docs/PREREG_TICKLOG.md`, commit `4d80fb9`** — chot **TRUOC** khi sua mot dong
code (commit code la `4074f8c`, sau `4d80fb9`). Moi dai luong / do dai khoi / luat doc trong
bao cao nay da co trong `4d80fb9`.

Ban chay: `/home/ubuntu/java/stage/tl_gate.out`, `tl_pair.out`, `tl_an.out`.
Cong cu: `tools/run_ticklog_gate.sh`, `tools/run_ticklog_pair.sh`,
`research/analysis/tick_paired.py`.

---

## 1. CONG NGHIEM THU — CA HAI PHAN PASS

`tools/run_ticklog_gate.sh`, `TICKER_SOURCE=aerospike`, `jar md5=4334ebeae8ef`,
bins `sha256_16=0f8721558fbd87ef`, baseline `/home/ubuntu/java/devrun/C2b`.

| # | co | profile (PROFILE_HASH) | equity cuoi | md5 `printDone.csv` | ket |
|---|---|---|---|---|---|
| baseline | — | `c2b.properties` (`7fd2895a1e7fefe0`, 23 key) | **60390** | `8f7afdfb27b15f5b6d4c886700def93c` | — |
| GATE 1 | **TAT** | `c2b.properties` (`7fd2895a1e7fefe0`, 23 key) | **60390** | `8f7afdfb27b15f5b6d4c886700def93c` | **PASS** |
| GATE 2 | **BAT** (POOL=1) | `c2b_ticklog.properties` (`4ed67165e217a046`, 27 key) | **60390** | `8f7afdfb27b15f5b6d4c886700def93c` | **PASS** |

Lenh that (in nguyen trong `tools/run_c2b_dev.sh`):

```
cmp -s <(tail -n +2 /home/ubuntu/java/devrun/C2b_TLOFF/storage/printDone.csv) <(tail -n +2 /home/ubuntu/java/devrun/C2b/storage/printDone.csv)
  -> PASS: C2b_TLOFF printDone.csv BYTE-IDENTICAL voi C2b
cmp -s <(tail -n +2 /home/ubuntu/java/devrun/C2b_TLON/storage/printDone.csv)  <(tail -n +2 /home/ubuntu/java/devrun/C2b/storage/printDone.csv)
  -> PASS: C2b_TLON printDone.csv BYTE-IDENTICAL voi C2b
```

Ca ba run cho `done:147/970/970`, `b:60390`. Hai profile khac nhau **DUNG** 4 dong ticklog
(`diff` in trong `tl_gate.out`), khong dong nao khac.

### 1.1 Cong thu BA (khong bat buoc) — cap cua VIEC 3 cung byte-identical
Chay lai `R5_arm7` / `R6_arm8` (env-mode, tai lap chinh xac `dev_rob2.sh`) voi co **BAT**:

| run moi | equity | md5 | ban luu 2026-09-02 | ket |
|---|---|---|---|---|
| `R5_TL` | 53968 (1025 lenh) | `81dd1704124e18353167377f58991ce8` | `R5_arm7` cung md5 | **PASS** |
| `R6_TL` | 53689 (974 lenh) | `7f07dae6d880805988b7be9c31383575` | `R6_arm8` cung md5 | **PASS** |

=> Ghi log **khong doi mot quyet dinh nao**, tren ca hai duong cau hinh (profile-mode va env-mode)
va ca hai che do (POOL=0 / POOL=1). Ngoai ra: equity cuoi doc tu `tick.bin` khop `sim.out`
(53968.8 vs 53968 / 53689.9 vs 53689 / 60390.9 vs 60390 — `sim.out` in so nguyen).

---

## 2. DUNG LUONG — UOC LUONG vs THAT. Uoc luong SAI 14.6 lan (nhung tran van dat)

| stream | so dong that | byte thoi that | sau gzip | uoc luong `PREREG_TICKLOG` §3 (thoi) | sai so |
|---|---|---|---|---|---|
| `tick.bin` | 87,456 | 2.80 MB | 0.56 MB | 2.8 MB | **dung** |
| `pos.bin` (moi phut) | 2,401,870 | 76.9 MB | 13.8 MB | 78.5 MB | **dung (−2%)** |
| `cand.bin` POOL=0 | 10,198,019 | 326.3 MB | 82.7 MiB | 22.4 MB | **thap 14.6x** |
| `cand.bin` POOL=1 | 226,067,081 | **7,234.7 MB** | **836.0 MB** | 497 MB | **thap 14.6x** |

Tong tren dia mot run DEV:

| run | che do | tong tren dia |
|---|---|---|
| `C2b_TLON` | POOL=1, posEveryMin=1 | **811 MiB** (850,286,524 byte) |
| — | | `cand.bin.gz` 836.0 MB / `pos.bin.gz` 13.8 MB / `tick.bin.gz` 0.56 MB |
| `R5_TL` | POOL=0, posEveryMin=1 | **97.0 MiB** (101,690,632 byte) |
| `R6_TL` | POOL=0, posEveryMin=1 | **98.5 MiB** (103,237,231 byte) |

**Muc tieu cung ≤ 1.5 GB/run: DAT** — 0.10 GB o che do mac dinh, 0.81 GB o che do nang nhat.

### 2.1 DINH CHINH `PREREG_TICKLOG` §3.1 — chinh no SAI, va de bai DUNG hon toi
`PREREG_TICKLOG` §3.1 tuyen bo de bai sai khi noi "cross-product hang chuc GB", voi ly do
"luoi selector la 15 phut nen tick quyet dinh vao lenh la 15 phut". **Cai do sai.**

Do dac sau khi co log (`tl_candsum` / `probe11`): khoang cach hai `ts` lien tiep trong `cand.bin`
la **60,000 ms = 1 PHUT**, moi phut co 129-262 dong. Nguyen nhan: `predict_wf_*.bin` la luoi 15
phut, nhung `WfoDataset` **forward-fill** sang moi phut (chinh la "BUG-FIX 2026-07-13" o
`WfoDataset.java:123`), nen `time2SymbolPred.get(time)` tra ve pool o **moi** phut va engine
**xet lai top-K moi phut** voi diem cu 15 phut. Vay:

- Tick **quyet dinh vao lenh** = **1 phut** (1,274,752 phut co pool tren DEV), khong phai 15 phut.
- Cross-product that = **226,067,081 dong = 7.23 GB nhi phan**, va **~15-16 GB neu la CSV**
  (~70 byte/dong). => **de bai dung**: CSV cross-product **la** hang chuc GB.
- Ba co che giam trong §3 vi vay **khong phai tuy chon** ma la **bat buoc**: nhi phan 32B
  (thay ~70B CSV) + gzip (ti so do duoc **8.65x** — thap vi cot toan float ngau nhien) + mac dinh
  chi ghi top-K (giam 22.2x).

Ghi nguyen trang, khong sua `PREREG_TICKLOG.md`. Bai hoc: uoc luong dung luong **phai** do tan so
tick tu chinh duong ma engine di (dem `.get(time)` khong null), khong duoc suy tu tan so cua
**du lieu goc**.

---

## 3. CHI PHI THOI GIAN

| run | co | `simMs` (vong sim) | `totalLoopMs` | wall |
|---|---|---|---|---|
| `C2b_TLOFF` | tat | **86,001** | 211,452 | 276 s |
| `C2b_TLON` | bat, **POOL=1** | **1,368,526** (**15.9x**) | 1,497,018 (7.1x) | 1,555 s (5.6x) |
| `R5_arm7` (2026-09-02) | tat | **87,231** | 222,680 | — |
| `R5_TL` | bat, POOL=0 | **184,749** (**2.12x**) | 346,961 (1.56x) | 377 s |
| `R6_arm8` (2026-09-02) | tat | 88,213 | 226,334 | — |
| `R6_TL` | bat, POOL=0 | 183,020 (2.07x) | 343,334 (1.52x) | 372 s |

Che do mac dinh (POOL=0): **+112% vong sim, +56% tong vong** (doc kline khong doi). Che do POOL=1:
**+1490% vong sim** — chi dung khi that su can do gene TOPK/selector, khong dung mac dinh.

---

## 4. VIEC 3 — TANG TICK CO MUA DUOC SUC PHAN BIET KHONG?

Cap: **`R5_arm7` vs `R6_arm8`** (exit thuan: arm 7% vs 8%), dung hai run vua chay lai
(`R5_TL`/`R6_TL`, byte-identical §1.1). Phuong phap `PREREG_CI` (khoi 72h chinh, 24h/168h do ben,
`N_REP=2000`, `SEED=20260903`, ghep cap cung chi so khoi, CI95 percentile,
`MDE80 = 2.80158*sd_boot`).

### 4.1 Bang so — CAU TRA LOI CHINH

| ma | tang | don vi lay mau | do dai khoi | n_khoi | `d` | CI95 | `sd_boot` | **MDE80** |
|---|---|---|---|---|---|---|---|---|
| `E0a` | equity CAGR | 1 ngay | **21 ngay** | 44 | **+0.247 pp** | [−2.238, +2.736] | 1.288 | **3.607 pp/nam** |
| `E0b` | equity, tong luong | 1 ngay | **72h** | 304 | **+0.319 %** | [−2.223, +3.254] | 1.436 | **4.023 %/nam** |
| **`E1`** | **tick, tong luong** | **15 phut** | **72h** | 304 | **+0.319 %** | [−2.055, +2.732] | 1.214 | **3.400 %/nam** |

Do ben cua `E1`: khoi 24h `MDE80 = 3.703`, khoi 168h `MDE80 = 3.255`. Khong khoi nao loai tru 0.

**Phan quyet theo luat da chot (`PREREG_TICKLOG` §6.6):**

```
MDE80(E1) / MDE80(E0b) = 3.400 / 4.023 = 0.845   -> nam trong [0.75, 1.33]
=> KHONG CAI THIEN
```

Doi chieu (khong dung lam bang chung, `PREREG_TICKLOG` §6.4):
`MDE80(E1)/MDE80(E0a) = 3.400/3.607 = 0.943`; tang **tung lenh** cua `PAIRED_CALIB`
(`pnlsum`, khoi 72h) = **3.282 %/nam**.

Quy ve "so nam DEV can de phan biet 3pp/nam o power 80%" (`= 2.45 * (MDE80/3)^2`):
**E0a 3.54 nam / E0b 4.41 nam / E1 3.15 nam / tung lenh 2.93 nam.** Cung mot bac.

### 4.2 DU DOAN GHI TRUOC DA DUNG — va do la ly do khong cai thien
`PREREG_TICKLOG` §6.3 ghi truoc: `S_b` la **tong luong** theo khoi, `Sigma f(t)` telescope ve
`eq(cuoi khoi) − eq(dau khoi)`, nen **lay mau day hon khong them thong tin**; du kien `MDE80(E1)`
nam trong **±25%** cua tang equity o **cung** do dai khoi.

Do duoc: diem uoc luong cua `E1` va `E0b` **giong nhau den 3 chu so** (`+0.319`), va
`MDE80` lech **15.5%** (3.400 vs 4.023) — **trong** dai da du doan. Phan lech con lai den tu
mot khac biet **ke toan**, khong tu thong tin: `E0b` doc `unP` cua `updateBalance` (lay mau theo
gio), `E1` doc `Sigma qty*(close − entry)` tai dung moc 15 phut. Vay:

> **Nut co that khong phai tan so lay mau. No la SO KHOI DOC LAP.**
> Tang tick lam tan so lay mau tang 96 lan (911 -> 87,456 quan sat) ma `MDE80` gan nhu khong
> doi, vi so **khoi 72h** van la 304 va tong luong trong moi khoi khong phu thuoc tan so lay mau.

### 4.3 Dai luong PHU `E2` (`roimean_tick`) — **KHONG** dung de doi phan quyet

| khoi | n_khoi giu | n_khoi bo | `d` (ROI) | CI95 | `sd` | `t` | loai tru 0 |
|---|---|---|---|---|---|---|---|
| 24h | 417 | 494 | **−0.002720** | [−0.004988, −0.000605] | 0.001114 | −2.44 | **Y** |
| **72h** | **171** | **133** | **−0.004233** | [−0.009498, **+0.000076**] | 0.002392 | −1.77 | **n** |
| 168h | 97 | 34 | −0.003561 | [−0.007097, −0.000085] | 0.001801 | −1.98 | **Y** |

Doc dung: `E2` **khong** loai tru 0 o do dai khoi **chinh** (72h) — theo luat, day khong phai
"thang". No loai tru 0 o 24h va 168h nhung **khong** o 72h, tuc ket luan **phu thuoc do dai khoi**
=> dung `PREREG_CI` §3.1 canh bao, phai doc la **khong phan biet duoc**. Dau am (`R5` arm7 giu
so lenh **te hon** `R6` arm8 tinh theo ROI trung binh tren so lenh dang mo) nguoc dau voi
`E1` (`+0.319%/nam` nghieng `R5`) — vi `E1` co **sizing va so lenh**, `E2` thi khong.

Mot nguyen nhan ky thuat cua `E2` phai ghi ro: **`nActive` trung vi = 0** — hon mot nua moc 15
phut khong co lenh nao mo (dong thoi trung binh chi 1.87 nhung phan bo rat lech). Vi vay `E2`
**bo 133/304 khoi** o 72h. Do la mot dai luong yeu vi ly do co cau, khong phai vi nhieu.

`E2` chi la **de nghi cho mot pre-reg sau** (`PREREG_TICKLOG` §6.6), khong phai phan quyet.

---

## 5. CAI TANG TICK THUC SU MUA DUOC: PHAN RA QUYET DINH 1-1 THEO TICK

Day la thu ma **ca** tang equity **va** tang tung lenh khong the cho. Ghep dung tren khoa
`(ts, symbolId, levelChange)`:

| dai luong | `R5_TL` (arm 7%) | `R6_TL` (arm 8%) |
|---|---|---|
| phut-ung-vien duoc XET | 10,198,019 | 10,198,019 |
| khoa CHUNG | **10,197,982** | chi A 37 dong / chi B 37 dong |
| trong do leg selector (`PREDICT_SYMBOL_TRADE`, ordinal 5) | 10,194,280 | 10,194,280 |
| leg `DCA_LEVEL1` (ordinal 2) | 3,619 | 3,619 |
| leg `BIG_DOWN` (ordinal 3) | 120 | 120 |
| `ENTERED` | **1,025** | **974** |
| `GATE_REJECT` | 9,635,332 | 9,583,423 |
| `ALREADY_OPEN` | 556,318 | **608,290** |
| `NO_TICKER` | 1,725 | 1,713 |
| `GRID_EXHAUSTED` | 3,619 | 3,619 |

**Tren 10,197,982 khoa chung, dung 63,604 (0.6237%) co quyet dinh KHAC nhau**, va phan ra cua
chung chi ra co che cua gene exit **chinh xac**:

| `R5` (arm 7%) | `R6` (arm 8%) | so phut |
|---|---|---|
| `GATE_REJECT` | `ALREADY_OPEN` | **57,707** |
| `ALREADY_OPEN` | `GATE_REJECT` | 5,798 |
| `ENTERED` | `ALREADY_OPEN` | **60** |
| `NO_TICKER` | `ALREADY_OPEN` | 21 |
| `ALREADY_OPEN` | `ENTERED` | **9** |
| `ALREADY_OPEN` | `NO_TICKER` | 9 |

Doc: nang arm 7% -> 8% lam cum **giu lau hon** => **+51,972 phut** coin bi khoa vi con vi the
(`ALREADY_OPEN`), va chinh viec khoa suat do lam **69 quyet dinh vao lenh** doi (60 lenh `R5`
vao ma `R6` khong, 9 nguoc lai) => `1025` vs `974` lenh. Do la **toan bo** co che truyen tu mot
tham so exit sang so lenh, do duoc tung phut, khong phai suy dien.

Mot con so nua chi tang nay cho: **`GATE_REJECT` chiem 94.5%** (9.64M / 10.20M) moi
phut-ung-vien; `ENTERED` chi **0.010%**. Rang buoc binding cua he **khong phai** top-K hay von —
**la gate MOM15**. `NO_BUDGET` = **0** dong tren ca hai run (von chua bao gio la rang buoc).

---

## 6. KET LUAN THANG

1. **Ha tang chay dung va TRO khi tat.** Ca hai cong byte-identity PASS (`printDone.csv` md5
   `8f7afdfb...`, equity 60390), cong thu ba tren cap `R5`/`R6` cung PASS.
2. **Dung luong trong tran** (0.10 GB mac dinh / 0.81 GB POOL=1 so voi tran 1.5 GB) — **nhung
   uoc luong truoc khi code sai 14.6 lan** (§2.1); no dat tran nho gzip 8.65x, khong nho tinh dung.
3. **Ha tang nay KHONG mua duoc suc phan biet cho dai luong PnL tong hop.**
   `MDE80(E1)/MDE80(E0b) = 0.845` — trong dai "khong cai thien" da chot truoc. Diem uoc luong
   giong het (`+0.319%/nam`). Ly do la mot dong nhat dai so, khong phai mot khiem khuyet trien
   khai: tong luong tren mot khoi khong phu thuoc tan so lay mau ben trong khoi.
   **Nut co la SO KHOI DOC LAP (304 khoi 72h tren 2.45 nam DEV), khong phai tan so lay mau.**
   => `PREREG_GS.md` §12.4 muc 2 ("lam simulator xuat log quyet dinh tung tick") **khong** la
   duong ra cho bai toan cong suat. Muc 2 con lai — **tang so cuoc doc lap** — moi la duong ra.
4. **Nhung no mua duoc mot thu khac, that:** phan ra quyet dinh 1-1 theo tick (§5). Voi cap
   exit-thuan nay no chi ra chinh xac 63,604 phut khac quyet dinh va 69 lenh khac nhau, va chi ra
   `GATE_REJECT` la rang buoc binding (94.5%) trong khi `NO_BUDGET = 0`. Do la gia tri **chan
   doan**, khong phai gia tri **thong ke**; no khong thoa `PREREG_GS` §11.2.
5. **Khuyen nghi (khong phai quyet dinh):** giu ha tang nay o che do mac dinh (POOL=0, +56% thoi
   gian, 0.10 GB) nhu cong cu **chan doan** cho gene exit/sizing/concurrency. **Khong** dau tu
   them de bien no thanh tieu chi quyet dinh — §4 cho thay khong co gi de lay o do. Neu muon
   tieu chi cho gene exit thi phai co **pre-reg moi** cho mot dai luong kieu `E2` (chuan hoa,
   khong phai tong luong) **va** phai xu ly viec `nActive` trung vi = 0 lam bo 44% khoi.

---

## 7. CAI BAO CAO NAY KHONG LAM

1. Khong noi gi ve VALIDATION / HOLDOUT. Moi so in-sample DEV.
2. Khong sua `PREREG_GS.md`, `PAIRED_CALIB.md`, `CI_REAUDIT.md`, `AUDIT_APPLIED.md`; khong doi
   diem uoc luong nao trong do; khong mo lai nhanh nao.
3. Khong thay the rang buoc `maxDD` — `maxDD` la tinh chat cua duong equity; khong dai luong tick
   nao trong bao cao nay ghi nhan duoc no (`PREREG_CI` §2.5 cam bootstrap `maxDD`).
4. Khong doi dai luong chinh sau khi thay ket qua: `E1` da chot o `4d80fb9`, `E2` chi la de nghi.
5. **Khong** noi `R5_arm7` tot hon hay te hon `R6_arm8`. Ca `E1` va `E2` deu **khong phan biet
   duoc** o do dai khoi chinh.

## 8. HAI CHO BOI CANH DUOC CAP BI SAI (ghi de lan sau khong lap)

1. **"Tick" cua quyet dinh vao lenh khong phai 15 phut, la 1 PHUT** (selector forward-fill).
   Vi vay cross-product **that su** hang chuc GB neu la CSV — de bai dung, va `PREREG_TICKLOG`
   §3.1 (do toi viet) sai. Xem §2.1.
2. **So sanh `MDE80` trong `PAIRED_CALIB` §3 / `PREREG_GS` §12.1 bi lech DO DAI KHOI.** No dat
   equity o khoi **21 ngay** canh tung-lenh o khoi **72h**. Do duoc o day: equity cung dai luong
   o khoi 72h cho `MDE80 = 4.023` (khong phai 3.607). Vi vay ti le "tung lenh / equity" cua cap
   nay la 3.282/4.023 = **0.82** chu khong phai 0.91, va ti le trung vi 0.95 trong
   `PREREG_GS` §12.1 **bi lan** hai nguyen nhan (tan so lay mau + gia dinh phu thuoc chuoi).
   **Ket luan cua `PAIRED_CALIB` khong doi** (van "khong cai thien"), nhung con so ti le do
   khong nen doc nhu mot phep do sach.
3. De bai goi `R5_arm7`/`R6_arm8` la mot cap DEV; dung, nhung chung chay **env-mode**
   (`dev_rob2.sh`) tren nen **KHONG** phai `C2b`: thieu `SELECTOR_ONLY_ENTRY`, `TS_GAP_CONST`,
   `TIER_FLAT`, va `DCA_GRID_SCALE` mac dinh. Vi vay so cua §4 khong so truc tiep duoc voi
   equity 60390 cua `C2b`; chung chi so voi nhau (dung y do ghep cap).
