# A1_S2_CODE - audit doc lap code tang S2 (LEVZ), 2026-11-26
Auditor A1 (khong phai nguoi viet). Luat: PREREG_LEVZ_S2 (74ec941e) + ERRATA1 (5f917679). Khong chay grid/select/rand/report that,
khong tong hop PnL that, khong doc 2026, khong sua code goc. Lam viec tren ban copy trong /tmp (da xoa).

## KET LUAN: PASS-WITH-MINOR (khong co loi CHAN; 1 diem dien giai p_wfo MASTER phai chot truoc RUN)

## 1. Tin hieu - tu viet lai doc lap (trong tam)
Code A1 rieng (sliding window numpy cho OI mean/sd ddof1 tren hang t-168..t-1, >= 135 hop le; funding so nguyen chinh xac bang
tong truc tiep tung lat (lo, j) + Fraction cho phuong sai, KHONG cumsum; P6 nguong = np.quantile tren s cua 90 ngay TRUOC 00:00
ngay d (khoi dong 30 ngay); P5/P5b: median sd truot 2160 hang < t (>= 720), san thich nghi, top 2 % cat ngang tai DUNG hang t,
>= 40 coin, hang pct average). Nguon: L.Data('2025-12') (X = ln OI ts in (t-70m, t-10m], funding ts <= t - 1m), U, has1m B1.
| tap | so diem so | lech trang thai | lech diem s |
|---|---|---|---|
| P6a | TOAN BO 4 790 328 coin-gio U (2021-12..2025-12) -> 5 964 ung vien | 0 | max 1.4e-9 (sai so float rolling pandas) |
| P6b | toan bo 4 790 328 -> 11 222 ung vien | 0 | max 1.4e-9 |
| P5  | 733 gio x moi coin U = 107 387 diem (150 gio dang o trang thai, 150 gio ngay truoc vao, 150 gio ngau nhien 2022-25 + cua P5b), 326 diem dung | 0 | 0 (tol 1e-12) |
| P5b | cung 733 gio / 107 387 diem, 339 diem dung | 0 | 0 |
Kiem rieng: (i) hang cat ngang dung z cua chinh gio t, chi coin U & z huu han tai t: khop (va mutant t+1 se lech); (ii) nguong P6
ngay d chi tu hang [24d-2160, 24d) - code sig_s2.py:79-83 + khop doc lap; H0 = 2021-12-01 00:00 UTC, luoi gio lien tuc (assert);
(iii) san sd thich nghi = median rolling(2160, mp 720).shift(1) - chi qua khu (sig_s2.py:51-54); (iv) z_f so nguyen chinh xac, ih in
{1,2,4,8} nen k8 = rate*1e8*8/ih nguyen - khong con hang so trung binh ca chuoi; (v) E0: ung vien (k, c) = trang thai & U & has1m;
gia vao = close nen 1m mo luc T_k (B1 paths) -> OI <= T_k - 10m, funding <= T_k - 1m: tin hieu truoc phut vao.
Test DEV c2 (doc out/test_c2.json): PASS, 381 cat, P5/P5b/P6a/P6b >= 100 diem trong trang thai va >= 100 diem truoc vao, 0 lech.
Han che c2: moi cat T <= 6161 (<= 2022-08) - nhan qua chi kiem dau 2022; bu lai bang doi chieu doc lap toan bo 2022-2025 o tren.
Doi chieu prereg: so dot ep72 (B0 episode_starts) cua 5 tap trung DUNG ERRATA E5; gio bo < 40 coin = 121 + 10 = 131; U cua
inputs.npz (rand) == U cua L.Data (cand) (kiem).

## 2. Engine / fold
Chay lai tren ban copy: test a PASS (REF qua duong S2: DEV, Y24 = F2, Y25 = F3, 47 385 o, 0 lech), b PASS (5 352 hang trung exits.npz,
0 lech moi khoa), g PASS (tat dinh). Fold Y22/Y23 dung CUNG cong thuc FB = (kidx(01/01), kidx(01/01 nam sau) - 1) da khop F2/F3 -> lenh
mo cuoi nam dong theo kl nhu B1 ('eod'). Mutant lech 1 gio -> test a BAT.

