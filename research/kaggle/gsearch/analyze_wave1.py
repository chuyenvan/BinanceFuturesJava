#!/usr/bin/env python3
"""Phan tich GS wave-1 (Sobol 15 chieu, 256 diem + 1 diem neo id=-1).

Cai DUNG luat chon trong PREREG_GS.md muc 4 (chon) va muc 6 (chan doan).
KHONG tu sang tao luat chon. Neu can doi luat, dung lai va bao lai nguoi giu PREREG,
KHONG tu dien giai lai o day.

Schema dau vao (da kiem chung tu /home/ubuntu/gs/smoke/out_gs_smoke.jsonl va
/home/ubuntu/gs/kernels/gs-w1-0/run.py TRUOC khi viet script nay -- moi dong 1 diem):
    {"id": <int>, "params": {15 key dung ten trong SPEC cua gen_params.py},
     "ok": <bool>,
     "equity_final": <so>,               # equity cuoi CA giai doan (dung de kiem diem neo)
     "full": {...}, "devA": {"cagr_pct":..., "maxdd_pct":..., "equity_end":...},
     "devB": {...},                      # CHI dung de in lenh o BUOC 8, KHONG dung de chon
     "n_trades": <int>, "n_trades_devA": <int>, "n_trades_devB": <int>}
Neu file thuc te lech schema nay, script se BAO LOI RO RANG (ten cot thieu) roi thoat,
KHONG doan.

Chay:  python3 analyze_wave1.py /duong/dan/gs_wave1_all.jsonl
       python3 analyze_wave1.py /duong/dan/gs_wave1_all.jsonl --gen-params /duong/dan/gen_params.py
"""
import argparse
import importlib.util
import json
import logging
import math
import sys
from pathlib import Path

import numpy as np

log = logging.getLogger("analyze_wave1")

DEFAULT_GEN_PARAMS_PATH = (
    "/home/ubuntu/src/BinanceFuturesJava/research/kaggle/gsearch/gen_params.py"
)

# ---- hang so luat chon, TAT CA lay tu PREREG_GS.md muc 4 va muc 6. KHONG duoc doi o day. ----
ANCHOR_EQUITY_EXPECTED = 60395     # PREREG_GS.md muc 5 + BASELINE_NOTE.md (Kaggle+file). KHONG phai 60390.
ANCHOR_EQUITY_TOL = 1e-6           # chi bu sai so BIEU DIEN float khi so/ghi JSON, KHONG phai noi long luat
MIN_N_TRADES_DEVA = 300            # PREREG muc 4 buoc 1
MAXDD_FLOOR_PCT = -25.0            # PREREG muc 4 buoc 1 (maxDD >= -25%)
K_NEIGHBORS = 10                   # PREREG muc 4 buoc 3
FINALIST_MIN_DIST_U = 0.15         # PREREG muc 4 buoc 5
FINALIST_MAX_N = 5                 # PREREG muc 4 buoc 5
SURROGATE_CV_R2_FLOOR = 0.3        # PREREG muc 6

REQUIRED_TOP_KEYS = ("id", "params", "ok")


class AnalysisInputError(Exception):
    """Du lieu dau vao thieu cot / sai dinh dang -- KHONG doan, bao loi ro rang."""


class WaveVoidError(Exception):
    """Diem neo khong tai lap dung equity da tien-dang-ky -- WAVE VOID theo PREREG muc 5."""


# ------------------------------------------------------------------ SPEC (khong hardcode) --

def load_spec(path):
    """Import bien SPEC that tu gen_params.py. KHONG duoc chep lai lo/hi/thang o day."""
    p = Path(path)
    if not p.exists():
        raise AnalysisInputError(
            "KHONG TIM THAY gen_params.py tai %s -- day la nguon SPEC duy nhat "
            "(ten chieu, lo, hi, thang do). Khong the doan lai." % path
        )
    spec_mod = importlib.util.spec_from_file_location("gs_gen_params_spec_ro", str(p))
    mod = importlib.util.module_from_spec(spec_mod)
    spec_mod.loader.exec_module(mod)
    if not hasattr(mod, "SPEC"):
        raise AnalysisInputError(
            "gen_params.py (%s) khong co bien SPEC -- co the file da doi dinh dang, "
            "KHONG tu doan cau truc moi." % path
        )
    spec = mod.SPEC
    if len(spec) != 15:
        raise AnalysisInputError(
            "SPEC trong gen_params.py co %d chieu, PREREG doi hoi DUNG 15 chieu. "
            "Dung lai, khong tu sua." % len(spec)
        )
    return spec


