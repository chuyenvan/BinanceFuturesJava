# A1_T1_CODE - audit DOC LAP code LEVZ T1 (PREREG_LEVZ_T1 186f2a5a + ADD1 45f45a5b) - A1, 2026-11-26
Nguoi audit: agent A1 (khong phai DEV). Khong chay grid / select / rand / report tren du lieu that; khong tong hop loi nhuan that.
Du lieu that chi dung o muc bang thoat tung lenh (doi chieu engine) + ve sinh. Khong doc du lieu >= 2026-01-01.
Moi file tam o mktemp -d (/tmp/a1t1_*), da xoa khi xong.

## KET LUAN: PASS-WITH-MINOR
Khong tim thay loi CHAN (look-ahead / so sach / lech prereg) trong engine, HEDGE, select, rand, report. Co loi NHO (duoi day).

## 1. Doi chieu prereg + ADD1 -> code (doc tung dong)
- Luoi: BRK 90, VOL 48, PART 8, STATE 8, HEDGE 93 bo goc (90 BRK + B1 xi 12 / 170 / 72) x 2 cong cu x 2 h = 372; x 3 z x 3 K x 2 gate
  -> 9 468 (A1 tu dem lai: BRK 1620, VOL 864, PART 144, STATE 144, HEDGE 6696). xi 12 = cfg 4107 cua grid_b1 (4107 = 21 x 195 + 12;
  khoi 21 = W7 E0 z3.0 K3) - dung ADD1 A1. exit_2024 / exit_2025 doc tu levz_b3/out/exitsel_b3.json va assert (170, 72).
- TP: close 1m <= p0 (1 - tp) -> xr = 1 - tp dung muc, phi ra 0,07 % do port._ledger (N xr FEE) - dung prereg. SL: close >= p0 (1+sl) ->
  close x 1,003 (nhu B1). SL va TP khong the cung phut; TP trung phut TIME -> TP o muc (cao hon close => bao thu cho short).
- PART: dong 50 % tai +s (khop muc), stop phan con lai ve p0 (close >= p0 -> close x 1,003), TP 3s / het H; dung prereg.
- STATE: hang tin hieu k + h (h >= 1), thoat phut 60 h (= T_{k+h} + 1 phut, cung quy uoc vao lenh), SL 15/30 % luon bat, tran H.
- VOL: u = sd(ddof 1) loi suat log gio tren CL[k-168..k] x can 24, san 2 %, tran 50 %, R = 0 -> khong TP.
- HEDGE: short = eq x 0,60 / ((1 + h) K); long = h x sum N x mk cua short dang mo SAU quyet dinh gio k; can lai moi gio tai P_k = close
  1m phut 60k; phi 0,07 % tren |luong can lai|; funding long = units x close phut 60k-1 x FR[k] (long tra khi > 0); gate chi chan short
  moi (gate ap tren danh sach ung vien, chan long chay moi gio); eq_worst = eq_worst short + hedge - units_{k-1} (P_k - min close 1m
  (T_{k-1}, T_k]) (ADD1 A3); maxdd tai close gio van bao (cot maxdd).
- Gate G_EW14 = B2 opts.gate_series + mask_at (g[k] tai gio vao) - y het grid_b2.
- WFO: select_b1.rule (sha e1f9d290..., KHOP SHA256SUMS cua B1 - khong sua), dd_mode 'folds'; 2024 = F1 -> F2, 2025 = F1+F2 -> F3;
  restrict() cua B1 assert khong cot fold khac. top-1 = qua tron luat, top-20 = 20 hop le diem cao nhat (B1 ADD1 B).
- Doi chung: lop W7 E0 z3,0, 100 luot, max diem B0 score_of qua toan bo bo thoat x K cua ho, tung ho x tung gate, p = ti le luot >= that
  (dinh nghia giong rand_b1). T-a..T-e: dung muc 5 (gate NONE); G_EW14 mang nhan 'gate hau kiem', khong co ket luan.
