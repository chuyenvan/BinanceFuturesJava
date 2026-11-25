# PHASE_S2A - P15_STAB Tang S2 (prereg dea45002 muc 4) - dung + phong chuoi lane sim DEV (agent RUN, 2026-11-24 18:31-19:30 +07)
Chi DEV ts < 2026-01-01 UTC. KHONG doc / tinh / in PnL, ROI, equity cua lane nao. Khong 242, khong mvn, khong java tren Oracle, khong git.

## 1. Quy trinh lane (tien le -> phan viet moi)
Ket qua khao sat (file:dong):
- pred.bin = header int32 BE n + n x (ts >i8, p15 >f4, risk >f4); A1 ~/wfo_ds_x1_2021/pred.bin md5 5dd6bb4c, n 2 500 260, 1 phut, 2021-03-31 17:00 -> 2025-12-31 23:59 UTC
  (rt_a3n.py :23 REC16, :94-104 ghep).
- Pool / ledger S1 phu thuoc p15: x1_ledger.py (rt-code, md5 c9aa44f9) :26-29 pool(tick) = coin co nhan tai tick 15' co p15 >= 0.008 (doc wfo_gate_pred.csv);
  S1 (x1_s1_save_model.py md5 00695118, :54-92) train XGBRanker tren ledger (g1lite) -> 16 JSON cut 20220101..20251001; bins A3 = a3lib/a3_build gan lai p0 cua
  net015 RAW (g015x26) theo diem S1 (res1109/r1_s1/a3_build.py :1-5, :73-100). Kiem: ledger goc cand_dev_x1.p15 == A1 tren 21 396 tick (max|d| 3.6e-9) => p15 nguon
  ledger DEV goc = A1.
- Ledger dung lai: Kaggle kernel rt-ledger-dev (work/kaggle/rt-ledger-dev/run.py; rt_t1_kernel.py :173-232 mode ledger lmode dev) -> g1lite float32 rt_g1lite32.py.
- Sim: template ~/kaggle_sim/r1-a3-s7 (run.py md5 443a75f3; CFG :16; a3_ds :73-148; pred_ds :216-257): CHINH tien le r1-a3-<seed> chi doi pred.bin (pred_ds) va
  giu chung bins A3 (r1-a3-bins sha 0d6e3781) => KHONG dung lai pool. S2 doi CA HAI (a3_ds = bins dung lai + pred_ds = pred lane), cung 1 dataset s2-a3-<lane>.
- rt_lane.py / rt_lchk.py / rt_lsim.py chi viet cho 2026 (bins26 / pred_2026 / S3) => KHONG ap duoc. Phan viet moi (toi thieu):
  code/s2_lane.py (sha256 785a43cd): pred | ledchk | a3 (import a3_build.py khong sua, chi doi MOD/OUT; dont_write_bytecode) | simk (copy run.py r1-a3-s7, chi doi 5 khoa CFG)
  | check (kiem khong-PnL). code/s2_heavy.sh (6c19be5b): Oracle heavy. code/s2_chain.sh (880325ae): dieu phoi.
  Kernel ledger moi = launcher rt-ledger-dev + 1 thay the chuoi (assert 1 lan): nguon wfo_gate_pred.csv "funding-gate-wfo-pred" -> "s2-gp-<lane>" (rt_t1_kernel.py :191).
- Kiem cong cu k0 (truoc moi lane): retrain S1 cut20220101 tu ledger goc cand_dev_x1 + feat keep9 tren Oracle => JSON sha256 14adeb85... == s1_model_allfold (TRUNG BYTE).
  rc x1_s1_save_model = 3 ca o k0 (lech ref khong lien quan JSON) => chuoi chap nhan rc 0/3 neu JSON ton tai.

