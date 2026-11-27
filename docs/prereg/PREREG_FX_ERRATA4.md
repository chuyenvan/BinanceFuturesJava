# PREREG_FX_ERRATA4 - G4 (sau khi tai + kiem ke nen 1 phut; chua co loi suat nao) va G2 (sau A1 code PASS-WITH-MINOR; chua chay)
Chot boi MASTER 2026-11-27 08:10. Ap cho PREREG_FX_G4 / PREREG_FX_G2 (915d7a1a).
N1 (G4, nguon). Nen 1 phut: Kaggle `almirneto/forex-multi-timeframe` (CC0 ghi tren Kaggle; xuat tu MT5, broker khong neu ten - rui ro nguon
   goc da ghi nhan; chi dung nghien cuu noi bo). 4 cap EURUSD, GBPUSD, USDJPY, AUDUSD, 2005-2019, parquet o ~/claude_master/w3/fx/data/
   derived/m1/ (provenance + DATA_REPORT_3.md). Gia la BID (quy uoc MT5): lenh MUA cong spread gia dinh theo muc chi phi cua prereg; cot
   spread cua file KHONG dung.
N2 (G4, mui gio). Gio may chu: truoc 2014-11-24 = Europe/Berlin; tu 2014-11-24 = Europe/Athens (ca hai doi gio theo lich chau Au); da doi
   sang UTC trong parquet. Kiem cheo FRED 12:00 New York: lech trung vi 0,004-0,026 %.
N3 (G4, chat luong). Cap-nam thieu > 5 % so phut trong gio giao dich bi LOAI hoan toan (khong sinh su kien, khong lam doi chung, khong
   tinh bien dong truot tu du lieu cua cap-nam do sau 20 ngay dau nam ke tiep): 2007 va 2008 (ca 4 cap), GBPUSD 2009, USDJPY 2009,
   AUDUSD 2006. Danh sach chot theo DATA_REPORT_3.md, khong doi sau khi thay ket qua.
N4 (G4, dau tuan / khoang trong). Khong dung gio co dinh: su kien "sap / vot" KHONG duoc tinh neu cua so N phut cua no chua mot khoang
   trong > 5 phut hoac nam trong 30 phut dau sau moi khoang trong > 60 phut (gom mo cua dau tuan). Lenh dang mo qua cuoi tuan: giu, danh
   gia tai nen dau tien sau khoang trong (gap tinh vao ket qua).
N5 (G4, chia thoi gian). TRAIN 2005-01..2012-12 (tru cac cap-nam bi loai), WFO 2013-01..2019-12; HOLDOUT >= 2020 khong doc.
N6 (G2). Chay voi ban code da audit (sha trong A1_G2_CODE.md). Ban mo ta do nhay REER thang m-2 va carry theo lai suat thang giu CHUA co
   trong code => khong bao; ghi la gioi han. Rui ro REER (BIS khong co vintage, lich su bi sua; AU / NZ noi suy CPI quy) da ghi nhan.
