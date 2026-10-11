#!/usr/bin/env python3
"""HO4-P0b Q1: cfg kernel ho4b-t1x — nhu d1x (bo 10 symbol chi-file) + market_data_object NAP TU market.bin DEV (loai race
tap phut) ; Tool1 2 lan khoi dau (10-01 nhu DEV, 09-15 som hon) + gate 1 lan => tach phan du Tool1 (phu thuoc lich su/
market) va xac nhan momentum×3 = race. Usage: ho4b_mkcfg_t1x.py <out.json>"""
import json, sys
c = json.load(open("/home/ubuntu/claude_master/1011/ho4b/cfg_d1x.json"))
T1 = "com.binance.chuyennd.ai_ml.features.export.fundingv2.ExportFeaturesForPythonTool"
GT = "com.binance.chuyennd.ai_ml.features.export.gate.ExportGateDataset"
c["tasks"] = [dict(name="g1", cls=GT, args=["20250925", "20251016", "@OUT/g1/gate.csv.gz"], mkdirs=["@OUT/g1"], out_glob="g1/*"),
              dict(name="t1", cls=T1, args=["20251001", "20251016", "@OUT/t1/"], env={"FF_UNFILTERED": "1"}, mkdirs=["@OUT/t1"], out_glob="t1/*"),
              dict(name="t1e", cls=T1, args=["20250915", "20251016", "@OUT/t1e/"], env={"FF_UNFILTERED": "1"}, mkdirs=["@OUT/t1e"], out_glob="t1e/*")]
c.update(tag="ho4b-t1x", market_from_dev=[1756659600000, 1761930000000])
json.dump(c, open(sys.argv[1], "w"), indent=1)