## 2. 8 lane (LANE.json moi lane: lane/<ten>/LANE.json - sha tung quy p15, diem ghep, kiem cheo)
| lane | rep (outB/rep) | thanh vien | pred sha256 | pred md5 | xcheck |
|---|---|---|---|---|---|
| c0s42 | C0S_s42 | PROD s42 e0 | 380b5c550460d369f57ae699f5846d12bf00f0d7e7eb1578e2a21035fd58ba8e | c68fdeaa9883f2eada625d31b65f22d3 | == file PROD s42 e0 17/17 quy (max|d| 0) |
| c0s7 | C0S_s7 | PROD s7 | c8d2a2a13227d6d56bd84814f183dfa84a212f964917e35e4763f02c4e227442 | abc8c47bcc00286b7af67b783fc0fc8c | exact 17/17 |
| c0s123 | C0S_s123 | PROD s123 | e09c0fb0c4bc1f4662b50ae24db58974419021d4bd69582970cb2ded35d10fce | 7d4ce82fa4cea2948c07f8f82c63e18a | exact 17/17 |
| c0s13 | C0S_s13 | PROD s13 | 107934eaee45e20a2e1d45f27e71ad5529626084c14fe317b24a8b945cfc0cb1 | 1a817e57b9927ffff6369fd55cdd2f91 | exact 17/17 |
| e8g1 | E8S_g1 | 42,7,123,13,2024,21,777,99 | 3419493b0a2bcc50fece371989338281b5451dd952e48fc87ca35a24ad2f0ca9 | 4648f3c6da135609ed5039bd6299e148 | mean 8 tv max|d| 3.7e-9 (17 quy) |
| e8g2 | E8S_g2 | 1001..1008 | 11b5cbbb81474508197a370f5ab9a03d7a9e82d979493c414209f5664482aa87 | 7c0f4cc648e8d6e802b2e03370ce2f66 | 3.7e-9 |
| e8g3 | E8S_g3 | 1009..1016 | 87ee0ad4e44f05f98ddf507e4e3b5dfb69755b40a25731d1a7f1209187757226 | a8e9f3e7bd23f6737df4696d9d59e3d4 | 3.7e-9 |
| e8g4 | E8S_g4 | 1017..1024 | 5def079eba6efb3ef4c4add7cfa899f5ed357f46921a7b18691468b0e4390d20 | 16514cefdf8e095337a960e72b62fa54 | 3.7e-9 |
Kiem cheo lam cho CA 17 quy (khong chi 1 quy). Assert: ts tang chat, n 2 500 260, max ts 2025-12-31 23:59 UTC < 2026-01-01, khong NaN, cot risk == A1.
Diem ghep (moi lane nhu nhau): A1 cho ts < 2021-09-30 17:00 UTC (= 2021-10-01 00:00 +07; 263 520 dong, sha 39d1316d); chuoi lap 2021-09-30 17:00 -> 2025-12-31 16:59 UTC
(2 236 320 dong, ts trung khop tung phut voi A1); DUOI A1 420 dong 2025-12-31 17:00..23:59 UTC (= 2026-01-01 +07, ngoai 16 quy cham; chuoi lap ket thuc o mep fold
+07; sha 9b3ace32). Mep quy cua chuoi lap = +07 (fold p15_stab), A1 = UTC. Ghep tai 2021Q4 (+07): quy 2021Q4 dung p15 lap, chua cham.
wfo_gate_pred.csv (dataset s2-gp-<lane>): cot timestamp,predReturn15M = p15 lane tai tick 15', ts >= 2021-04-01 +07; 166 684 dong; float32 tron ven (%.9g).

## 3. Seed sim
Khong co seed sim rieng: ten r1-a3-<seed> = seed p15 (pred_ds gate-abl-seed7 / gate-sb-s123 ...), sim tat dinh (CFG khong co khoa seed). S2: 1 kernel / lane, seed = lane.

## 4. Chuoi (code/s2_chain.sh, nohup setsid; log log/s2_chain.log; tien do RUN_S2.progress; marker lane/<l>/st/*)
gp dataset (s2-gp-<l>) -> kernel s2-led-<l> -> tai ve k/led-<l> -> HEAVY (1 lane / lan, nen): ledchk (tick ledger con cua tick p15>=0.008, khong trung, ts<2026,
p15 ledger == csv) + g1lite32 -> S1 16 fold (moi fold 1 flock -w 7200 oracle_heavy.lock nice -n 10; kiem RAM >= 4000 MB, dia >= 18.5 GB, nghi khi co run_rlive)
-> a3 bins (lane/<l>/bins; A3.json: sha concat, coverage >= 0.99, multiset tung tick == RAW) -> dataset s2-a3-<l> (16 bins + pred.bin) -> xoa bins local khi dataset
ready -> kernel sim-s2-<l> (run.py r1-a3-s7, chi doi tag/a3_ds/want_a3_sha/pred_ds/want_pred_md5; SIMK.json: dong khac CFG trung, overrides trung, profile
r4_kg0_k16_f015_g155 + TOPK 24 + GATE_QUOTA_SKIP_WHEN_FULL) -> tai k/<l> -> check (CHECK.json). MAXK = 3 kernel cua chuoi cung luc (de >= 1-2 slot).
Kernel private; khong upload jar (jar = dataset co san sim-jar-tsx sha cc0f9d11, jar_sec_check ok), khong key / kaggle.json.
Loi 1 lane => lane/<l>/st/FAIL (ly do) ; lane khac chay tiep. Chay lai: `cd ~/claude_master/w3/p15_stab/s2 && setsid nohup bash code/s2_chain.sh > log/chain_main.out 2>&1 < /dev/null &`
(bo marker FAIL neu muon thu lai lane do).

