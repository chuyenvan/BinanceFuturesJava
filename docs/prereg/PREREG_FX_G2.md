# PREREG_FX_G2_FINAL - TREND THEO CHUOI THOI GIAN (TSMOM) + LOC GIA TRI (REER) - NGHIEN CUU TREN GIAY
Soan: agent 2026-11-27 cho MASTER duyet + commit. Khuon: PREREG_FX_G1 + ERRATA1-3. Nhan: [K] da kiem trang nguon / file hom nay;
[KS] qua snippet / ben thu ba; CAN KIEM KHI TAI DU LIEU (kem cach kiem).
## 0. Boi canh + tien nghiem
- Chi dao owner (nguyen van bo dau): "forex da lay duoc ti du lieu nao chua ko ban luat la gi nhe nghien cuu chua ra thi lo gi buoc do voi";
  "su dung cac ki nang tren mang cung nhu cac phuong phap dang co gia tri cua he dang co".
- Ket qua truoc (MASTER_NOTE_FX_1127): G1 carry + gate KHONG DAT (WFO Sharpe 0,003); G3 COT KHONG DAT (0 / 12 cau hinh WFO duong).
- Tien nghiem TRUNG THUC (thap): Neely-Weller-Ulrich 2009 JFQA - loi nhuan quy tac MA / filter tren FX la that o thap nien 1970-80 nhung
  BIEN MAT tu dau 1990s (https://iro.uiowa.edu/esploro/outputs/journalArticle/The-Adaptive-Markets-Hypothesis-Evidence-from/9984963054302771 [K]).
  Moskowitz-Ooi-Pedersen 2012: TSMOM co tren 58 hop dong gom tien te nhung la danh muc da tai san (https://papers.ssrn.com/abstract=2089463 [K]).
  Asness-Moskowitz-Pedersen 2013: value tien te co nhung yeu (https://pages.stern.nyu.edu/~lpederse/papers/ValMomEverywhere.pdf [K]).
  => ky vong WFO 2006-2019 gan 0; ket qua am la hop le.
- Co che mang tu he crypto: luat don gian, sizing theo bien dong, kiem dinh WFO + doi chung giu cau truc; khong dung model.
## 1. Du lieu
Da co tren Oracle (~/claude_master/w3/fx/data/, PROVENANCE.md co URL + sha256, tai 2026-11-26) [K file]:
- Ty gia ngay FRED H.10 (gia tham chieu trua New York): DEXUSEU (1999-01-04), DEXJPUS, DEXUSUK, DEXSZUS, DEXCAUS, DEXUSAL, DEXUSNZ,
  DEXNOUS, DEXSDUS (1971-01-04). File: raw/FRED_<ID>.csv va derived/FRED_<ID>.csv.
- Lai suat OECD thang (CHI dung cho swap, KHONG dung cho tin hieu) - ngay dau / cuoi theo file [K]: US 1964-06; GB 1957-01 (het 2026-01);
  CA 1956-01; AU 1968-01; NZ 1973-12; NO 1979-01; SE 1982-01; CH 1999-07; EZ 1994-01 (het 2026-01); JP 2002-04.
Can tai them (BIS, mien phi) [K 2026-11-27: trang bulk https://data.bis.org/bulkdownload; HEAD tra 200]:
- https://data.bis.org/static/bulk/WS_EER_csv_flat.zip (6 642 263 byte, Last-Modified 2026-11-25) - dung ban nay;
  du phong https://data.bis.org/static/bulk/WS_EER_csv_col.zip (2 089 850 byte).
- Dieu khoan: https://data.bis.org/help/legal#terms-of-permitted-use-of-bis-statistics (CAN KIEM KHI TAI: doc va ghi vao PROVENANCE).
- Chuoi dung: REER THANG, ro HEP (narrow; co du lieu tu 1964 [KS - FRED/BIS mo ta]) cho US, XM (euro area), JP, GB, CH, CA, AU, NZ, NO, SE.
  CAN KIEM KHI TAI: ma cot (vd FREQ=M, EER_TYPE=R, EER_BASKET=N, REF_AREA) va ngay dau tung dong tien tu chinh file; dong nao khong co
  REER narrow => bien the loc gia tri KHONG ap cho dong do (ghi so). BIS co the sua lich su (doi trong so, doi nam goc) => rui ro muc 7.
- Neu WS_EER khong tai / khong doc duoc: G2 chi lam TREND (cau hinh F0), bo moi bien the REER, ghi ro.
- Cat moi du lieu khi nap: chi doc ngay < 2020-01-01 (HOLDOUT 2020-01..2026-10 KHONG doc); ghi sha256 + Last-Modified file BIS.
## 2. Chia thoi gian
- Chot de xuat: TRAIN 1975-01..2005-12; WFO 2006-01..2019-12 (hai nua 2006-2012, 2013-2019); HOLDOUT 2020-01..2026-10 khong doc.
  Ly do: tin hieu chi can ty gia (co tu 1971, lookback 12 thang + vol 63 ngay); TRAIN dai cho nhieu quan sat doc lap.
  Diem yeu: TRAIN chua giai doan 1975-1990 ma Neely-Weller cho la trend con loi => cau hinh chon co the thien ve che do da het;
  bao them (mo ta) TRAIN tach 1975-1989 / 1990-2005.
- Phuong an kia (MASTER co the chon): TRAIN 1994-01..2005-12 (giong G1; chi giai doan "hau suy giam"; it du lieu hon ~2,6 lan).
- Loc gia tri can 5 nam REER truoc: trong TRAIN 1975-1979 thieu 5 nam (neu REER narrow bat dau 1964 thi du) - CAN KIEM KHI TAI.
## 3. Tin hieu + luoi (chot; 12 cau hinh)
- Universe thang m: dong tien co ty gia hop le o ngay can bang VA co lai suat thang m-1 cho CA dong do va USD (de tinh swap).
  Quy tac BAO THU cho swap (chot): dong tien / thang thieu lai suat => NGOAI universe (khong tinh swap = 0). He qua: TRAIN som khong co
  JPY (< 2002-04), CHF (< 1999-07), EUR (< 1999), NO (< 1979), SE (< 1982) - ghi so dong tien moi nam. Phuong an khong chon: swap = 0
  (bo qua carry; khong bao thu vi carry JPY / CHF thoi do co the duong cho vi the short).
- Ngay tin hieu: ngay lam viec cuoi thang m (lich FRED). Thuc thi: gia FRED ngay lam viec KE TIEP (khong khop tai chinh gia dung tao
  tin hieu).
- TSMOM: s_i(L) = dau cua log(P_i(t) / P_i(t - L thang)) cua dong tien i vs USD (gia quy ve "USD tren 1 don vi dong tien"). L in {1, 3, 12}.
  Ban "TONG HOP" (C): s_i = dau cua trung binh s_i(1), s_i(3), s_i(12) (0 => khong vi the).
- Sizing (chot MOT): nghich dao bien dong, KHONG don bay: w_i = s_i / vol_i, vol_i = std log-return ngay 63 ngay truoc ngay tin hieu
  x sqrt(252); chuan hoa sum |w_i| = 1 (gross = 1). Khong vol-target danh muc.
- Loc gia tri V(X): khong LONG dong tien co REER(m-1) > (1 + X) x trung binh REER 60 thang truoc (m-60..m-1); khong SHORT dong tien co
  REER(m-1) < (1 - X) x trung binh do (doi xung). Vi the bi loc => 0, chuan hoa lai gross. USD khong vao tin hieu (la dong tai tro).
  REER dung thang m-1 (BIS cong bo giua thang sau - CAN KIEM ngay cong bo; neu tre hon 1 thang dung m-2).
- Luoi: tin hieu {L1, L3, L12, C} x loc {F0 = khong loc; V10 = X 10 %; V20 = X 20 %} = 12 cau hinh:
  1 L1-F0  2 L1-V10  3 L1-V20  4 L3-F0  5 L3-V10  6 L3-V20  7 L12-F0  8 L12-V10  9 L12-V20  10 C-F0  11 C-V10  12 C-V20.
- Chon cau hinh (chot): Sharpe TRAIN sau chi phi cao nhat; hoa => it bien hon (F0 truoc V; L dai truoc). Bao kem trung vi 12 cau hinh.
## 4. Chi phi (chot; kich ban xau x2 moi khoan)
- Spread + commission khu hoi moi giao dich: EURUSD 0,8 pip; cap khac MAX(3 pip, 3 bp gia tri giao dich) (ERRATA2 J1).
  Phi tinh tren |thay doi trong so| moi lan can bang (khong netting giua dong tien).
- Swap: moi ngay lich (r_dong_tien - r_USD)/360 x trong so (dau theo vi the), TRU bien broker 1 %/nam tren |trong so| moi dong tien;
  r = lai suat thang m-1. Tan suat thang: khong mo hinh rieng thu 4 x3 (tinh theo ngay lich).
## 5. Thuoc do + doi chung
- Loi suat nam hoa (so voi USD lai 0), Sharpe, maxDD (MTM ngay), Calmar, skew, thang te nhat, ti le nam duong, turnover / nam, so dong
  tien / nam, % vi the bi loc gia tri. Bao HAI so: TRAIN (in-sample) va WFO; ca 12 cau hinh + cau hinh chon + trung vi.
- Doi chung CHINH (giu cau truc): DICH VONG KHOI - voi moi dong tien, chuoi tin hieu thang (sau loc) cua giai doan WFO bi dich vong mot
  so thang ngau nhien k in [12, so thang - 12] (doc lap tung dong tien), giu nguyen sizing + chi phi; >= 1000 luot;
  p = (1 + so luot >= that) / (N + 1) (ERRATA3 K1).
- Doi chung phu (mo ta): mua-giu ro deu cac dong tien vs USD; dau ngau nhien moi thang (>= 1000); ban khong loc (F0) cung L.
- On dinh: bo 5 % THANG tot nhat (ceil, ERRATA2 J3) van > 0; chi phi x2; Sharpe theo hai nua WFO.
## 6. Tieu chi (tren WFO, cau hinh chon bang TRAIN; chot truoc)
 D1 Sharpe WFO sau chi phi > 0,3.   D2 p doi chung dich vong <= 0,05.   D3 maxDD WFO <= 25 %.
 D4 >= 60 % trong 12 cau hinh co loi suat WFO > 0.   D5 bo 5 % thang tot nhat van > 0.   D6 chi phi x2 van > 0.
 Ket luan: du D1-D6 => "DAT" => MASTER de nghi owner mo HOLDOUT (tieu chi HO chot truoc). Dat D1 + D2 => "CO TIN HIEU, CHUA DU".
 Con lai => "KHONG DAT". Bao them (mo ta, khong vao tieu chi): loc gia tri co cai thien Sharpe so voi F0 cung L o ca hai nua WFO khong.
## 7. Rui ro / gioi han
- FRED la gia trua NY (gia dinh khop tai gia do + chi phi), khong bid/ask; chi phi cap ngoai EURUSD la gia dinh bao thu.
- Universe thay doi theo thoi gian (TRAIN thieu JPY / CHF / EUR) => TRAIN va WFO khac tap dong tien.
- Tin hieu trend tren ~9 dong tien chung mot "nhan to USD" => n_eff nho; 12 cau hinh => rui ro chon.
- REER BIS co the bi sua lich su (trong so, nam goc) => nguy co nhin truoc nho; khong co ban "vintage". Ghi ro, khong khac phuc.
- Lai suat OECD la proxy swap broker. Du lieu den het 2026-10; khong dung sau do.
## 8. Thu tu thuc hien
1 MASTER commit. 2 Agent tai du lieu (Sonnet): tai WS_EER_csv_flat.zip (sha256, Last-Modified, dieu khoan BIS), lap bang (dong tien, ma
  cot REER narrow, ngay dau / cuoi), giai quyet cac muc CAN KIEM; cat < 2020-01-01. 3 MASTER duyet bao du lieu.
4 DEV (Opus): Python offline Oracle, logging, flock oracle_heavy.lock neu nang; unit test: (i) tin hieu thang m chi dung gia <= ngay tin
  hieu, REER <= m-1, lai suat <= m-1; (ii) thuc thi o ngay KE TIEP; (iii) doi chung dich vong giu so thang co vi the; (iv) D5 bo thang
  TOT nhat; (v) x2 nhan moi chi phi; (vi) chon cau hinh chi bang TRAIN. DEV khong tinh loi suat that.
5 A1 audit code (agent khac). 6 RUN TRAIN + WFO. 7 A1 audit ket qua (doi chieu tay 1 thang, vd 2008-10). 8 MASTER tu kiem >= 3 so.
9 Bao owner. Dem so cau hinh (12) cho DSR.

## CHOT CUA MASTER (2026-11-27 06:50, truoc khi viet code / tinh loi suat)
- TRAIN 1975-01..2005-12 (dong tien / thang thieu lai suat thi ngoai universe thang do - nhu ban soan); WFO 2006-01..2019-12; HOLDOUT
  2020-01..2026-10 khong doc. Loc gia tri X in {10 %, 20 %}, REER thang m-1. Neu khong tai / khong xac dinh duoc cot REER cua BIS thi chi
  chay 4 cau hinh TREND khong loc (ghi ro), khong thay nguon.
- Ap dung san cac bai hoc ERRATA1-3 cua G1 / G3: p = (1 + n_ge) / (N + 1); doi chung chinh giu cau truc; chi phi MAX(3 pip, 3 bp).
