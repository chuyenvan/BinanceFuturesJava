#!/usr/bin/env bash
# =============================================================================
# gridtest_report.sh - [GRIDTEST] BAO CAO cuoi phien (CHI DOC): bang T1-T10 so bo tu log 242 (tu moc pha A) + so/ledger c3 + doi chieu san
#   qua gl_api242 sub (co che chi-doc da audit: v3/account, positionRisk, openOrders, openAlgoOrders). Ghi $GT_SDIR/GRIDTEST_REPORT_<TS>.md
#   bash gridtest_report.sh            # chay bat ky luc nao sau pha A (ke ca dang chay)
#   T1/T2 so voi prereg: budget leg = 0,0225 x C3_CAPITAL x (1 - U_before/0,6) (+-2 %; tier != 1 => CAN_XEM); T2 bac: ref leg DCA / gia leg0 - 1
#   <= L_i (-1/-2/-3 %). Cac muc khac: so lieu tho + DAT/TRUOT/KHONG_XAY_RA so bo - MASTER chot.
# =============================================================================
. "$(cd "$(dirname "$0")" && pwd)/gridtest_common.sh"
gt_manifest_check "$0" || exit 1
gt_init gridtest_report
TSA=$(gt_sv GT_TS_A); SINCE=$(gt_sv GT_SINCE_A)
[[ "$SINCE" =~ ^[0-9]{14}$ ]] || die "chua co phien gridtest (state thieu GT_SINCE_A)"
OUTF=$GT_SDIR/GRIDTEST_REPORT_$TS.md
R=$(s242in "bash -s -- $A $SINCE" <<'EOF'
A=$1; S=$2; cd "$A" || { echo "ERR=cd"; echo END_R; exit 0; }
F1=""; FK=$(head -n 1 logs/full.log 2>/dev/null | awk '{d=$1;t=$2; print substr(d,7,4) substr(d,4,2) substr(d,1,2) substr(t,1,2) substr(t,4,2) substr(t,7,2)}')
{ [ -z "$FK" ] || [ "$FK" \> "$S" ]; } && F1=logs/full.log.1
grep -ahF -e '[C3-LIVE] SUBMIT' -e '[C3-LIVE-FILL] xac nhan' -e '[C3-LIVE-TRAIL] arm' -e 'c3s-' -e '[C3-LIVE-BOOK] dong cum' -e 'KHAN' \
  -e '[C3-LIVE-ORDER]' -e 'PUSH doi trang thai' -e '[LEGACY] managed' -e 'khoi dong adapter=' -e 'LECH' -e '[C3-LIVE-STREAM]' -e 'DA DONG tren san' $F1 logs/full.log 2>/dev/null \
  | grep -av 'Telegram respon' | awk -v S="$S" '{d=$1;t=$2; k=substr(d,7,4) substr(d,4,2) substr(d,1,2) substr(t,1,2) substr(t,4,2) substr(t,7,2); if (k >= S) print "L " k " " substr($0,1,300)}' \
  | tr -c 'A-Za-z0-9_ .,:;=/()[]+<>#\n-' '_' | tail -n 4000
S_MS=$(date -d "${S:0:4}-${S:4:2}-${S:6:2} ${S:8:2}:${S:10:2}:${S:12:2}" +%s 2>/dev/null)000
tail -n +2 run/c3live_ledger.csv 2>/dev/null | awk -F, -v m="$S_MS" '$11+0 >= m+0 {print "G " $0}'
echo END_R
EOF
) || R="ERR=ssh"
echo "$R" | grep -qx END_R || die "doc log 242 loi/khong tron ven"
API=$(gl_api242 sub) || API="ERR=ssh_api"
echo "$API" | grep -qx END_API || say "!! doc san (gl_api242 sub) khong tron ven - T7/T8 thieu"
{ echo "$R" | grep -E '^(L|G) '; echo "$API" | grep -E '^(TMB|AVAIL|BAL|POS_TOTAL|POS_LIST|ORD_TOTAL|ORD_C3|ALGO_TOTAL|ALGO_C3|ALGO_NONC3|POS_NONC3|POS_C3_MISMATCH|API_OK|KEY_SHA8|MULTI)=' | sed 's/^/A /'
  for k in GT_TS_A GT_TS_B GT_TS_OFF GT_L0_A GT_BRAKE GT_BRAKE_T GT_PHASE; do echo "S $k=$(gt_sv $k)"; done; } \
