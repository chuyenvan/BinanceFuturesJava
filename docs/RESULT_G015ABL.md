# RESULT_G015ABL -- ro soat 45 feature net015, bo dan funding-drift cluster (f23, f18/f21/f22)

Pre-reg: `docs/PREREG_G015ABL.md`. Diem bang `research/analysis/x1_rates.py X1_C3_G015ABL0
X1_C3_G015ABLn` (hieu = ABLn - ABL0, KHONG so truc tiep X1_C3_FULL_PARITY -- xem muc 0).

## 0. Vi sao so voi Stage 0 (control), khong so truc tiep X1_C3_FULL_PARITY
`docs/G4_RECIPE_C4.md` da do: retrain lai net015 qua `g015_net_train.py` (cung trainer dung
cho thi nghiem nay) chi dat spearman 0.985997 so voi model san xuat goc tren fold 20240101 --
KHONG phan biet duoc voi nen nhieu seed cung moi truong (s42 vs s43 = 0.984931). Neu so
Stage 1/2 truc tiep voi X1_C3_FULL_PARITY (dung tu model goc), hieu ung retrain-noise se lan
vao ket qua. Vi vay PREREG da bo sung **Stage 0 (control)**: retrain toan bo 45 feature
(`--drop-cols=""`), cung seed=42/may/script, lam nen so sanh cho Stage 1 va Stage 2.

**Cong hoi quy Stage 0** (muc 1 PREREG, tieu chi [0.98,0.99]): spearman fold 20240101 Stage 0
vs model san xuat goc = **0.985997** -- khop CHINH XAC 6 chu so voi gia tri da ghi trong
`G4_RECIPE_C4.md` cho "GPU s42 tai dung vs GOC x26". PASS -- xac nhan patch `--drop-cols=""`
la no-op that su, moi truong Kaggle tai lap dung.

## 1. Ket qua chinh (equity/CAGR KHONG phai tieu chi)

| tag | feature | n | win% | TSloss% | mP\|SM | mP\|SL | meanP | mMargin | maxDD% | UW | equity | CAGR% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| X1_C3_G015ABL0 (control, 45f) | 45 | 2319 | 83.96 | 15.65 | 7.436 | -19.544 | 3.213 | 1916 | -12.25 | 240 | 100,424 | 30.20 |
| X1_C3_G015ABL1 (bo f23) | 44 | 2272 | 83.67 | 15.71 | 7.292 | -19.901 | 3.019 | 1725 | -12.43 | 223 | 90,939 | 27.00 |
| X1_C3_G015ABL2 (bo f23+f18+f21+f22) | 41 | 2222 | 83.21 | 16.38 | 7.520 | -20.493 | 2.931 | 1516 | -27.74 | 284 | 78,617 | 22.46 |

## 2. Stage 1 (bo rieng f23 `fundingPersistence`) -- NULL

### 2.1 Rate + CI (hieu = ABL1 - ABL0)
Toan cua so 48 thang: **0/5** rate chat luong ngoai CI theo huong co loi (dieu kien can >=2).
`mMargin` ngoai CI (-191.2, CI [-242,-141]) nhung bi loai khoi bo tieu chi quyet dinh theo quy
uoc cua script (giong K12/5MGRID) -- du vay no AM o CA 4 nam khong ngoai le (-36.8 / -84.0 /
-155.5 / -326.4), cung co che suy giam margin da thay o 5MGRID (RESULT_5MGRID.md muc 4) nhung
nhe hon (~-10% toan cua so vs -20% cua 5MGRID).

Tach nam: 2022 0/5, 2023 0/5, 2024 **2/5** ngoai CI (mP\|SM -0.453, meanP -0.594 -- CA HAI AM,
tuc XAU hon, khong phai thang), 2025 0/5. **Khong nam nao co huong THANG (co loi) ngoai CI.**

