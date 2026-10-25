#!/usr/bin/env bash
# =============================================================================
# canary_report.sh [thu_muc_phien] — gom bang chung G-CANARY ve ORACLE + tinh tieu chi tong §5 => 1 file txt (KHONG chua key).
#   bash ops/c3live/canary/canary_report.sh                     (phien dang mo: run/canary)
#   bash ops/c3live/canary/canary_report.sh run/canary_done_<TS> (phien da cleanup)
# CHI DOC tren 242. Buoc: (1) tren 242 dem bi mat trong tung file cua phien (gia tri key/secret doc tu keys.env NGAY TREN 242,
#   chi in SO DEM; "signature=", listenKey day du, token Telegram) + dem dong [KILLSW] LATCH tu luc mo phien;
#   (2) chi keo ve Oracle cac file SACH (0 bi mat); (3) python tinh §5 + ket qua tung buoc K -> <LOGDIR>/report_<TS>/canary_report_<TS>.txt
# Dem lenh trung cid: tu journal (CALL_W theo cid) — cong cu CHUA co allOrders (diem mo, A1 doi chieu doc lap tren web/allOrders).
# Ket qua: "KET QUA: DAT|TRUOT" (+ duong dan file txt).
# =============================================================================
. "$(cd "$(dirname "$0")" && pwd)/canary_lib.sh"
cl_init report
SD=${1:-$CDIR}
[[ "$SD" =~ ^run/canary(_done_[0-9_]+)?$ ]] || die "thu muc phien la: $SD (run/canary hoac run/canary_done_<TS>)"
OUT=${REPORT_DIR:-$LOGDIR/report_$TS}
mkdir -p "$OUT/files" || die "khong tao duoc $OUT"
SEC=$($SSH_242 "bash -s -- $A $SD $KEYS_FILE" <<'EOF'
A=$1; D=$2; KF=$3
cd "$A" 2>/dev/null || { echo "ERR=cd"; exit 0; }
[ -d "$D" ] || { echo "ERR=nodir"; exit 0; }
K=""; S=""
if [ -r "$KF" ]; then
  K=$(sed -n 's/^\(export \)\{0,1\}C3_LIVE_API_KEY=//p' "$KF" | head -1 | tr -d "\"' \r")
  S=$(sed -n 's/^\(export \)\{0,1\}C3_LIVE_API_SECRET=//p' "$KF" | head -1 | tr -d "\"' \r")
fi
echo "KEYS_READ=$( [ -n "$K" ] && [ -n "$S" ] && echo 1 || echo 0)"
cnt() { local c; c=$(grep -a -c "$@" 2>/dev/null); echo "${c:-0}"; }
for f in $(find "$D" -maxdepth 1 -type f | sort); do
  k=0; s=0
  [ -n "$K" ] && k=$(cnt -F -f <(printf '%s\n' "$K") "$f")
  [ -n "$S" ] && s=$(cnt -F -f <(printf '%s\n' "$S") "$f")
  g=$(cnt -F 'signature=' "$f")
  l=$(cnt -E '[A-Za-z0-9]{56,}' "$f")
  t=$(cnt -E '[0-9]{8,10}:[A-Za-z0-9_-]{35}' "$f")
  echo "SEC $(basename "$f") $k $s $g $l $t"
done
unset K S
F0=$(ls "$D"/canary_*.jsonl 2>/dev/null | sort | head -1)
B=$(basename "${F0:-x}" | sed -n 's/^canary_\([0-9]\{8\}\)_\([0-9]\{6\}\)_.*/\1\2/p')
if [ -n "$B" ]; then
  L=0
  for f in $(ls logs/full.log* 2>/dev/null); do
    c=$(zcat -f "$f" 2>/dev/null | grep -a '\[KILLSW\] LATCH' | awk -v b="$B" '{d=$1; t=$2; k=substr(d,7,4) substr(d,4,2) substr(d,1,2) substr(t,1,2) substr(t,4,2) substr(t,7,2); if (k >= b) n++} END {print n+0}')
    L=$((L + c))
  done
  echo "LATCH_SINCE=$B $L"
else
  echo "LATCH_SINCE=none -1"
fi
EOF
) || die "khong ssh duoc 242"
echo "$SEC" | grep -q '^ERR=' && die "242: $(echo "$SEC" | grep '^ERR=')"
printf '%s\n' "$SEC" > "$OUT/secret_counts_242.txt"
CLEAN=$(echo "$SEC" | awk '$1=="SEC" && $3==0 && $4==0 && $5==0 && $6==0 && $7==0 {print $2}' | grep -E '^[A-Za-z0-9._-]+$')
DIRTY=$(echo "$SEC" | awk '$1=="SEC" && !($3==0 && $4==0 && $5==0 && $6==0 && $7==0) {print $2}')
[ -n "$DIRTY" ] && say "!! file co bi mat (KHONG keo ve): $(echo $DIRTY)"
if [ -n "$CLEAN" ]; then
  # shellcheck disable=SC2086
  $SSH_242 "cd $A/$SD && tar czf - $(echo $CLEAN)" < /dev/null > "$OUT/files.tgz" || die "khong keo duoc file phien"
  tar xzf "$OUT/files.tgz" -C "$OUT/files" && rm -f "$OUT/files.tgz"
