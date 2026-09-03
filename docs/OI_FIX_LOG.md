# OI_FIX_LOG — job "sua leak moc create_time": ket qua la KHONG SUA DU LIEU

Ngay: 2026-09-03. Script do: `/home/ubuntu/oifix/{v1,v3,v5,v6,v8,v9,v10}.py`, log `.log` cung ten,
ket qua JSON `v1.json v3.json v5.json v6.json v9.json v10.json`.
Bang: `/home/ubuntu/oifix/{pooled_table,persym_table,sharp_table,accept_detail}.md`.

Job nay duoc giao voi tien de "file OI bi nhiem 71.30% dong / 100% VALIDATION, hay ap phep dich
`+5m`". Yeu cau kem theo la **tu xac minh lai tung menh de bang du lieu**. Da xac minh. Ket qua:
tien de ve *nguon* dung, tien de ve *file trien khai* **SAI**. Do do khong ap phep dich.

---

## KET LUAN (6 dong)

1. **Moc doi nghia `create_time` la THAT.** Xac minh doc lap (khong dung lai so cua
   `OI_SCOPE_REPORT`): 15/15 symbol, 3 giai doan (2024-02, 2024-03, 2025-06), n = 64,800 cap
   moi o pooled. Truoc moc nhan = CUOI cua so; tu 2024-03-04 nhan = DAU cua so. Bien do phan
   biet 10x (gia ngam) den 1000x (ty le taker).
2. **File OI dang trien khai `/home/ubuntu/claudedata/oi/oi_percoin_full.bin` DA NHAN QUA SAN,
   KHONG bi ro ri.** Do TRUC TIEP tren chinh file (khong suy dien tu cot `ts`): 12 symbol x 12
   ngay + 150 symbol x 3 ngay = ~486 mau symbol-ngay trai 2021-03 .. 2026-05, gom mau
   VALIDATION va mau 2026. `taker_buy` cua file khop cua so **[t-5m, t)** o **450/450** mau;
   `ls_global` cua file bang gia tri Vision cua nhan **t-5m** (= trang thai tai `t`) o 444/450.
3. => **KHONG ap `+5m` len file, KHONG tao file moi.** Ap vao du lieu da dung se bien no thanh
   du lieu **tre 5 phut**, va con lam **hong** nhung symbol van dung quy uoc cu.
4. **Quy tac A (dich `+5m` cho MOI ban ghi `create_time >= 2024-03-04`) SAI mot phan.** Do duoc
   **6/176 symbol (3.4%)** tai 2024-03-05 va **2/281** tai 2026-05-15 **van dung quy uoc CU**
   sau moc (CTKUSDT, CVXUSDT, LITUSDT, SXPUSDT, MAVIAUSDT, AERGOUSDT, BDXNUSDT...). Moc
   2024-03-04 **khong phai moc toan cuc** — no la moc cua **da so** symbol.
5. **Cai that su sai la CODE, khong phai du lieu.** `VisionMetricsClient.parseDay:248` lay
   `create_time` nguyen xi. Rebuild bang `ExportFundingOiPerCoin source=vision` voi code hien tai
   **se tao ra** leak (va rule A cung se lam hong 3.4% symbol). Patch de xuat o muc 5;
   **chua ap** vi job nay bi cam chay java/compile (mot agent khac dang dung slot java).
6. **Vi khong sua du lieu: KHONG phai train lai G015, khong doi nguong, moi so DEV/VAL/C2b giu
   nguyen.** Thu phai sua la **tai lieu**: `OI_SCOPE_REPORT.md` muc 2.1/2.2/CHUA-PHAN-GIAI-#3 va
   dinh chinh dau `FEAT40_LOOKAHEAD.md`.

---

## 1. Xac minh doc lap NGUON (data.binance.vision) — quy uoc co doi thuc

### 1.1 Hai phep do CHINH XAC (khong phai tuong quan), 15 symbol x 3 giai doan

