# A1_S2_RESULT - audit doc lap KET QUA tang S2 (LEVZ short) - 2026-11-26
Agent A1 (khong viet code, khong audit code). Code doc lap cua A1 (tu cai lai luat chon select_b1: valid/score/plateau/neighbours; chi goi
port.run, exits.compute cua B1 va rand_s2.one_rep cho viec chay lai rand). Khong goi grid_s2/select_s2/report_s2 de tinh so.

## KET LUAN: XAC NHAN. "Ca 4 tap KHONG HON D0" la DUNG.
SHA khop: grid_s2 afbda276, select_s2 65537e65, rand_s2 32b3472d, REPORT_S2 1839ad79 (report_s2.json = 09ec9339, khong co sha doi chieu).

## 1. Tinh lai tu grid_s2.parquet (lech = 0 o moi o, sai lam tron < 5e-4)
| tap | frac_pos Y22/Y23/Y24/Y25 | trung vi luoi Y23/Y24/Y25 | WFO top-20 2023/2024/2025 | top-1 2023/2024 |
|---|---|---|---|---|
| REF | 0.957/0.662/0.487/0.974 | 0.0327/-0.0016/0.1644 | khong/khong/khong | - |
| P5  | 1.000/0.000/0.207/0.287 | -0.1973/-0.0951/-0.0732 | -0.3918/khong/khong | -0.535 (cfg 728) |
| P5b | 0.993/0.034/0.108/0.079 | -0.1131/-0.1499/-0.1469 | -0.3257/-0.0789/khong | -0.501 (1558) / -0.051 (1642) |
| P6a | 0.949/0.338/0.019/0.554 | -0.0880/-0.1840/0.0140 | -0.3056/-0.2146/khong | -0.314 (1937) / -0.235 (1834) |
| P6b | 0.824/0.431/0.029/0.379 | -0.0359/-0.2645/-0.0503 | -0.1764/-0.2781/khong | -0.338 (2652) / -0.303 (2419) |
Top-1, danh sach passing20, n_valid: trung TUYET DOI select_s2.json o ca 15 (tap, nam).

## 2. Chay lai port.run (B1) tren cand_s2 + exits_s2: 13 cau hinh (top-1 WFO + ngau nhien; REF 2 ngau nhien) x Y22..Y25 = 52 o
ret: lech max 1.4e-15; so lenh: lech 0 / 52; maxDD worst: dinh nghia B0 _maxdd (dinh = equity close cac gio TRUOC) - cong thuc doc lap
cua A1 (dinh gom gio hien tai) khop 51/52, o con lai lech 3.2e-4 do khac dinh nghia, khong phai loi.

## 3. Vi sao "khong cham duoc" (dem so cau hinh /585; gop = min qua fold train, ERRATA1 E4)
- REF: Y22 moi cau hinh chi 5 lenh (max 5) < 30 => 0 hop le moi nam (dung du bao F2).
- P5 2024: Y23 co 0/585 cau hinh lai => 0 hop le. 2025: Y23 van 0 lai => 0.
- 2025 (train Y22+Y23+Y24, can ret > 0 CA 3 nam): P5b 4 cau hinh co lai ca 3 nam, 4 hop le, plateau 0 qua; P6a 4 co lai ca 3 nam, maxDD > 30 % => 0
  hop le; P6b 8 co lai, 3 hop le, plateau 0 qua. Nut that: so cau hinh lai o Y24 chi 63 / 11 / 17 (P5b / P6a / P6b) va giao voi Y23 gan rong.
- Voi P5b/P6b 2025 bi chan boi PLATEAU (>= 60 % lang gieng lai ca 3 nam), khong boi so lenh.
=> He qua DUNG cua luat (E1 + E4 + plateau select_b1), KHONG phai loi. Dieu kien so lenh >= 30 khong rang buoc tap moi nao (n trung vi 102-221).

