# ADD24 R-LIVE ERRATA7 - bao cao DEV-HARNESS (Opus), 2026-11-24 ~19:50-20:10 +07
Viec: sua 3 cong V (V4b, V6, V10a) theo phan xu A1 + quyet dinh MASTER (V10a phuong an CHAT), du thao ERRATA7, script luot #3.
KHONG chay lane, KHONG chay official, KHONG mo output cham. Tien do: v12/add24_errata7.progress.

## Ket qua
- HEAD moi add24_wt (v1.2/add24-harness, chua push): 8d397ce2dbbdf3db72da9dd7bb4399866c675911 (cha a66109c1). 5 file: rlive_gates.py
  (V6 + chep them khoa V10a vao gates.json), live_log_parse.py (quy tac EQ_INCOME_ERR, C3MainEquity:218), v10_buffer.py (dieu kien
  (1)/(2) + phut chuyen trang thai + bo nen END-1'), tests/test_errata7.py (moi, 30 ca), tests/run_tests.sh (goi test moi).
- Du thao: w3/add24/ERRATA7_PROPOSED.md (ASCII, khuon ERRATA6, muc A-H, diff day du). Script: w3/add24/run_rlive_e7.sh.
- Tinh thu cong tren ban sao luot #2: V1..V8, V10a = true. V6 expect 6774 (window 7049, N1 275, last 1; minutes 6773 x 3 lane).
  V4b unmatched 0. V10a: domain 6769, dat (1) 6215, (2) 554 = 553 subset + 1 subset_trans (2026-11-21 16:29), KHONG DAT 0.
  gates.json / V10.json moi: v12/add24_errata7_sandbox/keep/ (sha: keep.sha256).
- Ong nuoc mu: score_L0 rc 0, score_L0DRY rc 0, conclude rc 0; 11 file; sha: v12/add24_errata7_sandbox/blind.sha256; blind/ chmod 000.
- Test: bash -n, py_compile OK; test_score 41/41; test_parser_v4b ok; test_errata7 30/30. Khong chay test java (guard_gate, full_tier3).
- Preflight e7 (HEAD 8d397ce2, khong go): TRUOT 3 - (1) ERRATA7 chua commit (du kien); (2) /dev/shm/add24/vision TON TAI (do luot #2 tao;
  E6 cung kiem dieu nay); (3) dia / 13008 MB < 15300 (lien tuc giam trong phien: 17250 -> 12867 -> 13008 MB; nguyen nhan da kiem:
  w3/p15_stab/s2 (s2_chain.sh) ghi funding.bin 4,4 GB moi lan, 19:31 va 19:50). Con lai DAT ke ca Vision 5170 request non200 0,
  oracle_heavy.lock ranh. Canh bao watcher parity pid 936196 van song (nhu luot #2).

## Diem MASTER can quyet / biet
1. Truoc "go": phai co nguoi xoa /dev/shm/add24/vision (DEV khong duoc xoa) va giai phong dia >= 15300 MB (s2_chain dang an dia).
2. Phut dat theo (2) KHONG duoc chuyen sang V10b (rlive_score chi doc outside_domain_mismatch_minutes - y nghia khong doi). Khac biet
   giu o 10 symbol chi con duoc danh gia o buoc cham L-X / L-T / L-SL. Dung voi "giu mien, chi doi dieu kien dat" nhung MASTER nen xac nhan.
3. V10a_mismatch_minutes doi nghia: nay = so phut KHONG DAT (so phut khong bit-exact cu -> V10a_not_bitexact_minutes). Da ghi ERRATA7 C.
4. Symbol ban ghi rig lay tu trace_dec (hang held=0, cot r_bits) - v10 cu chi doc symbol/held/bookfull. Da kiem multiset r_bits held=0 ==
   appended 6769/6769 phut (khong in gia tri); khac => phut truot (fail-closed).
5. A1 goi y grep them dong [C3-LIVE*] hiem (vd C3MainEquity:236 "funding ... khong on dinh"): KHONG them - log OW2 co dinh, parse lai
   cho unmatched 0, 49 file output parse trung byte voi luot #2 (chi counts.json khac + eq_income_err.csv moi).

## Khong chac chan
- Dinh nghia "phut chuyen trang thai": live = floor phut cua moc SUBMIT leg dau / dong cum; rig = phut co trace ma tap held khac phut
  co trace truoc do (sau lo N1, thay doi gan vao phut dau sau lo). La cach doc cua DEV cho cum tu "thoi diem mo/dong"; chi 1 phut dung toi.
- sha blind de so tat dinh sau luot #3: score.json / conclusion.json co the chua duong dan out => co the khac byte du ket qua giong; DEV
  khong mo nen khong biet (suy doan).
- Luot #3 chay lane lai: gia dinh rig tat dinh (A1 neu) => cong du kien nhu tinh thu; chua kiem tren lane moi.

## Phan nhay cam DEV da doc / thay
gates.json luot #2 + sandbox (V4 = 24 SUBMIT); dong log luot #2 co so dong tag (SUBMIT 24, FILL_STREAM 23, EXEC_ACK 24, EXEC_FILL 1,
CUM_DA_DONG 16, phan sau bi cat); V10.json / V10_diag (S_m / X / flex theo symbol o 554 phut; 16:29: S_m EVAAUSDT+PONSUSDT, X PONSUSDT,
flex EVAAUSDT); so dong trace_dec theo held (24855 / 137601). KHONG doc noi dung submit/exec/fill/order/trail/leg/eq; khong gia/size/PnL.
Khong doc file secret; ten bien .env khong can xem.
