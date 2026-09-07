# K12_RESULT -- SELECTOR_RANK_TOPK 8 -> 12 tren C3_FULL 48 thang

Pre-reg: `docs/PREREG_K12.md` (commit `bc9d066`), viet TRUOC khi chay. Diem bang
`research/analysis/x1_rates.py` + `qret_ladder.py` (2 nguon khop nhau).

## 1. Cong PARITY -- PASS
`X1_C3_FULL_PARITY` (K=8, dataset build lai `wfo_ds_k12`) tai lap DUNG `docs/X1_EXTEND.md`
muc 9: equity 111,428, n=2,266, maxDD -12.46%, UW 227 ngay -- khop tuyet doi tung so. Dataset/
jar/code-sha (`bc9d066`) hop le, duoc phep doc K12.

## 2. Ket qua chinh (equity/CAGR KHONG phai tieu chi)

| tag | n | win% | TSloss% | mP\|SM | mP\|SL | meanP | mMargin | maxDD% | UW | equity |
|---|---|---|---|---|---|---|---|---|---|---|
| K8 (parity) | 2266 | 84.69 | 14.96 | 7.333 | -19.570 | 3.308 | 1945 | -12.46 | 227 | 111,428 |
| K12 | 2971 | 83.74 | 16.49 | 7.321 | -18.718 | 3.027 | 1589 | -17.09 | 239 | 106,984 |

## 3. Tieu chi rate+CI -- KHONG dat nguong thang
Toan cua so 48 thang: chi **1/5** rate chat luong ngoai CI (`TSloss%` +1.53pp, XAU cho K12,
CI [0.487, 2.705]) -- can **>=2** theo quy tac muc 6 cua pre-reg. Tach rieng tung nam
2022/2023/2024/2025: **0/5** rate ngoai CI o CA 4 nam -- cai "1" cua toan cua so la hieu ung
gop trong so theo n, khong lap lai duoc o bat ky nam rieng le nao. => **Khong dat dieu kien (1).**

## 4. Rang buoc cung -- VI PHAM nhieu, khong phai ranh gioi
So RELATIVE voi K8 chay lai cung dataset (dung so cu X1_EXTEND lam doi chung phu, khong dung
de phan quyet vi khac dataset build):

| nam | maxDD K8 | maxDD K12 | chenh | han +3pp | UW K8 | UW K12 | chenh | han +30d | quy_min K8 | quy_min K12 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022 | -12.46 | **-17.09** | **-4.63** | VI PHAM | 64 | **187** | **+123** | VI PHAM | 0.63 | -1.58 |
| 2023 | -2.51 | -3.38 | -0.87 | OK | 45 | 62 | +17 | OK | 7.80 | 9.73 |
| 2024 | -11.36 | -12.38 | -1.02 | OK | 121 | **239** | **+118** | VI PHAM | -4.64 | **-6.31** (quy MOI vi pham) |
| 2025 | -10.60 | -11.75 | -1.15 | OK | 227 | 232 | +5 | OK | -2.47 | -3.03 |

Khong nam nao am o ca hai arm (thoa). Nhung **2022 (maxDD+UW) va 2024 (UW + quy moi vi pham
-5%)** vuot han bien pre-reg da chot truoc. => **Dieu kien (2) FAIL toan dien.**

## 5. Co che -- nhat quan voi `F1_FLOW_RESULT.md`, nay THAY tren nen C3_FULL
`TSloss%` xau di **O CA 4 NAM lien tuc** (17.00->19.21, 13.64->15.69, 14.52->16.11,
14.82->15.90) du khong nam nao rieng le vuot CI -- huong DON DIEU giong het co che da tim
o F1 (K cao hon = them lenh rank sau = chet time-stop nhieu hon), nay lap lai TREN NEN
C3_FULL co DCA that (dieu F1 chua kiem vi F1 chay tren C2b, DCA off).

DCA leg2+ PnL GIAM o ca 2 nam co DCA duong: 2022 2758->1720, 2025 4813->2933. Ly do thay
truc tiep tren `mMargin`: budget bi loang cho nhieu vi the hon (K12 mo them ~700 lenh/48
thang) nen `mMargin` toan cua so giam **-18%** (1945->1589) -- moi vi the DCA nho di, giam
kha nang "cuu lo" dung luc. => **dieu kien (3) cua pre-reg cung KHONG dat**: co che ro rang
chong lai K12, khong phai ngau nhien.

## 6. Phan quyet -- NULL, DONG huong
Ca (1) va (2) deu KHONG dat (dieu kien (3) cung phu hoa chong lai). **K=12 KHONG thay K=8.
Giu `SELECTOR_RANK_TOPK=8` cho C3_FULL.** Day la NULL **manh hon** ca `F1_FLOW` (K=16 tren
C2b, DCA off): mo rong K tren nen C3_FULL lam maxDD/UW xau NHANH va SAU hon (mot nam mat
+4.6pp maxDD tuyet doi, +123 ngay underwater) vi DCA giai ngan budget cho nhieu vi the hon
cung luc -- hai co che (rank sau thieu edge + DCA loang von) CONG HUONG thay vi trung hoa
nhau. Khong tune them gia tri K khac (K=9/10/11) sau khi thay so nay.

## 7. Equity -- KHONG phai tieu chi, bao rieng
K8: 111,428. K12: 106,984 (thap hon 4.0%). Huong trung voi rate/rang buoc cung o tren nhung
KHONG dung de phan quyet (luat cung #3 AGENT_RUNBOOK).

## 8. Don dep
Dataset `wfo_ds_k12` (4.0G) da xoa sau khi cham diem xong -- dia Oracle 94% day, khong duoc
giu du thua.
