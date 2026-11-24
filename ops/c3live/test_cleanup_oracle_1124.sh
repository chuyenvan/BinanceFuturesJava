#!/usr/bin/env bash
# test_cleanup_oracle_1124.sh - test SANDBOX cho cleanup_oracle_1124.sh (CLEAN_H). Khong dung du lieu that, khong sudo, khong 242.
#   bash ~/claude_master/v12/c3live/ops/c3live/test_cleanup_oracle_1124.sh      (tu xoa sandbox khi xong; giu log o $SB/test.log neu KEEP=1)
set -uo pipefail
export LC_ALL=C
S=$(cd "$(dirname "$0")" && pwd)/cleanup_oracle_1124.sh
SB=/home/ubuntu/claude_master/v12/cleanup_1124_sandbox; H=$SB/h; CM=$H/claude_master
PASS=0; FAIL=0; N=0
ok() { N=$((N + 1)); if [ "$1" = 0 ]; then PASS=$((PASS + 1)); echo "PASS T$N: $2"; else FAIL=$((FAIL + 1)); echo "FAIL T$N: $2"; fi; }
has() { grep -qF -- "$2" "$1"; }
tsum() { find "$1" -path "$1/claude_master/cleanup_logs" -prune -o -printf '%y %s %T@ %p\n' 2>/dev/null | sort | sha256sum | cut -c1-16; }
txt() { mkdir -p "$(dirname "$1")"; seq "$2" | awk '{print "line " $1 " abcdefghij abcdefghij " $1 % 97}' > "$1"; }
export CLEAN_H=$H CLEAN_RLIVE_PAT=fake_rlive_1124_$$ CLEAN_FSTAB=$SB/fstab CLEAN_SWAP_SHOW="/swapfile 8589930496 3000000000" \
       CLEAN_MEMAVAIL=18000 CLEAN_MINFREE=1048576 CLEAN_MINRAM=100
run() { local o=$SB/out_$N.log; bash "$S" "$@" > "$o" 2>&1; RC=$?; OUT=$o; }
[ -d "$SB" ] && rm -rf "$SB"
mkdir -p "$SB" || exit 9
# ------------------------------------------------ dung sandbox (~3 MB)
mkdir -p "$CM"/{deploy,locks,archive,cleanup_logs} "$H/ops" "$CM/w3/add24_wt/tools/add24/rlive" "$CM/w3/add24_wt/tools/e2e" "$CM/w3/c3_ops6/ops" \
         "$CM/vz_e1_wt/research/parity_v12/sh" "$CM/parity_v12w/d"
printf '%s\n' 'DAYS=2026-11-04,2026-11-05' 'LIVEBUF=$HOME/claude_master/pull242/2026-11-14/run/gate_ratio_live.bin.gz' > "$CM/w3/add24_wt/tools/add24/rlive/run_rlive.sh"
printf '%s\n' 'START=${START:-2026-11-04}' 'P=$HOME/claude_master/pull242' > "$CM/vz_e1_wt/research/parity_v12/sh/watch_daily_v12.sh"
printf '%s\n' 'W=$HOME/claude_master/parity_v12w' 'B=$W/d/$D' 'VIS=$HOME/claude_master/parity_v11w/vision/klines_1m' > "$CM/vz_e1_wt/research/parity_v12/sh/run_day.sh"
echo 'X=$HOME/claude_master/res1109/r3_gate/pred/' > "$CM/deploy/use_pred.sh"
mkdir -p "$CM/ind1114"; echo 'R="/home/ubuntu/claude_master/res1109/r1_s1/a2_bins"' > "$CM/ind1114/old.py"
for d in 2026-11-04 2026-11-15 2026-11-16; do mkdir -p "$CM/parity_v12w/d/$d"; touch "$CM/parity_v12w/d/$d/DONE"; done
for d in 2026-10-29 2026-11-03 2026-11-14 2026-11-16 2026-11-17 2026-11-18 2026-11-20; do
  txt "$CM/pull242/$d/logs/full.log" 3000; txt "$CM/pull242/$d/s1/s1.csv" 500; touch "$CM/pull242/$d/COMPLETE"; done
