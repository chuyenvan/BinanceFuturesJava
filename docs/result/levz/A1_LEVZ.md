# A1_LEVZ - AUDIT doc lap (agent A1, Opus) cho RUN LEVZ (PREREG_LEVZ @5e1031bc)
Ngay 2026-11-25. Code + output cua A1: ~/claude_master/w3/levz/a1/ (recalc.py, sample.py, recalc.json, sample.csv/json, ev_*.parquet, *.log). Khong import code RUN.

## VERDICT AUDIT: PASS-WITH-MINOR - ket luan NO-GO DUNG VUNG.
Moi nhanh truot C1 (p Holm >= 0.52) va C5 (bo 5% tot nhat => am) o ca ban cua RUN, ban A1 doc lap, ban funding "theo chu" va ban OI/f "theo chu".

## 1. Tai lap doc lap (DA KIEM BANG SO)
- recalc.py: dung lai toan bo panel gio tu file tho (kline1m, metrics5m, funding, d1), universe, z_oi/z_f/z_r, dot + cooldown 72h, E0/E1, ket qua.
  Tap lenh: 8/8 (nhanh x ky) KHOP 100% theo (sym, t0, te): KP 165/122/180/130, XN 469/340/577/406; 0 lenh le o hai phia.
  Sai khac gia tri: z_oi, z_f, f, P(te), funding, MAE = 0 tuyet doi. Lech duy nhat: 1 lenh/nhanh XN co te+24h > 2025-12-31 (A1 dung close 23:59, RUN dung close 23:00 - trai CHOICES muc 3 cua chinh RUN): lech net_ex lenh do <= 0.60%, lech mean <= 0.002%.
- sample.py (brute-force thang tu file tho, tung lenh, khong panel): 44 lenh (20 KP + 24 XN, 5-6 moi nhanh moi ky). Lech max: net_ex 1.5e-16, EW 0, P(te)/P(te+24h) 0, funding 1.5e-16, z_f 6.6e-11, z_r (E1) 1e-13, so coin EW 44/44 trung.
  z_oi: 39/44 lech < 2e-9; 5 lenh 12/2023 lech <= 0.014 - DA TRUY: OI tho co ban ghi oi=0 (2023-11-23 03:50, 2023-11-26 00:50); RUN bo oi<=0 va lay ban ghi hop le truoc do (dung "ban ghi moi nhat hop le"), brute cua A1 de NaN. RUN DUNG.
