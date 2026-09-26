# DIAG_GATE_FROZEN_20260926 — Vi sao kenh LIVE PAPER dong bang `[GATE] n_pass=0`?

- **Ngay do:** 2026-09-26 19:4x-20:1x (GMT+7). Repo `/home/ubuntu/src/BinanceFuturesJava`, branch `module`, HEAD `25e96d9`.
- **Cau hoi:** `[GATE] n_pass=0` lien tuc (Oracle shadow: 538 dong, 20/09 22:19 -> 26/09 19:33) + 0 entry tu 20/09 05:34;
  242 khong `would-BUY` tu 12/09 07:15. Day la **BUG**, **HIEU CHUAN**, hay **SU THAT**?
- **Ket luan mot cau:** **HIEU CHUAN** — khong phai bug ma; nhung nguong gate dang duoc bieu dien bang don vi `predReturn15M`
  cua *bo pred DEV (WFO)* trong khi *model live 2026* xuat p15 da bi nen (trung vi cao hon, duoi bi cat), nen cung cong thuc
  do nam **ngoai support** cua phan bo live: nguong 2,947-3,760% = **p99,91-99,95** cua DEV nhung **> p100** cua 2026
  (max 2,30% trong 8.929 mau). Cong them lech nhip: sim danh gia entry **moi 1 phut** (1.440/ngay) con live **moi 15 phut** (96/ngay)
  => ty le entry cua DEV (0,5-1,4/ngay) khong chuyen duoc sang live (ky vong ~0,09/ngay ~ 2,6/thang).
- **Rang buoc da giu:** chi DOC Oracle + 242 (`ssh -p 2222`, read-only). Khong restart/sua config/deploy; khong chay Java/sim
  tren Oracle; khong push git. Output tool de nho (`grep`, `awk`, `sort -n | awk` percentiles). **Sai lech da bao:** tren 242
  co ghi 1 file tam `/tmp/p15_242.txt` (4,4 KB) de tinh percentiles p15 -> **da `rm -f`** trong cung phien; khong con file nao
  tren 242. Khong file production nao bi sua.

---

## 1. VIEC 1 — Doc log `[GATE]`

### 1.1 Oracle shadow (`/home/ubuntu/shadow_c3/app/logs/full.log`)

| do | gia tri |
|---|---|
| So dong `[GATE]` | **538**, dong DAU `20/09/2026 22:19:00.125`, dong CUOI `26/09/2026 19:33:36.601` |
| `n_pass > 0` | **0 / 538** — chua tung pass |
| Mau dong | `[GATE] scale=1.7000 topk=8 base=0.00800 thr=[0.02947..0.03549] n_cand=8 n_rej=8 n_pass=0` |
| Nhip | 96 dong/ngay (7 · 76 · 96 · 93 · 96 · 95 · 75) => ~1 dong / 15 phut |
| `scale` | **1.7000 o ca 538 dong** (khong doi) |
| `n_cand`/`n_rej` | **8 / 8** o ca 538 dong (=> `n_pass = 8-8 = 0`, dung cong thuc `DetectEntrySignal2TradeNormal.java:426`) |
| `thr` | dai [2,947% .. 3,760%] (min 0,02947 · max 0,03760) |

⚠️ **Dinh chinh so lieu cu:** dong `[GATE]` dau tien la **20/09/2026 22:19**, KHONG phai 18/09 18:20 — 18/09 18:20 la moc
`full.log` bat dau ghi. Truoc 20/09 22:19 jar cu **khong co** dong `[GATE]` nao (format log moi chi co o ban build 20/09 22:06).
So 524 dong trong audit truoc la dem trong cua so bat dau tu 18/09 (nay la 538).

### 1.2 Truoc 20/09 22:19 thi gate co pass khong? — **CO, nhung bang luat KHAC**

`full.log` truoc moc jar moi: **1.008 dong `✅ AI PASS`** (18/09: 168 · 19/09: 704 · 20/09: 136), tat ca deu
`Reason: PERFECT: 15M(x%)` voi `min` ghi trong dong `🔕 [PREDICT fail]` la **`Min15M:0.80%`**:

```
20/09/2026 05:33:14.129 ✅ AI PASS [STARUSDT] Reason: PERFECT: 15M(0.83%) symbolPred: 0.21510452
18/09/2026 19:34:09.021 🔕 [PREDICT fail 8] market[15M:0.78% Risk4H:-2.29%] Min15M:0.80% | AIN(0.400) ONE(0.141) ...
```

