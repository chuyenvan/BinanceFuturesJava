#!/bin/bash
# R4u-final: worktree rieng tu commit sach, PrivateConfig copy tu ~/src_wt_pxcache (KHONG in noi dung), mvn package
# (env shadow, loai Live242WriteGuardTest), sec check + so voi r4t. Khong cham 242, khong upload.
set -u
C=$1
W=$HOME/claude_master/v12/wt_r4u3
O=$HOME/claude_master/res1109/r4u
LOG=$O/build_r4u3.log
export LIVE_IS_SHADOW_HOST=true
export MAVEN_OPTS=-Xmx2g
echo "start $(date) commit=$C" > $LOG
AV=$(free -m | awk '/Mem:/{print $7}'); DF=$(df -BG --output=avail ~ | tail -1 | tr -dc 0-9)
echo "avail_mb=$AV df_g=$DF" >> $LOG
if [ "$AV" -lt 4000 ] || [ "$DF" -lt 15 ]; then echo "SKIP_RESOURCES" >> $LOG; exit 3; fi
cd $HOME/claude_master/v12/c3live
[ -d $W ] || git worktree add --detach $W $C >> $LOG 2>&1
cd $W && git checkout -q --detach $C && echo "dirty=$(git status --short | wc -l)" >> $LOG
PC=src/main/java/com/binance/chuyennd/config/PrivateConfig.java
mkdir -p $(dirname $PC)
install -m 600 $HOME/src_wt_pxcache/$PC $PC
cmp -s $PC $HOME/claude_master/v12/c3live/$PC && echo "privateconfig=giong_c3live(r4t)" >> $LOG || echo "privateconfig=KHAC" >> $LOG
git check-ignore -q $PC && echo "privateconfig_gitignored=1" >> $LOG
flock -w 3600 $HOME/claude_master/locks/oracle_heavy.lock nice -n 10 \
  /home/ubuntu/tools/apache-maven-3.9.9/bin/mvn -o -T 1 package -Dtest=!Live242WriteGuardTest -Dsurefire.failIfNoSpecifiedTests=false > $O/mvn_r4u3.log 2>&1
echo "MVN_RC=$? $(date)" >> $LOG
grep -a -E 'Tests run: [0-9]+, Fail.*Skipped: [0-9]+$' $O/mvn_r4u3.log | tail -1 >> $LOG
grep -a -h 'Tests run' target/surefire-reports/*BigDownSelectTest.txt target/surefire-reports/*C3ExcludeLegacyHeldTest.txt target/surefire-reports/*LegacyIsolationTest.txt target/surefire-reports/*C3ExclForceTest.txt >> $LOG
J=$W/target/binance-java-sdk-1.2.4.jar
[ -f $J ] || { echo NOJAR >> $LOG; exit 4; }
F=$HOME/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4u3
cp $J $F && chmod 600 $F
md5sum $F >> $LOG
R=$HOME/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4t
for t in r4t:$R final:$F; do
  n=${t%%:*}; j=${t#*:}
  python3 -I $HOME/claude_master/nup3_wk/jar_sec_check.py $j $O/sec3_$n.json > /dev/null 2>&1; echo "sec_rc_$n=$?" >> $LOG
  python3 -I $HOME/claude_master/nup4_fix/jar_sec_check_tg.py $j > $O/sectg3_$n.json 2>&1; echo "sectg_rc_$n=$?" >> $LOG
done
python3 - $O >> $LOG <<'PY'
import json, sys
o = sys.argv[1]
a, b = json.load(open(o + "/sec3_r4t.json")), json.load(open(o + "/sec3_final.json"))
for k in a:
    if k == "jar":
        continue
    print("SEC", k, "SAME" if a[k] == b[k] else "DIFF r4t=%s final=%s" % (a[k], b[k]))
ta = json.load(open(o + "/sectg3_r4t.json")); tb = json.load(open(o + "/sectg3_final.json"))
ha = sorted(tuple(h) for v in ta.values() for h in v["hits"]); hb = sorted(tuple(h) for v in tb.values() for h in v["hits"])
print("SECTG hits", "SAME" if ha == hb else "DIFF", len(ha), len(hb))
PY
for c in com/binance/chuyennd/config/PrivateConfig.class com/binance/chuyennd/client/ClientSingleton.class com/binance/chuyennd/client/BinanceFuturesClientSingleton.class; do
  a=$(unzip -p $R $c | md5sum | cut -c1-8); b=$(unzip -p $F $c | md5sum | cut -c1-8)
  [ "$a" = "$b" ] && echo "CLASS_SAME $c" >> $LOG || echo "CLASS_DIFF $c" >> $LOG
done
unzip -v $J | awk 'NR>3 && $1 ~ /^[0-9]+$/ {print $7, $8}' | sort -k2 > /tmp/r4uf_m.crc
unzip -v $R | awk 'NR>3 && $1 ~ /^[0-9]+$/ {print $7, $8}' | sort -k2 > /tmp/r4uf_r.crc
echo "class_diff_vs_r4t:" >> $LOG; diff /tmp/r4uf_r.crc /tmp/r4uf_m.crc | grep '^[<>]' | awk '{print $1, $3}' | sort -u -k2 >> $LOG
rm -f /tmp/r4uf_m.crc /tmp/r4uf_r.crc
echo "DONE $(date)" >> $LOG
