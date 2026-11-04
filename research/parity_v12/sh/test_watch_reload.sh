#!/bin/bash
# test tu-nap: chay ban sao watcher voi sleep ngan trong thu muc tam, doi file -> phai thay RELOAD + START moi, cung pid
set -u
T=$(mktemp -d)
mkdir -p $T/r/sh $T/w/exinfo $T/w/d
src=$HOME/claude_master/vz_e1_wt/research/parity_v12/sh/watch_daily_v12.sh
sed -e "s#^R=.*#R=$T/r#" -e "s#^W=.*#W=$T/w#" -e "s#^P=.*#P=$T/p#" -e "s#sleep 1800#sleep 1#" \
    -e "s#bash \$R/sh/exinfo_snap.sh#true#" $src > $T/r/sh/watch_daily_v12.sh
touch $T/w/exinfo/exinfo_x.json.gz $T/w/exinfo/index.log
START=2099-01-01 bash $T/r/sh/watch_daily_v12.sh & pid=$!
sleep 3
echo "# doi" >> $T/r/sh/watch_daily_v12.sh
sleep 4
kill $pid 2>/dev/null; sleep 1
cat $T/w/watch_v12.log
nstart=$(grep -c START $T/w/watch_v12.log); nrel=$(grep -c RELOAD $T/w/watch_v12.log)
pids=$(grep START $T/w/watch_v12.log | sed 's/.*pid=\([0-9]*\).*/\1/' | sort -u | wc -l)
if [ $nstart -eq 2 ] && [ $nrel -eq 1 ] && [ $pids -eq 1 ]; then echo TEST_RELOAD PASS; else echo TEST_RELOAD FAIL; fi
rm -rf $T