## 3. WFO - kich ban tay (A1 tu viet, luoi gia 585 cau hinh, 3 cau hinh danh dau + 1 cau hinh doc)
A (Y22 0,5 / Y23 -0,2), B (0,3 / 0,3 / Y24 -0,5), C (0,2 / 0,2 / 0,25), D (Y22 = 0, Y23..Y25 = 10). Dap an tay 2023 -> A, 2024 -> B,
2025 -> C; code: A, B, C (D khong bao gio duoc chon du nam test = 10). passing20 dung thu tu tay (A,B,C + cfg_id tang dan), trung vi
top-20 va tong khop. Tinh huong Y23 am toan luoi: scored = [2023], 2024/2025 'khong cham duoc', tong = chi 2023 (khong cong 0).
Y22 n < 30 toan luoi: scored = [] , tong NaN. p_wfo tay [0,1, NaN, 0,05, 0,01, -0,2] vs that 0,05 -> 0,4 = code.

## 4. RAND
Pool = coin-gio U & has1m TRONG NAM (dung prereg "so luong moi nam"; B1 theo thang), n_y = so episode_starts (gap <= 72 h) cua tap
trong nam y (= E5); rut khong lap; cooldown 72 h ap o port.run (cung engine, nhu ung vien that); bang thoat = B1 exits.compute; cung
585 cau hinh; seed default_rng([SEED, set_idx, rep]). Kiem gia: rut nam dung so, trong U, khong trung; --shard 1/2 + 0/2 == 1 tien
trinh (DataFrame equals True).

