#!/usr/bin/env python3
"""HO3b mo ta sau cong 4 FAIL (KHONG sua, KHONG chay them kernel): (1) doan DEV (start < 2026-01-01) printDone moi == ho26;
(2) ngay lech dau tien + trung theo thang H1; (3) thuoc tham chieu: cung thuoc giua ho26 s42 va 7 seed khac cung cau hinh
(nhieu model p15) — de MASTER doc do chat cua nguong 95%/5%. Chi dem/ty le."""
import json, sys
sys.path.insert(0, "/home/ubuntu/claude_master/1003/ho3b")
import ho3b_mk_driver as D
A, B = "20260101 00:00", "20260701 00:00"


def match(n, o):
    nw = n[(n.st >= A) & (n.st < B)]; ow = o[(o.st >= A) & (o.st < B)]
    tn, to = D.tmin(nw.st), D.tmin(ow.st)
    byso, used, mt = {}, set(), []
    for i, (s, t) in enumerate(zip(ow.sym.tolist(), to.tolist())):
        byso.setdefault(s, []).append((t, i))
    for s, t, stt in sorted(zip(nw.sym.tolist(), tn.tolist(), nw.st.tolist()), key=lambda x: x[1]):
        hit = False
        for (t2, i) in byso.get(s, []):
            if i not in used and abs(t2 - t) <= 1:
                used.add(i); hit = True; break
        mt.append((stt[:6], hit))
    pn = float(n[(n.en >= A) & (n.en < B)].pnl.sum()); po = float(o[(o.en >= A) & (o.en < B)].pnl.sum())
    bym = {}
    for m, h in mt:
        x = bym.setdefault(m, [0, 0]); x[0] += 1; x[1] += int(h)
    return dict(n_new=len(nw), n_ref=len(ow), n_match=len(used), match_rate=len(used) / max(len(nw), len(ow), 1),
                rel_dpnl=abs(pn - po) / abs(po) if po else None, by_month_new_matched={k: "%d/%d" % (v[1], v[0]) for k, v in sorted(bym.items())})


res = {}
for tag, (_, ref) in D.SPEC.items():
    n, o = D.load_pd(tag), D.load_pd(ref)
    dn, do = n[n.st < A], o[o.st < A]
    cols = [c for c in n.columns if c not in ("st", "en")]
    same = len(dn) == len(do) and (dn[cols].astype(str).values == do[cols].astype(str).values).all()
    first = None
    ns, os_ = n[n.st >= A].reset_index(drop=True), o[o.st >= A].reset_index(drop=True)
    for i in range(min(len(ns), len(os_))):
        if ns.sym[i] != os_.sym[i] or ns.st[i] != os_.st[i]:
            first = ns.st[i] if ns.st[i] < os_.st[i] else os_.st[i]; break
    r = dict(dev_rows_equal=bool(same), n_dev=len(dn), first_divergence_start=first, gate=match(n, o))
    cfg = ref.split("-")[1]
    r["ref_seed_band"] = {s: match(D.load_pd("ho26-%s-s-s%d" % (cfg, s)), o) for s in (7, 13, 21, 99, 123, 777, 2024)}
    for s in r["ref_seed_band"].values():
        s.pop("by_month_new_matched")
    res[tag] = r
json.dump(res, open("/home/ubuntu/claude_master/1003/ho3b/mk/gate4_diag.json", "w"), indent=1)
print(json.dumps(res, indent=1))
