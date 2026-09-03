# GS WAVE-1 — KET QUA (doc theo PREREG_GS.md, khong sua luat)

**Doc luc:** 2026-09-04 (Oracle, gio VN) / gom ket qua 2026-09-03 18:50 UTC.
**Luat ap dung:** `docs/PREREG_GS.md` muc 4 (buoc 1-7) + muc 5 + muc 6 + toan bo 5 sua doi
(muc 9, 10, 11, 12, 13). **Khong mot dieu kien nao bi noi ra**; cho nao khong tinh duoc thi
ghi la khong tinh duoc, khong thay bang phep xap xi de lay ket luan.

**Dau vao:** `/home/ubuntu/gs/out/gs_wave1_all.jsonl` (257 dong).
**Harness:** `research/kaggle/gsearch/analyze_wave1.py` (khong sua mot dong nao trong job nay).
**Niem phong:** `research/kaggle/gsearch/finalists.json` commit `9ca1b0e` (2026-09-04T01:55:39+07:00
= 2026-09-03T18:55:39Z), **truoc** moi lan doc devB. Xem muc 7 duoi.

---

## 1. Gom ket qua — 257 dong, nhung khong phai theo duong da du kien

`bash /home/ubuntu/java/stage/gs_gather.sh` chay sach: 5/5 kernel `gs-w1-0..4` COMPLETE, tai ve
5 shard, ghep ra **256 dong**. Thieu 1 dong so voi 257 tien-dang-ky.

**Nguyen nhan (da truy, khong phai suy dien):** diem neo `id=-1` **khong nam trong**
`gs_shard_00..04`. Luc tao shard (2026-09-03 16:27) no duoc dat vao `gs_shard_smoke.jsonl`
(2 dong: `id=-1` va `id=0`) va duoc chay boi kernel **`gs-w1-smoke`**, ket qua o
`/home/ubuntu/gs/smoke/out_gs_smoke.jsonl`. Glob cua `gs_gather.sh` la `out_gs_0*.jsonl` nen
khong bat file smoke. **Khong co diem nao bi mat**: 5 shard chua dung `id=0..255`, khong trung,
khong thieu, khong bi hard-kill 12h (secs cao nhat 647s/diem).

**Kiem tra truoc khi ghep (bat buoc, vi neo den tu kernel khac):** kernel smoke va kernel
`gs-w1-0` **cung chay `id=0`**. So sanh 12 truong ket qua (`params`, `profile_hash`,
`equity_start`, `equity_final`, `date_first`, `date_last`, `full`, `devA`, `devB`, `n_trades`,
`n_trades_devA`, `n_trades_devB`): **GIONG NHAU HOAN TOAN**, ke ca `profile_hash`. Hai kernel
dung cung dataset, cung jar, cung moi truong => dong neo tu smoke la hop le de ghep.

File 257 dong duoc dung bang `research/kaggle/gsearch/`-ngoai (`/home/ubuntu/java/stage/gsbuild.py`):
1 dong neo (nguyen van tu smoke) + 256 dong Sobol. Ban 256 dong goc luu o
`/home/ubuntu/gs/out/gs_wave1_sobol256_raw.jsonl`. **Khong sua mot con so nao.**

---

## 2. Diem neo — KHONG VOID

`analyze_wave1.py` doc `id=-1`: **`equity_final = 60395`**, dung bang moc tien-dang-ky o
PREREG_GS muc 5 + `GS_BASELINE_NOTE.md`. Sai so = 0. `profile_hash = 7081c357ca12bdd6` (khop
`BASELINE_NOTE`). `devA`: CAGR 27.49%, maxDD -13.12%, 655 lenh.

=> **Wave KHONG VOID.**

Dung nhu muc 9.3 da bao truoc: log Kaggle cua kernel in `ANCHOR_CHECK expected=60390 ... MISMATCH`
vi hang `ANCHOR_EQUITY` trong `run.py` con la 60390. **Dong log do sai, ket qua thi dung.** Kiem
neo o day lam bang `analyze_wave1.py` (hang `ANCHOR_EQUITY_EXPECTED = 60395`), khong dung log kernel.

---

## 3. Buoc 1 — loc hop le: 115/256 diem qua, 141 diem bi loai