## 5. Loi / van de
NHO-1 (phai chot truoc RUN) rand_s2.py:102 + select_s2.py:62-65: wfo_sum cua luot ngau nhien cong tren cac nam LUOT DO cham duoc,
con that cong tren cac nam THAT cham duoc -> so tong 1 nam voi tong 3 nam (ERRATA chi quy dinh luot 0 nam). De nghi: wfo_sum ngau
nhien chi tinh tren scored_years cua tap that; luot thieu bat ky nam nao trong do -> KHONG >= that.
NHO-2 (cau truc, dung E4): 'min qua fold train' bat cau hinh hop le o Y22 cho CA 3 nam kiem -> tap yeu 2022 mat ca 3 nam. REF chi 25
ung vien / 5 dot 2022 -> gan nhu chac n < 30 o Y22 -> REF 0 nam cham duoc, khong co so doi chieu "cung quy trinh".
NHO-3 test hong (tong mutant: 4 BAT / 5 LOT chay + 3 LOT theo doc code): test_e vong tron (dem so luong theo chinh pools cua ham bi kiem) - mutant dem ung vien thay dot LOT; test_d khong
kiem dinh nghia top-20 (top-200 LOT). Them: assert n_y == cand_s2.json ep72_b0 va kich ban tay co gia tri phan biet.
NHO-4 CHOICES #5 van ghi "tinh 0" (da bi MASTER thay, code theo quyet dinh moi); #10 mo ta test c (0 diem trong trang thai) - da duoc
c2 thay the. P5b = xep hang TRONG tap f >= trung vi (dung D5b sigcount, E5); nguong 40 coin tinh tren fin2 (CHOICES #2) - chap nhan.

## 6. Mutant (ban copy; base: d e f a b g deu PASS)
M1 WFO dung Y24 khi chon 2024: d BAT | M8 fold lech 1 h: a BAT | M2 nam khong cham tinh 0: d LOT, f BAT (crash) |
M4 rand dem ung vien thay ep72: e LOT | M6 top-20 -> top-200: d LOT | M3 S-a >= 1/3: f LOT | M11 p_wfo NaN tinh >=: f BAT |
M13 seed khong theo tap: e LOT (seed van khac nhau giua tap vi chuoi seed ghi rieng; tac dong thuc: 2 tap cung luot dung chung rng - khong sai thong ke tung tap) | M5 rand luoi con 195, M7 bo nhan in-sample, M12 rand bo has1m: khong test nao assert (doc code: LOT;
fake ok1m toan 1). Mutant tin hieu (t+1, nguong gom ngay d, sd median gom t): khong chay test c tren mutant (ton ~10 phut/lan); da bi
loai tru bang doi chieu doc lap (code goc khop A1 100 %).

## 7. Ve sinh
--real I_HAVE_A1_PASS khoa o main() cua grid / select / rand / report (common_s2.require_real); work/ chi co cand_s2.npz, exits_s2.npz;
out/ khong co grid / select / rand / report; khong print (logging); khong ghi vao levz2 / b1 / rev.
CHUA kiem: mutant tin hieu qua test c; port.py cooldown (B1 da audit, test a bao dam); describe() muc 6 chua chay that.

## 8. sha256 (khop SHA256SUMS.txt)
f6b933530d3b0149cfa2b18e229d9d930e7bc4643e3d6a69ca78a54acb7c8403 cand_s2.py
cc69589878107167705fbb2a8d2f834bc7328a5ef5eed5d5bb45c490b2d6458b common_s2.py
bf1b78ecb93845631aaae8c5020fc884233ddf0643759c92a9a1aeb98a92106b exits_s2.py
2d4e01d42ff33e411534b3619961f2795cb2d462d0f04fdeb66c589073da6677 grid_s2.py
986134b412954472033674d65486bbc15d12dbadde0d295ed57d854cf7e76879 rand_s2.py
483604b3e7d4f9b97819b2cc13c0b6edee4ebdd03b0839338644ee7ab22dc09c report_s2.py
ba1ff9413afd078b100eb63d9532f7b9a375f00d34c0fd13d31d428299998608 select_s2.py
351078da39b80cf1d54c26001e40e5e849f7f14a85a8bc8bdde5f15eb540270d sig_s2.py
892e8b2e32d4cdf430e584ff6d1334f2300a584cdc52d723b8b896e6469c9b8c test_s2.py

## Vong 2 (sau ERRATA2 e6a2ad65) - KET LUAN CUOI: PASS-WITH-MINOR (khong loi CHAN)
1. sha256: 6 file "khong doi" (cand, common, exits, grid, select, sig) TRUNG ban vong 1. Doi: rand_s2 (p_wfo_stat, rng_for, real_pools),
   report_s2 (s_a, B1_REF_NOTE), test_s2 (own_ep72_by_year, test_e doc lap, test_h h1-h6, test_e2). Khong con ban cu de diff -> doc ky ham moi.
2. p_wfo tay (that cham 2024 + 2025, tong 0,10; 6 luot: cham it nam hon, bang (=, <), nhieu hon (<, >), thieu 2024) -> dap an 2/6;
   p_wfo_stat = 0,333 va summarize() tu part (wfo_sum luu = 999 bi bo qua) = 0,333 -> report lay p_wfo tu part, khong tu tong luu.
3. Test tren ban copy: h, e2, d, a, b, g, e, f deu PASS.
   Mutant: M3 S-a>=1/3 h BAT | M6 top-200 h BAT (d lot) | M13 seed khong theo tap h BAT | M5 rand luoi con h BAT (assert luoi thieu)
   | M12 bo has1m h, e2 BAT | M4 dem ung vien e, e2 BAT | P1 cong tren nam rieng cua luot h BAT | M2 nam khong cham tinh 0: h, d LOT,
   f BAT (crash TypeError) | P2 thieu nam van tinh >=: h LOT - vo hai thuc te vi top20 nam khong cham = NaN -> tong NaN -> False
   (kiem tra tap con la thua); NHO: them hang test co top20 huu han o nam khong cham.
4. Khoa --real o main() grid/select/rand/report; work/ chi cand_s2.npz, exits_s2.npz; out/ khong co grid/select/rand/report; khong print.
NHO con lai: comment rand_s2.py:121 cu; M2 chi bat gian tiep qua crash f.
sha256 ban audit vong 2:
f6b933530d3b0149cfa2b18e229d9d930e7bc4643e3d6a69ca78a54acb7c8403 cand_s2.py
cc69589878107167705fbb2a8d2f834bc7328a5ef5eed5d5bb45c490b2d6458b common_s2.py
bf1b78ecb93845631aaae8c5020fc884233ddf0643759c92a9a1aeb98a92106b exits_s2.py
2d4e01d42ff33e411534b3619961f2795cb2d462d0f04fdeb66c589073da6677 grid_s2.py
595f534a6193ffeb282cbdec7f4c9767cec68c941669da386ae4d441d7829e06 rand_s2.py
5dd0cc4e985b151aba7dc3140afad963c3f8260f51161fa99240deefc794ba0a report_s2.py
ba1ff9413afd078b100eb63d9532f7b9a375f00d34c0fd13d31d428299998608 select_s2.py
351078da39b80cf1d54c26001e40e5e849f7f14a85a8bc8bdde5f15eb540270d sig_s2.py
ee2b4343da5c0e5307ca9b2dee9bb3b785a19ec1e13612ff730e9fd4c6aa381d test_s2.py