- B1 code dung lai (exits.py, port.py, select_b1.py) sha KHOP levz_b1/SHA256SUMS.txt.

## 2. ENGINE - doi chieu DOC LAP (ref_a1.py cua A1: doc close1m.npy / gaps.npz / inputs.npz / sig_W7.parquet truc tiep, vong for tung
phut, KHONG dung path_of / Cur / ban tham chieu cua DEV), 260 ung vien that (seed 777, khac seed DEV) so voi work/exits_t1_*.npz:
| ho | lenh so | bo thoat | lech j | lech ly do | lech xr | lech funding | lech mxh | lech lon nhat |
|---|---|---|---|---|---|---|---|---|
| BRK | 6 348 | 6 bo moi ung vien + du 90 bo tren 52 ung vien | 0 | 0 | 0 | 0 | 0 | xr 0, fund 0 |
| VOL | 3 954 | 6 bo + du 48 bo tren 52 ung vien | 0 | 0 | 0 | 0 | 0 | 0 |
| PART | 2 080 | ca 8 bo | 0 | 0 | 0 | 0 (j1, xr1, mxh_raw 0 lech) | - | fund 3,5e-18 |
| STATE | 2 080 | ca 8 bo | 0 | 0 | 0 | 0 | 0 | 0; gio STATE (sth) 0 lech |
Ly do (ref): BRK tp 1720 / sl 2371 / time 2255 / eod 2; VOL tp 511 / sl 1628 / time 1812; PART be 364 / time 810 / sl 749 / tp 154;
STATE state 1962 / sl 108 / time 10. Funding cua PART: nua dau du ky toi phut chot (60h-1 <= j1), sau do 0,5 - khop tung so.
Phi PART: port tinh phi ra N x FEE x (0,5 xr1 + 0,5 xr2) = DUNG tong phi 2 nua; lech DUY NHAT la thoi diem ghi phi nua dau (luc dong lenh
thay vi luc chot) -> equity chia size o giua cao hon <= 0,5 x N x xr1 x 0,07 % (<= 0,035 % N, ~0,002 % equity voi K=10): dung nhu DEV noi,
thien lech mot chieu nhung khong dang ke.
PART trong port.py: cho (slot) + 'held' + cooldown giai phong tai kx cua PHAN CON LAI (j = phut thoat phan con lai) - KHONG som. MTM gio
(mk hieu dung = 0,5 xr1 + 0,5 mk sau phut chot), funding gio x 0,5 sau chot, hm bao thu trong cua so chua phut chot - doc dung.
Kiem rieng: thu tu SL / TP (khong the cung phut); phut vao = close nen 1m mo T_k (path[0]), su kien tu phut 1; het H tai phut 60H; gap:
0 path NaN tren 260 ung vien, 0 'miss' tren du lieu that (nhanh miss chi kiem bang test h tren du lieu gia - A1 chay lai PASS).
TP cung phut voi chot nua (PART): DEV khong cho (bao thu) - tren 260 x 8 lenh, cho phep hay khong cho deu ra cung ket qua (0 khac).

## 3. NHIN TRUOC
- VOL: CL[k, c] == close 1m phut 60k-1 (nen ket thuc dung T_k) o 260 / 260 ung vien; == phut 60k+59 chi 1 / 260 (trung gia ngau nhien).
  => CL[k] la nen DA DONG truoc lenh vao T_k + 1 phut. Khong nhin truoc. (Test d cua DEV: thay CL tuong lai khong doi u - A1 chay lai PASS.)
- STATE: hang sig t = T_{k+h}: OI dung tsr <= t - 10 phut (assert trong levz.py tier-1), funding = settlement ts <= t - 1 phut (fund_z),
  f quy ve 8 h (r8) => da cong bo tai T_{k+h}; thoat T_{k+h} + 1 phut. Khong nhin truoc. Mutant k+h-1 / k+h+1 deu bi test b, d bat.
