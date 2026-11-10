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
  cd "$W"
}
jar() { [ -f $CM/v12/jar/binance-java-sdk-1.2.4.jar_v12_$1 ]; }
P11=$CM/parity_v11w/d/2026-11-01
echo "== cleanup_oracle_disk v2 (sandbox)"
mk
OUT=$(CLEAN_H=$H bash $S 2>&1); RC=$?
chk "DRY: rc0, khong xoa gi, ke hoach co 1b/1d/1e/1f" "[ $RC = 0 ] && jar r4u && jar r4u2 && [ -d $CM/v12/wt_r4u ] && [ -f $P11/work/closes_cache.pkl ] && [ -d $CM/v12/a1r4s_fake ] && echo \"\$OUT\" | grep -q 'SE xoa binance-java-sdk-1.2.4.jar_v12_r4u2' && echo \"\$OUT\" | grep -q 'SE git worktree remove v12/wt_r4u ' && echo \"\$OUT\" | grep -q 'SE xoa a1r4s_fake' && echo \"\$OUT\" | grep -q 'SE xoa parity_v11w/d/2026-11-01: 3 file'"
OUT=$(CLEAN_H=$H bash $S --apply 2>&1); RC=$?
echo "$OUT" | grep -E 'ABORT|PHA 1:' | head -3
chk "1b: XOA jar r4u + r4u2 (md5 r4u2 chi o LOG); GIU r4u_final (md5 trong script), r4u3, r4t" "[ $RC = 0 ] && ! jar r4u && ! jar r4u2 && jar r4u_final && jar r4u3 && jar r4t && echo \"\$OUT\" | grep -q 'GIU (r4u thua nhung md5'"
chk "1b: jar cu khac van theo luat cu (r4j cu 20 ngay, md5 khong ai tro => xoa)" "! jar r4j"
chk "1d: wt_r4u sach => git worktree remove (ca target/); wt_r4u_final chi PrivateConfig => --force; wt_r4u3 GIU" "[ ! -d $CM/v12/wt_r4u ] && [ ! -d $CM/v12/wt_r4u_final ] && [ -d $CM/v12/wt_r4u3 ] && echo \"\$OUT\" | grep -q 'DA worktree remove --force v12/wt_r4u_final'"
chk "1d: wt_r4u2 commit khong thuoc nhanh nao => BO QUA (khong mat lich su)" "[ -d $CM/v12/wt_r4u2 ] && echo \"\$OUT\" | grep -q 'khong thuoc nhanh nao'"
chk "1e: XOA a1r4s_fake (11-06, >24 h); GIU a1pq_gates (ten), a1r4n_fake (truoc 11-05), a1sw_log (file < 24 h)" "[ ! -d $CM/v12/a1r4s_fake ] && [ -d $CM/v12/a1pq_gates ] && [ -d $CM/v12/a1r4n_fake ] && [ -d $CM/v12/a1sw_log ]"
pf_ok() { local p D; for p in parity_v11w parity_v12w; do D=$CM/$p/d/2026-11-01
  [ ! -f $D/work/closes_cache.pkl ] && [ ! -f $D/runs/holes.csv ] && [ ! -f $D/runs/fund_NEW2.csv.gz ] && [ -f $D/work/s1v_rows.csv.gz ] \
  && [ -f $D/runs/fund_BT.csv.gz ] && [ -f $D/live/feat45_live.csv.gz ] && [ -f $D/work/join_fund.csv.gz ] && [ -f $D/work/net_live_all.csv.gz ] \
  && [ -f $D/work/kprime_20261101.json ] && [ -f $D/report_daily.txt ] && [ -f $D/run_day.log ] && [ -f $D/WATCH_DONE ] || return 1; done; }
chk "1f: ngay DONE > 3 ngay: XOA closes_cache/holes/fund_NEW2 (ca 2 parity); GIU s1v_rows, fund_BT, feat45, join_fund, net_live_all, kprime, day_report, run_day.log, WATCH_DONE" "pf_ok"
chk "1f: ngay hom nay (DONE < 3 ngay) va ngay chua DONE => GIU; symlink holes.csv tro ra ngoai => khong theo, file ngoai con" "[ -f $CM/parity_v11w/d/$(date +%F)/work/closes_cache.pkl ] && [ -f $CM/parity_v11w/d/2026-10-30/work/closes_cache.pkl ] && grep -qx bimat $W/outside/holes.csv"
# fail-closed: CAM DUNG van ap dung (1d tro vao duong dan bi cam qua symlink)
mk; rm -rf $CM/v12/wt_r4u; mkdir -p $H/vz_e1/raw; ln -s $H/vz_e1/raw $CM/v12/wt_r4u
OUT=$(CLEAN_H=$H bash $S --apply 2>&1); RC=$?
echo "$OUT" | grep 'ABORT' | head -2
chk "fail-closed: wt_r4u la symlink vao vz_e1 (ngoai claude_master / CAM DUNG) => ABORT, vz_e1 nguyen ven" "[ $RC != 0 ] && echo \"\$OUT\" | grep -q 'ABORT: .*vz_e1' && [ -d $H/vz_e1/raw ]"
mk; rm -rf $CM/v12/wt_r4u; mkdir -p $CM/res1109/kl; ln -s $CM/res1109 $CM/v12/wt_r4u
OUT=$(CLEAN_H=$H bash $S --apply 2>&1); RC=$?
chk "fail-closed: wt_r4u la symlink vao res1109 (CAM DUNG trong claude_master) => ABORT CAM DUNG, res1109 nguyen ven" "[ $RC != 0 ] && echo \"\$OUT\" | grep -q 'ABORT: CAM DUNG' && [ -d $CM/res1109/kl ]"
mk; mkdir -p $CM/parity_v12w/d/2026-11-01/work/cache; echo x > $CM/parity_v12w/d/2026-11-01/work/cache/feat45_live.csv.gz
OUT=$(CLEAN_H=$H bash $S --apply 2>&1); RC=$?
chk "1f chi 3 ten: 'cache/' va feat45 trong cache khong bi dung" "[ $RC = 0 ] && [ -f $CM/parity_v12w/d/2026-11-01/work/cache/feat45_live.csv.gz ]"
echo "TEST $( [ $FAILN = 0 ] && echo PASS || echo FAIL ) $PASS/$((PASS+FAILN))"
[ $FAILN = 0 ]
