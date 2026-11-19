# PREREG_GRID_PREMISE_1120 - ADDENDUM 1 (CHOT 2026-11-20 04:40 +07, MASTER)

Khai ro thoi diem: viet SAU khi T1 va T3 da co ket qua day du (ca hai FAIL cong E; xem RESULT_GRIDP_T1.md, RESULT_GRIDP_T3.md) va SAU khi
T2, T4 DUNG o buoc kiem chung V6 TRUOC khi doc bat ky outcome thi truong nao cua chinh chung. Chua ai tinh S2 / S4 tren du lieu that.
Addendum nay chi sua (1) surrogate cua T2 bi sai ve toan hoc, (2) cong V6 cua T4 khong con du lieu tham chieu. Gia thuyet, thong ke chinh,
ky E / C, san hieu ung, Holm tren 4 phep thu: GIU NGUYEN.

## 1. T2 - sua surrogate (ban goc lam S2 = 0 voi MOI du lieu)
- Loi: A tai can bang deu moi ngay => R_A = tich theo ngay cua (1 + TB cheo coin cua loi nhuan ngay); hoan vi THU TU NGAY (cung hoan vi cho
  moi coin) chi doi thu tu cac thua so => R_A bat bien nhu R_B => S2 = 0, p chi la nhieu lam tron. Agent T2 chung minh bang du lieu tong
  hop (v6_synth_result.json: dao dong nguoc pha D tho +7,49 %/thang nhung S2 = 1e-17).
- Sua: surrogate = hoan vi KHOI 4 GIO trong thang (khoi canh theo UTC 00/04/08/12/16/20; loi nhuan khoi = log close cuoi khoi / close cuoi
  khoi truoc), CUNG MOT hoan vi cho moi coin (giu tuong quan cung khoi va tong loi nhuan tung coin => R_B bat bien), A tai can bang moi 6
  khoi (= 00:00 UTC) tren duong da hoan vi. >= 1000 hoan vi / thang. S2 = TB thang cua [D_thuc - TB_surrogate D], D = log(1+R_A,gross) -
  log(1+R_B,gross). Y nghia: thu tu thoi gian that (dao chieu tuong doi o thang >= 1 ngay) co lam tai can bang hang ngay loi hon so voi
  cung cac khoi loi nhuan do xep ngau nhien khong.
- Kiem bat buoc truoc khi doc du lieu that (V6 moi, tren du lieu TONG HOP, 200 duong x 30 thang): (a) GBM doc lap: |TB S2| < 2 SE;
  (b) dao dong nguoc pha chu ky 6 ngay bien do 10 %: TB S2 > 0 va >= 95 % duong co S2 > 0; (c) R_B bat bien < 1e-12 voi moi hoan vi;
  (d) A KHONG bat bien: do lech chuan cua D tren cac hoan vi > 1e-6 o du lieu (b). Khong dat => T2 = "KHONG CHAY DUOC" (tinh FAIL, giu vi
  tri Holm).
- Chot 2 diem prereg goc chua ro: (a) coin delist giua thang: phan von cua no thanh TIEN nam im, khong tham gia tai can bang (A chi tai can
  bang giua cac coin con song; B giu nguyen); (b) gross tinh theo close phut 23:59 UTC; net: turnover tai moi lan tai can bang x (phi + truot
  BASE) theo muc 0 prereg goc; funding that.
- Du lieu: funding lay tu dataset chi-gom-2021-2025 `chuyendinh/gridp-t1-funding` (KHONG mount `vz-funding` vi co file 2026); lifecycle:
  bo moi truong/ts >= 2026-01-01 truoc khi dung.

## 2. T4 - sua cong V6 (khong con du lieu tham chieu)
- Su that: du lieu raw ma GRID_T1 dung (~/vz_e1/raw) da bi xoa; tren lake Kaggle vz-kline1m, cung code g_vr.py (sha 2c2f6809, khong sua),
  cung 65 asset + ky cua GRID_T1 cho median VR(60) = 0,90758 (tham chieu 0,913) va ti le z < -1,96 = 63,08 % (tham chieu 56,9 %); BTCUSDT
  du cua so, 0 lo, 0 trung van lech (0,91172 vs 0,90731) => khac ban du lieu, khong phai khac code. Day la so cua CONG KIEM CHUNG, khong
  phai outcome cua T4.
- V6 moi (khai ro la sua SAU khi thay so V6 cu): (a) median VR(60) tren 65 asset + ky GRID_T1 nam trong 0,913 +- 0,010 (do duoc 0,90758:
  dat); ti le significant chi BAO CAO, khong la cong; (b) kiem tren du lieu tong hop (da chay truoc khi co so that): random walk => CI95
  cua S4 chua 0; AR(1) phi = -0,3 theo regime => S4 <= -0,05 va p < 0,01. Ca (a) va (b) dat moi chay E.
- Ghi nhan (khong sua): ham g_vr.vr_z tru trung binh 2 lan va khong hieu chinh mau nho => random walk 288 nen cho E[VR] ~ 1,011; san
  "TB VR_fwd trong RANGE <= 0,92" GIU NGUYEN theo chu (khong noi, khong siet); bao cao kem moc random walk nay.
- Ngay co lo > 60 phut trong cua so dac trung hoac cua so muc tieu: loai va dem (nhu V3).

## 3. Giu nguyen
Holm tren 4 p_C (T1, T3 da co: T1 p_C = 0,0479 nhung truot cong E va san hieu ung => FAIL; T3 p_C = 1,000 => FAIL). C cua T2, T4 chi chay
1 lan sau khi E + frozen_from_E da ghi sha256. Khong 2026. Khong them bien the.
