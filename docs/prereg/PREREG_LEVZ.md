# PREREG_LEVZ - trang thai CANG DON BAY theo z-score truot tung coin (OI + funding) -> short nhip xa. Tang 1 (do su kien)
Chot boi MASTER 2026-11-25 16:54 +0700, TRUOC khi viet code va truoc khi doc bat ky so nao. Sau commit chi sua bang ADDENDUM truoc khi xem so bi anh huong.

## 0. Nguon goc va boi canh
- Owner 2026-11-25: "Chuan hoa bang Z-Score thay vi nguong cung ... Z-score truot (7 hoac 14 ngay cua chinh dong do) ... khi Z(OI) va
  Z(Funding) cung vuot nguong cuc doan (vd > 2,5) thi truong dang cang don bay. Ket hop xac nhan dong luong gia dao chieu de vao lenh an nhip xa."
- Da do truoc day (KHONG lap lai): OI_STUDY (dOI24h decile cao nhat te nhat nhung chenh so EW khong tach 0); CROWDED_LONG (quantile truot
  L/S cap thi truong: null); FW / SQ (funding nguong cung: gross < phi); VZ E1 + B4 (38 phep, dao dau nam xac nhan); SHORT 21 vong (fade
  sau spike net ~ 0; "cho xac nhan roi vao" = artifact dieu-kien-theo-duong-gia); LIQ_PROXY; GATE_VZ.
- O CHUA do: su kien dong thoi z_OI va z_funding cua TUNG coin cung cuc doan DUONG (dong long, short NHAN funding) lam trigger short.
- Prior cua MASTER: thap. Day la phep thu re de dong / mo o nay, KHONG phai de tim tham so.
- Da kiem dinh: ledger du an > 130 phep; ho nay them k = 4.

## 1. Du lieu va luat nhan qua
- OI 5m: /home/ubuntu/vz/out/metrics5m/<yyyy>/<yyyy-mm>.parquet (ts = create_time UTC ms nguyen xi, sym, oi, oi_value). Quy uoc create_time
  doi nghia 2024-03-04 (OI_FIX_LOG) => luat an toan nhu LIQ_PROXY: tai moc gio t chi dung ban ghi co ts <= t - 10 phut. Dung cot oi (so hop dong).
- Funding: ~/claude_master/1016/carry/fund/funding-YYYY.parquet (ts, sym, interval_h, rate); r8 = rate x 8 / interval_h; tai t chi dung ky
  thanh toan co ts <= t - 1 phut.
- Gia 1m: ~/claude_master/res1109/r1_s1/kl/kline1m-YYYY-MM.parquet (Vision UM). Nen gio dung tu nen 1m DA DONG. Thieu thang trong
  2021-12..2025-12 => DUNG, bao MASTER (khong thay nguon).
- Thanh khoan: ~/claude_master/1016/screen/d1.parquet (qv30).
- Ky: khoi dong tu 2021-12; KHAM PHA 2022-01-01..2023-12-31; XAC NHAN 2024-01-01..2025-12-31 (chi doc MOT lan sau khi ma phan tich dong
  bang, ghi sha256 ma vao result). KHONG doc 2026 (reader phai assert ts < 2026-01-01 UTC truoc khi nap).
- Universe tai t: perp USDT, qv30 ngay truoc >= 20M, da niem yet >= 45 ngay, loai stablecoin / chi so (USDC, BUSD, TUSD, FDUSD, BTCDOM, DEFI,
  BLUEBIRD, FOOTBALL va ten tuong tu), du mau cho cua so (muc 2).

## 2. Tin hieu (tinh tai moi moc gio tron t, UTC; W in {14 ngay, 7 ngay})
- x(t) = ln(oi) cua ban ghi OI moi nhat hop le. z_oi = (x(t) - mean) / max(sd, 0,02) tren cac moc gio s in [t - W ; t - 1h] (khong gom t);
  can >= 80 % moc co gia tri. San sd 0,02 (log) chot truoc: OI gan nhu dung yen thi thay doi < 5 % khong duoc tinh la cuc doan.
- f(t) = r8 cua ky thanh toan gan nhat. z_f = (f(t) - mean) / max(sd, 0,00005) tren cac ky thanh toan trong [t - W ; ky ngay truoc ky gan
  nhat] (khong gom ky gan nhat); can >= 80 % so ky ky vong. San sd 0,005 %/8h chot truoc: funding hay kep o muc nen 0,01 % => sd ~ 0 => z ao.
- DONG LONG: LEV(t) = (z_oi > 2,5) VA (z_f > 2,5) VA (f(t) > 0,0001) (long dang tra CAO HON muc nen; dieu kien co che, khong tune).
- Dot (episode): gio t0 dau tien co LEV = true ma coin do khong co t0 nao trong 72 h truoc (cooldown 72 h moi coin, moi W).

