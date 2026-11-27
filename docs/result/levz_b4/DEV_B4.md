# DEV_B4 (chua audit) - 2026-11-27 - PREREG_X3_1127 PHAN A
## Lenh (tu ~/claude_master/w3/levz_b4; nice -n 15; moi buoc < 5 phut CPU => khong can lock)
DEV / test (da chay):
- python3 code/exits_b4.py all   -> work/exits_b4.npz (4 792 x 60) + work/hourly_b4_<D1_5|D1_10|D2_5|D2_10>.npz (~83 MB / file); ~60 s
- python3 code/test_b4.py all    -> test a b c d e f g i; ~95 s; logs/test_all3.log
- python3 code/test_b4.py h      -> du lieu GIA dau-cuoi (pump + 20 seed rand); ~8 phut; logs/test_h.log
- gia dau-cuoi tay: python3 code/grid_b4.py --fake pump --seed 1 && python3 code/select_b4.py --fake pump --seed 1 && python3 code/report_b4.py --fake pump --seed 1  (-> out/fake/)
RUN (CHI sau A1 PASS; thu tu; uoc thoi gian):
1. python3 code/exits_b4.py all                                   (~1 phut, neu code / du lieu doi; neu khong dung bang hien co)
2. python3 code/grid_b4.py --real I_HAVE_A1_PASS --nproc 2        (~2-4 phut uoc: 540 cfg x 4 fold, 4 792 ung vien) -> out/grid_b4.parquet
3. python3 code/select_b4.py --real I_HAVE_A1_PASS                (~1 phut) -> out/select_b4.json
4. python3 code/report_b4.py --real I_HAVE_A1_PASS                (giay) -> out/report_b4.{json,md}
## Ket qua test (2026-11-27, chay lai sau ERRATA1 E1)
a PASS: n_add 0 = B1 (8 bo trailing) + T1 (2 bo STATE H168) tuyet doi x 4 792 dong; mang gio NONE = B1 tren 600 dong.
b PASS: vong for tham chieu 600 lenh x 8 cfg = 4 800 (phu 48 cfg DCA) + STATE H72 n_add 0: 300 lenh x 2 SL = 600.
c PASS (12 000 phep doi gia sau phut thoat). d PASS (3 so tay + bien lo). e PASS (240 lan port tren du lieu gia).
f PASS (xem CHOICES #9). g PASS (tat dinh, sha 3f761bef...).
h PASS: pump => ca 4 kieu "DCA DAT" (pipeline noi duoc den "DAT"). Phan rand KHONG do duoc do nhay / bao dong gia
(du lieu rand gan nhu khong co cfg hop le) - KHONG trich so rand lam bang chung (ERRATA1 E2).
i PASS: nhanh ERRATA1 E1 cua V-b (NONE khong cham duoc => moc 0).
## Ve sinh (khong loi nhuan) - so leg khop (trung binh 12 cfg / kieu)
D1_5 1:51,0 % 2:49,0 % | D1_10 1:69,2 % 2:30,8 % | D2_5 1:51,0 % 2:19,3 % 3:29,7 % | D2_10 1:69,2 % 2:16,8 % 3:14,1 %; NaN 0.