### 2.2 Rang buoc cung (relative so Stage 0, tung nam)
| nam | maxDD ABL0 | maxDD ABL1 | chenh | han +3pp | UW ABL0 | UW ABL1 | chenh | han +30d | ket qua |
|---|---|---|---|---|---|---|---|---|---|
| 2022 | -10.61 | -12.43 | -1.82 | OK | 42 | 150 | +108 | **VI PHAM** | UW vuot xa han |
| 2023 | -2.86 | -2.50 | +0.36 | OK | 61 | 57 | -4 | OK | sach, hoi tot hon |
| 2024 | -12.25 | -11.13 | +1.12 | OK | 240 | 223 | -17 | OK | sach (quy_min ABL1 -4.74 > han cua ABL0 da vi pham -6.28 cung quy, khong phai vi pham MOI) |
| 2025 | -10.41 | -11.08 | -0.67 | OK | 234 | 223 | -11 | OK | sach |

Vi pham 1/4 nam (2022, UW). **Khong dat >=3/4 nam nen KHONG kich hoat dieu kien dung som
Stage 2** (muc 3 PREREG), nhung Stage 1 tu no khong dat dieu kien thay the (thieu ca dieu
kien (2) va (3)).

**Phan quyet Stage 1: NULL.** Giu nguyen f23 trong 45 feature.

## 3. Stage 2 (bo them f18/f21/f22 cung f23 -- 41 feature) -- NULL, XAU HON RO RET

### 3.1 Rate + CI (hieu = ABL2 - ABL0)
Toan cua so: **0/5** ngoai CI theo huong co loi. `mMargin` ngoai CI (-400.6, CI [-501,-296]),
loai khoi quyet dinh nhung AM manh hon Stage 1 o CA 4 nam (-52.6 / -371.9 / -362.8 / -674.6)
-- suy giam margin **gap ~2 lan** Stage 1 (mMargin toan cua so: 1516 vs 1916 control = -20.9%,
so voi Stage 1 chi -10.0%).

Tach nam: ca 4 nam **0/5** ngoai CI theo huong co loi (2022 0/5 do CI qua rong vi n giam
manh 334 vs 431).

### 3.2 Rang buoc cung (relative so Stage 0, tung nam) -- 2022 VO NANG NGHIEM TRONG
| nam | maxDD ABL0 | maxDD ABL2 | chenh | han +3pp | UW ABL0 | UW ABL2 | chenh | han +30d | ret_nam ABL2 | quy_min ABL2 | ket qua |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2022 | -10.61 | -27.74 | -17.13 | **VI PHAM manh** | 42 | 238 | +196 | **VI PHAM manh** | -4.85 (AM) | -15.14 | **VI PHAM 4/4 tieu chi cung** |
| 2023 | -2.86 | -2.35 | +0.51 | OK | 61 | 60 | -1 | OK | 58.23 | 6.48 | sach |
| 2024 | -12.25 | -9.48 | +2.77 | OK | 240 | 121 | -119 | OK | 39.07 | -4.41 | sach (quy_min > han cua ABL0, khong phai vi pham moi) |
| 2025 | -10.41 | -13.09 | -2.68 | OK (trong han) | 234 | 232 | -2 | OK | 7.34 | -1.51 | sach |

2022 rieng le da du de KET LUAN: maxDD -27.74% (gap 2.6 lan control), UW 238 ngay (gap 5.7 lan
control), NAM AM duy nhat trong toan bo 3 arm cua thi nghiem nay, quy 2022Q2 -15.1% (control
cung quy +8.8% -- day la VI PHAM MOI, khong phai ke thua tu control). Day la vi pham nghiem
trong nhat trong toan bo lich su K12/5MGRID/G015ABL.

**Phan quyet Stage 2: NULL manh.** Bo them cum f18/f21/f22 KHONG chi khong giup ma con pha vo
on dinh nghiem trong o nam 2022.

