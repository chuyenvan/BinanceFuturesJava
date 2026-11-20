"""sample.py - lay mau PHAN TANG tat dinh cho GRIDV2 S2 (PREREG_GRIDV2_S2 muc 4).

Don vi lay mau = cum (sym, ngay UTC cua t0) co >= 1 don vi COND_A c0.2 k2 (danh sach su kien tu events_kernel). Tang = nam x tier
(nam 2021H2/2022/2023 thuoc nua A; 2024/2025 nua B). Trong moi tang: xep cum theo khoa sha256("SEED|sym|ngay") (khong phu thuoc
thu tu dau vao), chon n_h = max(1, round(f_nua x N_h)) cum dau; phan con lai theo dung thu tu = DANH SACH DU PHONG (thay the khi
file Vision thieu, W6). Cum audit (W4/W5): theo thu tu khoa toan cuc trong cac cum da chon, lay den khi du >= AUDIT_MIN_UNITS don vi
va >= AUDIT_MIN_CLUSTERS cum MOI nua.
f_nua (che do auto, hang so prereg): f nho nhat trong F_GRID sao cho SE du doan <= SE_TARGET cho CA K_OPT va K_PESS (ket qua S1 tung
don vi, KHONG dung ket qua TL nao): SE_pred(f)^2 = SE_blk^2 + (1 - f)/f x sum_c u_c^2 / N^2, u_c = sum_{don vi khop trong cum c}
(net - M_nua) (xap xi lay mau Bernoulli cum; SE_blk = SE khoi 20 ngay S1 tren toan bo cum).
Xuat: sample.csv (ASCII, sap theo sym, ngay; sha256 = moc commit), sample_manifest.json.
Dung: python3 sample.py EVENTS_DIR OUT_DIR
"""
import glob
import hashlib
import json
import logging
import os
import sys
import numpy as np
import pandas as pd

log = logging.getLogger("sample_s2")
SEED_SAMPLE = 2026112150
SE_TARGET = 4.5
CAP_BYTES = 150e9                 # MASTER D2: tran tai zip; vuot -> f LON NHAT trong luoi con <= tran (apply_cap)
F_GRID = (0.05, 0.075, 0.10, 0.125, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 0.60, 0.80, 1.0)
AUDIT_MIN_UNITS = 300
AUDIT_MIN_CLUSTERS = 60
W_MIN, T_MIN = 115, 115
DS = 1619827200000
DAY = 86400000
MIN = 60000
SEAL = 1767225600000
HALF_B_DAY = (1704067200000 - DS) // DAY
STUDY_DAY = (1625097600000 - DS) // DAY
NDAY = (SEAL - DS) // DAY
BLOCK = 20
CSV_COLS = ["sym", "date", "half", "year", "tier", "stratum", "key", "rank", "n_stratum", "n_sel_stratum", "selected", "audit",
            "files", "n_units"]


def load_events(ev_dir):
    fs = sorted(glob.glob(os.path.join(ev_dir, "events_s*.parquet")))
    if not fs:
        raise RuntimeError("khong co events_s*.parquet trong %s" % ev_dir)
    ev = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    shas = {os.path.basename(f): hashlib.sha256(open(f, "rb").read()).hexdigest() for f in fs}
    if (ev.t0_ms >= SEAL).any() or (ev.date >= "2026-01-01").any():
        raise RuntimeError("su kien >= 2026 - DUNG")
    return ev, shas


def cluster_frame(ev):
    ev = ev if "dl_end_ms" in ev.columns else ev.assign(dl_end_ms=-1)
    g = ev.groupby(["sym", "date"], sort=True)
    fr = g.agg(day=("day", "first"), tier=("tier", "first"), tier_n=("tier", "nunique"), n_units=("t0_ms", "size"),
               t0_max=("t0_ms", "max"), dl_end=("dl_end_ms", "first")).reset_index()
    if (fr.tier_n != 1).any():
        raise RuntimeError("tier khong duy nhat trong cum (sym, ngay)")
    fr["year"] = fr.date.str[:4].astype(int)
    fr["half"] = np.where(fr.day >= HALF_B_DAY, "B", "A")
    fr["stratum"] = fr.year.astype(str) + "_T" + fr.tier.astype(int).astype(str)
    nxt = DS + (fr.day.to_numpy().astype(np.int64) + 1) * DAY
    need_next = fr.t0_max.to_numpy() + (W_MIN + T_MIN + 61) * MIN > nxt
    dle = fr.dl_end.to_numpy().astype(np.int64)
    need_next &= ~((dle >= 0) & (dle <= nxt))          # delist truoc nua dem: khong can (va Vision khong co) file D+1
    d1 = pd.to_datetime(nxt, unit="ms").strftime("%Y-%m-%d")
    fr["files"] = np.where(need_next, fr.date + ";" + d1, fr.date)
    if any(x >= "2026-01-01" for f in fr.files for x in f.split(";")):
        raise RuntimeError("cum can file >= 2026-01-01 - DUNG")
    fr["key"] = [hashlib.sha256(("%d|%s|%s" % (SEED_SAMPLE, s, d)).encode()).hexdigest() for s, d in zip(fr.sym, fr.date)]
    return fr.drop(columns=["tier_n", "dl_end"])


