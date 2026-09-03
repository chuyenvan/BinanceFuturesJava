# PREREG_B4 — mo lai nhanh B4: rolling-percentile gate

Chot luc: 2026-09-03, **TRUOC khi chay bat ky run nao**. Commit cua file nay phai co TRUOC moi
commit ket qua B4. Neu thu tu commit nguoc lai => toan bo ket qua B4 bi coi la **VOID**.

Pham vi: **CHI DEV** (2022-01-01 .. 2024-06-30). KHONG cham VALIDATION (2024-07-15..2025-12-31),
KHONG cham HOLDOUT 2026.

---

## 0. Vi sao mo lai — va vi sao mo lai KHONG phai la di tim chien thang

Ly do dong cu (`docs/AUDIT_APPLIED.md` muc B4): "RG95/RG97/RG95w180 deu thap hon C2b 60390
(56683 / 52045 / 59120) => THUA tren nen C2b; EV am tren nen C2b => khong nen".

Do lai bang block-bootstrap **ghep cap** (`docs/CI_REAUDIT.md` NHOM A #6c/#6d/#6e, phuong phap
chot truoc o `docs/PREREG_CI.md`): **ca 3 hieu nam TRONG CI**:

| cap | d (pp CAGR) | CI95 block 21 | CI95 block 10 | CI95 block 42 | phan loai |
|---|---|---|---|---|---|
| C2b - RG95 | +3.12 | [-2.49, +8.40] | [-1.44, +8.27] | [-3.06, +8.84] | khong phan biet duoc |
| C2b - RG97 | +7.20 | [-0.29, +14.76] | [+0.38, +14.64] | [-0.82, +16.17] | khong phan biet duoc |
| C2b - RG95w180 | +1.06 | [-4.79, +7.34] | [-4.10, +6.51] | [-5.40, +7.39] | khong phan biet duoc |

Va **maxDD quan sat cua ca 3 khong te hon C2b**: RG95 **-12.88**, RG97 **-12.33**,
RG95w180 -13.12 vs C2b **-13.12**.

=> Cau "EV am tren nen C2b" **khong duoc du lieu ho tro**: no la ket luan rut ra tu do chinh xac
gia (so sanh hai diem uoc luong ma khong co thanh do tin cay). Nhanh B4 la nhanh **duy nhat** trong
`CI_REAUDIT` HE QUA (ii) vua nam trong nhieu, vua khong vi pham rang buoc cung nao, vua co dau hieu
tot hon o chieu khac (maxDD).

Chi phi mo lai la thuc: `GateRollingThreshold.java` (97 dong) **da bi xoa** o commit `5f40a90`
(DOT 2 xoa co tro) => phai cai lai co che + pre-reg moi.

### 0.1 Ky vong PHAI ghi TRUOC khi chay — bai nay gan nhu chac chan KHONG chung minh duoc RG thang

`CI_REAUDIT` HE QUA (iii): `sd(hieu CAGR)` cho thay doi kieu **"noi gate"** tren DEV la **6.34pp**.
De phat hien mot cai thien that 3pp o cong suat 80% can **~87 nam** du lieu; DEV co **2.496 nam**.

=> Ket qua **du kien** la "KHONG PHAN BIET DUOC". Do la **dau ra hop le va co gia tri**: no dong
nhanh bang bang chung dung, thay vi bang do chinh xac gia. Bai nay **KHONG** duoc coi la thanh cong
chi khi tim ra so cao hon 60390. Neu trong luc chay ma xuat hien y muon thu them bien the de tim so
dep => **DUNG**: do la chon tren nhieu (leak L2).

---

## 1. Co che rolling gate — chot cung

### 1.1 Cho no cam vao
Gate MOM15 tang 2 (`AIRejectFilter.checkSignalDynamic`) hien dung nguong CO SO **hang so**
`Configs.MIN_MOMENTUM_15M` (= `SIM_MIN_MOMENTUM_15M` = 0.008), roi nhan he so theo score:

```
dyn_thr = thr_base * max(AI_DYNAMIC_MIN, score / PREDICT_SYMBOL_RATE_MAX_THRESHOLD * AI_DYNAMIC_MULTIPLIER)
```

Rolling gate **CHI thay `thr_base`** hang so bang mot nguong truot theo thoi gian.
Phan nhan he so theo score **KHONG doi mot chu**. Ca hai duong dung `thr_base` (early-hard-gate va
`dyn_thr`) deu dung cung mot gia tri truot.

