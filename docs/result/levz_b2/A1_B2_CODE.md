# A1_B2_CODE - audit doc lap tang GATE/FILTER LEVZ B2 (truoc khi chay luoi) - A1 (Opus) 2026-11-26 06:21-06:45 UTC
Luat: PREREG_LEVZ_B2 (da636b28) + ADDENDUM1 (d1241f48). Doi tuong: w3/levz_b2 (SHA256SUMS 15/15 OK). Sandbox A1: a1/ (code/, out/, devtest/).
Khong chay grid_b2 cho phuong an nao, khong tao out/grid_b2_*, khong bao so loi nhuan.

## VERDICT: PASS-WITH-MINOR cho `grid_b2 all -> report_b2`.
Placebo (muc 4e): BAT BUOC MASTER quyet TRUOC placebo cho F_NOPUMP / F_PUMP / F_FHI (xem B1). Khong chan luoi + report.

## B. Loi
B1 (BAT BUOC truoc placebo, khong chan luoi) - opts.py:124-131 draw_filter_perm + ADDENDUM1 B: voi F_NOPUMP / F_PUMP / F_FHI hoan vi nhan coin
  trong thang KHONG BAO GIO dat +-20 % ti le loai that tren tap ung vien (40 lan rut tho, ti le loai: F_NOPUMP that 0,270 vs hoan vi 0,011-0,035;
  F_PUMP 0,529 vs 0,880-0,928; F_FHI 0,118 vs 0,650-0,722; 0/40 trong dung sai) => placebo_b2 se RuntimeError sau 1 000 lan rut (da tai hien
  bang F_NOPUMP). Ly do: tap ung vien la coin dang bom / funding cao, nhan coin khac trong thang khong mang dac tinh do. F_LIQ50 (0,443 vs
  0,465-0,583; 60 % luot dat) va F_AGE90 (0,112 vs 0,059-0,120; 50 %) chay duoc. Hong an toan (dung, khong ra p sai) nhung neu 1 trong 3 filter
  nay dat (a)-(d) thi KHONG co placebo => MASTER can addendum (vd hoan vi nhan loc giua UNG VIEN cung thang = phuong an B-khac trong CHOICES_B2).
Khong co loi lam sai ket qua luoi / report.

## MINOR
M1 placebo GATE: dich vong giu ti le mo tren vong nhung ti le ung vien duoc giu cua placebo 0,41-0,54 (G_EW7, 3 luot) trong khi gate that
   chan ~57-99 % ung vien (gate that phan tuong quan voi tin hieu) => placebo co nhieu lenh hon han; thong ke "ti le cau hinh co lai F2"
   lan voi hieu ung so lenh. Dung chu prereg; ghi de MASTER doc p dung.
M2 Dich vong quay ca vung khoi dong NaN (BRmed NaN den 2022-03-01, EW14 14 ngay dau) vao giua chuoi => voi G_BRhi/G_BRlo placebo co
   ~3 thang gate dong gia. Nho.
M3 grid_b2.py:1-5 docstring hua assert "n_trades <= ... kept cands > 0" - khong co trong code (chi check_acct). Chu thich.
M4 BR: DEV them bao ve do phu (CHOICES 4): 65 gio 2022-2025 BR = NaN (cua so co gio < 50 % coin co z) => G_BRhi/G_BRlo chan ung vien gio do
   (11-17 ung vien/lop). Bat loi, phu hop "thieu du lieu => chan". BRmed bo qua cac gio NaN.
M5 (c) lay min 2 cach doc + them DEV: chat hon prereg (bat loi) - chap nhan. So sanh float bien (0,05-0,02) khong epsilon - khong dang ke.
M6 Cat-line: tham chieu dong mkt.py trong bao cao DEV dung; khong van de.

