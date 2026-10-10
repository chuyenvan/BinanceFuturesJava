#!/usr/bin/env python3
"""KDOSE D1 kiem phu: ti le o loi T5-T6 tren DUNG mau 170 symbol KDIV (kdiv_syms.json) de doi chieu 21,05% / 18,65% / 27,71%."""
import json, logging, sys
import numpy as np
sys.path.insert(0, "/home/ubuntu/claude_master/1010/kdose")
import kdose_data as KD

log = KD.log
P, names = KD.load_ticker()
z = np.load(KD.WD + "/kdose_err.npz")
zn = list(z["names"])
cur = {s: i for i, s in enumerate(names)}
perm = np.array([cur[s] for s in zn])
si, mi, ms = perm[z["si"].astype(np.int64)], z["mi"].astype(np.int64), z["msk"]
g = (mi >= KD.IG0) & (mi < KD.IW1)
N = np.isfinite(P[:, 3, KD.IG0:KD.IW1]).sum(1)
E = np.bincount(si[g], minlength=len(names))
EC = np.bincount(si[g & ((ms >> 3) & 1).astype(bool)], minlength=len(names))
ks = json.load(open("/home/ubuntu/claude_master/1003/kdiv/kdiv_syms.json"))
out = {}
for lab in ("all", "ho26", "top50"):
    ix = np.array([cur[s] for s in ks[lab] if s in cur])
    out[lab] = dict(nsym=int(len(ix)), cells=int(N[ix].sum()), err_pct=100.0 * E[ix].sum() / N[ix].sum(),
                    close_pct=100.0 * EC[ix].sum() / N[ix].sum())
out["universe"] = dict(nsym=len(names), cells=int(N.sum()), err_pct=100.0 * E.sum() / N.sum(),
                       close_pct=100.0 * EC.sum() / N.sum())
json.dump(out, open(KD.WD + "/kdose_chk170.json", "w"), indent=1)
log.info("CHK170 %s", json.dumps(out))