### 1.2 Dinh nghia nguong truot — 5 dieu phai chot, chot het o day

1. **Dai luong lay phan vi**: `AiPredictionData.predReturn15M` cua prediction **muc thi truong**,
   lay mau tren **luoi 15 phut** (chi cac moc `ts % 900000 == 0` cua `predictionMap`).
2. **Phan vi**: `p` = `SIM_GATE_ROLLING_PCT`, hop le khi `0 < p < 1`. Phan vi tinh tren mau da sap
   xep tang dan, **khong noi suy**: `k = min(m-1, max(0, floor(p*(m-1))))`, lay `buf[k]`, voi `m` =
   so mau trong cua so.
3. **Cua so**: `W` = `SIM_GATE_ROLLING_DAYS` ngay, khoang **nua mo `[t - W, t)`** — chi du lieu
   **TRUOC** `t`. Nhan qua, **khong nhin truoc**.
4. **Cap nhat**: **moi GIO wall-clock**. Bang `gio -> nguong` duoc tinh san MOT LAN luc init; truy
   van tai `t` lay `floorEntry(t)` (moc gio <= t). Trong mot gio nguong la hang so.
5. **Dau ky / chua du cua so**:
   - Moc gio dau tien = gio tron dau tien `>= ts_min + W` (phai co **DU** cua so W moi sinh moc).
   - Moc gio nao co `m < 96*7 = 672` mau (< 7 ngay du lieu trong cua so) thi **BO**, khong sinh moc.
   - Truy van `t` **truoc** moc dau tien => tra ve `Configs.MIN_MOMENTUM_15M` (hanh vi cu). So lan
     nay duoc dem (`nBeforeFirst`) va in ra log.
   - **Ghi truoc de khong ai dien giai lai sau**: tren dataset DEV hien tai `predictionMap` bat dau
     khoang 2021-04, nen moc gio dau tien roi vao ~2021-07 (W=90) / ~2021-10 (W=180) — tuc **truoc**
     2022-01-01 => vung dau ky **KHONG** roi vao DEV. Bao cao ket qua **phai in `nBeforeFirst`**;
     neu no `> 0` thi phai ghi ro va noi ro anh huong.

### 1.3 Tat / bat
- `SIM_GATE_ROLLING_PCT` khong khai bao / rong / ngoai `(0,1)` => gate truot **TAT**, `thres15M`
  tra thang `Configs.MIN_MOMENTUM_15M` => hanh vi **byte-identical** voi C2b (xem section 6).
- Tham so di qua **cong `Cfg`** (`Cfg.get`), khai trong **profile**. **KHONG** doc
  `System.getenv` truc tiep. `tools/check_cfg_gateway.sh` phai OK.
- Java: SLF4J. **Cam** `System.out` / `System.err` / `printStackTrace` trong code moi.

---

## 2. So bien the toi da: **3** — liet ke va KHOA

Dung **DUNG 3 diem da tung do** trong lan chay cu. Khong them diem moi => **khong them n_trials**
so voi so lan da thu trong qua khu; day khong phai mot vong tim kiem moi.

| ma run | profile | SIM_GATE_ROLLING_PCT | SIM_GATE_ROLLING_DAYS | doi ung run cu |
|---|---|---|---|---|
| `B4_RG95` | `profiles/b4_rg95.properties` | 0.95 | 90 | RG95 (56683) |
| `B4_RG97` | `profiles/b4_rg97.properties` | 0.97 | 90 | RG97 (52045) |
| `B4_RG95W180` | `profiles/b4_rg95w180.properties` | 0.95 | 180 | RG95w180 (59120) |

Moi key con lai trong 3 profile **giong y `profiles/c2b.properties`** (ke ca
`WFO_FUNDING_PRED_DIR=/home/ubuntu/predwf_map_s1a2`, `SIM_MIN_MOMENTUM_15M=0.008`).

**Chay qua 3 bien the = chon tren nhieu (leak L2) va lam VOID bai nay.** Neu ca 3 khong dat thi
**KET LUAN**, khong them bien the, khong noi rong cua so, khong doi phan vi.

---

## 3. TIEU CHI CHINH

- `d = CAGR(bien the) - CAGR(C2b)` tren DEV, **911 ngay** 2022-01-01..2024-06-29.
- Equity = `b + unP` (**mark-to-market**), doc y het `qret.py` / `PREREG_CI` section 1.
- `CAGR = (prod(1+r))^(365/911) - 1`, `r_1 = E_1/35000 - 1` (`CAPITAL_START=35000`).
- `sd_boot` = do lech chuan cua `d` tu **block-bootstrap GHEP CAP**: moving-block **circular**,
  block **21 ngay**, **2000 rep**, **seed 20260903**, mot danh sach chi so ngay dung cho **ca hai**
  run trong cap (`PREREG_CI` section 2.1-2.4).