## 4. Co che -- gia thuyet
Ca 3 feature bi bo o Stage 2 (`basketFundingAvg`, `fundingPercentileCoin`, `fundingZCoin`) deu
la thong ke funding tren `(-inf, t]` expanding -- FEAT40_LOOKAHEAD.md da canh bao day la "rui
ro tong quat hoa" (time-proxy) nhung KHONG chung minh no la nhieu thuan tuy. 2022 la nam DAU
cua DEV window (lich su funding expanding con ngan, gia tri thong ke chua on dinh) va CUNG la
nam regime funding-rate bien dong manh nhat (giai doan gau 2022). Ket qua Stage 2 sup do dung
o nam nay goi y cac feature funding-drift nay dang MANG THONG TIN THAT ve regime funding,
khong chi la proxy thoi gian -- bo chung lam mat tin hieu dung luc thi truong can no nhat.
Day la GIA THUYET tu quan sat, chua phai chung minh nhan qua day du (cung muc do bang chung
nhu co che DCA leg2+ trong RESULT_5MGRID.md muc 4).

Stage 1 (chi bo f23) khong sup do o 2022 (UW vi pham nhung maxDD/nam-am/quy deu sach) -- cho
thay rieng f23 it quan trong hon cum f18/f21/f22 doi voi on dinh nam 2022, phu hop voi gia
thuyet "cum funding-drift con lai mang tin hieu regime that".

## 5. Phan quyet cuoi cung
**Ca Stage 1 va Stage 2 deu NULL.** GIU NGUYEN net015 45-feature hien hanh lam mac dinh cho
`X1_C3_FULL` / san xuat. Khong feature nao trong f18/f21/f22/f23 duoc go bo.

Muc do tin cay: Stage 1 la NULL "sach" (khong thang, 1 vi pham nhe UW). Stage 2 la NULL
"nang" (khong thang, vi pham nghiem trong nhieu tieu chi cung cung luc trong 1 nam) -- cang
cho thay huong bo feature funding-expanding la SAI, khong chi la "khong khac biet".

GIU LAI toan bo code/model 2 stage de tham khao (khong xoa, dung quy tac muc 6 pre-reg):
- `research/pipeline/g015_net_train.py` (--drop-cols, da qua cong hoi quy Stage 0).
- Model + prediction 18 fold moi stage tai `/home/ubuntu/kg015abl/g015ablv{0,1,2}-stage{0,1,2}-gpu/out/`
  (~3.4GB tong, con giu tren Oracle). Kernel Kaggle van con
  (`chuyendinh/g015ablv{0,1,2}-stage{0,1,2}-gpu`) -- co the tai tao lai bins trong ~1 phut
  bang `kaggle kernels output ... -p .` neu can xoa roi dung lai.
- `profiles/x1_c3_full_ablv0.properties`, `x1_c3_full_ablv1.properties`,
  `x1_c3_full_ablv2.properties` (1 dong khac ban goc, giu lai lam tai lieu cau hinh).

## 6. Equity -- KHONG phai tieu chi, bao rieng
ABL0 (control): 100,424 (CAGR 30.20%). ABL1: 90,939 (-9.4%, CAGR 27.00%). ABL2: 78,617
(-21.7%, CAGR 22.46%). Huong trung voi rate/rang buoc cung o tren nhung KHONG dung de phan
quyet (luat cung AGENT_RUNBOOK #3).

## 7. Don dep
Da xoa ngay sau khi cham diem tung stage (dia Oracle rat cang, dao dong 1-7GB free trong
suot thi nghiem): `wfo_ds_ablv0`, `wfo_ds_ablv1`, `wfo_ds_ablv2` (moi cai ~4.0GB),
`predwf_map_s1a2_x1_ablv0`, `predwf_map_s1a2_x1_ablv1`, `predwf_map_s1a2_x1_ablv2`
(~888MB/cai). Da xoa them `ds_feat5m`/`ds_label5m` (~10GB, du lieu OOM-attempt cu tu
5MGRID, du thua theo RESULT_5MGRID.md muc 6) de co dia chay thi nghiem nay.
