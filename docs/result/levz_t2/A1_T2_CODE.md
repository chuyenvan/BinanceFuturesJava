# A1_T2_CODE - audit doc lap code T2 (doi diem vao lenh SHORT LEVZ) - TRANG THAI TAM (2026-11-27 09:05 +07)
Auditor A1 (khong phai DEV). Luat: PREREG_LEVZ_T2 (b0515b3c) + ADD1 M1-M6. Khong chay grid/select/placebo/report that; khong tong hop loi nhuan.
Thu muc tam: /tmp/a1t2.0LBOGl (script ref_entry.py, ref_exit.py, ref_gap.py, port_hand.py, plc_chk.py, mut.py + log).

## KET LUAN TAM: PASS-WITH-MINOR (CHUA CHOT - mutant dang cho lock oracle_heavy, xem muc 7)
Khong thay loi CHAN. sha256 9 file khop SHA256SUMS.txt va giao viec.

## 1. Doi chieu prereg/ADD1 <-> code: KHOP
- EL_b: lv = p0 (1+b), p0 = close1m[60k] (= gia vao E0); xet nen 60k+1..60k+2879 (dong <= T_k+48h), chi nen THAT, close >= lv, gia = lv
  (entry_t2.py:244-253). Phut tin hieu khong duoc xet; vi lv > p0 nen khong the khop o phut tin hieu.
- EB: L = min close1m[60h-1], h = k-23..k (24 nen gio dong tai <= T_k, truoc tin hieu); xet tai T_{k+j}, j=1..48 bang close1m[60(k+j)-1]
  (phut cuoi gio, da dong); vao close nen 60(k+j) x 0.999 (M1) (entry_t2.py:256-285).
- EO_x: X = log OI hang h = ban ghi cuoi ts in (T_h-70m, T_h-10m]; max tren hang k..k+j (fmax bo NaN); trigger OI_j <= (1-x) max;
  vao 60(k+j) x 0.999 (entry_t2.py:288-296).
- 211 bo thoat, luoi 13 293 (assert common_t2.py:98,120); gio vao port kb = floor(m/60) (exits_t2.py:68, grid_t2.py:42);
  funding chi moc T_{kb+h}, h>=1, khi nen vao dong truoc moc (exits_t2.py:82); time-stop/SL/trailing tinh tu m (duong gia canh m).
- WFO: select_b1.rule khong sua (restrict() chi cho thay fold duoc phep), hang xom trong ho thoat, subset theo kieu vao.
- Placebo M3 dung; U-a..U-f dung prereg; nhan [in-sample] cho DEV co trong report.

## 2. Diem vao - tham chieu doc lap tren du lieu that (vong for, close1m + gaps + OI 5m GOC)
420 ung vien ngau nhien (seed 20261127), moi kieu vao (gom khong khop):
| kieu | khop ref | khong khop | lech |
| EL_1 | 369 | 51 | 0 |  | EL_2 | 333 | 87 | 0 |  | EL_3 | 300 | 120 | 0 |
| EB | 133 | 287 | 0 |  | EO_3 | 402 | 18 | 0 |  | EO_5 | 371 | 49 | 0 |
- OI tre: 1 522 diem X (lagged) so voi metrics5m goc (ban ghi cuoi ts in (T-70m, T-10m]) -> lech 0 (38 diem goc thieu -> X NaN dung).
  Ref EO dung TRUC TIEP OI goc 5m (thang <= 2025-12, khong mo 2026).
- EB: close gio mm[60h-1] == CL[h] cua levz2 (CL = nen dong tai T_h): 10 056 diem, lech 0 => L chi tu 24 gio truoc tin hieu.
- EL: tre min 1 phut; px/p0 dung 1,01/1,02/1,03. EB/EO: tre la boi so 60, 60..2880 (vao sau moc 1 phut).
- Khong kieu nao dung gia/OI sau phut vao (ref chi doc <= phut quyet dinh; test c cua DEV cung PASS khi chay lai).

