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

## 10. Overlay snapshot (ban 3, 2026-11-27) - f2b_driver.py ddf97c3c..., test_f2b_driver.py bcce884e... (44/44 OK)
Ly do: iptables Oracle AS3222_CLOSE (owner, 2026-11-11) chan Kaggle -> Aerospike 161.118.212.3:3222 => parity NEN f2b-nen-a1/s7
chet "SYMBOL_MAPPER_PREFLIGHT_FAIL" (~/claude_master/w3/levz_kg/PARITY_DIAG.md). MASTER chon A: overlay snapshot, KHONG mo cong.
Nguon: ~/claude_master/w3/ho5/ho5_k2.py (sha e13a449b...) + ho5_k3.py (5539c193...), import truc tiep SAU khi kiem sha (ghim).
Co che (moi cau hinh NEN/smoke/24 o, cung mot ham overlay_patch = K3.fpatch(K2.patch(run.py))):
- Bo khoi PREFLIGHT TCP 3222; kiem sha mapper_snapshot.tsv 5c436e65 + ho5_mapper_overlay.jar 6143fa75 (ds ho5-a3-mapper-snap),
  funding_snapshot.tsvgz.bin fb024c40 (v3) + ho5_funding_overlay.jar 207e7c60 (ds ho5-a3-funding-snap); sai -> exit 2.
- Ban copy WORK config.properties: AEROSPIKE_HOST_226 -> 127.0.0.1 (moi truy cap Aerospike con sot se loi ngay).
- java -cp fund_overlay:mapper_overlay:sim.jar (jar sim cc0f9d11 KHONG doi; overlay = SimpleSymbolMapper / FundingFeeManager CFR,
  chi doi init doc file). Env SYMBOL_MAPPER_SNAPSHOT, FUNDING_SNAPSHOT dat TRONG run.py (KHONG qua extra_env; whitelist extra_env giu
  {WFO_DISABLE_DCA}). atexit xoa a3_ds/a3_bins. result.json them ho5_mapper/ho5_funding.
- cfg them 4 key want_snap_sha/want_ovl_sha/want_fsnap_sha/want_fovl_sha (ghim HO5_CFG). dataset_sources = r1-a3 + 2 ds snapshot
  (truoc pred_ds), chan ten 2026.
Snapshot: mapper 863 symbol (= "Loaded Symbol Mapper: 863" cua run r1-a3). Funding v3 = dump Aerospike test.funding_data (831 sym, toi
2026-08-05) U crawl fapi 2025-01-01..2026-10-01 (them 291 314 ban ghi, 3 420 trong 2025: BTCST/SNT/STPT/PLANCK...; cong chong lan 2025:
878 241 moc chung trung bit 100 %). Co ban ghi 2026 (sim dung o SIM_END_DATE 20251231). Dataset Kaggle hien = v3 (16 483 167 B).
Bang chung: sim-ho5-a3-rep3-s123 (v2) va rep4-s123 (v3) md5 printDone a11ce5f9 == r1-a3-s123, equity 144 003, 3 584 lenh.
CHUA kiem cho A1 / S7 => parity NEN f2b (md5 8986d332 / 083e3de0) la phep thu quyet dinh.
smoke_check them: bat buoc "HO5 mapper snapshot OK", "HO5 funding snapshot OK", "from SNAPSHOT", "Init funding fee data:";
FAIL neu co SYMBOL_MAPPER_PREFLIGHT_FAIL / SYMBOL_MAPPER_FAIL / HO5_*_SNAPSHOT_FAIL / "Error Scanning all Funding data" / "Connection
refused", hoac result.json thieu sha overlay. parity_compare cung doi sha overlay trong result.json.
fetch: fetch_selective (kernel_output_with_http_info; chi tai result.json, printDone.csv, sim.out(.gz), full/error.log, a3_funding.json,
prof_run/config.properties; bo *.bin, a3_ds/, a3_bins/, wfo_ds_pred/, > 600 MB). ks.fetch KHONG con dung.
Mutant (ban copy tam) deu bi bat: bo overlay nhanh B, thieu ds funding-snap, bo kiem PREFLIGHT_FAIL, fetch tai .bin, parity bo kiem
overlay, ghim sha funding v2.
Rui ro: (1) v3 them 3 420 moc funding 2025 so voi store r1-a3 da doc -> neu symbol do co lenh trong A1/S7 thi md5 lech (s123 khong
lech); khi do can MASTER quyet (vd dataset funding v2 b39b63ed - Kaggle chi giu ban moi nhat). (2) driver phu thuoc file ngoai repo
~/claude_master/w3/ho5/ho5_k2.py, ho5_k3.py + mapper/SNAP_SHA, fund/OVL_SHA (ghim sha, doi -> dung). (3) overlay la ma CFR decompile.

## 11. Ban 4 (2026-11-27, sua loi nho A1_F2B_DRIVER_V3 truoc LUOI; bang 25 o / overlay / whitelist / tieu chi KHONG doi)
Lam tren ban copy ~/claude_master/w3/levz_rev/f2b_v4/ (MASTER chep vao worktree + commit). Test: 58 (57 OK + 1 ERROR ky vong
test_real_git_state_readonly vi ban copy khong phai git repo); 14 mutant moi deu BAT.
- N1: parity_ok() them why += overlay_result_errs(result.json TREN DIA).
- N2: check_cell_fetch() sau moi fetch o (grid: _row_state COMPLETE; lenh `fetch <cell> <seed>` khong --smoke):
  cell_output_errs = sha overlay trong result.json + dong cam (OVL_FORBIDDEN + "SIM env override parse error") trong moi log
  + JAR_SHA256 (log + result) co va == r1-a3 cc0f9d11... + mapper co va >= 800. Loi -> marker cell_check=[loi], error="cell_check: ..."
  -> LOI (KHONG push lai); `fetch` exit 7. XONG chi khi cell_check == "OK" (va ok, java_rc 0 nhu cu); da fetch ma chua kiem -> LOI.