=> Gate thoi do la **nguong PHANG `base=0.008` (0,80%)**, KHONG dung `symbolPred` (dung "gate phang" cua bug LIVE rank-mode
da biet, `AIRejectFilter` thoi chua gop ve `EntryGate`). Pass xay ra bat cu khi `predReturn15M >= 0.80%`.
Dong `[GATE]` **chi bat dau** tu khi jar 20/09 22:06 vao chay (22:19) => "chua bao gio `n_pass>0`" la dung, nhung no chi co
nghia **"chua bao gio pass duoi LUAT DONG ×1.70"**, khong phai "gate chua bao gio pass".

### 1.3 Moc 20/09 05:34 khong phai do gate

- `✅ AI PASS` cuoi = **20/09 05:33:14**; `ledger.csv` entry cuoi = **20/09 05:34**.
- Tu 20/09 05:34 den 22:06, `DetectEntrySignal2TradeNormal` chi chay **2 lan** (`Check level market: 20260920 05:3x`),
  con lai 276 dong la `Read ticker from Aerospike` + `Error get position from binance` => **vong lap entry dung han**
  (process cu o trang thai idle), khong phai "gate chan".
- **JVM restart 20/09 22:06:11** (`MainClass: ...BinanceOrderTradingManager`, PID 1247839) = jar moi (`build 20/09 22:06`,
  sha256 `e3bf2d21…`) => tu 22:19 moi co dong `[GATE]` va tu do `n_pass=0` lien tuc.

### 1.4 242 (`/home/chuyennd/java/v_t_m/logs/full.log`, 81 MB, read-only)

| do | gia tri |
|---|---|
| `[GATE]` | **1.385** dong, dau tien **12/09/2026 08:15:53**, `n_pass>0` = **0** |
| Mau dau | `[GATE] topk=8 base=0.00800 thr=[0.01846..0.02300] n_cand=8 n_rej=8 n_pass=0` (chua co field `scale=`) |
| `scale` | 4 dong khong co field · **37 dong `scale=1.0000`** · **1.344 dong `scale=1.7000`** |
| Nhip | 96 dong/ngay |
| `would-BUY` cuoi | **12/09/2026 07:15:48** (SOPHUSDT, PONSUSDT) |

=> Tren 242 moc dong bang la **12/09 ~08:15**, tuc **ngay khi jar co cong `EntryGate` (L7) duoc deploy**, KHONG phai khi bat
`scale=1.70`. Luc dau `thr = [1,705%..2,300%]` (scale 1,0) da `n_pass=0`; sau do (scale 1,70) `thr = [2,9%..3,9%]`.
Duong cu tren 242 (truoc L7) la gate **PHANG** `2,284%` cho leg khong-selector ("`BAD MOMENTUM: 15M chua nay manh (1.17% < 2.28%)`,
dong cuoi 14/08) va leg selector van ra `would-BUY` den 12/09 07:15.

---

## 2. VIEC 2 — Code gate: nguong duoc tinh tu dau

| cho | file:line | noi dung |
|---|---|---|
| Cong thuc nguong | `src/main/java/com/binance/chuyennd/tradecore/EntryGate.java:85-87` | `thr = thrBase * max(DYN_MIN, (symbolPred/SCORE_BASE)*DYN_MULT) * gateScale` |
| Hang so | `EntryGate.java:45-49` | `DYN_MIN=0.26787`, `SCORE_BASE=0.15`, `DYN_MULT=1.28760` (hang so cung, khong fit) |
| `scale` | `EntryGate.java:58` + `Configs.java:763-765` | `GATE_DYN_SCALE`, doc 1 lan tu key `SIM_GATE_DYN_SCALE` (khong khai/<=0 => 1.0) |
| `thrBase` | `Configs.java:407` (default `0.02284`) + `Configs.java:759` (key `SIM_MIN_MOMENTUM_15M`) | env Oracle/242 dat `0.008` => `base=0.00800` trong log |
| Quy tac pass | `EntryGate.java:96-98` | `PASS <=> !(predReturn15M < thr)` (NaN => PASS) |
| Vo boc + REJECT | `AIRejectFilter.java:61-63` | `entryGate(pred, sp, predictSymbolTrade)`: `sp` chi khac null khi leg `PREDICT_SYMBOL_TRADE` |
| Live goi gate | `DetectEntrySignal2TradeNormal.java:766` | `aiRejectFilter.entryGate(predict, symbolPred, levelChange==PREDICT_SYMBOL_TRADE)` |
| Live log | `DetectEntrySignal2TradeNormal.java:420-426` | `n_pass = n_cand - n_rej` (n_rej = `predictRejects`, gom theo tick) |
| Sim goi gate | `SimulatorMarketLevelTicker1MStopLoss.java:1257` | cung `EntryGate.threshold` |
| Sim log | `SimulatorMarketLevelTicker1MStopLoss.java:592` | dong `[GATE] scale/base/n_cand/n_pass` |

