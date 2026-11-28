# PROGRAM_OPT_1128 - ERRATA1 (28/11/2026 ~20:15 +07). Viet khi CHUA co dac trung va CHUA ghep voi bat ky ket qua nao
(da co: du lieu tho DVOL + mot phan trade; khao sat su that ~/claude_master/w3/opt/SCOPING_B_1128.md). Sua muc B, bo sung O.

E1 CUM LENH = khoa (symbol, thoi diem dong) dung nhu sim Java (moi dong printDone = mot leg). KHONG dung
   levz_llv/out/clusters.parquet (gop nham cac chuoi "cham": cum moi mo dung phut cum cu dong; vi du c0s42 3 146 thay vi
   3 402 cum). Ghi nhan: phan tich LLV 27/11 dung dinh nghia cum cua prereg X3 (leg noi tiep / chong) - khac dinh nghia cua he.
E2 SAU LEDGER = SAU SEED CUA MOT HE: 4 seed DEV (p15_stab s2 k c0s42 / 7 / 123 / 13) va 2 seed r1-a3 (A1, S7) co cau hinh
   giong het (prof_run trung md5, cung jar cc0f9d11, 2021-07..2025-12, von 35 000), chi khac model gate p15 + snapshot mapper.
   => BO yeu cau "cung dau tren hai bo". Phan tich chinh tren CUM DUY NHAT (khoa: symbol + phut vao leg dau; ket qua = trung
   binh qua cac seed co cum do); bao them tung seed (do vung). Suy dien bang dich vong chuoi dac trung (R4) - mot offset cho tat ca.
E3 B1 muc NGAY: bo cum tu "giong X14". X14 (property SIM_LOSER_TS_EXT_DAYS) CHI hoan time-stop, khong chan vao lenh. Loc vao
   lenh theo ngay / theo gio la co che MOI: muon xac nhan bang sim (B4) phai sua Java + jar moi + cong parity khi tat; chi lam
   khi B1 co BAC-1, prereg rieng, owner build jar.
E4 B2 TRAILING - lam bang ENGINE THOAT THAT, khong xap xi bang close:
   (a) Du lieu: nen 1 phut OHLC tu data.binance.vision (futures/um, monthly klines 1m) cho cac (symbol, thang) phu tung cum tu
       phut vao den +45 ngay (close1m.npy chi co close, khong du).
   (b) Engine: sua ~/claude_master/w3/add24_wt/research/exitfit/exit_engine.py theo dung Java commit a8690d46: arm khi HIGH 1 phut
       >= VWAP x (1 + arm); SL = VWAP x (1 + r), r = lam tron 0,005 cua (dinh - min(dinh, gap)); dat SL o nen arm, tu nen sau
       khop khi LOW <= SL voi gia min(SL, OPEN); ratchet; time-stop 168 gio tu leg DAU cho cum chua arm, gia min(open, close);
       hoan X14 toi 336 gio; DCA -50 / -75 / -90 % tu gia leg dau (toi da 4 leg) voi tao lai cum (arm reset, VWAP moi); phi +
       funding nhu sim.
   (c) CONG PARITY (bat buoc truoc moi phan thuc te): voi tham so baseline (arm 7 %, gap 3 %), engine phai tai lap phut thoat va
       gia thoat cua ledger cho >= 99 % cum (leg DCA lay dung nhu ledger). Khong dat => dung B2 / B3, bao owner.
   (d) Phan thuc te tung cum (KHONG co phan hoi danh muc: U, skipFull, vao lai cung coin - ghi ro): luoi arm {3, 5, 7, 10, 15} %
       x gap {2, 3, 5} % (15 bo; goc 7 / 3), moi thu khac giu nguyen. (i) Mo ta: bo tot nhat toan cuc [in-sample].
       (ii) TUONG TAC voi trang thai: 5 dac trung BTC (dvol, atm_s, term, skew_s, vrp30; + dac trung BAC-1 cua B1 neu co), chia
       tam phan vi theo phan vi truot 365 ngay (q33 / q67). WFO nam kiem 2023, 2024, 2025: tren cac nam < Y chon (1) bo toan cuc
       tot nhat va (2) bo tot nhat TUNG tam phan vi; thong ke = tong loi suat cum nam Y cua (2) tru (1), cong 3 nam.
       p = dich vong chuoi dac trung (2 000 luot). Ho FDR = so dac trung. Bac theo R5.
E5 B3 DCA: DCA cua he o -50 / -75 / -90 % chi kich o ~50 cum moi seed (don vao 2022 va 10/2025) => KHONG du mau de kiem "DCA
   hien tai theo trang thai"; chi mo ta. Vi owner hoi DCA, them ho moi (chot truoc): DCA NONG phan thuc te bang cung engine:
   them MOT leg tai -x % tu gia leg dau, x trong {10, 20, 30}, co bang leg dau, tao lai cum nhu engine; so voi goc bang loi
   suat tren VON TOI DA da dung cua cum (khong phai tren von leg dau). (i) Mo ta toan cuc [in-sample]. (ii) TUONG TAC nhu E4
   (trang thai quyet dinh CHO / KHONG cho leg them), WFO 2023-2025, p dich vong, FDR theo so dac trung x 3 muc x.
   Ghi ro: bo qua ngan sach U va slot => moi BAC-1 phai qua sim Java (can sua Java ~40-80 dong + parity) truoc khi tin.
E6 VE SINH trade (chot theo su that du lieu, khong nhin ket qua): be mat IV (f02-f09) dung trade co 5 <= iv <= 400 va khong
   phai thanh ly (trade iv = 0 hoac cham tran ~500 bi loai); dong lenh f12-f14 loai trade block va combo (chieu chu dong khong
   ro), f10-f11 va f15 dung tat ca tru thanh ly; f16 dem trade thanh ly. DEV bao phan phoi; doi bo loc phai ERRATA.
E7 Gia BTCUSDT / ETHUSDT perp Binance Vision bat dau 2020-01 => giai doan mo rong cua A1 la tu 2020-02-01.
E8 Thu tu chay: A1 va B1 (chi can dac trung + ledger) truoc; B2 / B3 sau khi qua cong parity E4(c).
