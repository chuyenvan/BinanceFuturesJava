# PROGRAM_OPT - du lieu QUYEN CHON (options) lam kenh tin hieu moi (28/11/2026, MASTER viet TRUOC khi co bat ky so ket qua nao)

Owner 28/11: "thu cho he long short btc 1 kenh moi va thu cho ca he long hien tai xem co filter hoac traling, dca duoc gi khong
nhe. nhung toi can ban giao agent lam ki tranh tiec kiem hoac qua loa bo mat nhung gia tri nho co the tao len khac biet nhe".
Rang buoc: KHONG mua du lieu. Khao sat nguon: ~/claude_master/w3/opt_scope/SCOPING_OPT_1128.md.

## R - luat chung
R0 HOLDOUT: nghien cuu KHONG doc du lieu thi truong / ket qua >= 2026-01-01 00:00 UTC. Keo du lieu dung o 2025-12-31 23:59:59.
   Du lieu collector thu tu nay ve sau (C0) khong duoc doc trong chuong trinh nay.
R1 NHAN QUA: luoi quyet dinh theo GIO (dau gio UTC). Dac trung tai gio t chi dung trade co timestamp < t - 5 phut va nen DVOL
   da dong <= t. Kenh A: lenh thuc hien tai close 1 phut dau tien >= t. Kenh B: gio quyet dinh k cua mot cum = moc gio da dong
   gan nhat TRUOC phut vao leg dau.
R2 KHONG NGUONG CUNG: moi dac trung x duoc dung duoi dang truot: z90 = (x - trung binh 90 ngay) / do lech 90 ngay (shift 1 gio,
   can >= 30 ngay lich su); duoi = phan vi truot 365 ngay (can >= 90 ngay): q10 / q90 cua x.
R3 VE SINH (quyet dinh KHONG nhin ket qua): dac trung bi loai neu ti le gio khong NaN < 80 % trong 2021-04-01..2025-12-31; bao.
R4 SUY DIEN: doi chung bao toan cau truc = DICH VONG chuoi dac trung theo thoi gian (offset ngau nhien deu trong [30 ngay,
   N - 30 ngay], 2 000 luot, cung mot offset cho moi seed); p hai phia cho quet. Hieu chinh da kiem dinh BH-FDR trong TUNG ho.
   NHAT QUAN = cung dau o >= 4 / 5 nam (kenh A: 2021..2025) hoac >= 3 / 4 nam (kenh B: 2022..2025).
R5 HAI BAC (de khong bo mat gia tri nho): BAC-1 = q <= 0,10 va NHAT QUAN. BAC-2 = (q <= 0,25 hoac p tho <= 0,05) va NHAT QUAN -
   ghi vao danh sach theo doi kem co hieu ung + khoang tin cay; chi duoc dung trong phep kiem TO HOP (dau lay tu fold train).
   Con lai = KHONG. Khong them dac trung / nguong / horizon sau khi thay so; muon them phai ERRATA truoc khi chay.
R6 QUY TRINH: DEV (Opus) -> A1 code (Opus khac) -> RUN (Sonnet, kiem sha, khoa --real I_HAVE_A1_PASS) -> A1 ket qua (Opus khac)
   -> MASTER commit + bao owner. Moi buoc keo / dung du lieu co A1 du lieu rieng. Bao ca co hieu ung nho + khoang tin cay,
   khong chi "dat / truot". So in-sample luon dan nhan.

## O - du lieu + dac trung (dung chung hai kenh)
O0 Keo: (a) Deribit DVOL BTC, ETH theo gio 2021-03-24..2025-12-31; (b) Deribit moi lenh khop OPTION cua BTC (tu 2019-01-01) va
   ETH (tu 2019-04-01) den 2025-12-31 (host history.deribit.com), giu du truong (iv, mark_price, index_price, direction, amount,
   instrument, trade_seq, block_trade_id, combo_id, liquidation, tick_direction); kiem day du bang trade_seq lien tuc theo
   instrument; (c) Binance Vision option EOHSummary 2023-05-18..2023-10-23 (doi chieu); BVOLIndex rut gon theo gio (doi chieu);
   (d) gia + funding BTCUSDT, ETHUSDT perp Binance (kline 1 gio + 1 phut neu thieu, funding) 2019-12..2025-12.
O1 Dac trung theo gio cho c trong {BTC, ETH} (cua so 24 gio truot tru khi ghi khac; delta Black-Scholes tu iv cua chinh trade,
   index_price, strike, thoi gian con lai, lai suat 0):
   f01 dvol; f02 atm_s / f03 atm_m / f04 atm_l = trung vi iv cac trade |delta| trong [0,40; 0,60] voi ky han 1-7 / 20-45 /
   60-120 ngay (>= 20 trade, khong du thi mo rong 72 gio, van khong du = NaN); f05 skew_s / f06 skew_m = trung vi iv put delta
   [-0,35; -0,15] tru trung vi iv call delta [0,15; 0,35] (cung ky han); f07 term = atm_s - atm_l; f08 vrp30 = dvol - RV30
   (RV = do lech chuan loi suat log 1 gio, nam hoa, 30 ngay); f09 vrp7 = atm_s - RV7; f10 pcr_vol = khoi luong put / call (don
   vi coin); f11 pcr_prem = theo phi quyen chon; f12 dflow = tong(dau nguoi chu dong x amount x delta) / trung binh |.| 30 ngay;
   f13 vflow = tuong tu voi vega; f14 putbuy = (put mua chu dong - put ban chu dong) / khoi luong put; f15 block = ti le notional
   lenh block; f16 liq = so trade thanh ly; f17 dvol_chg24 / f18 dvol_chg72 = thay doi dvol 24 / 72 gio. Cheo: f19 = dvol ETH /
   dvol BTC. Tong 18 x 2 + 1 = 37 dac trung; bien kiem dinh = z90 cua tung dac trung (R2).
