# B4_RESULT — ket qua mo lai nhanh B4 (rolling-percentile gate)

Ngay: 2026-09-03. Pham vi: **CHI DEV** (2022-01-01..2024-06-29, 911 ngay). Khong cham VALIDATION,
khong cham HOLDOUT 2026. Khong rebuild bins, khong dung duong OI moi.

Phuong phap **chot TRUOC** o `docs/PREREG_B4.md`, commit **`a0c7ad6`** (2026-09-03T21:17:50+07:00).
Run dau tien bat dau **21:18** (dataset `wfo_ds_b4off`, log `build_C2b`/`sim.out` cua `B4_OFF`
21:21..21:25) => thu tu **pre-reg TRUOC run** dung.
CI/bootstrap: `research/analysis/ci_b4.py` (khuon `ci_group_a.py`, `docs/PREREG_CI.md`).
Tang tung lenh: `research/analysis/paired_test.py` (`docs/PREREG_PAIRED.md`).

---

## 1. CONG NGHIEM THU (PREREG_B4 muc 6): **PASS**

Chay lai C2b bang **code da cai lai rolling gate**, voi gate **TAT** (profile `c2b.properties`,
khong khai bao `SIM_GATE_ROLLING_*`), qua ban chuan `tools/run_c2b_dev.sh`:

```
cmp -s <(tail -n +2 /home/ubuntu/java/devrun/B4_OFF/storage/printDone.csv) \
       <(tail -n +2 /home/ubuntu/java/devrun/C2b/storage/printDone.csv)     # rc=0
```

| kiem | ket qua |
|---|---|
| `cmp` bo dong header | **rc=0 — BYTE-IDENTICAL** |
| md5 `printDone.csv` | `8f7afdfb27b15f5b6d4c886700def93c` (B4_OFF) = `8f7afdfb27b15f5b6d4c886700def93c` (C2b) |
| so lenh | 970 / 970 (971 dong ke header) |
| equity cuoi | **`b:60390`** (dung moc baseline) |
| chuoi equity NGAY | giong het C2b tung ngay (`ci_b4.py` muc 0: `True`) |
| `TICKER_SOURCE` | `aerospike` (Oracle), `EXCHANGE_INFO_PATH=exchange_info_pin.json` |
| dong `GATE-ROLL` trong log B4_OFF | **0 dong** (co that su TAT, khong am tham bat) |
| `tools/check_cfg_gateway.sh` | OK — khong tham so nao lach cong `Cfg` |
| `System.out/err/printStackTrace` trong file moi | khong co (SLF4J) |

=> Code sua **khong lam lech thu khac**. Moi so duoi day dung duoc.

## 1.1 Do trung khop voi lan chay CU (truoc refactor) — kiem chung bo sung

Co che cai lai tra ve **dung** cac so cua lan chay 2026-09-03 truoc `5f40a90`:

| run | equity moi | equity cu | so lenh moi/cu | bang nguong (moc gio, min, max) moi = cu |
|---|---|---|---|---|
| B4_RG95 | **56683** | 56683 | 1007 / 1007 | 39510 moc, min 0.00494, max 0.01450 — **khop** |
| B4_RG97 | **52045** | 52045 | 808 / 808 | 39510 moc, min 0.00539, max 0.01744 — **khop** |
| B4_RG95W180 | **59120** | 59120 | 1034 / 1034 | 37350 moc, min 0.00549, max 0.01207 — **khop** |

`nBeforeFirst = 0` cho ca 3 (khong co dong WARN "truy van truoc moc dau tien"): moc gio dau tien la
`1624989600000` (2021-06-30, W=90) va `1632765600000` (2021-09-28, W=180), deu **truoc** 2022-01-01
=> vung dau ky **khong** roi vao DEV, dung nhu du bao ghi truoc o PREREG_B4 muc 1.2.5.

---

## 2. BANG 3 BIEN THE — tieu chi CHINH va RANG BUOC CUNG

