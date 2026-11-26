# MASTER_NOTE FOREX G1 + G3 (nghien cuu tren giay) - 2026-11-27 01:12 +0700
Prereg PREREG_FX_G1 / G3 (058ed482) + ERRATA1 a65fb2d0 + ERRATA2 50b5995e + ERRATA3 2ea33f61. Du lieu cong khai FRED / ECB / CFTC (43 file,
data/PROVENANCE.md). Code A1 PASS-WITH-MINOR / PASS (2 vong moi cai). Chay that 27/11 ~01:00, cutoff 2019-12-31. HOLDOUT 2020-2026 KHONG mo.
Ket qua A1 XAC NHAN ca hai (tinh lai doc lap khop 3-4 chu so; doi chieu tay thang 2008-10 khop).
G1 - carry G10 + gate bien dong rolling: KHONG DAT.
- Cau hinh chon bang TRAIN (k2, gate FX_VOL q0,80 N3; Sharpe TRAIN 0,96 [in-sample]): WFO 2006-2019 Sharpe 0,003; CAGR -0,07 % / nam; maxDD
  13,5 %. Trung vi 12 cau hinh WFO Sharpe -0,045; 3 / 12 cau hinh duong; chi phi x2 am; bo 5 % thang tot nhat -20 %. D1..D7 = F F T F T F F.
- Mo ta: carry khong gate: TRAIN Sharpe 0,76 [in-sample] -> WFO -0,02 (2008: -18 %). Gate cat duoc cu sap 2008 (maxDD 4 % vs 20 %) nhung
  bo lo pha hoi 2009-2012 => WFO ~ 0. Nguyen nhan chinh: carry G10 suy giam sau 2008.
G3 - z-score vi the COT: KHONG DAT.
- WFO Sharpe sau phi: LevFunds -0,38; AssetMgr -0,27; NonComm -0,23; gop 2013-2019 -0,60. 0 / 12 cau hinh WFO duong. Truoc phi cung ~0 /
  hoi am (-0,1..-0,4 % / nam). Chieu chon tren TRAIN khong giu dau tren WFO (D8 truot ca 3 nhom); dao chieu cung khong on dinh.
- LUU Y: p cua doi chung chinh (0,004 / 0,002 / 0,014) KHONG co gia tri - doi chung bi lech bat loi cho luot ngau nhien (A1); p theo doi
  chung dich vong: 0,76 / 0,56 / 0,61. Khong duoc dan cac p nho do.
He qua: hai y tuong "co can cu nhat" cua forex (carry, vi the dam dong) khong qua WFO sau chi phi retail. Bai hoc trung voi he crypto: tin
hieu positioning khong on dinh dau; gate rolling giam DD nhung khong tao loi nhuan. Con lai trong khao sat: G2 (trend + REER) - tien nghiem
thap (quy tac trend don gian da mat loi nhuan tu thap nien 1990). Khong mo holdout.
