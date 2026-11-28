# CHOICES_B - cho Java mo ho / lua chon cua DEV-B (PROGRAM_OPT muc B). Java = git show a8690d46:src/main/java/com/binance/chuyennd/...

## [MASTER CHOT 28/11]
1. Viec DEV tu sua dieu kien STOP cua P2 bang so do that (parquet 0.87 MB/file tren 197 file pilot, ~3.7 GB) thay he so
   doan 0.9: CHAP NHAN lan nay. Tu nay MOI thay doi dieu kien dung phai bao MASTER TRUOC khi chay. Giu cua so +45 ngay.
   Nguong tu dung dia 11 GB giu nguyen.
2. Funding phan thuc te: keo fundingRate monthly tu Vision (kiem CHECKSUM) cho cung (sym, thang); ham funding theo dung
   sim; KIEM khop funding ledger tren thoat goc (bao phan phoi sai so). Khong am tham dung funding ledger cho phan thuc te.
3. float32: chap nhan CO DIEU KIEN - neu parity day du co ca lech do lam tron gia thi tai lai symbol do o float64;
   quet so chu so co nghia + double-rounding tren zip goc ~50 symbol gia cao nhat (out/FLOAT32_SCAN.json).
4. Cum khong co tick (sym khong co trong exchange_info_pin.json) => KHONG normalize (nhu Java CS:217-221): DONG Y.
5. Hai chi tiet minPrice-reset va guard delist: GIU, dan dong Java + test rieng (test_minprice_reset_*, test_delist_*).

## Lua chon cua DEV (dan Java)
C1 Cum = (sym, end) (SIM closeOrder 1127-1160 chep end/tp/status moi leg). Kiem: 0 cum co >1 gia thoat / status.
C2 Gio ledger UTC+7: TraceOrderDone in theo mui gio may chay; chung minh thuc nghiem (P1_TZCHECK.json: lech 7h khop
   98.7-100 %, lech 0 / 14h <= 0.7 %).
C3 Nen dau tien xu ly la nen SAU phut vao: SIM vong tick goi startUpdateOldOrderTrading (cap nhat cum CU) truoc khoi
   createOrderBUY (SIM:247-258 roi 335-404) => cum tao cuoi tick.
C4 minPrice: updatePriceByKlineSimple minPrice=min(minPrice, LOW) (OTI:135-138); KHI arm (OTI:194) va KHI ratchet
   (OTI:265) minPrice = lastPrice (= CLOSE nen do). => nen sau khop khi min(close nen arm/ratchet, LOW nen sau) <= SL,
   KHONG chi LOW <= SL. mergeOrder: minPrice = close nen leg (SIM:1214).
C5 Nen arm: updateStatusNew dat SL roi return (BLOCK_INTRABAR_LOOKAHEAD=true, CFG:122); SIM sau do goi updateTPSL cung
   nen (SIM:1104-1109) - khong doi SL vi SL moi == SL. Khop: status STOP_MARKET_DONE neu SL > entry, gia min(SL, OPEN).
C6 Cong arm hai lop: SIM:1098 HIGH >= entry*(1+arm) (float32) VA OTI:191 rate=(HIGH-entry)/entry > arm (nghiem).
   Ratchet OTI:256 rate >= arm; SL moi > SL cu va > entry.
C7 trailRate: FIX_B1=true nhung TS_MAX_GAP == TS_MAX_GAP_WEAK == 0.03 => nhanh pNoPump vo hieu; GIVEBACK 1.0
   (result.json overrides TS_GIVEBACK_RATIO=1.0; default Java 0.5). Math.round(float) = floor(x+0.5f).
C8 normalizePrice: BigDecimal(Float.toString) FLOOR theo tick, setScale HALF_UP (CS:217-238); tick tu
   /home/ubuntu/java/exchange_info_pin.json (gia dinh cung file sim dung - parity xac nhan).
C9 Time-stop: t - clusterFirstLegTime > 168h (nghiem), t = khoa tick = open_time nen; X14: floorDiv(t, 86400000) thuoc tap
   ngay (Configs:922-933, khoang dong ca hai dau) va t - anchor <= (168+336)h => hoan. Gia min(open, close).
C10 Delist (SIM:465-480 + 905-913): chi o moc gio KHONG phai nua dem (nhanh else cua time % DAY == 0), ticker khong
   "available" va timeUpdate < t - 2 ngay => dong tai lastPrice, end = timeUpdate. Engine: chi xet nen THIEU (nen
   volume 0 & H==L van duoc cap nhat timeUpdate vi startUpdateOldOrderTrading chi can ticker != null).
