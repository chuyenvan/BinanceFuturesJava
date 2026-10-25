#!/usr/bin/env python3
"""[V12 SAFE] chay day_harness.main (parity_v11 OFFLINE) voi jar tuy chon vao thu muc RIENG — KHONG sua harness chinh thuc.
argv: DAY JAR OUTDIR [SHARE_CACHE_FROM_DIR]
Chi monkeypatch 2 bien module: CPE (classpath: stubcls + cls chinh thuc + JAR) va RUN (thu muc ghi). WORK (segs.json),
Vision, univ, mapper, funding: CHI DOC tu ~/claude_master/parity_v11w."""
import os
import sys

DAY, JAR, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
SHARE = sys.argv[4] if len(sys.argv) > 4 else None
os.environ["PV_DAY"] = DAY
os.environ.pop("PV_WORK", None)
R = os.path.expanduser("~/claude_master/vz_e1_wt/research/parity_v11")
sys.path.insert(0, R + "/py")
import day_harness as dh  # noqa: E402

B = os.path.expanduser("~/claude_master/parity_v11w/build")
assert os.path.abspath(OUT).startswith(os.path.expanduser("~/claude_master/v12/")), OUT
dh.CPE = {"CP_OFF": B + "/stubcls:" + B + "/cls:" + JAR, "CP_NOSTUB": B + "/cls:" + JAR}
dh.RUN = OUT
os.makedirs(OUT, exist_ok=True)
if SHARE:
    _orig = dh.build_cache

    def build_cache(d, uni, frm, to):
        name = "cache_%d_%d.ser.gz" % (frm, to)
        src = os.path.join(SHARE, name)
        assert os.path.exists(src), src
        if not os.path.exists(os.path.join(d, name)):
            os.symlink(src, os.path.join(d, name))
        open(d + "/cache_build.log", "w").write("shared from %s\nshared\n" % src)
        return name
    dh.build_cache = build_cache
print("RUN=", dh.RUN, "CP_OFF=", dh.CPE["CP_OFF"], "WORK=", dh.WORK)
dh.main()
