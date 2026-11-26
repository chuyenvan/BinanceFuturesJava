# PREREG_FX_G3_FINAL - VI THE COT (CFTC) LAM TIN HIEU TUAN - "dong long" phien ban FX (NGHIEN CUU TREN GIAY)
Soan: agent theo chot cua MASTER 2026-11-26. MASTER commit. Khong giao dich that (phap ly VN: FX_SURVEY.md muc D).
Nhan: [K] da mo trang nguon / ket qua tu chinh domain nguon 2026-11-26; [KS] snippet / ben thu ba; CAN KIEM KHI TAI DU LIEU.
## 0. Boi canh + tien nghiem
- Chi dao owner (nguyen van bo dau): "them huong nghien cuu thi truong forex tim noi lay du lieu free va su dung cac ki nang tren mang
  cung nhu cac phuong phap dang co gia tri cua he dang co". Khao sat: ~/claude_master/w3/fx/FX_SURVEY.md.
- Tien nghiem: Tornell-Yuan 2012: vi the dau co du bao tiep dien, hedger du bao dao chieu (https://econpapers.repec.org/RePEc:umb:econwp:09116 [K]);
  Bundesbank DP 41/2015: vi the dau co EUR di theo gia [KS]. He crypto: positioning (crowded-long, funding factor, LEVZ OI+funding)
  NO-GO / dao dau giua nam => ky vong THAP. Chi dung LUAT, khong model.
- Gia dinh thuc thi: gia FRED H.10 la gia tham chieu TRUA New York (khong phai gia dong cua / gia khop); khop tai gia do + chi phi.
  Du lieu den het 2026-10; khong dung ngay sau 2026-10-31.
## 1. Du lieu
- CFTC COT [K]: du lieu chot THU 3, cong bo binh thuong THU 6 15:30 ET; lich su khong sua lai.
  https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm ; trang file: https://cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm
  * Legacy futures-only (tu 1986): https://www.cftc.gov/files/dea/history/deacot1986_2016.zip va deacotYYYY.zip cho 2017..2026 [K: mau
    deacot2020.zip]; nhom Non-commercial (ten cot cu the CAN KIEM KHI TAI: doc header file).
  * TFF futures-only (tu 2006-06-13): https://www.cftc.gov/files/dea/history/fin_fut_txt_2006_2016.zip va fut_fin_txt_YYYY.zip cho
    2017..2026 [K: mau fut_fin_txt_2020.zip - chu y thu tu "fin_fut" / "fut_fin" khac nhau]. Cot [K, https://cftc.gov/node/129081]:
    Report_Date_as_MM_DD_YYYY, CFTC_Contract_Market_Code, Open_Interest_All, Lev_Money_Positions_Long_All / Short_All,
    Asset_Mgr_Positions_Long_All / Short_All (ten cot chinh xac doi chieu header khi tai).
- Hop dong CME da xac nhan (ten + ma tren trang CFTC) [K]: EURO FX 099741 (bang strike-price CFTC); BRITISH POUND STERLING 096742;
  CANADIAN DOLLAR 090741; SWISS FRANC 092741 (bao TFF 2021-09-28 tren cftc.gov); AUSTRALIAN DOLLAR 232741 (bang strike-price CFTC).
- CAN KIEM KHI TAI DU LIEU (khong doan): JAPANESE YEN 097741 va NZ DOLLAR 112741 (ma thay tren cftc.gov / ten chi qua ben thu ba);
  cach kiem: loc file theo CFTC_Contract_Market_Code, doc cot Market_and_Exchange_Names, phai la "JAPANESE YEN - CHICAGO MERCANTILE
  EXCHANGE" / "NZ DOLLAR - CHICAGO MERCANTILE EXCHANGE"; khong khop => loai dong tien do. Ma cua cac hop dong o Legacy 1993-2005 co the
  khac (EUR chi tu 1999; truoc 1999 KHONG ghep DEM) => agent lap bang (ma, ten, ngay dau, ngay cuoi) tu chinh file, MASTER duyet.
- Gia: FRED DEXUSEU (tu 1999-01-04), DEXJPUS, DEXUSUK, DEXSZUS, DEXCAUS, DEXUSAL, DEXUSNZ (tu 1971-01-04) [K]. Kiem cheo ECB
  eurofxref-hist.zip + quy tac ngay nghi / thieu: nhu PREREG_FX_G1_FINAL muc 3. Lai suat cho swap: chuoi OECD nhu G1 muc 1
  (dong tien thieu lai suat => khong giao dich dong tien do giai doan do, log).
## 2. Ngay cong bo (chong nhin truoc) + cong bo tre
- Lay lich cong bo THAT tu nguon chinh thuc CFTC (trang Release Schedule / thong bao). Cong bo tre do dong cua chinh phu: 10-12/2025
  (vd bao cao 2025-09-30 cong bo 2025-11-19, het ton dong ~2025-12-29 [KS - mondovisione dan CFTC]); 10/2013 va 12/2018-01/2019 (lich
  cong bo that CAN KIEM KHI TAI).
- Tuan cong bo tre: LOAI khoi tin hieu (khong gia dinh ngay). Lenh vao tai gia FRED cua ngay lam viec DAU TIEN SAU ngay cong bo that
  (binh thuong thu 6 => thu 2).
- Neu KHONG lay duoc lich cong bo that tu nguon chinh thuc: quy tac bao thu = bao cao thu 3 chi duoc dung tu thu 2 TUAN SAU (t+6 ngay),
  va loai toan bo cac khoang dong cua da biet (2013-10-01..2013-10-16; 2018-12-22..2019-01-25; 2025-10-01..2025-11-12) + cac bao cao co
  ngay chot nam trong / ngay truoc khoang do ma cong bo bi day lui (tim tu thong bao CFTC; khong tim duoc => loai 8 tuan sau moi khoang).
## 3. Universe + chia thoi gian
- Dong tien = cac hop dong xac nhan o muc 1 (toi da 7: EUR, GBP, CAD, CHF, AUD + JPY, NZD neu xac nhan), vs USD; EUR chi tu 1999.
- LEG (Legacy Non-commercial): TRAIN 1993-01..2005-12; WFO 2006-01..2019-12.
- TFF (Leveraged Funds; Asset Manager): TRAIN 2006-06..2012-12 (NGAN ~6,5 nam - DIEM YEU, da chap nhan); WFO 2013-01..2019-12.
- HOLDOUT chung 2020-01..2026-10, mo MOT lan sau dong bang, owner duyet.
## 4. Tin hieu + luat (chot; 12 cau hinh)
- x_t = (Long - Short) / Open_Interest_All cua nhom tai ngay chot t. z_t = (x_t - mean) / sd cua W tuan den t (gom t, chi bao cao da
  cong bo truoc ngay vao lenh; can du W quan sat). Cuc tri: |z_t| >= 1,5.
- H_TD (tiep dien): z >= 1,5 => LONG dong tien vs USD; z <= -1,5 => SHORT. H_ND (nguoc): dau nguoc.
- Chon chieu CHI tren TRAIN, theo tung nhom: dau cua loi suat trung binh TRAIN (sau chi phi) cua cau hinh W52 / giu 4 tuan duoi H_TD:
  > 0 => H_TD; < 0 => H_ND; = 0 (hoa) => KHONG giao dich nhom do. Ap nguyen cho WFO va HO, khong doi.
- Giu H tuan, H {1, 4}. H=4: 4 phan chong lop (moi tuan mo phan 1/4, dong phan mo 4 tuan truoc). Trong so moi dong tien 1/N_dt
  (N_dt = so dong tien hop le), moi phan x 1/H; gross <= 1.
- Luoi: nhom {LevFunds_TFF, AssetMgr_TFF, NonComm_LEG} x W {52, 156} x H {1, 4} = 12 cau hinh.
- Cau hinh chon (moi nhom): Sharpe TRAIN cao nhat trong 4 cau hinh cua nhom (theo chieu da chon); "gop 3 nhom" = trung binh deu 3 cau
  hinh chon. Bao kem trung vi 12 cau hinh.
## 5. Chi phi (chot; x2 kich ban xau)
- Spread + commission KHU HOI: EUR 0,8 pip (IC Markets Raw [K]); cac cap khac 3 pip (GIA DINH BAO THU). Doi ra bp theo gia.
- Swap: moi ngay lich (r_long - r_short)/360, tru bien broker 1,0 %/nam moi chan; lai suat thang m-1. Khong mo hinh rieng thu 4 x3.
## 6. Thuoc do + doi chung
- Return nam hoa, Sharpe, maxDD (MTM ngay), Calmar, hit rate, so lenh theo dong tien x nam, IC (z vs return 1 va 4 tuan) theo nam,
  skew, turnover. Bao TRAIN va WFO.
- Doi chung: (a) mua-giu ro deu; (b) NGAU NHIEN >= 500 luot: cung so lenh moi dong tien x nam, cung H, ngay vao ngau nhien trong tuan
  hop le, ti le long/short nhu that => p; (c) carry thuan cung thoi gian giu (tach phan loi do carry).
- On dinh: bo 5 % tuan tot nhat; chi phi x2; khong 1 dong tien chiem > 50 % loi (bao).
## 7. Tieu chi (tren WFO; ap cho TUNG nhom va cho GOP 3 nhom)
 D1 Sharpe WFO sau chi phi > 0,3.  D2 p ngau nhien (b) <= 0,05.  D3 maxDD WFO <= 25 %.
 D4 >= 60 % trong 12 cau hinh co loi suat WFO > 0 (cho gop); >= 3/4 cau hinh cua nhom (cho tung nhom).
 D6 bo 5 % tuan tot nhat van > 0.  D7 chi phi x2 van > 0.
 D8 chieu chon tren TRAIN GIU dau (loi suat trung binh cung dau) tren WFO o >= 2/3 nhom.
 D9 >= 150 lenh WFO cho cau hinh chon; thieu => "KHONG DU MAU" (khong ket luan DAT / KHONG DAT ve nhom do).
 Ket luan: du D1-D4, D6-D9 => "DAT" => MASTER de nghi owner mo HOLDOUT. Dat D1 + D2 => "CO TIN HIEU, CHUA DU". Con lai => "KHONG DAT".
## 8. Rui ro / gioi han
- COT chi phu futures CME, khong phai toan thi truong OTC; phan loai nhom tu khai (Form 40) co the troi theo thoi gian.
- Tin hieu tre >= 6 ngay; tuan cong bo tre bi loai => mat mau o dung giai doan bien dong.
- TFF train ngan; so su kien |z| >= 1,5 doc lap it; tuong quan cheo qua USD => n_eff nho; de khop nhieu.
- FRED trua NY, khong bid/ask; chi phi cap ngoai EUR la gia dinh; lai suat la proxy swap.
## 9. Thu tu thuc hien
1 MASTER commit. 2 Agent tai du lieu (Sonnet): file muc 1, provenance + sha256, bang ma hop dong (ma, ten, ngay dau/cuoi), bang ngay
  cong bo that (hoac ghi ro dung quy tac bao thu muc 2), dem truoc so su kien |z| >= 1,5 moi dong tien x nam tren TRAIN.
3 MASTER duyet. 4 DEV (Opus), Python offline, logging; test nhan qua: (i) assert ngay cong bo < ngay vao lenh cho moi lenh; (ii) z_t
  khong dung bao cao sau t; (iii) doi chieu tay 1 thang (2008-10, EUR va GBP: x, z, lenh, PnL). 5 A1 audit code. 6 RUN TRAIN -> chot
  chieu -> WFO (khong cham >= 2020). 7 A1 audit ket qua. 8 MASTER tu kiem >= 3 so. 9 Bao owner. Dem phep thu (12 cau hinh + chon chieu
  3 nhom) cho DSR.
