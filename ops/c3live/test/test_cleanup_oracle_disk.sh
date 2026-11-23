#!/usr/bin/env bash
# test_cleanup_oracle_disk.sh — test GIA (sandbox CLEAN_H) cho cleanup_oracle_disk.sh v2: dich moi 1b(r4u thua)/1d/1e/1f + fail-closed.
#   bash ops/c3live/test/test_cleanup_oracle_disk.sh /tmp/t_cl
HERE=$(cd "$(dirname "$0")/.." && pwd); S=$HERE/cleanup_oracle_disk.sh
W=${1:?thu muc tam}; rm -rf "$W"; mkdir -p "$W"; H=$W/h; CM=$H/claude_master
PASS=0; FAILN=0
chk() { if eval "$2"; then PASS=$((PASS+1)); echo "  [PASS] $1"; else FAILN=$((FAILN+1)); echo "  [FAIL] $1"; fi; }
G() { git -c user.name=t -c user.email=t@l "$@" >/dev/null 2>&1; }
mk() {
  rm -rf "$H"; mkdir -p $CM/deploy $CM/locks $CM/v12/jar $CM/parity_v12w $CM/parity_v11w/d $H/ops
  echo '[{"md5":"694b29b2e5be32b537ca6c38557e64db"},{"md5":"8c81e6b560b61e7d43ca32c4a50ec926"}]' > $CM/parity_v12w/jars.json
  for t in r4t r4u3 r4u r4u_final r4u2 r4j; do head -c 2048 /dev/urandom > $CM/v12/jar/binance-java-sdk-1.2.4.jar_v12_$t; done
  touch -d '2026-10-20' $CM/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4j
  MF=$(md5sum < $CM/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4u_final | cut -c1-32)
  MU2=$(md5sum < $CM/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4u2 | cut -c1-32)
  # c3live = repo goc (CAM DUNG); md5 r4u_final nam trong 1 script => phai GIU; md5 r4u2 chi nam trong 1 LOG => van XOA
  mkdir -p $CM/v12/c3live/ops; cd $CM/v12/c3live && G init -q -b main && echo a > a && echo target/ > .gitignore && G add a .gitignore && G commit -qm a
  echo "PIN=$MF" > $CM/v12/c3live/ops/pin_x.sh; echo "jar $MU2 da chay" > $CM/deploy/old_run.log
  G -C $CM/v12/c3live worktree add --detach $CM/v12/wt_r4u main
  G -C $CM/v12/c3live worktree add --detach $CM/v12/wt_r4u_final main; echo secret > $CM/v12/wt_r4u_final/PrivateConfig
  G -C $CM/v12/c3live worktree add --detach $CM/v12/wt_r4u2 main; (cd $CM/v12/wt_r4u2 && echo z > z && G add z && G commit -qm mo_coi)
  G -C $CM/v12/c3live worktree add --detach $CM/v12/wt_r4u3 main
  mkdir -p $CM/v12/wt_r4u/target; head -c 4096 /dev/urandom > $CM/v12/wt_r4u/target/x.jar
  for n in a1r4s_fake a1pq_gates a1r4n_fake a1sw_log; do mkdir -p $CM/v12/$n; echo x > $CM/v12/$n/f; done
  touch -d '2026-11-06 10:00' $CM/v12/a1r4s_fake/f $CM/v12/a1pq_gates/f; touch -d '2026-11-02' $CM/v12/a1r4n_fake/f
  for p in parity_v11w parity_v12w; do
    D=$CM/$p/d/2026-11-01; mkdir -p $D/work $D/runs $D/live
    for f in work/closes_cache.pkl runs/holes.csv runs/fund_NEW2.csv.gz work/s1v_rows.csv.gz runs/fund_BT.csv.gz live/feat45_live.csv.gz \
             work/join_fund.csv.gz work/net_live_all.csv.gz work/kprime_20261101.json report_daily.txt run_day.log; do head -c 1000 /dev/urandom > $D/$f; done
    echo done > $D/WATCH_DONE; touch -d '2026-11-02' $D/WATCH_DONE
    R=$CM/$p/d/$(date +%F); mkdir -p $R/work; echo x > $R/work/closes_cache.pkl; echo done > $R/DONE
    N=$CM/$p/d/2026-10-30; mkdir -p $N/work; echo x > $N/work/closes_cache.pkl
  done
  mkdir -p $W/outside; echo bimat > $W/outside/holes.csv; ln -s $W/outside/holes.csv $CM/parity_v11w/d/2026-11-01/work/holes.csv
  mkdir -p $CM/v12/a1x_adv $CM/v12/a1y_drylog; echo x > $CM/v12/a1x_adv/f; echo x > $CM/v12/a1y_drylog/f; touch -d '2026-11-06' $CM/v12/a1x_adv/f $CM/v12/a1y_drylog/f
  # [v4 g] target/: WHITELIST (v12/a1, v12/a1_*, ing1030/a1_wt*, wt_r4u*) — ngoai whitelist KHONG BAO GIO xoa
  mtg() { mkdir -p "$1/classes" "$1/maven-status"; head -c 3000 /dev/urandom > "$1/classes/A.class"; }
  mtg $CM/v12/a1_r4i/target                                                        # whitelist, khong ai dung => XOA
  mtg $CM/v12/a1_r4j/target; mkdir -p $CM/tools_x; echo "java -cp \$CM/v12/a1_r4j/target/classes X" > $CM/tools_x/run.sh   # co script tham chieu => GIU
  mtg $CM/v12/a1_soak/target                                                       # process mo file => GIU
  mtg $CM/ing1030/a1_wt3/target; head -c 5000 /dev/urandom > $CM/ing1030/a1_wt3/target/app.jar
  echo "PIN2=$(md5sum < $CM/ing1030/a1_wt3/target/app.jar | cut -c1-32)" > $CM/v12/c3live/ops/pin_y.sh   # jar tham chieu, khong co ban trong v12/jar => GIU
  mtg $CM/ing1030/a1_wt2/target; cp $CM/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4t $CM/ing1030/a1_wt2/target/app.jar   # tham chieu nhung co ban r4t => XOA
  echo "PIN3=$(md5sum < $CM/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4t | cut -c1-32)" >> $CM/v12/c3live/ops/pin_y.sh
  mkdir -p $CM/v12/a1_pq/target/d; echo du_lieu > $CM/v12/a1_pq/target/d/x.csv    # whitelist nhung 'target' khong phai build => GIU
  # A1 MAJ: ngoai whitelist => GIU du khong ai tham chieu
  mtg $CM/v12/wt_t2c/target; mkdir -p $CM/v12/wt_t2c/target/test-classes; echo c > $CM/v12/wt_t2c/target/test-classes/ExitReplayDevMain.class
  mtg $H/src_wt_bcd/target; head -c 4000 /dev/urandom > $H/src_wt_bcd/target/binance-java-sdk-1.2.4.jar
  mtg $CM/v12/old_wt/target; mtg $H/shadow_c3/app/target; mtg $CM/v12/wt_r4u3/target; mtg $CM/r3_wt/target; mtg $CM/res1109/r1/target
  # [v5 i] ban sao nghien cuu res1109
  RS=$CM/res1109; mkdir -p $RS/r1_s1/a2_bins $RS/r1_s1/kl $RS/r3_gate/jar_q $RS/r3_gate/pred $RS/r3_gate/orch_m2r/ds_sim-jar-r3x $RS/r5_quality $RS/r4u $CM/1004/gqd
  head -c 7000 /dev/urandom > $RS/r1_s1/a2_bins/predict_wf_1.bin; echo '{}' > $RS/r1_s1/a2_bins/a2_report.json; echo '{}' > $RS/r1_s1/a2_bins/dataset-metadata.json
  head -c 5000 /dev/urandom > $RS/r1_s1/kl/kline1m-2022-01.parquet; echo 'export KEY_X=1' > $RS/r1_s1/r1_env242.sh
  head -c 6000 /dev/urandom > $RS/r3_gate/jar_q/sim.jar; echo t > $RS/r3_gate/jar_q/sha.txt
  head -c 6000 /dev/urandom > $RS/r3_gate/pred/pred_s1.bin; echo "x=\$R/res1109/r3_gate/pred/pred_s1.bin" > $CM/tools_x/use_pred.py   # pred co script tham chieu => GIU
  head -c 6000 /dev/urandom > $RS/r3_gate/orch_m2r/ds_sim-jar-r3x/sim.jar; echo '{}' > $RS/r3_gate/orch_m2r/ds_sim-jar-r3x/dataset-metadata.json; echo '{}' > $RS/r3_gate/orch_m2r/loop_state.json
  head -c 6000 /dev/urandom > $RS/r5_quality/sig_S1.npz; echo '{}' > $RS/r5_quality/confirm.json; head -c 6000 /dev/urandom > $RS/r5_quality/other.npz
  echo b > $RS/r4u/build_r4u.log; head -c 3000 /dev/urandom > $CM/1004/gqd/cand_base.npz
  # [v3 h] log shadow
  mkdir -p $H/shadow_c3/app/logs $H/shadow_c3/app/storage/data $H/shadow_c3b/app/logs
  echo cu > $H/shadow_c3/app/logs/full.log.1; touch -d '2026-10-20' $H/shadow_c3/app/logs/full.log.1
  echo moi > $H/shadow_c3/app/logs/full.log; echo d > $H/shadow_c3/app/storage/data/x.dat; touch -d '2026-10-01' $H/shadow_c3/app/storage/data/x.dat
  echo j > $H/shadow_c3/app/logs/old.jar; touch -d '2026-10-01' $H/shadow_c3/app/logs/old.jar
  echo cu > $H/shadow_c3b/app/logs/b.log; touch -d '2026-10-25' $H/shadow_c3b/app/logs/b.log
  cd "$W"
}
jar() { [ -f $CM/v12/jar/binance-java-sdk-1.2.4.jar_v12_$1 ]; }
P11=$CM/parity_v11w/d/2026-11-01
echo "== cleanup_oracle_disk v4 (sandbox)"
mk
bash -c "exec 3<$CM/v12/a1_soak/target/classes/A.class; exec sleep 120" & BUSY=$!; sleep 0.5
OUT=$(CLEAN_H=$H bash $S 2>&1); RC=$?
chk "DRY: rc0, khong xoa gi, ke hoach co 1b/1d/1e/1f/1g/1h + goi y journalctl (chi in)" "[ $RC = 0 ] && jar r4u && jar r4u2 && [ -d $CM/v12/wt_r4u ] && [ -f $P11/work/closes_cache.pkl ] && [ -d $CM/v12/a1r4s_fake ] && [ -d $CM/v12/old_wt/target ] && [ -f $H/shadow_c3/app/logs/full.log.1 ] && echo \"\$OUT\" | grep -q 'SE xoa binance-java-sdk-1.2.4.jar_v12_r4u2' && echo \"\$OUT\" | grep -q 'SE git worktree remove v12/wt_r4u ' && echo \"\$OUT\" | grep -q 'SE xoa a1r4s_fake' && echo \"\$OUT\" | grep -q 'SE xoa parity_v11w/d/2026-11-01: 2 file' && echo \"\$OUT\" | grep -q 'SE xoa claude_master/v12/a1_r4i/target' && echo \"\$OUT\" | grep -q 'sudo journalctl --vacuum-size=200M'"
OUT=$(CLEAN_H=$H bash $S --apply 2>&1); RC=$?
kill $BUSY 2>/dev/null
echo "$OUT" | grep -E 'ABORT|PHA 1:' | head -3
chk "1g whitelist: XOA a1_r4i/target (khong ai dung), a1_wt2/target (jar tham chieu nhung co ban v12/jar); GIU a1_r4j (script tham chieu), a1_soak (process mo file), a1_wt3 (jar tham chieu khong co ban), a1_pq ('target' du lieu)" "[ $RC = 0 ] && [ ! -d $CM/v12/a1_r4i/target ] && [ ! -d $CM/ing1030/a1_wt2/target ] && [ -d $CM/v12/a1_r4j/target ] && [ -d $CM/v12/a1_soak/target ] && [ -f $CM/ing1030/a1_wt3/target/app.jar ] && [ -f $CM/v12/a1_pq/target/d/x.csv ] && echo \"\$OUT\" | grep -q 'co script/crontab tham chieu' && echo \"\$OUT\" | grep -q 'process dang dung file' && echo \"\$OUT\" | grep -q 'KHONG co ban trong v12/jar'"
chk "1g A1 MAJ: ngoai whitelist GIU nguyen: wt_t2c/target (test-classes ExitReplayDevMain), src_wt_bcd/target (sim.jar), old_wt, shadow_c3, wt_r4u3, r3_wt, res1109" "[ -f $CM/v12/wt_t2c/target/test-classes/ExitReplayDevMain.class ] && [ -f $H/src_wt_bcd/target/binance-java-sdk-1.2.4.jar ] && [ -d $CM/v12/old_wt/target ] && [ -d $H/shadow_c3/app/target ] && [ -d $CM/v12/wt_r4u3/target ] && [ -d $CM/r3_wt/target ] && [ -d $CM/res1109/r1/target ]"
RS=$CM/res1109
chk "1i: XOA .bin a2_bins, .jar jar_q + ds_sim-jar-*, sig_*.npz; GIU json/txt/metadata, pred (script tham chieu), kl, r1_env242.sh, r4u log, other.npz, 1004 cand_base.npz, loop_state.json" "[ ! -f $RS/r1_s1/a2_bins/predict_wf_1.bin ] && [ -f $RS/r1_s1/a2_bins/a2_report.json ] && [ -f $RS/r1_s1/a2_bins/dataset-metadata.json ] && [ ! -f $RS/r3_gate/jar_q/sim.jar ] && [ -f $RS/r3_gate/jar_q/sha.txt ] && [ ! -f $RS/r3_gate/orch_m2r/ds_sim-jar-r3x/sim.jar ] && [ -f $RS/r3_gate/orch_m2r/ds_sim-jar-r3x/dataset-metadata.json ] && [ -f $RS/r3_gate/orch_m2r/loop_state.json ] && [ ! -f $RS/r5_quality/sig_S1.npz ] && [ -f $RS/r5_quality/other.npz ] && [ -f $RS/r5_quality/confirm.json ] && [ -f $RS/r3_gate/pred/pred_s1.bin ] && [ -f $RS/r1_s1/kl/kline1m-2022-01.parquet ] && [ -f $RS/r1_s1/r1_env242.sh ] && [ -f $RS/r4u/build_r4u.log ] && [ -f $CM/1004/gqd/cand_base.npz ] && echo \"\$OUT\" | grep -q \"tham chieu 'res1109/r3_gate/pred'\""
chk "1h: XOA log shadow_c3/shadow_c3b > 7 ngay; GIU log moi, storage/data, jar" "[ ! -f $H/shadow_c3/app/logs/full.log.1 ] && [ ! -f $H/shadow_c3b/app/logs/b.log ] && [ -f $H/shadow_c3/app/logs/full.log ] && [ -f $H/shadow_c3/app/storage/data/x.dat ] && [ -f $H/shadow_c3/app/logs/old.jar ]"
chk "1e A1 MIN-1: GIU bang chung a1x_adv, a1y_drylog (du 11-06, > 24 h)" "[ -d $CM/v12/a1x_adv ] && [ -d $CM/v12/a1y_drylog ]"
chk "1b: XOA jar r4u + r4u2 (md5 r4u2 chi o LOG); GIU r4u_final (md5 trong script), r4u3, r4t" "[ $RC = 0 ] && ! jar r4u && ! jar r4u2 && jar r4u_final && jar r4u3 && jar r4t && echo \"\$OUT\" | grep -q 'GIU (r4u thua nhung md5'"
chk "1b: jar cu khac van theo luat cu (r4j cu 20 ngay, md5 khong ai tro => xoa)" "! jar r4j"
chk "1d: wt_r4u sach => git worktree remove (ca target/); wt_r4u_final chi PrivateConfig => --force; wt_r4u3 GIU" "[ ! -d $CM/v12/wt_r4u ] && [ ! -d $CM/v12/wt_r4u_final ] && [ -d $CM/v12/wt_r4u3 ] && echo \"\$OUT\" | grep -q 'DA worktree remove --force v12/wt_r4u_final'"
chk "1d: wt_r4u2 commit khong thuoc nhanh nao => BO QUA (khong mat lich su)" "[ -d $CM/v12/wt_r4u2 ] && echo \"\$OUT\" | grep -q 'khong thuoc nhanh nao'"
chk "1e: XOA a1r4s_fake (11-06, >24 h); GIU a1pq_gates (ten), a1r4n_fake (truoc 11-05), a1sw_log (file < 24 h)" "[ ! -d $CM/v12/a1r4s_fake ] && [ -d $CM/v12/a1pq_gates ] && [ -d $CM/v12/a1r4n_fake ] && [ -d $CM/v12/a1sw_log ]"
pf_ok() { local p D; for p in parity_v11w parity_v12w; do D=$CM/$p/d/2026-11-01
  [ ! -f $D/work/closes_cache.pkl ] && [ ! -f $D/runs/holes.csv ] && [ -f $D/runs/fund_NEW2.csv.gz ] && [ -f $D/work/s1v_rows.csv.gz ] \
  && [ -f $D/runs/fund_BT.csv.gz ] && [ -f $D/live/feat45_live.csv.gz ] && [ -f $D/work/join_fund.csv.gz ] && [ -f $D/work/net_live_all.csv.gz ] \
  && [ -f $D/work/kprime_20261101.json ] && [ -f $D/report_daily.txt ] && [ -f $D/run_day.log ] && [ -f $D/WATCH_DONE ] || return 1; done; }
