# CHOICES_G3 - lua chon cua DEV khi prereg mo ho (MASTER duyet / sua)
Nguon luat: PREREG_FX_G3.md, PREREG_FX_ERRATA1.md (H3-H6), PREREG_FX_G1.md muc 3 + 6.

## Du lieu / nap
C1. TFF raw CO DU 11 file o data/raw/ (fin_fut_txt_2006_2016.zip + fut_fin_txt_2017..2026.zip; sha trong PROVENANCE.md dong
    39-49) - bao cao truoc cua DEV ("raw/ khong co zip TFF") la SAI (do lenh ls bi cat). Loader doc derived/cot_legacy_fx_cut.csv
    va derived/cot_tff_fx_cut.csv (cat <= 2026-10-31, KHONG cat <= 2019): moi dong co ngay > cutoff bi bo NGAY khi doc tung dong
    (read_cot: `if t > cutoff: continue` truoc khi parse bat ky so nao; test g_real_max_date_le_cutoff + j_fake_post_cutoff).
C2. Hop dong = MA + ho ten regex (ERRATA1 H3); EUR >= 1999-01-01 (ECU 1986 bi loai, 10 dong). Dong cung ma sai ten => loai + log.
C3. Ty gia: P = USD / 1 don vi ngoai te. DEXUSEU/UK/AL/NZ giu nguyen; DEXJPUS/SZUS/CAUS nghich dao. Loi suat LONG = P1/P0 - 1.
C4. OI <= 0 => x = NaN (khong co trong du lieu <= 2019).
C5. Lich su COT truoc TRAIN (1986-1992 cho LEG) DUOC dung lam warm-up cho cua so z (nhan qua, ngoai HOLDOUT); giao dich chi tu
    ngay vao lenh >= dau TRAIN (LEG 1993-01-01, TFF 2006-06-01).

## Tin hieu
C6. Cua so W tuan = cac bao cao cung ma co ngay trong (T - 7W ngay, T], x khac NaN, DA CONG BO truoc ngay neo (pub <= T+7-1).
    Neu > W bao cao (lech ngay khong phai thu 3) giu W bao cao moi nhat. Can n >= 0,95 W (W52: 50; W156: 149). sd ddof=1.
C7. Ngay cong bo binh thuong gia dinh <= T+6 (chi dung de loc cua so); ngoai le lay tu cot_release_exceptions.csv. Bao cao co
    pub > T+6 => LOAI (H5); no van vao cua so cua bao cao sau khi da cong bo truoc ngay neo cua bao cao do.
C8. Ngay neo = T + 7 ngay lich; ngay vao = ngay dau tien >= neo co gia FRED hop le cua dong tien do (G1 muc 3: ngay thieu ->
    ngay hop le ke tiep); khong tim duoc trong 7 ngay => khong hop le tuan do.
C9. Hop le (dem vao N_dt) = z xac dinh + khong bi loai + co lai suat thang (thang ngay neo - 1) cho dong tien VA USD + co gia vao.
    He qua: JPY ngoai universe den 2002-04 (OECD JP), CHF den 1999-07, EUR tu 1999 => LEG TRAIN thuc te it dong tien hon.
C10. N_dt dem theo NHOM x W tai cung ngay bao cao.

## Mo phong
C11. Moi phan (tranche) giu 7*H ngay lich tu ngay neo; dong tai ngay gia hop le dau tien >= neo + 7H. Tuan bi loai / thieu =>
     o 1/H do de trong (khong don vi trong so).
C12. Don vi co dinh u = w / P_vao; PnL ngay theo ty le von CO DINH (cong don, khong lai kep); maxDD tren 1 + cumsum.
C13. [ERRATA2 J1+J5] Chi phi khu hoi = max(so pip * pip / gia niem yet FRED, 3 bp); EURUSD chi 0,8 pip. Nua khi mo, nua khi
     dong. MAC DINH tinh cho TUNG phan (netting=False). eval bao kem ban netting=True (wfo_netting_descriptive_only), chi mo ta.
C14. Swap: moi ngay lich trong (D[d-1], D[d]] W*(r_ccy - r_usd)/360, lai suat thang (ngay) - 1; bien broker 1 %/nam tren |vi the
     rong| moi dong tien ("moi chan" = moi vi the dong tien vs USD, nhu G1). Thieu lai suat giua ky => swap 0 (log; <= 2019 khong xay ra).
