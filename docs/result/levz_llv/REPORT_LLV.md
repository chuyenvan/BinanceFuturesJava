# REPORT_LLV - lenh LONG co kem khi coin "dong long"? (PREREG_X3_1127 phan C) - 2026-11-27
Code: `code/llv.py` (1 lan chay, khong tune). Output: `out/llv.json` (moi bang), `out/clusters.parquet`, log `logs/llv.log`.
Du lieu < 2026-01-01 UTC (assert). Perm seed 20261127, 5 000 luot.

## Dinh nghia (chot truoc khi chay)
- Ledger 4 seed c0s42/c0s7/c0s123/c0s13; gio UTC+7 -> UTC (-7 h, da kiem levz_an c_tzcheck).
- CUM (C1): cung sym, sap theo gio vao; leg moi thuoc cum neu ts <= max(te) cua cum (noi tiep cham dung phut dong cung tinh la noi tiep:
  256-293 truong hop / seed). ret = sum pnl / sum margin (margin = notional vao). Nam/thang = gio vao leg dau (UTC). DEV = 2022..2025.
- k = moc gio CHAT TRUOC phut vao (T_k < ts; vao dung HH:00 -> dung HH-1). Dac trung tu sig_W7 (z_oi, z_f, f), doi24 = lnOI[k]-lnOI[k-24]
  (dinh nghia feat_b3, OI tsr <= h-10 min). LEV24 = co gio j in [k-23,k] voi z_oi>=2,5 & z_f>=2,5 & f>1e-4 (NaN = khong).
- Hop le kiem dinh: map duoc sym, u[k]=1, z_oi/z_f/f/doi24 huu han.
- Perm: hoan vi nhan trong (seed, thang); thong ke = TB 4 seed cua (TB nhom - TB phan con lai); mot phia; nguong 0,0125.

## So cum
| seed | cum (tat ca) | DEV | 2022/23/24/25 | khong map | ngoai universe | hop le |
|---|---|---|---|---|---|---|
| c0s42 | 3146 | 2580 | 484/708/777/611 | 3 | 897 | 1664 (64,5 %) |
| c0s7 | 3228 | 2662 | 474/710/825/653 | 4 | 949 | 1692 (63,6 %) |
| c0s123 | 3245 | 2678 | 501/722/848/607 | 4 | 919 | 1738 (64,9 %) |
| c0s13 | 3126 | 2550 | 515/710/773/552 | 3 | 881 | 1652 (64,8 %) |
Khong map: BLUEBIRD, FOOTBALL. So leg/cum (DEV): ~93 % 1 leg, ~5 % 2 leg, max 13.
Hop le: sum pnl cum = sum pnl ledger = equity_final - equity_start (4/4, sai so < 1 USD).

## Kiem dinh
| H | n nhom (gop 4 seed) | chenh TB gop | seed nhat quan (>=3/4 nam) | p perm | ket luan |
|---|---|---|---|---|---|
| H1 LEV24 thap hon | 198 (2,9 %) | -0,31 pp | 0/4 | 0,101 | KHONG CO MANH MOI |
| H2 z_oi <= -1 cao hon | 1470 (21,8 %) | +0,97 pp | 3/4 (c0s7 2/4) | 0,0008 | CO MANH MOI |
| H3 f < 0 cao hon | 1577 (23,4 %) | +0,62 pp | 0/4 | 0,0002 | KHONG CO MANH MOI (khong nhat quan) |
| H4 doi24 ngu phan vi thap cao hon | 1355 (20,1 %) | +0,78 pp | 3/4 | 0,021 | KHONG CO MANH MOI (p > 0,0125) |
Bang nam x seed day du trong llv.json (tests.*.table). Diem chinh:
- H1: 2022 khong co cum LEV24 nao; 2023 sai dau 4/4, 2025 dung dau 4/4 nhung moi o chi 3-5 cum.
- H2: 2024 dung dau 4/4 (+2,4..+3,1 pp) va 2025 4/4 (+0,1..+0,9); 2023 sai dau 3/4; 2022 dung 3/4. Hieu ung chu yeu tu 2024.
- H3: 2022-2023 dung dau 8/8 (+1,6..+3,3 pp), 2024-2025 sai dau 8/8 -> phu thuoc che do (2022 funding am pho bien).
  Null perm H3 TB -0,53 pp (khac 0 vi thanh phan thang) - p nho nhung khong qua tieu chi nhat quan.
