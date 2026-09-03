#!/usr/bin/env python3
"""Test cho analyze_wave1.py. Sinh du lieu TONG HOP (khong dung ket qua that) de kiem
chung co che chon dung PREREG_GS.md muc 4, KHONG can cho ket qua wave 1 that ve.

Du lieu tong hop dung 256 vector Sobol THAT lay tu gen_params.py (dung SPEC/seed da
tien-dang-ky) + 1 diem neo id=-1, roi gan CAGR tong hop theo mot vung phang (plateau)
rong + mot dinh nhon co lap de kiem tra co che k-NN "lay tam vung tot" hoat dung dung.

Chay:  python3 test_analyze_wave1.py [--gen-params /duong/dan/gen_params.py]
"""
import argparse
import json
import logging
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_wave1 as aw  # noqa: E402

log = logging.getLogger("test_analyze_wave1")

ANCHOR_EQUITY_OK = 60395
ANCHOR_EQUITY_BAD = 60000  # PREREG: bat ky gia tri khac 60395 deu phai VOID


def _sobol_param_rows(spec, n_points=256, gen_params_path=None):
    """Sinh dung 256 vector Sobol THAT (khong bia) bang chinh gen_params.py, tra ve
    (list[dict params], np.ndarray u (n,15))."""
    if gen_params_path is None:
        gen_params_path = aw.DEFAULT_GEN_PARAMS_PATH
    import importlib.util

    spec_mod = importlib.util.spec_from_file_location("gp_for_test", gen_params_path)
    gp = importlib.util.module_from_spec(spec_mod)
    spec_mod.loader.exec_module(gp)
    from scipy.stats import qmc

    sob = qmc.Sobol(d=len(gp.SPEC), scramble=True, seed=gp.SEED)
    pts = sob.random_base2(m=gp.M)
    assert pts.shape[0] == n_points
    rows = []
    for i in range(n_points):
        rec = {}
        for j, (name, _c, lo, hi, sc) in enumerate(gp.SPEC):
            rec[name] = gp.map_dim(float(pts[i][j]), lo, hi, sc)
        rows.append(rec)
    U = pts.copy()  # gia tri u [0,1] GOC truoc khi map_dim/round -- dung de thiet ke CAGR tong hop
    return rows, U


def _make_anchor_row(spec, equity_final):
    params = {name: c2b for name, c2b, _lo, _hi, _sc in spec}
    return {
        "id": -1,
        "params": params,
        "ok": True,
        "equity_final": equity_final,
        "full": {"equity_end": equity_final},
        "devA": {"cagr_pct": 27.49, "maxdd_pct": -13.12, "equity_end": 56835},
        "devB": {"cagr_pct": 13.12, "maxdd_pct": -6.36, "equity_end": equity_final},
        "n_trades": 970, "n_trades_devA": 655, "n_trades_devB": 315,
    }


def _make_sobol_row(pid, params, cagr_pct, maxdd_pct=-10.0, n_trades_devA=500, ok=True):
    return {
        "id": pid,
        "params": params,
        "ok": ok,
        "equity_final": 50000.0,
        "full": {"equity_end": 50000.0},
        "devA": {"cagr_pct": cagr_pct, "maxdd_pct": maxdd_pct, "equity_end": 50000.0},
        "devB": {"cagr_pct": cagr_pct * 0.5, "maxdd_pct": maxdd_pct, "equity_end": 50000.0},
        "n_trades": n_trades_devA * 2, "n_trades_devA": n_trades_devA, "n_trades_devB": n_trades_devA,
    }