**Kiem soat so hoc (khong suy dien):** voi `base=0.008`, `scale=1.70`, va `symbolPred` doc tu chinh log 2026
(`STAR(0.296)`…`ENA(0.322)`, dai [0,252..0,322]):

```
thr(sp=0.2524) = 0.008 * (0.2524/0.15*1.2876) * 1.70 = 0.02947  -> khop dong [GATE] thr min  = 0.02947
thr(sp=0.3220) = 0.008 * (0.3220/0.15*1.2876) * 1.70 = 0.03759  -> khop dong [GATE] thr max  = 0.03760
```

=> Cong thuc **khop byte-muc** voi log. Khong co loi don vi/scale, khong co NaN (`thr` in ra so), khong co exception
(`full.log`: 0 ERROR sau 21/09 21:17 — loi duy nhat la Aerospike outage 21/09, khong lien quan tien). `n_cand=8 n_rej=8 n_pass=0`
la nhat quan (8 ung vien = `SELECTOR_RANK_TOPK=8`, ca 8 bi gate chan).

**Diem mau chot — nhip danh gia khac nhau (chua tung duoc ghi nhan trong `LEAN_GATE_AUDIT`):**

- **SIM: 1 phut / lan.** `SimulatorMarketLevelTicker1MStopLoss.java:219-221` (`if (time2Tickers.size() >= 1440)` roi
  `for (entry : time2Tickers.entrySet())`) + `:403-436` (leg selector moi tick) => 1.440 lan/ngay x 8 ung vien = 11.520/ngay.
  Kiem chung bang so cua chinh run DEV: `n_cand=17.925.650` / (1.645 ngay x 1.440) = **7,57 ung vien/tick** (dung top-8).
- **LIVE: 15 phut / lan.** Do duoc 96 dong `[GATE]`/ngay tren CA HAI host (Oracle + 242) => **96 lan/ngay**.
- => Cung mot luat, nhung live co **15x it co hoi** hon sim. Voi mot nguong chi no o duoi rat mong, ty le entry live
  ky vong = ty le sim / ~15.

---

## 3. VIEC 3 — So phan bo: nguong nam o dau?

### 3.1 Nguon so (khong fit tren 2026)

| tap | nguon | n | min | p50 | p90 | p99 | p99,9 | max |
|---|---|---|---|---|---|---|---|---|
| **DEV 2021-07..2025-12** | `/home/ubuntu/wfo_ds_x1_2021/pred.bin` (`predReturn15M`, luoi 1 phut) | 2.500.260 | 0,202% | **0,545%** | 0,837% | 1,308% | 2,818% | **12,261%** |
| DEV 2024-2025 (subset) | nhu tren | 1.052.640 | — | — | — | — | — | — |
| **2026 (LIVE) 12/08-26/09** | 242 `full.log`, `market[15M:x%]` | **8.929** | 0,400% | **0,910%** | 1,220% | 1,770% | (p99,5=1,85) | **2,300%** |
| 2026 (Oracle shadow) 20-26/09 | Oracle `full.log`, `market[15M:x%]` | 538 | 0,530% | 0,940% | 1,170% | 1,490% | — | 2,300% |

### 3.2 Nguong hien tai nam o percentile nao

| nguong | y nghia | percentile trong DEV (2021-25) | trong DEV 2024-25 | trong 2026 (8.929 mau) |
|---|---|---|---|---|
| 2,947% (`thr` min, Oracle 26/09) | gate hien hanh | **p99,910** | p99,963 | **> p100** (max 2,30%) |
| 3,760% (`thr` max, Oracle 26/09) | gate hien hanh | **p99,949** | p99,975 | **> p100** |
| 1,705% (`thr` min, 242 12/09, scale 1,0) | gate luc deploy | p99,610 | p99,840 | p99,8x (135/8.929 mau ≥) |
| 0,800% (`base`, luat phang cu) | gate truoc L7 | p87,711 | p81,151 | ~p52 (p50 = 0,91%) |

### 3.3 Kiem dinh: phan bo 2026 co KHAC DEV khong? (Poisson, ky vong = ty le DEV x 8.929 mau)

