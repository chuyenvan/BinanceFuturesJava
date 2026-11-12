"""Them arm P0 (A0 chay lai, G-P0) vao r1_a3_driver.py."""
import logging
logging.basicConfig(level=logging.INFO)
fn = "r1_a3_driver.py"
s = open(fn).read()
rep = [
 ('def build(seed):\n    ks = GA.ks_mod()\n    tag = "r1-a3-" + seed.lower()\n',
  'def build(seed, arm="A3"):\n    ks = GA.ks_mod()\n    tag = ("r1-a3-" if arm == "A3" else "r1-p0-") + seed.lower()\n'),
 ('           "a3_ds": A3_DS, "moc21_ds": MOC21_DS, "want_a3_sha": a3_sha()}\n    dss = [ks.USER + "/" + GA.BUNDLE] + ks.TICKER_DS + [ks.USER + "/" + JAR_DS, ks.USER + "/" + MOC21_DS,\n                                                         ks.USER + "/" + A3_DS]\n',
  '           "a3_ds": A3_DS, "moc21_ds": MOC21_DS, "want_a3_sha": a3_sha()}\n    dss = [ks.USER + "/" + GA.BUNDLE] + ks.TICKER_DS + [ks.USER + "/" + JAR_DS, ks.USER + "/" + MOC21_DS,\n                                                         ks.USER + "/" + A3_DS]\n    if arm == "P0":  # G-P0: A0 = tsx-x14 nguyen ban (A3_BLOCK bi bo qua vi khong co a3_ds)\n        for _k in ("a3_ds", "moc21_ds", "want_a3_sha"):\n            cfg.pop(_k)\n        dss = [ks.USER + "/" + GA.BUNDLE] + ks.TICKER_DS + [ks.USER + "/" + JAR_DS]\n'),
 ('def check(seed):\n    """So cau hinh voi run tham chieu tsx-x14-<seed> (overrides, jar)."""\n    ks, folder, ref, cfg = build(seed)\n',
  'def check(seed, arm="A3"):\n    """So cau hinh voi run tham chieu tsx-x14-<seed> (overrides, jar)."""\n    ks, folder, ref, cfg = build(seed, arm)\n'),
 ('def push(seed):\n    assert check(seed), "overrides khac run tham chieu -> DUNG"\n    ks, folder, ref, cfg = build(seed)\n',
  'def push(seed, arm="A3"):\n    assert check(seed, arm), "overrides khac run tham chieu -> DUNG"\n    ks, folder, ref, cfg = build(seed, arm)\n'),
 ('    {"upload": lambda: upload(), "check": lambda: check(a.seed), "push": lambda: push(a.seed)}[a.cmd]()',
  '    {"upload": lambda: upload(), "check": lambda: check(a.seed), "push": lambda: push(a.seed),\n     "check_p0": lambda: check(a.seed, "P0"), "push_p0": lambda: push(a.seed, "P0")}[a.cmd]()'),
]
for o, n in rep:
    assert s.count(o) == 1, o[:80]
    s = s.replace(o, n)
open(fn, "w").write(s)
logging.info("patched")
