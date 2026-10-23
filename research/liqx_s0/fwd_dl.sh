#!/bin/bash
# LIQX_S0 forward sample F: Vision monthly 1d klines 2026-09 (universe), daily 1m klines + daily metrics for top-100.
set -u
B=https://data.binance.vision/data/futures/um
W=~/claude_master/liqx_wk/fwd; mkdir -p $W/k1d $W/k1m $W/met; cd $W
zcat ~/vz/out/metrics5m/2026/2026-09.symbols.csv.gz | tail -n +2 | cut -d, -f1 > syms_2609.txt
cat syms_2609.txt | xargs -P 8 -I{} sh -c "[ -s k1d/{}.zip ] || curl -s --retry 2 -f -o k1d/{}.zip $B/monthly/klines/{}/1d/{}-1d-2026-09.zip"
ls k1d | wc -l
python3 - <<'EOF'
import zipfile, glob, os, io, pandas as pd
rows = []
for f in glob.glob(os.path.expanduser("~/claude_master/liqx_wk/fwd/k1d/*.zip")):
    z = zipfile.ZipFile(f); txt = z.read(z.namelist()[0]).decode()
    lines = [l for l in txt.splitlines() if l and l[0].isdigit()]
    qv = sum(float(l.split(",")[7]) for l in lines)
    rows.append((os.path.basename(f)[:-4], qv, len(lines)))
d = pd.DataFrame(rows, columns=["sym", "qv", "ndays"]).sort_values("qv", ascending=False)
d["rank"] = range(1, len(d) + 1)
d.head(100).to_csv(os.path.expanduser("~/claude_master/liqx_wk/fwd/uni_F.csv"), index=False)
print(d.head(5), len(d), d.head(100).ndays.value_counts().to_dict())
EOF
tail -n +2 uni_F.csv | cut -d, -f1 > uni_F.txt
for D in 2026-10-15 2026-10-16 2026-10-17 2026-10-18 2026-10-19 2026-10-20 2026-10-21 2026-10-22; do
  cat uni_F.txt | xargs -P 8 -I{} sh -c "[ -s k1m/{}-$D.zip ] || curl -s --retry 2 -f -o k1m/{}-$D.zip $B/daily/klines/{}/1m/{}-1m-$D.zip; [ $D = 2026-10-15 ] || [ -s met/{}-$D.zip ] || curl -s --retry 2 -f -o met/{}-$D.zip $B/daily/metrics/{}/{}-metrics-$D.zip"
done
echo k1m $(ls k1m | wc -l) met $(ls met | wc -l); du -sh $W