| ly do loai | so diem |
|---|---|
| khong hoan tat (`ok=false`) | 20 |
| `n_trades_devA < 300` | 65 |
| `maxDD < -25%` | 56 |
| NaN | 0 |
| **con lai hop le** | **115** |

(Mot diem co the trung nhieu ly do nen tong theo ly do > 141.)

**20 diem "khong hoan tat" — da truy nguyen, khong bo di im lang.** Ca 20 deu chay JVM xong
(`secs` 202-647s, khong timeout) va deu bao cung mot loi harness:
`TypeError: type complex doesn't define __round__ method`. Do la `run.py:178`
`((end/eq0) ** (1.0/yrs) - 1.0)` voi `end < 0`: co so am luy thua phan so -> so phuc -> `round()`
nem loi. **19/20 diem co `equity_final` AM** (tu -2455 den -162137, tu von 35000) — tuc la
**chay bay tai khoan**, khong phai mat du lieu. Diem thu 20 (`id=59`) co `equity_final=7411`
(-79% von) va `date_last=20240413` — ket thuc som, cung la diem chet.

=> Ca 20 deu la diem xau. Neu harness khong crash thi ca 20 se bi loai o bo loc `maxDD < -25%`
anyway. **Viec loai chung khong lam lech ket qua len phia tot.** Nhung phai ghi nhan: harness
wave-1 khong tinh duoc chi so cho diem equity am — day la loi can sua truoc wave sau, khong phai
loi cua thiet ke chon.

---

## 4. Cau hoi trung tam cua thiet ke: argmax NS co khac argmax CAGR khong?

**CO, va khac rat xa.**

| | id | CAGR devA | NS | maxDD devA | n_trades devA | xep hang NS |
|---|---|---|---|---|---|---|
| **argmax NS** (= diem DUOC CHON theo muc 4 buoc 4) | **149** | **21.13%** | **27.58** | -6.81% | 327 | 1/115 |
| **argmax CAGR** (doi chieu, KHONG duoc chon) | **127** | **53.61%** | 23.50 | -22.93% | 562 | **11/115** |
| diem neo C2b | -1 | 27.49% | 21.08 | **-13.12%** | 655 | — |

Ba dieu doc duoc, khong suy dien them:

1. **Dinh CAGR (id=127) nam ngoai top-5 NS** (hang 11/115). PREREG_GS muc 4 buoc 4 da chot truoc
   rang truong hop nay "la KET QUA, khong phai loi". Ghi nhan dung nhu vay.
2. **Diem duoc chon co CAGR THAP HON NEO 6.36pp** (21.13 vs 27.49). Luat chon (argmax NS) tra ve
   mot diem te hon neo tren chinh chi so chinh. Do la hau qua truc tiep, da tien-cam-ket, cua
   viec lay TAM vung rong thay vi dinh nhon.
3. **Dinh CAGR mua CAGR bang maxDD:** id=127 -22.93%, hai finalist CAGR cao nhat -22.17% (id=156)
   va -23.08% (id=172), so voi neo **-13.12%**. Ca ba deu qua bo loc -25% nen hop le theo luat,
   nhung khoang cach maxDD gan **10pp** so voi neo la mot su that dinh luong phai ghi. Muc 12.3
   da chot: rang buoc maxDD giu o tang equity, doc lap — va o tang do, cac diem CAGR cao **te hon
   neo ro rang**.

### Phan vi cua diem neo trong 115 diem hop le

| dai luong | gia tri neo | phan vi | so diem vuot neo |
|---|---|---|---|
| CAGR devA | 27.49% | **85.2%** | 17/115 (14.8%) |
| NS | 21.08 | **74.8%** | 29/115 |

Phan bo CAGR devA cua 115 diem hop le: min 2.18 / p25 11.19 / trung vi 16.38 / p75 23.03 /
max 53.61; **do lech chuan giua cac diem = 9.18pp**.

