# PREREG_FX_G4_FINAL - "MUA SAU CU SAP" TRONG NGAY TREN NEN 1 PHUT (+ BAN SAU CU VOT) - NGHIEN CUU TREN GIAY
Soan: agent 2026-11-27 cho MASTER duyet + commit. Khuon: PREREG_FX_G1 + ERRATA1-3. Nhan: [K] da kiem trang nguon hom nay; [KS] qua
snippet / ben thu ba; [UT] uoc tinh chua kiem; CAN KIEM KHI TAI DU LIEU (kem cach kiem).
## 0. Boi canh + tien nghiem
- Chi dao owner (nguyen van bo dau): "forex da lay duoc ti du lieu nao chua ko ban luat la gi nhe nghien cuu chua ra thi lo gi buoc do voi";
  "su dung cac ki nang tren mang cung nhu cac phuong phap dang co gia tri cua he dang co".
- Day la phuong phap LOI cua he crypto (mua khi sap manh bat thuong, thoat trailing / time-stop) chuyen sang FX.
- Tien nghiem trung thuc (THAP): bien dong 1 gio cua cap chinh co ~0,1-0,2 % [UT] trong khi chi phi khu hoi 0,8 pip - 3 bp => phi chiem
  phan lon bien do bat lai; bai hoc FAMILY2 cua he crypto: TP / SL chat bi phi an het. FX khong co thien lech tang dai han nhu coin =>
  thu ca hai phia (MUA sau cu sap, BAN sau cu vot). Edge BIG_DOWN cua he long mong manh theo nguong cung (LONG_INVENTORY A3) => o day
  dung nguong theo bien dong truot. Khong co bang chung hoc thuat da kiem cho "mean-reversion sau cu sap trong ngay" tren FX (FX_SURVEY E).
## 1. Du lieu M1 - tinh trang nguon (kiem 2026-11-27)
- Dukascopy: Terms of Use cam dung "scraper", "robot", "bot" de truy cap / sao chep du lieu va cam dung website de lap co so du lieu khi
  chua co dong y bang van ban; noi dung tai ve chi cho dung ca nhan phi thuong mai [K]: https://www.dukascopy.com/swiss/english/legal-pages/terms-of-use/
  => KHONG dung Dukascopy (khong tai tu dong, khong tai tay de lap kho du lieu).
