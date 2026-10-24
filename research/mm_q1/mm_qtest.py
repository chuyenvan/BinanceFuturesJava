"""Pre-prereg QUALITY-ONLY test (no fill sim / no markout): timing, memory, book quality."""
import sys, time, resource, json
sys.path.insert(0, "/home/ubuntu/claude_master/vz_e1_wt/research/mm_q1")
import mm_core as C
h0 = int(sys.argv[1]); syms = sys.argv[2:]
for s in syms:
    t = time.time()
    D = C.load_d(s, h0); nob, ntr = D["nob"], D["ntr"]
    t1 = time.time()
    if D["ob"] is None or D["tr"] is None:
        print(s, "MISSING"); continue
    info, S = C.replay(D)
    t2 = time.time()
    q = C.quality(h0, info, S)
    r, why = C.kline_r(s, h0)
    print(s, f"dl={t1-t:.1f}s replay={t2-t1:.1f}s wireMB={(nob+ntr)/1e6:.1f} maxrssMB={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024:.0f}", json.dumps({**info, **q, "r1h": r, "kl": why}))