def _build_plateau_vs_peak_dataset(spec, param_rows, U_raw):
    """Thiet ke CAGR tong hop: MOT plateau rong (~25%) quanh tam hinh khoi 15-chieu,
    MOT dinh nhon co lap (40%) o diem XA tam nhat, lang can dinh nhon la baseline TE (~5%).
    Tra ve (list[dict] 256 dong sobol, R_plateau, peak_index, in_plateau_bool_array)."""
    n = U_raw.shape[0]
    center = np.full(U_raw.shape[1], 0.5)
    dist_to_center = np.linalg.norm(U_raw - center, axis=1)
    order = np.argsort(dist_to_center)
    r_idx = order[int(0.35 * n)]
    R = dist_to_center[r_idx]
    in_plateau = dist_to_center <= R
    rng = np.random.RandomState(123)
    noise = rng.uniform(-0.3, 0.3, size=n)
    cagr = np.where(in_plateau, 25.0, 5.0) + noise
    peak_idx = int(order[-1])  # diem XA tam nhat trong 256 mau
    cagr[peak_idx] = 40.0
    log.info("Thiet ke test: %d/%d diem trong plateau (R=%.4f quanh tam u=0.5^15).", in_plateau.sum(), n, R)
    log.info("Diem dinh nhon (peak) = index %d, dist_to_center=%.4f (xa nhat trong mau), cagr=40.0",
              peak_idx, dist_to_center[peak_idx])
    rows = []
    for i in range(n):
        rows.append(_make_sobol_row(i, param_rows[i], float(cagr[i])))
    return rows, R, peak_idx, in_plateau, dist_to_center


def test_plateau_beats_sharp_peak(spec, param_rows, U_raw):
    """PREREG muc 4 buoc 4: chon la argmax NS, KHONG phai argmax CAGR. Test nay chung minh
    co che kNN chon TAM VUNG PHANG rong thay vi DINH NHON co lap dung mot minh."""
    log.info("=== TEST 1: chon diem trong plateau, KHONG chon dinh nhon co lap ===")
    sobol_rows, R, peak_idx, in_plateau, dist_to_center = _build_plateau_vs_peak_dataset(
        spec, param_rows, U_raw
    )
    anchor_row = _make_anchor_row(spec, ANCHOR_EQUITY_OK)
    records = [anchor_row] + sobol_rows

    result = aw.run(records, spec, run_surrogate=False)

    peak_id = peak_idx  # id == index o day
    chosen_ns_id = result["chosen_ns_id"]
    chosen_cagr_id = result["chosen_cagr_id"]

    log.info("Ket qua: chosen_ns_id=%s chosen_cagr_id=%s peak_id=%s", chosen_ns_id, chosen_cagr_id, peak_id)
    assert chosen_cagr_id == peak_id, (
        "Ky vong argmax CAGR chinh la dinh nhon (id=%s) vi no duoc gan CAGR=40 duy nhat, "
        "nhung argmax CAGR tra ve id=%s -- thiet ke test sai, khong phai loi analyze_wave1."
        % (peak_id, chosen_cagr_id)
    )
    chosen_dist = dist_to_center[chosen_ns_id]
    assert chosen_dist <= R + 1e-9, (
        "THAT BAI: diem duoc CHON (argmax NS, id=%s) nam NGOAI plateau (dist=%.4f > R=%.4f). "
        "Co che 'lay tam vung tot' KHONG hoat dung dung." % (chosen_ns_id, chosen_dist, R)
    )
    assert chosen_ns_id != peak_id, (
        "THAT BAI: diem duoc CHON (argmax NS) TRUNG voi dinh nhon co lap (id=%s) -- "
        "co che kNN khong loc duoc dinh nhon." % peak_id
    )
    peak_ns = float(result["NS"][np.where(result["ids"] == peak_id)[0][0]])
    chosen_ns = float(result["NS"][np.where(result["ids"] == chosen_ns_id)[0][0]])
    log.info(
        "BANG CHUNG: NS(diem duoc chon, id=%s)=%.3f  >>  NS(dinh nhon, id=%s)=%.3f  "
        "(CAGR dinh nhon=40.0 nhung NS thap vi lang can toan diem te ~5%%).",
        chosen_ns_id, chosen_ns, peak_id, peak_ns,
    )
    assert chosen_ns > peak_ns, "THAT BAI: NS cua diem duoc chon phai LON HON NS cua dinh nhon."
    log.info("=== TEST 1 PASS ===\n")


