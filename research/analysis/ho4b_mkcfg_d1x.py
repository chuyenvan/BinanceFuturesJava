#!/usr/bin/env python3
"""HO4-P0b Q1(iii): cfg kernel ho4b-d1x — nhu D1 (ticker DEV + funding local) nhung BO 10 symbol chi co trong file ticker DEV
ma store Aerospike khong co (DGB, FTT, GLMR, IDEX, MDT, RAD, RAY, SC, STRAX, WAVES — do ho4b_tkas 2025-07-15/10-10).
Cung cua so voi ho4b-det de quy % lech ve nguyen nhan universe. Usage: ho4b_mkcfg_d1x.py <out.json>"""
import json, sys
c = json.load(open("/home/ubuntu/claude_master/1011/ho4b/cfg_det.json"))
keep = {"mkt1", "g1", "t1", "l1"}
c["tasks"] = [t for t in c["tasks"] if t["name"] in keep]
c.update(tag="ho4b-d1x", drop_syms=["DGBUSDT", "FTTUSDT", "GLMRUSDT", "IDEXUSDT", "MDTUSDT", "RADUSDT", "RAYUSDT", "SCUSDT",
                                    "STRAXUSDT", "WAVESUSDT"])
json.dump(c, open(sys.argv[1], "w"), indent=1)