- **gia ngam**: `col3/col2` = gia tai thoi diem snapshot; so voi `close` cua nen 5m.
- **ty le taker**: `col7` phai bang **chinh xac** `tb/(vol-tb)` cua nen 5m tuong ung.

`err` = sai so tuong doi trung vi. Bang day du: `/home/ubuntu/oifix/sharp_table.md`.
Trich (mau dai dien, don vi = sai so tuong doi):

| ky | symbol | implied err @t | implied err @t+5m | taker err win [t-5m,t) | taker err win [t,t+5m) |
|---|---|---|---|---|---|
| PRE 2024-02 | BTCUSDT | **3.3e-05** | 7.0e-04 | **2.6e-04** | 3.8e-01 |
| PRE 2024-02 | ETHUSDT | **4.5e-05** | 9.0e-04 | **1.9e-04** | 3.4e-01 |
| PRE 2024-02 | LTCUSDT | **6.4e-05** | 8.7e-04 | **4.2e-09** | 4.4e-01 |
| POST 2024-03 | BTCUSDT | 1.0e-03 | **4.3e-05** | 3.7e-01 | **4.6e-04** |
| POST 2024-03 | ETHUSDT | 1.2e-03 | **4.1e-05** | 3.1e-01 | **3.6e-04** |
| VAL 2025-06 | BTCUSDT | 5.5e-04 | **1.9e-05** | 4.2e-01 | **2.7e-04** |
| VAL 2025-06 | XRPUSDT | 9.2e-04 | **4.4e-05** | 3.9e-01 | **3.0e-04** |

**15/15 symbol o ca 3 giai doan** cho cung ket luan, khong mot ngoai le. Truoc moc nhan = cuoi
cua so (nhan qua); tu moc nhan = dau cua so (chua 5 phut tuong lai). Menh de goc **DUNG**.

### 1.2 Cong nghiem thu bat buoc — tuong quan voi nen 5m thuc, TRUOC/SAU khi ap quy tac

Phep do: voi cot snapshot dung `d(t) = x(t) - x(t-5m)`; voi cot flow (`col7`) dung `x(t)`.
`PRE` = tuong quan voi nen `[t-5m, t)`; `FOL` = voi nen `[t, t+5m)`. Dat khi `|PRE| > |FOL|`.
15 symbol, 15 ngay/giai doan (n = 4,320 cap/symbol; **n = 64,800 cap/o** khi pooled z-score).
Bang day du: `/home/ubuntu/oifix/pooled_table.md`, `persym_table.md`.

**POOLED (n=64,800 moi o) — 18/18 o DAT:**

| ky | cot | TRUOC PRE | TRUOC FOL | truoc | SAU PRE | SAU FOL | sau |
|---|---|---|---|---|---|---|---|
| PRE 2024-02 | sum_open_interest | +0.3298 | +0.0134 | PRE | +0.3298 | +0.0134 | **PRE** |
| PRE 2024-02 | sum_open_interest_value | +0.8296 | +0.0150 | PRE | +0.8296 | +0.0150 | **PRE** |
| PRE 2024-02 | count_toptrader_ls | -0.3352 | -0.0082 | PRE | -0.3352 | -0.0082 | **PRE** |
| PRE 2024-02 | sum_toptrader_ls | -0.0798 | -0.0208 | PRE | -0.0798 | -0.0208 | **PRE** |
| PRE 2024-02 | count_ls | -0.2899 | -0.0180 | PRE | -0.2899 | -0.0180 | **PRE** |
| PRE 2024-02 | sum_taker_ls_vol | +0.4169 | -0.0056 | PRE | +0.4169 | -0.0056 | **PRE** |
| POST 2024-03 | sum_open_interest | +0.0599 | +0.2772 | FOL | +0.2772 | -0.0188 | **PRE** |
| POST 2024-03 | sum_open_interest_value | +0.0338 | +0.8548 | FOL | +0.8548 | -0.0202 | **PRE** |
| POST 2024-03 | count_toptrader_ls | -0.1262 | -0.2956 | FOL | -0.2956 | +0.0020 | **PRE** |
| POST 2024-03 | sum_toptrader_ls | +0.0112 | -0.0860 | FOL | -0.0860 | +0.0111 | **PRE** |
| POST 2024-03 | count_ls | -0.1396 | -0.2340 | FOL | -0.2340 | -0.0129 | **PRE** |
| POST 2024-03 | sum_taker_ls_vol | +0.0056 | +0.4241 | FOL | +0.4241 | -0.0026 | **PRE** |
| VAL 2025-06 | sum_open_interest | +0.0314 | +0.1528 | FOL | +0.1528 | -0.0196 | **PRE** |
| VAL 2025-06 | sum_open_interest_value | -0.0017 | +0.8081 | FOL | +0.8081 | -0.0374 | **PRE** |
| VAL 2025-06 | count_toptrader_ls | -0.0408 | -0.1676 | FOL | -0.1676 | -0.0149 | **PRE** |
| VAL 2025-06 | sum_toptrader_ls | -0.0119 | +0.1064 | FOL | +0.1064 | -0.0145 | **PRE** |
| VAL 2025-06 | count_ls | +0.0008 | -0.0879 | FOL | -0.0879 | -0.0360 | **PRE** |
| VAL 2025-06 | sum_taker_ls_vol | +0.0286 | +0.4336 | FOL | +0.4336 | -0.0044 | **PRE** |

