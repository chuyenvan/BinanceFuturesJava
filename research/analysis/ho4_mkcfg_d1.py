#!/usr/bin/env python3
"""HO4-P3 CHAN DOAN D1 (khong phai cong): cung kernel exporter nhung ticker = file DEV (wfo-ticker-2025h1/h2) va
funding_data = ban sao local DEV => do tinh tat dinh cua cong cu goc tren Kaggle vs DEV (tach khoi khac biet du lieu Vision)."""
import json, sys
c = json.load(open("/home/ubuntu/claude_master/1010/ho4/cfg_devx.json"))
c.update(tag="ho4-dev-d1", dev_ticker_ds=["wfo-ticker-2025h1", "wfo-ticker-2025h2"], funding_local=True)
json.dump(c, open(sys.argv[1], "w"), indent=1)
