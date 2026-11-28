# A1_B - kiem toan doc lap DEV-B (agent A1-B, 2026-11-28)
PHAN QUYET: PASS-WITH-MINOR (engine KHONG dung dap an ledger; tai lap dung; co 3 viec PHAI lam truoc phan thuc te, muc 9).

1 sha256: 33/33 file khop SHA256SUMS.txt. CUM (code rieng, csv thuan): c0s42 3402, r1a3_a1 3559 = DEV; lech 0 o moi cot (t_first, t_end, gia, status, n_legs, capital, pnl, ret, leg_t, leg_e); tong PnL = ledger (103932.2337 / 110391.1926); legs 1/2/3/4 = 3352/41/8/1 va 3506/44/8/1; 0 cum co nhieu tp/status; 0 chong lan cung sym. capital = sum(margin) = sum(e*q) (ti so 1 +-1.5e-7, lev 1) => ret = PnL/von toi da: hop ly. TZ: 300/300 va 299/299 gia vao = close nen tai lech 7h (lech 0h: 12, 14h: 2). unique: 6896 = toi; 0 trung trong seed; LUU Y 110 cum (sym,t_first) nhieu seed co thoat/leg KHAC nhau.
2 Engine vs Java: thu tu tick (update gia+funding -> time-stop neo leg dau, min(O,C), X14 -> cong arm theo HIGH, arm khong khop cung nen -> SL khop minPrice<=SL tai min(SL,OPEN) -> ratchet SL moi>SL & >entry, minPrice=close -> merge DCA: VWAP float32, minPrice=close, SL=null) khop SIM:1000-1111, OTI:133-268, TU:52-58, SIM:1199-1260. Phi = q*e*(0.000982+2*0.000067) tren notional VAO (dung calTp). Funding = rate*qty*close, moc (last, t], tu leg dau, mang qua merge = accrueFundingMark OTI:347-365. (a) dau vao simulate = (t,e,q) leg + nen + tick + ext_days(prof_run) + cua so t0+45d: KHONG dung phut/gia/ly do/PnL ledger -> PASS.
3 parity_b.py: 20881/20881 (DEV). Vong rieng 402 cum-seed (seed 13; dca 40, x14 40, ts168 40, delist 12, openfill 34, random 236): 402/402.
4 Dot bien (3000 cum-seed): m0 100; m1 85.6; m2 83.1; m3 94.1; m4 24.0; m5 99.4 (tren cum DCA n=44: 59.1); m6 94.4; m7 27.3; m8 84.4. Moi dot bien deu bi bat.
5 test_b: 28/28 OK. 7 ca nen GIA rieng (arm3/gap2; arm15/gap5; extra-10%+hoi; extra->time-stop; extra+DCA -50%; ret/von toi da 189; leg DCA bi bo khi thoat som): 7/7 dung tinh tay.
6 OHLC 30 file: 30/30 CHECKSUM ok, so dong + ts trung, sai so tuong doi 0 (parquet float64); nen phang vol 0: 2506/1297410 (0.19%). 6 thang delist: Vision 404, nen cuoi truoc thang -> dung.
7 Khong tim thay ket qua phan thuc te tren cum that (chi docstring/CHOICES/DEV_B nhac extra_dca).
2b HANH VI DCA PHAN THUC TE: leg DCA ledger chen DUNG timestamp ledger; thoat som -> bi bo (dung). Engine KHONG tu sinh DCA theo muc gia. Neu cum song LAU hon ledger (gap rong/arm cao/ts dai) thi moi DCA sau thoi diem thoat goc BI THIEU -> sai lech co huong. Cum chua dong sau 45 ngay tra ok=False (bars_end) -> neu bo qua la thien lech chon mau.
2c extra_dca: kich khi CLOSE<=firstEntry*(1-x), khop gia CLOSE cung nen, sau buoc thoat, khong cong tin hieu/ngan sach -> LAC QUAN ve kha nang khop (sim chi DCA o tick co tin hieu + budget).
9 PHAI SUA: (i) danh dau + dem cum phan thuc te co t_exit > t_end_ledger ma LOW cham firstEntry*(1-0.5) trong (t_end_ledger, t_exit] (DCA thieu), bao rieng/loai; (ii) xu ly bars_end (khong am tham bo); (iii) gan nhan extra_dca la can tren lac quan, them bien the khop o OPEN nen sau. LUU Y: 110 cum unique khong dong nhat giua seed; khong phan hoi danh muc (U, skipFull, vao lai cung coin); live kich theo MARK ~10 s.
sha256: 
5bf55316  code/exit_engine_b.py
774ca2ea  code/parity_b.py
9d7fde6b  out/clusters_unique.parquet
7e80cc2f  out/PARITY_B.json
97b03389  work/ohlc_manifest.csv
a2a00180  test/test_b.py