**Canh bao ve tinh so sanh duoc cua NS(neo) (quan sat, KHONG doi luat):** ban kinh chua k=10 lang
can cua **neo la 1.002**, trong khi cua 115 diem Sobol hop le co trung vi **1.238** va **min
1.053** — tuc la khong diem Sobol nao co ban kinh chat bang neo. NS(neo) do dat mot vung **cuc bo
hon** NS cua moi diem Sobol, nen con so phan vi 74.8% khong hoan toan cung don vi. Diem hop le
**gan neo nhat cach 0.733** trong khong gian `u` (duong cheo hop 15 chieu = 3.873): wave 1
**khong lay mau o lan can cua C2b**, nen no khong tra loi duoc truc tiep cau "C2b co nam giua mot
vung phang khong" — no chi tra loi "trong 115 diem rai deu, C2b o phan vi 85% CAGR".

---

## 5. Buoc 5 — finalist

Raw top-5 theo NS: `[149, 0, 181, 156, 172]`. Sau loc trung greedy `u >= 0.15` (muc 9.2):
**y het**, `[149, 0, 181, 156, 172]` — khong cap nao gan hon 0.15, nen loc khong cat gi.

| # | id | NS | CAGR devA | so voi neo | maxDD devA | n_trades devA | khoang cach u den neo |
|---|---|---|---|---|---|---|---|
| 1 | 149 | 27.58 | 21.13% | **-6.36pp** | -6.81% | 327 | 1.290 |
| 2 | 0 | 27.47 | 20.08% | **-7.41pp** | -9.48% | 300 | 1.025 |
| 3 | 181 | 26.34 | 23.06% | **-4.43pp** | -12.07% | 505 | 0.930 |
| 4 | 156 | 25.49 | 35.30% | +7.81pp | -22.17% | 519 | 1.431 |
| 5 | 172 | 25.12 | 42.37% | +14.88pp | -23.08% | **2246** | 1.244 |

**3/5 finalist co CAGR devA THAP HON neo.** Chi 2 finalist vuot neo, va ca hai bang cach nhan
gap doi maxDD. id=172 con chay **2246 lenh** tren DEV-A (neo: 655) — gap 3.4 lan tan so giao dich.

---

## 6. Buoc 4 — niem phong bang thu tu commit (muc 9.1)

`finalists.json` (id + tham so + NS + CAGR devA + maxDD devA + n_trades devA, **khong co mot so
devB nao**) da commit:

```
commit 9ca1b0e5fc35ced2fb495a283969dee9c5abf5be
2026-09-04T01:55:39+07:00  (= 2026-09-03T18:55:39Z)
```

Kem theo commit do: `export_finalists.py` (script xuat, chi doc `devA`) va `wave1_analyze.txt`
(nguyen van log `analyze_wave1.py`, khong chua so devB — da grep kiem truoc khi `git add`).

**Xac nhan tuan thu muc 9.1 buoc 3-4:** khong mot so `devB` nao duoc doc truoc commit tren.
Script doc devB (`/home/ubuntu/java/stage/devb.py`) **lay danh sach id tu `git show
HEAD:.../finalists.json`** (khong tu ban lam viec) va loai moi ban ghi khong phai finalist khoi
bo nho **truoc** khi mo truong `devB` — 252/257 ban ghi khong bao gio duoc mo truong devB.
**Khong co vi pham nao de bao.**

---

## 7. Muc 11.2 — nguong `neo + 2.35*sd_boot`: **sd_boot KHONG DO DUOC trong wave nay**

### 7.1 Ly do (ha tang, khong phai lua chon)

`PREREG_CI.md` muc 2 doi hoi `sd_boot` = do lech chuan block-bootstrap cua **HIEU** CAGR giua
diem do va neo, tinh **ghep cap** tren **chuoi loi nhuan NGAY** (block 21 ngay, 2000 rep,
seed 20260903). Chuoi ngay do khong ton tai:

- `gs-w1-*/run.py` ghi **de** cung mot `/kaggle/working/logs/sim.out` cho moi diem trong shard,
  va file jsonl chi giu chi so tong hop + loi nhuan theo **QUY** (8 quy cho DEV-A). Vi vay chuoi
  ngay chi con lai cho **diem cuoi cua moi shard** (`id` 51/102/153/204/255) va cho diem cuoi cua
  kernel smoke (`id=0`). Trong 5 finalist, **chi `id=0` co chuoi ngay**.
- Chuoi ngay cua **diem neo** khong co trong vung duoc phep doc: ban Kaggle da bi ghi de (smoke
  chay `id=-1` roi `id=0`, `sim.out` con lai la cua `id=0` — da xac nhan `b:51957` o dong cuoi),
  va ban Oracle chi nam trong `/home/ubuntu/java/devrun/` (`GS_FILE15`/`GS_FILE24`), la vung
  **CAM cham** trong job nay.