def normalize_u(value, lo, hi, scale):
    """Nghich dao cua map_dim() trong gen_params.py -- dua gia tri that ve u in [0,1]."""
    v = float(value)
    if scale in ("lin", "int"):
        return (v - lo) / (hi - lo)
    if scale in ("log", "logint"):
        return (math.log(v) - math.log(lo)) / (math.log(hi) - math.log(lo))
    raise AnalysisInputError("SPEC co thang khong biet: %r (chi ho tro lin/log/int/logint)" % (scale,))


def compute_u_vector(params, spec, point_id):
    u = np.empty(len(spec), dtype=float)
    for j, (name, _c2b, lo, hi, scale) in enumerate(spec):
        if name not in params:
            raise AnalysisInputError(
                "Diem id=%s: 'params' THIEU chieu '%s' (co trong SPEC gen_params.py). "
                "Dung lai, khong doan gia tri." % (point_id, name)
            )
        u[j] = normalize_u(params[name], lo, hi, scale)
    return u


# ------------------------------------------------------------------------- doc du lieu --

def load_jsonl(path):
    p = Path(path)
    if not p.exists():
        raise AnalysisInputError("Khong tim thay file ket qua: %s (co the wave chua chay xong)." % path)
    records = []
    with p.open() as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise AnalysisInputError("Dong %d cua %s KHONG phai JSON hop le: %s" % (lineno, path, e))
    if not records:
        raise AnalysisInputError("File %s RONG -- chua co ket qua nao de phan tich." % path)
    return records


def _check_required_keys(rec, context):
    missing = [k for k in REQUIRED_TOP_KEYS if k not in rec]
    if missing:
        raise AnalysisInputError(
            "%s: THIEU cot bat buoc %s. Kiem tra lai script sinh ket qua, khong doan." % (context, missing)
        )


def split_anchor(records):
    anchors = [r for r in records if r.get("id") == -1]
    sobol = [r for r in records if r.get("id") != -1]
    if len(anchors) != 1:
        raise AnalysisInputError(
            "Ky vong DUNG 1 dong id=-1 (diem neo C2b), thay %d dong. Dung lai." % len(anchors)
        )
    if len(sobol) != 256:
        log.warning(
            "Ky vong 256 diem Sobol (id=0..255), thay %d diem trong file. "
            "Wave co the CHUA chay xong -- phan tich duoi day chay tren so diem HIEN CO, "
            "ket qua se KHONG day du cho toi khi du 256 diem.",
            len(sobol),
        )
    return anchors[0], sobol


# ------------------------------------------------------------- BUOC 5 (PREREG muc 5): neo --

def check_anchor(anchor):
    """Tra ve equity_final cua neo neu WAVE khong VOID; nem WaveVoidError neu VOID."""
    _check_required_keys(anchor, "Diem neo (id=-1)")
    if not anchor.get("ok"):
        raise WaveVoidError(
            "Diem neo (id=-1) co ok=%r (run khong hoan tat / loi: %s). "
            "=> WAVE VOID theo PREREG_GS.md muc 5. KHONG chon gi."
            % (anchor.get("ok"), anchor.get("err"))
        )
    eq = anchor.get("equity_final")
    if eq is None:
        eq = (anchor.get("full") or {}).get("equity_end")
    if eq is None:
        raise WaveVoidError(
            "Diem neo (id=-1) khong co 'equity_final' lan 'full.equity_end'. "
            "=> WAVE VOID theo PREREG_GS.md muc 5 (khong doc duoc ket qua neo)."
        )
    if abs(float(eq) - ANCHOR_EQUITY_EXPECTED) > ANCHOR_EQUITY_TOL:
        raise WaveVoidError(
            "Diem neo equity_final=%s, ky vong CHINH XAC %s (xem BASELINE_NOTE.md: "
            "Kaggle+file phai ra 60395, KHONG phai 60390 cua Oracle+aerospike). "
            "Sai so cho phep = 0 theo PREREG_GS.md muc 5 -- KHONG duoc dieu chinh neo cho khop. "
            "=> WAVE VOID. Toan bo ket qua bi loai, khong chon gi."
            % (eq, ANCHOR_EQUITY_EXPECTED)
        )
    return float(eq)