`d = CAGR(bien the) - CAGR(C2b)`, pp/nam. `sd_boot` = block-bootstrap **ghep cap**, block **21
ngay**, 2000 rep, seed 20260903. Nguong DAT (PREREG_B4 muc 3): `d > 1.4823 * sd_boot`
(`1.4823 = sqrt(2 ln 3)`, hieu chinh so sanh boi cho 3 bien the).
Rang buoc cung (muc 4): `maxDD >= -15.12%`, quan sat, **khong** bootstrap.

| run | equity | CAGR | maxDD | underwater | d (pp) | CI95 d (block 21) | sd_boot | nguong | tieu chi chinh | rang buoc cung |
|---|---|---|---|---|---|---|---|---|---|---|
| **C2b** (neo) | 60390 | +24.43% | **-13.12%** | 93 ngay | — | — | — | — | — | DAT |
| **B4_RG95** (p .95 / 90d) | 56683 | +21.31% | **-12.88%** | 99 ngay | **-3.118** | [-8.404, +2.488] | 2.705 | +4.010 | **KHONG DAT** | **DAT** |
| **B4_RG97** (p .97 / 90d) | 52045 | +17.23% | **-12.33%** | 147 ngay | **-7.197** | [-14.764, +0.288] | 3.771 | +5.589 | **KHONG DAT** | **DAT** |
| **B4_RG95W180** (p .95 / 180d) | 59120 | +23.37% | **-13.12%** | 187 ngay | **-1.055** | [-7.338, +4.795] | 3.018 | +4.474 | **KHONG DAT** | **DAT** |

Do ben theo do dai block (block 21 la CHINH; hai cot con lai chi de xem ket luan co phu thuoc
do dai block hay khong):

| run | CI95 block 21 | CI95 block 10 | CI95 block 42 | loai tru 0 | phan loai PREREG_CI muc 4 |
|---|---|---|---|---|---|
| B4_RG95 | [-8.404, +2.488] | [-8.273, +1.438] | [-8.841, +3.059] | `nnn` | KHONG PHAN BIET DUOC |
| B4_RG97 | [-14.764, +0.288] | [-14.643, **-0.381**] | [-16.169, +0.819] | `nYn` | KHONG PHAN BIET DUOC |
| B4_RG95W180 | [-7.338, +4.795] | [-6.507, +4.098] | [-7.392, +5.399] | `nnn` | KHONG PHAN BIET DUOC |

Ba dieu can doc dung o bang tren:
1. **Ca 3 bien the deu DAT rang buoc cung maxDD**, va **ca 3 deu co maxDD KHONG te hon C2b**
   (-12.88 / -12.33 / -13.12 vs -13.12). Day la phan cua `CI_REAUDIT` duoc **tai lap**.
2. **Khong bien the nao dat tieu chi chinh.** Hon nua ca 3 diem uoc luong deu **AM** (RG thap hon
   C2b), tuc khong co bien the nao du "di dung huong" de noi den chuyen vuot nguong.
3. `d` cua ca 3 **nam trong CI** o do dai block chinh => tang equity DEV **khong phan biet duoc**
   RG voi C2b, dung nhu du bao ghi truoc o PREREG_B4 muc 0.1 (`sd` ~2.7-3.8pp cho 3 cap nay,
   `sd` chung cho thay doi kieu gate 6.34pp).

`underwater` dai hon (99 / 147 / 187 ngay vs 93) la **so quan sat**, khong co CI, va **khong** thuoc
tieu chi nao da chot => chi ghi lai, khong dung de phan quyet.

---

## 3. TANG TUNG LENH (`paired_test.py`) — do BO SUNG, khong phai tieu chi chinh cua B4

Tieu chi chinh cua B4 da chot o tang equity (muc 3 cua pre-reg). Muc nay them vao vi de bai yeu cau
cham bang `paired_test.py`, va vi `CI_REAUDIT` HE QUA (iii) muc 3 khuyen do o tang thap hon.
Dai luong CHINH `roisum` (`sum(pnl/margin)` theo khoi), khoi **72h**, `d = RG - C2b`:

| cap | d (roisum, khoi 72h) | CI95 | loai tru 0 (24/72/168) | phan quyet script | huong |
|---|---|---|---|---|---|
| B4_RG95 vs C2b | -0.01136 | [-0.02767, +0.00550] | `nnn` | KHONG PHAN BIET DUOC | — |
| **B4_RG97 vs C2b** | **-0.02998** | **[-0.05019, -0.01042]** | **`YYY`** | phan biet duoc | **C2b HON RG97** |
| B4_RG95W180 vs C2b | -0.00307 | [-0.01777, +0.01855] | `nnn` | KHONG PHAN BIET DUOC | — |

Bon dai luong cua RG97 (`roisum`, `roimean`, `pnlsum`, `roisum_gross`) **deu** `YYY` va **deu am**;
`roisum` va `pnlsum` vuot ca nguong bao thu `2.35*sd` ma script tu ap (`p = 0.002`/`0.003` bootstrap
2 phia). Voi RG95, `roimean` la `YYY` am (`p = 0.023`) nhung `roisum` — dai luong CHINH — thi khong.

=> Tang tung lenh **khong** cuu duoc RG. No lam dieu nguoc lai: voi RG97 no **phan biet duoc**, va
huong la **RG97 kem hon C2b**. Muc nay **khong** duoc dung de doi phan quyet (tieu chi chinh la
tang equity, da chot truoc); no chi cho thay ket luan "dong nhanh" khong dua tren mot phep do duy
nhat het hoi.

---

## 4. TIEU CHI PHU theo CHE DO (PREREG_B4 muc 5) — cat theo NGAY, chot TRUOC

Ly do ton tai cua rolling gate la **thich nghi drift/che do thi truong**. Phep cat da chot truoc:
**BEAR = 2022-01-01..2022-12-31** va **HOI PHUC = 2023-01-01..2023-12-31** (365 ngay moi doan,
`n_eff` = 18 khoi 21 ngay moi doan). `d` va CI tinh **rieng trong tung doan**, cung seed 20260903.

**Doan BEAR 2022:**

| run | CAGR doan | maxDD doan | d (pp) | CI95 (block 21) | P(d>0) |
|---|---|---|---|---|---|
| C2b | +11.64% | -13.12% | — | — | — |
| B4_RG95 | +5.44% | -12.88% | -6.197 | [-14.881, +0.280] | 0.033 |
| B4_RG97 | +0.28% | -12.33% | -11.357 | [-26.739, **-0.533**] | 0.021 |
| B4_RG95W180 | +4.50% | -13.12% | -7.134 | [-17.849, +1.110] | 0.050 |

**Doan HOI PHUC 2023:**

| run | CAGR doan | maxDD doan | d (pp) | CI95 (block 21) | P(d>0) |
|---|---|---|---|---|---|
| C2b | +45.45% | -1.89% | — | — | — |
| B4_RG95 | +47.52% | -3.53% | +2.075 | [-8.734, +14.658] | 0.653 |
| B4_RG97 | +44.68% | -3.52% | -0.768 | [-13.377, +13.278] | 0.468 |
| B4_RG95W180 | +49.02% | -3.64% | +3.570 | [-8.316, +16.261] | 0.747 |

Doc dung:
- Trong **HOI PHUC 2023**, hai bien the p=0.95 co diem uoc luong **duong** (+2.1 / +3.6pp) — dung
  huong ma gia thuyet "thich nghi che do" du bao, nhung CI **rat rong** va chua 0 (nhu da du bao
  truoc: `n_eff` = 18 khoi).
- Trong **BEAR 2022** thi ca 3 deu **am**, va cai am nhieu nhat (RG97, -11.36pp) co CI **loai tru 0**.
  Tuc gia thuyet "nguong truot giup o che do xau" **khong** duoc du lieu ung ho; neu co gi thi
  huong la **nguoc lai**.