- Lay chuoi ngay cua 5 finalist = **chay lai sim** = bi cam trong job nay.

=> **Khong the tinh `sd_boot` dung phuong phap cho bat ky finalist nao.** Khong thay bang uoc
luong khong ghep cap: `PREREG_CI` muc 2.3 **cam** so hai CI rieng le (bootstrap doc lap pha tuong
quan va lam CI cua hieu rong gia).

### 7.2 Nguong duoc ap: dung `sd` DA DO SAN, lay gia tri LON NHAT (siet lai)

`CI_REAUDIT.md` muc (iii) da do `sd(hieu CAGR)` tren cung cua so DEV, dung **dung** phuong phap
cua `PREREG_CI` (block 21 ngay, 2000 rep, seed 20260903). Lay cac gia tri do lam thay the:

| lop thay doi | sd(hieu) da do | nguong `27.49 + 2.35*sd` | finalist nao vuot |
|---|---|---|---|
| chi doi tham so exit | 2.57pp | 33.53% | 156 (35.30), 172 (42.37) |
| doi selector | 4.45pp | 37.95% | 172 (42.37) |
| **noi gate (lon nhat da do)** | **6.34pp** | **42.39%** | **khong finalist nao** |

Moi finalist khac neo o **ca 15 chieu** — nhieu hon "doi selector" — nen lop ap dung it nhat la
selector, va **lop bao thu nhat trong so da do la 6.34pp**. Chon `sd` lon nhat lam nguong **cao
nhat**, tuc la **kho hon** de tuyen bo thanh cong: day la siet lai, dung huong ma muc 11.3 cho phep.

**Ket qua theo nguong bao thu (6.34pp): KHONG finalist nao vuot `neo + 2.35*sd_boot`.**
Va phai ghi thang: ket cuc nay **doi dau** khi doi lop `sd` (id=172 vuot o 2 lop, truot o lop thu
ba, va truot chi **0.02pp**). Ban than su phu thuoc do la ket qua: **du lieu DEV hien co khong
phan biet duoc** id=172 voi neo.

### 7.3 Muc 10.2 — CI block-bootstrap cua CAGR canh khoang cach 3pp (bat buoc in)

CI cua chinh diem neo tren DEV-A khong tinh duoc (thieu chuoi ngay cua neo, muc 7.1). In hai
nguon do duoc, deu theo dung `PREREG_CI`:

**(i) CI da do san cua HIEU, co diem neo la mot ve** (`CI_REAUDIT.md`, block 21 ngay, 2000 rep,
seed 20260903, ghep cap, DEV 911 ngay):

| cap | d (pp CAGR) | CI95 block 21 |
|---|---|---|
| C2b vs N4_a8s175 | -0.62 | **[-5.55, +4.32]** |
| C2b vs C2_g015 | +7.33 | [-1.72, +15.61] |
| C2b vs RG95 | +3.12 | [-2.49, +8.40] |

**Khoang cach 3pp nam GON TRONG ca ba CI.** Nguong 3pp goc o muc 4 buoc 7 vi vay khong phan biet
duoc voi 0 — dung nhu muc 11.1 da chot truoc.

**(ii) CI tuyet doi do tren chuoi ngay DUY NHAT co san cua wave nay** (`id=0`, finalist #2,
DEV-A 730 ngay, `CAGR = prod(1+r)^(365/730)-1`, moving-block circular, 2000 rep, seed 20260903):

| do dai block | sd | CI95 | n_eff |
|---|---|---|---|
| **21 ngay (chinh)** | **9.557pp** | **[4.344, 41.430]** | 35 khoi |
| 10 ngay (do ben) | 10.383pp | [3.321, 43.569] | 73 khoi |
| 42 ngay (do ben) | 9.002pp | [5.361, 39.672] | 18 khoi |