## 3. Vao lenh (SHORT) - hai kieu
- E0 (khong xac nhan): vao tai te = t0, gia P(te) = close nen 1m co open_time = te.
- E1 (xac nhan dao chieu): trong (t0 ; t0 + 24 h], moc gio t1 dau tien co z_r(t1) <= -2, voi z_r = r1h(t1) / sd(r1h tren [t1 - W ; t1 - 1h]),
  r1h = close(t1) / close(t1 - 1h) - 1 (khong tru mean). Vao tai te = t1, P(te) nhu tren. Khong co t1 trong 24 h => khong lenh (dem).
  Moi thu do TU te (thoi diem thong tin da co) - bai hoc R1d.

## 4. Ket qua moi lenh
- H in {24 h (CHINH), 4 h, 72 h}. gross = -(P(te + H) / P(te) - 1). net = gross - 0,14 % + tong rate cac ky thanh toan trong (te ; te + H]
  (rate > 0 => short NHAN). Stress phi 0,24 %.
- net_ex (CHINH) = net - (-(EW)) voi EW = trung binh deu loi suat gia cung cua so cua moi coin trong universe tai te (khong phi) - tuc loi
  nhuan short VUOT phan beta "alt tu troi xuong" (bai hoc SHORT: drift ~ 90 % beta).
- MAE = max(high 1m trong (te ; te + H]) / P(te) - 1; bao ti le lenh MAE >= 10 %, >= 20 %.
- Thieu gia tai te + H (huy niem yet) => dung close cuoi cung co, gan co, dem rieng.

## 5. Gia thuyet (k = 4, Holm) va chi tieu
- A1 = W14-E0, A2 = W14-E1, A3 = W7-E0, A4 = W7-E1. Chi tieu: mean net_ex 24 h > 0.
- Chi MO TA (khong tinh k, khong duoc dung de tuyen bo edge): guong (z_oi > 2,5 VA z_f < -2,5 VA f < 0 => LONG); tung thanh phan rieng
  (chi z_oi; chi z_f); doi chung nguong CUNG (f >= 0,05 %/8h VA dOI24h >= +25 %) de tra loi cau "z-score co hon nguong cung khong".
- Thong ke: bootstrap theo cum TUAN lich (10 000 lan), CI 95 %, p mot phia; Holm tren 4 nhanh o ky XAC NHAN, alpha 0,05. Bao MDE(80 %).

## 6. Tieu chi "CO CUA" (mot nhanh phai dat TAT CA; neu khong => NO-GO, DONG ho, KHONG chinh nguong / cua so / phi roi do lai)
C1 XAC NHAN: mean net_ex 24 h > 0, p Holm < 0,05. C2 KHAM PHA cung dau (> 0). C3 n >= 150 lenh o MOI ky (thieu => DONG vi khong du su
kien). C4 >= 3/4 nam lich (2022..2025) co mean net_ex > 0. C5 bo 5 % lenh tot nhat o XAC NHAN van > 0. C6 net THO (chua tru beta) 24 h > 0
o XAC NHAN. C7 ti le lenh MAE >= 10 % <= 30 %. C8 stress phi 0,24 % van > 0 o XAC NHAN.
- Dat => chi la "CO CUA": buoc sau la prereg tang 2 (mo phong danh muc co von / ky quy / gioi han vi the + HO 2026 MOT lan), owner quyet.

## 7. Kiem hop le (bat buoc, bao trong result)
V1 nhan qua: xoa / lam nhieu moi du lieu sau t tren mau 200 moc => tin hieu tai t khong doi. V2 dau funding: kiem tay 3 lenh (rate > 0 =>
short duoc cong). V3 gia vao = close 1m dung phut (10 lenh). V4 mo ta: so dot moi nam / moi nhanh, ti le dot ma san sd cua z_f hoac z_oi
dang ap, phan bo f(t) va dOI tai t0. V5 tai lap: chay 2 lan cung md5.

## 8. Rang buoc thi hanh
Python offline tren Oracle (logging, khong print); KHONG Java / sim / Kaggle / 242; viec nang qua
mkdir -p ~/claude_master/locks && flock -w 3600 ~/claude_master/locks/oracle_heavy.lock nice -n 10 <cmd> (khong long flock; RAM trong >= 4000 MB,
dia >= 15 GB; doc theo thang, khong concat ca 4 nam). Thu muc ~/claude_master/w3/levz/. Ket qua docs/result/LEVZ.md + dong ledger.
RUN (agent) -> A1 (agent KHAC) -> MASTER tu kiem >= 3 so -> bao owner. Khong gui owner so chua audit.
