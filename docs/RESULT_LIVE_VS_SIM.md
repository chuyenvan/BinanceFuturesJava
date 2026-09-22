# RESULT — LIVE/SHADOW (forward) vs SIM T170: KHOP hay LECH

Ngay 2026-09-23. Thuc thi `docs/PREREG_LIVE_VS_SIM.md` (commit `edcc551`) — **chot TRUOC**,
khong doi tieu chi sau khi thay so. Script: `research/analysis/live_vs_sim.py` (thuan Python,
chi DOC). Ket qua tho: `/tmp/live_vs_sim/{live_vs_sim.json,report.txt}`.

## 0. PHAN DINH BANG CHUNG (doc truoc khi tin bat ky so nao)
- `ledger.csv` = **lenh THAT cua nhanh live** (paper `SHADOW_NO_PUSH=true`, khong push len san)
  chay tren ticker that 2026 ⇒ **bang chung FORWARD**.
- **KHONG** phai backtest, **KHONG** mo seal holdout 2026 (sim T170 ket thuc 2025-12-01).
- ⇒ **KHONG** dung tap nay de tune bat ky tham so nao. Muc 10 ghi ro dieu do.
- **N rat nho**: shadow chi co **3 ngay co lenh** (06/09, 18/09, 19/09); 07-17/09 process CHET
  (khong co du lieu). Voi cau hinh T170 chi con **2 ngay / 51 lenh dong** ⇒ moi CI duoi day
  **chi de MO TA**, khong phai ket luan thong ke.
- Nguon + hash: shadow `ledger.csv` md5 `11121bf9e3b164d41dbd342c1273a947` (65 lenh),
  `ledger_from_log.csv` md5 `922fdfc1ca3c96ccef007961bd198233` (60 entry 18-19/09,
  100% `PREDICT_SYMBOL_TRADE`);
  sim `printDone.csv` md5 `efb793e2468ca3a7318da0f0ad23d4fc` (1089 leg / 1069 cum).
- **KHONG** lay `archive_flatgate_20260912` tren 242: mau do la **cung che do gate PHANG**
  (da co dai dien 06/09 o day) nen khong them thong tin cho cau hoi T170, va quy tac la
  "chi lay neu can" ⇒ khong cham 242.

## 1. TAN SUAT — va giai thich chenh "7×"
| Tap | n | span (ngay) | ngay co lenh | lenh/ngay-lich | lenh/ngay-HOAT-DONG | slot | lenh/slot | coin |
|---|---|---|---|---|---|---|---|---|
| shadow (ledger, 3 ngay) | 65 | 13,5 | 3 | **4,82** | 21,67 | 45 | 1,44 | 24 |
| shadow T170 (18-19/09) | 51 | 1,4 | 2 | 37,66 | **25,50** | 38 | 1,34 | 15 |
| shadow (from_log 18-19/09) | 60 | 1,4 | 2 | 41,44 | **30,00** | 43 | 1,40 | 18 |
| sim T170 (toan bo) | 1089 | 1588,2 | 110 | **0,69** | 9,90 | 291 | 3,74 | 358 |
| sim T170 chi PST | 821 | 1588,2 | — | 0,52 | — | — | — | — |

| Cach chuan hoa | shadow | sim | ty le |
|---|---|---|---|
| **span lich 13,5-14 ngay** (65 lenh) | 4,82/ngay | 0,686/ngay | **7,0×** ← chinh la "32 lenh/tuan" (65÷14×7 = 32,5) |
| ngay CON SONG (18/09 11:00Z→23/09 06:00Z = 4,8 ngay, 60 entry) | 12,5/ngay | 0,686/ngay | 18,3× |
| ngay HOAT DONG | 25,5-30/ngay | 9,90/ngay | 2,6-3,0× |
| ty le ngay CO entry | 2/4,8 = 41,7% | 110/1588 = 6,9% | 6,0× |
| slot/ngay-HD | 19-21,5 | 2,65 | 7,5× |
| lenh/slot (do "day" book) | 1,34-1,40 | 3,74 | **0,37×** (shadow THAP hon) |

**Ket luan muc 1** — "7×" la **that** nhung la **SAN PHAM CUA CACH DEM**:
1. **(a) Cach dem (chiem phan lon):** 65 lenh ÷ **14 ngay lich** = 4,64-4,82/ngay. Nhung shadow
   CHET 12/14 ngay (07-17/09). Tu so nay ra dung "32 lenh/tuan". **Cung so do, chia theo ngay
   CON SONG ⇒ 12,5/ngay = 18×**, khong phai 7×.