Diem uoc luong 20.031% (harness ghi 20.08% theo cong thuc `yrs=365.25`; parser da doi chieu khop
tung so: `equity_end devA = 50426`, `full = 51957`, `cagr devA = 20.08%`).
**Day la CI TUYET DOI cua MOT cau hinh, KHONG phai `sd_boot` cua hieu**, va theo `PREREG_CI` muc
2.3 no **khong duoc** dung de so hai cau hinh. In ra chi de thay do rong that cua thang do
CAGR tren DEV-A: **CI 95% cua mot cau hinh trai gan 37pp**. Khoang cach 3pp la mot phan muoi hai
be rong do.

**=> Cau bat buoc theo muc 10.2:** khoang cach 3pp — va ca khoang cach 14.88pp cua finalist tot
nhat — **khong phan biet duoc voi nhieu o muc CI da do**.

---

## 8. Muc 11.2 — dieu kien tang GHEP CAP: KHONG THUC HIEN DUOC cho **ca 5** finalist

Muc 11.2 doi hoi finalist phai thang neo o tang **tung lenh / tung tick** theo thong ke ghep cap,
CI cua hieu khong chua 0. `research/analysis/paired_test.py` doc
`/home/ubuntu/java/devrun/<TAG>/storage/printDone.csv` cho tung run.

- Khong finalist nao co `printDone.csv`: chung chay tren Kaggle, va `run.py` ghi de
  `storage/printDone.csv` moi diem => chi con lai cua diem cuoi moi shard. (`id=0` co, nhung
  neo thi **khong** — ban Oracle nam trong `devrun/`, vung cam.)
- Muc 12.3 da chot truoc: voi gene **khong phai selector/gate**, dieu kien nay **khong the thoa
  bang du lieu hien co**. Moi finalist khac neo dong thoi o ca 15 chieu, trong do **14 chieu
  khong co bieu dien nao o tang tick**: `SIM_F_BASE`, `SIM_U_MAX`, `DCA_GRID_SCALE`,
  `SIM_RATE_PROFIT_STOP_MARKET`, `TS_GIVEBACK_RATIO`, `SIM_TS_MAX_GAP(_WEAK)`,
  `SIM_TS_PNOPUMP_WEAK_THR`, `SIM_LOSER_TIME_STOP_HOURS`, `SIM_AI_DYNAMIC_*`. Chi
  `SELECTOR_RANK_TOPK` (va mot phan `SIM_PREDICT_SYMBOL_RATE_MAX`, `SIM_MIN_MOMENTUM_15M`) co
  the dung o tang tick — nhung mot phep thu chi tren TOPK **khong** kiem tra finalist.

=> **Ca 5 finalist (149, 0, 181, 156, 172) roi vao truong hop muc 12.3.** Dieu kien bat buoc cua
(a) khong the thoa. Khong chay sim de tao `printDone.csv` (bi cam trong job nay va se chiem slot
java) — **da dung va bao lai**, dung nhu yeu cau.

---

## 9. Buoc 6 — xac nhan tren DEV-B (giu nguyen nguong 0.6 / -20%, muc 13.2)

Doc **sau** commit `9ca1b0e`, chi doc devB cua dung 5 finalist.

| id | CAGR devA | CAGR devB | nguong 0.6*devA | maxDD devB | n_trades devB | dk1 | dk2 | ket qua |
|---|---|---|---|---|---|---|---|---|
| 149 | 21.13 | 21.58 | 12.68 | -0.10% | 139 | dat | dat | **CONFIRMED** |
| 0 | 20.08 | 6.26 | 12.05 | -6.08% | 173 | truot | dat | khong CONFIRMED |
| 181 | 23.06 | 12.60 | 13.84 | -8.55% | 233 | truot | dat | khong CONFIRMED |
| 156 | 35.30 | 29.27 | 21.18 | -5.35% | 251 | dat | dat | **CONFIRMED** |
| 172 | 42.37 | 40.65 | 25.42 | -6.27% | 1087 | dat | dat | **CONFIRMED** |

**3/5 CONFIRMED (149, 156, 172); 2/5 khong (0, 181).**

**Cau bat buoc theo muc 13.2 — gan cho TUNG ket luan tren, khong tru mot cai nao (149, 0, 181,
156, 172):**

> "tap xac nhan nay co n_eff = 51 khoi; doi chung seed khong chua thong tin cung vuot nguong tren
> chinh tap nay, nen ket qua buoc 6 khong phan biet duoc giua tin hieu that va tinh chat cua cua so."