## Ket qua tinh lai doc lap (code A1, tu parquet goc kline1m / funding / d1 / sig_W7; a1/code/recalc_mkt.py)
Gia gio = close nen 1m CUOI co open_time trong [T_k-60m, T_k-1m] (A1 tu dung tu kline1m, khong qua hr_*).
- 300 gio ngau nhien 2022-2025: EW3 300/300, EW7 300/300, EW14 300/300 (max|d| 1e-16), BTC7 300/300, BTC20 300/300 (1e-13), BR 300/300,
  BRmed 298/300 (2 lech = do BR NaN-guard M4 trong cua so 90 ngay; dung BR cua DEV thi khop). BR toan chuoi 2022-2025: 34 999/35 064, 65 lech
  = dung 65 gio NaN-guard (da kiem: moi gio deu co do phu < 50 % trong cua so).
- 600 (coin, gio) (300 tu ung vien cand_b1, 300 o U ngau nhien): R24 600/600, f (r8 ky gan nhat <= t-1m) 600/600, qv30 600/600, tuoi 600/600.
- BTC: 0 gio thieu 2022-2025 (BTCdev doi du 24n gia khong anh huong).
- Ham DEV (cc_from_hr, ewr, btcdev, br, brmed, lagret) chay lai tu hr_* + sig_W7 => trung BYTE mkt.npz (8/8 chuoi).
Look-ahead (a1/code/lookahead.py): 3 moc cat ngau nhien; lam nhieu CC, z_oi, z_f, f sau moc => moi gia tri <= moc KHONG doi (8/8 chuoi x 3),
  sau moc doi (tru BRmed trong 400 gio - trung vi 90 ngay van 0, binh thuong). Nen gio dang hinh thanh khong dung (ca pha b07).
  Khong dung gia vao CLH (close nen 1m mo tai T_k) - xac nhan tu code + so khop kline.

## opts / mat na
- Mat na A1 viet lai cho CA 12 phuong an tren toan bo 19 367 ung vien (12 lop): trung 100 % (12/12). Bang ti le chan W7 E0 z2,5 theo nam tai lap
  dung describe_b2 (vd G_EW7 0,903/0,988/0,953/0,574).
- Chi so dong: E1 k = gio kich z_r <= -2 (833/833 lop W7 E1 z2,5), E0 k = gio LEV (4 792/4 792); mau coin-gio lay tu ung vien khop goc => khong lech hang.
- Chi bo ung vien VAO moi; vi the mo / cooldown / top-K do port B1 nguyen.

## grid_b2
- port / exits B1 import nguyen (sha levz_b1, levz2 OK; levz khong file moi). NONE 300 cau hinh chay lai (thu muc tam A1): 300/300 trung tuyet doi
  grid_b1 (moi cot tru sec) + check_acct.
- G_EW7: ung vien do A1 loc -> port.run fold F2 cho 3 cau hinh (cfg 611, 1326, 5700) => ledger lenh + equity TRUNG HET voi duong DEV, va cot F2_*
  cua run_all trung.

## report_b2 - (a)-(d) dung chu: (a) frac(ret>0) >= 0,5 & median >= 0; (b) F1, F3 median >= goc-0,02 & frac >= goc-0,10; (c) min(2 cach doc) >= 0,5
  o DEV/F1/F2/F3 (bat loi); (d) top20_valid (ADD1 B cua B1) median > 0 ca 2024 va 2025; WFO 2024 chi F1, 2025 chi F1+F2 (ca pha r5: xao tron
  F2/F3/DEV khong doi lua chon 2024; xao F3/DEV khong doi 2025).
## Test: DEV 49/49 PASS (chay ban sao trong a1/devtest). Ca pha A1: 15/15 PASS (9 ham chuoi/opts/placebo + 6 luoi gia co bay (a)(b)(c)(d)).
## Thoi gian / RAM (do): port ~0,042 s/cau hinh (1 tien trinh) => 12 x 7 020 ~ 59 phut 1 tien trinh, ~20-25 phut 3 tien trinh; RSS 1 tien trinh 1,7 GB
  (3 fork COW uoc 2,5-4 GB). Placebo: gate 1,7 s/luot, filter (LIQ50) 1,9 s/luot (1 tien trinh) => 500 luot ~15 phut 1 tt / ~5-6 phut 3 tt. Sandbox A1 < 5 MB.
## Khong kiem duoc / suy doan: universe U, z_oi/z_f (tang 1, da audit truoc) dung lai, khong tinh lai tu OI; nhan ngay d1 (dau ngay) gia dinh nhu tang 1.