2. **(b) Config KHONG dong nhat:** lo 06/09 (14 lenh) chay **gate PHANG 0,008** (truoc fix 18/09;
   `docs/SHADOW_EVAL_20260911.md`, `docs/L6_GATE_DYN_FIX.md`) — **khong phai T170**. Lo 18-19/09
   moi la gate dyn 1,70 (xac nhan trong `/proc/1390453/environ`: `SIM_GATE_DYN_SCALE=1.70`,
   `SELECTOR_ONLY_ENTRY=0`, `SIM_LOSER_TIME_STOP_HOURS=168`; jar shadow co `entryGate` ⇒ da co
   fix L6). Rieng 19/09 config da doi sang **FLATGRID KEEPLEG0** (`DCA_GRID_WEIGHTS=1,1,1,1`,
   `SCALE=6.0`) ⇒ 19/09 **khong con la T170 nguyen ban**.
3. **(c) Di book + chuoi re-entry:** shadow vao lenh tren luoi 15m va **dien toi da 8 lenh/tick**
   khi book trong (18/09 11:29 = 8 lenh; 06/09 08:29 = 8 lenh). 65 lenh chi tren **24 coin**
   (AKE 10, BR 8, ONE 7, SYN 6...) ⇒ riêng 18-19/09: 51 lenh / 15 coin = **3,4 lenh/coin**.
   Trailing thoat +7% ⇒ slot trong ⇒ tick sau vao lai cung coin. **Sim cung the** (1069 cum /
   1089 leg, 291 slot) nhung sim **khong** co nhip nay o moi ngay.
4. **(d) Regime:** sim **cung burst** — 1089 leg chi tren **110 ngay** (6,9%), median 8 leg/ngay-HD,
   max **123 leg/ngay** (2025-10-11); top-10 ngay = 34,4% so leg. Nghia la "sim 0,69 lenh/ngay"
   la **trung binh 4,4 nam**, con 2 ngay cua shadow roi vao mot dot hoi phuc ⇒ so voi *ngay hoat
   dong* thi chi con 2,6-3,0×. Voi N=2 ngay, **khong tach duoc (d) regime khoi (b) config**.
5. Khac biet thanh phan: shadow 65/65 = PST; sim 821 PST + 248 BIG_DOWN + 20 DCA ⇒ shadow
   **khong sinh leg BIG_DOWN nao** trong cua so nay.

## 2. `reason` ↔ `status` (anh xa)
| shadow | n | sim | n | Ghi chu |
|---|---|---|---|---|
| `TRAILING_STOP` | 58 | `STOP_MARKET_DONE` | 983 | **1-1 ve y nghia** |
| `TIME_STOP_168H` | 7 | `STOP_LOSS_DONE` | 106 | **KHONG 1-1 ve nhan**, nhung **1-1 ve CO CHE**: trong 106 `STOP_LOSS_DONE` thi **105 la time-stop 168h** (hold ≥167h; med 168,0h) va **1** la hard SL. ⇒ co the so truc tiep 7 ↔ 105 |

⇒ Tap **map duoc** dung de so: `TRAILING_STOP` ↔ `STOP_MARKET_DONE`; `TIME_STOP_168H` ↔
time-stop 168h cua sim (105 leg). Hard SL cua sim (1 leg) khong co doi ung o shadow
(`ShadowBookC3` chi co **2 duong dong**: arm-trailing va time-stop 168h — **khong** co cat lo
theo priceSL duoi entry).

## 3. PnL/notional GROSS (%) — chi so CHINH
| Tap | n | mean | median | win% | p10 | p90 | min | max |
|---|---|---|---|---|---|---|---|---|
| shadow 18-19/09 (**T170**) | 51 | **7,892** | **5,500** | 100,00 | **3,50** | **14,50** | 3,50 | 38,50 |
| shadow 06/09 (gate phang) | 14 | 10,130 | 4,619 | 64,29 | -23,38 | 32,55 | -48,36 | 148,00 |
| sim PST+SM | 738 | **6,779** | **4,997** | 97,97 | **3,50** | **14,00** | -63,14 | 207,00 |
| sim SM (moi level) | 983 | 7,642 | 5,000 | 96,95 | 3,50 | 14,00 | -63,14 | 207,00 |
| sim SM **chi leg duong** | 953 | 8,531 | 5,000 | 100,00 | 3,68 | 14,00 | 0,10 | 207,00 |
| sim PST+time-stop 168h | 83 | -18,521 | -16,548 | 2,41 | -32,75 | -4,76 | -67,69 | 3,53 |
| shadow time-stop 168h | 7 | -12,527 | -6,683 | 28,57 | -35,71 | 5,66 | -48,36 | 6,30 |
| shadow (toan bo) | 65 | 8,374 | 5,500 | 92,31 | 3,50 | 20,30 | -48,36 | 148,00 |
| sim (toan bo) | 1089 | 5,244 | 4,997 | 88,25 | -4,85 | 13,00 | -67,69 | 207,00 |