- H4: 2022 sai dau 4/4, 2024 dung 4/4 (+1,9..+2,3 pp).

## Uoc tho tac dong PnL (BO QUA phan hoi slot / quota / von - cum bi bo khong duoc thay bang lenh khac)
PnL DEV goc (USD): 97 126 / 101 881 / 116 579 / 112 339.
- Bo cum LEV24 (H1): 94 841 / 99 513 / 115 093 / 111 251 (-1,0..-2,4 %), bo 1,7-2,0 % cum. Khong co loi.
- Chi giu nhom tot trong cum hop le (cum khong hop le giu nguyen): H2 57,8k/58,5k/68,8k/67,5k (bo ~50 % cum DEV, PnL -40..-43 %);
  H3 -43 %; H4 -40 %. Moi nam deu giam. => Gate cung "chi vao khi z_oi <= -1" PHA PnL: phan con lai van lai TB ~+3,3 %/cum.
  Neu dung, chi dang xet la nghieng size (tang size nhom z_oi <= -1), khong phai loc.

## Mo ta (ngoai kiem dinh)
- 2,9 % cum hop le roi vao LEV24.
- ret TB theo ngu phan vi z_oi (trong nam-seed, gop): Q1 (thap) 4,7 % / Q2 3,3 / Q3 3,6 / Q4 4,4 / Q5 2,4 - khong don dieu;
  Q5 thap nhat o 3/4 nam. TB toan bo 3,7 %, trung vi 5,4 %, sd 11 %.
- Ti le time-stop (proxy: leg giu dung 168/336/504 h) va lo lon (ret <= -10 %), nhom vs con lai:
  H1 12,6/14,5 % ; 9,6/9,6 %. H2 12,2/15,1 % ; 8,1/10,0 %. H3 11,9/15,3 % ; 9,2/9,7 %. H4 15,4/14,3 % ; 8,3/9,9 %.

## Kiem nhan qua
- Moi cum: T_k < ts (assert); 50 cum ngau nhien: T_k = H0 + k h, tre 1-60 phut; z_oi/z_f/f khop dong sig_W7 (sym, t=T_k);
  OI tsr[k] <= T_k - 10 min va tsr[k-24] <= T_{k-24} - 10 min; doi24 khop; LEV24 chi dung k-23..k. 0/50 loi.
- Quy uoc sig (tu levz.py, da audit): f = settlement ts <= t - 1 min; z_oi tu OI tsr <= t - 10 min.

## Gioi han
- 4 seed la cung chien luoc, cum trung lap phan lon -> "3/4 seed" khong phai 4 mau doc lap; tieu chi nhat quan yeu hon tren giay.
- 35-36 % cum DEV bi loai vi coin ngoai universe levz tai k -> ket luan chi cho phan universe.
- Tac dong PnL bo qua slot/quota (von giai phong se vao lenh khac) - can sim Java de biet that.
- Time-stop la proxy theo gio giu; "lo lon" -10 % dat tay, chi mo ta.
- H2 dat chu yeu nho 2024; 2023 nguoc dau.
## Buoc ke (C4)
H2 "CO MANH MOI" -> theo C4: prereg gate/nghieng size dua tren z_oi <= -1 + sim Java (Kaggle), ngoai pham vi file nay. Luu y uoc tho cho thay loc cung
lam giam PnL; nen prereg dang tang size, khong phai loc.
