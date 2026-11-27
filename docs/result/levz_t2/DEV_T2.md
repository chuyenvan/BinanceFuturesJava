# DEV_T2 - doi diem vao lenh SHORT LEVZ (PREREG_LEVZ_T2 @b0515b3c + ADD1). CHUA AUDIT. Chua co so loi nhuan that nao.
Thu muc: ~/claude_master/w3/levz_t2/{code,work,out,logs}. Lua chon: CHOICES_T2.md (1-15). sha256: SHA256SUMS.txt.

## 1. Lenh (Oracle, cwd ~/claude_master/w3/levz_t2; viec nang qua flock)
F="flock -w 3600 $HOME/claude_master/locks/oracle_heavy.lock nice -n 10 /usr/bin/python3 -B"
1. diem vao (da chay, ~4 s):        $F code/entry_t2.py build
2. bang thoat (da chay, ~40 s):     $F code/exits_t2.py build
3. test (da chay):                  $F code/test_t2.py a_exits a_grid b c d e f g h
4. GRID that (~3-4 phut, 3 tien trinh; SAU A1 PASS):   $F code/grid_t2.py --real I_HAVE_A1_PASS --nproc 3
5. SELECT that (~1-2 phut):         $F code/select_t2.py --real I_HAVE_A1_PASS
6. PLACEBO time (600 luot) tren Kaggle (muc 3); PLACEBO perm (120 luot, mo ta) tren Oracle (~7-9 h wall, nohup):
   nohup $F code/placebo_t2.py --real I_HAVE_A1_PASS --kind perm --nproc 3 > logs/placebo_perm.log 2>&1 &
7. sau khi gop part Kaggle vao out/placebo_t2_parts:   $F code/placebo_t2.py --summary --real I_HAVE_A1_PASS
8. REPORT:                          $F code/report_t2.py --real I_HAVE_A1_PASS   -> out/report_t2.{md,json}

## 2. Ket qua test (logs/test_*.log)
a_exits PASS: bang E0 qua T2 == exits.npz B1 (7 mang x 195 + mk/hm/fh/fc) va exits_t1_PART / STATE (moi mang), 4 792 ung vien.
a_grid  PASS: grid E0 qua T2 (1 899 cfg) == grid_b1 W7E0 (1 755 cfg x 108 cot) va grid_t1 PART/STATE NONE (144) tuyet doi.
b PASS: 500 ung vien that / kieu vao: phut + gia vao == vong for tham chieu (OI doc doc lap tu parquet); 14 lenh gia/p0 < 0,5 la nen that.
c PASS: 200 ung vien that / kieu vao moi: nhieu loan gia sau phut vao + OI sau gio quyet dinh => phut / gia vao khong doi.
d PASS: 300 lenh that EL_1 (r > 0, khong gap): 3 bo B1 + PART + STATE == vong for tham chieu (j, ly do, xr, funding).
e PASS: 20 lan chay port tren du lieu gia: tong net = thay doi equity; <= K vi the / gio; cooldown > 72 h; vao chi o (kb, coin) da khop.
f PASS: placebo cung so lenh, phut trong cua so tren nen that, perm = hoan vi trong nam, seed, shard 0/2+1/2 == 1 tien trinh.
g PASS: gia cay san EL_2 (19 luot) => p 0,050, U-a..U-f du => KIEU VAO DAT; nhieu thuan (3 luot) => p 0,25, KHONG HON E0 (CHOICES 14, 16).
h PASS: tat dinh (entry tinh lai == luu; exits tuan tu == song song == luu; grid gia 1 tien trinh == 3 tien trinh).

## 3. Ve sinh du lieu that (khong loi nhuan)
Ung vien 4 792 (2022: 31, 2023: 1 097, 2024: 2 783, 2025: 881). Ti le khop / do tre trung vi: E0 1,000 / 0; EL_1 0,889 / 1,1 h;
EL_2 0,797 / 3,2 h; EL_3 0,714 / 5,6 h; EB 0,293 / 11 h; EO_3 0,957 / 8 h; EO_5 0,878 / 12 h. Khong NaN. Gia vao / p0 thap nhat 0,365
(coin sap trong cua so, giu nguyen - ADD1 M4). Ly do thoat B1 (moi 195 bo gop): sl 10-16 %, trailing 58-62 %, time 22-32 %.

## 4. Uoc thoi gian
grid that ~0,04 s/cfg x 13 293 / 3 tien trinh ~ 3-4 phut. Placebo: bench du lieu gia cung co (4 761 ung vien, 3 546 khop): 188 s / luot
(1 tien trinh; bang thoat 10 s, grid 1 899 cfg 178 s). 600 luot time ~ 32 gio CPU; 120 luot perm ~ 6-7 gio CPU (Oracle 3 tien trinh ~ 2-3 h).
Kaggle (he so ~2,1x cham / tien trinh trong kernel 4 tien trinh): 5 kernel x 4 tien trinh => ~3,5-4 h + ~11 phut dung close1m / kernel.

## 5. Kaggle (placebo time) - goi va lenh
File can (ngoai goi levz-kg-core hien co): levz_t2/code/{common_t2,entry_t2,exits_t2,grid_t2,select_t2,placebo_t2}.py +
levz_t2/work/entry_t2.npz (0,96 MB). Tu core (da co): levz_t1/code/{common_t1,exits_t1}.py; levz_b1/code/{common_b1,exits,port,
select_b1}.py; levz_b1/work/{gaps.npz,cand_b1.npz}; levz2/code/sim.py; levz2/work/{inputs.npz (FR),sig_W7.parquet,sig_meta.json};
close1m.npy do runner dung lai (paths.build). KHONG can: exits_t2_*.npz, levz/work/oi_*.parquet (placebo khong doc OI), du lieu 2026.
Buoc: them 6 file code + entry_t2.npz vao code/kg_pack.py (CODE / DATA), `bash code/kg_ops.sh pack && bash code/kg_ops.sh dsversion "add T2"`;
moi kernel i = 0..4 (cwd ~/claude_master/w3/levz_kg):
for i in 0 1 2 3 4; do bash code/kg_ops.sh push t2p-$i "{\"job\":\"script\",\"path\":\"levz_t2/code/placebo_t2.py\",\"args\":[\"--real\",\"<LOCK>\",\"--kind\",\"time\",\"--nproc\",\"4\",\"--shard\",\"$i/5\",\"--out\",\"/kaggle/working/out\"]}"; sleep 3; done
Tai / gop: `bash code/kg_ops.sh fetch t2p-$i` roi chep parts (time_<E>_<rep>.parquet) vao levz_t2/out/placebo_t2_parts; dem phai = 600
(6 kieu x 100) truoc khi --summary. Nen chay thu 1 kernel truoc (KAGGLE_RULES).
Luu y: runner job script chua symlink levz_t2/out => bat buoc --out /kaggle/working/out (parts o /kaggle/working/out/placebo_t2_parts).

## 6. Con no / rui ro
- A1 can audit: quy uoc kb = floor (CHOICES 9), funding nhan khi nen vao dong truoc moc, U-f khi E0 khong cham duoc nam (CHOICES 15).
- report_t2 / select_t2 / placebo --summary moi chay tren du lieu gia (test g), chua chay that (dung luat).
