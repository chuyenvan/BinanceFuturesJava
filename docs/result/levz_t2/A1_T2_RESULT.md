# A1_T2_RESULT - kiem toan doc lap KET QUA T2 (2026-11-27)
PHAN QUYET: PASS-CO-LUU-Y. So lieu grid/select/placebo/report tai lap doc lap khop tuyet doi; ket luan "KHONG HON E0" ca 6 kieu dung luat.
Luu y chinh: dong moc B1 trong report KHONG cung pool voi E0 T2 (xem muc 2).

1 sha: PASS. 9 code + entry_t2.npz + CHOICES/DEV khop SHA256SUMS.txt (=A1_T2_CODE). Ket qua: grid 7a3d9f4e, select 5ccc5084, placebo 663e9ecb,
  report.md 503f1d93, report.json 3b94ec61 - khop. Goi Kaggle pkg/t2: 6 file code cung sha.
2 Nghi van E0 vs B1: KHONG LOI. Hang E0 ho B1 (1755) == grid_b1 W=7,E=E0 (1755): max|diff| ret/n/maxdd_worst F1..F3,DEV = 0.
  PART/STATE E0 (72+72) == grid_t1 gate NONE: diff 0. Nguyen nhan lech: moc B1 tinh tren TOAN grid_b1 7020 cfg (W 7/14 x E E0/E1).
  Tai lap B1 full: frac_pos 64.4/19.6/84.0 %, WFO24 top20 -22.96 %, WFO25 top20 +6.11 % (dung moc). Subset W7E0: 72.8/45.0/84.2 %.
  2024 khop vi top-20 B1 = 20/20 W7E0; 2025 top-20 B1 co 5/20 W14 => +6.1 vs +10.2. Top-1 2024/2025 B1 = T2 E0 (-36.3 / +10.9).
  => E0 T2 la moc hop le "cung quy trinh T2" (U-f). Dong B1 trong report chi la tham khao, KHONG so sanh truc tiep.
3 Tai lap WFO/frac_pos doc lap (code rieng): lech lon nhat = 0 (cung chosen id, cung 20 id, cung median) ca 7 kieu.
4 Placebo time: PASS. 600 part, 600 (entry,rep) duy nhat, rep 0..99 du, seed/ten khop, 0 dong ket qua trung. Shard 0 Oracle = EL_1,
  shard 1..5 Kaggle = EL_2..EO_5 (dung i%6). n_filled = npz. Trial Kaggle (EL_2/EB rep 0,1) trung tuyet doi part chinh (tat dinh).
  p tinh lai: EL_1 41/101, EL_2 15, EL_3 92, EB 101, EO_3 89, EO_5 10 (n_ge 40/14/91/100/88/9) = json. Thong ke placebo = cung ham wfo_stat.
  Luu y: placebo EB/EO chi tren ung vien SE khop (chon theo tuong lai) - doi chung cau truc, khong phai chien luoc giao dich duoc.
  EB: placebo trung vi 0.73 vs that -0.016 => cho gay vao DO hon ngau nhien trong chinh cua so.
5 U-a..U-f tinh lai = report. EL_1: dat U-a,U-d; truot U-b (F2 45.4 %<50), U-c (p 0.406), U-e (bo best5: -222/-411), U-f 2025 (+0.59 vs +10.24).
  EO_5: dat U-a,U-d,U-f; truot U-b (F2 30.0 %), U-c (p 0.099>0.05), U-e (2024 top1 -10.6 %, bo best5 -2383) => khong du ca muc "CO CAI THIEN".
  EB: valid 13 (2024) / 4 (2025) cfg => "top-20" thuc la 13/4 cfg; top-1 None vi khong cfg nao qua plateau 60 % - dung luat. U-d truot (77 lenh).
6 Du lieu: PASS. 13293 cfg = 7x3x3x211; signal max 2025-12-31 10:00; phut vao max < 2026-01-01; khong cot 2026; NaN chi o tham so khong
  thuoc ho. Khop 0.889/0.797/0.714/0.293/0.957/0.878, EL gia/p0 = 1.01/1.02/1.03 dung dinh nghia; EB/EO gia/p0 min 0.365 (M4, giu).
7 Khong duoc noi: DEV (in-sample); p perm = NaN (job dang chay); placebo p chua hieu chinh 6 kieu; report van gan nhan "CHUA AUDIT".
