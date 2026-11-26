# PREREG_FX_G1_FINAL - CARRY G10 + GATE BIEN DONG ROLLING (NGHIEN CUU TREN GIAY)
Soan: agent theo chot cua MASTER 2026-11-26. MASTER commit. Khong giao dich that (phap ly VN: FX_SURVEY.md muc D).
Nhan nguon: [K] = da mo trang nguon / ket qua tu chinh domain nguon ngay 2026-11-26; [KS] = qua snippet / ben thu ba;
CAN KIEM KHI TAI DU LIEU = agent tai du lieu phai xac nhan (kem cach kiem) truoc DEV.
## 0. Boi canh + tien nghiem
- Chi dao owner (nguyen van bo dau): "them huong nghien cuu thi truong forex tim noi lay du lieu free va su dung cac ki nang tren mang
  cung nhu cac phuong phap dang co gia tri cua he dang co". Khao sat: ~/claude_master/w3/fx/FX_SURVEY.md.
- Tien nghiem: carry co premium nhung lech am, sap khi VIX / thanh khoan xau (Brunnermeier-Nagel-Pedersen 2008,
  https://www.nber.org/papers/w14473 [K]). Carry G10 sau 2008 duoc cho la yeu [chua co nguon - tri nho] => ky vong THAP; ket qua am la
  hop le. Co che mang tu he long: gate rolling kieu GDV2 (phan vi truot, causal).
- Gia dinh thuc thi: gia FRED H.10 la gia tham chieu TRUA New York (noon buying rate), KHONG phai gia khop that; gia dinh khop tai gia
  do + chi phi muc 4. Du lieu dung den het 2026-10; KHONG dung ngay sau 2026-10-31.
## 1. Du lieu
Ty gia ngay FRED H.10 (Board of Governors; tag "Public Domain: Citation Requested" [K]):
  DEXUSEU (USD/EUR, tu 1999-01-04 [K]); DEXJPUS (JPY/USD), DEXUSUK (USD/GBP), DEXSZUS (CHF/USD), DEXCAUS (CAD/USD),
  DEXUSAL (USD/AUD), DEXUSNZ (USD/NZD), DEXNOUS (NOK/USD), DEXSDUS (SEK/USD): tat ca tu 1971-01-04 [K, ALFRED].
  EUR CHI tu 1999 (KHONG ghep DEM).
Lai suat ngan han (OECD MEI qua FRED; thang, % nam, trung binh thang; trich dan OECD theo ghi chu trang FRED [K]):
  IR3TIB01USM156N [K], IR3TIB01EZM156N [K; EA19, ban nam tu 1994], IR3TIB01GBM156N [K; ban nam/quy tu 1986], IR3TIB01JPM156N [K; CHI
  tu 2002-04], IR3TIB01CHM156N [K ton tai; ban nam tu 2000], IR3TIB01NOM156N [K], IR3TIB01SEM156N [K], IR3TIB01CAM156N,
  IR3TIB01AUM156N, IR3TIB01NZM156N (3 chuoi cuoi: CAN KIEM KHI TAI DU LIEU - mo https://fred.stlouisfed.org/series/<ID>, ghi khoang).
  Thay the: IR3TCD01JPM156N ton tai [K] nhung la lai suat CD (Certificates of Deposit), KHAC dinh nghia interbank => KHONG dung.
  JPY truoc 2002-04 va CHF truoc thang dau co chuoi thang => dong do NGOAI universe giai doan do.
  Ngay ket thuc chuoi OECD: co trang hien so cuoi 2025-03 (GB) va trang khac 2026-01 => CAN KIEM KHI TAI; thang nao thieu => dong do
  ngoai universe thang do (USD thieu => thang do dong het vi the, ghi log).
Bien dong: VIXCLS (FRED, ngay, tu 1990-01-02 [KS - ALFRED]); FX_VOL tu tinh tu cac chuoi DEX* (muc 3).
Doi chieu ty gia thu 2: ECB https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip (CSV, tu 1999; URL [KS - thu vien R bbk va
  Go dung cung URL]; trang goc [K]: https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html).
## 2. Danh sach tai du lieu (agent tai lam dung; ghi provenance: URL, thoi diem tai, sha256, so dong, ngay dau / cuoi)
- FRED CSV moi chuoi: https://fred.stlouisfed.org/graph/fredgraph.csv?id=<ID> (dang URL CAN KIEM KHI TAI; neu loi dung FRED API
  https://api.stlouisfed.org/fred/series/observations?series_id=<ID>&file_type=json voi key mien phi do OWNER tao - agent khong dang ky).
  ID: DEXUSEU DEXJPUS DEXUSUK DEXSZUS DEXCAUS DEXUSAL DEXUSNZ DEXNOUS DEXSDUS VIXCLS
      IR3TIB01USM156N IR3TIB01EZM156N IR3TIB01GBM156N IR3TIB01JPM156N IR3TIB01CHM156N IR3TIB01CAM156N IR3TIB01AUM156N
      IR3TIB01NZM156N IR3TIB01NOM156N IR3TIB01SEM156N
- ECB: eurofxref-hist.zip (URL tren).
- Cat moi chuoi o 2026-10-31. Luu vao thu muc du lieu rieng (khong trong repo code); file chi doc sau khi tai.
- Bao cao tai du lieu: bang (ID, ngay dau, ngay cuoi, so quan sat, so ngay thieu ".") + so dong tien hop le moi nam.
## 3. Kiem cheo + ngay nghi / thieu
- FRED vs ECB (1999+): USD/xxx tu ECB = (EUR/xxx)/(EUR/USD); |log(FRED) - log(ECB)| > 1,5 % cung ngay => co (lech gio chot 14:10 CET vs
  trua NY la binh thuong). Bao ti le co theo cap x nam; cap-nam co > 0,5 % ngay bi co => MASTER xem tay truoc DEV.
- FRED "." = thieu. Danh gia MTM dung gia hop le gan nhat <= 3 ngay lam viec; khong khop lenh ngay thieu -> ngay hop le ke tiep;
  thieu > 3 ngay lien tiep => dong tien do ngoai universe thang do (log).
## 4. Universe + chia thoi gian
- Toi da 9 dong tien vs USD: EUR (tu 1999), JPY (tu 2002-04 theo lai suat), GBP, CHF (theo chuoi thang), CAD, AUD, NZD, NOK, SEK.
  Universe THAY DOI theo thang = dong co ca ty gia va lai suat thang m-1. Bao so dong tien moi nam. Can 2k <= so dong tien:
  thang co < 6 dong => cau hinh k=3 KHONG giao dich thang do; < 4 dong => k=2 cung khong (log).
- TRAIN 1994-01..2005-12; WFO 2006-01..2019-12 (hai nua: 2006-2012, 2013-2019); HOLDOUT 2020-01..2026-10, mo MOT lan sau dong bang,
  owner duyet.
## 5. Tin hieu + luat (chot; 12 cau hinh)
- Tai can bang: ngay lam viec cuoi thang m. d_i = r_i - r_USD, r la lai suat THANG m-1 (chong nhin truoc: OECD la trung binh thang,
  cong bo sau). Long k dong tien d cao nhat, short k dong tien d thap nhat (vs USD); trong so deu 1/(2k) moi chan; gross = 1.
- Gate (causal, kieu GDV2): v_t = FX_VOL = trung binh deu vol thuc 21 ngay (std log-return ngay x sqrt(252)) cua cac dong tien trong
  universe, hoac v_t = VIXCLS. q_t = phan vi q cua v trong N nam TRUOC t (khong gom t). Kiem tra moi ngay: v_t > q_t => dong het (flat,
  tien USD lai 0). Mo lai chi o lan tai can bang ke tiep neu v <= q. Thieu du N nam lich su v => gate OFF giai doan do (ghi ro).
- Luoi: k {2,3} x gate {OFF; FX_VOL q0,80 N3; FX_VOL q0,90 N3; FX_VOL q0,80 N10; FX_VOL q0,90 N10; VIX q0,90 N3} = 12 cau hinh.
- Luat chon cau hinh (chot): Sharpe TRAIN (sau chi phi) cao nhat trong 12; hoa => k nho hon, roi gate OFF truoc. Bao KEM trung vi 12
  cau hinh tren WFO. Khong chon lai trong WFO.
## 6. Chi phi (chot; kich ban xau = x2 moi khoan)
- Spread + commission KHU HOI: EURUSD 0,8 pip (IC Markets Raw: spread TB 0,1 pip + $7/lot round turn, https://icmarkets.com/en/trading-accounts/raw-spread-account [K]).
  Cac cap khac: KHONG co so trong khao sat => 3 pip khu hoi (GIA DINH BAO THU), doi ra bp theo gia tai thoi diem giao dich.
- Swap/carry: moi ngay lich (r_long - r_short)/360 tren notional moi chan, TRU bien broker 1,0 %/nam tren MOI chan; r = thang m-1.
  Tan suat thang tinh theo ngay lich => khong can mo hinh rieng "thu 4 x3" (ghi ro).
- Truot: khong them ngoai spread (gia dinh FRED + spread bao thu); lenh dong do gate: chi phi spread x2.
## 7. Thuoc do + doi chung
- Loi suat vuot troi nam hoa (so voi USD lai 0 - ghi ro), Sharpe, maxDD (MTM ngay), Calmar, skew thang, thang te nhat, ti le nam duong,
  turnover/nam, % thoi gian gate dong, so dong tien / nam.
- Bao HAI so: TRAIN (in-sample) va WFO; ca 12 cau hinh + cau hinh chon + trung vi.
- Doi chung: (a) mua-giu ro deu cac dong tien vs USD; (b) cung k khong gate; (c) NGAU NHIEN >= 500 luot: moi thang chon ngau nhien
  k long / k short trong universe thang do, cung tan suat, cung so chan, cung do giu, cung gate + chi phi => p = ti le >= that.
- On dinh: bo 5 % thang tot nhat; chi phi x2.
## 8. Tieu chi (tren WFO, cau hinh chon bang TRAIN)
 D1 Sharpe WFO sau chi phi > 0,3.
 D2 p doi chung ngau nhien (c) <= 0,05 (>= 500 luot).
 D3 maxDD WFO <= 25 %.
 D4 >= 60 % trong 12 cau hinh co loi suat WFO > 0.
 D5 gate cai thien Calmar so voi cung k khong gate o CA HAI nua WFO (2006-2012, 2013-2019). (Neu cau hinh chon la gate OFF: D5 xet
    cau hinh gate tot nhat TRAIN cung k - ghi ro.)
 D6 bo 5 % thang tot nhat van > 0.   D7 chi phi x2 van > 0.
 Ket luan: du D1-D7 => "DAT" => MASTER de nghi owner mo HOLDOUT (tieu chi HO chot truoc khi mo). Dat D1 + D2 (khong du) =>
 "CO TIN HIEU, CHUA DU". Con lai => "KHONG DAT". Bao so that, khong doi luat sau khi thay so.
## 9. Rui ro / gioi han
- FRED la gia tham chieu trua NY, khong bid/ask; chi phi cap ngoai EURUSD la gia dinh. Lai suat interbank OECD chi la proxy swap broker.
- Universe nho va thay doi (TRAIN 1994-1998 khong co EUR, JPY vao 2002) => TRAIN va WFO khong cung tap dong tien.
- ~168 thang WFO, 12 cau hinh => luc thong ke thap; rui ro chon cau hinh.
- Gate co the chi "giam phoi nhiem" -> D5 doc cung Calmar, khong chi return.
## 10. Thu tu thuc hien
1 MASTER commit prereg nay. 2 Agent tai du lieu (Sonnet): muc 2, provenance + sha256, bao kiem cheo muc 3, giai quyet CAN KIEM.
3 MASTER duyet bao du lieu. 4 DEV (Opus): Python offline tren Oracle, logging, flock oracle_heavy.lock neu nang; test nhan qua:
  (i) assert tin hieu thang m chi dung lai suat <= m-1 va gia <= ngay can bang; (ii) q_t khong gom t; (iii) doi chieu tay 1 thang
  (2008-10: universe, xep hang, trong so, PnL, chi phi). 5 A1 audit code (agent khac). 6 RUN TRAIN + WFO (khong cham >= 2020).
7 A1 audit ket qua. 8 MASTER tu kiem >= 3 so. 9 Bao owner. Dem so cau hinh (12) cho DSR.
