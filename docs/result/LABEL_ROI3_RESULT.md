# LABEL_ROI3 — CI cho phep so nhan, VA MOT CONFOUND LAM PHEP SO DO VO DUNG

Chay 2026-09-04, `research/analysis/lab3_label_ci.py`, log `/home/ubuntu/cov/LAB3.out`.
970 lenh C2b, join 100%. Block-bootstrap **ghep cap** khoi 72h, 2000 rep, seed 20260904.
**MO TA.** Bo sung cai `LABEL_ROI2` thieu: **chi co diem uoc luong, khong co CI**.

⚠️ `khoi 72h: 299 tong nhung chi **89 CO du lieu**`, ~10.9 lenh/khoi.

## 1. CI cua tung nhan

| nhan | rho vs ROI that | CI95 | sd |
|---|---|---|---|
| `g1lite_72h` (C2b) | +0.474 | [+0.398, +0.553] | 0.040 |
| `maxFav_72h` | +0.472 | [+0.396, +0.550] | 0.039 |
| `pathq_72h` | +0.452 | [+0.374, +0.529] | 0.040 |
| `g1lite_24h` | +0.396 | [+0.326, +0.467] | 0.037 |
| `retEnd_72h` | +0.373 | [+0.299, +0.451] | 0.039 |
| `g1lite_4h` | +0.258 | [+0.195, +0.323] | 0.033 |
| `hit6_4h` (G015) | +0.175 | [+0.100, +0.239] | 0.034 |

## 2. CI cua HIEU (ghep cap)

| phep so | d | CI95 | verdict |
|---|---|---|---|
| **CHAN TROI** 72h − 4h | **+0.215** | [+0.148, +0.282] | **LOAI TRU 0** |
| **CHAN TROI** 24h − 4h | **+0.137** | [+0.084, +0.189] | **LOAI TRU 0** |
| **CHAN TROI** 72h − 24h | **+0.078** | [+0.040, +0.116] | **LOAI TRU 0** |
| C2b − `hit6_4h`(G015) | **+0.299** | [+0.223, +0.376] | **LOAI TRU 0** |
| 72h − `retEnd_72h` | +0.102 | [+0.052, +0.155] | LOAI TRU 0 |
| **CONG THUC** `g1lite` − `pathq` (cung 72h) | +0.023 | [-0.008, +0.057] | **chua 0** |
| **CONG THUC** `g1lite` − `maxFav` (cung 72h) | **+0.003** | [-0.005, +0.011] | **chua 0** |

⇒ Ve mat thong ke: **khac biet CHAN TROI phan biet duoc** (ca 3 buoc loai tru 0);
**khac biet CONG THUC thi KHONG** (+0.003 va +0.023, ca hai chua 0).

## 3. 🔴 NHUNG PHEP SO CHAN TROI BI CONFOUND — khong dung de ket luan duoc

ROI cua mot lenh hien thuc hoa trong **toi 168h** (trailing arm 7%, hoac time-stop 7 ngay —
`C2B_SPEC §5.1`). Nhan `maxFav_72h` **quan sat 72h cua CHINH duong gia do**; `maxFav_4h` chi
quan sat **4h dau**. Nen nhan chan troi dai **co hoc** chia se nhieu hon voi ROI —
day la **CHONG LAN CUA SO**, gan nhu tautology, **khong phai** "muc tieu du bao tot hon".

Mau don dieu 4h -> 24h -> 72h **chinh la thu ma chong lan thuan se tao ra**. Phep do nay
**khong phan biet duoc** hai cach giai thich:
(a) chan troi 72h la muc tieu tot hon that; (b) chan troi 72h chi don gian **nhin thay nhieu hon**
cua cung ket qua.

⇒ **RUT ket luan cua `LABEL_ROI2` muc 2** ("chan troi dai hon TOT HON, don dieu va lon").
Phat bieu con dung duoc: *"tuong quan voi ROI tang don dieu theo chan troi, va phan lon/toan bo
co the do chong lan cua so — phep do nay khong ket luan duoc nhan nao tot hon lam MUC TIEU TRAIN."*

Phan **KHONG** bi confound (va van dung): **so CONG THUC o cung chan troi 72h** — o day chong lan
la nhu nhau cho moi nhan. Ket qua: `g1lite` / `maxFav_72h` / `pathq_72h` **khong phan biet duoc
nhau**; chi `retEnd_72h` kem ro (+0.102, loai tru 0).
⇒ **Cong thuc khong quan trong; ho `maxFav` > `retEnd`.** Ket luan nay sach.

## 4. VA PHEP SO THAT SU CAN THI KHONG TON TAI

Cau hoi dung la: **train S1 tren nhan 4h so voi tren nhan 72h thi selector nao tot hon tren
full DEV?** Do:

- `SELECTOR_FEATURES §B.2`: moi the he da tung train deu o **72h** — V2 (`maxFav_72h>=0.06`),
  V3 (`maxFav_72h/vol_7d`), S1 (`rel5` tu `g1lite` **72h**). Cac nhanh `s1b*`/`s1a4` doi
  **pool/feature**, khong doi chan troi.
- ⇒ **CHUA BAO GIO co S1 train tren nhan 4h.** Phep so "full DEV giua 2 chan troi" **khong ton tai**.
- Va **khong the dung "G015 vs S1"** lam thay the: hai cai do khac nhau **BON** thu cung luc —
  chan troi (4h vs 72h), nhan (nhi phan vs ngu phan vi trong tick), thuat toan (classifier vs
  ranker), feature (45 vs 9). Khong tach duoc phan nao do chan troi.

## 5. Muon lam cho dung thi phai the nao

Train hai bien the S1 **chi khac chan troi cua nhan** (moi thu con lai y nguyen: 9 feature,
`rank:ndcg`, 10 fold, purge 72h, seed 42, CPU), roi cham tren **full DEV** bang mot tieu chi
**KHONG phai nhan nao trong hai** — neu khong lai roi vao chinh confound §3. Ung vien tieu chi:
`pathq_72h`, hoac ROI that cua sim (nhung moi bien the sinh tap lenh khac nhau nen khong ghep cap
sach), cong **1 run java** cho rang buoc cung `maxDD >= -15.12%`.
⚠️ Phai **PRE-REG** truoc (day la phep so MODEL, khong con la mo ta), va phai chot truoc cach xu ly
viec "hai bien the sinh hai tap lenh khac nhau".
⚠️ Va nho `COV_RESULT`: tap thua nhu the nay (**89 khoi co du lieu**) co the **duoi phu** =>
CI o §1-§2 rat co the **hep hon that**. Chua kiem phu cho chuoi cap-lenh nay.