## 3. Bang thoat tu phut vao that - minute loop doc lap
EL_2 230 lenh (229 r>0), EO_3 230 lenh (d>0, r=0) x 5 bo: B1 (30%,336h,off), (15%,168h,7%/3%), (50%,24h,3%/5%), PART(12%,168h),
STATE(zo 0, 30%, 720h): j (tu T_kb), ly do, xr, funding: lech 0 / 2 300 so sanh. Them mk/fh 49 gio dau moi lenh: lech 0.
Them 60 lenh EL r = 59 (moc T_{kb+1} trung luc nen vao dong -> khong nhan funding): lech 0. Ly do da phu: sl/trail/time/state/be/tp/eod.
CHUA phu: 'miss' (khong lenh that nao co gap trong duong 721 h - 134 gap toan bo du lieu).

## 4. Port (B1 port.py khong sua) - kich ban tinh tay: KHOP
K=2: A vao k100 (r0), B tin hieu k100 vao tre 5h17' (kb 105), C k102; D cung coin A k150; E cung coin B k175.
Ky vong tay: A@100 N=3000, C@102 N=2999,37 (B dang cho KHONG chiem cho), B@105 N=2980,101447 (eq sau C dong); D bi cooldown
(150-100<=72), E bi cooldown tinh tu kb 105 (70<=72). grid/port cho dung ket qua nay.
Khong nhin truoc: equity tai kb chi gom vi the dong/mo truoc kb; slot giai phong trong (T_kb, m] khong dung (bao thu).

## 5. Placebo
Du lieu that (chi phut vao): EL_2/EB/EO_3 rep0: so lenh = so khop (3 819/1 406/4 584), offset 1..2880, 100 % nen that, trung binh
1 428-1 448 (deu ~1 440), rep0 != rep1; perm = hoan vi trong nam (EB bo 2 do cua so cat cuoi data, chi mo ta). 1 200 seed khac nhau.
p_value toy: (1+1)/5 dung; nam thieu tinh la khong >=; real NaN -> p NaN. Test f chay lai PASS (shard 0/2+1/2 == 1 tien trinh).
Cong bang: lech co he thong ngoai "gia tang >= b%": (a) EL that khop dung muc, KHONG truot; placebo truot 0,1 % (theo prereg);
(b) EB/EO that luon r = 0 (vao dau gio) con placebo r > 0 98 % -> port gan slot tai kb som hon fill toi 59 phut (ca hai deu bao thu
nhu nhau); (c) do tre placebo trung binh 24 h vs that 3-11 h -> nhieu lenh placebo vat fold/eod hon. Khong lech nao lam dep that.

## 6. Loi NHO (khong chan)
N1 report_t2.py:249-253: U-c dung p_time ca khi placebo chua du 100 luot (p_time_complete chi ghi). Sua: U-c = complete AND p <= 0,05.
N2 report_t2.py:217 (CHOICES 15): E0 khong cham duoc nam => kieu vao "hon E0" nam do. Prereg khong noi; nghieng co loi. MASTER chot
   (de xuat: U-f truot neu E0 khong cham duoc, hoac bao ro).
N3 port (CHOICES 9): trong cung gio kb, uu tien slot theo s chu khong theo phut khop -> biet truoc ung vien diem s cao se khop trong
   gio do (chi anh huong EL/placebo khi tranh slot trong cung gio; khong dung ket qua lenh). Ghi han che trong report.
N4 exits_t2.py:82: r = 59 -> moc T_{kb+1} trung luc nen vao dong, bi loai funding (bao thu, mo ho). Ghi CHOICES.
N5 CHOICES 14: test g dung 19 luot placebo (lech giao viec 3 luot) - hop ly, da ghi.

## 7. Mutant / test (dang chay)
Chay lai test_t2 tren ban copy (BASE doi sang /tmp, nproc 3->2): rebuild entry/E0/EL_1/EL_2 == ban goc (tat dinh);
a_exits, a_grid, b, c, d, e, h, f: PASS. g: dang cho lock. 16 mutant (EL gia=close, p0 phut sau, EB L sau tin hieu, EB/EO cung nen,
OI khong tre, max OI tuong lai, EL bo mask nen that, funding moc truoc, bo luat r, j khong cong r, STATE khong tru r, port ceil,
port gio tin hieu, placebo ngoai cua so, placebo khac so lenh, select thay fold kiem): KET QUA CHUA CO (log /tmp/a1t2.0LBOGl/mut_mut.log,
mut_g.log). Theo suy luan: 'p khong cong 1', 'U-f so voi B1', 'select thay fold kiem' se LOT test g (g chi assert verdict).

