#!/bin/bash
# ADD24 cong V4b (ERRATA3 A5): voi MOI quy tac parser, dem DOC LAP bang grep -F (dong khong trung, trong cua so) == tag_lines == parsed
# cua parser; va so dong [C3-LIVE*] khong khop quy tac = 0 (khac 0 => liet ke theo dang, A1 xem). Khong in gia tri dong.
# usage: v4b.sh <counts.json cua parser> <start 'YYYY-MM-DD HH:MM'> <end> <out.json> <log files...>
set -u
CJ=$1; S=$2; E=$3; OUT=$4; shift 4
T=$(cd "$(dirname "$0")" && pwd)
TMP=$(mktemp -d /dev/shm/add24/v4b.XXXX)
SK=$(date -d "$S" +%Y%m%d%H%M%S); EK=$(date -d "$E" +%Y%m%d%H%M%S)
for f in "$@"; do case $f in *.gz) zcat "$f";; *) cat "$f";; esac; done | sort -u | \
  awk -v s=$SK -v e=$EK '{k=substr($1,7,4) substr($1,4,2) substr($1,1,2) substr($2,1,2) substr($2,4,2) substr($2,7,2); if (k>=s && k<e) print}' > $TMP/w.log
python3 $T/live_log_parse.py --dump-rules > $TMP/rules.json
python3 - "$CJ" "$TMP" "$OUT" <<'PY'
import json, subprocess, sys
cj, tmp, out = sys.argv[1:4]
c = json.load(open(cj)); rules = json.load(open(tmp + '/rules.json'))
res = {'rules': {}, 'ok': True}
for r in rules:
    cmd = 'cat %s/w.log' % tmp
    for t in r['tags']:
        cmd += " | grep -F -e %s" % json.dumps(t).replace('$', '\\$')
    n = int(subprocess.run(cmd + ' | wc -l', shell=True, capture_output=True, text=True).stdout.strip() or 0)
    p = c['counts'][r['name']]
    ok = n == p['tag_lines'] == p['parsed']
    res['rules'][r['name']] = {'grep': n, 'tag_lines': p['tag_lines'], 'parsed': p['parsed'], 'ok': ok}
    res['ok'] &= ok
res['unmatched_c3live_lines'] = c.get('unmatched_c3live_lines', 0)
res['unmatched_by_shape'] = c.get('unmatched_by_shape', {})
res['ok'] &= res['unmatched_c3live_lines'] == 0
json.dump(res, open(out, 'w'), indent=1)
print(json.dumps({'ok': res['ok'], 'bad': [k for k, v in res['rules'].items() if not v['ok']], 'unmatched': res['unmatched_c3live_lines']}))
PY
rm -rf $TMP