**Doc:** chan **THANG** khop rat sat: shadow T170 (med 5,50 / p10 3,50 / p90 14,50) vs sim PST+SM
(4,997 / 3,50 / 14,00) — lech median **+0,50pp**, va mean shadow **7,892 nam LOT trong** 2 moc
cua sim: 6,779 (khi GIU leg lo) va 8,531 (khi BO leg lo). Nghia la **chenh lech mean dao dau
theo viec xu ly chan THUA ⇒ uoc luong khoang [-0,64pp, +1,11pp]/lenh, bao 0 ⇒ KHONG phan biet duoc.**
Chan **THUA thi KHONG so duoc**: 7 lenh time-stop cua shadow deu thuoc **lo 06/09 (gate phang)**
va bi **phong dai thoi gian giu** do process chet (giu 289,6-290,6h thay vi 168h); lo T170
(18-19/09) **chua co lenh thua nao** vi dong ho 168h moi nong vao 25-26/09 (hom nay 23/09).

## 4. NET (%) — va gia thuyet "sim tinh chi phi dat hon thuc te"
Bat doi xung da ghi trong pre-reg: **shadow `pnl` = GROSS** (`ShadowBookC3.closeAt`:
`pnl=(exit-entry)*qty`, khong tru phi), **sim `pnl` = NET** (tru `RATE_FEE` 0,002 (2 chan)
+ `SLIPPAGE_RATE` 0,003×2 + funding ⇒ **0,8% notional/lenh**).

| | mean %/notional |
|---|---|
| shadow T170 gross | 7,892 |
| shadow T170 net @c=0,008 (mo hinh cua sim) | 7,092 |
| shadow T170 net @c=0,001 (gia dinh taker 2 chan that) | 7,792 |
| sim PST+SM gross | 6,779 |
| sim PST+SM net (thuc te trong file) | 5,979 |
| sim SM gross | 7,642 / net 6,922 |

**Doc:** khi ap **CUNG mo hinh phi 0,8%** cho ca hai ben, khoang cach net thu ve **~0,2-1,1pp/lenh**
va **dao dau** tuy tap so sanh ⇒ **toan bo "shadow net tot hon" la khac biet MO HINH PHI**, khong
phai alpha. Con **dau hieu ve gia thuyet "sim tinh chi phi 2-5× that"**:
- **DUNG DAU (yeu):** mo hinh phi 0,8%/lenh la **khoan lech duoc biet duy nhat** giua hai so;
  neu chi phi round-trip THAT ~0,1% thi sim dang tru **~0,7pp/lenh qua nang**.
- **KHONG DU DE KET LUAN:** tap nay **khong co** du lieu phi/slippage/spread THUC cua san; 0,8% la
  **gia dinh theo code sim**, khong phai do duoc. Theo dung luat doc da chot o pre-reg muc 7:
  *"gross ≈ 0 nhung net lech ~0,8pp ⇒ chi la khac biet MO HINH PHI, KHONG duoc goi la bang chung
  sim dat hon that"* ⇒ **khong** tuyen bo duoc 2-5×.

## 5. Thoi gian giu lenh (gio)
| | mean | median | max |
|---|---|---|---|
| shadow T170 (18-19/09) | 11,4 | **2,65** | 70,1 |
| shadow 06/09 (phong dai do outage) | 211,8 | 290,59 | 317,0 |
| sim SM (trailing) | — | **3,3** | 168,0 |
| sim time-stop | — | 168,0 | 168,0 |
⇒ Chan THANG khop (**2,65h vs 3,3h**, CI sim `[2,1, 5,7]` chua 2,65). Lo 06/09 la **artifact cua
outage** (dung do lai nhu so cua chien luoc).

## 6. Phan bo level
shadow: `PREDICT_SYMBOL_TRADE` 65/65 (0 BIG_DOWN, 0 DCA) — sim: PST 821 / BIG_DOWN 248 / DCA 20.
⇒ Khong so duoc nhanh BIG_DOWN (shadow khong co mau).