- **Hieu chinh so sanh boi** cho 3 bien the: `sqrt(2 * ln 3) = 1.4823` => dung **1.48**.

> **DAT tieu chi chinh <=> `d > +1.48 * sd_boot`** (mot phia, huong "RG hon C2b").

Bao cao **bat buoc** kem theo, de nguoi doc thay ca buc tranh: CI95 percentile cua `d` o **ca 3**
do dai block **21 / 10 / 42**, `sd(d)`, `P(d>0)`, va phan loai theo `PREREG_CI` section 4
(SONG / KHONG PHAN BIET DUOC / DAO CHIEU). Phan loai do la **thong tin bo sung**; **dieu kien
quyet dinh** la nguong `1.48 * sd_boot` o block **21**.

---

## 4. RANG BUOC CUNG

**maxDD >= -15.12%** (moc cu cua du an), do o **tang equity** tren duong equity ngay **quan sat**
(`b+unP`), **KHONG bootstrap** (`PREREG_CI` section 2.5 cam bootstrap maxDD).

Bien the vi pham rang buoc nay => **CHET**, khong xet CAGR (khuon H1b/H1c).

---

## 5. MOT tieu chi PHU — chot TRUOC khi chay

Ly do ton tai cua rolling gate la **thich nghi drift / che do thi truong** (mean `predReturn15M`
troi 0.0036 -> 0.0091 giua cac quy => nguong co dinh lam selectivity dao dong). Nen chot **DUNG MOT**
phep cat theo **NGAY cu the**:

- **Doan BEAR**: `2022-01-01 .. 2022-12-31` (365 ngay)
- **Doan HOI PHUC**: `2023-01-01 .. 2023-12-31` (365 ngay)
- Doan `2024-01-01..2024-06-29` **khong dung** cho tieu chi phu.

Do trong TUNG doan, cho C2b va cho tung bien the: CAGR annualized cua doan (tu chuoi loi nhuan
**ngay** trong doan, `CAGR = (prod(1+r))^(365/n) - 1`) va maxDD cua doan. Bao cao `d` cua tung doan
kem CI95 block-bootstrap **ghep cap** block **21 ngay**, **2000 rep**, **seed 20260903**, tinh
**rieng trong tung doan**.

Du bao truoc (de khong ai ngac nhien roi dien giai lai): moi doan chi ~**18 khoi** 21 ngay => CI se
**rat rong**, gan nhu chac chan chua 0.

**RANG BUOC CUNG cua tieu chi phu:**
- Day la tieu chi **PHU**. **KHONG duoc dung de tuyen bo thang** neu tieu chi chinh (section 3)
  khong dat.
- **KHONG duoc them phep cat nao khac** (quy, thang, regime khac, nguong volatility...) sau khi
  thay so. Chi doan BEAR va doan HOI PHUC o tren.

---

## 6. CONG NGHIEM THU BAT BUOC — truoc khi tin bat ky so nao

Chay lai C2b bang **code da sua** voi rolling gate **TAT** (profile `profiles/c2b.properties`,
khong co key `SIM_GATE_ROLLING_*`), dung ban chuan `tools/run_c2b_dev.sh`:

```
tools/run_c2b_dev.sh /home/ubuntu/src/BinanceFuturesJava/profiles/c2b.properties \
                     B4_OFF /home/ubuntu/wfo_ds_b4off /home/ubuntu/java/devrun/C2b
```

**PASS <=>** ca hai dieu sau:
1. `cmp -s <(tail -n +2 $B/B4_OFF/storage/printDone.csv) <(tail -n +2 $B/C2b/storage/printDone.csv)`
   tra `rc=0` (byte-identical, bo dong header);
2. equity cuoi `b:60390`, `TICKER_SOURCE=aerospike` (Oracle).

**FAIL =>** ban sua code da lam lech thu khac. **PHAI sua truoc.** **KHONG duoc chay 3 bien the.**

---

## 7. BA CACH DOC KET QUA (a) / (b) / (c) — chot truoc, khuon `PREREG_GS` section 4 buoc 7

