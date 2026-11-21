# PREREG_RETRAIN_DIAG_DRAFT - chan doan TUNG MODEL sau RETRAIN T1 FAIL (NHAP, agent thiet ke 2026-11-21; MASTER chot + commit TRUOC khi chay)
Can cu: docs/prereg/OWNER_DECISION_PILOT_1121.md (c3a9f01b: Q1 pilot model cu; Q2 U4a chan doan Q3, U4b kiem MOT lan 10-01->cuoi du lieu;
Q3 khong tune tham so chien luoc theo model tren quy kiem chung; tham so phu thuoc thang diem = hieu chuan lai theo cong thuc co dinh tu diem
TRUOC moc train; quy tac chon tham so theo model phai kiem tren NHIEU quy DEV truoc). Ket qua T1: docs/result/retrain_pilot_t1/RESULT_RETRAIN_T1.md
(932770e5): Lane N ROI D5 -6,44 % vs Lane L +3,12 % (d -9,56 pp), 164 vs 110 lenh, 35 lenh chung. Kiem ke code: v12/RETRAIN_DIAG_DEV.md.
Moi kernel / script doc 2026 log "HOLDOUT_UNSEAL_2026_1121 (U4a|U4b)". Cong cu: chain/a3/sim fork da qua P-N1/P-N2 (RETRAIN_PILOT).

## 0. Nguyen tac
- N1 Tham so chien luoc GIU NGUYEN cau hinh r1-a3 (profile r4_kg0_k16_f015_g155 + overrides HO5); jar sim cc0f9d11 cho moi lane U4a (tru lane "R"
  can jar moi - muc 2.3).
- N2 U4a la CHAN DOAN: khong chon cau hinh nao bang PnL Q3. Nhanh cua cay quyet dinh (muc 3) dua vao DO LUONG CO CHE (khong PnL); PnL cac lane
  chi la kiem tinh nhat quan (mau thuan co che vs PnL => "khong ket luan" => nhanh mac dinh).
- N3 Cong thuc ung vien = 1 cong thuc duy nhat, ghi ra truoc U4b; thanh phan nao co the kiem tren DEV (2022-2025) thi PHAI qua DEV truoc (muc 4).
- N4 U4b chay MOT lan (muc 5); FAIL -> giu model cu, khong lam lai tren cung cua so.

## 1. Tham so phu thuoc model (tom tat; chi tiet + file:dong o RETRAIN_DIAG_DEV.md muc 1)
- Gate (nhanh PREDICT, cau hinh r1-a3 SIM_GATE_ROLLING_MODE=ratio): r = p15 / (max(0.26787, sp/0.15*1.28760) * 1.55) (GateRollingRatio.java
  threshold/ratio; EntryGate DYN_MIN/SCORE_BASE/DYN_MULT final, SIM_GATE_DYN_SCALE=1.55). PASS <=> r > q_t, q_t = phan vi 0,999950829 cua bo dem
  r CUA CHINH run trong 90 ngay truoc, tinh lai moi gio, causal (GateRatioBuffer computeQ), warm-up 7 ngay -> base 0.008. Bo dem la static cho ca run,
  KHONG reset / reseed khi doi fold (sim WFO) hay doi model (live: LiveGateRollingRatio nap file persist LIVE_GATE_ROLLING_FILE + seedHistory tu p15
  qua khu cua model DANG chay). => thang diem p15 (va sp) co tu-thich-nghi nhung TRE 90 ngay; voi duoi 0,99995 rat nhay voi duoi phan phoi.
- sp (symbolPred) = 1 - P(win) cua net015 sau khi A3 gan lai theo thu hang S1 (a3lib.assign: giu MULTISET P(win) cua tick, S1 tot nhat nhan P(win)
  cao nhat; A1 tradfi / thieu diem bi day xuong cuoi). sp vao gate qua factor (thang diem net015 tuyet doi) va vao chon top-K (SELECTOR_RANK_TOPK=24
  theo override; profile ghi 16 - override thang) - thu hang chi phu thuoc S1 (A3) => bat bien thang diem S1.