# --------------------------------------------------------- BUOC 1 (PREREG muc 4): loc hop le --

def filter_valid(sobol_recs, spec, param_names):
    """Tra ve (danh sach diem hop le, dict dem ly do loai). Diem loi dinh dang -> raise."""
    exclude_reasons = {
        "khong_hoan_tat": 0,
        "n_trades_devA<300": 0,
        "maxDD<-25%": 0,
        "NaN": 0,
    }
    valid = []
    for r in sobol_recs:
        _check_required_keys(r, "Diem id=%s" % r.get("id"))
        pid = r["id"]
        params = r["params"]
        for name, _c, _lo, _hi, _s in spec:
            if name not in params:
                raise AnalysisInputError(
                    "Diem id=%s: 'params' thieu chieu '%s'. Dung lai, khong doan." % (pid, name)
                )
        reasons = set()
        devA = r.get("devA")
        n_tr = r.get("n_trades_devA")
        cagr = devA.get("cagr_pct") if devA else None
        mdd = devA.get("maxdd_pct") if devA else None
        if not r.get("ok") or devA is None or n_tr is None or cagr is None or mdd is None:
            reasons.add("khong_hoan_tat")
        else:
            vals = (n_tr, cagr, mdd)
            if any(isinstance(x, float) and math.isnan(x) for x in vals):
                reasons.add("NaN")
            if n_tr < MIN_N_TRADES_DEVA:
                reasons.add("n_trades_devA<300")
            if mdd < MAXDD_FLOOR_PCT:
                reasons.add("maxDD<-25%")
        if reasons:
            for reason in reasons:
                exclude_reasons[reason] += 1
        else:
            valid.append(r)
    return valid, exclude_reasons


# ------------------------------------------------------- BUOC 2+3 (PREREG muc 4): u + kNN --

def build_u_matrix(valid, spec):
    U = np.empty((len(valid), len(spec)), dtype=float)
    for i, r in enumerate(valid):
        U[i] = compute_u_vector(r["params"], spec, r["id"])
    out_of_range = np.where((U < -1e-6) | (U > 1 + 1e-6))
    n_bad = out_of_range[0].size
    if n_bad:
        bad_ids = sorted({valid[i]["id"] for i in out_of_range[0]})
        log.warning(
            "BUOC 2: %d gia tri u nam ngoai [0,1] (vuot do lam tron cua map_dim), "
            "id lien quan: %s -- se duoc kep ve [0,1] truoc kNN.",
            n_bad, bad_ids[:20],
        )
    return np.clip(U, 0.0, 1.0)


def knn_neighbor_score(U, cagr, k=K_NEIGHBORS):
    """NS(i) = trung binh CAGR cua i va k lang can gan nhat (Euclid, khong tinh) trong U.
    Khong he so phat (lambda=0) -- dung PREREG muc 4 buoc 3."""
    n = U.shape[0]
    k_eff = min(k, n - 1) if n > 1 else 0
    if k_eff < k:
        log.warning(
            "Chi co %d diem hop le, khong du de lay k=%d lang can rieng; dung k=%d.",
            n, k, k_eff,
        )
    NS = np.empty(n)
    for i in range(n):
        d = np.linalg.norm(U - U[i], axis=1)
        order = np.argsort(d)
        neigh = [j for j in order if j != i][:k_eff]
        NS[i] = np.mean(np.concatenate(([cagr[i]], cagr[neigh]))) if neigh else cagr[i]
    return NS


# --------------------------------------------------------------- BUOC 5 (PREREG muc 4): finalist --

def select_finalists(order_ns_desc, U, min_dist=FINALIST_MIN_DIST_U, max_n=FINALIST_MAX_N):
    """Dien giai PREREG ('top 5 theo NS, loc trung >=0.15 trong u, toi da 5') nhu THUAT TOAN
    THAM (greedy): di tu tren xuong theo NS giam dan, bo qua diem cach MOI finalist da chon
    < min_dist, dung khi du max_n hoac het danh sach. Day la mot cho PREREG khong noi ro thu tu
    ap dung ('top 5 roi loc' co the cho ket qua khac 'loc dan toi khi du 5') -- xem bao cao."""
    finalists = []
    for i in order_ns_desc:
        if all(np.linalg.norm(U[i] - U[f]) >= min_dist for f in finalists):
            finalists.append(int(i))
        if len(finalists) >= max_n:
            break
    return finalists