- G_EW14: g[k] tai gio vao (B2 da audit cach tinh g). HEDGE can lai bang close phut 60k (cung phut voi gia vao short) - khong nhin truoc;
  funding chan long dung close phut 60k-1 x FR[k] cua moc T_k.

## 4. SO SACH HEDGE - tinh tay (hedge_hand.py: 3 lenh short, 7 gio, BTC len / xuong, funding +/-, bo ke toan doc lap cua A1)
| kich ban | eq cuoi code | eq cuoi A1 | lech eq tung gio | lech eq_worst | hedge PnL | phi can lai | funding long | expo max |
|---|---|---|---|---|---|---|---|---|
| h=1 BTC len | 9975.8652 | 9975.8652 | 3,6e-12 | 3,6e-12 | -20.2295 | 2.9586 | +0.1888 | 0.408 |
| h=1 BTC xuong | 10018.8530 | 10018.8530 | 1,8e-12 | 1,8e-12 | +22.7526 | 3.0019 | +0.2016 | 0.413 |
| h=0,5 len | 9981.3074 | 9981.3074 | 1,8e-12 | 1,8e-12 | -13.4857 | 1.9724 | +0.1258 | 0.409 |
| h=0,5 xuong | 10009.9838 | 10009.9838 | 3,6e-12 | 3,6e-12 | +15.1857 | 2.0025 | +0.1344 | 0.412 |
| h=1 BTCETH | 9975.9592 | 9975.9592 | 3,6e-12 | 3,6e-12 | -20.1355 | 2.9586 | +0.2831 | 0.408 |
| h=0 | 9992.1900 | 9992.1900 | 3,6e-12 | - | 0 | 0 | 0 | 0.411 |
Tay tung buoc gio 2 (h=1, len): realized cid0 = 1000 x 0,05 - 0,7 - 0,665 = 48,635; MTM cid1 = 1000 (1 - 1,03 - 0,0007) = -30,7;
hedge = -1951,0448 + 19,5098 x 101 = 19,4454 => eq = 10037,3804 => size = eq x 0,6 / (2 x 3) = 1003,738 = code (1003,73804).
Size h = 0,5: 10 000 x 0,6 / (1,5 x 3) = 1333,33 = code. Phoi nhiem (short + long) / eq <= 0,413 < 0,60 o moi gio.
h = 0 trung B1: test c chay lai PASS (108 cau hinh, 99 595 lenh, frames .equals()).

## 5. Test DEV chay lai (ban copy, BASE doi sang mktemp): a b c d e g h i = ALL PASS (a 1,1 s; b 8,1 s; c 68 s; d 38 s; e 10 s; g 79 s).
Test f (pipeline day du tren du lieu GIA, qua flock oracle_heavy): phan GRID chay XONG 9 468 cau hinh tren du lieu GIA (17:17-17:36, run_grid + check_acct cua B0 khong loi, 2 tien trinh); phan rand (30 luot) / report A1 DUNG giua chung de kip han -> KHONG xac nhan lai phan rand/report cua test f (DEV bao PASS; fake_report_t1.md cua DEV).

## 6. Mutant (ban copy, moi mutant 1 thay doi; test DEV a b c d e h i (+g voi rand) + hand-check HEDGE cua A1)
| mutant | test DEV | hand-check HEDGE A1 | ghi chu |
|---|---|---|---|
| M01_tp_fill_at_close | BAT (b_slow_reference) | - |  |
| M02_part_no_breakeven | BAT (b_slow_reference; h_miss_path_fake) | - |  |
| M03_state_row_k_h_plus1 | BAT (b_slow_reference; d_no_lookahead) | - |  |
| M04_state_row_k_h_minus1 | BAT (b_slow_reference; d_no_lookahead) | - |  |
| M05_vol_candle_after_entry | BAT (b_slow_reference; d_no_lookahead) | - |  |
| M06_hedge_no_rebal_fee | LOT | BAT |  |
| M07_hedge_no_funding | LOT | BAT |  |
| M08_hedge_funding_sign | LOT | BAT |  |
| M09_short_size_no_1plus_h | LOT | BAT |  |
| M10_hedge_only_at_cand_hours | LOT | BAT |  |
| M11_rand_wrong_zclass | LOT | - |  |
| M12_select_uses_test_fold | LOT | - |  |
| M13_part_full_funding | BAT (b_slow_reference) | - |  |
| M14_sl_no_slip | BAT (a_engine_eq_b1_no_trail; b_slow_reference) | - |  |
| M15_partview_mk_raw | LOT | - |  |
| M16_tp_no_fee_via_xr | BAT (b_slow_reference) | - |  |

