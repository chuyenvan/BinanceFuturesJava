# F2B_DEV - driver FAMILY2B (DEV agent, 2026-11-26, ban 2 sau audit A1 PASS-WITH-MINOR)
Prereg: docs/prereg/PREREG_FAMILY2B.md @5f917679 (muc 4, 8, 9). Audit: ~/claude_master/w3/levz_rev/A1_F2B_DRIVER.md.
Chua push / goi Kaggle. Driver TU CHOI push khi f2b_driver.py / test_f2b_driver.py chua commit (C1) -> MASTER commit truoc.

## 1. Ban goc r1_a3_driver.py
- Dung: ~/claude_master/vz_e1_wt/research/r1_s1/r1_a3_driver.py (branch research/vz-e1, commit cuoi cham file c57b75ba),
  sha256 bcc977921aad904e... (223 dong). Ban da chay r1-a3 (~/claude_master/res1109/r1_s1/) va ban luu tru
  docs/result/res1109_raw/r1_s1/ trung sha256 -> khong mo ho.
- Phu thuoc (doc, khong sua): ~/src/BinanceFuturesJava (branch module) tools/kaggle_sim.py 7edd7945...,
  research/analysis/gate_ablation_driver.py 66810e4c..., gate_skipfull_driver.py 0bd5f6a0...,
  ~/claude_master/iso/burst_cooldown_driver.py 8e9eea0b...; tsx/code_sha.txt = a8690d46.

## 2. File (research/r1_s1/)
- f2b_driver.py      sha256 acbcb9de72f4a0871bbe06ba7e090adb265eaf7bd41464cf2b0e94690c820997 (827 dong)
- test_f2b_driver.py sha256 4e111e6776330109e8bc5f4c735c8cf4dd23174b3042c92b6400372c6eabdb74
- F2B_DEV.md (file nay)
State NGOAI worktree: $F2B_STATE_DIR (mac dinh /home/ubuntu/kaggle_sim/f2b_state): PARITY_OK_<seed>.json, pushed/<tag>.json
(ghi git_head, driver_sha256, version, overrides, extra_env, ts_push, ts_fetch, ok, java_rc, n_trades, equity_final, error).
Out cu KHONG xoa: chuyen sang /home/ubuntu/kaggle_sim/out/_stale/<slug>.<ms> truoc moi fetch.

## 3. Test: 35/35 OK (khong mang, 0.46 s)
cd ~/claude_master/vz_e1_wt/research/r1_s1 && PYTHONDONTWRITEBYTECODE=1 F2B_STATE_DIR=$(mktemp -d) python3 -m unittest -v test_f2b_driver
Moi ham mang kaggle_sim gia lap cuc bo; OUTDIR/WORKDIR/STATE tam moi test (run tham chieu symlink, chi doc).
- Bang (4): 25 o go tay x 2 seed, check_f2b dat 50; nhanh A khong X14, B con; khong DCA_GRID_ENABLED.
- NEN (1): == R.OV, cfg r1-a3 tru tag, run.py == run.py r1-a3 DA PUSH (A1, S7) tru tag, metadata tru id/title.
- Guard (11): WL_ADD dung 5 key go tay; DCA_GRID_SCALE bi bat boi loi "(b) key them ngoai whitelist" cu the (M13);
  key la, doi gia tri r1-a3, env la (HOLDOUT_UNSEAL), jar khac, end 2026, seed la; dry/list 0 goi mang, 0 file.
- C1 git (3): porcelain " M"/"??" -> NotCommitted, chan TRUOC free_slots; marker ghi git_head + driver_sha256; git that (chi doc).
- Parity (9): chan push khi chua/sai/khac seed PARITY_OK hoac out tren dia thieu; md5 printDone r1-a3 tren dia == ho so;
  mac dinh KHONG cho (push -> RUNNING -> COMPLETE: fetch 1 lan); --wait; out cu dung md5 nhung kernel moi lech -> LECH (N6),
  out cu sang _stale; result.tag sai -> loi; ERROR -> exit 7 khong push lai; bo so jar_sha256 bi bat (M17);
  PARITY_OK hop le nhung printDone/jar tren dia bi doi -> khong hop le (N3).
- Smoke (4): mau tot PASS + in TAKE_PROFIT_DONE; tung tin hieu FAIL (parse error, jar, mapper 500, DCA_LEVEL1, X14 nhanh A,
  thieu TAKEPROFIT, thieu PREARM_SL); extHours=0 khong dem; nhanh B: X14 > 0 hop le, khong can TP; CLI exit 6.
- Grid (4): thu tu 48 o co dinh; status chi doc; 3 vong (max-slots, chi seed co parity, XONG fetch 1 lan, LOI khong push lai,
  FREE=0 khong push); CLI 1 vong.
Mutant (ban copy tam): bo so jar parity, them DCA_GRID_SCALE vao whitelist, bo kiem X14, bo bam lai md5 (parity_ok),
dung lai out cu (bo _stale) -> ca 5 deu lam test FAIL.