# --------------------------------------------------------------- BUOC 7 (PREREG muc 4): neo --

def anchor_percentile(anchor, spec, U_valid, cagr_valid, NS_valid, k=K_NEIGHBORS):
    devA = anchor.get("devA")
    if not devA or "cagr_pct" not in devA:
        raise AnalysisInputError(
            "Diem neo (id=-1) khong co devA.cagr_pct -- can de tinh phan vi BUOC 7."
        )
    anchor_cagr = float(devA["cagr_pct"])
    anchor_u = np.clip(compute_u_vector(anchor["params"], spec, -1), 0.0, 1.0)
    n = U_valid.shape[0]
    k_eff = min(k, n)
    d = np.linalg.norm(U_valid - anchor_u, axis=1)
    neigh = np.argsort(d)[:k_eff]
    anchor_ns = float(np.mean(np.concatenate(([anchor_cagr], cagr_valid[neigh]))))
    pct_cagr = 100.0 * float(np.mean(cagr_valid <= anchor_cagr))
    pct_ns = 100.0 * float(np.mean(NS_valid <= anchor_ns))
    return {
        "anchor_cagr": anchor_cagr,
        "anchor_ns": anchor_ns,
        "pct_cagr": pct_cagr,
        "pct_ns": pct_ns,
        "n_pop": n,
    }


# ------------------------------------------------------- BUOC 6 (PREREG muc 6): CHAN DOAN --

def surrogate_diagnostics(U, cagr, param_names, cv_r2_floor=SURROGATE_CV_R2_FLOOR):
    """CHAN DOAN, KHONG dung de chon diem. Phai in CV R^2 TRUOC; neu < nguong thi KHONG
    duoc bao cao importance/PDP (PREREG muc 6 -- dieu kien cung, khong duoc lach)."""
    result = {"cv_r2": None, "reported": False}
    n = U.shape[0]
    if n < 20:
        log.warning("BUOC 6: chi co %d diem hop le, qua it de fit surrogate co y nghia -- bo qua.", n)
        return result
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.model_selection import KFold, cross_val_score

    gbr = GradientBoostingRegressor(random_state=42)
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    scores = cross_val_score(gbr, U, cagr, cv=kf, scoring="r2")
    cv_r2 = float(np.mean(scores))
    result["cv_r2"] = cv_r2
    result["cv_r2_folds"] = scores.tolist()
    log.info("BUOC 6 (CHAN DOAN) - surrogate GradientBoosting u->CAGR, CV R^2 (KFold=5) = %.4f (folds=%s)",
              cv_r2, np.round(scores, 4).tolist())
    if cv_r2 < cv_r2_floor:
        log.info(
            "KHONG BAO CAO PHAN RA -- surrogate qua yeu (CV R^2=%.4f < nguong %.2f theo PREREG muc 6).",
            cv_r2, cv_r2_floor,
        )
        return result
    from sklearn.inspection import permutation_importance, partial_dependence

    gbr.fit(U, cagr)
    pi = permutation_importance(gbr, U, cagr, n_repeats=30, random_state=42)
    order_imp = list(np.argsort(-pi.importances_mean))
    log.info("  permutation importance (giam dan, CV R^2 dat nguong nen duoc phep bao cao):")
    importances = []
    for j in order_imp:
        log.info("    %-30s mean=%.4f std=%.4f", param_names[j], pi.importances_mean[j], pi.importances_std[j])
        importances.append((param_names[j], float(pi.importances_mean[j]), float(pi.importances_std[j])))
    pdp_out = {}
    for j in range(len(param_names)):
        pdr = partial_dependence(gbr, U, [j], grid_resolution=10)
        grid = pdr.get("grid_values", pdr.get("values"))[0]
        avg = pdr["average"][0]
        pdp_out[param_names[j]] = (np.round(grid, 3).tolist(), np.round(avg, 3).tolist())
        log.info("    PDP %-30s u-grid=%s cagr_pred=%s", param_names[j],
                  np.round(grid, 3).tolist(), np.round(avg, 3).tolist())
    log.info(
        "  CANH BAO (PREREG muc 6): 256 diem tu MOT day Sobol duy nhat KHONG cho phep uoc luong "
        "chi so Sobol bac 1/tong (can thiet ke Saltelli voi ma tran A, B, AB_i). Phan tren CHI LA "
        "CHAN DOAN (surrogate + permutation importance + PDP), KHONG duoc dung de chon diem hay "
        "de bo chieu khoi wave sau ma khong co doc PRE-REG moi."
    )
    result.update({"reported": True, "importances": importances, "pdp": pdp_out})
    return result


