# A1_G3_CODE - audit doc lap code G3 (COT z-score FX, tren giay)
A1 (khong phai DEV), 2026-11-27. Chi doc du lieu <= 2019-12-31; KHONG tinh loi suat / Sharpe / chieu tin hieu tren du lieu that.

## KET LUAN: PASS-WITH-MINOR
Khong thay loi CHAN (nhin truoc, sai chieu, ro ri TRAIN->WFO, sai so sach). 6 diem NHO duoi day nen sua / ghi ro truoc khi chay that.

## SHA256 (khop SHA256SUMS.txt, kiem dau va cuoi audit)
eval_g3.py 1579d183...76c31e6 | load_g3.py 15a2b28c...16eebf4 | sig_g3.py 9e0d2595...1171394 | sim_g3.py 4625a5e9...2209266 | test_g3.py c9a3403a...1bca382

## Doi chieu prereg / ERRATA -> code (tat ca KHOP)
- 7 hop dong ma+ho ten (load_g3.py:25-36, name_ok :65); ECU 099741 truoc 1999 loai (10 dong, name regex + min_date).
- x = (L - S)/OI (load_g3.py:133); z truot W{52,156}, cua so (T-7W, T], chi bao cao pub <= neo-1, n >= 95 % W, khong noi suy, ddof=1 (sig_g3.py:255-286).
- |z| >= 1,5 (sig:229,321-322); neo = T+7, vao = ngay co gia FRED dau tien >= neo (<= 7 ngay) (sig:267,289-315) = H5.
- Loai bao cao pub > T+6 theo cot_release_exceptions (sig:248-252) = H5.
- H {1,4} 4 phan chong lop, w = dir*signal/(N_dt*H), dong tai gia hop le dau tien >= neo+7H (sim:97-109); gross <= 1 (n_sig <= N_dt).
- 12 cau hinh; H_TD/H_ND; chon chieu chi tren TRAIN W52/H4 H_TD, hoa => khong giao dich (eval:254-258,329-340).
- Chia thoi gian dung (sig:232-236), theo ngay vao lenh.
- Chi phi J1 max(3 pip, 3 bp), EUR 0,8 pip; nua mo / nua dong; KHONG netting mac dinh (J5); x2 (sim:42-56,147-155).
- Swap ngay lich (r_ccy - r_usd)/360 lai suat thang-1; bien 1 %/nam (sim:57-73).
- Ngau nhien >= 500 (eval:398-400), D1-D4, D6-D9 (eval:367-369, 418-420), nhan [in-sample] (eval:435-453), DSR count.

## Tu kiem doc lap tren du lieu that (code rieng, doc thang file ZIP raw CFTC + CSV raw FRED, loc <= 2019-12-31 khi doc)
- x: LEG 9631 dong, TFF 4953 dong x 2 nhom: khop 100 %, lech max = 0, khong dong thieu/du.
- z (3 nhom x 2 W, 7 dong tien, toan bo cac tuan - khong chi mau 300): so diem z xac dinh 8317 / 7593 (LEG W52/W156), 4504 / 3812 (LevF), 4504 / 3812 (AssetMgr); lech max = 0,0; 0 tuan lech trang thai xac dinh; 0 lech tin hieu tren tuan hop le; gom 1865/1465/1102/616/1265/978 tuan cuc tri va 223-590 tuan sat nguong (|z| 1,4-1,6).
- Quanh 2013-09..12 va 2018-11..2019-03: khop 100 %; dung 5 + 10 bao cao bi loai.
- Ngay vao lenh (moi tuan hop le, 7546/7012/4497/3805/4497/3805): 0 truong hop < T+7; 0 cuoi tuan; 0 ngay khong co gia FRED raw; 0 khong phai ngay hop le dau tien >= T+7; 0 pub >= ngay vao; 0 bao cao bi loai lot vao.
- C7: 15 bao cao tre <= 2019 chi vao cua so cua bao cao SAU khi da cong bo (vd 2013-10-29 pub 11-06 -> lan dau trong cua so bao cao 2013-11-05 neo 11-12; 2019-02-26 pub 03-05 -> bao cao 2019-03-05 neo 03-12). KHONG nhin truoc.
- Chieu: P = USD/1 ngoai te; DEXUSEU/UK/AL/NZ giu nguyen, DEXJPUS/SZUS/CAUS nghich dao. Vi du that: EUR NonComm 2000-12-19 z=+1,89 -> signal +1 -> H_TD w=+0,0625 = LONG EUR vs USD; JPY 2002-12-31 z=+2,20 -> long JPY (loi khi DEXJPUS giam); tuong tu CHF, CAD. Gia derived = raw (lech 0), lai suat derived = raw.
- FRED 1986-2019: khong co khoang thieu > 2 ngay lam viec (quy tac 3 ngay G1 khong bi kich hoat).

