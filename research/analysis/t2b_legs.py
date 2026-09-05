"""T2b — do rate + PnL tach theo LEG LEVEL tu printDone.csv.

Leg index duoc tai lap bang cach gom cum theo (sym, end): mergeOrder gop moi leg cua mot coin
thanh MOT vi the, nen moi leg trong cum dong cung mot moc `end`. Trong cum, sap theo `start`
=> leg 0 = leg dau, leg 1+ = DCA. Khong co cot leg index trong file goc.
"""
import csv, sys, logging, collections, math, random
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
LOG = logging.getLogger("t2b")

def load(tag, base="/home/ubuntu/java/devrun"):
    p = f"{base}/{tag}/storage/printDone.csv"
    rows = []
    with open(p) as f:
        for r in csv.DictReader(f):
            if not r.get("sym"): continue
            try:
                r["profit"] = float(r["profit"]); r["margin"] = float(r["margin"])
                r["pnl"] = float(r["pnl"])
            except (TypeError, ValueError):
                continue
            rows.append(r)
    # leg index trong cum (sym, end)
    cl = collections.defaultdict(list)
    for r in rows: cl[(r["sym"], r["end"])].append(r)
    for k, g in cl.items():
        g.sort(key=lambda x: x["start"])
        for i, r in enumerate(g): r["leg"] = i; r["clen"] = len(g)
    return rows

def rates(rows):
    n = len(rows)
    if n == 0: return {}
    st = collections.Counter(r["status"] for r in rows)
    sl = [r for r in rows if r["status"] == "STOP_LOSS_DONE"]
    sm = [r for r in rows if r["status"] == "STOP_MARKET_DONE"]
    l1 = [r for r in rows if r["leg"] == 0]
    l2 = [r for r in rows if r["leg"] >= 1]
    m = lambda a, k: (sum(x[k] for x in a) / len(a)) if a else float("nan")
    return dict(n=n, TSloss=100.0*len(sl)/n, win=100.0*sum(1 for r in rows if r["profit"]>0)/n,
        mSM=m(sm,"profit"), mSL=m(sl,"profit"), mP=m(rows,"profit"),
        mMargin=m(rows,"margin"), mMargin_l1=m(l1,"margin"), totMargin=sum(r["margin"] for r in rows),
        n_l1=len(l1), n_l2=len(l2), pnl_l1=sum(r["pnl"] for r in l1), pnl_l2=sum(r["pnl"] for r in l2),
        mprofit_l1=m(l1,"profit"), mprofit_l2=m(l2,"profit"), pnl_tot=sum(r["pnl"] for r in rows),
        status=dict(st), level=dict(collections.Counter(r["level"] for r in rows)),
        legdist=dict(collections.Counter(r["leg"] for r in rows)))

def boot(a, b, key, B=4000, blk_h=72, infl=1.21, seed=7):
    """block-bootstrap 72h x1.21, hai mau doc lap (khong ghep cap)."""
    rnd = random.Random(seed)
    def blocks(rows):
        d = collections.defaultdict(list)
        for r in rows:
            t = r["start"][:8] + r["start"][9:11]
            d[t[:8] + str(int(t[8:10]) // blk_h)].append(r)
        return list(d.values())
    ba, bb = blocks(a), blocks(b)
    ds = []
    for _ in range(B):
        sa = [x for _ in ba for x in rnd.choice(ba)]
        sb = [x for _ in bb for x in rnd.choice(bb)]
        ra, rb = rates(sa), rates(sb)
        if ra and rb and not math.isnan(ra.get(key, float("nan"))) and not math.isnan(rb.get(key, float("nan"))):
            ds.append(ra[key] - rb[key])
    ds.sort()
    lo, hi = ds[int(0.025*len(ds))], ds[int(0.975*len(ds))]
    c = 0.5*(lo+hi); h = 0.5*(hi-lo)*infl
    return c-h, c+h

if __name__ == "__main__":
    for tag in sys.argv[1:]:
        r = rates(load(tag))
        LOG.info("== %s ==", tag)
        for k, v in r.items(): LOG.info("  %-12s %s", k, round(v,4) if isinstance(v,float) else v)