# ------------------------------------------------------------- BUOC 8: lenh DEV-B (CHI IN) --

def log_devb_plan(finalists, valid, ids, param_names):
    log.info("BUOC 8 - ke hoach xac nhan DEV-B cho toi da %d finalist (CHI IN RA, KHONG chay):", len(finalists))
    log.info(
        "  LUU Y quan trong (can nguoi giu PREREG xac nhan, KHONG tu quyet o day): kho code hien "
        "tai (gs-w1-*/run.py) KHONG co duong chay 'chi DEV-B' rieng biet -- moi lan chay JVM luon "
        "mo phong CA giai doan 2022-01-01..2024-06-29 trong MOT pass, roi cat lat DEV-A/DEV-B tu "
        "CUNG mot chuoi equity. Vi vay o ha tang hien co, 'xac nhan tren DEV-B' cho 1 finalist ve "
        "ky thuat la CHAY LAI toan bo giai doan bang dung params cua finalist do, roi CHI DOC "
        "truong ket qua 'devB' (bo qua 'devA'/'full' vi DEV-A da co san tu wave 1). Duoi day la "
        "GOI Y dinh dang shard 1-dong cho tung finalist de dua vao co che run.py hien co; day KHONG "
        "phai lenh shell chay duoc ngay (run.py doc /kaggle/input theo glob, khong nhan tham so dong "
        "lenh) -- nguoi van hanh Kaggle/DEV-B can tu ghep vao pipeline cua ho."
    )
    for rank, idx in enumerate(finalists, 1):
        r = valid[idx]
        pid = r["id"]
        shard_line = json.dumps({"id": pid, **{k: r["params"][k] for k in param_names}})
        log.info("  finalist #%d id=%s -> dong shard DEV-B de nghi: %s", rank, pid, shard_line)


# --------------------------------------------------------------------------- pipeline chinh --