Phep kiem **co hieu luc**: cot "truoc" cho PRE o giai doan PRE (6/6) va cho FOL o ca hai giai doan
sau moc (12/12). Sau khi ap quy tac: **18/18 = PRE**. Quy tac dich `+5m` la **DUNG HUONG va DUNG
DO LON** (dich 10m se lam `|PRE|` roi ve muc nhieu, kiem duoc qua cot "SAU FOL" ~0.00-0.04).

**PER-SYMBOL (n=4,320/symbol) — so symbol DAT `|PRE|>|FOL|`:**

| ky | cot | n sym | truoc DAT | sau DAT |
|---|---|---|---|---|
| PRE 2024-02 | sum_open_interest | 15 | 14 | 14 |
| PRE 2024-02 | sum_open_interest_value | 15 | 15 | 15 |
| PRE 2024-02 | count_toptrader_ls | 15 | 14 | 14 |
| PRE 2024-02 | sum_toptrader_ls | 15 | 14 | 14 |
| PRE 2024-02 | count_ls | 15 | 15 | 15 |
| PRE 2024-02 | sum_taker_ls_vol | 15 | 15 | 15 |
| POST 2024-03 | sum_open_interest | 15 | 0 | **15** |
| POST 2024-03 | sum_open_interest_value | 15 | 0 | **15** |
| POST 2024-03 | count_toptrader_ls | 15 | 2 | **15** |
| POST 2024-03 | sum_toptrader_ls | 15 | 6 | 11 |
| POST 2024-03 | count_ls | 15 | 1 | **15** |
| POST 2024-03 | sum_taker_ls_vol | 15 | 0 | **15** |
| VAL 2025-06 | sum_open_interest | 15 | 1 | **15** |
| VAL 2025-06 | sum_open_interest_value | 15 | 0 | **15** |
| VAL 2025-06 | count_toptrader_ls | 15 | 1 | **15** |
| VAL 2025-06 | sum_toptrader_ls | 15 | 4 | 14 |
| VAL 2025-06 | count_ls | 15 | 0 | 13 |
| VAL 2025-06 | sum_taker_ls_vol | 15 | 0 | **15** |