Ghi chu mutant: M15 (PartView dung mk tho thay mk hieu dung) LOT ca test DEV lan hand-check HEDGE (khong lien quan). A1 kiem rieng PartView
bang dac ta tu viet (pv.py: 200 lan x 3 ung vien x 721 gio = 432 600 o mk / hm / fh): 0 lech => code hien tai dung, nhung thieu test hoi quy
(gop vao NHO-2). M11 / M12 (rand sai lop z, select nhin fold kiem) LOT - xem NHO-3. M01-M05, M13, M14, M16 (engine) deu BI test b / a / d / h bat.

## 7. Loi
CHAN: khong co.
NHO-1 (exits_t1.py:297-307, CHOICES 5) VOL u tu CL cua store gio B0: 63 / 8 524 ung vien union co NaN trong cua so CL 169 gio; 38 trong
  do bi u = NaN -> SL = tran 50 % du close1m co du du lieu; 25 con lai u lech tuong doi den vai % so voi u tinh tu close 1m (phut 60t-1).
  Khong phai nhin truoc. Sua (tuy MASTER): tinh close gio tu close1m.npy phut 60t-1 (cung kho voi engine), hoac giu + ghi ro 38 ca SL 50 %.
NHO-2 (test/test_t1.py) Bo test DEV KHONG bat loi so sach HEDGE va PartView (M06-M10, M15): quen phi can lai, quen funding, dao dau funding, size khong chia (1+h),
  chan long chi can lai o gio co ung vien - deu LOT (test c chi h = 0; test e chi kiem tu nhat quan hedge_acct_err). Code hien tai DUNG
  (A1 hand-check khop 1e-12) nhung khong co hang rao hoi quy. Sua: them hedge_hand.py cua A1 thanh test (j) (so voi ke toan doc lap).
NHO-3 Loi chon / doi chung (dung test fold khi chon, sai lop z cua rand) khong co test bat - A1 kiem bang doc code: WFO folds dung,
  select_b1.restrict() assert; ZCLS = 3,0. Nen them assert trong select_t1.wfo (folds < test) va rand_t1 (ZCLS == 3.0).
NHO-4 (common_t1.py:64, CHOICES 4) Map ma: grid parquet x_trail = ti le TP, x_time gom STATE, x_sl gom 'be'. select_b1.rule / B0
  score_of / valid_of CHI dung ret, maxdd_worst, n (A1 doc) => KHONG anh huong luat chon / T-a..T-e. Chi la rui ro doc nham: bao cao
  khong duoc trich cot x_* cua grid nhu ly do that (report_t1 da dung rt that - test i).
NHO-5 (port._ledger qua PartView) cot expo / notional cua PART tinh ca nua da chot (0,5 N xr1) la notional -> expo_mean PART phong dai;
  chi la thuoc do mo ta, khong vao luat chon.
