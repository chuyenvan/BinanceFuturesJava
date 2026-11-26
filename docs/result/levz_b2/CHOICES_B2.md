# CHOICES_B2 - lua chon cai dat LEVZ B2 (PREREG_LEVZ_B2 @da636b28) - ghi TRUOC khi chay bat ky phuong an nao
Nguyen tac: prereg khong ro => chon cach BAT LOI (neu xac dinh duoc huong), khong thi theo quy uoc tang 1 / B0 / B1 + ghi lai.
Cho nao la doi luat / luat suy bien => "CAN MASTER QUYET" (cuoi file). Engine B1 (port, exits, select_b1) import nguyen, KHONG sua.

## Chuoi (mkt.py)
1. Gia gio: CC[k] = clast cua nen gio [T_{k-1}, T_k) (bang hr_<ym> tang 1: close nen 1m cuoi co open_time trong gio do). KHONG dung CLH
   cua B1 (= close nen 1m mo tai T_k = gia vao, dong luc T_k + 1 phut => nhin truoc 1 phut). Gio khong co nen 1m nao => NaN (khong ffill)
   => moi dieu kien dung no bi chan (bat loi). Nen gio mo tai T_k (dang hinh thanh) khong bao gio duoc dung (test).
2. EWr_n(k): TB deu tren coin U[k] co CA HAI gia CC[k], CC[k - 24n]; coin thieu gia bi BO khoi trung binh (khong chan ca gio); NaN neu
   khong coin nao. Do phu thuc te: >= 66 coin moi gio 2022-2025 (describe_b2.json).
3. BTCdev_n(k) = CC[k, BTC] / TB so hoc CC[k-24n .. k-1, BTC] - 1; can DU 24n gia (thieu 1 => NaN => chan). BTC khong thieu gio nao sau khoi dong.
4. BR(k): cua so 24 gio k-23..k (gom gio t, vi LEV tai k chi dung thong tin <= T_k); LEV7 = z_oi >= 2,5 & z_f >= 2,5 & f > 1e-4 tu sig_W7
   (B0, da audit), KHONG doi u tai gio LEV; tu so chi tinh coin co U[k]; mau so = #U[k]. Bao ve khoi dong: BR = NaN neu trong cua so co gio
   ma < 50 % coin U co z_oi, z_f huu han (=> BR co tu 2021-12-07 15:00). Ung vien E0 tu no lam BR > 0 (khong loai tru chinh no).
5. BRmed(k) = trung vi cac BR huu han trong k-2160 .. k-1 (90 ngay x 24, khong gom k); can >= 1 728 (80 %) gia tri huu han => co tu 2022-03-01.
6. qv30(D) = TB qv ngay D-30..D-1, can du 30 ngay (dinh nghia universe tang 1), D = ngay UTC cua T_k; 50M = 50e6 USDT. Tuoi = so ngay tu
   dong d1 dau tien (d1 bat dau 2021-01-01 => can duoi; khong anh huong vi ung vien tu 2022); khong co d1 => -1 => chan.
7. f = f cua tin hieu B0 (r8: rate ky gan nhat <= t - 1 phut quy ve 8 h, con hieu luc) - cung bien ma LEV dung (f > 1e-4); F_FHI so
   r8 >= 0,0003. sig_W7 va sig_W14 cho f TRUNG nhau (assert khi build).
8. Kiem nguoc tren du lieu that (test): R24, BTC7, EW3, BR, BRmed tai gio ngau nhien tinh lai bang vong lap doc thang hr_*.parquet / sig - khop.

## Phuong an (opts.py)
9. Dieu kien xet tai gio ung vien k: E0 = gio LEV; E1 = gio VAO t1 (gio kich z_r, cung la gio vao). Diem s cua E1 van lay tu gio LEV (B0).
10. Moi gio xet doc lap: ung vien bi chan o k van co the vao o gio sau neu lai la ung vien va dieu kien dat (khong "nho" lan bi chan).
11. Chan chi bo ung vien (k, c) khoi tap ung vien cua lop; vi the dang mo, cooldown, top-K, size, bang thoat: nguyen B1. NONE = khong bo gi
    => tai lap grid_b1 trung tuyet doi (300/300 cau hinh, moi cot tru 'sec').

## Luoi / bao cao (grid_b2.py, report_b2.py)
12. Luoi = dung 7 020 cau hinh grid_b1.all_cfgs (cung cfg_id); assert ke toan B0 check_acct cho DEV/F1/F2/F3.
13. "Loi nhuan" = cot <fold>_ret (ti le); "2 diem %" = 0,02. "maxDD xau nhat" bao trung vi va max qua cau hinh cua <fold>_maxdd_worst.
14. (c) "so lenh con lai (trung vi qua cau hinh)": doc theo 2 cach - trung vi cua (n_O / n_goc) va (trung vi n_O) / (trung vi n_goc) - lay
    cai NHO HON (bat loi); "moi fold" gom DEV, F1, F2, F3 (bat loi: them DEV).