Vi vay ba nhan CONFIRMED o tren **khong duoc doc nhu bang chung**. Chung duoc bao cao vi luat
tien-dang-ky buoc phai bao cao, khong vi chung noi len dieu gi.

---

## 10. Buoc 7 — PHAN QUYET: **(b)**

Kiem tung dieu kien cua **(a)** theo dung van ban da siet:

| dieu kien cua (a) | trang thai |
|---|---|
| co >= 1 finalist CONFIRMED (buoc 6) | dat **ve hinh thuc** (3/5) — nhung muc 13.2: khong doc duoc nhu bang chung |
| `CAGR(devA) > neo + 2.35*sd_boot` (muc 11.2) | **khong dat** o nguong bao thu (6.34pp -> 42.39%); va `sd_boot` dung phuong phap **khong do duoc** (muc 7.1) |
| thang neo o tang GHEP CAP, CI cua hieu loai 0 (muc 11.2) | **khong the thuc hien** cho ca 5 finalist (muc 12.3) |

=> **(a) khong duoc tuyen bo.** Ket qua nay da duoc muc 13.2 du bao nguyen van: "(a) tren thuc te
**khong the tuyen bo** trong wave nay".

Giua (b) va (c), theo **dung chu** cua muc 4 buoc 7: co finalist CONFIRMED nhung khong diem nao
vuot nguong => **(b)**.

**Nhung phai ghi thang mot dieu, vi day la cho de tu lua nhat:** cai duy nhat dat (b) thay vi (c)
la ba nhan CONFIRMED o buoc 6 — chinh la ba nhan ma muc 13.2 tuyen bo **khong co suc phan biet**
(cua so 2024H1 co `n_eff = 51 khoi`; doi chung seed khong chua thong tin cung "vuot nguong" tren
chinh cua so nay). Vay **ranh gioi (b)/(c) khong duoc thiet lap bang du lieu**. Ve noi dung thuc
te, (b) va (c) o wave nay dan den **cung mot ket luan**, va do la ket luan ma muc 11.2 da chot
truoc cho ca hai truong hop:

> **KET LUAN CHINH: khong the phan biet bang du lieu DEV hien co.**

Va — theo dung muc 11.2 — ket luan nay **KHONG** duoc doc thanh "C2b la tot nhat". Bang chung o
muc 4 cho thay dieu nguoc lai la co the: 17/115 diem hop le co CAGR devA cao hon neo, va C2b nam
o phan vi 85%, khong phai 100%. Dieu do khong chung minh duoc gi, va cung khong bac bo duoc gi.

### Nhung gi phan quyet (b) buoc phai lam theo (muc 4 buoc 7 + muc 11.3 + muc 13.4)

- **Dung lai. KHONG re-baseline.** Khong doi C2b sang bat ky finalist nao, ke ca id=172
  (equity/CAGR cao hon) — do dung la kieu chon tren nhieu ma muc 11.3 goi ten.
- **KHONG lam wave 2 tren cung khong gian** (N=512 hay thu hep range). Muc 12.4: quet tiep tham so
  la **huong sai**.
- **KHONG buoc sang VALIDATION.** So lan cham VALIDATION giu nguyen = 5. Wave nay khong tao ra
  ung vien nao du dieu kien de de nghi L3.
- Duong "log quyet dinh tung tick" da chet (muc 13.4 / `TICKLOG_RESULT.md`). Duong con lai la
  **them cuoc doc lap** (them symbol / lenh ngan hon / thi truong khac), khong phai them nam.

---

## 11. Muc 6 — phan ra phuong sai (CHAN DOAN, khong dung de chon)

**CV R^2 IN TRUOC, dung dieu kien muc 6.** Surrogate `GradientBoostingRegressor(random_state=42)`,
`u in [0,1]^15 -> CAGR devA`, 115 diem hop le, `KFold(5, shuffle, random_state=42)`:

```
CV R^2 = 0.3730     folds = [0.5474, 0.0070, 0.6433, 0.4583, 0.2092]
```

`0.3730 >= 0.30` => **dat nguong, DUOC PHEP bao cao phan ra.**

