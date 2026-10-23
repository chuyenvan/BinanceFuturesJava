import os
p = os.path.expanduser("~/claude_master/vz_e1_wt/research/liqx_s0/v2_indep.py")
s = open(p).read()
old_loop = s[s.index("        qv = {}; close = {}"):s.index("        uni = [s for s, _ in")]
new_loop = '''        # RUN 2 fix (V2 own bug): window [D-30d, D) can reach 2 months back (e.g. 2022-03-01 -> 2022-01-30); read 3 files.
        qv = {}; close = {}
        p2y, p2m = (py, pm - 1) if pm > 1 else (py - 1, 12)
        for (yy, mm) in ((p2y, p2m), (py, pm), (y, m)):
            if not os.path.exists(KL % (yy, mm)):
                continue
            t = pq.read_table(KL % (yy, mm), columns=["ts", "sym", "quote_volume", "close"])
            ts = t.column("ts")
            w = pc.and_(pc.greater_equal(ts, D - 30 * 86400000), pc.less(ts, D))
            agg = t.filter(w).select(["sym", "quote_volume"]).group_by("sym").aggregate([("quote_volume", "sum")]).to_pydict()
            for s_, v in zip(agg["sym"], agg["quote_volume_sum"]):
                qv[s_] = qv.get(s_, 0.0) + v
            w2 = pc.and_(pc.greater_equal(ts, D - 6 * MIN), pc.less(ts, D + 86400000))
            tt = t.filter(w2).to_pydict()
            for s_, a, b in zip(tt["sym"], tt["ts"], tt["close"]):
                close[(s_, int(a))] = b
'''
s = s.replace(old_loop, new_loop)
open(p, "w").write(s); print("ok")
