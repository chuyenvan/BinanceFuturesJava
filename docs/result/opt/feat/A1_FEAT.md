# A1_FEAT - kiem toan code doc lap thu vien dac trung PROGRAM_OPT (28/11/2026)
PHAN QUYET: PASS-WITH-MINOR (khong thay nhin-truoc, sai dau, sai don vi, lech luat lam doi ket qua).
File da kiem (sha256 khop SHA256SUMS.txt): optfeat.py b207fd64..cacc, test_feat.py fb732519..dd65, hygiene.py b688f02a..656e,
feat_hourly.parquet 5f3e54fa..3002, FEAT_META.json 44d72dfe, HYGIENE.md 8bdf6bbc, CHOICES_FEAT.md 386ba9c0, DEV_FEAT.md 3615b742.

1. Doi chieu luat: f01-f19 khop O1+E6+C1-C17 (dong code: avail_hour L79-80; derive L82-103; surface_select L217-229 = valid iv[5,400],
   T>0, khong liq, giu block/combo; aggregate L244-252: f10/f11/f15 = moi trade tru liq; f12/f13 = khong block/combo + valid, giu liq;
   f14 = put khong block/combo; f16 = dem liq; ky han theo T con lai tai luc trade, inclusive; pick L287-299 24h->72h; rv L255-264).
   Mo ho duy nhat do duoc: f05/f06 mo rong 72h CHUNG hai chan (C4) vs tung chan: lech 1/59 gio mau (7.5 diem vol). Khong loi.
2. NHAN QUA: DVOL ts = gio MO nen (thuc nghiem: corr dDVOL vs return kline mo cung gio = -0.227 BTC/-0.258 ETH o j=0, j=+1 = 0.003)
   => f01(t)=close nen t-1h la nen da dong. Test doc lap 25 t* (seed 3; 10 truoc 2021-04, 15 sau; BTC+ETH), cua so 40 ngay:
   (b) cat trade ts>=t*-5m, DVOL/kline chua dong; (c) thuoc doc iv x10, amount x10, index x3 trade ts>=t*-5m, DVOL x2, kline x2 sau t*;
   so 22 cot (18 x + n_f02,n_f12,f12_raw,f13_raw) x 169 gio <= t* = 92 950 o moi phep: LECH 0 / 0. transforms (z90,hi,lo,terc)
   tren chuoi x cat tai t*: lech 0. (Cat thuc hien trong bo nho, khong sao raw ra dia - cung phep thu.)
3. Tham chieu doc lap (code rieng, khong import optfeat), 60 gio seed 5, 2019-2025: f02 60/60, f03 55, f05 59, f07 56, f08 40,
   f10 60, f11 60, f12 (raw+chuan hoa) 60, f14 60, f15 60, f16 60, f17 40 => lech lon nhat 7e-12; NaN trung khop 100 %.
4. BS: 500 trade, delta/vega lech max 1e-16, 0 sai dau put. Index vs forward (parity call-put cung strike, +-10 phut): basis nam
   hoa BTC 2021-04-12/13: 100-122 % (1-7d), 68-81 % (7-45d); 2024-03-12/13: 31-44 %. Lech |delta| trung vi: tenor s 0.03-0.05 (2021-04),
   0.008-0.013 (2024-03); tenor m 0.05-0.09; tap ATM doi 10-24 % trade; trung vi IV ATM lech 0.1-2.2 diem vol. LUU Y (dung luat O1).
5. Dot bien: m1 bat (T1,T3); m2 bat (T1); m3 CHI T5 bat; m4 bat (T2,T3,T4); m5 CHI T3 bat; m6 CHI T4 bat (T1/T2/T3/T5 lot);
   m7 bat (T1). Khong dot bien nao lot ca bo test. Lo hong nho: T1 khong bat z90 khong shift va doi dai delta.
6. R3 doc lap: min non-NaN 37 x = 0.944 (ETH f06); BTC f03 0.961, BTC f06 0.952, ETH f04 0.994, BTC f12/ETH f15/BTC f09 1.00 => khong LOAI.
   corr f03~dvol BTC 2021..25: .920 .928 .971 .965 .982 (lech trung vi -8.5 -> -1.9); ETH .961 .952 .977 .953 .900.
   EOH: lag -1/0/+1: f02 .845/.857/.868, f05 .518/.533/.543 (can gio dung; +1 nhinh vi cua so 24h tre). f05 vs EOH chi strike co
   volume>0: .759; them trung binh 24h EOH: .895 (f02: .965) => 0.53 do mark_iv strike khong thanh khoan + cua so 24h, KHONG phai loi.
7. C18 xac nhan: max|z90| 2021-25: f16 101/83, f11 59/63; inf = 0 moi cot (sd=0 -> NaN). Ti le co duoi (ky vong ~0.10):
   f16 lo 0.33/0.30 (gia tri 0 trung, q10=0 => lo gan nhu moi gio liq=0) - co lo f16 VO NGHIA; muc IV co xu huong: BTC f01 lo .29,
   f03 lo .26, f04 lo .30, ETH f01 lo .22, f19 hi .23, BTC f15 hi .19 (phi dung, khong phai loi). Clip z90 [-5,5] an toan.
8. Chay lai lenh DEV vao tmp: data_hash 1c6a9e0b..8d87 = ban luu; 61 368 gio 2019-01-01..2025-12-31 23:00, 0 lo luoi, khong >= 2026.
9. (i) DEV PHAI sua: khong co loi chan. Nen (khong chan): them test T1 cho transforms/delta band (m3/m6 chi 1 test bat).
   (ii) LUU Y: index thay forward lech delta 2021 (basis >60 %) -> atm/skew 2021 lech 1-2 diem vol + tap ATM doi; co lo f16 vo nghia,
   co hi/lo cac muc IV lech xa 10 % do xu huong; z90 DVOL NaN den ~2021-04-23; f05 vs EOH chi 0.53 (nhieu); f03 lech DVOL -8 diem 2021-22.
Gioi han: luc dot bien vo tinh co 4 tien trinh test cung luc (lenh kill bo chay cu bi tu choi) - vuot muc 2 tien trinh ~8 phut.