## So sach tinh tay (2 dong tien EUR + JPY, 8 tuan, 5 phan EUR H=4 chong lop + 2 long / 1 short JPY, lai suat doi giua thang)
- Gia MTM 0,02136801 = sim; swap 0,00115278 = sim (dung dau, dung lai suat thang-1); phi tung phan 0,00016093 = sim; netting 0,00015348 = sim; x2 phi 0,00032187 = sim.
- Bien broker: sim 0,00061806 = tinh tay tren |vi the rong moi dong tien|; tinh theo tung phan = 0,00076389 (xem NHO-1).
- Vi the rong EUR 2010-02-02 = 0,5 (phan 1 dong + phan 5 mo cung ngay; khong netting tinh 2 lan phi).
- Long EUR khi EUR tang: loi; long JPY khi DEXJPUS giam: loi; short JPY: lo. H_ND = -H_TD.

## Ro ri / cutoff / doi chung
- Chon chieu: chi phan vao <= cuoi TRAIN, cat ngay <= cuoi TRAIN + assert (eval:256,329-331). Mutant chon bang WFO va mutant bo end TRAIN deu bi test f bat.
- Warm-up COT 1986-1992 (C5): chi la qua khu cua z, khong dung loi suat; hop le. TFF khong co warm-up => TRAIN W156 thuc te tu ~2009-06 (1355 tuan hop le vs 2047 W52) - DIEM YEU da biet.
- Cutoff: COT (read_cot :108), FRED + lai suat (read_series :90) bo dong > cutoff truoc khi parse; assert_cutoff; cutoff >= 2020 can --holdout I_HAVE_OWNER_OK. eval/sim khong co --cutoff. Exceptions CSV doc ca dong 2023/2025 (chi la ngay meta) roi loc - vo hai.
- Khoa: sim/eval unlock_real truoc khi nap (--real I_HAVE_A1_PASS); test g PASS. Khong co print. Tat dinh (seed co dinh, test i PASS). out/ khong co ket qua loi suat that (chi synthetic_h_*, handcheck noPnL, dem su kien, inventory).

## Test + mutant (ban copy trong mktemp; out cua test chuyen vao thu muc tam)
- test_g3.py goc: 110/110 PASS.
- 23 mutant: BAT 17 - vao T+3; khong loai bao cao tre; z gom t+1 (2 bien the); dao chieu JPY; netting bat; phi khong x2; chon chieu bang WFO; bo end TRAIN khi chon chieu; cua so 90 %; H_ND = H_TD; tat guard cutoff; bo cat FRED; bo cat COT; dong phan sau H-1 tuan; bo N_dt trong trong so; bao cao tre vao cua so truoc khi cong bo.
- LOT 6: nguong 1,0; D9 nguong 15; dao dau swap; bo bien broker; doi chung ngau nhien toan long; bo min_date EUR (tuong duong - ten ECU da bi loai). 4 lot dau A1 da kiem truc tiep (doc code + so sach tay) => dung, nhung test thieu.

