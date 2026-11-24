#!/usr/bin/env bash
# test_cleanup_oracle_1124.sh v2 - test SANDBOX cho cleanup_oracle_1124.sh (CLEAN_H). Khong du lieu that, khong sudo, khong 242,
# khong lock that (lock trong sandbox). KEEP=1 de giu sandbox.
set -uo pipefail
export LC_ALL=C
S=$(cd "$(dirname "$0")" && pwd)/cleanup_oracle_1124.sh
SB=/home/ubuntu/claude_master/v12/cleanup_1124_sandbox; H=$SB/h; CM=$H/claude_master
PASS=0; FAIL=0; N=0
ok() { N=$((N + 1)); if [ "$1" = 0 ]; then PASS=$((PASS + 1)); echo "PASS T$N: $2"; else FAIL=$((FAIL + 1)); echo "FAIL T$N: $2"; fi; }
has() { grep -qF -- "$2" "$1"; }
tsum() { find "$1" -path "$1/claude_master/cleanup_logs" -prune -o -printf '%y %s %T@ %p\n' 2>/dev/null | sort | sha256sum | cut -c1-16; }
txt() { mkdir -p "$(dirname "$1")"; seq "$2" | awk '{print "line " $1 " abcdefghij abcdefghij " $1 % 97}' > "$1"; }
old() { find "$1" -exec touch -h -d '2026-10-01 00:00' {} + 2>/dev/null; }
export CLEAN_H=$H CLEAN_RLIVE_PAT=fake_rlive_1124_$$ CLEAN_FSTAB=$SB/fstab CLEAN_SWAP_SHOW="/swapfile 8589930496 3000000000" \
       CLEAN_MEMAVAIL=18000 CLEAN_MINFREE=1048576 CLEAN_MINRAM=100 CLEAN_D2B_NDOCS=2
run() { local o=$SB/out_$N.log; bash "$S" "$@" > "$o" 2>&1; RC=$?; OUT=$o; }
fake_rlive() { ( sleep "$1"; exec -a "fake_rlive_1124_$$" sleep "$2" ) & }
G() { git -c user.name=t -c user.email=t@l -c init.defaultBranch=main "$@"; }
[ -d "$SB" ] && rm -rf "$SB"
mkdir -p "$SB" || exit 9
# ------------------------------------------------ dung sandbox (~3 MB)
mkdir -p "$CM"/{deploy,locks,archive,cleanup_logs} "$H/ops" "$CM/w3/add24_wt/tools/add24/rlive" "$CM/w3/add24_wt/tools/e2e" "$CM/w3/c3_ops6/ops" \
         "$CM/vz_e1_wt/research/parity_v12/sh" "$CM/parity_v12w/d"
( cd "$CM/vz_e1_wt" && G init -q && echo r > README && G add README && G commit -qm i ) || exit 9
printf '%s\n' 'DAYS=2026-11-04,2026-11-05' 'LIVEBUF=$HOME/claude_master/pull242/2026-11-14/run/gate_ratio_live.bin.gz' > "$CM/w3/add24_wt/tools/add24/rlive/run_rlive.sh"
printf '%s\n' 'START=${START:-2026-11-04}' 'P=$HOME/claude_master/pull242' > "$CM/vz_e1_wt/research/parity_v12/sh/watch_daily_v12.sh"
printf '%s\n' 'W=$HOME/claude_master/parity_v12w' 'B=$W/d/$D' 'VIS=$HOME/claude_master/parity_v11w/vision/klines_1m' > "$CM/vz_e1_wt/research/parity_v12/sh/run_day.sh"
echo 'X=$HOME/claude_master/res1109/r3_gate/pred/' > "$CM/deploy/use_pred.sh"
mkdir -p "$CM/ind1114"; echo 'R="/home/ubuntu/claude_master/res1109/r1_s1/a2_bins"' > "$CM/ind1114/old.py"
for d in 2026-11-04 2026-11-15 2026-11-16; do mkdir -p "$CM/parity_v12w/d/$d"; touch "$CM/parity_v12w/d/$d/DONE"; done
for d in 2026-10-29 2026-11-03 2026-11-14 2026-11-16 2026-11-17 2026-11-18 2026-11-20; do
  txt "$CM/pull242/$d/logs/full.log" 3000; txt "$CM/pull242/$d/s1/s1.csv" 500; touch "$CM/pull242/$d/COMPLETE"; done
