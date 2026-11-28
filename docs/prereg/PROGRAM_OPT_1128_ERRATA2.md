# PROGRAM_OPT_1128 - ERRATA2 (28/11/2026 ~22:15 +07). Viet SAU khi du lieu + dac trung + engine qua A1 doc lap, TRUOC khi ghep
voi bat ky loi suat tuong lai / ket qua cum nao. Can cu: opt/A1_DATA.md (PASS-CO-LUU-Y), opt/feat/A1_FEAT.md (PASS-WITH-MINOR),
opt/b/A1_B.md (PASS-WITH-MINOR), feat/out/HYGIENE.md - khong tai lieu nao chua loi suat tuong lai hay ket qua theo nhom.

F1 Vi pham R0 nho (DEV-DATA tu bao, A1 xac nhan): mot zip BVOL ngay 2026-01-05 bi nap vao RAM khi liet ke, khong dong nao duoc
   giu / ghi; code da loc <= 2025-12-31. Hai duong con lai (phan trang delivery price, danh sach instrument) co the dua ban ghi
   2026 vao RAM roi loc truoc khi luu - chap nhan (thuoc tinh hop dong, khong phai gia). Khong dac trung nao dung chung.
F2 R3: khong dac trung nao bi loai (ti le khong NaN thap nhat 94,4 %). Dac trung phu thuoc DVOL co z90 tu ~2021-04-23.
F3 z90 duoi day (f11, f15, f16: |z| toi ~100 khi do lech chuan ~0): thong ke HANG (IC Spearman, co duoi theo phan vi) dung z90
   nguyen; moi cho CONG hoac HOI QUY z90 (to hop, phan du) dung z90c = cat z90 trong [-5, +5].
F4 Co duoi DUOI cua f16 (so trade thanh ly) vo nghia (gia tri 0 trung nhau => q10 = 0, co bat ~30 % so gio): BO phep kiem duoi
   duoi cua f16. Cac co duoi khac giu nguyen dinh nghia (phan vi truot 365 ngay) du ti le bat lech 10 % do phi dung; bao ti le
   bat that kem moi ket qua.
F5 THEM hai dac trung lam tron (quyet dinh tu su that DO TIN CAY, khong tu loi suat: skew_s cua BTC chi tuong quan 0,53 voi be
   mat bid / ask that cua Binance EOH 2023 vi nhieu, len 0,90 khi lay trung binh 24 gio; term 0,66): f20 skew_s72 va f21
   term72 = cung dinh nghia f05 / f07 nhung cua so 72 gio (>= 20 trade moi chan / moi ky han; khong mo rong them). Cho BTC, ETH.
   => 41 dac trung. Ho FDR: A1 = 41 x 4 horizon x 4 thong ke - 8 (F4) = 648 (ETH lam bien phu thuoc: ho rieng 648);
   B1 = 41 x 3 - 2 (F4) = 121.
F6 Delta dung index_price (dung O1), khong dung gia forward cua ky han: khi basis lon (2021) tap trade "ATM" lech 10-24 %, IV
   ATM lech 0,1-2,2 diem vol. GIU dinh nghia; ghi la han che; neu co BAC-1 / BAC-2 o dac trung be mat thi kiem do vung bang
   forward suy tu put-call parity (mo ta, sau).
F7 Quy uoc thoi gian (A1 xac nhan): nen DVOL / kline / EOH ghi ts = dau nen, chi dung duoc tu ts + 1 gio (code da dung). Bang
   instrument la anh chup 2026: chi dung strike / loai / ngay het han. Block / combo: moi leg option mot dong, leg khong phai
   option khong co trong du lieu (452 block BTC, 184 ETH thieu leg) - f15 tinh theo notional cac leg option.
F8 Gia cho kenh A: loi suat A1 tinh tu close nen 1 GIO Binance perp (nen dong tai t va t + h); bo cac gio ma nen 1 gio co
   volume 0. A2 thuc hien tai close 1 phut dau tien >= t co volume > 0 (Vision lap phut thieu bang nen phang volume 0).
F9 Kenh B - phan thuc te bang engine (A1-B):
   (a) Funding: dung fundingRate Binance Vision cho moi cum (sim lay tu Aerospike, khop den sai so float tru LIT: ledger ghi 0
       vi nguon sim thieu LIT). MOC SO SANH = engine chay tham so goc + funding Vision (khong phai PnL ledger).
   (b) Leg DCA goc (-50 / -75 / -90 %) chi duoc phat lai dung thoi diem ledger khi cum con mo; engine KHONG tu sinh DCA sau.
       Cum bi GAN CO "thieu DCA" neu duoi BAT KY bo (arm, gap) / muc x nao trong luoi, cum song qua thoi diem thoat ledger va
       LOW cham gia leg dau x 0,5 truoc khi thoat; cum "bars_end" = con mo sau 45 ngay duoi bat ky bo nao. Phan tich CHINH
       loai cac cum co co nay khoi MOI bo (cung mot tap cum cho ca luoi - khong chon mau theo bo); bao so cum loai; do nhay:
       them lai voi xu ly co hoc.
   (c) DCA nong (E5): bien the CHINH = leg them khop tai OPEN nen ke tiep sau nen co CLOSE <= gia leg dau x (1 - x); bien the
       khop ngay tai CLOSE bao kem la can tren lac quan. Ca hai khong co cong tin hieu / ngan sach U => la can tren ve kha
       nang khop; moi BAC-1 phai qua sim Java.
   (d) 110 cum duy nhat co thoat / leg khac nhau giua cac seed: ket qua = trung binh cac seed (nhu E2 ERRATA1).
F10 B1 "phan du": hoi quy z90c len [loi suat BTC 24 gio truoc k, RV7 BTC tai k, so cum duy nhat co phut vao trong cung gio k].