15. (d) dung top-20 = 20 cau hinh hop le diem cao nhat (ADD1 B cua B1 = 'top20_valid'); top20_rule (co cao nguyen) chi bao them.
16. So cau hinh hop le = luat in-sample B1 (select_b1.rule F1..F3, DD theo DEV). Bien so sanh dung tuyet doi (khong epsilon).
17. report_b2 tren grid_b1 (ban goc) tai lap dung n_valid, chosen, WFO top1/top20 cua levz_b1/out/select_b1.json (da kiem).

## Placebo (placebo_b2.py)
18. Chi chay khi report_b2.json ghi pass_a_to_d = True cho O (--force chi de thu, ghi file *_FORCE, PASS luon False).
19. Mau 300 cau hinh: 25 / tang W x E x z_min, seed 20261126 (grid_b2.sample300, dung chung kiem NONE). Thong ke = ti le cau hinh co F2_ret > 0,
    tinh bang port.run chi fold F2 (da test: == grid_b1 F2_ret). Gia tri that cross-check == grid_b2_<O>.parquet F2_ret.
20. GATE: MOT do lech d ~ U{720 .. NH-720} gio moi luot (dung chung moi lop / cau hinh), dich vong tren toan chuoi 2021-12-01..2025-12-31
    (NH = 35 808) => ti le mo tren vong giu nguyen tuyet doi; tren rieng F2 chi giu xap xi.
21. FILTER: moi luot, moi thang lich m: hoan vi ngau nhien cac coin thuoc U o it nhat 1 gio cua thang; ung vien (k, c) nhan gia tri loc cua
    (k, pi_m(c)). Giu NGUYEN so coin qua loc moi gio trong tap coin cua thang (test); ti le bi loai TREN UNG VIEN chi giu xap xi (bao kept_frac).
22. Seed placebo 20261128; luot r cua O: default_rng([20261128, chi so O trong OPTS, r]). p = #(stat_r >= stat_that) / 500; nguong 0,05 / 12.

## CAN MASTER QUYET
A. G_BRhi / G_BRlo SUY BIEN tren du lieu that (mo ta, khong loi nhuan): BRmed = 0 o 100 % gio 2022-2023, 96 % 2024, 77 % 2025 (LEV
   z >= 2,5 rat hiem => BR = 0 phan lon thoi gian). Va moi ung vien E0 tu no lam BR > 0. Ket qua: G_BRhi mo 84-100 % thoi gian, chan <= 0,6 %
   ung vien (W7 E0 z2,5); G_BRlo chan 99-100 % ung vien. Da cai DUNG CHU prereg (>= / <). Neu muon gia thuyet "do rong LEV" co nghia can
   doi dinh nghia (vd BR theo z thap hon, hoac so sanh > thay >=) - la DOI LUAT, MASTER quyet TRUOC khi chay.
B. Placebo FILTER "giu ti le bi loai": cai = giu dung tren (coin cua thang x gio) (hoan vi nhan coin, dung chu prereg); KHONG giu dung tren
   tap ung vien. Phuong an khac: hoan vi nhan loc giua cac UNG VIEN trong thang (giu dung ti le tren ung vien nhung khong con la "nhan coin").
C. F_FHI dung f = r8 (quy ve 8 h, nhu LEV); phuong an khac = rate tho cua ky (khac voi coin ky 4 h / 1 h).
D. EWr: coin thieu gia bi bo khoi trung binh (khong chan); phuong an khac: can >= x % universe co gia.
E. BR: cua so gom gio t va LEV khong doi u tai gio LEV; phuong an khac: k-24..k-1 / doi u.

## VONG 2 - PREREG_LEVZ_B2_ADDENDUM1 (d1241f48) da chot A-E
- A: giu dung chu (BRhi / BRlo suy bien van chay; Bonferroni / 12). C, E: nhu da cai (muc 4, 7).
- D (da cai, mkt.ewr): coin thieu gia tai t hoac t - n bi bo; EWr = NaN (=> gate DONG) neu so coin co du 2 gia < 50 % #U[k] (bien: dung 50 %
  van nhan). Du lieu that: KHONG gio nao bi anh huong (0 gio doi gia tri o EW3 / EW7 / EW14; do phu thap nhat trong cac gio co gia tri = 63,8 %);
  work/mkt.npz dung lai cho noi dung TRUNG BYTE (sha256 khong doi).
- B (da cai, opts.draw_filter_perm + placebo_b2): ti le loai thuc te tren tap ung vien = gop 12 lop (moi dong ung vien cua cand_b1, ca DEV) voi
  mat na hoan vi; lech > 20 % tuong doi so voi ti le loai that (cung cach gop) => bo luot rut, rut lai tu CUNG dong rng (tat dinh theo seed);
  bien |ex - that| = 20 % van nhan; that = 0 => chi nhan 0; toi da 1 000 lan rut / luot roi bao loi. Ghi moi luot: ex_rate, n_redraw; tong:
  n_redraw_total, ex_rate_minmax, real_ex_rate (out/placebo_b2_<O>.json). GATE khong doi.
