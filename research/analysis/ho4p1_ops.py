#!/usr/bin/env python3
"""HO4-P1 (ADDENDUM-6 af6d6c94): thao tac Kaggle. jards | cfg <tag> <kind> | push <cfg.json> | oipush <tag> | active
kind: det (lat DEV P3-DET, = cfg ho4-dev-x tru jar/universe/closes) | q1 | q2 | q3 (2026, §6.5)."""
import json, logging, os, shutil, subprocess, sys
import pandas as pd
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("ho4p1")
A = "/home/ubuntu/src/BinanceFuturesJava/research/analysis"
sys.path.insert(0, A)
W = "/home/ubuntu/claude_master/1011/ho4p1"
JAR = "/home/ubuntu/claude_master/1011/ho4race_wt/target/binance-java-sdk-1.2.4.jar"
JAR_SHA = "99c5f040c9295a610fe815e7c6759ccfccbd1cca370dcfc3bcb935b33ec3a2fb"
BASE = "/home/ubuntu/claude_master/1010/ho4/cfg_devx.json"


def jards():
    from kaggle.api.kaggle_api_extended import KaggleApi
    d = W + "/stage/ho4p1-jar-exp"
    shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    os.link(JAR, d + "/sim.jar")
    sha = subprocess.run(["sha256sum", d + "/sim.jar"], capture_output=True, text=True).stdout.split()[0]
    assert sha == JAR_SHA, sha
    json.dump({"sim.jar_sha256": sha, "git": "0594986e"}, open(d + "/JAR_SHA.json", "w"))
    json.dump({"title": "ho4p1-jar-exp", "id": "chuyendinh/ho4p1-jar-exp", "licenses": [{"name": "CC0-1.0"}]},
              open(d + "/dataset-metadata.json", "w"))
    a = KaggleApi(); a.authenticate()
    a.dataset_create_new(d, public=False, quiet=True, dir_mode="skip")
    log.info("CREATED ho4p1-jar-exp sha %s", sha)


def T(name, cls, args, out, env=None, cfg=None, post=None, extra=None):
    t = {"name": name, "cls": cls, "args": args, "mkdirs": ["@OUT/" + out] if out else [], "out_glob": (out + "/*") if out else name}
    if env: t["env"] = env
    if cfg: t["cfg"] = cfg
    if post: t["post"] = post
    t.update(extra or {})
    return t


GATE = "com.binance.chuyennd.ai_ml.features.export.gate.ExportGateDataset"
T1 = "com.binance.chuyennd.ai_ml.features.export.fundingv2.ExportFeaturesForPythonTool"
LAB = "com.binance.chuyennd.ai_ml.features.export.ExportFundingLabel"
MKT = "com.binance.chuyennd.research.ExportMarketData2File"
LENV = {"LABEL_THREADS": "4", "LABEL_STEP_MIN": "15"}
# kind -> (months, days, ingest, fund_months, mkt TIME_RUN, gate args, [(t1/lab start,end)], S)
SPEC = {
    "q1": (["2025-12", "2026-01", "2026-02", "2026-03", "2026-04"], [], ["20251201", "20260403"],
           ["2025-11", "2025-12", "2026-01", "2026-02", "2026-03", "2026-04"], "20251201", ["20251220", "20260401"],
           [("20251231", "20260401")], [1767200400000, 1775005200000]),
    "q2": (["2026-03", "2026-04", "2026-05", "2026-06", "2026-07"], [], ["20260301", "20260703"],
           ["2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07"], "20260301", ["20260320", "20260701"],
           [("20260401", "20260701")], [1775005200000, 1782838800000]),
    "q3": (["2026-06", "2026-07", "2026-08", "2026-09"], ["2026-10-01", "2026-10-02", "2026-10-03"], ["20260601", "20261003"],
           ["2026-05", "2026-06", "2026-07", "2026-08", "2026-09"], "20260601", ["20260620", "20261001"],
           [("20260701", "20261001")], [1782838800000, 1790787600000]),
}


def ms7(d):
    """yyyymmdd 00:00 +07 -> epoch ms."""
    import datetime
    return int(datetime.datetime.strptime(d + "+0700", "%Y%m%d%z").timestamp() * 1000)


SQ = {"q1": ("20260101", "20260401"), "q2": ("20260401", "20260701"), "q3": ("20260701", "20261001")}


def cfg(tag, kind):
    c = json.load(open(BASE))
    c["tag"] = tag
    c["jar_ds"], c["jar_sha"] = "ho4p1-jar-exp", JAR_SHA
    mp = pd.read_csv("/home/ubuntu/claudedata/oi/symbol_map.csv")
    c["closes_map"] = {r.symbol: int(r.symId) for r in mp.itertuples()}
    assert set(c["mapper"]) == set(c["closes_map"]), "mapper != symbol_map 863"
    c["tail_min"] = 1440
    c["days"] = []
    if kind != "det":
        months, days, ingest, fm, tr, ga, tl, _ = SPEC[kind]
        c.update(months=months, days=days, ingest=ingest, fund_months=fm, S=[ms7(SQ[kind][0]), ms7(SQ[kind][1])])
        tasks = [T("mkt", MKT, [], None, cfg={"TIME_RUN": tr}, post="market", extra={"out_glob": "market_rebuilt.bin", "timeout_s": 7200}),
                 T("gate", GATE, [ga[0], ga[1], "@OUT/gate/gate.csv.gz"], "gate")]
        for a, b in tl:
            tasks.append(T("t1", T1, [a, b, "@OUT/t1/"], "t1", env={"FF_UNFILTERED": "1"}))
            tasks.append(T("lab", LAB, [a, b, "@OUT/lab/funding_label.csv"], "lab", env=dict(LENV)))
        c["tasks"] = tasks
    else:
        assert c["S"] == [1751302800000, 1767200400000] and c["ingest"] == ["20250601", "20251231"]
    p = W + "/cfg_%s.json" % tag
    json.dump(c, open(p, "w"), indent=1)
    log.info("CFG %s kind=%s S=%s ingest=%s tasks=%s", p, kind, c["S"], c["ingest"], [(t["name"], t["args"]) for t in c["tasks"]])
    return p


def push(p):
    import ho4p1_exp_kernel as E
    E.submit(p)


def oipush(tag):
    sys.argv = ["x", "submit", tag]
    import ho4p1_oi_kernel as O
    O.submit(tag)


def active():
    import ho4p1_exp_kernel as E
    log.info("ACTIVE %s", E.active())


if __name__ == "__main__":
    a = sys.argv[1]
    if a == "jards":
        jards()
    elif a == "cfg":
        cfg(sys.argv[2], sys.argv[3])
    elif a == "push":
        push(sys.argv[2])
    elif a == "oipush":
        oipush(sys.argv[2])
    elif a == "active":
        active()