## Loi NHO (khong chan)
1. sim_g3.py:154 bien broker tinh tren |vi the RONG moi dong tien|, khong theo tung phan: khi phan long/short cung dong tien chong nhau thi giam phi - trai tinh than bao thu J5 va lech voi trades.net_ret_unit (sim:139-140 tinh theo tung phan; hit rate dung so nay). Anh huong nho (<= 1 %/nam x phan vi the bu tru). Sua: marg = -cm * |w| tung phan (cong don gross_pos = cumsum |dW|) hoac MASTER ghi ro C14 la netting bien.
2. eval_g3.py:362/414 p = mean(rand >= real) khong +1; nen (1 + #>=)/(n + 1). Them: doi chung (C21) rai tuan ngau nhien doc lap, con tin hieu that thanh cum lien tiep => phan phoi Sharpe ngau nhien hep hon => p co the lac quan. Dung prereg, nhung de nghi bao kem ban "dich vong khoi" (circular shift chuoi dau trong dong tien x nam) de mo ta.
3. eval_g3.py:335-341 metrics WFO (D1, D3, D6, D7) gom PnL cua phan vao cuoi TRAIN tran sang <= 4 tuan dau WFO, trong khi D2 / D9 chi tinh phan vao trong WFO. Nho; sua: dung tr loc start=wa cho metrics WFO hoac ghi ro.
4. sim C16: vi the con mo 2019-12-31 khong tinh phi dong - vo cung nho, nen tinh nua phi dong de bao thu.
5. Test thieu: THRESH, D9 = 150, dau swap, bien broker, D2 bang chung doi chung khong co kiem tay. De nghi them assert hang so + 1 test swap / bien co dap an tay (kich ban tren cua A1).
6. Loai tuan chua co z cua TFF (khong warm-up) => TRAIN TFF W156 ~3,5 nam; MASTER can ghi ro khi doc ket qua (khong phai loi code).

## CHOICES
- C5 OK (nhan qua). C7 OK (da kiem, khong nhin truoc). C9 OK (bao thu, giam universe som). C12 OK. C14 xem NHO-1 (co loi nhe cho ket qua). C15 OK (bao thu). C19 OK (nhom hoa = 0, bao thu). C21 xem NHO-2 (co the lac quan p). C23 OK (nhat quan voi co so chon chieu W52/H4). C24 OK nhung "lenh" = phan; H1 va H4 cung so phan nen khong lam dep D9.

## CHUA kiem
- Lich cong bo that ngoai danh sach exceptions (vd cac tuan bu sau dong cua 2013-11, 2019-03) - tin theo DATA agent.
- PnL that 2008-10 (J6 - viec cua A1 KET QUA sau khi chay). Thoi gian chay eval that. Tinh dung chuoi lai suat OECD lam proxy swap.

# Vong 2 (sau ERRATA3 K1-K4, K6, K7) - 2026-11-27
## KET LUAN CUOI: PASS
Ca 5 diem NHO-1..NHO-5 cua vong 1 da sua dung ERRATA3; NHO-6 ghi nhan (K7). Khong phat hien loi moi.
## SHA256 (da kiem)
eval_g3.py 34dccc35365a55cb57cee13cf8758c9287900a4ff7e4589825b07f510920f64c
load_g3.py 15a2b28c9aed210d0cf06fe24cc2814047e494f7a0494269449e2283116eebf4 (khong doi)
sig_g3.py 079224ef49116f958e7d7b6a66f1a61d9d46f071852523225781de14f77f3e66
sim_g3.py 9244cc6eba5e937157870d1f5495566053d62e82ff2d3c9fedcafd1b288e66c9
test_g3.py a35f2d11f526f2292bf9c71eebfc63d664da1f760062884f8dc5c39b51ad6734
## (1) sig_g3 chi tach ham
signal_from_z (sig_g3.py:101-107) giu nguyen THRESH 1,5 va dieu kien eligible. Chay lai doi chieu doc lap tu raw: x lech 0 (9631 + 2 x 4953 dong);
z lech 0,0 tren 8317/7593/4504/3812/4504/3812 diem; 0 lech trang thai xac dinh; 0 lech tin hieu; ngay vao 0 vi pham (>= T+7, la ngay FRED
hop le dau tien), 0 bao cao bi loai lot vao. Giong het vong 1.
## (2) So sach tay voi K2 + K3 (cung kich ban EUR + JPY, 8 tuan)
- Khong close_at / x2 / close_at 2010-02-10 / close_at 2010-02-13 (thu 7 -> dong thu 6): gia, swap, bien, phi khop sim tung ngay (lech <= 3e-19).
- K2: bien = tong |w| tung phan (sim:144-145,164-165) - kich ban co long/short JPY bu tru nay ra 0,00076389 = tinh tay theo phan.
- K3: phan con mo bi ep dong tai close_at / ngay cuoi co phi dong (sim:124,133-135,148); PnL sau ngay dong = 0.
- Ranh gioi: TRAIN dung phan vao trong [ta, te] + close_at=te; WFO dung phan vao trong [wa, we] + close_at=we (eval: evaluate_group) => phan
  vao tuan cuoi TRAIN khong nam trong WFO. Chon chieu: phan vao <= te, ep dong tai te bang gia <= te, cat <= te + assert => van chi dung TRAIN.
## (3) perm_p va dich vong
perm_p = (1 + #>=)/(N+1) (eval perm_p), dung cho D2 nhom va gop. Dich vong khoi (shift_pool / shift_tranches): dich vong chuoi dau that
theo tung dong tien trong WFO, giu so lenh va cum; rng rieng (seed+1000); chi ghi block_shift_..._DESCRIPTIVE_NOT_CRITERION, KHONG vao D.
Ghi chu nho (khong chan): dich vong theo ca chuoi WFO cua dong tien (khong theo dong tien x nam) - hop ly cho muc dich mo ta.
## (4) Test + mutant
- test_g3.py (ban copy): 123/123 PASS.
- 5 mutant lot o vong 1 nay BAT HET (test k): nguong 1,0; D9 = 15; dao dau swap; bo bien; ngau nhien toan long.
- Moi: bien tren vi the rong -> BAT (k_margin_per_tranche_H4); WFO gom phan tran tu TRAIN -> BAT (f, h crash o random_pool - bat gian tiep,
  khong co assert rieng); perm_p bo +1 -> BAT; bo ep dong close_at -> BAT.
- LOT 1: chon chieu cat den cuoi WFO nhung van chi phan vao <= te (gan tuong duong: chi them <= 4 tuan PnL tran + bo ep dong) - khong
  phai ro ri tin hieu WFO; mutant chon chieu bang WFO that da bi bat o vong 1.
## Con lai (khong chan)
- Gop 3 nhom tren 2013-2019: chuoi LEG co the gom <= 4 tuan dau 2013 tu phan LEG vao cuoi 2012 (van la WFO cua LEG, khong ro ri); doi chung
  ngau nhien cung cau truc nen cong bang. Neu MASTER muon tuyet doi sach: close_at / start rieng cho cua so chung.
- trades.open_at_end nay luon False (do ep dong) - chi la cot mo ta.
- Chua kiem: lich cong bo ngoai exceptions; PnL that 2008-10 (J6); thoi gian chay eval that.