| nguong | ty le DEV | ky vong @8.929 | **thuc do 2026** | P(X <= thuc do) |
|---|---|---|---|---|
| ≥1,5% | 0,6058% | 54,1 | **293** | 1,0 (2026 **nhieu hon**) |
| ≥2,0% | 0,2323% | 20,7 | **5** | **4,1e-5** |
| ≥2,3% | 0,1595% | 14,2 | **1** | **9,9e-6** |
| ≥2,9% | 0,0938% | 8,4 | **0** | **2,3e-4** |

- 2026 p50 = **0,910% = DEV p93,4** (2024-25: p90,5) => **than phan bo 2026 CAO hon DEV**, khong phai "thi truong yen hon".
- Nhung **duoi 2026 bi cat**: 45 ngay, 8.929 mau, khong mau nao ≥2,9% (ky vong 8,4) va chi 1 mau ≥2,3% (ky vong 14,2).
- => Dau hieu cua **doi thang do dau ra cua model live** (nen quanh 0,4-2,3%), khong phai "2026 thieu co hoi" theo nghia
  thi truong lang di (neu lang thi trung vi phai THAP hon DEV, do lai cao hon).
- **Canh bao su that con lai:** khong the loai tru 100% rang 2026 la che do "bien do nen" that; phan biet dut khoat doi hoi
  so sanh bien do/thuc te (khong nam trong pham vi bai nay - khong chay sim/tick tren Oracle).

### 3.4 Sanity: ty le entry tren DEV duoi LUAT HIEN TAI

| run (nguon) | cua so | `n_pass` gate | lenh | entry/ngay |
|---|---|---|---|---|
| `RESULT_GATESCALE.md` §2+§4 · `X1_GS_T170` (scale 1,70) | 2022-01..2025-12 (1.460 ngay) | 724 | 940 (704 leg selector) | **0,50** |
| `RESULT_GATE_CALIB.md` §1 · T170 dataset `wfo_ds_x1_2021` | 2021-07..2025-12 (1.645 ngay) | 841 | 1.089 | **0,51** |
| `RESULT_GATESCALE.md` §1 · `X1_GS_OFF` (scale 1,00) | 2022-01..2025-12 (1.460 ngay) | 2.056 | 2.266 | **1,41** |

Gia tri entry DEV (tu `devrun/X1_GS_T170/storage/printDone.csv`, 704 leg `PREDICT_SYMBOL_TRADE`, 2022-01-06..2025-12-01):
`pred15m` tai entry: min 1,08% · p50 **2,71%** · p90 5,62% · max 11,95%; `symbolPred` tai entry: min 0,045 · p50 **0,175** · p90 0,289 · max 0,444.