**Nhung phai ghi kem do on dinh:** cac fold trai tu **0.007 den 0.643**. Trung binh vua qua nguong
0.30. Mot fold gan nhu khong giai thich duoc gi. Nghia la thu tu importance duoi day co the doi
neu doi seed chia fold. **Doc nhu goi y huong, khong nhu do luong.**

**Moi truong: CPU, khong GPU** (muc 13.3). `sklearn 1.7.2 / scipy 1.15.3 / numpy 2.2.6`,
`CUDA_VISIBLE_DEVICES=""`. Khong dung XGBoost, khong dung `device="cuda"`.

### Permutation importance (n_repeats=30, random_state=42)

| # | chieu | mean | std |
|---|---|---|---|
| 1 | **SIM_F_BASE** | **0.4995** | 0.0790 |
| 2 | **SIM_RATE_PROFIT_STOP_MARKET** | **0.4547** | 0.0391 |
| 3 | **DCA_GRID_SCALE** | **0.2783** | 0.0372 |
| 4 | SIM_U_MAX | 0.0468 | 0.0063 |
| 5 | SIM_MIN_MOMENTUM_15M | 0.0325 | 0.0051 |
| 6 | SELECTOR_RANK_TOPK | 0.0309 | 0.0038 |
| 7 | SIM_AI_DYNAMIC_MIN | 0.0233 | 0.0040 |
| 8 | SIM_PREDICT_SYMBOL_RATE_MAX | 0.0231 | 0.0080 |
| 9 | SIM_AI_DYNAMIC_MULTIPLIER | 0.0227 | 0.0034 |
| 10 | SIM_TS_PNOPUMP_WEAK_THR | 0.0099 | 0.0016 |
| 11 | SIM_TS_MAX_GAP | 0.0053 | 0.0007 |
| 12 | SIM_LOSER_TIME_STOP_HOURS | 0.0042 | 0.0009 |
| 13 | SIM_AI_DYNAMIC_MAX | 0.0036 | 0.0005 |
| 14 | SIM_TS_MAX_GAP_WEAK | 0.0019 | 0.0003 |
| 15 | TS_GIVEBACK_RATIO | 0.0014 | 0.0002 |

### Doc gi tu day — va khong duoc doc gi

**Ba chieu dau chiem gan het**, roi tut mot buoc gap 6 lan xuong chieu thu tu (0.278 -> 0.047).
Ba chieu do la `SIM_F_BASE` (kich thuoc vi the goc), `SIM_RATE_PROFIT_STOP_MARKET` (nguong chot
lai) va `DCA_GRID_SCALE` (he so nhan luoi DCA) — **ca ba deu la chieu KICH THUOC / DON DAY, khong
mot chieu nao la chieu CHAT LUONG TIN HIEU.**

Huong cua PDP thong nhat va don dieu voi ca ba:

| chieu | PDP CAGR du doan tu u thap -> u cao |
|---|---|
| SIM_F_BASE | -4.83 -> -3.22 -> ... -> +4.84 -> +5.09 -> **+8.12** |
| SIM_RATE_PROFIT_STOP_MARKET | -5.16 -> -4.27 -> ... -> +3.43 -> **+6.62** |
| DCA_GRID_SCALE | -4.96 -> -3.41 -> ... -> +4.07 -> +3.20 |

**Tuc la: trong 115 diem con lai sau bo loc, CAGR tang gan don dieu theo don day.** Cai ma
surrogate hoc duoc chu yeu la "danh nang hon thi CAGR cao hon" — mot quan he ke toan, khong phai
mot phat hien ve chien luoc. Va no khop voi muc 4 cua doc nay: cac diem CAGR cao nhat (127, 172,
156) deu co maxDD -22..-23% so voi -13.12% cua neo.

=> **Chieu that su lam doi ket qua xep hang CAGR devA cua wave 1 la truc don day, khong phai truc
chat luong xep hang.** Do la cau tra loi (chan doan) cho cau hoi "chieu nao bi HPO che": theo do
nay, khong co chieu tin hieu nao bi che ro rang; chieu duy nhat co do doc lon la chieu **rui ro**,
va chieu do bi rang buoc maxDD chan lai — dung nhu thiet ke. `SELECTOR_RANK_TOPK` xep hang **6/15**
voi importance 0.031, tuc **khong** co dau hieu la mot chieu bi bo qua.

**Ba dieu KHONG duoc suy ra tu phan tren (theo muc 6):**