- N2b: marker o ghi v3_only = {n_trades_printdone, n_trades_v3_only, n_trades_v3_only_hold_2025, v3_only_per_sym}. Tap symbol tu
  ~/claude_master/w3/ho5/fund/ds3/gate2025.json (sha ghim c66396e4...): only_crawl_top = BTCST, SNT, STPT, PLANCK, tong 3 420 ==
  only_crawl (khop ERRATA2 P4). Sha khac / tong lech -> "khong xac dinh duoc" (khong doan). r1-a3-a1/s7: 0 lenh tren 4 symbol nay.
- N6: test tach rieng OVERLAY_GONE / OVERLAY_MARKERS (bo + lap) / regex 2026 (vz-x-2026, -l26, data26, -26) voi overlay_patch /
  overlay_dss tu-nhat-quan -> moi test chi con DUNG 1 loi cua lop dang kiem.
- score: muc 5 prereg, KHONG goi mang, chay voi so o tuy y (o thieu -> "chua co"). Equity cuoi ngay = b + unP dong "Update YYYYMMDD
  HH:MM => b: .. unP: .." trong sim.out, giu dong cuoi moi ngay (= research/analysis/reset_rule_score.py load_daily, RX_DAILY);
  years = ngay/365.25; CAGR = (eq_cuoi/eq_dau)^(1/years)-1; maxDD = min(eq/cummax-1); Calmar = CAGR/|maxDD| (= core_metrics).
  Toan cua so sim (2021-07-01..2025-12-30), KHONG cong chi phi legacy. PnL nam = tong pnl printDone theo nam ngay dong (loc nhu
  load_legs). Ly do thoat = dem cot status. Hop le: NEN can parity_ok(seed); o can cell_check OK. DAT <=> moi seed Calmar > NEN,
  maxDD >= maxDD NEN, CAGR >= 0.5 x CAGR NEN; VA so nam 2022-2025 co PnL > 0 o CA 2 seed (cung nam) >= 3.
  Ghi $F2B_STATE_DIR/score/F2B_SCORE.md + .json (hoac --out DIR).
  Doi chieu that (chi doc): r1-a3-a1 CAGR 37.24 % maxDD -16.85 % Calmar 2.21, n 3 622, eq 145 391; r1-a3-s7 35.67 / -17.69 / 2.02.
- Can MASTER xac nhan: (a) maxDD dung equity ngay cua sim (b+unP), khong phai MTM kline Vision (dd_mtm22 cua r1_score.py);
  (b) cua so toan bo thay vi 2022+; (c) "3/4 nam o ca 2 seed" doc la cung nam (chat hon doc tung seed);
  (d) LUU Y: r1-a3-a1/s7 va ho5 rep4 deu co java_rc = 1 (ok = true) -> grid cu (va ban nay) se gan LOI cho moi o neu kernel f2b
  cung tra java_rc 1; score KHONG dung java_rc.

### Lenh mot dong (ban 4)
D=~/claude_master/vz_e1_wt/research/r1_s1
python3 $D/f2b_driver.py parity A1 --repush                # marker cu con (A1 N4); S7 tuong tu; sau do goi 'parity A1' toi khi xong
python3 $D/f2b_driver.py grid --max-slots 5                # MOT vong: fetch + kiem o (N2) + push o ke tiep
python3 $D/f2b_driver.py status                            # chi doc
python3 $D/f2b_driver.py score                             # cham muc 5 -> $F2B_STATE_DIR/score/F2B_SCORE.md/.json

### Ban 4b - quyet dinh MASTER 2026-11-27 (5 diem)
1. java_rc: XONG = result.ok == true VA co printDone.csv VA cell_check == "OK" VA java_rc == java_rc run tham chieu r1-a3-<seed>
   (doc ho so; hien = 1). java_rc khac -> LOI. Marker ghi java_rc, java_rc_ref, ok, has_printdone.
   Ly do java_rc = 1: SimulatorMarketLevelTicker1MStopLoss.main() goi System.exit(1) sau simulatorWithInitEntry + sleep 5 s
   (src/main/java/com/binance/chuyennd/research/SimulatorMarketLevelTicker1MStopLoss.java:161, worktree vz_e1_wt) => rc 1 la ket thuc
   binh thuong; error.log r1-a3-a1 rong; tools/kaggle_sim.py:402 tinh ok = co dong cuoi + n_trades > 0.
2. maxDD = chuoi equity MTM cuoi ngay cua sim (b + unP) - CHAP NHAN (prereg muc 5). 3. Toan cua so 2021-07..2025-12; PnL nam
   2022-2025 cho tieu chi nam. 4. Nam duong = CA HAI seed cung duong, >= 3. 5. Khong cong chi phi legacy 0,008.
Score in kem (mo ta): so lenh, win % (cot profit > 0), PnL/lenh, status printDone (TAKE_PROFIT_DONE = TP; STOP_LOSS_DONE /
STOP_MARKET_DONE GOP SL / time-stop / trailing / X14 - khong tach duoc tu status), U proxy TB / max = m / (b+unP) cuoi ngay
(sim.out khong in U; m = marginRunning, BudgetManagerSimple.java:268), so lenh v3-only tinh truc tiep tu printDone moi o (ca NEN).
Test: 60 (59 OK + 1 ERROR ky vong git).