def run(records, spec, run_surrogate=True):
    """Chay TOAN BO luat chon PREREG muc 4 + chan doan muc 6 tren `records` (list dict da
    json.loads). `spec` = SPEC lay tu gen_params.py (load_spec()). Nem WaveVoidError neu diem
    neo khong dat, AnalysisInputError neu du lieu thieu cot. Tra ve dict ket qua co cau truc
    (dung cho ca CLI va test) -- KHONG in/log gi ngoai cac dong log.info/log.warning da co."""
    param_names = [row[0] for row in spec]

    anchor, sobol_recs = split_anchor(records)
    anchor_equity = check_anchor(anchor)
    log.info("Diem neo OK: equity_final = %s (== %s ky vong theo PREREG_GS.md muc 5). Wave khong VOID.",
              anchor_equity, ANCHOR_EQUITY_EXPECTED)

    valid, exclude_reasons = filter_valid(sobol_recs, spec, param_names)
    n_excluded = len(sobol_recs) - len(valid)
    log.info("BUOC 1 - loc hop le: %d/%d diem hop le, %d diem bi loai (mot diem co the vi NHIEU ly do "
              "cung luc nen tong theo ly do co the > so diem bi loai):",
              len(valid), len(sobol_recs), n_excluded)
    for reason, cnt in exclude_reasons.items():
        log.info("    loai vi %s: %d diem", reason, cnt)
    if not valid:
        raise AnalysisInputError("Khong con diem Sobol nao hop le sau BUOC 1 -- khong the phan tich tiep.")

    U = build_u_matrix(valid, spec)
    cagr = np.array([r["devA"]["cagr_pct"] for r in valid], dtype=float)
    ids = np.array([r["id"] for r in valid])
    log.info("BUOC 2 - da chuan hoa %d diem hop le ve u in [0,1]^%d theo dung lo/hi/thang cua SPEC.",
              len(valid), len(spec))

    NS = knn_neighbor_score(U, cagr, k=K_NEIGHBORS)
    log.info("BUOC 3 - da tinh NS (k=%d lang can, khong he so phat) cho %d diem hop le.",
              K_NEIGHBORS, len(valid))

    order_ns = np.argsort(-NS)
    order_cagr = np.argsort(-cagr)
    chosen_ns_idx = int(order_ns[0])
    chosen_cagr_idx = int(order_cagr[0])
    log.info("BUOC 4 - CHON theo argmax NS: id=%s NS=%.4f CAGR=%.4f",
              ids[chosen_ns_idx], NS[chosen_ns_idx], cagr[chosen_ns_idx])
    log.info("  (doi chieu, KHONG phai diem duoc chon) argmax CAGR: id=%s NS=%.4f CAGR=%.4f",
              ids[chosen_cagr_idx], NS[chosen_cagr_idx], cagr[chosen_cagr_idx])
    if ids[chosen_ns_idx] == ids[chosen_cagr_idx]:
        log.info("  => argmax NS TRUNG argmax CAGR (id=%s).", ids[chosen_ns_idx])
    else:
        log.info("  => argmax NS KHAC argmax CAGR: theo PREREG day la KET QUA hop le (lay tam vung "
                  "tot rong nhat), KHONG phai loi; diem duoc CHON van la id=%s.", ids[chosen_ns_idx])

    raw_top5_ids = [int(ids[i]) for i in order_ns[:5]]
    finalists = select_finalists(order_ns, U, min_dist=FINALIST_MIN_DIST_U, max_n=FINALIST_MAX_N)
    log.info("BUOC 5 - raw top-5 theo NS (truoc loc trung u>=%.2f): %s", FINALIST_MIN_DIST_U, raw_top5_ids)
    log.info("  finalist sau loc trung (%d/%d toi da): %s", len(finalists), FINALIST_MAX_N,
              [int(ids[i]) for i in finalists])
    for rank, i in enumerate(finalists, 1):
        log.info("    #%d id=%s NS=%.4f CAGR=%.4f", rank, ids[i], NS[i], cagr[i])

    pct = anchor_percentile(anchor, spec, U, cagr, NS, k=K_NEIGHBORS)
    log.info(
        "BUOC 7 - phan vi diem neo trong %d diem hop le: CAGR=%.4f%% (phan vi %.1f%%), "
        "NS=%.4f%% (phan vi %.1f%%)",
        pct["n_pop"], pct["anchor_cagr"], pct["pct_cagr"], pct["anchor_ns"], pct["pct_ns"],
    )

    log_devb_plan(finalists, valid, ids, param_names)

    surrogate = None
    if run_surrogate:
        surrogate = surrogate_diagnostics(U, cagr, param_names)

    return {
        "anchor_equity": anchor_equity,
        "n_sobol_total": len(sobol_recs),
        "n_valid": len(valid),
        "exclude_reasons": exclude_reasons,
        "valid_ids": [int(x) for x in ids],
        "chosen_ns_id": int(ids[chosen_ns_idx]),
        "chosen_cagr_id": int(ids[chosen_cagr_idx]),
        "raw_top5_ids": raw_top5_ids,
        "finalist_ids": [int(ids[i]) for i in finalists],
        "anchor_percentile": pct,
        "surrogate": surrogate,
        "U": U,
        "cagr": cagr,
        "NS": NS,
        "ids": ids,
    }


def _build_argparser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input_jsonl", help="duong dan file jsonl ket qua wave 1 (vd gs_wave1_all.jsonl)")
    ap.add_argument("--gen-params", default=DEFAULT_GEN_PARAMS_PATH,
                     help="duong dan gen_params.py de doc SPEC (mac dinh: duong chinh thuc tren Oracle)")
    ap.add_argument("--no-surrogate", action="store_true", help="bo qua BUOC 6 (chan doan surrogate)")
    ap.add_argument("-v", "--verbose", action="store_true", help="log muc DEBUG")
    return ap


def main(argv=None):
    args = _build_argparser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    try:
        spec = load_spec(args.gen_params)
        records = load_jsonl(args.input_jsonl)
        log.info("Doc %d dong tu %s", len(records), args.input_jsonl)
        run(records, spec, run_surrogate=not args.no_surrogate)
    except WaveVoidError as e:
        log.error(str(e))
        log.error("KET LUAN CUOI CUNG: WAVE VOID.")
        return 1
    except AnalysisInputError as e:
        log.error(str(e))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