- **Rang buoc da chot: day la tieu chi PHU.** No **khong** duoc dung de tuyen bo thang (va o day
  cung khong co gi de tuyen bo). Khong them phep cat nao sau khi thay so — khong quy, khong thang,
  khong regime khac.

---

## 5. PHAN QUYET — cach doc **(b)** cua PREREG_B4 muc 7

> Ca **3/3** bien the DAT rang buoc cung maxDD. **0/3** bien the vuot nguong `1.48 * sd_boot`.

=> **CACH DOC (b): KHONG PHAN BIET DUOC bang du lieu DEV hien co. DONG nhanh B4.**

Phat bieu dung, dung nguyen van tu day tro di:

> *Rolling-percentile gate (phan vi 0.95/0.97, cua so 90/180 ngay, cap nhat moi gio) **khong lam
> te hon** rang buoc rui ro cua du an — maxDD ca 3 bien the (-12.88 / -12.33 / -13.12) khong xau
> hon C2b (-13.12). Nhung DEV **khong the phan biet** no voi C2b o tang equity: hieu CAGR
> -3.12 / -7.20 / -1.06pp voi `sd_boot` 2.7-3.8pp, CI95 chua 0 o do dai block chinh. Ca 3 diem
> uoc luong deu am, tuc khong co bien the nao dang tien ve phia "hon C2b". O tang tung lenh,
> RG97 **phan biet duoc va kem hon** C2b. Nhanh dong vi **khong co co so dat cuoc vao no**, KHONG
> phai vi da chung minh duoc no thua.*

**Nhung gi phai SUA trong `docs/AUDIT_APPLIED.md` muc B4** (de nghi, chua sua trong commit nay vi
ngoai pham vi bai):
- Cau **"EV am tren nen C2b"** phai **RUT**. No la ket luan tu do chinh xac gia. Cai do duoc la
  "hieu nam trong nhieu", va rieng RG97 thi tang tung lenh do duoc la kem hon.
- Cau **"ca 3 thua C2b 60390"** phai doi thanh **"ca 3 khong phan biet duoc voi C2b o tang equity;
  maxDD ca 3 khong te hon C2b"**.
- Ghi ro ly do dong moi: **khong phan biet duoc + khong co dau hieu di dung huong**, chu khong phai
  "thua".

**KHONG lam** (theo dung cach doc (b)):
- **KHONG re-baseline.** C2b van la neo: b:60390 / CAGR +24.43 / maxDD -13.12.
- **KHONG** doi baseline sang bat ky RG nao (ke ca RG95w180, cai gan C2b nhat).
- **KHONG** mo them bien the tren cung khong gian (noi cua so, doi phan vi, doi tan so cap nhat...).
  Da dung dung 3/3 quota. Them bien the = chon tren nhieu = leak L2.
- **KHONG** cham VALIDATION / HOLDOUT de "xac nhan them". Tieu chi chinh khong dat => khong co gi
  de xac nhan.

## 5.1 Cau tra loi cho cau hoi "vay bao nhieu du lieu moi phan biet duoc?"

`sd_boot` do duoc o day (2.705 / 3.771 / 3.018 pp) khop khoang `sd` cua nhom "noi gate" trong
`CI_REAUDIT` (6.34pp la cap C2b-H1a; cac cap RG hep hon vi RG chi doi nguong co so, khong doi
duong logic). Voi `sd = 3.0pp` va delta = 3pp o cong suat 80%: can `911 * (3.0/1.071)^2 = 7146`
ngay = **~19.6 nam**. Voi delta = 1pp: **~176 nam**. DEV co 2.496 nam. Ket luan cua
`CI_REAUDIT` HE QUA (iii) — "khong the dat duoc bang cach cho them du lieu" — **duoc cung co**,
khong bi bac.

---