- Trailing STRONG/WEAK (TS_PNOPUMP_WEAK_THR 0.29 tuyet doi tren sp): r1-a3 dat SIM_TS_MAX_GAP = SIM_TS_MAX_GAP_WEAK = 0.03 => hai nhanh cung tran
  => nguong 0.29 KHONG con tac dung (kiem: Configs.java:145,527,918-922).
- Base 0.008 (SIM_MIN_MOMENTUM_15M): chi o warm-up 7 ngay dau run va nhanh BIG_DOWN / DCA_LEVEL1 (nguong p15 TUYET DOI) - phu thuoc thang p15.
- Bins predict_wf: RAW net015 (P(win) theo (ts,sym)) -> A3 -> funding.bin (forward-fill 15'); khong binning/quantile thang diem nao khac.
- Do duoc tu log (khong phai PnL): GATE-RATIO 2026Q3 pass/seen: Lane N 142 / 2 912 910 (rho 4,9e-5), Lane L 94 / 3 041 795 (3,1e-5); Q2 trung
  122 / 3 011 221. Muc tieu thiet ke rho ~ 1 - pct = 4,9e-5.
- Nghi pham tu CODE (chua co so moi): (1) p15 T1 co duoi nang hon (Q3: max 0,145 vs 0,092, p99 0,0136 vs 0,0131) + bo dem gate 90 ngay chua
  "nhan" thang moi => pass +51 % Q3 => them lenh ma Lane L khong vao; (2) S1 T1 hoc 45,1 % dong voi feature Vision ma rk_oi_delta24h chi trung
  0,2 %, ls_global 90 % voi DEV (K3) => thu tu top-K doi (top-8 trung 81 %); (3) net015 T1 gan thang cu (p50 0,420 vs 0,417; spearman 0,984) =>
  it nghi nhat, nhung vao gate qua factor.

## 2. U4a - lane chan doan (2026Q3, cau hinh r1-a3, 2 seed: a1 + s123 - xem P1 muc 7)
### 2.1 Lane (P = p15 T1, S = S1 T1, M = net015 T1; chu cai thuong = model live)
| lane | p15 | S1 | net015 | du lieu 2026 (Q1-Q2 = Lane L byte) | ghi chu |
|---|---|---|---|---|---|
| LLL | live | live | live | = Lane L (co) | moc |
| P (Pss) | T1 | live | live | pred N + bins L | |
| S (pSs) | live | T1 | live | pred L + bins0701 = assign(S1 T1, RAW_L) | |
| M (psM) | live | live | T1 | pred L + bins0701 = assign(S1 live, RAW_N) | |
| PS, PM, SM | ... | ... | ... | to hop tuong ung | tuy chon (P2 muc 7) |
| NNN | T1 | T1 | T1 | = Lane N (co) | |
| PR, NNNR | T1 + reseed | ... | ... | can jar moi (2.3) | sau cong jar |
- Du lieu: chi la to hop artefact DA CO (pred_2026 L/N, RAW_L, RAW_N tu rt-chain-n26, S1 live / T1) qua rt_a3n (them che do chon S1 / RAW) +
  dataset rt-<lane>-data26; cong moi lane: bins / pred byte-trung phan lay tu L hoac N (sha) va rt_nchk 100 % (dong end < 07-01 trung L).
### 2.2 Do luong co che (KHONG PnL) - chay TRUOC sim, re
- D-cal (p15): phan vi duoi p15 T1 vs fold_20 tren DEV 2026Q2 (gate_dataset_full, truoc S3, khong nhan) va Q3 Vision: q99, q99,9, q99,99, max;
  ti so duoi T1/live; tuong tu cho r (can sp: dung bins L cho ca hai) - ghi bang.
- D-gate (tu log sim, khong PnL): pass/seen theo quy cua moi lane (GATE-RATIO quarterCounts), so lenh, so lenh chung voi L.
- D-ruler (Tang A, AGENT_RUNBOOK luat 12; nhan Vision Q3, khong PnL): p15 IC vs label_oldbasket; net015 AUC / rank-IC theo tick (y = retEnd_4h >
  0,015); S1 rank-IC + lift@8 / precision@8 (g1lite tren pool Q3) - T1 vs live, CI bootstrap tuan (block 7 ngay, 2000, seed 20261121).
- D-src (S1): (a) bang lech feature DEV vs Vision theo cot tren doan chong lan (14 118 dong lead-in 12/2025, da do K3) + tren 2025H2 lat det-a
  (HO4-P1 P3-DEV feat_v2 61,5 %, rk_* ~0-6 %); (b) ruler S1 T1 tach 2 nhom feature (rk_* vs con lai) bang permutation tren Q3 (mo ta).
### 2.3 Bien the "R" (hieu chuan lai bo dem gate) - KHONG lam duoc voi jar cc0f9d11
- Jar sim chi co SIM_GATE_ROLLING_MODE/PCT/DAYS; khong co khoa seed / dump / reset bo dem (kiem chuoi hang so trong class). Can thay doi code (prereg
  rieng + cong parity G0 byte-identical khi tat): SIM_GATE_RESEED_AT=<ms list> + SIM_GATE_RESEED_P15=<pred.bin cua model moi> => tai moc, xay lai
  bo dem r tu (p15 MOI, sp da ghi) cua cac ung vien 90 ngay truoc (sim phai luu (ts, sym, sp) ung vien trong bo dem - them 1 mang song song).
  Luu y: p15 T1 tren 90 ngay truoc S3 la IN-SAMPLE (train toi S3-15') -> duoi co the lech; phuong an thay the khong in-sample: anh xa phan vi
  (quantile map) p15 moi ve phan phoi p15 cu tren cung 90 ngay (cong thuc co dinh, khong PnL).
### 2.4 Quy tac quy ket (ghi truoc; MO TA)
- Delta_X = ROI_D5(lane X) - ROI_D5(LLL), X in {P,S,M}; Delta_tot = ROI(NNN) - ROI(LLL) = -9,56 pp; tuong tac = Delta_tot - sum Delta_X.
- "X la nguyen nhan chinh" neu Delta_X cung dau Delta_tot va |Delta_X| >= 0,5 |Delta_tot| (ly do: >= 1/2 hieu ung, 3 model => nguong thap nhat
  de toi da 1 model dat ma van co nghia). Khong model nao dat -> "tuong tac / khong quy ket".
- Mo ta kem: PnL nhom lenh chung vs chi-co-o-lane; theo thang; pass gate theo quy.

## 3. Cay quyet dinh (ghi TRUOC khi chay U4a) -> MOT cong thuc ung vien
Dau vao chinh = do luong co che (2.2); PnL quy ket (2.4) chi de kiem nhat quan.
- B1 [hieu chuan gate] Neu D-cal: q99,99(p15 T1)/q99,99(live) >= 1,2 (hoac <= 0,83) tren DEV Q2 VA D-gate lane P: |pass_P/pass_L - 1| >= 0,25:
  => cong thuc can thanh phan "hieu chuan lai bo dem gate khi doi p15" (2.3, ban quantile-map hoac reseed). Thanh phan nay PHAI qua DEV (muc 4)
  truoc; DEV FAIL -> thanh phan bi loai va p15 giu ban live (khong lam moi p15).
- B2 [lech nguon S1] Neu D-ruler S1 T1 kem S1 live (lift@8 thap hon, CI80 khong chua 0) VA D-src cho rk_* lech (> 50 % o khac): => S1 KHONG lam moi
  bang du lieu tron nguon; cong thuc dung S1 train chi tren dong ts < 2026-01-01 (= S1 live hien tai) cho toi khi co nguon feature thong nhat.
- B3 [net015] Neu D-ruler net015 T1 kem live (AUC thap hon, CI80 khong chua 0): giu net015 live; nguoc lai lam moi.
- B4 [nhat quan] Neu nhanh chon theo co che mau thuan quy ket PnL (vd B1 kich hoat nhung Delta_P cung dau voi Delta_tot nhung < 10 % |Delta_tot|):
  ghi "khong ket luan" cho model do -> giu ban live.
- B5 [mac dinh] Khong nhanh nao kich hoat => cong thuc = giu ca 3 model live (khong co ung vien U4b); trinh MASTER/owner; lich: kiem lai khi co du
  lieu forward >= 1 quy.
- Cong thuc ung vien = to hop ket qua B1-B4 (moi model: lam moi / giu live / lam moi + hieu chuan), train toi 2026-09-30 (mep +07) theo recipe RETRAIN.

## 4. Kiem thanh phan cong thuc tren DEV (2022-2025, 16 quy, 8 seed) - bat buoc cho thanh phan "hieu chuan gate"
- So sanh A/B: A = WFO hien tai (khong reseed khi doi fold moi quy), B = reseed / quantile-map bo dem gate o moi moc fold bang p15 cua fold moi
  tren 90 ngay truoc moc. Cung bins, cung moi thu khac; 8 seed gate-sb (A1, s123, s13, s2024, s21, s7, s777, s99); cua so 2022-01-01..2025-12-30.
- Chi so (luat 3 AGENT_RUNBOOK: RATE): win %, TSloss %, mean(profit|SL), admit / quy, rho gate theo quy (|rho - 4,9e-5|), + SigmaPnL theo quy
  (cap seed). Tieu chi "KHONG LAM XAU" (ghi truoc): B khong co rate chat luong nao xau hon A ngoai CI bootstrap block-72h (2000 rep, seed 20260905)
  VA so quy B < A (SigmaPnL, trung binh 8 seed) <= 8/16 VA khong vi pham rang buoc cung RISK_APPETITE moi hon A. Dat -> thanh phan duoc dung.
- Chi phi: jar moi (code + unit test + parity G0 byte-identical voi r1-a3 khi tat) ~0,5-1 ngay; p15 fold DEV moi seed tren 90 ngay truoc moi moc
  (GA.retrain san) ~1-2 h; 16 kernel sim 48 thang (~40-45 ph/kernel, <= 5 song song) ~2,5-3 h wall.
- KHONG kiem duoc tren DEV: lech nguon Vision (chi co tu 2026); thanh phan B2 / B3 dua vao ruler Q3 + kiem cuoi U4b.

## 5. Kiem cuoi U4b (MOT lan, prereg rieng truoc khi chay)
- Cong thuc ung vien train toi 2026-09-30 (mep +07; T2 recipe + P14b; xu ly 8 id mapper theo ADD2 A2-2 dem theo ID); cua so 2026-10-01 -> ngay
  cuoi du lieu; so voi model live cung cua so (Lane L keo dai). Sim lien tuc tu 2021-07 nhu HO5; 2 lane x 8 seed (hoac 2 seed - P1).
- Du lieu: Q4 Vision hien co gs-x26-q4 / gs-oi-c / gs-chain-q4 toi 2026-10-31 (+07) la bien the "nt" (loai tradfi, jar exporter khac) -> KHAC nguon
  ho4p1 cua Q1-Q3. Khuyen nghi export lai Q4 bang DUNG cau hinh ho4p1 (cfg_ho4p1-x26-q3 doi cua so, jar ho4p1-jar-exp) toi ngay Vision moi nhat
  (~11-19), lap ngay thieu bang REST (nhu GST ADD7), OI kernel, ticker, chain; funding crawl (fcrawl ADD3) toi cuoi cua so. Chi phi ~0,5-1 ngay
  lich (exporter 1,5-2,5 h + OI ~1 h + tk + chain 1-2 h + funding 20 ph). Cua so ~7 tuan.
- Tieu chi (de xuat, ly do): cong suat THAP (Q3: CI80 bootstrap tuan cua d rong ~16 pp / 13 tuan) -> chi bat duoc hong lon.
  U-E0: SigmaPnL cua so (trung binh seed) >= 0 HOAC >= SigmaPnL Lane L cung cua so; U-NI: d = ROI_D5 N - L >= -1,0 pp x (so ngay / 91).
  PASS = ca hai. Mo ta: CI80 bootstrap tuan, so lenh, pass gate, lenh chung.
- He qua: PASS -> shadow 7 ngay (PREREG_RETRAIN_PILOT muc 9, an toan 16(c)) -> script doi model owner (muc 10) + audit. FAIL -> giu model live;
  lich kiem lai moi quy (forward), khong lam lai tren cua so nay.

## 6. Chi phi + thu tu + diem dung
1. Do luong co che 2.2 (Oracle + 1 kernel ruler) ~2-3 h -> STOP-D1 (MASTER doc, chua co PnL lane moi).
2. Du lieu lane P/S/M (+ PS/PM/SM neu chot) ~1 h Oracle -> 6 kernel (2 seed) hoac 24 (8 seed) ~45 ph/kernel -> STOP-D2 (cham mo ta + ap cay).
3. Neu B1: jar moi + DEV A/B (muc 4) ~1-1,5 ngay -> STOP-D3.
4. Prereg U4b (cong thuc + tieu chi) -> commit -> du lieu Q4 ~0,5-1 ngay -> train cong thuc -> sim -> STOP-D4.
Gioi han: Q3 da bi nhin 2 lan (HO4, Lane N) -> moi ket luan U4a la chan doan; 8 seed ~ 1 mau (ROI L 3,1214-3,1217 %); mapper 8 id tu 07-09;
1 quy; gate rolling khong reseed lam lane co p15 moi "tron" 90 ngay; in-sample neu reseed bang p15 moi.

## 7. Diem MASTER chot (khuyen nghi)
- P1 So seed U4a: 2 (a1, s123) vi 8 seed cho ket qua gan trung (sd d 0,0002 pp) - tiet kiem 4x. **Khuyen nghi 2.**
- P2 Lane cap (PS/PM/SM): chi chay neu khong model don nao dat nguong 50 %. **Khuyen nghi co dieu kien.**
- P3 Ruler (D-ruler) dung nhan Vision Q3: la do chat luong offline (khong PnL) - duoc phep theo U4a? **Khuyen nghi co (luat 12).**
- P4 Bien the R: quantile-map (khong in-sample) hay reseed in-sample. **Khuyen nghi quantile-map**, va chi lam sau khi B1 kich hoat.
- P5 Nguong B1 (1,2 / 0,25) va B2/B3 (CI80) - MASTER xac nhan.
- P6 U4b du lieu: export lai Q4 cau hinh ho4p1 toi ~11-19 (**khuyen nghi**) hay dung gs-* nt toi 10-31.
- P7 Neu B5 (giu ca 3 model): khong co U4b; ke hoach forward.

## 8. MASTER duyet (2026-11-21 ~16:40 +07) - muc nay THANG khi mau thuan
Ban nay = PREREG_RETRAIN_DIAG_DRAFT.md (sha256 966ded8b...) + muc 8. Can cu OWNER_DECISION_PILOT_1121 (c3a9f01b; U4a / U4b). Chua chay lane
chan doan nao, chua do co che nao, chua doc du lieu >= 2026-10-01.
- P1: 2 seed (a1, s123). P2: lane cap chi khi khong model don nao dat nguong 50 %. P3: ruler dung nhan Vision Q3 - DUOC (do luong offline, U4a).
- P4: bien the hieu chuan gate = quantile-map (khong reseed in-sample), CHI thiet ke + chay sau khi B1 kich hoat va MASTER duyet tai STOP-D2;
  uu tien cach cai dat bang TIEN XU LY file pred (khong sua jar) neu lam duoc dung nghia nhan qua (khong dung phan phoi tuong lai).
- P5: nguong B1 (ti so q99,99 >= 1,2 hoac <= 0,83 VA |pass_P / pass_L - 1| >= 0,25), B2 / B3 (CI80 khong chua 0), B4 (< 10 %): XAC NHAN.
- P6: U4b export lai Q4 bang cau hinh ho4p1 toi ngay Vision moi nhat - lam khi toi buoc U4b. P7: roi vao B5 -> khong co U4b.
- Thu tu luot dau: (1) do co che 2.2 -> ghi ket qua + ap cac dieu kien CO CHE cua B1 / B2 / B3 TRUOC khi mo PnL lane moi; (2) lane P / S / M
  2 seed -> quy ket 2.4 -> ap cay (B4 kiem nhat quan) -> DUNG tai STOP-D2. Khong lam muc 3-5 o luot dau.
- U4a la CHAN DOAN: khong ket luan nao tu U4a duoc dung de doi model tren live; duong duy nhat toi live = cong thuc ung vien -> (DEV neu ap
  dung) -> U4b mot lan -> shadow 7 ngay -> script doi model da audit, owner chay.