**Khong lap liem: 4/18 o KHONG dat 15/15 per-symbol** (`sum_toptrader_ls` 11/15 va 14/15,
`count_ls` 13/15 o VAL, `sum_open_interest`/`count_toptrader_ls` o giai doan PRE 14/15).
Ly do la **cong suat phep do**, khong phai quy tac sai, va co **nhom doi chung** chung minh dieu do:
giai doan PRE **khong bi dich, khong duoc dich**, ma per-symbol cung chi dat 14/15 o 3 cot.
`sd(r)` o n=4,320 la `1/sqrt(4320) = 0.0152`; `|corr|` pooled cua `sum_toptrader_ls` chi
0.080-0.106, tuc bien do that chi ~5 sd o muc pooled va nho hon nhieu o tung symbol don le.
Voi cot yeu do, phep do dut diem la phep do CHINH XAC muc 1.1 (15/15, bien do 10x-1000x), khong
phai tuong quan. Cot `sum_toptrader_ls` **khong** duoc feature nao dung (`OiMetricSets` col 5).

---

## 2. Do TRUC TIEP tren file OI trien khai — file DA NHAN QUA

`OI_SCOPE_REPORT` chi doc **cot `ts`** cua file va **suy ra** ty le nhiem 71.30% (muc CHUA PHAN
GIAI #3 tu ghi nhan la chua biet file duoc build tu `--vision` hay tu 226). Job nay doc **gia tri**
va giai duoc muc #3.

Cach do (khong phai tuong quan):
- `taker_buy` cua file = `r/(1+r)` nen **nghich dao duoc**: `r = tb/(1-tb)` = dung `col7`. So `r`
  voi `tb/(vol-tb)` **chinh xac** cua nen 5m -> biet ban ghi mo ta cua so nao.
- `ls_global` cua file la `col6` tho (`floorStale`, khong bien doi) -> so bang **dong nhat so hoc**
  voi `col6` cua Vision o nhan `t`, `t-5m`, `t+5m`.

**Bang (trich `v5.log`; `err` = sai so tuong doi trung vi; 288 ban ghi/o):**

| symbol | ngay | taker err win [t-5m,t) | taker err win [t,t+5m) | file vs vision(t) | file vs vision(t-5m) |
|---|---|---|---|---|---|
| BTCUSDT | 2021-03-15 | **6.9e-08** | 3.5e-01 | **2.3e-08** | 5.0e-03 |
| BTCUSDT | 2022-06-15 | **5.7e-08** | 2.9e-01 | **1.8e-08** | 9.7e-03 |
| BTCUSDT | 2024-02-26 | **2.7e-04** | 3.7e-01 | **2.2e-08** | 2.1e-03 |
| BTCUSDT | 2024-03-05 | **1.3e-03** | 2.8e-01 | 4.7e-03 | **2.3e-08** |
| BTCUSDT | 2024-07-20 | **1.3e-04** | 5.2e-01 | 1.4e-03 | **1.6e-08** |
| BTCUSDT | 2025-06-11 | **2.3e-04** | 4.5e-01 | 1.3e-03 | **2.8e-08** |
| BTCUSDT | 2026-05-15 | **1.5e-04** | 3.6e-01 | 1.2e-03 | **2.3e-08** |
| ETHUSDT | 2025-06-11 | **3.9e-04** | 3.8e-01 | 2.6e-03 | **2.5e-08** |
| SOLUSDT | 2026-05-15 | **1.8e-04** | 4.4e-01 | 1.3e-03 | **2.7e-08** |
| TRXUSDT | 2026-05-15 | **6.5e-05** | 6.5e-01 | 1.4e-03 | **2.4e-08** |

Doc bang: **truoc** moc, file = Vision o nhan `t` (Vision khi do nhan qua) => file nhan qua.
**Sau** moc, file = Vision o nhan `t-5m` (= trang thai tai `t`) => file **da duoc dich `+5m` san**
=> van nhan qua. Ca hai phia, `taker_buy` cua file luon khop cua so **da dong** `[t-5m, t)` voi
bien do 1,000x - 4,000x. **Khong co ban ghi nao mo ta cua so tuong lai.**

**Kiem rong (`v6.log`, 150 symbol dong nhat moi ngay):**

| ngay | n symbol | ls_global khop vision(t-5m) (dung) | khop vision(t) | taker nhan qua | taker ro ri |
|---|---|---|---|---|---|
| 2024-03-05 | 150 | 147 | 3 | **150** | **0** |
| 2025-06-11 | 150 | 148 | 2 | **150** | **0** |
| 2026-05-15 | 150 | 149 | 1 | **150** | **0** |

6 truong hop "khop vision(t)" **khong phai ro ri** — do la symbol van dung quy uoc CU (muc 4).

### 2.1 Dau vet cau truc tai diem noi — xac nhan phep dich DA duoc ap khi build file

Quet toan file (`v6.log`), cua so 2024-03-03 22:00 .. 2024-03-04 02:00, **259 symbol co du lieu**:

- **ts trung lap = 0** (259/259).
- **so symbol co ts = 2024-03-04 00:00:00 = 0** (259/259 **thieu** moc nay).
- Khoang cach bat thuong duy nhat: dung **mot** buoc `600000 ms` (23:55 -> 00:05) o moi symbol.

Do la **dau vet vat ly** cua viec dich `+5m` co dieu kien: cua so `[23:55, 00:00)` bien mat va
moc `00:00` khong ton tai. Neu file khong duoc dich thi phai co ts 00:00 va khong co buoc 10 phut.
Ket hop voi muc 2: **file da duoc build voi phep dich dung** (bo phat hanh Kaggle
`chuyendinh/funding-oi-percoin`, `claudedata/oi/oi_dl.log`). Code trong repo **khong** chua phep
dich nao (`grep -rn 1709510400000` = 0 dong; khong co hang so `2024-03-04` trong `src`), nen ban
build Kaggle **khong dung** duong code hien tai cua repo.

Kiem thuoc tinh khac cua file: `ts % 300000 != 0` -> **0 dong / 140,924,110** (dung luoi 5m).

### 2.2 Duong LIVE / forward (REST API) — xac minh lai, khop bao cao goc

Do 2026-09-03, 3 symbol, `limit=500`:

| endpoint | quy uoc nhan | bang chung |
|---|---|---|
| `openInterestHist` | **NHAN QUA** (nhan = dung thoi diem snapshot) | gia ngam khop `close` tai `t`: err **2.0e-05 / 2.7e-05 / 2.6e-05**; tai `t+5m`: 6.5e-04 / 8.0e-04 |
| `takerlongshortRatio` | **DAU cua so** (giong Vision-moi) | err win `[t,t+5m)` **1.1e-04 / 9.1e-05**; win `[t-5m,t)` 4.8e-01 / 4.1e-01 |

=> menh de "snapshot API khong can dich, taker API can dich `+5m`" **DUNG**. Sau khi da xac nhan
history nhan qua, forward `takerlongshortRatio` van **can** dich `+5m` neu duong forward duoc bat.

Do sau lich su API (quan trong cho Viec 2): `limit` toi da 500 diem 5m = **~41.6 gio**; goi kem
`startTime/endTime` cach 400 ngay -> **HTTP 400** o ca 5 endpoint. => **REST API khong dung duoc
de keo dai lich su OI/LS/taker**; chi Vision co lich su.

---

## 3. QUYET DINH: khong sua du lieu. File giu nguyen.

| muc | gia tri |
|---|---|
| file OI dang dung (KHONG doi) | `/home/ubuntu/claudedata/oi/oi_percoin_full.bin` |
| kich thuoc | 4,227,723,300 byte = 140,924,110 dong x 30 byte (`long ts`, `short symId`, 5 x `float`) |
| sha256 | `e3887f63097299655213f8382ca7e473e126ee4d7ddf69a39658942651b305ec` |
| file moi da tao | **KHONG CO** (`/home/ubuntu/oi_fixed/` khong duoc tao) |
| dia | 194G, con 19G truoc va sau job (khong ghi gi len dia du lieu) |

Ly do khong ghi: ap `+5m` len du lieu **da nhan qua** se (a) lam moi feature OI **tre 5 phut** so
voi thuc te — mat tin hieu, tao train/serve skew moi, va (b) **lam hong** ~3.4% symbol dang dung
quy uoc cu (dich chung sang tuong lai, tao leak MOI o cho dang sach). Do la lam xau di, khong
phai sua.

---

## 4. Moc 2024-03-04 KHONG phai moc toan cuc — 3.4% symbol van dung quy uoc cu

Phep do (`v10.py census`): voi tung `(symbol, ngay)`, xac dinh quy uoc bang phep do CHINH XAC
ty le taker (`col7` vs `tb/(vol-tb)` cua nen 5m). Nguong: `err` ben nay < `err` ben kia / 10.

| ngay | NEW | **OLD** | AMBIG | UNKNOWN (col7 rong) |
|---|---|---|---|---|
| 2024-03-05 | 170 | **6** | 0 | 0 |
| 2026-05-15 | 266 | **2** | 0 | 13 |

Symbol OLD do duoc: `CTKUSDT`, `CVXUSDT`, `LITUSDT`, `SXPUSDT`, `MAVIAUSDT` (2024-03-05);
`AERGOUSDT`, `BDXNUSDT` (2025-06 / 2026-05). Bang chung tung symbol, vi du CTKUSDT 2024-03-05:
`err_old = 8.0e-04` vs `err_new = 3.6e-01` (450x).

**Dau hieu nhan biet re:** file cua symbol OLD chay `00:05:00 .. 24:00:00` (moc dau tien cua ngay
o giay 300 sau nua dem), file NEW chay `00:00:00 .. 23:55:00`. Trong mau do, `grid_sec == 300`
la **du bao hoan hao** cho OLD (moi symbol OLD deu co, va moi symbol co deu la OLD). Nhung
**khong du**: 13 symbol o 2026-05-15 co file bat dau giua ngay (`grid_sec` 7800/8100) va `col7`
rong -> phep do taker cho UNKNOWN, phep do `grid_sec` cung khong ket luan duoc.

=> Vi vay quy tac sua **khong duoc** la "dich neu ts >= 2024-03-04". Phai la **do quy uoc theo
tung (symbol, ngay)**.

---

## 5. Patch code de xuat — CHUA AP (can slot java de compile)

Job nay bi cam chay java (mot agent khac dang dung slot). Mot sua doi java khong compile duoc se
lam hong build cua ho, nen khong sua. Duoi day la quy tac phai ap, kem cach kiem.

**Diem sua:** `VisionMetricsClient.parseDay` (`:236-260`), ngay sau `OiMetricSets.normalize5m(ts)`.

**Quy tac (thu tu uu tien, tinh 1 lan cho moi file daily = moi `(symbol, ngay)`):**

1. Tai nen 5m cung `(symbol, ngay)` (Vision `daily/klines/<SYM>/5m/`). Tinh
   `err_old = median | col7(t) / (tb(t-5m)/(vol(t-5m)-tb(t-5m))) - 1 |` va `err_new` voi nen `t`.
   Neu `err_new < err_old/10` => **NEW** => `ts += 5m` cho **ca 6 cot / toan ban ghi**.
   Neu `err_old < err_new/10` => **OLD** => khong dich.
2. Neu `col7` rong hoac ket qua AMBIG: dung phep gia ngam `col3/col2` vs `close` cua nen `t-5m`
   (OLD) hay nen `t` (NEW). Bien do do duoc 10x-20x — yeu hon nhung du dut diem.
3. Neu ca hai deu khong ket luan duoc: **de NaN** cho ngay do, ghi `LOG.warn`. **KHONG** doan
   theo ngay. Mot ngay NaN re hon mot ngay ro ri.

**Cam:** hardcode `ts >= 2024-03-04` roi dich tat ca. Da do la sai voi 3.4% symbol.

**Duong forward** (`OpenInterestIngestor2AerospikeNew.parseAll:214`): neu bat forward ingest thi
phai `+5m` **chi cho** endpoint `takerlongshortRatio`; 4 endpoint snapshot **khong** dich
(da xac minh muc 2.2).

**Kiem sau khi sua (chay lai duoc bang script co san):** `python3 /home/ubuntu/oifix/v3.py` phai
cho 18/18 o pooled = `PRE`; `v6.py` phai cho `taker_causal = 150/150` moi ngay va
`trung_lap = 0`. Neu file duoc rebuild, phai so sha256 va so hang so cua file moi voi file cu:
so dong phai giu nguyen theo tung symbol tru symbol OLD (khong duoc dich).

**Diem mu cua verify hien tai (giu nguyen ket luan bao cao goc):** `BackfillOiVerify:130` goi
`openInterestHist?...limit=30` (2.5h gan nhat) roi so `stored[ts]` vs `api[ts]` — 2.5h gan nhat la
dong do forward ghi, tuc so API voi API. Phai them mot phep so **dong Vision-backfill cu** voi
API, hoac phep do noi bo kieu muc 1.1 (khong can API, chi can nen kline).

---

## 6. PHAI DO LAI GI — danh sach that (ngan hon nhieu so du kien)

Vi **khong sua du lieu**, khong co gi trong day phai train lai hay do lai:

- G015 selector (`/home/ubuntu/sel_models_net015`, 28 artifact): **KHONG** phai train lai.
- `score_g015` -> `dyn_thr` -> nguong vao lenh C2b: **KHONG** doi.
- `docs/LEAK_L1_REPORT.md` rho 0.1675, `docs/CI_REAUDIT.md` #8/#9, `docs/PHASE1_DECISION_SURFACE.md`
  B5/B6, `docs/PREREG_CI.md`, `docs/PREREG_GS.md`, moi so DEV/VAL cua C2b: **KHONG** doi.
- ONNX live, gate model: **KHONG** phai convert lai.

Cai **phai** lam:

1. **Sua tai lieu** (bat buoc — dang ghi sai su that):
   - `docs/OI_SCOPE_REPORT.md`: muc 2.1 ("VALIDATION BI, 100%"), muc 2.2 (bang 71.30% dong bi
     dich), muc 2.3, va CHUA PHAN GIAI #3 (da phan giai: file build voi phep dich dung).
     Ket luan dong 3 ("ca 5 feature OI chua 5 phut tuong lai tren 100% VALIDATION") **SAI** ve
     *file trien khai*; dung ve *nguon Vision tho + code repo*.
   - `docs/FEAT40_LOOKAHEAD.md`: khoi DINH CHINH dau file (dang ghi "5/5 feature ro ri, 71.30%
     dong, 100% VALIDATION") phai sua thanh: nguon+code co van de, **du lieu trien khai thi khong**.
2. **Sua code** truoc **bat ky** lan rebuild file OI nao (muc 5). Rebuild bang code hien tai la
   duong duy nhat dua leak vao du lieu.
3. **Bat forward ingest** thi phai dich taker (muc 5).
4. Con lai chua phan giai (giu nguyen tu bao cao goc): diem noi backfill/forward **trong
   Aerospike 226/242** chua do (job nay chi do file `.bin` + Vision + REST, khong doc 226/242).
   File `.bin` khong bi, nhung 226/242 co the bi — can do rieng neu duong live duoc dung.
5. `col2` va `col5` bi dich nhung khong feature nao dung — neu sau nay them feature tu 2 cot nay
   thi phai ap cung quy tac muc 5.

## 7. Do phu cot theo thoi gian (anh huong ty le NaN, khong anh huong ket luan)

Trong 486 mau symbol-ngay doc tu file `.bin`, `nan = [0,0,0,0,0]` o tat ca mau cua 12 symbol lon
(2021-03 .. 2026-05). Rieng phia **nguon Vision**, 13/281 symbol o 2026-05-15 co `col7` rong.
Bao cao goc ghi `col7` rong o 2022-01-15 / 2022-04-15 va `col4/col5` rong o 2022-08-10 — job nay
khong do lai muc do phu do mot cach he thong.