| python3 -I -c '
import sys, re, time
CAP = 1000.0; LV = [-0.01, -0.02, -0.03]
sub = []; conf = {}; arms = []; stops = []; closes = []; khan = []; ordl = []; push = []; leg = []; start = []; lech = []; strm = []; led = []; A = {}; S = {}
for ln in sys.stdin:
    ln = ln.rstrip("\n")
    if ln.startswith("A "): k, _, v = ln[2:].partition("="); A[k] = v; continue
    if ln.startswith("S "): k, _, v = ln[2:].partition("="); S[k] = v; continue
    if ln.startswith("G "): led.append(ln[2:].split(",")); continue
    if not ln.startswith("L "): continue
    key, body = ln[2:16], ln[17:]
    if "[C3-LIVE] SUBMIT" in body:
        m = dict(re.findall(r"(cid|qty|budget|legIdx|notional|U_before)=([^ ]+)", body)); toks = body.split()
        i = toks.index("SUBMIT") if "SUBMIT" in toks else -1
        m["sym"] = toks[i + 1] if i >= 0 else "?"; m["level"] = toks[i + 2] if i >= 0 else "?"; m["t"] = key; sub.append(m)
    elif "[C3-LIVE-FILL] xac nhan" in body:
        m = re.search(r"xac nhan qua stream (\S+) (\S+) qty=(\S+) avg=(\S+) ref=(\S+)", body)
        if m: conf[m.group(2)] = (m.group(1), float(m.group(3)), float(m.group(4)), float(m.group(5)))
    elif "[C3-LIVE-TRAIL] arm" in body: arms.append(key + " " + body[body.find("arm"):][:120])
    elif "[C3-LIVE-TRAIL]" in body and "stop=" in body and "cid=c3s-" in body: stops.append(key + " " + body[body.find("[C3-LIVE-TRAIL]"):][:140])
    elif "[C3-LIVE-BOOK] dong cum" in body or "DA DONG tren san" in body: closes.append(key + " " + body[body.find("["):][:170])
    elif "KHAN" in body: khan.append(key + " " + body[24:][:170])
    elif "[C3-LIVE-ORDER]" in body and re.search(r"-2019|-4[0-9]{3}|margin|Margin", body): ordl.append(key + " " + body[24:][:170])
    elif "PUSH doi trang thai" in body: push.append(key + " " + body[body.find("PUSH"):][:60])
    elif "[LEGACY] managed" in body: leg.append((key, re.search(r"managed (\d+)", body).group(1) if re.search(r"managed (\d+)", body) else "?"))
    elif "khoi dong adapter=" in body: start.append(key)
    elif "LECH" in body: lech.append(key + " " + body[24:][:150])
    elif "[C3-LIVE-STREAM]" in body: strm.append(key + " " + body[24:][:100])
out = []; P = out.append
P("# GRIDTEST_REPORT (so bo, tu dong) - pha A %s, B %s, OFF %s, pha hien tai %s" % (S.get("GT_TS_A"), S.get("GT_TS_B") or "-", S.get("GT_TS_OFF") or "-", S.get("GT_PHASE")))
P("Nguon: log 242 tu moc pha A + ledger c3 + gl_api242 sub (chi doc). KHONG dung cho quyet dinh tham so chien luoc (prereg muc 8).")
P(""); P("## SUBMIT (%d)" % len(sub)); P("| t | sym | level | legIdx | cid | qty | budget | ky_vong | lech | notional | U_before |"); P("|---|---|---|---|---|---|---|---|---|---|---|")
t1 = []; t2 = []; first = {}
for m in sub:
    try:
        u = float(m.get("U_before", "nan")); b = float(m.get("budget", "nan")); ex = 0.0225 * CAP * (1 - u / 0.6); d = b / ex - 1
    except Exception: ex = float("nan"); d = float("nan")
    li = m.get("legIdx", "?")
    (t1 if li == "0" else t2).append(abs(d) <= 0.02)
    P("| %s | %s | %s | %s | %s | %s | %s | %.3f | %+.2f%% | %s | %s |" % (m["t"], m["sym"], m["level"], li, m.get("cid"), m.get("qty"), m.get("budget"), ex, d * 100, m.get("notional"), m.get("U_before")))
P(""); P("## Bac DCA (ref leg DCA / gia khop leg0 - 1 vs L_i)")
seq_ok = True; lv_ok = True; per = {}
for m in sub:
    per.setdefault(m["sym"], []).append(m)
for s, ms in per.items():
    idx = [int(x.get("legIdx", -1)) for x in ms]
    if idx != list(range(len(idx))) and not (idx and idx[0] == 0 and idx == sorted(idx)): seq_ok = False
    c0 = conf.get(ms[0].get("cid"))
    for x in ms[1:]:
        li = int(x.get("legIdx", 0)); cx = conf.get(x.get("cid"))
        if li > 3 or li < 1: lv_ok = False; P("- %s legIdx %d NGOAI luoi" % (s, li)); continue
        if c0 and cx:
            dr = cx[3] / c0[2] - 1; ok = dr <= LV[li - 1] + 1e-9; lv_ok = lv_ok and ok
            P("- %s leg%d: ref %.8g / leg0 avg %.8g - 1 = %+.3f%% (bac %.0f%%) %s" % (s, li, cx[3], c0[2], dr * 100, LV[li - 1] * 100, "OK" if ok else "NGOAI_BAC"))
        else: P("- %s leg%d: thieu dong xac nhan stream (REST?) - kiem tay" % (s, li))