O2 Kiem dac trung (khong dung ket qua): atm_m so voi DVOL (tuong quan, do lech); skew / atm tu trade so voi bang Binance EOH
   2023 (bid / ask that) va voi anh chup Tardis ngay 1 moi thang (neu tai rut gon duoc); bao do tin cay tung dac trung.

## A - kenh moi: he LONG / SHORT BTC (BTCUSDT perp, 1x, phi 0,07 % / chieu, funding that)
A1 QUET thong tin (mo ta co kiem dinh): 37 dac trung x horizon {4, 24, 72, 168} gio x 4 thong ke: (i) IC Spearman giua z90 tai
   t va loi suat log BTC t -> t + h; (ii) chenh trung binh loi suat thap phan vi cao nhat tru thap nhat; (iii) duoi tren: loi
   suat khi x >= q90 tru vo dieu kien; (iv) duoi duoi: x <= q10 tru vo dieu kien. Lay mau moi 8 gio (00, 08, 16 UTC). Giai doan
   chinh 2021-04-01..2025-12-31; mo rong 2020-01-01.. cho dac trung khong can DVOL (bao rieng, khong vao FDR). Ho FDR = 592.
   Lap lai y het voi ETH lam bien phu thuoc (bao rieng, ho FDR rieng).
A2 HE (chi chay sau A1; khuon chot tu bay gio): vi the trong {-1, 0, +1}; (a) he don: moi dac trung BAC-1; (b) TO HOP: trung
   binh cong z90 (dau theo fold train) cua moi dac trung BAC-1 + BAC-2; vao khi |diem| vuot phan vi truot q trong {0,80; 0,90;
   0,95} (365 ngay); giu H trong {24, 72, 168} gio; SL trong {khong, 5 %, 10 %}; khong chong lenh. WFO mo rong: nam kiem 2022,
   2023, 2024, 2025 (chon tren du lieu < nam do; hang xom >= 60 % duong). Tieu chi DAT: lai rong > 0 o >= 3 / 4 nam kiem; Sharpe
   ngay ngoai mau >= 0,7; maxDD <= 25 %; >= 60 lenh; p dich vong (ca quy trinh) <= 0,05; bo 5 % lenh loi nhat van > 0; tuong
   quan voi mua-va-giu BTC |rho| <= 0,5 hoac alpha hoi quy > 0 co y nghia. Bao kem: mua-va-giu, va he long hien tai (mo ta).

## B - he LONG hien tai (alt sau sap): filter / trailing / DCA theo trang thai quyen chon
Du lieu ket qua: cum lenh tu ledger sim 4 seed DEV (~/claude_master/w3/p15_stab/s2/k/c0s{42,7,123,13}) va lap lai tren baseline
r1-a3 hai seed (A1, S7) - ket luan can CUNG DAU tren ca hai bo. Dac trung thi truong => phu 100 % cum.
B1 FILTER: voi tung dac trung (37): (i) IC Spearman z90 tai k voi loi suat cum; (ii) cum co x >= q90 so voi phan con lai;
   (iii) cum co x <= q10 so voi phan con lai. Ho FDR = 111. Kiem dong gop RIENG: lap lai voi phan du cua dac trung sau khi hoi
   quy len [loi suat BTC 24 gio, RV7 BTC, so cum vao trong cung gio] (bao rieng). Muc NGAY: PnL theo ngay vao lenh voi dac trung
   luc 00:00 UTC (co che co ngay giong X14). Uoc tho tac dong PnL / maxDD khi bo nhom xau (ghi ro bo qua phan hoi slot).
   TO HOP: diem = trung binh z90 BAC-1 + BAC-2 (dau tu fold train), WFO 2023 / 2024 / 2025: bo cum co diem xau nhat 10 % / 20 %.
B2 TRAILING va B3 DCA: phan thuc te (tham so DCA / trailing / time-stop dung cua he, cach gan co ngay vao sim Java, du lieu
   duong gia 1 phut cua tung cum) duoc khao sat truoc; chi tiet kiem dinh ghi trong ADD1 TRUOC khi chay. Khung: do MFE / MAE /
   muc tra lai / thoi gian hoi cua tung cum theo trang thai (5 dac trung: dvol, atm_s, term, skew_s, vrp30 cua BTC + moi dac
   trung BAC-1 cua B1); phep kiem TUONG TAC: (arm, gap) tot nhat va loi ich cua leg DCA co khac nhau giua cac tam phan vi trang
   thai vuot qua doi chung dich vong khong.
B4 XAC NHAN bang sim Java (Kaggle, driver da audit) chi cho bien the co BAC-1 o B1-B3; prereg rieng truoc khi chay.

## C - thu thap ve sau
C0 Collector chup toan bo chuoi quyen chon Deribit moi gio (get_book_summary_by_currency: BTC, ETH, USDC) ~1,9 GB / nam: viet +
   A1 audit, chi BAT khi owner duyet (tien trinh thuong truc tren Oracle).

## Dung som
Sau A1 va B1: neu KHONG co dac trung BAC-1 nao va phep TO HOP khong vuot doi chung => bao owner, de nghi dung (giu collector).