echo log > "$CM/pull242/pull.log"; echo c > "$CM/pull242/cron.out"
txt "$CM/parity_v11w/vision/klines_1m/2026-11-20/A.csv" 500; txt "$CM/parity_v11w/work/w.json" 2000
txt "$CM/parity_v11w/d/2026-10-25/live/f.csv" 2000; txt "$CM/parity_v11w/d/2026-10-24_ops/o.txt" 50; txt "$CM/parity_v11w/d/logs/l.log" 50
txt "$CM/parity_v11w/d/run_1025.out" 50; mkdir -p "$CM/parity_v11w/d/2026-x-notdate"
txt "$CM/parity_v11w/live/l.csv" 200; txt "$CM/parity_v11w/runs/r1/o.csv" 200; txt "$CM/parity_v11w/univ/u.txt" 20; txt "$CM/parity_v11w/build/b.class" 20
txt "$CM/res1109/r1_s1/a2_bins/p1.bin" 300; txt "$CM/res1109/r1_s1/a2_bins/meta.json" 10; txt "$CM/res1109/r1_s1/kl/k.bin" 300
txt "$CM/res1109/r1_s1/a3_bins/a3.bin" 300; txt "$CM/res1109/r1_s1/g015x26/g.bin" 300
txt "$CM/res1109/r3_gate/pred/pred_s1.bin" 300; txt "$CM/res1109/r5_quality/sig_a.npz" 300; txt "$CM/res1109/r5_quality/sig_meta.json" 10
txt "$H/java/devrun/run1/storage/printDone.csv" 3000; txt "$H/java/devrun/run1/a.txt" 1000; ln -s run1 "$H/java/devrun/lnk"; mkdir -p "$H/java/devrun/empty"
txt "$H/java/fsrun/CLOSES.txt" 100
mkdir -p "$H/vz/pilot_upload"; head -c 300000 /dev/urandom > "$H/vz/pilot_upload/k.parquet"
PC=src/main/java/com/binance/chuyennd/config/PrivateConfig.java
mkdir -p "$H/src/BinanceFuturesJava"; ( cd "$H/src/BinanceFuturesJava" && G init -q && printf '%s\n' 'target/' 'logs/' '*.res' > .gitignore && echo a > a.txt && G add -A && G commit -qm init ) || exit 9
for w in geom nsel gqsf pxcache c3live2 nowrite; do G -C "$H/src/BinanceFuturesJava" worktree add -q -b "b_$w" "$H/src_wt_$w" >/dev/null 2>&1 || exit 9; done
txt "$H/src_wt_geom/target/x.jar" 10; txt "$H/src_wt_geom/logs/run.log" 10
echo dirty >> "$H/src_wt_nsel/a.txt"
mkdir -p "$H/src_wt_gqsf/$(dirname $PC)"; echo 'class PrivateConfig {}' > "$H/src_wt_gqsf/$PC"
echo 'ket qua' > "$H/src_wt_c3live2/PrivateConfig_NOTES_result.md"
echo '{"kq":1}' > "$H/src_wt_nowrite/out.res"
printf '%s\n' 'LABEL=cloudimg-rootfs / ext4 defaults 0 1' '/swapfile none swap sw 0 0' > "$SB/fstab"
old "$H"
echo "sandbox: $(du -sh "$SB" | cut -f1)"
P18=$(tsum "$CM/pull242/2026-11-18"); P20=$(tsum "$CM/pull242/2026-11-20"); VIS=$(tsum "$CM/parity_v11w/vision"); FS=$(tsum "$H/java/fsrun")
RS3=$(tsum "$CM/res1109/r1_s1/a3_bins")$(tsum "$CM/res1109/r1_s1/g015x26")
# ------------------------------------------------ DRY toan bo
ALL0=$(tsum "$H")
run
ok "$([ "$RC" = 0 ] && [ "$(tsum "$H")" = "$ALL0" ] && echo 0 || echo 1)" "DRY rc=0 va KHONG doi gi trong sandbox (rc=$RC)"
L=$OUT
ok "$(has $L 'SE nen java/devrun' && has $L 'SE nen pull242/2026-10-29' && has $L 'SE nen pull242/2026-11-16' && has $L 'SE nen parity_v11w/work' && echo 0 || echo 1)" "DRY: nen devrun, pull242 10-29/11-16, parity_v11w/work"
ok "$(has $L 'BO QUA pull242/2026-11-14 - run_rlive.sh dev1105' && has $L 'BO QUA pull242/2026-11-17 - parity v1.2 ngay 2026-11-17 chua DONE' && ! grep -q 'pull242/2026-11-18\|pull242/2026-11-20' $L && echo 0 || echo 1)" "DRY pull242: 11-14 + 11-17 bo qua; ngay >= 11-18 khong la ung vien"
ok "$(! grep -q 'nen parity_v11w/d\|BO QUA parity_v11w/d\|parity_v11w/vision\|parity_v11w/live \|parity_v11w/runs' $L && has $L 'BO QUA: docs/result/parity_v11_daily_* tracked 0' && echo 0 || echo 1)" "DRY: muc 2 khong con 'd'; 2b BO QUA khi tong ket chua commit; vision/live/runs khong la ung vien"
ok "$(has $L 'SE xoa res1109/r1_s1/a2_bins: 1 file' && has $L 'BO QUA res1109/r3_gate/pred - tham chieu SONG' && has $L 'ind1114/old.py' && has $L 'SE xoa res1109/r5_quality/sig_' && ! grep -q 'a3_bins\|g015x26' $L && echo 0 || echo 1)" "DRY res1109: a2_bins + sig xoa; pred chan; a3_bins/g015x26 KHONG con trong muc 3 (MAJOR-1)"
ok "$(grep -q "SE git worktree remove  $H/src_wt_geom" $L && grep -q "file ignored se MAT khi worktree remove ($H/src_wt_geom)" $L && grep -q "SE git worktree remove --force $H/src_wt_gqsf" $L && grep -q "BO QUA (1 file chua commit/untracked ngoai src/main/java/com/binance/chuyennd/config/PrivateConfig.java) $H/src_wt_nsel" $L && ! grep -q src_wt_pxcache $L && echo 0 || echo 1)" "DRY worktree: geom (ignored target/ logs/ duoc in), gqsf --force (dung duong PrivateConfig), nsel ban bo qua, pxcache khong dung"
ok "$(grep -q "BO QUA (1 file chua commit/untracked ngoai .*) $H/src_wt_c3live2" $L && grep -q "BO QUA (1 muc ignored ngoai target/ logs/ PrivateConfig.java ledger.csv: out.res ) $H/src_wt_nowrite" $L && echo 0 || echo 1)" "MINOR-1: PrivateConfig_NOTES_result.md KHONG duoc coi la PrivateConfig => bo qua; MINOR-2: ignored out.res => bo qua"
ok "$(has $L 'BO QUA vz/pilot_upload - khong dang nen' && has $L 'SE: swapoff' && has $L 'SE: sudo journalctl --vacuum-size=200M' && echo 0 || echo 1)" "DRY: pilot_upload bo qua; swap + journal chi in"
# ------------------------------------------------ --only gia tri la => thoat loi, khong lam gi
bad=0; for v in 6 5e 2c 0 '1;rm' '' ',1' '1,,3' 'a' '5a 5b'; do run --apply "--only=$v"; if [ "$RC" != 1 ] || ! has $OUT 'only sai'; then bad=1; fi; done
ok "$([ "$bad" = 0 ] && [ "$(tsum "$H")" = "$ALL0" ] && echo 0 || echo 1)" "MAJOR-3: --only gia tri la (6 5e 2c 0 '1;rm' rong ...) => rc 1, khong doi gi"
# ------------------------------------------------ MAJOR-2: tham chieu o w3/add24_wt/tools (cap 1) => devrun BO QUA
echo "B=$H/java/devrun" > "$CM/w3/add24_wt/tools/run_c2b_dev.sh"; old "$CM/w3/add24_wt/tools"
run --only=5b
ok "$([ "$RC" = 0 ] && has $OUT 'BO QUA java/devrun - tham chieu SONG' && has $OUT 'tools/run_c2b_dev.sh' && echo 0 || echo 1)" "MAJOR-2: devrun duoc w3/add24_wt/tools/run_c2b_dev.sh tham chieu => BO QUA (rc=$RC)"
rm -f "$CM/w3/add24_wt/tools/run_c2b_dev.sh"; ALL0=$(tsum "$H")
# ------------------------------------------------ run_rlive dang chay => tu choi
bash -c "exec -a fake_rlive_1124_$$ sleep 8" & BG=$!; sleep 1
run --apply
ok "$([ "$RC" = 3 ] && has $OUT 'TU CHOI --apply' && [ "$(tsum "$H")" = "$ALL0" ] && echo 0 || echo 1)" "run_rlive dang chay => --apply TU CHOI rc=3, khong doi gi (rc=$RC)"
wait $BG 2>/dev/null
# ------------------------------------------------ MINOR-3: run_rlive xuat hien GIUA chung => dung truoc thao tac pha huy
fake_rlive 1 15; BG=$!
CLEAN_TEST_DELAY=3 run --apply --only=1,3
ok "$([ "$RC" = 1 ] && has $OUT 'run_rlive dang chay - khong swapoff' && has $OUT 'run_rlive dang chay - dung truoc rm' && [ -f "$CM/res1109/r1_s1/a2_bins/p1.bin" ] && [ -f "$CM/res1109/r5_quality/sig_a.npz" ] && echo 0 || echo 1)" "MINOR-3: run_rlive xuat hien sau kiem dau => ABORT truoc swapoff va truoc rm res1109, file nguyen (rc=$RC)"
wait $BG 2>/dev/null
fake_rlive 1 6; BG=$!
CLEAN_TEST_DELAY=3 run --apply --only=5a
ok "$([ "$RC" = 1 ] && has $OUT 'run_rlive dang chay - dung truoc worktree remove' && [ -d "$H/src_wt_geom" ] && echo 0 || echo 1)" "MINOR-3: run_rlive xuat hien => ABORT truoc git worktree remove, worktree nguyen (rc=$RC)"
wait $BG 2>/dev/null
# ------------------------------------------------ dia duoi nguong => dung phan nen
W0=$(tsum "$CM/parity_v11w/work")
CLEAN_MINFREE=999999999999999 run --apply --only=2
ok "$([ "$RC" = 2 ] && has $OUT 'DUNG phan nen: dia trong' && [ "$(tsum "$CM/parity_v11w/work")" = "$W0" ] && [ -z "$(ls -A "$CM/archive")" ] && echo 0 || echo 1)" "dia duoi nguong => DUNG phan nen rc=2, goc nguyen (rc=$RC)"
# ------------------------------------------------ swap sandbox
run --apply --only=1
ok "$([ "$RC" = 0 ] && has $OUT '[sandbox, KHONG chay] sudo swapoff /swapfile' && has $OUT '[sandbox, KHONG chay] sudo mkswap /swapfile' && has $OUT '[sandbox, KHONG chay] sudo swapon /swapfile' && echo 0 || echo 1)" "swap sandbox: chi in lenh (rc=$RC)"
CLEAN_MEMAVAIL=3000 run --apply --only=1
ok "$([ "$RC" = 0 ] && has $OUT 'BO QUA: swap dang dung' && ! has $OUT 'sudo swapoff' && echo 0 || echo 1)" "swap: dung + 2000 >= RAM available => bo qua"
# ------------------------------------------------ res1109 apply
run --apply --only=3
ok "$([ "$RC" = 0 ] && [ ! -e "$CM/res1109/r1_s1/a2_bins/p1.bin" ] && [ -f "$CM/res1109/r1_s1/a2_bins/meta.json" ] && [ -f "$CM/res1109/r1_s1/kl/k.bin" ] && [ -f "$CM/res1109/r3_gate/pred/pred_s1.bin" ] && [ ! -e "$CM/res1109/r5_quality/sig_a.npz" ] && [ "$(tsum "$CM/res1109/r1_s1/a3_bins")$(tsum "$CM/res1109/r1_s1/g015x26")" = "$RS3" ] && echo 0 || echo 1)" "res1109 apply: xoa a2_bins .bin + sig; giu json, kl, pred, a3_bins, g015x26 (rc=$RC)"
# ------------------------------------------------ --only=5a rieng: chi worktree
DV0=$(tsum "$H/java/devrun")
run --apply --only=5a
ok "$([ "$RC" = 0 ] && [ ! -e "$H/src_wt_geom" ] && [ ! -e "$H/src_wt_gqsf" ] && [ -d "$H/src_wt_nsel" ] && [ -d "$H/src_wt_c3live2" ] && [ -f "$H/src_wt_c3live2/PrivateConfig_NOTES_result.md" ] && [ -f "$H/src_wt_nowrite/out.res" ] && [ -d "$H/src_wt_pxcache" ] && ! git -C "$H/src/BinanceFuturesJava" worktree list | grep -q 'src_wt_geom\|src_wt_gqsf' && echo 0 || echo 1)" "--only=5a: geom + gqsf go; nsel, c3live2 (NOTES giu), nowrite (out.res giu), pxcache nguyen (rc=$RC)"
ok "$(! has $OUT 'MUC 5d' && ! has $OUT 'NEN LOSSLESS' && [ "$(tsum "$H/java/devrun")" = "$DV0" ] && echo 0 || echo 1)" "--only=5a KHONG cham 5b/5c/5d"
# ------------------------------------------------ process mo file => bo qua
( exec 7<"$H/java/devrun/run1/a.txt"; sleep 8 ) & BG=$!; sleep 1
run --apply --only=5b
ok "$(has $OUT 'BO QUA java/devrun - process dang dung' && [ "$(tsum "$H/java/devrun")" = "$DV0" ] && [ ! -e "$CM/archive/java__devrun.tar.zst" ] && echo 0 || echo 1)" "process mo file trong devrun => BO QUA, goc nguyen (rc=$RC)"
wait $BG 2>/dev/null
run --apply --only=5d
ok "$(has $OUT '[sandbox, KHONG chay] sudo journalctl --vacuum-size=200M' && echo 0 || echo 1)" "--only=5d: journal sandbox chi in lenh"
# ------------------------------------------------ verify lech => giu goc
CLEAN_TEST_MUTATE=$H/java/devrun/run1/a.txt run --apply --only=5b
ok "$([ "$RC" = 1 ] && has $OUT 'LECH sha256 tung file' && has $OUT 'GIU NGUYEN goc' && [ -f "$H/java/devrun/run1/a.txt" ] && [ -z "$(ls "$CM/archive" | grep devrun)" ] && echo 0 || echo 1)" "verify lech => xoa .part, giu goc, rc=1 (rc=$RC)"
# ------------------------------------------------ nen thanh cong + lossless
old "$H/java/devrun"; cp -a "$H/java/devrun" "$SB/ref_devrun"
run --apply --only=5b
mkdir -p "$SB/x"; zstd -q -dc "$CM/archive/java__devrun.tar.zst" | tar -C "$SB/x" -xf -
ok "$([ "$RC" = 0 ] && [ ! -e "$H/java/devrun" ] && diff -r --no-dereference "$SB/ref_devrun" "$SB/x/devrun" >/dev/null && [ -L "$SB/x/devrun/lnk" ] && [ -d "$SB/x/devrun/empty" ] && (cd "$CM/archive" && sha256sum -c --quiet java__devrun.tar.zst.sha256) && [ -s "$CM/archive/java__devrun.sha256list" ] && [ "$(tsum "$H/java/fsrun")" = "$FS" ] && echo 0 || echo 1)" "nen devrun: goc xoa; giai nen + diff -r == ban truoc; .sha256 dung; fsrun nguyen (rc=$RC)"
# ------------------------------------------------ symlink => abort
mkdir -p "$H/java/devrun_real"; txt "$H/java/devrun_real/z.txt" 100; ln -s devrun_real "$H/java/devrun"; R0=$(tsum "$H/java/devrun_real")
run --apply --only=5b
ok "$([ "$RC" = 1 ] && has $OUT 'ABORT muc 5b: symlink' && [ "$(tsum "$H/java/devrun_real")" = "$R0" ] && [ -L "$H/java/devrun" ] && echo 0 || echo 1)" "symlink => ABORT muc, dich nguyen (rc=$RC)"
rm -f "$H/java/devrun"
# ------------------------------------------------ pull242 apply
cp -a "$CM/pull242/2026-10-29" "$SB/ref_1029"
run --apply --only=4
mkdir -p "$SB/y"; zstd -q -dc "$CM/archive/pull242/2026-10-29.tar.zst" | tar -C "$SB/y" -xf -
ok "$([ "$RC" = 0 ] && [ ! -e "$CM/pull242/2026-10-29" ] && [ ! -e "$CM/pull242/2026-11-03" ] && [ ! -e "$CM/pull242/2026-11-16" ] && [ -d "$CM/pull242/2026-11-14" ] && [ -d "$CM/pull242/2026-11-17" ] && [ -f "$CM/pull242/pull.log" ] && diff -r "$SB/ref_1029" "$SB/y/2026-10-29" >/dev/null && echo 0 || echo 1)" "pull242 apply: nen 10-29/11-03/11-16 lossless; giu 11-14, 11-17, file cap 1 (rc=$RC)"
# ------------------------------------------------ parity_v11w muc 2 (khong cham d)
D0=$(tsum "$CM/parity_v11w/d")
run --apply --only=2
ok "$([ "$RC" = 0 ] && [ ! -e "$CM/parity_v11w/work" ] && [ -f "$CM/archive/parity_v11w__work.tar.zst" ] && [ "$(tsum "$CM/parity_v11w/d")" = "$D0" ] && [ "$(tsum "$CM/parity_v11w/vision")" = "$VIS" ] && echo 0 || echo 1)" "muc 2 apply: nen work; d (khong thuoc muc 2) + vision nguyen (rc=$RC)"
# ------------------------------------------------ MUC 2b
run --apply --only=2b
ok "$([ "$RC" = 0 ] && has $OUT 'BO QUA: docs/result/parity_v11_daily_* tracked 0' && [ "$(tsum "$CM/parity_v11w/d")" = "$D0" ] && echo 0 || echo 1)" "2b: tong ket chua commit => BO QUA, d nguyen (rc=$RC)"
for x in 20261028 20261029; do mkdir -p "$CM/vz_e1_wt/docs/result/parity_v11_daily_$x"; echo '{}' > "$CM/vz_e1_wt/docs/result/parity_v11_daily_$x/s.json"; done
( cd "$CM/vz_e1_wt" && G add docs && G commit -qm d ) || exit 9
echo '{"x":1}' >> "$CM/vz_e1_wt/docs/result/parity_v11_daily_20261029/s.json"
run --apply --only=2b
ok "$([ "$RC" = 0 ] && has $OUT 'hoac chua sach' && [ "$(tsum "$CM/parity_v11w/d")" = "$D0" ] && echo 0 || echo 1)" "2b: tong ket bi sua (chua sach) => BO QUA (rc=$RC)"
( cd "$CM/vz_e1_wt" && G checkout -q -- docs ) || exit 9
( cd "$CM/parity_v11w/d/2026-10-25" && sleep 8 ) & BG=$!; sleep 1
run --apply --only=2b
ok "$([ "$RC" = 0 ] && has $OUT 'BO QUA: process dang dung' && [ "$(tsum "$CM/parity_v11w/d")" = "$D0" ] && echo 0 || echo 1)" "2b: process cwd trong d => BO QUA (rc=$RC)"
wait $BG 2>/dev/null
( exec -a "bash /x/parity_v11/sh/watch_daily.sh" sleep 8 ) & BG=$!; sleep 1
run --apply --only=2b
ok "$([ "$RC" = 0 ] && has $OUT 'watch_daily.sh (watcher v1.1)' && [ "$(tsum "$CM/parity_v11w/d")" = "$D0" ] && echo 0 || echo 1)" "2b: watcher v1.1 watch_daily.sh dang chay => BO QUA (rc=$RC)"
wait $BG 2>/dev/null
ln -s "$CM/pull242/2026-11-20" "$CM/parity_v11w/d/2026-11-30"
run --apply --only=2b
ok "$([ "$RC" = 1 ] && has $OUT 'ABORT muc 2b: symlink ten ngay' && [ "$(tsum "$CM/pull242/2026-11-20")" = "$P20" ] && [ -d "$CM/parity_v11w/d/2026-10-25" ] && echo 0 || echo 1)" "2b: symlink ten ngay trong d => ABORT, khong xoa gi (rc=$RC)"
rm -f "$CM/parity_v11w/d/2026-11-30"
run --apply --only=2b
MAN=$(ls "$CM"/archive/parity_v11w_d_manifest_*.txt 2>/dev/null | head -1)
ok "$([ "$RC" = 0 ] && [ ! -e "$CM/parity_v11w/d/2026-10-25" ] && [ ! -e "$CM/parity_v11w/d/2026-10-24_ops" ] && [ -f "$CM/parity_v11w/d/logs/l.log" ] && [ -f "$CM/parity_v11w/d/run_1025.out" ] && [ -d "$CM/parity_v11w/d/2026-x-notdate" ] && [ -n "$MAN" ] && grep -q '2026-10-25/live/f.csv' "$MAN" && [ "$(tsum "$CM/parity_v11w/vision")" = "$VIS" ] && [ -d "$CM/parity_v11w/live" ] && [ -d "$CM/parity_v11w/runs" ] && [ -d "$CM/parity_v11w/univ" ] && [ -d "$CM/parity_v11w/build" ] && echo 0 || echo 1)" "2b: xoa 2026-10-25 + 2026-10-24_ops; giu d/logs, run_*.out, ten khong khop; manifest co; vision/live/runs/univ/build nguyen (rc=$RC)"
# ------------------------------------------------ bat bien cuoi
ok "$([ "$(tsum "$CM/pull242/2026-11-18")" = "$P18" ] && [ "$(tsum "$CM/pull242/2026-11-20")" = "$P20" ] && echo 0 || echo 1)" "pull242 ngay >= 11-18 KHONG bao gio bi dung"
rm -rf "$H/vz/pilot_upload"; ln -s "$CM/pull242/2026-11-20" "$H/vz/pilot_upload"
run --apply --only=5c
ok "$([ "$RC" = 1 ] && has $OUT 'ABORT muc 5c: symlink' && [ "$(tsum "$CM/pull242/2026-11-20")" = "$P20" ] && echo 0 || echo 1)" "ung vien symlink -> pull242 11-20 => ABORT, 11-20 nguyen (rc=$RC)"
echo "=== KET QUA: $PASS/$N PASS, $FAIL FAIL"
mkdir -p /home/ubuntu/claude_master/cleanup_logs/test_1124v2_$$ && cp "$SB"/out_*.log /home/ubuntu/claude_master/cleanup_logs/test_1124v2_$$/ 2>/dev/null
if [ "${KEEP:-0}" != 1 ]; then rm -rf "$SB"; fi
[ "$FAIL" = 0 ]