C11 Funding (SIM_FUNDING_MARK=true, CFG:137/954): accrueFundingMark moi nen: cac moc settle trong (fundingLastSettle |
   clusterFirstLegTime, t] cong rate*qty*close(nen t)*FUNDING_SCALE(1) (float32); carry qua merge; computeFundingOnClose
   bu toi timeUpdate. Toan bo funding cum gan vao leg dau. NGUON sim: Aerospike DataManagerAerospikeFloatSim.getFundingMap
   (FundingFeeManager.java:91-150) - KHONG phai Vision; khoa = thoi diem settle. Engine dung Vision fundingRate
   (calc_time, last_funding_rate) => do sai so so voi ledger (PARITY_B.json "funding").
C12 Phi: calTp (OTI:274-300) qty*(tp-entry) - qty*entry*RATE_FEE(0.000982) - qty*entry*SLIP(0.000067)*2 - funding.
C13 Gia Vision float64 -> float32 (sim KlineObjectSimple la float). Rui ro double-rounding: xem FLOAT32_SCAN.json.
C14 Che do TAI LAP: leg DCA lay dung ledger; engine khong quyet DCA (sim chi xet DCA o tick co tin hieu, SIM:336-404).
C15 extra_dca (E5, CHUA parity): leg them khi CLOSE nen <= firstEntry*(1-x) (sim DcaUtils dung lastPrice=close tu gia
   leg dau), qty = mult * qty leg dau, gia vao = close nen, xu ly SAU buoc cap nhat nen (nhu createOrderBUY), merge =>
   arm reset, VWAP moi, time-stop van neo leg dau. Loi suat = PnL / tong e*q moi leg (von toi da da dung, lev 1).
   Bo qua U/throttle/slot (khong phan hoi danh muc).
C16 Ledger ket thuc dong cum cuoi 2025-11-28; hold toi da 504h => cua so +45 ngay du (kiem: n_open_at_window_end).

## [MASTER CHOT vong 3 - 28/11]
6. DUYET: thang OHLC khong co tren Vision SAU ngay huy niem yet = KHONG CO NEN (guard delist kiem that). Cum khop ledger
   (phut, gia, ly do) => vao parity, duoc dung ve sau; cum KHONG khop => loai khoi phan thuc te, liet ke rieng.

## Bo sung vong 3 (DEV)
C17 6 thang thieu (AKRO 2022-06/07, ANC 2022-06, BZRX 2022-01, KEEP 2022-03, LUNA 2022-06) da XAC NHAN sau huy niem yet
   (code/delist_check.py -> work/delist_months.json): nen cuoi Vision < dau thang thieu, thang truoc bi cat duoi, khong co
   monthly nao trong 6 thang sau (HEAD), daily cung 404. Nen cuoi: AKRO 2022-05-27 09:16, ANC 2022-05-13 06:40,
   BZRX 2021-12-19 02:10, KEEP 2022-02-15 02:03, LUNA 2022-05-13 06:49 UTC.
C18 Engine `bars_until` (= cuoi cua so): het nen ma bars_until - timeUpdate > 2 ngay => ap guard delist tai moc gio dau
   tien thoa (SIM:465-480 chay theo dong ho tick, khong can nen cua symbol). Ap cho MOI cum (trung thanh Java); voi cum
   co du nen toi cuoi cua so thi khong tac dung.
C19 Funding: Vision fundingRate (calc_time, last_funding_rate) khop funding ledger toi ~5e-10 von (p99) cho moi symbol
   TRU LIT: ledger funding = 0 cho ca 100 cum-seed LIT (sim/Aerospike khong co funding LIT), engine tu Vision != 0.
   Sai so lon nhat 0.38 % von cum (LIT 2022-11-08, giu 21 ngay). Phan thuc te: dung funding Vision (dung thuc te); LIT
   la lech DU LIEU cua sim (khong phai cong thuc) - can MASTER chot: (a) Vision cho LIT, ghi chu; hoac (b) 0 nhu sim.
C20 FLOAT32_SCAN: 50 symbol gia cao nhat (YFI, MKR, BNB, BCH, ZEC, TAO, SOL ...): so chu so co nghia lon nhat <= 7
   (max 6), 0 gia co double-rounding float64->float32 khac Float.parseFloat => KHONG can luu float64. Parity 100 %
   => khong co ca lech do lam tron gia.
C21 Moc funding: mau 1/20 file: ~38 % calc_time Vision co phan ms le (0-47 ms); chu ky 8 / 4 / 2 / 1 h deu co; cong thuc (from, t] voi t = open
   nen phut => moc settle 08:00:00.00x duoc tinh o nen 08:01 (gia close nen 08:01). Khop ledger => sim cung dung moc co ms le.
