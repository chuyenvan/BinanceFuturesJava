#!/usr/bin/env python3
"""Xuat finalists.json tu ket qua GS wave-1 (PREREG_GS.md muc 9.1 buoc 2).

CHI doc truong devA. TUYET DOI khong doc devB o day: theo muc 9.1, devB chi duoc doc SAU khi
file nay da duoc commit. Script khong sua analyze_wave1.py, chi goi lai ham run() cua no.
"""
import importlib.util, json, logging, sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("gsexp")

BASE = Path("/home/ubuntu/src/BinanceFuturesJava/research/kaggle/gsearch")
IN = "/home/ubuntu/gs/out/gs_wave1_all.jsonl"
OUT = BASE / "finalists.json"


def load_mod(name, path):
    s = importlib.util.spec_from_file_location(name, str(path))
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


aw = load_mod("analyze_wave1_ro", BASE / "analyze_wave1.py")
spec = aw.load_spec(str(BASE / "gen_params.py"))
recs = aw.load_jsonl(IN)
res = aw.run(recs, spec, run_surrogate=False)

by_id = {r["id"]: r for r in recs}
anchor = by_id[-1]
rows = []
for rank, pid in enumerate(res["finalist_ids"], 1):
    r = by_id[pid]
    i = res["valid_ids"].index(pid)
    rows.append({
        "rank": rank,
        "id": pid,
        "NS_devA": round(float(res["NS"][i]), 4),
        "cagr_pct_devA": r["devA"]["cagr_pct"],
        "maxdd_pct_devA": r["devA"]["maxdd_pct"],
        "n_trades_devA": r["n_trades_devA"],
        "equity_end_devA": r["devA"]["equity_end"],
        "params": r["params"],
    })

doc = {
    "prereg": "docs/PREREG_GS.md muc 4 (buoc 1-5) + muc 9.1/9.2",
    "input_jsonl": IN,
    "n_lines_input": len(recs),
    "anchor": {
        "id": -1,
        "equity_final": anchor["equity_final"],
        "cagr_pct_devA": anchor["devA"]["cagr_pct"],
        "maxdd_pct_devA": anchor["devA"]["maxdd_pct"],
        "n_trades_devA": anchor["n_trades_devA"],
        "void": False,
        "note": "equity_final = 60395 DUNG BANG moc tien-dang-ky (PREREG muc 5). Wave khong VOID.",
    },
    "n_sobol_total": res["n_sobol_total"],
    "n_valid": res["n_valid"],
    "exclude_reasons": res["exclude_reasons"],
    "chosen_ns_id": res["chosen_ns_id"],
    "chosen_cagr_id": res["chosen_cagr_id"],
    "raw_top5_ns_ids": res["raw_top5_ids"],
    "finalist_ids": res["finalist_ids"],
    "anchor_percentile": res["anchor_percentile"],
    "finalists": rows,
    "seal": ("File nay duoc COMMIT TRUOC khi doc bat ky so devB nao (PREREG muc 9.1 buoc 2-4). "
             "Moi so trong file chi tu devA (2022-01-01..2023-12-31)."),
}
OUT.write_text(json.dumps(doc, indent=2, sort_keys=False) + "\n")
log.info("WROTE %s (%d finalist)", OUT, len(rows))