def se_parts(ev, half, model):
    """SE_blk (khoi 20 ngay, toan bo cum), sum_c u_c^2, N, M cho 1 nua x mo hinh S1 ('o' K_OPT / 'p' K_PESS)."""
    lo, hi = (STUDY_DAY, HALF_B_DAY) if half == "A" else (HALF_B_DAY, NDAY)
    ok = (ev[model + "_filled"] == 1) & (ev[model + "_excl"] == 0) & (ev.day >= lo) & (ev.day < hi)
    e = ev[ok]
    N = len(e)
    if N == 0:
        return dict(N=0, M=np.nan, se_blk=np.nan, sum_uc2=np.nan)
    M = e[model + "_net"].sum() / N
    D = hi - lo
    Sd = np.bincount(e.day - lo, weights=e[model + "_net"], minlength=D)
    Nd = np.bincount(e.day - lo, minlength=D).astype(float)
    st = np.arange(0, D, BLOCK)
    Sb, Nb = np.add.reduceat(Sd, st), np.add.reduceat(Nd, st)
    se_blk = np.sqrt(((Sb - M * Nb) ** 2).sum()) / N
    uc = (e[model + "_net"] - M).groupby([e.sym, e.date]).sum()
    return dict(N=int(N), M=float(M), se_blk=float(se_blk), sum_uc2=float((uc ** 2).sum()))


def se_pred(parts, f):
    return float(np.sqrt(parts["se_blk"] ** 2 + (1.0 - f) / f * parts["sum_uc2"] / parts["N"] ** 2))


def choose_f(ev):
    out = {}
    for h in ("A", "B"):
        P = {m: se_parts(ev, h, m) for m in ("o", "p")}
        tab = {str(f): {m: se_pred(P[m], f) for m in P} for f in F_GRID}
        fh = next((f for f in F_GRID if max(tab[str(f)].values()) <= SE_TARGET), 1.0)
        out[h] = dict(f=fh, parts=P, table=tab, se_pred_at_f=tab[str(fh)])
    return out


def select(fr, fmap):
    fr = fr.sort_values(["stratum", "key"]).copy()
    fr["rank"] = fr.groupby("stratum").cumcount()
    fr["n_stratum"] = fr.groupby("stratum").key.transform("size")
    f_row = fr.half.map(lambda h: fmap[h])
    fr["n_sel_stratum"] = np.maximum(1, np.round(f_row * fr.n_stratum + 1e-9)).astype(int)
    fr["n_sel_stratum"] = np.minimum(fr.n_sel_stratum, fr.n_stratum)
    fr["selected"] = fr["rank"] < fr.n_sel_stratum
    fr["audit"] = False
    for h in ("A", "B"):
        s = fr[(fr.half == h) & fr.selected].sort_values("key")
        cu = s.n_units.cumsum().to_numpy()
        k = np.arange(1, len(s) + 1)
        need = np.flatnonzero((cu >= AUDIT_MIN_UNITS) & (k >= AUDIT_MIN_CLUSTERS))
        nk = (need[0] + 1) if need.size else len(s)
        fr.loc[s.index[:nk], "audit"] = True
    return fr.sort_values(["sym", "date"]).reset_index(drop=True)


def write_csv(fr, path):
    lines = [",".join(CSV_COLS)]
    for r in fr[CSV_COLS].itertuples(index=False):
        lines.append(",".join(str(int(x)) if isinstance(x, (bool, np.bool_)) else str(x) for x in r))
    data = ("\n".join(lines) + "\n").encode("ascii")
    with open(path, "wb") as f:
        f.write(data)
    return hashlib.sha256(data).hexdigest()


def read_csv(path, expected_sha=None):
    data = open(path, "rb").read()
    h = hashlib.sha256(data).hexdigest()
    if expected_sha is not None and h != expected_sha:
        raise RuntimeError("W1: sha256 sample.csv %s != da commit %s - DUNG" % (h, expected_sha))
    fr = pd.read_csv(path, dtype={"sym": str, "date": str, "files": str, "key": str, "stratum": str, "half": str})
    fr["selected"] = fr.selected.astype(int).astype(bool)
    fr["audit"] = fr.audit.astype(int).astype(bool)
    return fr, h


