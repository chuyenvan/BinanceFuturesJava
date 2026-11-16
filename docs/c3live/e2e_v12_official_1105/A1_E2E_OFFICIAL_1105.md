# A1 audit luot chinh thuc (iii) 11-05 - out1105_1117_0132 (harness def1f034)
KET LUAN: (I) nguyen ven PASS. (II) lech AINUSDT = THIEU-SOT-DAU-VAO-HARNESS (khong nhan khai truoc nao ap duoc) => E2 sau phan xu = FAIL (giu nguyen) => (iii) FAIL.

## (I) Nguyen ven
1. Khoa OFFICIAL_1105.lock (r--, 01:32:27) head=def1f034 a1=def1f034 errata= rong. Chi 1 thu muc out1105_*; fx1105 mtime 01:32:31-01:34:26 (trong luot); khong co result.json dev nao START=1793836800000 (out, out_v2..v5 = 10-30). Worktree c3_e2e HEAD def1f034, git status sach. labels md5 7af0c00e... (n=0) o ca 7 luot; env242 md5 8956befd... dong nhat. jar md5 641803565297d4065d90245e04a00f11 (jar_ok theo bo cham, A1 chua doi chieu doc lap voi md5 r4u3fin2).
2. Tu tinh tu legs/fills R0: 24 SUBMIT; budget 225.0000/216.5647/208.4436; 24/24 budget = 0.0225*C_eff*(1-U/0.6), U tu fills (BUY tru SELL theo thoi gian), max |rel| 1.4e-7 (C_eff = cot eq cua jar: 10000 / 9990.917). Thoat: 24 SELL, 3 TRAIL_TIME_STOP + 21 trail. ARM_CUNG_NEN kiem bang nen fixture: JCT arm 23:19:20 SL 0.0031075, nen 23:19 L=0.003106 -> khop 0.003106 cung nen; UAI arm 01:44:30 SL 0.105288, nen 01:44 O.0920 L.0918 H.1083 C.1028 -> khop 0.1028; CAP doi SL 0.115993 21:23:20, nen 21:23 L=0.11358 -> khop 0.11358. R-1000 24/24 SUBMITTED.
3. Khong PASS rong: F1 dung 1 leg chan (UAI 22:51, submitted 0, fin_excl 1; HUMA/IDOL van SUBMITTED); D1 S-DCA 2 cum x 3 bac day du; X1 n=24. K1 la tieu chi vang mat loi (0 dong ERROR/latch/KHAN). D1 tu nhien = KHONG XAY RA (khong tinh PASS).

## (II) AINUSDT
Bang (that log 22:53 vs R-OLD): sym | qty that/rep | sizingPx that(notional/qty)/rep(open b+1) | C_eff that/rep | U that/rep | |db|/b
JCT  | 11642/11860 | 0.0030440/0.002988 | 9999.50/9998.43 | .0329345/.0328849 | 1.96e-5
AIN  | 131/131     | 0.26841/0.26732    | 9999.50/9998.43 | .0364133/.0364292 | 1.35e-4
Q    | 1291/1289   | 0.027110/0.02715   | 9998.40/9998.43 | .0399249/.0399368 | 1.86e-5
ARIA | 238/238     | 0.14936/0.14922    | 9999.50/9998.43 | .0293827/.0293327 | 1.94e-5
(C_eff that = budget/(0.00375*(1-U/0.6)) tu dong log [C3-LIVE] SUBMIT; dong 736493-736850 full.log@1793928180_135437659.gz)
- Gia khop: 23/23 avg that = fill replay = close nen quyet dinh (ref). U tang theo qty*gia khop o CA hai ben. Gia thuyet MASTER (U lech do gia khop) SAI.
- Lech qty do gia SIZE: jar dung price_realtime (C3LiveHook.onLeg, tuoi <=30 s); rig dung open nen b+1 (CrashDayRig.java:896).
- Lech chinh do C_eff: equity c3 that (C3MainEquity.c3Equity, cache 60 s, UPL theo markPrice) = 9999.50 cho CLANKER..AIN, lam moi giua AIN (22:53:09.445) va Q (09.891) -> 9998.40; replay dung 1 gia tri 9998.43 (eq_at 22:53:00) cho ca phut. relK = -1.07e-4 cho 8 leg CLANKER..AIN, +2.5e-6 tu Q.
- Vi sao rieng AIN: |db|/b = relK - dU/(0.6-U) = -1.07e-4 - 2.8e-5. Truoc AIN dU am (bu tru relK, vd JCT -1.07e-4 + 8.8e-5); JCT replay qty 11860 > 11642 lam dU doi dau o AIN -> cong don. CLANKER sat nguong 9.7e-5. Neu chi khop U: AIN van 1.07e-4 FAIL; neu chi khop C_eff: 2.8e-5 PASS.
- git diff bc030d76(r4q) 5e10325b: 0 dong o C3LiveHook, C3MainEquity, C3LiveEntry, LiveBookC3 (c3live chi C3LiveRuntime dong legacy blocksC3). Khong phai khac jar. exchangeInfo: step AIN/JCT=1 hai ben, qty = floor(budget/px) dung o ca hai -> khong phai exchangeInfo. AIN khong lien quan LEGACY (SUBMIT ca 2 ben).
- Phan loai: THIEU-SOT-DAU-VAO-HARNESS (chac chan cao cho co che; gia tri equity that khong log truc tiep). E2 sau phan xu: FAIL (22/23, 1 lech khong nhan).

## 7. De xuat sua DAU VAO (khong doi nguong, khong them nhan)
- Thieu 2 dau vao trong-phut: (a) price_realtime luc sizing tung leg; (b) markPrice + thoi diem lam moi cache equity c3 (60 s) cua 3 vi the 22:52.
- (a) nap gia size tung leg cho R-OLD 22:52-22:53 = notional/qty tu dong SUBMIT that (chi GIA). Rui ro khop nguoc: gia nay suy tu qty that => qty gan nhu chac khop; budget van do jar tinh doc lap nen chua tu-dong. Uu tien nguon doc lap neu co (kiem pull242/2026-11-05/dumps co price_realtime theo giay khong).
- (b) KHONG duoc nap C_eff/equity suy tu budget (tautology truc tiep). Chi chap nhan nap markPrice theo giay tu nguon doc lap + cho rig lam moi equity dung pha cache that (moc lam moi suy tu thoi diem, khong tu gia tri). Neu khong co nguon gia theo giay doc lap: (b) khong sua duoc => E2 khong the dat ma khong tautology; MASTER ghi FAIL + nguyen nhan, hoac prereg moi (khong phai errata).
- Theo prereg 2: errata truoc, chay lai, bao cao ca 2 luot.