## 5. Thu ket qua (pha sau)
- k/<lane>/ : output sim (result.json - CO chua so PnL, chi mo khi da qua CHECK ; storage/printDone.csv ; logs/sim.out[.gz] ; a3_funding.json ...).
- lane/<lane>/CHECK.json : kiem khong-PnL (ok, java_rc == base, jar cc0f9d11, mapper, profile_hash / profile / overrides == r1-a3-s7, pred_md5_used == LANE,
  pred_base == A1, bins a3 sha == A3.json, fold_count / leak_free / date_first / date_last == base, ton tai printDone + sim.out). PASS bat buoc truoc khi cham.
- lane/<lane>/{LANE,LEDCHK,A3,SIMK}.json ; s1/ (16 JSON) ; cand32.parquet ; log/*. Cham: ROI D5 / CAGR22 / maxDD (gvz_mtm) nhu baseline r1-a3.

## 6. Trang thai luc roi di (2026-11-24 19:16 +07)
- Dieu phoi: s2_chain.sh PID 3334713 (setsid nohup; log log/s2_chain.log ; RUN_S2.progress). Heavy hien tai: s2_heavy.sh e8g1 (log/heavy.pid).
- Code cuoi: s2_lane.py sha256 ac404a72... (sua assert simk 19:11), s2_chain.sh / s2_heavy.sh da va 2 lan (18:49 dsexist poll ; 18:50 xoa bins khi ds ready,
  heavy cho dia thay vi FAIL) - moi lan va deu kill + chay lai chuoi (idempotent, marker giu).
- 8/8 kernel ledger s2-led-<lane> complete + tai ve (c0s42: 7 051 156 dong, sha cc8813cb, LEDCHK PASS: 21 444 / 21 492 tick mo, p15 ledger == csv).
- c0s42: S1 16/16 fold, A3 bins sha concat c5a0b8e6de90369e9b31e46f534805313273155ca7b9fafeab5543cab7218ff9 (coverage min 0.99949, multiset tung tick == RAW),
  dataset s2-a3-c0s42 ready, kernel sim-s2-c0s42 RUNNING (push 19:13). SIMK: dong ngoai CFG trung template, overrides trung, chi doi 5 khoa CFG.
- e8g1: heavy dang chay (S1 11/16). 6 lane con lai: ledger da tai, cho heavy (tuan tu).
- Uoc luong: heavy ~20 ph / lane (S1 ~16 x 30-60 s + a3 ~4 ph + ledchk) => heavy xong ~21:40 ; sim ~37 ph / kernel (r1-a3-s7 secs 2192), <= 3 song song
  => toan bo ~22:30 +07 (de dem toi 23:30).
- Dia: s2/ 2.0 GB luc nay (ledger tai ve 211 MB / lane, xoa sau ledchk ; cand32 ~ 200 MB / lane giu lai ; bins 0.9 GB / lane xoa khi dataset ready) => dinh ~3-4 GB,
  cuoi ~2.5-3 GB ; dia trong hien 21 GB (guard 18.5 GB truoc heavy).

## 7. Sai lech / ghi chu so voi prereg / MASTER_NOTE
- Ghep A1 truoc 2021-10-01 +07 va 420 dong cuoi (2025-12-31 17:00-23:59 UTC) => S1 fold dau (cut 20220101) train tren pool tu p15 A1 (2021Q2-Q3) + p15 lap (2021Q4):
  chung cho moi lane o phan A1. Mep quy chuoi lap +07, A1 UTC (lech 7 h o mep 2021-10-01).
- Pool S1 DUNG LAI theo p15 lane (khac tien le r1-a3-<seed> dung chung bins). net015 RAW (g015x26) giu nguyen = WFO baseline.
- Nhan ledger tren Kaggle doc file nhan 202[1-6] (nhu rt-ledger-dev); chi tick p15 < 2026 vao ledger; cua so nhan 72 h cua tick cuoi thang 12/2025 nhin sang 2026
  (giong baseline cand_dev_x1; S1 train chi dung dong < cut - 72 h, cut <= 20251001).
- x1_s1_save_model tra rc 3 (lech ref pred_s1a2x1 - binh thuong khi model moi; k0 cung rc 3 nhung JSON trung byte). Chap nhan rc 0/3 khi co JSON.
- G_FULL cua a3_build = False la du kien (so voi pool cu) - chi thong tin; kiem dung: multiset tung tick + coverage.
- C0-PROD 4 seed (42,7,123,13) la thanh vien cua E8 nhom 1 (audit da neu) - khong so cap e8g1 vs c0s*.
- Khong co seed sim (sim tat dinh); 1 kernel / lane.

## 8. Rui ro
- Kaggle quota / hang doi: MAXK 3 cua chuoi; neu tai khoan co kernel khac chay, push co the loi => lane FAIL "sim push" (xoa marker FAIL la chay lai).
- Oracle RAM: S1 fit ~ vai GB; guard RAM 4000 MB + flock; R-LIVE (run_rlive) => heavy tam dung.
- Kernel sim loi (A3_FAIL / PRED mismatch) => FAIL, xem k/<lane>/*.log ; dataset va sha da ghi.
- Neu sim java_rc khac base (base java_rc = 1, ok = True) => CHECK FAIL de nguoi xem.

## 9. Sua loi 19:46-20:12 (errata, theo yeu cau MASTER)
- Loi: sim-s2-c0s42 (19:32) va sim-s2-e8g1 (19:50) status error. Log kernel (chi file .log): A3 sha OK, PRED_MD5_USED dung lane, roi
  "SYMBOL_MAPPER_PREFLIGHT_FAIL: khong toi duoc Aerospike Oracle 161.118.212.3:3222" (template r1-a3-s7 doc mapper qua Aerospike; cong 3222 da dong
  tu HO5 ADD1) => PLUMBING, sim chua chay, khong ghi gi; du lieu lane khong lien quan.
- Sua toi thieu: template sim = ~/claude_master/w3/ho5/kern/ho5-a3-rep4-s123 (= r1-a3-s123 + snapshot mapper 5c436e65 / overlay 6143fa75 + funding
  fb024c40 / overlay 207e7c60; da tai lap r1-a3-s123 DEV trung byte printDone: RESULT_HO5_A3_2026.md:20, HO5_A3_2026.md:163). Van chi doi 5 khoa CFG;
  assert overrides + profile == r1-a3-s7; datasets: bo r1-a3-bins + gate-sb-s123, them s2-a3-<lane> (+ ho5-a3-mapper-snap, ho5-a3-funding-snap cua template).
  CHECK.json them: overrides/profile_hash == r1-a3-s7, snapshot mapper/funding sha == rep4. Base so java_rc/date = ho5-a3-rep4-s123/result.json.
- c0s42, e8g1 push lai 20:07 -> running qua moc preflight (>3 ph). s2_lane.py cu: log/s2_lane.py.bak_1946.
- Dia: 2 x 4.2 GB a3_ds/funding.bin trong output kernel loi (kernel thoat truoc buoc don) + bins/S1/cand32 cua lane da upload. Da xoa (chi file S2 tao).
  Truoc 12.9-13 GB trong (19:58-20:04) -> sau 22 GB. Chinh sach moi (code/s2_chain_v2.sh, s2_heavy_v2.sh): xoa bins + S1 + cand32 khi dataset s2-a3 ready;
  xoa k/<l>/a3_ds/funding.bin + a3_bins sau khi tai output; khong bat dau heavy khi dia < 18 GB hoac co run_rlive (cho, ghi log); heavy tu cho dia >= 18 GB;
  cooldown 180 s sau moi lane heavy (lock oracle_heavy da nha theo tung fold S1 / tung buoc).
- Dieu phoi hien tai: s2_chain_v2.sh PID 3360754 (chain cu 3334713 da kill; heavy c0s7 bash cu kill, chay lai bang v2 - marker giu buoc da xong).

## 10. Sua loi 25/11 (agent RUN, 07:45-08:30 +07)
- (1) CHECK FAIL c0s42/c0s7/e8g1/e8g2 = loi PHEP KIEM: check() tim logs/sim.out, nhung template ho5 gzip log (ho5 kern: `subprocess.call(["gzip","-f",LOGP])`)
  -> file that la k/<l>/logs/sim.out.gz (~100 KB, ~5 000 dong). Sua s2_lane.py check(): doc .gz hoac plain (tien le rt_lchk.py:16) + ham _simlog chi DEM dong
  (khong tra noi dung): gzip -t ok, 0 dong Exception/SEVERE/FATAL, so dong "done:" == base ho5-a3-rep4-s123 (1644), so dong GATE-RATIO == base (3),
  "Loaded Symbol Mapper" == 1. Them vao must. Chay lai: 4/4 PASS (khong truong False). FAIL cu -> log/FAIL_check_*.old; dat check.done. Backup log/s2_lane.py.bak_0755.
- (2) "a3 dataset create" FAIL = QUOTA private dataset Kaggle: log/kaggle_<l>.log "The size of your files is 925.988 MB, it exceeds the 317.651 MB of
  remaining private quota" (quota tinh dung luong GIAI NEN 926 MB/ds a3, list hien 235 MB nen). kaggle CLI 1.6.17 khong co lenh delete ->
  code/s2_dsdel.py (KaggleApi auth trong bo nho, POST api.kaggle.com/v1/datasets.DatasetApiService/DeleteDataset; assert slug bat dau s2-gp-/s2-a3-).
  Da XOA: s2-a3-c0s42, s2-a3-c0s7, s2-a3-e8g1, s2-a3-e8g2 (lane da sim_dl + check PASS; sha bins o lane/<l>/A3.json, LANE.json). Khong xoa ds nao khac
  (s2-gp-* giu, 1 MB). Tai tao neu can: khong con bins local (da xoa theo chinh sach dia) -> phai dung lai heavy.
  s2_chain_v2.sh buoc 5: idempotent (ds da ton tai -> a3_up) ; loi quota -> retry vong sau (<= 20 lan, dem lane/<l>/st/quota_n) thay vi FAIL.
  Backup log/s2_chain_v2.sh.bak_0810.
- (3) Bo FAIL 4 lane c0s123 e8g3 c0s13 e8g4 (-> log/FAIL_a3ds_*.old). Bins con nguyen (a3.done) -> khong dung lai heavy.
  Chuoi: `MAXK=3 setsid nohup bash code/s2_chain_v2.sh c0s123 e8g3 c0s13 e8g4` PID 3544812 (log/chain_main_v3.out, log/s2_chain.log).
  s2-a3-c0s123 uploaded 07:52, s2-a3-e8g3 07:54, roi c0s13, e8g4.
- LUU Y QUOTA: 4 ds a3 moi = 3.7 GB ~ het quota lai. Lane P15/S3 sau can xoa s2-a3-* cua lane da xong bang code/s2_dsdel.py truoc khi tao ds moi.

## 11. Trang thai luc roi di 25/11 + thu ket qua (pha cham)
- c0s42, c0s7, e8g1, e8g2: sim_dl + check.done (PASS). c0s123, e8g3, c0s13, e8g4: xem RUN_S2.progress (muc nay viet luc 07:58; cap nhat cuoi o progress).
- Uoc: 3 sim song song push ~08:00 (~35-40 ph/kernel) -> xong ~08:40; e8g4 push khi co slot ~08:40 -> xong ~09:20; check -> du 8 lane ~09:30 +07
  (de dem 10:30). Chuoi tu END khi 4 lane check.done/FAIL ("chain END" trong RUN_S2.progress).
- Output sim (template ho5) o k/<lane>/: result.json (khoa TIEN: equity_start, equity_final, b_final, n_trades; khoa khong tien: ok, java_rc, date_*,
  profile*, overrides, pred_md5_*, r1_a3, ho5_*), storage/printDone.csv (giao dich), storage/BalanceIndex.data, OrderTestDone.data, logs/sim.out.gz
  (log java, co dong "done:"/"Update YYYYMMDD 07:00 =>" chua so du), logs/full.log, logs/error.log (rong), config.properties, prof_run.properties,
  sim-s2-<lane>.log (log kernel - CO dong "RESULT {...}" va SIM_DONE equity => cung la PnL). Base so sanh: ~/claude_master/w3/ho5/out/ho5-a3-rep4-s123/.
- Agent RUN 25/11 KHONG mo bat ky so PnL nao (chi liet ke ten khoa result.json, dem dong log).
- 08:06: sim-s2-c0s123/e8g3/c0s13 running (push 08:00), e8g4 a3_up cho slot. Chain PID 3544812. Dia trong 22.9 GB.