NHO-6 (grid_t1.run_grid / rand_t1.run_reps) resumable theo cfg_id / (ho, gate, luot) nhung part file khong ghi sha code: neu sua code
  giua chung se tron ket qua cu-moi. Truoc khi chay that: thu muc out/*_parts phai rong (hien rong). Seed rand = [20261128, r] - khong lap,
  cung tap ngau nhien cho moi ho / gate theo thiet ke; imap_unordered + 1 file / luot => khong tron luot.

## 8. CHOICES_T1 (22 muc) - soat
Khong muc nao trai prereg. Muc co the 'lam dep' da kiem: 2/3 (TP dung muc - bao thu khi trung TIME), 7 (TP phan con lai chi tu phut sau
- bao thu; thuc te 0 khac biet tren mau), 8 (phi PART dung tong, lech thoi diem <= 0,035 % N), 4 (map ma - khong vao luat chon), 5 (NHO-1),
17 (hang xom: doi 1 tham so 1 nac trong ho; R cua VOL theo thu tu 1,2,3,khong TP; 3 bo goc B1 cua HEDGE khong co hang xom theo bo goc
=> it hang xom hon, cao nguyen de/kho hon tuy truong hop - chap nhan duoc, da ghi), 18 (T-b, T-d dung chu prereg), 19 (T-e = bo 5 %
lenh LAI nhat theo net, cong hedge_pnl cho HEDGE - hop ly vi chan long khong la 'lenh'), 21 (rand dung nghia B1).

## 9. Khoa chan
grid_t1 / rand_t1 / report_t1: main() tu choi neu thieu '--real I_HAVE_A1_PASS' (assert trong build_real); select_t1 khong co main.
work/ chi co exits_t1_{BRK,VOL,PART,STATE}.npz (bang thoat - duoc phep); out/ RONG; logs/ chi exits_all + test_*. Khong file luoi /
select / rand / report that nao. Logging: 0 print() trong code/ va test/. Tat dinh: test g PASS (A1 chay lai).

## 10. CHUA kiem
- Vi tri 124 gap > 24 h so voi ung vien that (chi biet 0 miss, nhu DEV). Nhanh 'miss' chi kiem tren du lieu gia (test h).
- Khong kiem lai noi bo B2 gate_series / B0 candidates / tier-1 signal (da audit o tang truoc) ngoai quy uoc thoi gian.
- Toc do chay that (uoc cua DEV ~7,5 h cho rand) - khong do.
- Mutant cho port.py (phi TP) khong ap dung: phi TP nam trong port B1 (khong sua), dung chung moi ly do thoat.

## 11. sha256 cac file da audit (KHOP SHA256SUMS.txt cua DEV)
```
c8074eb655ab4b1f61da573bcce5c7c217fb931a7a5802bb2b144f987b88fc05  code/common_t1.py
1a50e86e441d02390cbad93c6398615450df344efc6e264ebe69b9f6d285ed7a  code/exits_t1.py
d59531a8c6e4a0ba1fbcd080fc903a880dee1e3981e907416bde59d290387a8d  code/hedge_t1.py
b35f46ef51f36ab2574522898e252a19cb1401e4184d025986e9c29a8c02cb17  code/grid_t1.py
36370bd1bdae8b60904bcf24601ce091693bc08d92e5c8eb3bfccbb4c4f48391  code/select_t1.py
40a613494aa85271645dcca836057564815723fb8eb04f34e61d052cab8fc949  code/rand_t1.py
32c9ae823884b77451914183bac00393cac1ffb932808c0cb7bfdcfeb6d70e2a  code/report_t1.py
281d8dbf8f41b2b0ca37ad691e6c29887d2e4ba821e8b63afc25a0cbbbeaa0dc  code/fake_t1.py
74c40afbb8eb2a19a7834c04586b66b9e904d3d976a7789ef5eed706ffb88f2e  test/test_t1.py
code/common_t1.py: OK
code/exits_t1.py: OK
code/fake_t1.py: OK
code/grid_t1.py: OK
code/hedge_t1.py: OK
code/rand_t1.py: OK
code/report_t1.py: OK
code/select_t1.py: OK
test/test_t1.py: OK
```

## 12. Ghi chu quy trinh A1
A1 da tao roi xoa ngay 1 file rong '.a1_tmp_path_note' trong levz_t1 (17:12, so suat lenh; khong con). Ngoai ra chi ghi file nay.
Script A1 (ref_a1.py, hedge_hand.py, mut.py, pv.py, u_all.py) o thu muc tam da xoa; noi dung co the viet lai theo mo ta muc 2-6.