- Mui gio / can gio: kline ts la phut UTC ms, P(te) = close nen open_time == te (kiem 44/44); funding 8h thanh toan dung 00/08/16 UTC, ts lech 0-15 ms; metrics ts boi so 5' UTC, khong trung (sym, ts). OI dung tai t co tuoi dung 10' (max oi_age = 10' moi lenh) => khong ban ghi tuong lai. E0: te == t0 100%; E1: te > t0 100%.
- Dau: gross = -(P1/P0-1); rate>0 => short CONG (brute khop); net_ex = net + EW (short tru beta dung chieu).
- EW: universe A1 tu tinh tu d1 tai ngay te, trung so coin voi RUN 44/44; 0 coin universe thieu gia tai te o moi lenh (khong loai thien lech); coin huy niem yet trong cua so => close cuoi (dung prereg muc 4), n_sub24 = 1 lenh/nhanh XN, 0 o KP.

## 2. Bang 4 nhanh do A1 tinh (net_ex 24h, % moi lenh; bootstrap cum tuan seed 777)
| nhanh | KP n | KP mean [CI] | XN n | XN mean [CI] | p1 | p Holm | XN bo top5% | XN median | gross tho XN | EW XN | gross+EW XN | fund XN | KP gross / EW |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 W14-E0 | 165 | +0.40 [-0.90; 1.34] | 469 | +0.44 [-0.56; 1.59] | 0.228 | 0.68 | -0.85 | +1.59 | +0.31 | +0.12 | +0.43 | +0.15 | +0.92 / -0.47 |
| A2 W14-E1 | 122 | +0.37 [-1.10; 1.44] | 340 | +0.85 [-0.34; 2.46] | 0.130 | 0.52 | -0.71 | +1.16 | -0.11 | +0.98 | +0.87 | +0.12 | +0.21 / +0.22 |
| A3 W7-E0  | 180 | +0.33 [-1.31; 1.27] | 577 | -0.08 [-0.93; 0.92] | 0.571 | 0.80 | -1.45 | +0.74 | +0.03 | -0.12 | -0.09 | +0.15 | +0.64 / -0.26 |
| A4 W7-E1  | 130 | +0.30 [-1.98; 1.79] | 406 | +0.16 [-1.00; 1.52] | 0.401 | 0.80 | -1.32 | +0.74 | -0.62 | +0.81 | +0.18 | +0.11 | -0.60 / +0.96 |
EW = loi suat long deu cua universe cung 24h (EW > 0 = thi truong tang). gross+EW = loi short vuot beta truoc phi/funding. Funding (~+0.11..0.15%) gan bang phi 0.14% => net_ex ~ gross+EW.
Ti le gross > 0 XN: 59% / 51% / 56% / 50%. Theo nam XN: A1 2024 +0.14 (365) 2025 +1.51 (104); A2 2024 +0.01 (263) 2025 +3.71 (77); A3 2024 -0.49 / 2025 +1.00; A4 2024 -0.57 / 2025 +2.20.
Khop RUN: mean XN RUN +0.4412/+0.8483/-0.0819/+0.1578 vs A1 +0.4425/+0.8500/-0.0809/+0.1593 (lech chi do lenh cuoi ky); p, CI gan (seed khac).
Cham lai C1-C8 = trung RUN: A1 truot C1,C5; A2 truot C1,C3(KP n122),C5,C6,C7(MAE_close 30.9%); A3 truot C1,C5,C8; A4 truot C1,C3(KP n130),C5,C6. C7 "?" cua A1/A3/A4 khong doi verdict (da truot C1, C5) - XAC NHAN.

## 3. Lech prereg (muc + anh huong bang so)
- (nho) Funding (te+1m, te+H+1m] thay (te, te+H]: chi khac voi ky co ts lech ms. Ban theo chu: mean XN +0.4435/+0.8505/-0.0799/+0.1595 (A1), RUN-lit +0.4422/+0.8488/-0.0809/+0.1581; p Holm khong doi; bo top5 van am. Verdict KHONG doi. Ban cua RUN hop ly kinh te hon.
- (nho) "OI tre toi da 1h" + "f con hien hanh": ban A1 theo chu (OI moi nhat hop le khong gioi han tuoi, f khong yeu cau hien hanh): n giong het moi nhanh tru A2 XN 340 -> 339; mean XN +0.45/+0.84/-0.08/+0.16, KP +0.40/+0.40/+0.33/+0.30. Verdict KHONG doi.
- (nho) Gia cuoi ky XN dung close 23:00 thay 23:59 (trai CHOICES 3): 1 lenh/nhanh, mean lech <= 0.002%.
- (han che du lieu, da khai) MAE do bang close 1m (can duoi). C7 A1/A3/A4 (25.8/25.0/29.8%) chua ket luan; A4 sat 30% - MAE that gan nhu chac > 30%. Khong anh huong verdict.
- Khong thay lua chon nao trong CHOICES lam doi luat theo huong tao/giet tin hieu; cac muc 5,6,8,11 deu trong pham vi dien giai.

## 4. Ky luat
- FREEZE.txt: sha256 7 file code KHOP code hien tai (A1 kiem). frozen 10:17:41Z; XAC NHAN chay 10:17:50Z (log), sau freeze. Lan chay XN thu 2 = V5 (prereg bat buoc), md5 14 file trung.
- levz.py/.pyc mtime 17:09 (+07) truoc KP 17:12 => khong sua loi phan tich sau khi xem KP; score.py sua 17:13 (sau KP, truoc freeze) - chi bang/cham, khong doi so.
- Reader RUN filter ts < 2026-01-01 + assert; grep code/log khong thay doc 2026. KP nap du lieu den 2024-01 (de tinh ket qua lenh cuoi 2023) - nam trong XN nhung chi gia, chap nhan duoc.
- V0/build doc tho 2024-25 truoc freeze: chi dem phu + bang gio, khong tinh tin hieu/ket qua; log V0 chi so dem. Anh huong: thap (khong co thong tin hieu suat).
- TU KHAI cua A1: trong lenh kham schema dau tien A1 da nap TOAN BO d1.parquet (co ngay toi 2026-09-30) va in 5 dong dau (09/2025) + min/max ngay; khong xem gia tri nao >= 2026. Cac lenh sau deu filter day < 2026-01-01. Khong anh huong so.

## 5. Giet nham? (tung gia thuyet loi, DA KIEM BANG SO)
- Dau short nguoc: KHONG (brute 44/44). EW tru sai dau: KHONG (net_ex = net + EW, brute). Vao tre 1h: KHONG (P(te) = close nen open_time te; E0 te = t0). z gom t: KHONG (cua so [t-W, t-1h], tai lap chinh xac bang code doc lap). Funding nguoc dau: KHONG.
- San sd: 17.7% (W14) / 27.4% (W7) dot XN dang chiu san; n XN 469-577 cho E0 => san KHONG lam mat gan het su kien. (Khong chay ban bo san - la bien the moi.)
- Universe: median 150 coin tai te, 0 thieu gia. Khong hep bat thuong.
- Ket qua: chieu loi short vuot beta DUONG o 3/4 nhanh XN (+0.43/+0.87/+0.18), am A3 (-0.09); KP ca 4 +0.36..+0.45. Nhung: CI rong (MDE80 ~1.1-1.8%/lenh), p Holm >= 0.52, phu thuoc 2025 (A2 2024 = +0.01%) va duoi phai (bo 5% => am, median > mean khong cuu duoc). Gross tho (chua tru beta) XN gan 0 hoac am cho E1 (-0.11, -0.62): phan duong cua A2/A4 den tu viec thi truong tang (EW +0.8..+1.0%) chu khong phai coin roi tuyet doi.

## 6. Phan CHI MO TA
- D_hard tinh lai tu parquet RUN: KP +2.0172% n64, XN -2.0435% n392, MAE_close>=10% 37.8% - DUNG. Guong / tung thanh phan: chi doi chieu summary_*.json voi bang (khop), KHONG tai lap doc lap events.
- RESULT ghi ro "CHI MO TA, KHONG duoc dung de tuyen bo"; khong thay trinh bay nhu ket luan. OK.

## 7. MASTER DUOC noi / KHONG DUOC noi voi owner
DUOC: "LEVZ dong theo luat: 4 nhanh khong nhanh nao co y nghia (p Holm >= 0.5), bo 5% lenh tot nhat thi am. Da audit doc lap, tai lap 100% tap lenh, khong co loi dau/gio/join." "Co dau hieu chieu dung nhung nho (+0.2..+0.9%/lenh vuot beta o 3/4 nhanh), khong phan biet duoc voi 0, don vao 2025 va vai lenh lon." "Phep thu chi du suc phat hien edge >= ~1.1-1.8%/lenh; edge nho hon khong bi loai tru nhung cung khong du chung minh."
KHONG DUOC: "Chung minh khong co tin hieu" / "z-score vo dung". "Co edge +0.85% (A2)". "Nguong cung +2% (KP)" hay "guong long co loi" - la mo ta, da dao dau. Mo lai bang nguong/cua so/phi khac (trai prereg muc 6).

## 8. Khong kiem duoc
- MAE that (khong co high 1m). Ban khong san sd (bien the - khong chay). Tinh dung cua quy uoc create_time 2024-03-04 ngoai luat tre 10' (khong co nguon doi chieu). Tai lap doc lap events guong / chi z_oi / chi z_f. Ledger + docs/result/LEVZ.md (prereg muc 8) - khong kiem.