- HistData.com [K]: M1 theo BID (OHLC), gio EST CO DINH khong DST (UTC-5), volume = 0, file zip theo cap-nam (nam hien hanh theo thang),
  ten file vd HISTDATA_COM_ASCII_EURUSD_M1_2015.zip. Tai qua FORM POST /get.php voi truong an tk (token trong trang), date, datemonth,
  platform, timeframe, fxpair (da doc ma HTML trang EURUSD 2015 - chi doc trang, KHONG gui form). robots.txt chi cam /wp-admin/.
  KHONG thay trang dieu khoan su dung; FAQ: mien phi, khong bao hanh. Site BAN quyen tai FTP / SFTP (PayPal) cho tai "thuan tien hon".
  https://www.histdata.com/f-a-q/ ; https://www.histdata.com/download-by-ftp/
  Danh gia: gui lai form bang script voi token lay tu trang la vung xam (khong co dieu khoan cam, nhung token + dich vu FTP tra phi cho
  thay kenh free nham cho thao tac tay) => KHONG tu dong hoa khi chua co owner / MASTER quyet. Ket luan: "KHONG CO NGUON M1 TU DONG
  HOP LE RO RANG". Phuong an (MASTER / owner chon MOT):
  P1 (mac dinh) owner tai TAY qua trinh duyet: 4 cap x 15 nam (2005-2019) = 60 file; neu du dia them 3 cap = 45 file nua.
  P2 owner mua quyen FTP / SFTP cua HistData (gia CAN KIEM tren https://www.histdata.com/download-by-ftp/) roi agent tai bang FTP.
  P3 MASTER chap nhan tu dong hoa form cong khai voi toc do thap (1 file / 10 s, User-Agent ro rang) - agent KHONG tu lam neu khong co
  chot bang van ban.
- Dung luong [UT - CAN KIEM bang 1 file tai tay]: ~372 000 nen / cap-nam; zip ~4-6 MB, giai nen ~18-22 MB / cap-nam.
  4 cap x 15 nam ~ 0,3 GB zip / ~1,3 GB CSV; 7 cap ~ 0,5 / 2,3 GB. De xuat: giu zip goc + chuyen sang parquet (nen), xoa CSV giai nen
  => < 1 GB cho 7 cap; tran 4 GB tren Oracle (con ~13 GB). Neu thieu: chi 4 cap EURUSD, GBPUSD, USDJPY, AUDUSD.
- Cap: uu tien EURUSD, GBPUSD, USDJPY, AUDUSD; them USDCAD, USDCHF, NZDUSD neu P1 / P2 du. Chi tai 2005-01..2019-12 (HOLDOUT
  2020-01..2026-10 KHONG tai o buoc nay).
- Lich tin kinh te co lich su mien phi dang tin: KHONG tim thay (FX_SURVEY B) => "KHONG LOC TIN" - rui ro muc 7.
- Kiem chat luong khi tai (CAN KIEM KHI TAI): (i) doi gio EST co dinh -> UTC (+5 h) roi -> gio New York co DST; (ii) bao so phut thieu /
  khoang trong > 5 phut ngoai cuoi tuan theo cap-nam; (iii) doi chieu gia M1 luc ~12:00 NY voi FRED H.10 cung ngay (|log diff| > 0,5 %
  => co, bao ti le); (iv) nhan thoi gian cua nen M1 la dau hay cuoi phut - xac dinh tu file / FAQ "Data Files: Detailed Specification".
## 2. Chia thoi gian
- TRAIN 2005-01..2012-12; WFO 2013-01..2019-12 (hai nua 2013-2016, 2017-2019); HOLDOUT 2020-01..2026-10 (khong tai, khong doc).
## 3. Tin hieu + luoi (chot; 12 cau hinh)
- Gia: BID close M1 (P). r_N(t) = log(P_t / P_{t-N}). sigma_N(t) = std cua log-return 1 phut trong 20 ngay giao dich TRUOC ngay cua t
  x sqrt(N) (chi du lieu < ngay t). z = r_N / sigma_N. sigma60(t) = std 1 phut 20 ngay truoc x sqrt(60) (dung cho thoat).
- Su kien MUA (L): z <= -T. Su kien BAN (S): z >= +T. KHONG dung nguong % cung.
- Loai su kien: cuoi tuan / 30 phut dau sau khi thi truong mo (chu nhat 17:00 NY) va cua so rollover 16:55-17:15 NY; mot cap chi co 1 vi
  the; dang co vi the => bo su kien moi cung cap.
- Vao lenh: close cua phut KE TIEP sau phut z vuot nguong; L mua tai ASK = BID + spread(h); S ban tai BID.
- Thoat (danh gia tai close MOI phut - cung co che voi bot live, bai hoc B1): SL = 2,0 x sigma60 tu gia vao; trailing arm khi lai dinh
  >= 1,0 x sigma60, gap = 0,5 x sigma60 tu dinh (dinh do bang close phut); time-stop TS. L thoat tai BID, S thoat tai ASK.
  Khoang trong du lieu / cuoi tuan: vi the con mo qua cuoi tuan => thoat tai gia mo dau tien (gap) - khong noi suy.
- Luoi: phia {L, S} x (N, T) in {(15, 4), (60, 3), (60, 4)} x TS {4 h, 24 h} = 12 cau hinh:
  1 L-15-4-4h  2 L-15-4-24h  3 L-60-3-4h  4 L-60-3-24h  5 L-60-4-4h  6 L-60-4-24h  7-12 = cung thu tu voi S.
- Chon cau hinh (chot): Sharpe TRAIN (theo thang, sau chi phi) cao nhat; hoa => TS ngan truoc, roi T cao truoc.
- Sizing: moi lenh notional = 1/ (so cap) cua von, khong don bay; loi suat tinh tren von.
## 4. Chi phi (chot; kich ban xau x2)
- Du lieu chi co BID => cong spread gia dinh. Chi phi khu hoi co so: EURUSD 0,8 pip; cap khac MAX(3 pip, 3 bp) (ERRATA2 J1).
  Theo khung gio NY: 16:55-17:15 va 30 phut dau tuan: x3 (nhung da loai vao lenh trong khung nay; ap cho THOAT roi vao khung do).
  Khong co lich tin => khong cong them quanh tin (rui ro). Moi chieu = nua chi phi khu hoi, ap vao gia ASK / BID nhu muc 3.
- Truot lenh stop / SL: them 0,5 x chi phi khu hoi moi lan SL / time-stop khop (bao thu). Swap: vi the qua 17:00 NY tinh
  (r - r_USD)/360 theo lai suat OECD thang m-1 + bien broker 1 %/nam (TS 24 h co the qua dem; TS 4 h thuong khong).
## 5. Thuoc do + doi chung
- So lenh, loi suat trung binh / lenh (bp, sau phi), hit rate, payoff, Sharpe theo thang, maxDD (MTM phut), Calmar, lenh te nhat,
  phan bo theo gio trong ngay / cap / nam; ti le thoat SL / trailing / time-stop. Bao HAI so: TRAIN va WFO; ca 12 cau hinh + trung vi.
- TRUOC KHI CHAY (agent tai du lieu): dem so su kien moi cau hinh x cap x nam tren TRAIN; neu WFO du kien < 150 lenh => MASTER quyet.
- Doi chung CHINH (giu cau truc): DICH VONG THEO NGAY - moi luot, toan bo moc thoi gian su kien cua mot cap trong WFO bi dich cung mot so
  ngay giao dich k ngau nhien (vong trong giai doan WFO), GIU gio-trong-ngay, cum su kien, so lenh, phia, cung co che thoat + chi phi;
  >= 500 luot (de xuat 1000); p = (1 + so luot >= that) / (N + 1).
- Doi chung phu (mo ta): vao ngau nhien cung cap / cung gio (+-30 phut) / cung so lenh moi nam.
- On dinh: bo 5 % THANG tot nhat van > 0; chi phi x2; theo cap (khong 1 cap > 50 % loi).
## 6. Tieu chi (tren WFO, cau hinh chon bang TRAIN; chot truoc)
 D1 Sharpe WFO (thang) sau chi phi > 0,3.  D2 p doi chung dich vong <= 0,05.  D3 maxDD WFO <= 25 %.
 D4 >= 60 % trong 12 cau hinh co loi suat WFO > 0.  D5 bo 5 % thang tot nhat van > 0.  D6 chi phi x2 van > 0.
 D7 >= 150 lenh WFO cho cau hinh chon; thieu => "KHONG DU MAU".
 Ket luan: du D1-D7 => "DAT" => de nghi mo HOLDOUT (tieu chi HO chot truoc; can tai them 2020-2026 luc do). Dat D1 + D2 => "CO TIN
 HIEU, CHUA DU". Con lai => "KHONG DAT".
## 7. Rui ro / gioi han
- Gia HistData la feed cua mot nguon khong ro (FAQ khong neu), chi BID; spread / truot la gia dinh; gia khop that cua broker khac.
- KHONG loc tin: nhieu "cu sap" la phan ung tin vi mo (Andersen-Bollerslev-Diebold-Vega 2003) => co the khong hoi; dien hinh rui ro
  truot + spread gian lon hon gia dinh.
- Gio EST co dinh -> phai doi DST dung; sai 1 gio lam lech cua so rollover.
- Su kien cum (cung ngay tin, nhieu cap USD cung luc) => n_eff nho; 12 cau hinh => rui ro chon.
- Phi so voi bien do: neu sigma60 ~ 10 bp va phi khu hoi 3 bp => phi = 0,3 sigma (UT) => kho co loi sau phi.
- Nguon M1 phu thuoc thao tac / quyet dinh cua owner (muc 1). Du lieu dung den 2019-12 (WFO); khong dung sau 2026-10.
## 8. Thu tu thuc hien
1 MASTER commit + chot P1 / P2 / P3 (muc 1). 2 Owner / agent tai du lieu theo phuong an chot: provenance (URL, ten file, kich thuoc,
  sha256, thoi diem), kiem chat luong muc 1 (iv buoc), dem su kien TRAIN, kiem dung luong. 3 MASTER duyet bao du lieu.
4 DEV (Opus): Python offline Oracle, flock oracle_heavy.lock (du lieu lon), logging; unit test: (i) sigma chi dung ngay truoc; (ii) vao
  lenh phut KE TIEP; (iii) thoat danh gia tai close phut, L thoat BID / S thoat ASK; (iv) gap cuoi tuan; (v) doi DST; (vi) doi chung giu
  gio-trong-ngay + so lenh; (vii) x2 nhan moi chi phi; (viii) chon cau hinh chi bang TRAIN. DEV khong tinh loi suat that.
5 A1 audit code (agent khac). 6 RUN TRAIN + WFO. 7 A1 audit ket qua (doi chieu tay 3 lenh ngau nhien tu M1 goc). 8 MASTER tu kiem
  >= 3 so. 9 Bao owner. Dem so cau hinh (12) cho DSR.

## CHOT CUA MASTER (2026-11-27 06:50)
- Nguon nen 1 phut: KHONG tu dong hoa form tai cua HistData va KHONG dung Dukascopy (dieu khoan). Phuong an: tim dataset CONG KHAI tren
  Kaggle co giay phep ro rang chua nen 1 phut cac cap chinh (tai bang kaggle CLI); kiem cheo voi ty gia ngay FRED truoc khi dung. Khong
  tim duoc nguon dat => G4 TAM DUNG (bao owner), khong lach.
- Chap nhan: khong loc tin (ghi la rui ro); he so chi phi x3 quanh gio rollover; tham so thoat SL 2,0 / arm 1,0 / gap 0,5 (boi so sigma60).
- 4 cap uu tien: EURUSD, GBPUSD, USDJPY, AUDUSD; them cap khac neu nguon co va dia cho phep (tran 4 GB).
