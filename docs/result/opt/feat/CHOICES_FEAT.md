# CHOICES_FEAT (DEV-FEAT, 2026-11-28) - lua chon khi luat mo ho; MASTER quyet / A1 soat
C1 Cua so: trade dung tai t <=> ts < t-5min; cua so 24h = ts in [t-24h-5min, t-5min) (72h tuong tu). Gom theo 'gio san sang' a=((ts+5min)//1h+1)h.
C2 DVOL/kline nhan = gio MO nen; f01(t)=close nen ts=t-1h, KHONG ffill (thieu nen => NaN). f17/f18 = f01(t)-close nen ts=t-25h / t-73h.
C3 Bien ky han / delta deu INCLUSIVE ([1,7],[20,45],[60,120] ngay lien tuc, T=(exp-ts)/365d; |delta| [0.40,0.60]; put [-0.35,-0.15]; call [0.15,0.35]).
C4 Mo rong 72h: f02-f04 theo tung dac trung; f05/f06 HAI chan cung cua so: 24h neu ca put va call >=20, else 72h neu ca hai >=20, else NaN.
C5 Be mat (E6): 5<=iv<=400, khong thanh ly, T>0; block/combo VAN dung cho be mat (E6 chi loai thanh ly).
C6 f12/f13: loai block+combo (E6); GIU thanh ly (E6 khong noi loai); CHI trade co delta hop le (5<=iv<=400, T>0) - iv=0 thi delta khong xac dinh. f14: loai block+combo, khong can iv.
C7 f12/f13 chuan hoa: S24(t) / mean(|S24|) tren [t-720h, t-1h] (shift 1), min 360 gio; mau=0 => NaN.
C8 Block = block_trade_id khac null (block_rfq_id rong 100 % o mau 2019-2022). Combo = combo_id khac null. Liq = liquidation khac null (M/T/MT).
C9 Do phu: ngay co file + checkpoint = 'phu'; gio t ma cua so 24h (72h) cham ngay khong phu => dac trung trade = NaN (tranh 0 gia do thieu du lieu). Ti so co mau 0 => NaN; f16 = 0 hop le.
C10 RV: log return 1h close perp; return NaN neu thieu nen ke; RV30 can >=648/720 return, RV7 >=151/168; ddof=1; x sqrt(8760) x 100.
C11 R2: z90 = (x_t - mean)/sd tren x shift 1, cua so 2160 dong, min 720 gia tri khong NaN; sd=0 => NaN. Phan vi: cua so 8760 dong, min 2160, noi suy linear; hi = x>=q90, lo = x<=q10, terc 0 neu x<=q33, 2 neu x>=q67, else 1. Tat ca NaN khi x NaN.
C12 Chi instrument dang '<CUR>-' (inverse). Mau 2019-2022: 0 instrument USDC, 0 lech bang instrument. contract_size=1 moi instrument; truong contracts rong => amount = coin.
C13 f19 = ETH f01 / BTC f01, cot 'X_f19_dvol_ratio_*'.

## [MASTER CHOT 28/11]
- C6 DONG Y: f12/f13/f14 GIU thanh ly; f12/f13 chi trade 5<=iv<=400 (delta xac dinh); f14 = moi put khong block/combo, KE CA iv ngoai khoang (code dang lam dung vay; T3 trade 10 iv=500 nam trong f14).
- C4, C7, C2 DONG Y. C9 DONG Y cho dev; ban day du: optfeat.run() TU CHOI neu state/status_full_*.json chua 'done' ca 3 (co --dev de phat trien).
- Lech muc atm_m vs dvol la binh thuong; chi bao theo nam.
C14 (vong 2) Cot n_* / w_* chi co nghia o gio cov24 = 1 (gio dau luoi < 72h va gio cham ngay chua keo: dac trung = NaN, n_* co the thieu).
C15 (vong 3, hygiene) EOH: dung mark_iv x 100 (best_buy_iv / best_sell_iv thua, NaN nhieu); delta = cot delta cua EOH; anh chup gio hh coi la cuoi gio => so voi dac trung tai t = hh + 1h; loc 5 <= iv <= 400, T > 0; ky han do tu ngay het han 08:00 UTC.
C16 BVOL: nen gio nhan theo gio mo, close nen [t-1h, t) so voi dac trung tai t.
C17 R3 tinh tren x (khong phai z90). z90 can them 30 ngay sau khi DVOL bat dau (2021-03-24) => z90 cac dac trung DVOL NaN den ~2021-04-23 (A1 can biet).
C18 Ghi nhan (KHONG doi, theo R5): z90 cua f11 / f15 / f16 duoi rat day (|z90| > 8 o 126 / 94 / 506 gio BTC; f15 2019 z toi 1169 do sd gan 0) - MASTER can quyet co winsorize truoc khi kiem dinh hay chi dung co duoi / tam phan vi; phai ERRATA neu doi.