C15. Chi phi x2 = nhan doi spread (sau quy tac max) VA bien broker (G1: "x2 moi khoan").
C16. Vi the con mo tai cuoi du lieu (2019-12-31): danh gia theo gia cuoi, khong tinh phi dong.

## Danh gia
C17. Chon chieu: dau trung binh loi suat NGAY (sau chi phi) TRAIN cua W52/H4 H_TD, mo phong chi gom phan vao <= cuoi TRAIN va cat
     ngay <= cuoi TRAIN; hoa = dung 0.0 => nhom khong giao dich.
C18. Cau hinh chon = Sharpe TRAIN cao nhat (theo chieu da chon); hoa => thu tu W52H1, W52H4, W156H1, W156H4.
C19. "Gop 3 nhom" = trung binh deu loi suat ngay 3 cau hinh chon tren cua so WFO CHUNG 2013-01..2019-12 (LEG WFO 2006-2012
     chi bao rieng). Nhom hoa chieu dong gop 0.
C20. D6: prereg G3 noi "bo 5 % TUAN tot nhat" (brief MASTER ghi "thang") => theo prereg: tuan W-FRI, bo ceil(5 %) tuan, tong con lai > 0.
C21. D2 ngau nhien: >= 500 luot; moi luot giu dung so lenh moi dong tien x nam (lenh vao trong WFO), cung H, tuan vao ngau nhien
     trong cac tuan HOP LE cua dong tien-nam do (khong lap neu du), dau = hoan vi dau that (giu ti le long/short), trong so
     1/(N_dt*H) cua tuan duoc chon. Thong ke = Sharpe WFO; so that tinh tren cung tap (chi lenh vao trong WFO).
     p = ti le Sharpe ngau nhien >= that. Gop: trung binh luot thu i cua 3 nhom.
C22. D4 nhom: >= 3/4 cau hinh co ann_ret WFO > 0; gop: >= 60 % cua 12 (tuc >= 8).
C23. D8 nhom: W52/H4 theo chieu chon co trung binh WFO > 0; gop: >= 2/3 nhom (nhom hoa khong tinh).
C24. D9: so phan (tranche) vao trong WFO cua cau hinh chon >= 150; gop: tong 3 nhom trong cua so chung.
C25. Doi chung (a) mua-giu: trung binh deu % thay doi gia cac dong tien co gia, khong phi / swap. (c) carry: cung cac phan WFO cua
     cau hinh chon, dau = dau (r_ccy - r_usd) thang neo-1. Hit rate = ti le phan co loi suat rong (gia + swap - bien - phi) > 0.
     IC = Spearman(z, log-return 1w / 4w tu ngay vao) theo nam.
C26. Khoa: sim_g3.simulate tu choi data real neu chua unlock_real("I_HAVE_A1_PASS"); CLI sim/eval goi unlock truoc khi nap.

ERRATA2 J7: C5, C7, C9, C12, C14, C15, C19, C21, C23, C24 chap nhan tam; A1 soat. D6 = TUAN (J3). PnL 2008-10 do A1 ket qua (J6).

## ERRATA3 (sau A1 PASS-WITH-MINOR)
K1. p = (1 + #luot >= that) / (N + 1) (eval_g3.perm_p) cho D2 nhom va gop.
K2. Bien broker 1 %/nam tren TONG |w| cac phan dang mo (sim_g3 Gt), khong tren vi the rong. Thay C14 phan "|vi the rong|".
K3. Thuoc do TRAIN: chi phan vao trong TRAIN, ep dong (co phi) tai cuoi TRAIN; thuoc do WFO (D1, D3, D4, D6, D7, D8, D9, p): chi phan
    vao trong WFO, ep dong (co phi) tai 2019-12-31. Chon chieu dung cung mo phong TRAIN (ep dong cuoi TRAIN). Thay C16: vi the con mo
    cuoi du lieu / cuoi ky bi tinh phi dong. Gop 3 nhom: LEG dung chuoi WFO-only cat 2013-2019.
K4. Bao kem p "dich vong khoi" (moi dong tien: chuoi dau tin hieu that tren cac tuan hop le WFO, dich vong lag ngau nhien 1..L-1,
    trong so 1/(N_dt*H) cua tuan dich toi), N = so luot ngau nhien, seed rieng; nhan "DESCRIPTIVE_NOT_CRITERION".
K6. test_k: nguong 1,5; D9 150; p +1; dau swap; bien theo phan (dap an tay H=4); x2 bien; ep dong co phi; doi chung giu bo dau
    long/short tung dong tien-nam; dich vong giu so lenh moi dong tien.