- **(a)** Co **>= 1** bien the vua dat rang buoc cung section 4, vua co `d > +1.48 * sd_boot`
  => luan diem "rolling-percentile gate co gia tri o tang equity DEV" **DUOC CHUNG MINH**.
  Nhanh B4 **GIU MO**. Buoc tiep la **DE NGHI** cham VALIDATION theo L3 — **khong tu dong chay**.
  Van phai ghi kem `sd_boot` va CI de nguoi doc thay do rong.

- **(b)** Tat ca bien the dat rang buoc cung nhung **khong bien the nao** vuot nguong
  => **KHONG PHAN BIET DUOC bang du lieu DEV hien co**. **DONG** nhanh B4 voi ly do **dung**:
  "DEV khong co suc phan biet o tang equity cho thay doi kieu gate (`sd` 6.34pp)" — **KHONG** phai
  "RG thua" va **KHONG** phai "C2b tot hon". **KHONG re-baseline**, khong doi baseline sang RG,
  **khong** mo them bien the tren cung khong gian. Kem theo: cau "EV am tren nen C2b" trong
  `AUDIT_APPLIED` muc B4 phai **rut**.

- **(c)** **Khong** bien the nao dat rang buoc cung maxDD
  => **DONG** nhanh B4 bang **RANG BUOC CUNG** (khuon H1b/H1c), khong can ban CAGR.

Truong hop hon hop (mot so bien the chet rang buoc cung, so con lai khong vuot nguong) doc theo
**(b)** cho nhom con song, va ghi ro bien the nao chet vi rang buoc cung.

**Khong duoc doc theo cach khac.** Khong them bo loc hau kiem, khong doi tieu chi chinh, khong doi
he so 1.48, khong doi moc maxDD -15.12%, khong doi do dai block chinh (21) sau khi thay so.

---

## 8. Gioi han pham vi — chot cung

- **CHI DEV** 2022-01-01..2024-06-30 (`SIM_END_DATE=20240630`). KHONG cham VALIDATION
  (2024-07-15..2025-12-31), KHONG cham HOLDOUT 2026.
- **KHONG rebuild bins**, KHONG cham `/home/ubuntu/predwf_map_s1a2/` hay file OI. Dung DUNG
  `WFO_FUNDING_PRED_DIR=/home/ubuntu/predwf_map_s1a2` nhu `c2b.properties` de ket qua so duoc voi
  baseline **60390**. (Mot agent khac dang sua du lieu OI ra duong dan MOI — bai nay khong dung
  duong dan do.)
- Dataset WFO chi build **tam** cho chinh cac run nay va **xoa ngay sau khi xong** (dia con ~19G).
- **Mot slot java duy nhat**: kiem `pgrep -a java` rong truoc moi run; sau khi xong khong de JVM
  zombie (xac nhan bang `readlink /proc/<pid>/cwd`, **khong** `pkill -f`).
- KHONG submit kernel Kaggle. KHONG cham `/home/ubuntu/gs/`, `/home/ubuntu/oifix/`,
  `/home/ubuntu/oiprobe/`.
- KHONG sua/xoa kill-switch `SHADOW_NO_PUSH` hay bat ky co chan dat lenh that.
- KHONG `git push`.

---

## 9. THU TU THUC HIEN — bat buoc

1. **Commit file nay.** Ghi lai commit hash. (Thu tu se bi kiem bang timestamp.)
2. Cai lai `GateRollingThreshold` cho khop code hien tai + 3 profile `profiles/b4_rg*.properties`.
   Build (`mvn -DskipTests package`). Chay `tools/check_cfg_gateway.sh` (phai OK).
3. **Cong nghiem thu section 6.** FAIL => DUNG, sua, khong chay tiep.
4. Chay **3** bien the tren DEV.
5. Cham: `qret.py` (mark-to-market) + `research/analysis/paired_test.py` +
   `research/analysis/ci_b4.py` (cung khuon `ci_group_a.py`, chot o `PREREG_CI`).
6. Viet `docs/B4_RESULT.md` theo dung section 3 / 4 / 5 / 7. Commit **sau**.

## 10. NHUNG GI PRE-REG NAY KHONG LAM

- Khong doi diem uoc luong nao cua C2b (b:60390 / CAGR 24.43 / maxDD -13.12).
- Khong sua `docs/PREREG_CI.md`, `docs/PREREG_GS.md`, `docs/CI_REAUDIT.md`.
- Khong tra loi cau leak `f0..f39`.
- Khong bootstrap maxDD, khong bootstrap underwater-days.
- Khong hua rang ket qua se phan biet duoc. Xem section 0.1.