def test_anchor_void_on_wrong_equity():
    log.info("=== TEST 2: neo sai equity (%s thay vi %s) -> phai WAVE VOID ===",
              ANCHOR_EQUITY_BAD, ANCHOR_EQUITY_OK)
    spec = aw.load_spec(aw.DEFAULT_GEN_PARAMS_PATH if Path(aw.DEFAULT_GEN_PARAMS_PATH).exists()
                         else _fallback_spec_path())
    anchor_bad = _make_anchor_row(spec, ANCHOR_EQUITY_BAD)
    dummy_sobol = [_make_sobol_row(i, {n: c for n, c, _l, _h, _s in spec}, 10.0) for i in range(256)]
    records = [anchor_bad] + dummy_sobol
    try:
        aw.run(records, spec, run_surrogate=False)
    except aw.WaveVoidError as e:
        log.info("Da nhan WaveVoidError dung nhu ky vong: %s", e)
    else:
        raise AssertionError("THAT BAI: neo sai equity nhung KHONG nem WaveVoidError.")

    # kiem tra o muc CLI (main()) cung tra ve VOID va exit code != 0
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
        tmp_path = f.name
    rc = aw.main([tmp_path, "--gen-params", aw.DEFAULT_GEN_PARAMS_PATH
                  if Path(aw.DEFAULT_GEN_PARAMS_PATH).exists() else _fallback_spec_path(),
                  "--no-surrogate"])
    log.info("main() tra ve exit code = %s (ky vong != 0 khi VOID)", rc)
    assert rc != 0, "THAT BAI: main() phai tra ve exit code != 0 khi neo VOID."
    log.info("=== TEST 2 PASS ===\n")


def test_filter_excludes_bad_points(spec, param_rows):
    log.info("=== TEST 3: loc dung diem n_trades<300 va maxDD<-25%% ===")
    anchor_row = _make_anchor_row(spec, ANCHOR_EQUITY_OK)
    rows = [_make_sobol_row(i, param_rows[i], 10.0 + 0.01 * i) for i in range(256)]
    BAD_NTRADES_ID = 7
    BAD_MAXDD_ID = 42
    rows[BAD_NTRADES_ID] = _make_sobol_row(BAD_NTRADES_ID, param_rows[BAD_NTRADES_ID], 10.0, n_trades_devA=100)
    rows[BAD_MAXDD_ID] = _make_sobol_row(BAD_MAXDD_ID, param_rows[BAD_MAXDD_ID], 10.0, maxdd_pct=-40.0)
    records = [anchor_row] + rows

    result = aw.run(records, spec, run_surrogate=False)
    log.info("exclude_reasons = %s", result["exclude_reasons"])
    assert result["exclude_reasons"]["n_trades_devA<300"] >= 1, "THAT BAI: khong dem duoc loai vi n_trades_devA<300."
    assert result["exclude_reasons"]["maxDD<-25%"] >= 1, "THAT BAI: khong dem duoc loai vi maxDD<-25%."
    assert BAD_NTRADES_ID not in result["valid_ids"], "THAT BAI: diem n_trades=100 khong bi loai khoi valid_ids."
    assert BAD_MAXDD_ID not in result["valid_ids"], "THAT BAI: diem maxDD=-40%% khong bi loai khoi valid_ids."
    assert result["n_valid"] == 256 - 2
    log.info("=== TEST 3 PASS ===\n")


def _fallback_spec_path():
    return str(Path(__file__).resolve().parent.parent.parent / "gen_params.py")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen-params", default=None)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    gp_path = args.gen_params or (aw.DEFAULT_GEN_PARAMS_PATH if Path(aw.DEFAULT_GEN_PARAMS_PATH).exists()
                                   else _fallback_spec_path())
    log.info("Dung gen_params.py tai: %s", gp_path)
    spec = aw.load_spec(gp_path)
    param_rows, U_raw = _sobol_param_rows(spec, gen_params_path=gp_path)

    test_plateau_beats_sharp_peak(spec, param_rows, U_raw)
    test_anchor_void_on_wrong_equity()
    test_filter_excludes_bad_points(spec, param_rows)

    log.info("TAT CA TEST PASS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
