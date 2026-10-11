#!/usr/bin/env python3
"""HO4-P0b Q1(i): cfg kernel ho4b-det — dau vao DEV (ticker wfo-ticker-2025h2 + funding local), moi exporter chay 2 lan
tham so y het (bat dinh), gate them 1 lan khoi dau som hon (phu thuoc diem bat dau), round-trip ticker DEV -> Aerospike ->
ExportTickerDaily (do trung thuc nap). Cua so 2025-09-01..10-31 (DEV). Usage: ho4b_mkcfg_det.py <out.json>"""
import json, sys
c = json.load(open("/home/ubuntu/claude_master/1010/ho4/cfg_devx.json"))
T1 = "com.binance.chuyennd.ai_ml.features.export.fundingv2.ExportFeaturesForPythonTool"
LB = "com.binance.chuyennd.ai_ml.features.export.ExportFundingLabel"
GT = "com.binance.chuyennd.ai_ml.features.export.gate.ExportGateDataset"
MK = "com.binance.chuyennd.research.ExportMarketData2File"
tasks = [dict(name="rt", cls="com.binance.chuyennd.ai_ml.hpo.kaggle.ExportTickerDaily", args=["20251010", "20251013", "@OUT/rt/"],
              mkdirs=["@OUT/rt"], post="tk_rt", out_glob="rt/*")]
for i in (1, 2):
    tasks.append(dict(name="mkt%d" % i, cls=MK, args=[], cfg={"TIME_RUN": "20250901"}, pre="truncate_market", post="market",
                      dump="mkt%d.bin" % i, mkey="_%d" % i, out_glob="mkt%d.bin" % i, timeout_s=3600))
for i in (1, 2):
    tasks.append(dict(name="g%d" % i, cls=GT, args=["20250925", "20251016", "@OUT/g%d/gate.csv.gz" % i], mkdirs=["@OUT/g%d" % i], out_glob="g%d/*" % i))
tasks.append(dict(name="g3", cls=GT, args=["20250905", "20251016", "@OUT/g3/gate.csv.gz"], mkdirs=["@OUT/g3"], out_glob="g3/*"))
for i in (1, 2):
    tasks.append(dict(name="t%d" % i, cls=T1, args=["20251001", "20251016", "@OUT/t%d/" % i], env={"FF_UNFILTERED": "1"},
                      mkdirs=["@OUT/t%d" % i], out_glob="t%d/*" % i))
for i in (1, 2):
    tasks.append(dict(name="l%d" % i, cls=LB, args=["20251001", "20251012", "@OUT/l%d/funding_label.csv" % i],
                      env={"LABEL_THREADS": "4", "LABEL_STEP_MIN": "15"}, mkdirs=["@OUT/l%d" % i], out_glob="l%d/*" % i))
c.update(tag="ho4b-det", dev_ticker_ds=["wfo-ticker-2025h2"], funding_local=True, ingest=["20250901", "20251031"],
         fund_months=["2025-08", "2025-09", "2025-10"], tasks=tasks)
json.dump(c, open(sys.argv[1], "w"), indent=1)