1. **Khong tinh duoc chi so Sobol bac 1 / bac tong.** 256 diem tu **mot** day Sobol duy nhat khong
   cho phep. Muon co chi so Sobol dung phai co thiet ke **Saltelli** (ma tran A, B, AB_i) — wave 1
   khong co, va khong the "hoi to" tu day hien co. Cac con so o tren la permutation importance cua
   mot surrogate, **khong** la Si/ST.
2. **Khong duoc dung phan ra nay de chon diem.** Khong dung.
3. **Khong duoc bo chieu nao khoi wave sau dua tren bang nay** ma khong co mot doc PRE-REG moi.
   Voi CV R^2 = 0.373 va mot fold = 0.007, bang nay khong du chac de bo 12 chieu duoi.

**Gia tri thuc con lai cua wave 1 nam o day**, dung nhu muc 11.3 da noi truoc: khong phai tim
diem tot hon, ma la biet rang truc co do doc lon nhat trong hop tham so hien tai la **truc don
day** — va truc do da bi rang buoc rui ro chan. Neu muon cai thien that thi phai doi **feature /
so cuoc doc lap**, khong phai doi 15 hang so nay.

---

## 12. Loi ha tang phat hien trong wave nay (can sua truoc wave sau, khong doi ket qua wave 1)

1. **`run.py` crash tren diem co equity am** (`round()` cua so phuc). 20/256 diem mat het chi so
   thay vi duoc ghi nhan la diem chet. Sua: kep `end/eq0 <= 0` truoc khi luy thua.
2. **`run.py` khong luu chuoi equity NGAY cho tung diem.** Day la ly do duy nhat khien muc 11.2
   khong tinh duoc `sd_boot` va muc 10.2 khong tinh duoc CI cua neo. Chi phi luu them: 911 so
   nguyen/diem (~10KB/shard). **Day la thu can sua nhat.**
3. **`run.py` khong luu `printDone.csv` theo diem** => tang ghep cap khong lam duoc (muc 8).
4. **`gs_gather.sh` glob `out_gs_0*.jsonl` khong bat file smoke**, nen bo sot dong neo.
5. **`ANCHOR_EQUITY = 60390` trong `run.py`** — da biet truoc o muc 9.3, log in MISMATCH sai.
6. **Docstring `gen_params.py`** con ghi 60390 (muc 9.3). Khong sua trong job nay (`gen_params.py`
   bi cam sua).

---

## 13. Nhung gi KHONG bi cham trong job nay

- **VALIDATION (2024-07-15..2025-12-31): khong cham.** So lan cham giu nguyen = 5.
- **HOLDOUT 2026: khong cham.**
- `docs/PREREG_GS.md`: **khong sua mot ky tu nao** (ke ca them). Moi nhan xet nam trong file nay.
- `research/kaggle/gsearch/gen_params.py`, `params.jsonl`, `analyze_wave1.py`: khong sua.
- Khong chay java, khong chay sim, khong submit kernel Kaggle moi.
- Khong cham `/home/ubuntu/fs/`, `/home/ubuntu/g015/`, `/home/ubuntu/tick/`,
  `/home/ubuntu/feataudit/`, `/home/ubuntu/oifix/`, `/home/ubuntu/java/devrun/`.
- Khong `git push`.
- Moi doan devB dien ra **sau** commit `9ca1b0e` va **chi** cho 5 finalist trong file da commit.

## 14. File

| duong dan | noi dung |
|---|---|
| `/home/ubuntu/gs/out/gs_wave1_all.jsonl` | 257 dong (1 neo + 256 Sobol) |
| `/home/ubuntu/gs/out/gs_wave1_sobol256_raw.jsonl` | 256 dong nguyen ban tu 5 shard |
| `research/kaggle/gsearch/finalists.json` | niem phong, commit `9ca1b0e` |
| `research/kaggle/gsearch/wave1_analyze.txt` | log nguyen van `analyze_wave1.py` |
| `research/kaggle/gsearch/export_finalists.py` | script xuat finalists (chi devA) |
| `/home/ubuntu/gs/out/devb_step6.json` | ket qua buoc 6 (doc sau niem phong) |
| `/home/ubuntu/gs/out/analyze_wave1.log` | ban goc cua log tren |