nconf = sum(1 for m in sub if m.get("cid") in conf)
def v(cond_ok, happened=True): return "KHONG_XAY_RA" if not happened else ("DAT" if cond_ok else "TRUOT/CAN_XEM")
P(""); P("## Bang T1-T10 (so bo)")
P("| T | ket qua | so lieu |"); P("|---|---|---|")
n0 = sum(1 for m in sub if m.get("legIdx") == "0"); nd = len(sub) - n0
P("| T1 leg0 sizing | %s | %d leg0, %d trong +-2%% (tier != 1 => CAN_XEM) |" % (v(all(t1), n0 > 0), n0, sum(t1)))
P("| T2 leg DCA dung bac | %s | %d leg DCA; legIdx tuan tu=%s; bac=%s; budget +-2%%: %d/%d |" % (v(seq_ok and lv_ok and all(t2), nd > 0), nd, seq_ok, lv_ok, sum(t2), len(t2)))
P("| T3 khop that | %s | %d/%d SUBMIT co xac nhan stream (qty/avg vs san: so cid voi userTrades - tay) |" % (v(nconf == len(sub), len(sub) > 0), nconf, len(sub)))
P("| T4 margin BFUSD | %s | %d dong loi margin/-2019/-4xxx; BAL=%s MULTI=%s |" % (v(len(ordl) == 0, len(sub) > 0), len(ordl), A.get("BAL", "?")[:120], A.get("MULTI", "?")))
P("| T5 user stream | %s | %d dong STREAM, %d dong LECH recon |" % (v(len(lech) == 0, len(sub) > 0), len(strm), len(lech)))
P("| T6 trailing/stop | %s | %d arm, %d dong dat stop c3s- |" % (v(len(stops) >= len(arms), len(arms) > 0), len(arms), len(stops)))
fl = A.get("POS_TOTAL") == "0" and A.get("ALGO_C3") == "0"
P("| T7 dong lenh | %s | %d dong dong cum; san bay gio: POS_TOTAL=%s ALGO_C3=%s ORD_C3=%s |" % (v(fl, len(closes) > 0), len(closes), A.get("POS_TOTAL"), A.get("ALGO_C3"), A.get("ORD_C3")))
rp = sum(float(r[7] or 0) for r in led if len(r) > 8); fee = sum(float(r[8] or 0) for r in led if len(r) > 8)
P("| T8 so sach | CAN_XEM | ledger phien: %d cum, realized %.4f, phi %.4f; tmb san bay gio %s (doi chieu: tmb0 truoc pha A + realized - phi + funding) |" % (len(led), rp, fee, A.get("TMB")))
bt = S.get("GT_BRAKE_T") or ""
after = []
if bt:
    kb = time.strftime("%Y%m%d%H%M%S", time.localtime(int(bt)))
    after = [m for m in sub if m["t"] > kb]
P("| T9 kill-switch | %s | phanh=%s; SUBMIT sau phanh=%d |" % (v(len(after) == 0, bool(bt)), S.get("GT_BRAKE") or "-", len(after)))
P("| T10 LEGACY | CAN_XEM | truoc pha A=%s; [LEGACY] managed theo thoi gian: %s |" % (S.get("GT_L0_A"), " ".join("%s:%s" % x for x in leg[-12:])))
P(""); P("## Su kien")
for title, arr in (("Khoi dong JVM", start), ("PUSH", push), ("arm", arms), ("stop c3s-", stops), ("dong cum", closes), ("KHAN", khan), ("loi lenh margin", ordl), ("LECH", lech)):
    P("- %s (%d): %s" % (title, len(arr), "; ".join(arr[-8:]) if arr else "-"))
P("- ledger: " + "; ".join("%s legs=%s reason=%s pnl=%s fee=%s" % (r[0], r[2], r[9], r[7], r[8]) for r in led if len(r) > 9))
P("- san: POS_LIST=%s ORD_TOTAL=%s ALGO_TOTAL=%s ALGO_NONC3=%s POS_NONC3=%s MISMATCH=%s" % (A.get("POS_LIST"), A.get("ORD_TOTAL"), A.get("ALGO_TOTAL"), A.get("ALGO_NONC3"), A.get("POS_NONC3"), A.get("POS_C3_MISMATCH")))
print("\n".join(out))
' > "$OUTF.tmp" || die "tinh bao cao loi"
sed -E "$GT_SED" "$OUTF.tmp" > "$OUTF"; rm -f "$OUTF.tmp"
cat "$OUTF"
say "=== BAO CAO: $OUTF"
