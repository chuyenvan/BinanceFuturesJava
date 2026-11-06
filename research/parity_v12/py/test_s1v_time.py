#!/usr/bin/env python3
"""[ADD13] test S1V cua so theo thoi gian: lien mach => trung bit ban vi tri cu; gio thieu => KDD (khong ra so)."""
import os
import sys
import numpy as np
os.environ.setdefault("PV_DAY", "2026-11-04")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import day_s1v as M  # noqa: E402

H = 3600000
rng = np.random.default_rng(20261106)


def old(th, cv, h):
    idx = np.searchsorted(th, h - H, "right") - 1
    st = max(0, idx - 167)
    r_all = np.full(len(cv), np.nan)
    r_all[1:] = cv[1:] / cv[:-1] - 1
    r = r_all[st:idx + 1]
    r = r[~np.isnan(r)]
    vol = np.nan if (len(r) < M.MINP or len(r) < 2) else float(np.sqrt(((r - r.mean()) ** 2).sum() / (len(r) - 1)))
    mx = M.roll_max(cv, idx, 168, M.MINP)
    dd = np.nan if (np.isnan(mx) or mx == 0) else cv[idx] / mx - 1
    return vol, dd, M.hrs_since_high(th, cv, idx), M.ret(cv, idx, 72), M.ret(cv, idx, 336)


def same(a, b):
    return all((np.isnan(x) and np.isnan(y)) or x == y for x, y in zip(a, b))


ok = []
t0 = 1792195200000
for n in (400, 120, 90):                       # du lich su / niem yet moi (120 h, 90 h)
    th = t0 + np.arange(n) * H
    cv = np.cumprod(1 + rng.normal(0, 0.01, n)) * 10
    for h in (th[-1] + H + 5 * 60000, th[-1] + H + 59 * 60000, th[n // 2] + H + 60000):
        ok.append(same(M.feats_time(th, cv, h), old(th, cv, h)))
# gio thieu giua cua so -> KDD
th = t0 + np.arange(400) * H
cv = np.cumprod(1 + rng.normal(0, 0.01, 400)) * 10
keep = np.ones(400, bool); keep[300:324] = False      # mat 24 gio (nhu 10-28)
th2, cv2 = th[keep], cv[keep]
for h in (th[-1] + H + 60000, th[330] + H + 60000):
    try:
        M.feats_time(th2, cv2, h); ok.append(False)
    except M.KDD:
        ok.append(True)
# gio muc tieu thieu -> KDD (ban cu lay gio truoc do)
keep = np.ones(400, bool); keep[399] = False
try:
    M.feats_time(th[keep], cv[keep], th[399] + H + 60000); ok.append(False)
except M.KDD:
    ok.append(True)
# gio thieu NGOAI moi cua so (truoc T-336h) -> van tinh duoc, khong KDD
keep = np.ones(400, bool); keep[5:10] = False
ok.append(M.feats_time(th[keep], cv[keep], th[-1] + H + 60000) is not None)
print("cases", ok)
print("TEST_S1V_TIME", "PASS" if all(ok) else "FAIL")