## 4. p_wfo (ERRATA2 F1) tu 500 part
500 file, 500 dong, 0 trung (tap, luot); moi tap 100 luot, rep 0..99. p_wfo: P5 0.96 (chi tren 2023), P5b 0.59, P6a 0.43, P6b 0.32, REF NaN - khop report.
Chay lai 5 luot tren Oracle (P5#17, P5b#63, P6a#5, P6b#88, REF#41) bang rand_s2.one_rep: 13/13 truong khop tung so voi part Kaggle.
Ghi chu: luot ngau nhien cham duoc 2025 o 16-49 % luot/tap; tap that 0 % -> tap that KHONG tot hon short ngau nhien.

## 5. Tinh hop le
close1m.npy = 2 148 480 phut = dung toi 2025-12-31 23:59; FR/hourly dai NH = 35 808 gio => khong the doc gia/funding >= 2026.
Gio vao lon nhat 2025-12-31 16:00; gio thoat lon nhat trong bang = NH (bar 23:59 dong luc 00:00 2026-01-01; trong port fold Y25 kl=NH-1 => eod).
52 ledger: moi lenh ke in [k0, kl), kx <= kl, ke_min/kx_max nam trong nam fold; moi (ke, c, cid) thuoc dung tap ung vien.

## 6. 2022 lai gan het, 2023-2025 lo: dac tinh hay loi?
Khong phai loi dau. (a) REF di cung pipeline (da khop B1) co hinh dang KHAC: 2025 lai 97 % cau hinh, trung vi +0.164. (b) Loi suat net
moi lenh (tat ca ung vien, khong qua danh muc) vs 400 short ngau nhien (coin, gio) / nam, cung bang thoat B1:
SL30/H72: RAND 2022..2025 = +0.43 / -1.25 / +0.22 / +0.99 %; du (tap - RAND) P5 +3.6/-1.1/-2.4/+0.5; P5b +3.2/-1.7/-2.0/+0.5;
P6a +2.7/-0.2/-1.2/+0.1; P6b +1.7/+0.3/-1.2/+0.2; REF +9.6/+2.3/-1.4/+4.1 (pp/lenh).
SL50/H720: du P6a/P6b 2025 = -5.2/-5.2 pp; SL15/H168/trail 5-3: du moi tap moi 2023-2025 am (-0.1..-1.8 pp).
EW alt (B1 ew_alt_daily) theo nam: 2022 -82 %, 2023 +107 %, 2024 +6 %, 2025 -71 %.
Ket luan: sau khi tru short ngau nhien cung nam, tap moi DUONG o 2022, AM o 2023 va 2024 (moi tap, moi bo thoat do), 2025 ~0 den am. 2025 la nam
alt giam manh ma tap moi van lo/hoa => KHONG chi la beta am; tin hieu co "edge" doi dau theo nam, khong on dinh. (Han che: ung vien lien gio cung
coin chong nhau => se that lon hon so in; random dan deu thoi gian, khong khop phan bo thoi diem.)

## 7. DUOC / KHONG DUOC noi voi owner
DUOC: 4 tap moi truot S-a (moi trung vi top-20 cham duoc deu am), S-b (chi Y22 >= 50 %, P6a them Y25 0.55 => <= 2/4 nam), S-c (p_wfo 0.32-0.96);
so nam cham duoc P5 1, P5b/P6a/P6b 2, REF 0; ti le cau hinh lai va trung vi luoi tung nam (so mo ta, ca luoi); "2025 khong tap nao chon duoc cau
hinh tu 2022-2024"; so doi chieu REF lay tu B1 (2024 -23.0 %, 2025 +6.1 %) kem ghi chu quy trinh khac.
KHONG DUOC: coi nam khong cham duoc la 0 hay cong vao tong; dung DEV/p_max (in-sample) lam bang chung; noi "2022 tap moi co edge" (nam train,
in-sample cho chon); trich trung vi luoi 2025 duong cua P6a (+0.014) / REF (+0.164) nhu ket qua WFO; dung so du-lenh muc 6 (ngoai prereg, mo ta
A1) nhu tieu chi; noi "chi la beta" (so lieu bac bo).

## 8. Chua kiem
Xay dung cand_s2 (tin hieu P5/P5b/P6, nhan qua) va bang exits_s2 (khong tinh lai ngoai 5 luot rand); fold DEV; S-d/S-e (vo nghia khi S-a truot);
bao cao mo ta muc 6 prereg trong REPORT_S2; sha report_s2.json.