fi
# log script Oracle cua phien (khong bao gio co key): van dem mau bi mat
LOC=0
for f in "$LOGDIR"/*.log; do
  [ -f "$f" ] || continue
  c=$(grep -a -c -E 'signature=|[0-9]{8,10}:[A-Za-z0-9_-]{35}|[A-Za-z0-9]{56,}' "$f" 2>/dev/null); LOC=$((LOC + ${c:-0}))
done
RPT=$OUT/canary_report_$TS.txt
python3 -I - "$OUT/files" "$OUT/secret_counts_242.txt" "$LOC" "$RPT" "$SD" <<'EOF'
import glob, json, os, re, sys
fdir, secf, loc, rpt, sd = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5]
L = []
def p(s=""): L.append(s)
sec = [l.split() for l in open(secf) if l.startswith("SEC ")]
keys_read = any(l.strip() == "KEYS_READ=1" for l in open(secf))
latch = [l.split() for l in open(secf) if l.startswith("LATCH_SINCE=")]
latch_n = int(latch[0][1]) if latch else -1
st = {}
sp = os.path.join(fdir, "canary_state.json")
if os.path.exists(sp):
    st = json.load(open(sp))
steps = st.get("steps") or {}
J = []
for f in sorted(glob.glob(os.path.join(fdir, "canary_*.jsonl"))):
    for line in open(f, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line: continue
        try: J.append(json.loads(line))
        except Exception: pass
REQ = ["K0", "K1", "K2", "K3", "K4", "K5", "K6", "K6b", "K7", "K7b", "K8"]
crit = []
def C(n, name, ok, detail):
    crit.append((n, name, "DAT" if ok else "TRUOT", detail))
# 1. lenh trung cid (journal)
sends, acc, dup4116 = {}, {}, 0
for e in J:
    if e.get("type") != "CALL_W": continue
    api = str(e.get("api", ""))
    if not (api.startswith("newMarketOrder") or api.startswith("newStopMarket")): continue
    cid = e.get("cid")
    sends[cid] = sends.get(cid, 0) + 1
    if e.get("ok") is True: acc[cid] = acc.get(cid, 0) + 1
    if str(e.get("errCode")) == "-4116": dup4116 += 1
dupAcc = {c: n for c, n in acc.items() if n > 1}
dupSend = {c: n for c, n in sends.items() if n > 1}
C(1, "0 lenh trung cid", len(sends) > 0 and not dupAcc and dup4116 == 0,
  "lenh gui=%d cid=%d; cid chap nhan >1 lan=%s; -4116=%d; cid gui >1 lan (tham khao)=%s; nguon: journal (CHUA allOrders)"
  % (sum(sends.values()), len(sends), dupAcc or 0, dup4116, dupSend or 0))
r = {k: (steps.get(k) or {}).get("result") for k in REQ}
def alldat(ks): return all(r.get(k) == "DAT" for k in ks)
C(2, "0 stop mo coi / 0 luc vi the!=0 ma 0 stop", alldat(["K2", "K4", "K5", "K6", "K7", "K7b"]), "do trong buoc K2 K4 K5 K6 K7 K7b")
C(3, "so = san 100%", alldat(["K1", "K6", "K7", "K8"]), "do trong buoc K1 K6 K7 K8 (qty, avg +-1 tick)")
C(4, "0 latch kill-switch ngoai kich ban", latch_n == 0, "dong [KILLSW] LATCH log bot tu luc mo phien = %s" % latch_n)
ws = [e.get("w1m") for e in J if isinstance(e.get("w1m"), (int, float))]
n429 = sum(1 for e in J if e.get("http") in (429, 418))
C(5, "weight < 1200 (50% cua 2400), 0 HTTP 429/418", len(ws) > 0 and max(ws) < 1200 and n429 == 0,
  "max X-MBX-USED-WEIGHT-1M=%s (mau=%d); 429/418=%d" % (max(ws) if ws else "KHONG DO DUOC", len(ws), n429))
s242 = sum(int(x[2]) + int(x[3]) + int(x[4]) + int(x[5]) + int(x[6]) for x in sec)
C(6, "0 bi mat trong log", keys_read and s242 == 0 and loc == 0,
  "242: %d file, tong dem=%d (key doc duoc tren 242=%s); log script Oracle=%d" % (len(sec), s242, keys_read, loc))
k7b = (steps.get("K7b") or {}).get("data") or {}
C(7, "lop chan A/B", alldat(["K6b", "K7b"]),
  "K6b=%s; K7b=%s; (B) symbol chinh=%s ms; (A) lan dau sau chot=%s ms" % (r.get("K6b"), r.get("K7b"), k7b.get("s1.blockedMs"), k7b.get("A.firstSeenAfterCloseMs")))
lat = sorted(e.get("latMs") for e in J if e.get("type") == "CALL_W" and str(e.get("api", "")).startswith("newMarketOrder") and isinstance(e.get("latMs"), (int, float)))
sl = []
def walk(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "streamLatMs" and isinstance(v, (int, float)) and v >= 0: sl.append(v)
            else: walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
walk(steps)
def pp(a): return "p50=%s p100=%s n=%d" % (a[len(a) // 2], a[-1], len(a)) if a else "khong co"
crit.append((8, "do tre leg (thong tin, khong nguong)", "GHI", "gui->response MARKET: %s; FILLED->stream: %s" % (pp(lat), pp(sorted(sl)))))
cost = None
if st: cost = float(st.get("cumFeeStable", 0)) - float(st.get("cumRealized", 0)) - float(st.get("cumFunding", 0))
C(9, "chi phi <= 2 USDT", cost is not None and cost <= 2.0 and not st.get("feeOther"),
  "phi+lo da chot=%s USDT; phi tai san khac=%s; aborted=%s" % (None if cost is None else round(cost, 4), st.get("feeOther"), st.get("aborted")))
C(10, "diem CHUA XAC MINH §7 co ket qua", all(k in steps for k in ["K0", "K1", "K2", "K3", "K4", "K8"]), "xem 'Du lieu tung buoc' (K0 so du, K1 so du/phi, K2 c, K3 ma loi, K4 san tu huy?, K8 so cai)")
allK = alldat(REQ)
okAll = allK and all(c[2] in ("DAT", "GHI") for c in crit)
p("G-CANARY BAO CAO — phien %s (prereg docs/prereg/GCANARY_PREREG.md §5, CHOT MASTER 10-25)" % sd)
p("symbol chinh=%s phu=%s chon luc=%s; tmb0=%s; MO-5 tiem timeout da dung=%s" % (st.get("symMain"), st.get("symAux"), st.get("pickedAtMs"), st.get("tmb0"), st.get("injectTimeoutUsed")))
p("KET QUA TONG: %s" % ("DAT" if okAll else "TRUOT"))
p("")
p("== Buoc K")
for k in REQ:
    s = steps.get(k) or {}
    p("  %-4s %-8s %s" % (k, s.get("result") or "KHONG_CO (=TRUOT)", "; ".join(s.get("fails") or [])[:400]))
p("")
p("== Tieu chi tong §5")
for n, name, v, d in crit:
    p("  %2d. %-45s %-5s %s" % (n, name, v, d))
p("")
p("== Thong tin them")
p("  journal: %d su kien; GUARD_REFUSE=%d; INJECT_TIMEOUT=%d; STEP_REFUSED=%d" % (len(J), sum(1 for e in J if e.get("type") == "GUARD_REFUSE"),
  sum(1 for e in J if e.get("type") == "INJECT_TIMEOUT"), sum(1 for e in J if e.get("type") == "STEP_REFUSED")))
p("  file 242 (ten, key, secret, tham so chu ky, chuoi>=56, token TG):")
for x in sec: p("    %s" % " ".join(x[1:]))
p("")
p("== Du lieu tung buoc (canary_state.json, cat 3000 ky tu/buoc)")
for k in sorted(steps):
    p("  [%s] %s" % (k, json.dumps((steps[k] or {}).get("data"), ensure_ascii=False, sort_keys=True)[:3000]))
txt = "\n".join(L) + "\n"
# chot chan cuoi: moi doan khop mau bi mat trong chinh bao cao => che + TRUOT (ghi ten mau, khong ghi noi dung)
PAT = {"signature": r"signature=[^\s\"',;&]*", "token_tg": r"[0-9]{8,10}:[A-Za-z0-9_-]{35}", "chuoi>=56": r"[A-Za-z0-9]{56,}"}
hit = []
for name, rx in PAT.items():
    txt, n = re.subn(rx, "[CHE:" + name + "]", txt)
    if n: hit.append("%s=%d" % (name, n))
if hit:
    txt = "!! BAO CAO CO DOAN KHOP MAU BI MAT (da che): %s => KET QUA TONG: TRUOT\n" % ", ".join(hit) + txt.replace("KET QUA TONG: DAT", "KET QUA TONG: TRUOT")
    okAll = False
open(rpt, "w", encoding="utf-8").write(txt)
print(txt)
sys.exit(0 if okAll else 3)
EOF
RC=$?
say "Bao cao: $RPT"
say "KET QUA: $( [ $RC = 0 ] && echo DAT || echo TRUOT )"
say "Log: $CL_LOG"
exit $RC
