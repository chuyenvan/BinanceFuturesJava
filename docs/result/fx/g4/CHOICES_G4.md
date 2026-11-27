# CHOICES_G4 - lua chon cua DEV khi prereg G4 / ERRATA4 mo ho (MASTER duyet)
Luat: PREREG_FX_G4.md (+ CHOT CUA MASTER), PREREG_FX_ERRATA4.md N1-N5, bai hoc ERRATA1-3.

## Du lieu
E1. Thoi gian = phut UTC int64; ts parquet = gio MO nen (DATA_REPORT_3). Close cua nen t co tai t+1 phut.
E2. Cutoff: pyarrow filter ts < cutoff+1 ngay (dong > cutoff KHONG duoc doc); assert sau khi doc; >= 2020 can --holdout I_HAVE_OWNER_OK.
E3. N3: cap-nam bi loai danh dau theo NAM UTC cua nen (bad); khong sinh su kien, khong vao lenh, khong lam doi chung; cua so sigma
    cham phien bad => sigma NaN (tu dong = 20 phien dau nam ke tiep khong co su kien). Lenh mo tu truoc van danh gia qua nen bad
    (gia van co) - hiem.
E4. Phien = ngay NY cua (t + 7 h) (moc 17:00 NY); phien < 60 nen khong tinh la ngay giao dich (vd nen le 17:00 NY thu 6).

## Tin hieu
E5. r1 chi khi 2 nen cach dung 1 phut. sigma1 = std gop (ddof=1) cua moi r1 trong 20 phien giao dich TRUOC; sigma_N = sigma1*sqrt(N);
    sigma60 cho thoat = sigma1*sqrt(60) cua phien su kien (co dinh suot lenh).
E6. r_N(i) = log(c_i / c_j), j = nen cuoi co t_j <= t_i - N. N4: loai neu co nen trong (j, i] sau khoang trong > 5 phut, hoac t_i < 30
    phut sau khoang trong > 60 phut (gom dau tuan; ap ca o dau chuoi du lieu).
E7. Ngoai N4 van GIU loai prereg muc 3: nen vao lenh trong 16:55-17:15 NY bi loai (N4 chi thay quy tac "cuoi tuan / 30 phut dau tuan").
E8. Nen vao = nen KE TIEP (i+1), phai cach nen su kien <= 5 phut; khong phai nen cuoi du lieu.
E9. Mot vi the / cap / CAU HINH (moi cau hinh chi 1 phia); su kien co nen <= nen thoat bi bo (su kien moi phai SAU nen thoat).
E10. Dem tren du lieu that: "event_bars" (moi phut thoa) va "episodes" (phut dau cua chuoi phut lien tiep) - khong phai so lenh that
     (so lenh can mo phong thoat, bi khoa).

## Mo phong
E11. Gia tham chieu = BID close nen vao; chi phi khu hoi C = max(3 pip, 3 bp) (EURUSD 0,8 pip) theo gia, nua khi vao (theo gia vao),
     nua khi ra (theo gia ra) - tuong duong L mua ASK / ban BID, S ban BID / mua ASK. Cot spread file khong dung (N1).
E12. Loi suat lenh don: side*(P_ra/P_vao - 1); d cho SL/trailing tinh cung kieu (ty le, khong log).
E13. Thu tu khi nhieu dieu kien cung nen: (gia MO nen sau khoang trong > 5 phut: SL > trailing > time-stop) truoc, roi close: SL >
     trailing > time-stop > het du lieu. Trailing tinh tu dinh cua cac close (dinh truoc nen dang xet khi kiem gia mo).
E14. Time-stop: nen dau tien co gio mo >= gio mo nen vao + TS; thoat tai close nen do (hoac gia mo neu nen do sau khoang trong).
E15. x3: nen thoat trong 16:55-17:15 NY HOAC < 30 phut sau khoang trong > 60 phut ("30 phut dau tuan" theo N4). Truot +0,5 C cho
     SL / time-stop / het du lieu (khong cho trailing). x2 nhan spread + truot + bien broker.
E16. Swap: moi moc 17:00 NY (thu 2-6; thu 6 x3) nam trong (gio vao, gio ra]: side*(r_base - r_quote)/360 lai suat OECD thang m-1
     (EZ, GB, JP, AU, US) - bien 1 %/nam. Khong tru ngay le.
E17. Sizing: moi lenh notional = 1/so cap (4) cua von; loi suat cong don (khong lai kep).

## Danh gia
E18. TRAIN / WFO theo GIO VAO (bai hoc K3); PnL ca lenh ghi vao THANG RA. Sharpe theo thang x sqrt(12), thang khong lenh = 0.
E19. maxDD cau hinh chon = MTM tung phut (gia close, tru phi vao) tren cac lenh vao trong ky; 12 cau hinh con lai bao maxDD theo
     loi suat da chot (mo ta).
E20. Chon cau hinh: Sharpe TRAIN cao nhat; hoa => TS ngan, roi T cao, roi thu tu luoi.
E21. MAU THUAN brief vs prereg: brief goi doi chung CHINH = vao ngau nhien cung cap / gio UTC / thang / so lenh; prereg muc 5 + D2 =
     DICH VONG THEO NGAY. Code tinh CA HAI; D2 mac dinh = dich vong ngay (prereg); --d2 random de doi. MASTER chot.
E22. Dich vong ngay: moi luot, moi cap mot k ngau nhien 1..S-1 (S = so phien hop le WFO); su kien that (cac lenh da khop) chuyen sang
     phien (j+k) mod S cung phut-trong-phien (gio NY); khop nen dau tien >= muc tieu trong 5 phut va hop le, khong thi bo (~1-2 %).
     Lenh doi chung doc lap (khong ap 1 vi the) de giu so lenh; sigma60 lay tai nen moi.
E23. Doi chung ngau nhien: moi lenh that -> nen hop le ngau nhien cung cap, cung thang, cung gio UTC; doc lap.
E24. Thong ke doi chung = Sharpe thang WFO; p = (1 + n_ge)/(N + 1), N >= 500.
E25. D4 = >= 8/12 cau hinh co tong loi suat WFO > 0; D5 bo ceil(5 %) thang tot nhat; D7 >= 150 lenh WFO.
E26. Test (h) du lieu gia: nhieu thuan Gauss voi cum bien dong theo gio (khong hieu ung chieu) de co du su kien; nhieu Gauss khong cum
     cho "KHONG DU MAU" (it su kien |z| >= 4 tren 60 phut) - van la ket luan dung cua code, nhung test can "KHONG DAT".