## 8. CHOICES 16 muc: 1-8, 10-13, 16 OK; 9 OK + N3/N4; 14 OK (N5); 15 xem N2.
Khoa --real I_HAVE_A1_PASS: 4 script, thieu/sai khoa -> LOCKED. out/ rong; work/ chi entry + exits. Khong print (chi logging). Tat dinh.

## 9. CHUA kiem
- 'miss' tren du lieu that (khong co ca); 94 coin phang 3 ngay cuoi data (co the delist chua vao gaps - ke thua B1, khong rieng T2).
- Ket qua mutant + test g (dang chay). Doi chieu kline goc cho nen THAT (dung gaps.npz da audit o B1).

## 10. Vong chot (A1 doc lap thu 2, 2026-11-27)
- sha256 9 file khop giao viec (7 file da audit khong doi; report_t2 c0517f21..., test_t2 cbd436a6...). out/ rong; work/ chi entry + exits;
  --real I_HAVE_A1_PASS (require_real) co o grid / select / placebo / report main.
- Mutant cu (log A1 truoc): BAT 13 (M1, M2, M4, M5, M6 boi b; M8a boi a_exits; M8b, M9, M9c boi d; M7, M7b boi e; M10, M11 boi f);
  M3 (EB L sau tin hieu) = build error IndexError (lo ra, khong lot im); LOT: M15 (EL bo mask nen that; b/c/h pass), M14 (select thay
  fold kiem; g pass 2 lan).
- report_t2 moi: N1 dung (U-c = complete AND p <= 0,05; complete = du NREP time = 100, --summary luon so voi NREP), N2 dung (nam E0 NaN
  => U-f False + note). U-a (top-20 valid ca 2 nam > 0), U-b (>= 0,5 F1/F2/F3), U-d (trung vi qua cau hinh cua F2_n + F3_n; F2 = 2024,
  F3 = 2025 da kiem FOLDS), U-e (bo ceil 5 % lenh LOI NHAT cua top-1 tung nam, thieu top-1 => False), U-f, ket luan 3 muc dung prereg
  sec 5; p = (1 + n_ge) / (N + 1), luot thieu nam = KHONG >= (ADD1 M3). DEV gan [in-sample].
- Test ban copy: n12, e, h PASS; f: xem duoi. Mutant moi (n12 + e; placebo count + f): BAT X2 U-c bo complete, X3 U-f so hang so,
  X4 U-f True khi E0 NaN, X11 PART khong can U-c (n12); X13 placebo khac so lenh (f). LOT (n12/e): X1 p khong +1, X5 select thay fold kiem,
  X6 top-200, X7 U-a mot nam, X8 U-b 30 %, X9 U-e bo lenh LO nhat, X10 U-d sai fold, X12 p < 0,05. Khong chay g tren mutant (17 phut/luot);
  suy luan: g chi assert verdict => X1, X5/M14, X6-X10 nhieu kha nang van lot; X12 co the bi g bat (19 luot => p min = 0,05).
  Code that dung o tat ca cac diem nay => "test chua bao ve" (NHO, T1).
- Kich ban tinh tay (EA / EP + E0, 3 cau hinh, 2 nam, 5 luot placebo): describe, wfo_stat, p_value (ge = 2, p = 0,5) va 7 ca criteria
  (DAT / CO CAI THIEN / KHONG HON E0) KHOP 100 %.
- NHO moi: T1 test chua bao ve tang select / report / p (danh sach LOT tren; nen them unit test thuan cho criteria tung U, p_value,
  concentration, WFO folds). T2 M15: test b/c khong phan biet mask nen that cho EL (code dung).
- KET LUAN CUOI: PASS-WITH-MINOR (khong loi CHAN). Mo khoa --real duoc, kem N3/N4 (CHOICES 19-20) va T1/T2 ghi nhan.
- Test f ban copy (ban goc): PASS.
