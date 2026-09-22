"""[BRCT50 B9] Sinh CSV regime gate LIEN TUC (top50/MA200/thr50) tu breadth_score_series.csv.
Ban sao breadth_cont_csv.py, CHI doi chuoi breadth all-coin -> top50 (0 doi co che gate).
Format RegimeSchedule: utcDay,dateUTC,breadth_pct,regime,scale,... ; scale (cot idx 4) = gate lien tuc.
Che do lien tuc doc cot idx 4 (SIM_REGIME_GATE_VALUE_COL=4). regime (cot 3) chi de audit/nhi phan.
Causal: gate_top50_ma200 da tinh causal <= t-1 (breadth_robust.py Phan 2, dinh nghia A). Lead-in 30 ngay = gate dau.
"""
import csv, logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
L=logging.getLogger("brct50_csv")
SRC="research/analysis/out/breadth_score_series.csv"
OUT="/home/ubuntu/regime_work/regime_cont_top50.csv"
rows=[]
with open(SRC) as f:
    r=csv.DictReader(f)
    for d in r:
        day=int(d["day_id"]); date=d["date"]
        br=float(d["breadth_score_top50"])
        gate=float(d["gate_top50_ma200"])
        reg="UP" if br>=0.5 else "NOTUP"
        rows.append((day,date,round(br*100,4),reg,round(gate,4)))
rows.sort()
first_day=rows[0][0]; first_gate=rows[0][4]
lead=[(first_day-k, "LEADIN", rows[0][2], rows[0][3], first_gate) for k in range(30,0,-1)]
allr=lead+rows
with open(OUT,"w",newline="") as f:
    w=csv.writer(f)
    w.writerow(["utcDay","dateUTC","breadth_pct","regime","scale","topn_main","ma_window","threshold_pct"])
    for day,date,brp,reg,gate in allr:
        w.writerow([day,date,brp,reg,gate,"top50",200,50.0])
gv=[x[4] for x in rows]
L.info("rows_data=%d lead=%d total=%d first=%s(%d,gate=%.4f) last=%s gate_min=%.4f gate_max=%.4f gate_mean=%.4f",
       len(rows),len(lead),len(allr),rows[0][1],first_day,first_gate,rows[-1][1],min(gv),max(gv),sum(gv)/len(gv))
g25=[x[4] for x in rows if x[1].startswith("2025")]
L.info("gate_2025 mean=%.4f min=%.4f max=%.4f n=%d", sum(g25)/len(g25),min(g25),max(g25),len(g25))
