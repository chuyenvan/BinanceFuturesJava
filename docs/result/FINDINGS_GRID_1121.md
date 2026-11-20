# FINDINGS_GRID_1121 - Ket luan ho GRID (2026-11-19 .. 2026-11-21) - MASTER
Pham vi: grid nhu mot nguon loi nhuan DOC LAP va grid nhu lop thuc thi, Binance USDT-M futures, du lieu 2021-07 .. 2025-12
(2026 niem phong, chua dung). So trial ho grid: 98. Khong co thay doi nao cho cau hinh live.

## 1. Ket luan
K1. Grid hai chieu (mua + ban quanh gia) KHONG co loi the sau phi, o moi khung da thu (buoc 0,1-0,4 sigma_1d, giu 30 phut - 1,3 ngay),
    moi nhom thanh khoan. Buoc nho (0,1 sigma; 0,2 sigma giu ngan tren top-60): can tren dong thoi 95 % < 4 bps ngay ca duoi mo hinh
    khop lac quan => DONG MANH. Buoc rong: chua loai duoc vi nhieu, uoc luong 2024-25 quanh 0.
K2. Chon coin theo kinh nghiem thuc hanh (di ngang / ER thap; tap "ly tuong": di ngang + bien dong vua + >= 90 ngay + top-60 +
    funding khong cuc doan) KHONG tao loi the (M -0,6 .. +2,3 bps duoi khop lac quan; -10 .. -14 duoi khop bi quan).
K3. Grid mot chieu theo xu huong (chi mua khi coin + BTC tren SMA20 dang tang; chi ban khi nguoc lai): lai tho la BETA; sau khi tru
    beta BTC khong o nao dat; tru them phi hedge thi am.
K4. O duy nhat tung "dat" (dat lenh 0,2 sigma ngay sau cu soc gia + volume cua mot coin; S1, chi duoi K_OPT: +19,9 bps) la HIEN VAT cua
    mo hinh khop tren nen 1 phut: quy tac "khop va chot trong cung phut" coi dinh phut den sau day phut. Kiem bang du lieu tung giao dich
    tren cung mau (S2, 6 604 cum, 24 644 don vi): TL_TOUCH +5,9 (2021-23, p 0,26) / -1,2 (2024-25); TL_THROUGH -2,4 / -9,1 => L2-C, DONG.
    BAI HOC PHUONG PHAP: khong dung quy tac "vong tron cung phut theo thu tu co loi" tren nen OHLC cho bat ky chien luoc limit nao;
    dung K_OPT3 (thoat cung phut chi khi close phut khop da vuot muc thoat) hoac du lieu giao dich.
K5. Lenh limit SAU dat san (1 - 2,5 sigma_1d duoi / tren gia dau gio, khop khi gia xuyen qua; S3 "WICK"): KHONG o nao dat (luat W-B,
    dong THEO NGAN SACH - khong du bang chung, khong phai chung minh la khong co). Mo ta (KHONG phai bang chung): lenh MUA sau 2,5 sigma
    duoi khop bi quan co M +253/+275 bps (2021-23, t 3,6/4,4) va +242/+269 bps (2024-25, t 2,4/2,3; p Romano-Wolf 0,40), duong moi nam
    2021-2025, khong phu thuoc top-3 coin / 3 su kien / giai doan 20 ngay lai nhat; NHUNG toan bo den tu cac cu sap TOAN THI TRUONG
    (BTC cung roi): 2024-25 sap toan thi truong +326 bps, cu roi rieng coin -24 bps. Tuc la cung ban chat voi loi the crash-buy ma c3
    da khai thac; khong co bang chung day la loi the MOI cua "grid". Lenh BAN sau: khong co gi (c1,0 am ro o 2024-25).
K6. "Grid lam lop thuc thi cho crash-buy": cac bien the chinh da dong tu truoc - vao lenh bang limit / bac thang thap hon gia tin hieu
    (EXEC_RESULT 10-12: lenh khong khop la lenh lai nhat), DCA nong / sau theo % (NULL), bac thang chot loi (GRIDP_T3 FAIL), luoi co
    dinh sau cu sap BTC (GRIDP_T1 FAIL). Luoi DCA hien co (-50/-75/-90): dCAGR22 +2,37 pp nhung gan nhu toan bo tu 1 su kien 10/2025,
    maxDD sau hon 1,79 pp (DCAGRID_A3) => giu nguyen, khong mo rong.
K7. Tri thuc thuc hanh tren internet (36 nguon, docs/result/GRID_PLAYBOOK_1120.md): gan nhu khong nguon nao cong bo PnL tong that nhieu
    thang; hai nguon co kiem chung doc lap (arXiv 2608.21888, arXiv 2506.11921) khop voi K1.

## 2. Bang thi nghiem
| Thi nghiem | Prereg / ket qua (commit) | Ket qua |
|---|---|---|
| Vong 1: T1 luoi sau sap, T2 rebalance, T3 bac thang thoat, T4 nhan RANGE | PREREG_GRID_PREMISE_1120 (+ADD1) / v12/RESULT_GRIDP_T1..T4 | 0/4 PASS |
| DCAGRID_A3 (dong gop luoi DCA hien co) | PREREG_DCAGRID_A3 (+ADD1) / v12/RESULT_DCAGRID_A3 | "co dong gop" theo chu, 1 su kien |
| S1 kinh te don vi luoi, 32 o x 2 mo hinh khop | 4ecc655d + ADD1 19608bbd / 246ae234 | L-C: 1 o chi duoi K_OPT |
| S2 kiem khop muc giao dich o COND_A | 56eddec8, mau 6dfd2453 / 766b4424 | L2-C: hien vat, dong |
| S3 WICK lenh sau, 12 o x 2 mo hinh | 1c748473 / (commit nay) | W-B: 0 o dat |

## 3. Dieu kien mo lai (chi voi bang chung NGOAI)
- Ho grid doc lap hai chieu / theo coin / theo trend: khong mo lai tru khi phi maker ve <= 0 hoac co ha tang uu tien hang doi.
- Lenh mua sau luc sap toan thi truong: neu muon theo, phai (i) dat thanh cau hoi cua ho crash-buy (so voi c3 trong sim Java co von
  chung, chong lan lenh), (ii) prereg MOT gia thuyet duy nhat, (iii) kiem tren du lieu 2026 (owner mo niem phong); 10 thang 2026 co
  cong suat thap (SE uoc > 150 bps) nen chi phat hien duoc loi the rat lon.