chk "1f: ngay DONE > 3 ngay: XOA closes_cache/holes (ca 2 parity); GIU fund_NEW2 (A1 MIN-2), s1v_rows, fund_BT, feat45, join_fund, net_live_all, kprime, day_report, run_day.log, WATCH_DONE" "pf_ok"
chk "1f: ngay hom nay (DONE < 3 ngay) va ngay chua DONE => GIU; symlink holes.csv tro ra ngoai => khong theo, file ngoai con" "[ -f $CM/parity_v11w/d/$(date +%F)/work/closes_cache.pkl ] && [ -f $CM/parity_v11w/d/2026-10-30/work/closes_cache.pkl ] && grep -qx bimat $W/outside/holes.csv"
# fail-closed: CAM DUNG van ap dung (1d tro vao duong dan bi cam qua symlink)
mk; rm -rf $CM/v12/wt_r4u; mkdir -p $H/vz_e1/raw; ln -s $H/vz_e1/raw $CM/v12/wt_r4u
OUT=$(CLEAN_H=$H bash $S --apply 2>&1); RC=$?
echo "$OUT" | grep 'ABORT' | head -2
chk "fail-closed: wt_r4u la symlink vao vz_e1 (ngoai claude_master / CAM DUNG) => ABORT, vz_e1 nguyen ven" "[ $RC != 0 ] && echo \"\$OUT\" | grep -q 'ABORT: .*vz_e1' && [ -d $H/vz_e1/raw ]"
mk; rm -rf $CM/v12/wt_r4u; mkdir -p $CM/res1109/kl; ln -s $CM/res1109 $CM/v12/wt_r4u
OUT=$(CLEAN_H=$H bash $S --apply 2>&1); RC=$?
chk "fail-closed: wt_r4u la symlink vao res1109 (CAM DUNG trong claude_master) => ABORT CAM DUNG, res1109 nguyen ven" "[ $RC != 0 ] && echo \"\$OUT\" | grep -q 'ABORT: CAM DUNG' && [ -d $CM/res1109/kl ]"
mk; mkdir -p $CM/zz; echo x > $CM/zz/bad.sh; chmod 000 $CM/zz/bad.sh
OUT=$(CLEAN_H=$H bash $S --apply 2>&1); RC=$?; chmod 644 $CM/zz/bad.sh
chk "fail-closed: grep tham chieu khong doc duoc 1 file *.sh => ABORT truoc khi xoa target whitelist" "[ $RC != 0 ] && echo \"\$OUT\" | grep -q 'grep tham chieu loi' && [ -d $CM/v12/a1_r4i/target ]"
mk; mkdir -p $CM/parity_v12w/d/2026-11-01/work/cache; echo x > $CM/parity_v12w/d/2026-11-01/work/cache/feat45_live.csv.gz
OUT=$(CLEAN_H=$H bash $S --apply 2>&1); RC=$?
chk "1f chi 3 ten: 'cache/' va feat45 trong cache khong bi dung" "[ $RC = 0 ] && [ -f $CM/parity_v12w/d/2026-11-01/work/cache/feat45_live.csv.gz ]"
# ======================================================================= [v6] PHA 2: nen lossless whitelist cung (sandbox)
XA=$CM/audit_1030b; XN=$H/net015_repro; XK=$H/kg015x26_2021; ARCH=$CM/archive
mk2() {   # sandbox v5 + 3 muc whitelist pha 2 (cu, khong git, khong tham chieu); kich thuoc K < N < A
  mk
  mkdir -p $XA/head/src $XN $XK/g/sub
  for i in 1 2 3; do head -c 20000 /dev/zero > $XA/head/src/f$i.txt; done; echo 'class A {}' > $XA/head/src/A.java
  head -c 30000 /dev/urandom > $XN/predict.bin; echo log > $XN/reproA.log; : > $XN/mon.out
  seq 1 2000 > $XK/g/sub/d.csv; echo x > "$XK/g/ten co dau cach.txt"; ln -s sub/d.csv $XK/g/link
  find $XA $XN $XK -exec touch -h -d '2026-10-20 12:00' {} +
  rm -rf $W/ref; mkdir -p $W/ref; cp -a $XA $XN $XK $W/ref/
}
arc_ok() { [ -f $ARCH/$1.tar.zst ] && [ -f $ARCH/$1.tar.zst.sha256 ] && [ -f $ARCH/$1.manifest.tsv ] && [ ! -e $ARCH/$1.tar.zst.part ]; }
no_arc() { [ ! -e $ARCH/$1.tar.zst ] && [ ! -e $ARCH/$1.tar.zst.part ] && [ ! -e $ARCH/$1.tar.zst.part.manifest ] && [ ! -e $ARCH/$1.tar.zst.part.sha256 ]; }
lossless() {   # sha256 -c, giai nen ra thu muc tam, so sanh tung byte + symlink voi ban chep truoc khi nen
  local n=$1 x=$W/x_$1; rm -rf $x; mkdir -p $x
  (cd $ARCH && sha256sum -c --quiet $n.tar.zst.sha256) || return 1
  zstd -q -dc $ARCH/$n.tar.zst | tar -C $x -xf - || return 1
  diff -r --no-dereference $W/ref/$n $x/$n >/dev/null || return 1
  [ "$(wc -l < $ARCH/$n.manifest.tsv)" = "$(find $W/ref/$n -type f | wc -l)" ]
}
run2() { OUT=$(CLEAN_H=$H CLEAN_P2_MINFREE=${XMF:-0} bash $S "$@" 2>&1); RC=$?; echo "$OUT" | grep -E 'ABORT|DA nen|LECH|DUNG PHA 2' | head -4; }
echo "== [v6] pha 2 (sandbox)"
mk2; run2
chk "P2 DRY: rc0, 3 muc 'SE nen' + bang du kien, KHONG tao archive, goc nguyen" "[ $RC = 0 ] && [ -d $XA ] && [ -d $XN ] && [ -d $XK ] && [ ! -d $ARCH ] && [ \$(echo \"\$OUT\" | grep -c 'SE nen') = 3 ] && echo \"\$OUT\" | grep -q 'BANG PHA 2' && echo \"\$OUT\" | grep -q '=== PHA 2: du kien'"
run2 --apply
chk "P2 APPLY: 3 archive + .sha256 + .manifest.tsv, goc da xoa, thu tu nho -> lon (kg < net < audit)" "[ $RC = 0 ] && arc_ok audit_1030b && arc_ok net015_repro && arc_ok kg015x26_2021 && [ ! -e $XA ] && [ ! -e $XN ] && [ ! -e $XK ] && [ \"\$(echo \"\$OUT\" | grep -o 'DA nen [a-z0-9_]*' | tr '\n' ' ')\" = 'DA nen kg015x26_2021 DA nen net015_repro DA nen audit_1030b ' ]"
chk "P2 lossless: sha256 -c OK; giai nen == ban chep (diff -r, ca symlink + ten co dau cach); manifest du dong" "lossless audit_1030b && lossless net015_repro && lossless kg015x26_2021"
mkdir -p $XN; echo moi > $XN/z; touch -d '2026-10-20' $XN/z $XN
run2 --apply
chk "P2 chay lai: da nen => BO QUA (khong co); da co archive cung ten => BO QUA, goc moi giu nguyen" "[ $RC = 0 ] && [ -f $XN/z ] && echo \"\$OUT\" | grep -q 'BO QUA (da co archive/net015_repro.tar.zst' && echo \"\$OUT\" | grep -q 'BO QUA (khong co / da nen) $XA'"
mk2; mkdir -p $XN/sub/.git; echo x > $XN/sub/.git/HEAD; touch -h -d '2026-10-20' $XN/sub/.git/HEAD $XN/sub/.git $XN/sub $XN
run2 --apply
chk "P2 .git: muc co .git => ABORT (rc!=0); net015_repro nguyen, khong archive/.part; audit_1030b (sau) chua bi dung" "[ $RC != 0 ] && echo \"\$OUT\" | grep -q 'ABORT: .*net015_repro chua .git' && [ -f $XN/predict.bin ] && no_arc net015_repro && [ -d $XA ] && no_arc audit_1030b"
mk2; mkdir -p $CM/vz_e1_wt/docs/result; echo "P=~/net015_repro/predict.bin" > $H/ops/use_n.sh
echo "bash \$HOME/kg015x26_2021/g/run.sh" > $H/L2_99.sh
echo '{"src":"/x/claude_master/audit_1030b/head"}' > $CM/vz_e1_wt/docs/result/r.json
run2 --apply
chk "P2 tham chieu: ~/ops/*.sh => BO QUA net015_repro; ~/L2_99.sh (file cap 1 cua ~) => BO QUA kg015x26_2021; docs/*.json chi ghi log => audit_1030b VAN nen" "[ $RC = 0 ] && [ -f $XN/predict.bin ] && no_arc net015_repro && [ -f $XK/g/sub/d.csv ] && no_arc kg015x26_2021 && arc_ok audit_1030b && [ ! -e $XA ] && echo \"\$OUT\" | grep -q 'tham chieu: $H/ops/use_n.sh' && echo \"\$OUT\" | grep -q 'tham chieu: $H/L2_99.sh' && echo \"\$OUT\" | grep -q 'ghi chep docs (khong chan)'"
mk2; touch $XA/head/src/f2.txt
run2 --apply
chk "P2 mtime: co file moi (>= 2026-11-01) => BO QUA audit_1030b; 2 muc con lai nen" "[ $RC = 0 ] && [ -f $XA/head/src/f2.txt ] && no_arc audit_1030b && arc_ok net015_repro && arc_ok kg015x26_2021 && echo \"\$OUT\" | grep -q 'BO QUA (co muc moi >= 2026-11-01'"
mk2; ln $XK/g/sub/d.csv $XK/g/hl.csv; touch -h -d '2026-10-20' $XK/g $XK/g/hl.csv
run2 --apply
chk "P2 kiem lech (hardlink => tar 'h' => so file thuong lech): xoa .part, GIU goc kg015x26_2021; muc khac van nen; exit 1 cuoi" "[ $RC != 0 ] && [ -f $XK/g/hl.csv ] && [ -f $XK/g/sub/d.csv ] && no_arc kg015x26_2021 && arc_ok net015_repro && arc_ok audit_1030b && echo \"\$OUT\" | grep -q 'LECH:' && echo \"\$OUT\" | grep -q 'GIU NGUYEN ban goc' && echo \"\$OUT\" | grep -q 'LOI pha 2'"
mk2; bash -c "exec 3<$XN/predict.bin; exec sleep 300" & BUSY=$!; sleep 0.5
run2 --apply; kill $BUSY 2>/dev/null
chk "P2 /proc: process mo file trong net015_repro => BO QUA, giu goc; muc khac nen" "[ $RC = 0 ] && [ -f $XN/predict.bin ] && no_arc net015_repro && arc_ok kg015x26_2021 && echo \"\$OUT\" | grep -q 'BO QUA (process dang dung'"
mk2; XMF=999999999999999 run2 --apply
chk "P2 dia trong < nguong 15.3 GiB (gia lap) => DUNG pha 2 truoc muc dau, khong nen gi" "[ $RC = 0 ] && [ -d $XA ] && [ -d $XN ] && [ -d $XK ] && [ ! -d $ARCH ] && echo \"\$OUT\" | grep -q 'DUNG PHA 2: dia trong'"
mk2; rm -rf $XN; mkdir -p $H/vz_e1/raw; ln -s $H/vz_e1 $XN
run2 --apply
chk "P2 fail-closed: net015_repro la symlink (vao vz_e1) => ABORT, dich nguyen ven" "[ $RC != 0 ] && echo \"\$OUT\" | grep -q 'ABORT: pha 2: symlink' && [ -d $H/vz_e1/raw ]"
mk2; mkdir -p $H/java; echo x > $H/java/bad.sh; chmod 000 $H/java/bad.sh
run2 --apply; chmod 644 $H/java/bad.sh
chk "P2 fail-closed: grep tham chieu pha 2 khong doc duoc 1 file (~/java/bad.sh) => ABORT, khong nen gi" "[ $RC != 0 ] && echo \"\$OUT\" | grep -q 'grep tham chieu pha 2 loi' && [ -d $XA ] && [ -d $XN ] && [ -d $XK ] && no_arc kg015x26_2021"
echo "TEST $( [ $FAILN = 0 ] && echo PASS || echo FAIL ) $PASS/$((PASS+FAILN))"
[ $FAILN = 0 ]