## 4. Lenh mot dong (duong dan vz_e1_wt; cwd bat ky)
D=~/claude_master/vz_e1_wt/research/r1_s1
python3 $D/f2b_driver.py list | dry A10R1-S1 A1
python3 $D/f2b_driver.py smoke A10R1-S1 A1                 # tag f2b-smk-A10R1-S1-a1
python3 $D/f2b_driver.py fetch A10R1-S1 A1 --smoke         # kiem muc 9 + A1 N1/N2; FAIL -> exit 6
python3 $D/f2b_driver.py parity A1                         # goi lai dinh ky: push -> (dang chay) -> fetch moi + so md5; S7 tuong tu
python3 $D/f2b_driver.py grid --max-slots 5                # MOT vong; goi lai dinh ky
python3 $D/f2b_driver.py status                            # bang 48 o + parity + smoke (khong push/fetch)
python3 $D/f2b_driver.py push A10R1-S2 S7                  # 1 o le (can PARITY_OK_S7)
Exit: 0 ok | 2 tham so/cau hinh | 3 parity lech | 4 FREE=0 | 5 chan (parity/da push/chua commit) | 6 smoke FAIL | 7 kernel loi.

## 5. Quy tac kiem smoke (fetch --smoke, smoke_check)
Quet moi *.log, sim.out (.gz neu chua giai nen) trong out dir, dem THEO TUNG FILE; printDone.csv doc bang csv (cot level, status, profit).
FAIL neu: >= 1 dong "SIM env override parse error"; JAR_SHA256 (log + result.json) khong thay hoac != jar r1-a3 (cc0f9d11...);
mapper (dong "Loaded Symbol Mapper: N" + result.json symbol_mapper) < 800 (khong thay so -> canh bao); printDone co dong level
DCA_LEVEL*; o co SL ma 0 dong "PREARM_SL sym="; o co TP ma 0 dong "TAKEPROFIT sym="; nhanh A (bo X14) ma co dong
"[TSX] extHours=<n>" voi n > 0 (Java chi in dong nay khi EXT_HOURS > 0; r1-a3-a1 full.log co dung 1 dong extHours=336).
IN (khong ket luan): 5 dong TAKE_PROFIT_DONE dau (sym, entry, tp, profit, status, level) - cot profit la %, doi chieu +TP x 100
(A10R1: ~10.0); so dong "HARD SL"; dem status printDone. Profit co tru phi hay khong: nguoi doc xac nhan.

## 6. Grid (N5)
Thu tu co dinh: CELLS (bang prereg, bo NEN) x seed (A1, S7). Mot lan goi: o da push chua fetch -> _status; COMPLETE -> chuyen out
cu sang _stale + fetch moi (XONG neu ok & java_rc 0, nguoc lai LOI); ERROR/CANCEL -> LOI (ghi marker, KHONG push lai, bao MASTER);
roi push o CHUA_PUSH theo thu tu neu parity_ok(seed) va so kernel f2b dang chay < --max-slots va free_slots() > 0 (NoSlot -> dung).
Khong vong lap / sleep. status = cung bang, chi doc.

## 7. Lua chon prereg khong noi ro (MASTER xac nhan)
1. Gia tri override la chuoi nhu bang; TP = Decimal R x |SL|; SIM_TAKE_PROFIT_ONLY="true" (parseBoolean; "1" = FALSE).
2. Tag smoke rieng f2b-smk-<cell>-<seed>; tag luoi giu chu hoa ten o; slug/kernel id chu thuong.
3. parity so: result.tag, md5_printdone result.json, md5 file printDone, jar_sha256 voi ho so r1-a3-<seed> (md5 day du doc tu
   out/r1-a3-<seed>/result.json, doi chieu tien to prereg). Truoc moi push luoi: bam lai printDone tren dia (N3).
4. Ket qua gan voi lan chay: chi fetch khi _status (ban kernel moi nhat) = COMPLETE va marker push ton tai; out cu chuyen
   _stale TRUOC fetch; kiem result.tag. Kaggle API khong cho chon version khi fetch -> day la muc gan toi da (ghi version neu API tra).
5. R.build chay trong WORKDIR tam; R.a3_sha cache trong bo nho.

## 8. Prereg sai / thieu (A1 neu, DEV xac nhan) - KHONG sua prereg
(i) muc 3: cong thuc leg thieu he so tierMultiplier (CoinRankManager.getBudgetMultiplier) - chung moi o.
(ii) muc 9: "tsxDeferTicks = 0" - Java khong in chu nay; dau hieu dung = 0 dong "[TSX] extHours=<n>" voi n > 0 o nhanh A (muc 5 tren).
(iii) muc 10: duong dan ~/src/BinanceFuturesJava/research/r1_s1 khong ton tai (branch module) -> dung duong dan muc 4.
(iv) muc 3: bay DCA_GRID_ENABLED=false voi 1,0,0,0 la 0,75 % (ladder van chia sum weights), khong phai 0,375 % - khong anh huong (da cam).
Them: muc 9 "TAKE_PROFIT_DONE profit = +10 %" chua biet co tru phi -> doc tay.

## 9. Con no
- Chua chay that smoke / parity / luoi (sau khi MASTER commit). Chua cham diem muc 5.
