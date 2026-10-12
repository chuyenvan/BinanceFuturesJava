#!/usr/bin/env python3
"""BCAST (PREREG_BACKCAST_RESERVOIR 596c1ef8): sinh research/analysis/bcast_exp_kernel.py tu ho4p1_exp_kernel.py (thay chuoi co assert)
+ 2 cfg exporter bcast-x20-a / bcast-x20-b (giong het nhau tru tag) tu cfg_ho4p1-x26-q1.json.
Chi doi: WD, nhan prereg, chinh sach slot (BCAST <= 1 kernel, tai khoan < 2). Logic exporter giu nguyen.
Usage: python3 bcast_mkexp.py"""
import json, logging, sys
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("bcast_mk")
A = "/home/ubuntu/src/BinanceFuturesJava/research/analysis/"
W = "/home/ubuntu/claude_master/1012/bcast"
s = open(A + "ho4p1_exp_kernel.py").read()
R = [('WD = "/home/ubuntu/claude_master/1011/ho4p1/kaggle"', 'WD = "/home/ubuntu/claude_master/1012/bcast/kaggle"'),
     ('RES = dict(tag=CFG["tag"], prereg="ADDENDUM-6", steps={}, tasks=[])',
      'RES = dict(tag=CFG["tag"], prereg="BCAST 596c1ef8 (exporter ho4p1)", steps={}, tasks=[])'),
     ('''    act = active()
    if len(act) >= 2:''', '''    act = active()
    if len(act) >= 2 or any("/bcast-" in x for x in act):''')]
for a, b in R:
    assert s.count(a) == 1, a[:70]
    s = s.replace(a, b)
s = s.replace('"""HO4-P1 (ADDENDUM-6; sinh boi ho4p1_mkexp.py', '"""BCAST (sinh boi bcast_mkexp.py tu ho4p1_exp_kernel.py). HO4-P1 (ADDENDUM-6; sinh boi ho4p1_mkexp.py', 1)
compile(s, "bcast_exp_kernel", "exec")
open(A + "bcast_exp_kernel.py", "w").write(s)
c = json.load(open("/home/ubuntu/claude_master/1011/ho4p1/cfg_ho4p1-x26-q1.json"))
months = ["2020-%02d" % m for m in range(1, 13)] + ["2021-01"]
c.update(S=[1577811600000, 1609434000000], months=months, fund_months=months, ingest=["20200101", "20210103"], days=[])
c["cfg_override"]["TIME_RUN"] = "20200101"
c["tasks"] = [
    dict(name="mkt", cls="com.binance.chuyennd.research.ExportMarketData2File", args=[], mkdirs=[], out_glob="market_rebuilt.bin",
         cfg={"TIME_RUN": "20200101"}, post="market", timeout_s=7200),
    dict(name="gate", cls="com.binance.chuyennd.ai_ml.features.export.gate.ExportGateDataset",
         args=["20200101", "20210102", "@OUT/gate/gate.csv.gz"], mkdirs=["@OUT/gate"], out_glob="gate/*"),
    dict(name="t1", cls="com.binance.chuyennd.ai_ml.features.export.fundingv2.ExportFeaturesForPythonTool",
         args=["20200101", "20210102", "@OUT/t1/"], mkdirs=["@OUT/t1"], out_glob="t1/*", env={"FF_UNFILTERED": "1"}),
    dict(name="lab", cls="com.binance.chuyennd.ai_ml.features.export.ExportFundingLabel",
         args=["20200101", "20210104", "@OUT/lab/funding_label.csv"], mkdirs=["@OUT/lab"], out_glob="lab/*",
         env={"LABEL_THREADS": "4", "LABEL_STEP_MIN": "15"})]
assert "LENDUSDT" not in c["mapper"] and "BTCSTUSDT" not in c["mapper"] and len(c["mapper"]) == 863
for tag in ("bcast-x20-a", "bcast-x20-b"):
    c["tag"] = tag
    json.dump(c, open(W + "/cfg_%s.json" % tag, "w"), indent=1)
log.info("MK_OK bcast_exp_kernel.py + cfg a/b (months %s..%s, ingest %s)", months[0], months[-1], c["ingest"])