echo log > "$CM/pull242/pull.log"; echo c > "$CM/pull242/cron.out"
txt "$CM/parity_v11w/vision/klines_1m/2026-11-20/A.csv" 500; txt "$CM/parity_v11w/work/w.json" 2000; txt "$CM/parity_v11w/d/2026-10-25/live/f.csv" 2000
txt "$CM/parity_v11w/live/l.csv" 200; txt "$CM/parity_v11w/runs/r1/o.csv" 200
txt "$CM/res1109/r1_s1/a2_bins/p1.bin" 300; txt "$CM/res1109/r1_s1/a2_bins/meta.json" 10; txt "$CM/res1109/r1_s1/kl/k.bin" 300
txt "$CM/res1109/r3_gate/pred/pred_s1.bin" 300; txt "$CM/res1109/r5_quality/sig_a.npz" 300; txt "$CM/res1109/r5_quality/sig_meta.json" 10
txt "$H/java/devrun/run1/storage/printDone.csv" 3000; txt "$H/java/devrun/run1/a.txt" 1000; ln -s run1 "$H/java/devrun/lnk"; mkdir -p "$H/java/devrun/empty"
txt "$H/java/fsrun/CLOSES.txt" 100
mkdir -p "$H/vz/pilot_upload"; head -c 300000 /dev/urandom > "$H/vz/pilot_upload/k.parquet"
G() { git -c user.name=t -c user.email=t@l -c init.defaultBranch=main "$@"; }
mkdir -p "$H/src/BinanceFuturesJava"; ( cd "$H/src/BinanceFuturesJava" && G init -q && echo a > a.txt && G add a.txt && G commit -qm init ) || exit 9
for w in geom nsel gqsf pxcache; do G -C "$H/src/BinanceFuturesJava" worktree add -q -b "b_$w" "$H/src_wt_$w" >/dev/null 2>&1 || exit 9; done
echo dirty >> "$H/src_wt_nsel/a.txt"; echo 'class PrivateConfig {}' > "$H/src_wt_gqsf/PrivateConfig.java"
printf '%s\n' 'LABEL=cloudimg-rootfs / ext4 defaults 0 1' '/swapfile none swap sw 0 0' > "$SB/fstab"
find "$H" -exec touch -h -d '2026-10-01 00:00' {} + 2>/dev/null
echo "sandbox: $(du -sh "$SB" | cut -f1)"
P18=$(tsum "$CM/pull242/2026-11-18"); P20=$(tsum "$CM/pull242/2026-11-20"); VIS=$(tsum "$CM/parity_v11w/vision"); FS=$(tsum "$H/java/fsrun")
# ------------------------------------------------ T1 DRY toan bo: khong doi gi, ke hoach dung
ALL0=$(tsum "$H")
run
ok "$([ "$RC" = 0 ] && [ "$(tsum "$H")" = "$ALL0" ] && echo 0 || echo 1)" "DRY rc=0 va KHONG doi gi trong sandbox (rc=$RC)"
L=$OUT
ok "$(has $L 'SE nen java/devrun' && has $L 'SE nen pull242/2026-10-29' && has $L 'SE nen pull242/2026-11-16' && has $L 'SE nen parity_v11w/work' && echo 0 || echo 1)" "DRY: nen devrun, pull242 10-29/11-16, parity_v11w/work"
ok "$(has $L 'BO QUA pull242/2026-11-14 - run_rlive.sh dev1105' && has $L 'BO QUA pull242/2026-11-17 - parity v1.2 ngay 2026-11-17 chua DONE' && ! grep -q 'pull242/2026-11-18\|pull242/2026-11-20' $L && echo 0 || echo 1)" "DRY pull242: 11-14 (harness song) + 11-17 (chua DONE) bo qua; ngay >= 11-18 khong bao gio la ung vien"
ok "$(has $L 'BO QUA parity_v11w/d - file song' && ! grep -q 'parity_v11w/vision\|parity_v11w/live \|parity_v11w/runs' $L && echo 0 || echo 1)" "DRY parity_v11w: d bi chan (run_day.sh), vision/live/runs khong la ung vien"
ok "$(has $L 'SE xoa res1109/r1_s1/a2_bins: 1 file' && has $L 'BO QUA res1109/r3_gate/pred - tham chieu SONG' && has $L 'ind1114/old.py' && has $L 'SE xoa res1109/r5_quality/sig_' && echo 0 || echo 1)" "DRY res1109: a2_bins + sig xoa; pred chan (deploy); tham chieu nghien cuu cu duoc liet ke"
ok "$(grep -q "SE git worktree remove  $H/src_wt_geom" $L && grep -q "SE git worktree remove --force $H/src_wt_gqsf" $L && grep -q "BO QUA (1 file chua commit/untracked ngoai PrivateConfig) $H/src_wt_nsel" $L && ! grep -q src_wt_pxcache $L && echo 0 || echo 1)" "DRY worktree: geom thuong, gqsf --force (chi PrivateConfig), nsel ban => bo qua, pxcache khong dung"
ok "$(has $L 'BO QUA vz/pilot_upload - khong dang nen' && has $L 'SE: swapoff' && has $L 'SE: sudo journalctl --vacuum-size=200M' && echo 0 || echo 1)" "DRY: pilot_upload (khong nen duoc) bo qua; swap + journal chi in"
# ------------------------------------------------ T run_rlive dang chay => tu choi
bash -c "exec -a fake_rlive_1124_$$ sleep 8" & BG=$!; sleep 1
run --apply
ok "$([ "$RC" = 3 ] && has $OUT 'TU CHOI --apply' && [ "$(tsum "$H")" = "$ALL0" ] && echo 0 || echo 1)" "run_rlive dang chay => --apply TU CHOI rc=3, khong doi gi (rc=$RC)"
wait $BG 2>/dev/null
# ------------------------------------------------ T dia duoi nguong => dung phan nen
W0=$(tsum "$CM/parity_v11w/work")
CLEAN_MINFREE=999999999999999 run --apply --only=2
ok "$([ "$RC" = 2 ] && has $OUT 'DUNG phan nen: dia trong' && [ "$(tsum "$CM/parity_v11w/work")" = "$W0" ] && [ -z "$(ls -A "$CM/archive")" ] && echo 0 || echo 1)" "dia duoi nguong => DUNG phan nen rc=2, goc nguyen, khong archive (rc=$RC)"
# ------------------------------------------------ T swap sandbox: chi in lenh
run --apply --only=1
ok "$([ "$RC" = 0 ] && has $OUT '[sandbox, KHONG chay] sudo swapoff /swapfile' && has $OUT '[sandbox, KHONG chay] sudo mkswap /swapfile' && has $OUT '[sandbox, KHONG chay] sudo swapon /swapfile' && echo 0 || echo 1)" "swap sandbox: chi in lenh swapoff/mkswap/swapon (rc=$RC)"
CLEAN_MEMAVAIL=3000 run --apply --only=1
ok "$([ "$RC" = 0 ] && has $OUT 'BO QUA: swap dang dung' && ! has $OUT 'sudo swapoff' && echo 0 || echo 1)" "swap: dung + 2000 >= RAM available => bo qua"
# ------------------------------------------------ T res1109 apply
run --apply --only=3
ok "$([ "$RC" = 0 ] && [ ! -e "$CM/res1109/r1_s1/a2_bins/p1.bin" ] && [ -f "$CM/res1109/r1_s1/a2_bins/meta.json" ] && [ -f "$CM/res1109/r1_s1/kl/k.bin" ] && [ -f "$CM/res1109/r3_gate/pred/pred_s1.bin" ] && [ ! -e "$CM/res1109/r5_quality/sig_a.npz" ] && [ -f "$CM/res1109/r5_quality/sig_meta.json" ] && echo 0 || echo 1)" "res1109 apply: xoa .bin/.npz whitelist; giu json, kl, pred (tham chieu song) (rc=$RC)"
# ------------------------------------------------ T process mo file => bo qua; worktree apply
D0=$(tsum "$H/java/devrun")
( exec 7<"$H/java/devrun/run1/a.txt"; sleep 8 ) & BG=$!; sleep 1
run --apply --only=5
ok "$(has $OUT 'BO QUA java/devrun - process dang dung' && [ "$(tsum "$H/java/devrun")" = "$D0" ] && [ ! -e "$CM/archive/java__devrun.tar.zst" ] && echo 0 || echo 1)" "process mo file trong devrun => BO QUA, goc nguyen (rc=$RC)"
ok "$([ ! -e "$H/src_wt_geom" ] && [ ! -e "$H/src_wt_gqsf" ] && [ -d "$H/src_wt_nsel" ] && [ -d "$H/src_wt_pxcache" ] && ! git -C "$H/src/BinanceFuturesJava" worktree list | grep -q 'src_wt_geom\|src_wt_gqsf' && echo 0 || echo 1)" "worktree: geom + gqsf(--force) go bang git worktree remove; nsel (ban) + pxcache con nguyen"
ok "$(has $OUT '[sandbox, KHONG chay] sudo journalctl --vacuum-size=200M' && echo 0 || echo 1)" "journal sandbox: chi in lenh"
wait $BG 2>/dev/null
# ------------------------------------------------ T verify lech => giu goc
CLEAN_TEST_MUTATE=$H/java/devrun/run1/a.txt run --apply --only=5
ok "$([ "$RC" = 1 ] && has $OUT 'LECH sha256 tung file' && has $OUT 'GIU NGUYEN goc' && [ -f "$H/java/devrun/run1/a.txt" ] && [ -z "$(ls "$CM/archive" | grep devrun)" ] && echo 0 || echo 1)" "verify lech (goc bi sua sau khi nen) => xoa .part, giu goc, rc=1 (rc=$RC)"
# ------------------------------------------------ T nen thanh cong + lossless (giai nen, diff -r)
find "$H/java/devrun" -exec touch -h -d "2026-10-01 00:00" {} +; cp -a "$H/java/devrun" "$SB/ref_devrun"
run --apply --only=5
mkdir -p "$SB/x"; zstd -q -dc "$CM/archive/java__devrun.tar.zst" | tar -C "$SB/x" -xf -
ok "$([ "$RC" = 0 ] && [ ! -e "$H/java/devrun" ] && diff -r --no-dereference "$SB/ref_devrun" "$SB/x/devrun" >/dev/null && [ -L "$SB/x/devrun/lnk" ] && [ -d "$SB/x/devrun/empty" ] && (cd "$CM/archive" && sha256sum -c --quiet java__devrun.tar.zst.sha256) && [ -s "$CM/archive/java__devrun.sha256list" ] && [ "$(tsum "$H/java/fsrun")" = "$FS" ] && echo 0 || echo 1)" "nen devrun: goc da xoa; giai nen + diff -r == ban truoc (ca symlink, thu muc rong); .sha256 dung; fsrun nguyen (rc=$RC)"
# ------------------------------------------------ T symlink => abort
mkdir -p "$H/java/devrun_real"; txt "$H/java/devrun_real/z.txt" 100; ln -s devrun_real "$H/java/devrun"; R0=$(tsum "$H/java/devrun_real")
run --apply --only=5
ok "$([ "$RC" = 1 ] && has $OUT 'ABORT muc 5b: symlink' && [ "$(tsum "$H/java/devrun_real")" = "$R0" ] && [ -L "$H/java/devrun" ] && echo 0 || echo 1)" "symlink => ABORT muc, dich nguyen (rc=$RC)"
rm -f "$H/java/devrun"
# ------------------------------------------------ T pull242 apply
cp -a "$CM/pull242/2026-10-29" "$SB/ref_1029"
run --apply --only=4
mkdir -p "$SB/y"; zstd -q -dc "$CM/archive/pull242/2026-10-29.tar.zst" | tar -C "$SB/y" -xf -
ok "$([ "$RC" = 0 ] && [ ! -e "$CM/pull242/2026-10-29" ] && [ ! -e "$CM/pull242/2026-11-03" ] && [ ! -e "$CM/pull242/2026-11-16" ] && [ -d "$CM/pull242/2026-11-14" ] && [ -d "$CM/pull242/2026-11-17" ] && [ -f "$CM/pull242/pull.log" ] && diff -r "$SB/ref_1029" "$SB/y/2026-10-29" >/dev/null && echo 0 || echo 1)" "pull242 apply: nen 10-29/11-03/11-16 (lossless diff -r); giu 11-14, 11-17 (chua DONE), file cap 1 (rc=$RC)"
ok "$([ "$(tsum "$CM/pull242/2026-11-18")" = "$P18" ] && [ "$(tsum "$CM/pull242/2026-11-20")" = "$P20" ] && echo 0 || echo 1)" "pull242 ngay >= 11-18 KHONG bao gio bi dung"
# ------------------------------------------------ T parity_v11w apply
run --apply --only=2
ok "$([ "$RC" = 0 ] && [ ! -e "$CM/parity_v11w/work" ] && [ -f "$CM/archive/parity_v11w__work.tar.zst" ] && [ -d "$CM/parity_v11w/d" ] && [ "$(tsum "$CM/parity_v11w/vision")" = "$VIS" ] && [ -d "$CM/parity_v11w/live" ] && [ -d "$CM/parity_v11w/runs" ] && echo 0 || echo 1)" "parity_v11w apply: nen work; d (tham chieu song) + vision/live/runs nguyen (rc=$RC)"
# ------------------------------------------------ T guard: duong dan pull242 >= 11-18 qua symlink ung vien => abort
ln -s "$CM/pull242/2026-11-20" "$H/vz/pilot_upload2"; rm -rf "$H/vz/pilot_upload"; ln -s "$CM/pull242/2026-11-20" "$H/vz/pilot_upload"
run --apply --only=5
ok "$([ "$RC" = 1 ] && has $OUT 'ABORT muc 5c: symlink' && [ "$(tsum "$CM/pull242/2026-11-20")" = "$P20" ] && echo 0 || echo 1)" "ung vien la symlink -> pull242 11-20 => ABORT, 11-20 nguyen (rc=$RC)"
echo "=== KET QUA: $PASS/$N PASS, $FAIL FAIL"
cp "$SB"/out_*.log /home/ubuntu/claude_master/cleanup_logs/ 2>/dev/null; mkdir -p /home/ubuntu/claude_master/cleanup_logs/test_1124_$$ && mv /home/ubuntu/claude_master/cleanup_logs/out_*.log /home/ubuntu/claude_master/cleanup_logs/test_1124_$$/ 2>/dev/null
if [ "${KEEP:-0}" != 1 ]; then rm -rf "$SB"; fi
[ "$FAIL" = 0 ]