def make_sample(ev, out_dir, fmap=None):
    os.makedirs(out_dir, exist_ok=True)
    fr = cluster_frame(ev)
    ch = choose_f(ev) if fmap is None else None
    fm = fmap if fmap is not None else {h: ch[h]["f"] for h in ("A", "B")}
    fr = select(fr, fm)
    sha = write_csv(fr, os.path.join(out_dir, "sample.csv"))
    strata = {}
    for st_, g in fr.groupby("stratum"):
        strata[st_] = dict(N=int(len(g)), n_sel=int(g.selected.sum()), units=int(g.n_units.sum()),
                           units_sel=int(g[g.selected].n_units.sum()), files_sel=int(sum(len(x.split(";")) for x in g[g.selected].files)))
    man = dict(seed=SEED_SAMPLE, se_target=SE_TARGET, f_grid=list(F_GRID), f=fm, choose=ch, strata=strata,
               n_clusters=int(len(fr)), n_selected=int(fr.selected.sum()), n_audit=int(fr.audit.sum()),
               units_audit=int(fr[fr.audit].n_units.sum()),
               n_files_selected=int(sum(len(x.split(";")) for x in fr[fr.selected].files)), sample_csv_sha256=sha)
    json.dump(man, open(os.path.join(out_dir, "sample_manifest.json"), "w"), indent=1, default=float)
    log.info("sample: %d cum, chon %d, audit %d, f %s, sha %s", len(fr), fr.selected.sum(), fr.audit.sum(), fm, sha)
    return fr, man


def apply_cap(ev, out_dir, head_json):
    """MASTER D2: head.json (fetch_reduce --head-only tren mau theo luat SE) -> neu tong byte <= CAP: giu nguyen. Neu vuot: chon f LON
    NHAT trong F_GRID (<= f da chon, cung cho moi nua: f_nua' = min(f_nua, f)) sao cho tong byte cac file DUY NHAT cua mau <= CAP
    (lua chon long nhau: n_h tang theo f => file cua f nho la tap con, HEAD da phu). File HEAD khong 200 tinh 0 byte.
    Ghi lai sample.csv + manifest (cap_applied, f moi, SE du doan). Tra man."""
    man0 = json.load(open(os.path.join(out_dir, "sample_manifest.json")))
    H = json.load(open(head_json))
    size = {(r["sym"], r["date"]): max(int(r["bytes"]), 0) for r in H["rows"]}
    fr0 = cluster_frame(ev)
    f0 = {h: float(man0["f"][h]) for h in ("A", "B")}

    def tot(fm):
        fr = select(fr0, fm)
        fs = {(s, d) for s, ff in zip(fr[fr.selected].sym, fr[fr.selected].files) for d in ff.split(";")}
        miss = [x for x in fs if x not in size]
        if miss:
            raise RuntimeError("head.json khong phu file cua mau (%d) - DUNG" % len(miss))
        return sum(size[x] for x in fs)

    t0 = tot(f0)
    if t0 <= CAP_BYTES:
        man0["cap"] = dict(applied=False, total_bytes=t0, cap_bytes=CAP_BYTES)
        json.dump(man0, open(os.path.join(out_dir, "sample_manifest.json"), "w"), indent=1, default=float)
        return man0
    chosen = None
    for f in sorted(F_GRID, reverse=True):
        fm = {h: min(f0[h], f) for h in ("A", "B")}
        if tot(fm) <= CAP_BYTES:
            chosen = fm
            break
    if chosen is None:
        raise RuntimeError("ngay ca f nho nhat vuot tran - DUNG, bao MASTER")
    fr, man = make_sample(ev, out_dir, chosen)
    pr = {h: {m: se_pred(se_parts(ev, h, m), chosen[h]) for m in ("o", "p")} for h in ("A", "B")}
    man["cap"] = dict(applied=True, total_bytes_before=t0, total_bytes=tot(chosen), cap_bytes=CAP_BYTES, f_before=f0,
                      f_after=chosen, se_pred_after=pr)
    man["events_sha256"] = man0.get("events_sha256")
    json.dump(man, open(os.path.join(out_dir, "sample_manifest.json"), "w"), indent=1, default=float)
    log.info("CAP: %.1f GB > tran -> f %s, %.1f GB, SE du doan %s", t0 / 1e9, chosen, man["cap"]["total_bytes"] / 1e9, pr)
    return man


def main():
    """python3 sample.py EVENTS_DIR OUT_DIR            -> mau theo luat SE
       python3 sample.py EVENTS_DIR OUT_DIR HEAD_JSON  -> ap tran CAP (sau fetch_reduce --head-only)"""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    ev, shas = load_events(sys.argv[1])
    if len(sys.argv) == 4:
        apply_cap(ev, sys.argv[2], sys.argv[3])
        return
    fr, man = make_sample(ev, sys.argv[2])
    man["events_sha256"] = shas
    json.dump(man, open(os.path.join(sys.argv[2], "sample_manifest.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