## 7. CI block-72h (2000 rep, seed 20260923; hai ben rut DOC LAP)
| tap | n_blk | mean CI | median CI | win CI | hold-med CI |
|---|---|---|---|---|---|
| shadow (65, 2 block) | 2 | [7,89, 10,13] | [4,62, 5,50] | [64,3, 100,0] | [2,7, 290,6] |
| shadow T170 (51) | **1** | degenerate (32h = 1 block) ⇒ **CI vo nghia** | | | |
| sim (1089) | 96 | [4,01, 6,45] | [4,50, 5,00] | [85,8, 90,9] | [2,8, 8,1] |
| sim SM (983) | 93 | [**6,59, 8,73**] | [4,999, 5,496] | [94,4, 99,4] | [2,1, 5,7] |
| sim SM chi leg duong (953) | 93 | [**7,18, 9,97**] | [5,00, 5,50] | [100, 100] | [2,4, 5,3] |
| sim PST (821) | 73 | [2,99, 5,79] | [4,50, 5,00] | [85,4, 91,2] | [4,8, 10,7] |

**DOC CI:** mean shadow T170 7,892 **nam trong** CI cua sim SM `[6,59, 8,73]` va cua sim SM-chi-duong
`[7,18, 9,97]` ⇒ **khong khac biet duoc**. Median shadow 5,50 vs CI median sim SM
`[4,999, 5,496]` ⇒ **sat mep tren** (lech 0,004pp) — coi nhu chong lan.
CI cua shadow (1-2 block) **khong dung de bac bo** gi: voi 1 block CI la mot diem.

## 8. KET LUAN (theo tieu chi R da chot)
**R1 — KHOP o muc CO CHE + PHAN PHOI chan THANG.** Bang chung:
- Anh xa 1-1 ve co che: arm +7% roi trailing (`TRAILING_STOP` ↔ `STOP_MARKET_DONE`) va time-stop
  168h cho cum chua arm (`TIME_STOP_168H` ↔ 105/106 `STOP_LOSS_DONE`) — **cung mot luat dong**,
  khop ca o muc code (`ShadowBookC3` la ban port cua luat sim).
- Phan phoi ret gross cua chan thang **khop sat**: med 5,50 vs 4,997; p10 3,50 vs 3,50;
  p90 14,50 vs 14,00; mean 7,892 nam trong CI cua sim.
- Thoi gian giu chan thang khop: med 2,65h vs 3,3h.
**Lech o dau:**
1. **Chan THUA: khong so duoc** (survivorship) — lo T170 chua nong dong ho 168h; 7 lenh thua
   duy nhat thuoc lo gate phang 06/09 va bi phong dai hold do outage ⇒ **KHONG duoc dung**.
2. **Duoi phai rong hon o sim**: SM max 207% vs shadow 38,5% (cung ly do: lenh duong cua shadow
   chua chay het) ⇒ moi so sanh "mean gross" con lai la **can duoi**.
3. **Tan suat: KHONG ket luan duoc.** N=2 ngay cua T170, va 2 ngay do nam trong mot dot hoi phuc
   ⇒ khong tach duoc regime khoi config. Con so "7×" la **artifact cua mau so ngay lich** (12/14
   ngay shadow chet). Chuan hoa dung ⇒ **2,6-3,0×** (ngay hoat dong), rieng **lenh/slot thi shadow
   THAP hon (1,4 vs 3,74)**.
4. **Gia thuyet chi phi:** chieu **dung** (moi khac biet net deu quy duoc ve mo hinh phi 0,8%/lenh
   cua sim va khoan nay lon hon chi phi that thong thuong), nhung **khong du bang chung** de noi
   "2-5×": khong co du lieu phi THUC trong tap nay. **Khong** duoc goi day la bang chung.

## 9. Cai KHONG the noi tu tap nay
- Khong noi duoc win%/ky vong cua T170 tren live (thieu chan thua).
- Khong noi duoc tan suat live co "dung" hay khong (2 ngay, 1 regime).
- Khong noi duoc gi ve BIG_DOWN leg (0 mau) va DCA (0 mau; va 19/09 da doi sang FLATGRID).
- Khong suy duoc gi cho holdout 2026 cua sim (khong mo).

## 10. KHONG TUNE
Muc dich la **kiem tra khop/noi suy**. Bat ky thay doi tham so nao (gate, DCA, time-stop,
selector, phi) dua tren tai lieu nay deu **lam mat tinh forward** ⇒ phai mo **PREREG MOI** va
chay tren du lieu khac. Tai lieu nay **khong** de xuat tune.