=> **Luật hiện tại KHÔNG hỏng trên DEV**: no 0,5-1,4 lan/ngay (≈15-42 entry/thang) — nho (a) p15 DEV co duoi dai
(≥3,9% xuất hiện 0,056% so mau = 0,81 mau/ngay o luoi 1 phut) va (b) sim danh gia **1.440 lan/ngay**.
Tren live 2026: (a) duoi do **khong ton tai** (0/8.929 ≥2,9%) va (b) nhip chi **96 lan/ngay**
=> ky vong live = `P(p15 >= 2,947%) x 96/ngay = 0,0899% x 96 = **0,086 lan/ngay ~ 2,6 entry/thang**
(va `0,086 x 6,9 ngay = 0,6` => **quan sat 0 la BINH THUONG**, P(0) ~ 0,55-0,62).

---

## 4. VIEC 4 — KET LUAN

### 4.1 Phan quyet: **HIEU CHUAN** (khong phai BUG; "SU THAT" khong duoc ung ho)

**Khong phai BUG** (bang so, khong suy dien):
1. Cong thuc `EntryGate` tai lap **chinh xac** dai `thr` trong log (0,02947/0,03759 vs log 0,02947/0,03760).
2. `n_cand=8, n_rej=8, n_pass=0` nhat quan voi `SELECTOR_RANK_TOPK=8` va voi dong `🔕 [PREDICT fail 8]`.
3. 0 ERROR/exception lien quan tien trong cua so; khong NaN (thr/base in ra so).
4. Khong co nhanh code moi: L7 chi gop cong thuc ve 1 cho (`EntryGate`), khong doi hang so.

**Khong phai "SU THAT" theo nghia 2026 khong co co hoi:** trung vi p15 2026 (0,910%) nam o **p93,4 cua DEV**
(2024-25: p90,5) — model live bao bien do **cao hon**, khong phai thi truong yen hon. Cai bi mat la **duoi tren**
(0 mau ≥2,9% / ky vong 8,4; p=2,3e-4) => phan bo **dau ra model live** khac phan bo **bo pred DEV ma nguong duoc hieu chuan tren do**.

**HIEU CHUAN — hai khuyet diem dinh luong:**
- **(a) Nguong sai don vi nguon:** `thr` duoc bieu dien bang `predReturn15M` tuyet doi, hieu chuan tren bo pred DEV/WFO
  (`pred.bin`, p50 0,545%, duoi dai toi 12,26%). Live 2026 dung model khac (p50 0,910%, max 2,30%/45 ngay) =>
  nguong hien hanh (2,947-3,760%) **vuot qua support cua chinh dau vao live**. Cung 1 cong thuc, 2 phan bo dau vao khac nhau
  => `n_pass` **tat dinh = 0**, khong phai "xui".
- **(b) Lech nhip sim<->live:** sim danh gia entry **1 phut/lan** (1.440/ngay, `Simulator…:219-221`), live **15 phut/lan** (96/ngay).
  Voi luat duoi-mong, ky vong live = 1/15 sim => ket qua DEV "0,5-1,4 entry/ngay" **khong chuyen duoc** sang live
  (ket qua that: 0,086/ngay ~ 2,6/thang), tuc kenh shadow **khong the giao dich o cau hinh hien tai** — dung nhu quan sat.

### 4.2 He qua cho quyet dinh go-live / holdout

- **Khong doc ket qua 2026 nhu "gate dung/thi truong het co hoi".** `n_pass=0` o 2026 la **ky vong** cua cau hinh hien tai,
  khong phai tin hieu ve chat luong luat.
- **Khong duoc go-live cau hinh hien tai** (duoi mong + lech nhip): kenh se khong vao lenh trong ~2,6 entry/thang va moi
  lan vao la mot cu no hiem => mau forward rat nho, khong du de danh gia.
- **Ket qua DEV (T170: n=1.089, CAGR +29,27%) van dung cho SIM**, nhung **khong** la bang chung cho live o cau hinh nay
  (khac nguon p15 + khac nhip).
- **Holdout 2026 van nguyen ven**: bai nay chi DOC log 2026 de chan doan; moi tham so fit (neu co) chi dung du lieu
  <= 2025-12-31.

### 4.3 De xuat

1. **Pre-reg hieu chuan lai gate:** `docs/prereg/PREREG_GATE_RECAL.md` (da soan, **CHUA AP DUNG**) — dat nguong
   theo **phan vi cuon** cua chinh chuoi p15 cua **model live** (hoac bo pred nguon live), fit **<= 2025-12-31**,
   muc tieu **ty le entry/thang ky vong** + do budget, chot truoc khi nhin 2026.
2. **Do lai nhip:** chay 1 lan sim voi entry-leg **lay mau 15 phut** (khop nhip live) de co ty le entry "chuyen doi duoc"
   truoc khi tin bat ky con so entry/thang nao cua sim. Neu khong, moi so sanh sim<->live deu thieu 1 buoc 15x.
3. **Them watchdog `gatePassCuoi`** vao `bin/health.sh`: `[GATE] n_pass=0` lien tuc >= 3 ngay (hoac >= 300 dong) phai bao dong
   (hien khong co, `grep -c gatePass health.log = 0`).
4. **KHONG tu ap dung** bat cu thay doi nao vao production: can **owner duyet** (deploy jar, doi env/profile, mo holdout).

---

## 5. Bang chung tho (tai lap)

```bash
# Oracle shadow
cd /home/ubuntu/shadow_c3/app/logs
grep -c '\[GATE\]' full.log                                    # 538
grep '\[GATE\]' full.log | head -1                             # 20/09/2026 22:19:00.125 ... thr=[0.02977..0.03747]
grep -c 'n_pass=[1-9]' full.log                                 # 0
grep '\[GATE\]' full.log | awk '{print $1}' | sort | uniq -c    # 96/ngay
grep -c 'AI PASS' full.log                                      # 1008 (18-20/09, gate PHANG 0.80%)
grep 'AI PASS' full.log | tail -1                               # 20/09 05:33:14 15M(0.83%)
grep -o 'market\[15M:[0-9.-]*%' full.log | sed 's/market\[15M://;s/%//' | sort -n | awk '{a[NR]=$1} END{...}'
# 242 (read-only)
ssh -p 2222 -i ~/.ssh/id_rsa_chuyennd root@103.157.218.242 \
  'cd /home/chuyennd/java/v_t_m/logs; grep -ac "\[GATE\]" full.log; grep -ac "n_pass=[1-9]" full.log'
# DEV pred.bin (dtype >i8,>f4,>f4 sau header int32)
# python3: np.fromfile -> percentiles + frac >= nguong
```

**So nguon JSON:** `docs/audit/DIAG_GATE_FROZEN_20260926.json`.