## 6. Trang thai code sau bai nay — can quyet dinh cua chu du an

Bai nay **them lai** `GateRollingThreshold.java` (149 dong, commit `c1785b9`) + 2 diem goi `init` +
3 profile `profiles/b4_rg*.properties`. Voi cau hinh dang chay (`c2b.properties` khong khai bao
`SIM_GATE_ROLLING_*`) co che nay **TRO** va da chung minh byte-identical (muc 1).

Nguyen tac DOT 2 (`5f40a90`) la **khong de co tro trong cay** — do la ly do file nay tung bi xoa.
Nhanh B4 gio dong lai => co nay lai la co tro. Hai duong deu hop ly va **quyet dinh la cua chu
du an**, toi khong quyet thay:
- **Giu**: doi lai ~144 dong tro; loi la lan sau khong phai khao co git de tai lap (chi phi do
  chinh la thu lam bai nay dat).
- **Xoa lai** (`git revert c1785b9`, giu lai `docs/PREREG_B4.md` +
  `docs/B4_RESULT.md` + `research/analysis/ci_b4.py`): giu cay sach dung nguyen tac DOT 2. Ban ghi
  va cach tai lap van con nguyen trong hai doc nay.

Neu **giu**, phai giu kem: 3 profile `b4_rg*` **khong** duoc dung lam baseline, va `c2b.properties`
**khong** duoc them `SIM_GATE_ROLLING_*` (them vao la doi neo, vi pham cach doc (b)).

---

## 7. NHUNG GI BAO CAO NAY **KHONG** LAM / **KHONG** NOI

- **Khong** noi RG "thua". Noi "khong phan biet duoc o tang equity" (va rieng RG97 kem hon o tang
  tung lenh).
- **Khong** noi C2b "tot hon". Cach doc (b) cam ket luan do.
- **Khong** doi diem uoc luong nao cua C2b, khong doi neo, khong sua `PREREG_CI` / `PREREG_GS` /
  `CI_REAUDIT`.
- **Khong** bootstrap maxDD hay underwater (`PREREG_CI` muc 2.5).
- **Khong** cham VALIDATION (2024-07-15..2025-12-31) hay HOLDOUT 2026; khong rebuild bins; khong
  cham `/home/ubuntu/predwf_map_s1a2/`, `/home/ubuntu/gs/`, `/home/ubuntu/oifix/`,
  `/home/ubuntu/oiprobe/`; khong submit kernel Kaggle; khong sua kill-switch.
- Dataset tam (`wfo_ds_b4off`, `wfo_ds_b4rg`) da **xoa** sau khi chay; khong con JVM nao.
- Luu y ve tac dung phu: `paired_test.py` ghi de
  `/home/ubuntu/paired/paired_out.json` (duong dan hardcode trong script). File do la ket qua
  hieu chuan cu cua `PAIRED_CALIB.md`; ban ghi trong doc do khong bi anh huong, nhung neu can lai
  json cu thi phai chay lai `paired_test.py` voi cac cap cu.

## 8. Tai lap

```
git show a0c7ad6:docs/PREREG_B4.md            # pre-reg, chot truoc
tools/run_c2b_dev.sh profiles/c2b.properties B4_OFF /home/ubuntu/wfo_ds_b4off \
                     /home/ubuntu/java/devrun/C2b        # cong nghiem thu
# 3 bien the: profiles/b4_rg95.properties, b4_rg97.properties, b4_rg95w180.properties
#   env WFO_DATA_DIR=<ds> WFO_SMART_CACHE=1 SIM_END_DATE=20240630 TRADING_PROFILE=<profile>
python3 research/analysis/ci_b4.py                        # muc 2 + 4
python3 research/analysis/paired_test.py B4_RG95 C2b B4_RG97 C2b B4_RG95W180 C2b   # muc 3
python3 /home/ubuntu/java/fsrun/qret.py C2b B4_RG95 B4_RG97 B4_RG95W180
```
