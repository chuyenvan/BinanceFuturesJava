"""
cpcv_harness.py — TIẾN TRÌNH TỰ SEARCH PARAM, không leak-qua-mắt-người.

Người chỉ làm 1 việc: đóng băng SPEC (search space + objective O + PASS). Sau đó máy chạy hết,
người xem số OOS đúng 1 lần ở cuối. Mọi trial đều vào sổ (trial_ledger) ⇒ DSR tự deflate.

KIẾN TRÚC (điểm mấu chốt, khác cách làm thẳng tay):
  Không chạy 28 path × M config = 28M backtest. Thay vào đó:
    B1. Đánh giá M config × N block, MỖI CẶP ĐÚNG 1 LẦN  -> M×N backtest (vd 16×8 = 128).
    B2. Toàn bộ C(8,2)=28 tổ hợp CPCV chỉ còn là SỐ HỌC trên ma trận đó — miễn phí.
  Hợp lệ vì model selector đã BAKED (không train lại theo fold); "training" ở đây = việc CHỌN knob,
  và việc chọn đó chỉ được nhìn các block TRAIN của từng tổ hợp.

CHỐNG LEAK BIÊN: các block cách nhau một khoảng gap = purge + embargo (≥ max(label_horizon, MAX_HOLD)).
  Lệnh mở cuối block train không thể chạy sang block test. Vùng gap bị VỨT, không dùng cho bên nào.

VAI TRÒ:
  INNER (train-only): argmax_config O(các block train)   <- máy chọn, người không chạm
  OUTER (test-only) : chỉ ĐO O của config đã chọn        <- không bao giờ dùng để chọn

Chạy: python3 cpcv_harness.py  -> self-test bằng evaluator giả (không cần Oracle).
Logging: module `logging` (không print). Cùng thư mục với cpcv_validation.py + trial_ledger.py.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from itertools import combinations
from typing import Callable, Protocol, Sequence

import numpy as np

from cpcv_validation import deflated_sharpe_ratio, pbo_cscv
from trial_ledger import TrialLedger, canonical_json, spec_hash

logger = logging.getLogger("harness")

MS_HOUR = 3_600_000


# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Block:
    idx: int
    start_ms: int
    end_ms: int

    @property
    def name(self) -> str:
        return f"b{self.idx:02d}"


def build_blocks(start_ms: int, end_ms: int, n_blocks: int, gap_ms: int) -> list[Block]:
    """Chia [start,end) thành n_blocks đoạn bằng nhau rồi CẮT BỎ `gap_ms` ở đuôi mỗi đoạn.

    Vùng bị cắt = purge+embargo. Block i dùng [s_i, e_i - gap), nên lệnh mở trong block i buộc phải
    đóng trước khi chạm block i+1 (với gap ≥ MAX_HOLD) và nhãn của nó không tràn sang (gap ≥ horizon).
    """
    if n_blocks < 4:
        raise ValueError("n_blocks >= 4 (can du block de chia train/test)")
    edges = np.linspace(start_ms, end_ms, n_blocks + 1).astype(np.int64)
    out: list[Block] = []
    for i in range(n_blocks):
        s, e = int(edges[i]), int(edges[i + 1]) - gap_ms
        if e <= s:
            raise ValueError(f"gap_ms={gap_ms} qua lon so voi do dai block ({edges[i+1]-edges[i]} ms)")
        out.append(Block(i, s, e))
    return out


class Evaluator(Protocol):
    """Cầu nối sang Java. Chạy backtest 1 config trên 1 khoảng thời gian, trả metric.

    Bên Java cần 1 entrypoint nhận (start_ms, end_ms, env knobs) và in ra JSON metric — hiện CHƯA CÓ
    (WfoWorker đi theo jobstore + window tự sinh). Xem ghi chú JavaRangeEvaluator ở cuối file.
    Trả về dict tối thiểu: {"pnl", "maxdd_pct", "calmar", "trades"}; tuỳ chọn "daily": [pnl từng ngày]
    (có thì DSR chuẩn hơn nhiều).
    """

    def evaluate(self, knobs: dict, block: Block) -> dict: ...


# ---------------------------------------------------------------------------
def objective_O(calmars: Sequence[float]) -> float:
    """O = median − 0.5·std (khung v1, ĐANG FROZEN).

    ⚠️ Đã đo được nhược điểm: std là 2 chiều nên fold TỐT BẤT THƯỜNG (Calmar cao do maxDD nhỏ) cũng
    bị phạt. Đo trên EXPLORE 12 fold: median 0.66, std 1.78 -> O = −0.23 dù 12/12 fold đều lãi.
    Muốn đổi sang downside-std/MAD thì PHẢI pre-register v2, không sửa lén ở đây.
    """
    a = np.asarray(list(calmars), dtype=float)
    if a.size == 0:
        return float("nan")
    if a.size == 1:
        return float(a[0])
    return float(np.median(a) - 0.5 * a.std(ddof=1))


def sample_configs(space: dict, n: int, seed: int) -> list[dict]:
    """Bốc n cấu hình tất định từ search space. space: {knob: (lo, hi)} hoặc {knob: [giá trị,...]}.

    Tất định theo seed ⇒ chạy lại ra đúng danh sách cũ ⇒ ledger dedupe được, resume được.
    """
    rng = np.random.default_rng(seed)
    keys = sorted(space)
    out: list[dict] = []
    for _ in range(n):
        cfg = {}
        for k in keys:
            v = space[k]
            if isinstance(v, (list, tuple)) and len(v) == 2 and all(
                    isinstance(x, (int, float)) for x in v) and not isinstance(v, list):
                cfg[k] = float(rng.uniform(v[0], v[1]))
            elif isinstance(v, tuple):
                cfg[k] = float(rng.uniform(v[0], v[1]))
            else:  # danh sách rời rạc
                cfg[k] = v[int(rng.integers(0, len(v)))]
        out.append({k: (round(x, 6) if isinstance(x, float) else x) for k, x in cfg.items()})
    return out


# ---------------------------------------------------------------------------
def run_campaign(*, spec: dict, evaluator: Evaluator, ledger: TrialLedger, campaign: str,
                 dataset_epoch: str, phase: str, blocks: list[Block], n_configs: int,
                 k_test: int = 2, seed: int = 42) -> dict:
    """Chạy trọn 1 campaign. Trả dict kết quả. KHÔNG in verdict pass/fail — caller quyết theo spec."""
    ok, msg = ledger.verify()
    if not ok:
        raise RuntimeError(f"TRIAL LEDGER HONG: {msg} -> moi ket luan DSR/PBO deu vo hieu")
    if phase == "TEST":
        ledger.assert_test_allowed(dataset_epoch, campaign)

    sf = spec_hash(spec)
    configs = sample_configs(spec["search_space"], n_configs, seed)
    logger.info("[HARNESS] campaign=%s spec=%s phase=%s | %d config x %d block = %d backtest",
                campaign, sf, phase, len(configs), len(blocks), len(configs) * len(blocks))

    # --- B1: ma trận (block x config) — mỗi ô đúng 1 backtest, có resume từ ledger -------------
    done: dict[tuple[str, str], dict] = {}
    for rec in ledger.records():
        if rec["campaign"] == campaign and rec["spec"] == sf and rec["dataset_epoch"] == dataset_epoch:
            done[(canonical_json(rec["knobs"]), rec["block"])] = rec["metrics"]

    calmar = np.zeros((len(blocks), len(configs)), dtype=float)
    daily_by_config: dict[int, list[float]] = {c: [] for c in range(len(configs))}
    reused = 0
    for ci, cfg in enumerate(configs):
        key = canonical_json(cfg)
        for b in blocks:
            m = done.get((key, b.name))
            if m is None:
                m = evaluator.evaluate(cfg, b)
                ledger.append(campaign=campaign, phase=phase, spec_fingerprint=sf,
                              dataset_epoch=dataset_epoch, knobs=cfg, block=b.name,
                              metrics=m, seq=ci)
            else:
                reused += 1
            calmar[b.idx, ci] = float(m.get("calmar", 0.0))
            if m.get("daily"):
                daily_by_config[ci].extend(float(x) for x in m["daily"])
    if reused:
        logger.info("[HARNESS] resume: dung lai %d o da co trong so", reused)

    # --- B2: CPCV thuần số học — 28 tổ hợp, inner chọn / outer chỉ đo -------------------------
    n = len(blocks)
    paths: list[dict] = []
    for test_idx in combinations(range(n), k_test):
        train_idx = [i for i in range(n) if i not in test_idx]
        o_train = np.array([objective_O(calmar[train_idx, c]) for c in range(len(configs))])
        winner = int(np.nanargmax(o_train))                      # <- CHỈ nhìn train
        o_test = objective_O(calmar[list(test_idx), winner])     # <- CHỈ đo
        paths.append({"test_blocks": list(test_idx), "winner": winner,
                      "O_train": float(o_train[winner]), "O_test": float(o_test)})

    o_tests = np.array([p["O_test"] for p in paths], dtype=float)
    o_median = float(np.median(o_tests))
    pos_ratio = float(np.mean(o_tests > 0))
    winner_counts: dict[int, int] = {}
    for p in paths:
        winner_counts[p["winner"]] = winner_counts.get(p["winner"], 0) + 1
    winner_stability = max(winner_counts.values()) / len(paths)

    # --- B3: PBO + DSR ------------------------------------------------------------------------
    s_blocks = n if n % 2 == 0 else n - 1
    pbo = pbo_cscv(calmar[:s_blocks], s_blocks=s_blocks) if len(configs) >= 2 else {"pbo": float("nan")}

    best_overall = int(np.nanargmax([objective_O(calmar[:, c]) for c in range(len(configs))]))
    series = daily_by_config[best_overall] or list(calmar[:, best_overall])
    if len(series) < 8:
        logger.warning("[HARNESS] chuoi loi nhuan chi %d diem (<8) -> DSR = nan. "
                       "Evaluator nen tra them key 'daily'.", len(series))
    n_tr = ledger.n_trials(dataset_epoch)

    # sharpe_std_across_trials PHẢI là std của SHARPE giữa các trial — KHÔNG phải std của O.
    # (O tính trên Calmar, khác đơn vị hoàn toàn; truyền nhầm làm sr0 sai bậc ⇒ DSR vô nghĩa.)
    def _sr(xs) -> float:
        a = np.asarray(xs, dtype=float)
        return float(a.mean() / a.std(ddof=1)) if a.size > 1 and a.std(ddof=1) > 0 else 0.0

    per_trial_sr = [_sr(daily_by_config[c] or calmar[:, c]) for c in range(len(configs))]
    sr_std = float(np.std(per_trial_sr, ddof=1)) if len(configs) > 1 else 1.0
    dsr = deflated_sharpe_ratio(np.asarray(series, dtype=float), n_trials=max(2, n_tr),
                                sharpe_std_across_trials=max(1e-6, sr_std))

    res = {
        "campaign": campaign, "spec": sf, "phase": phase, "dataset_epoch": dataset_epoch,
        "n_configs": len(configs), "n_blocks": n, "n_paths": len(paths),
        "O_test_median": o_median,
        "O_test_p25": float(np.percentile(o_tests, 25)),
        "O_test_p75": float(np.percentile(o_tests, 75)),
        "pos_path_ratio": pos_ratio,
        "winner_stability": winner_stability,
        "pbo": pbo.get("pbo"),
        "dsr": dsr.get("dsr"), "sr": dsr.get("sr"), "sr0": dsr.get("sr0"),
        "n_trials_ledger": n_tr,
        "best_overall_config": configs[best_overall],
        "paths": paths,
    }
    logger.info("[HARNESS] O_test median=%.4f (p25=%.4f p75=%.4f) | %%path duong=%.0f%% | "
                "PBO=%.2f DSR=%.3f (n_trials=%d) | winner on dinh=%.0f%%",
                res["O_test_median"], res["O_test_p25"], res["O_test_p75"], pos_ratio * 100,
                res["pbo"], res["dsr"], n_tr, winner_stability * 100)
    return res


def check_pass(res: dict, criteria: dict) -> tuple[bool, list[str]]:
    """Đối chiếu với PASS đã pre-register. Trả (pass, lý do từng tiêu chí)."""
    reasons = []
    ok = True
    for key, (op, thr) in criteria.items():
        v = res.get(key)
        good = (v is not None and not (isinstance(v, float) and math.isnan(v))
                and ((v < thr) if op == "<" else (v > thr) if op == ">" else (v >= thr)))
        ok &= bool(good)
        reasons.append(f"{'✅' if good else '❌'} {key}={v if v is None else round(float(v), 4)} {op} {thr}")
    return ok, reasons


# ---------------------------------------------------------------------------
# JavaRangeEvaluator — CHƯA VIẾT ĐƯỢC, cần thêm 1 entrypoint bên Java.
#
# Cần: com.binance.chuyennd.ai_ml.wfo.framework.CpcvRangeRunner
#      đọc env WFO_RANGE_START/WFO_RANGE_END (ms) + các knob (SIM_*), chạy
#      SimulatorMarketLevelTicker1MStopLoss trên đúng khoảng đó, gọi
#      HPOFitnessCalculatorV4.evaluateDetailed(..., windowDaysActual) rồi in 1 dòng JSON:
#        {"pnl":..,"maxdd_pct":..,"calmar":..,"trades":..,"daily":[..]}
#      (WfoWorker hiện tự sinh window từ DATA_START/TRAIN_MONTHS nên không dùng lại được.)
# Python phía này chỉ subprocess.run([...java...], env=...) rồi json.loads dòng cuối.
# ---------------------------------------------------------------------------


def _selftest() -> None:
    import os
    import tempfile
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    spec = {
        "search_space": {"TP": (0.01, 0.06), "TS_MULT": (1.0, 6.0), "MAX_HOLD_H": (4.0, 240.0)},
        "objective": "median(Calmar_net) - 0.5*std(Calmar_net)",
        "pass": {"pbo": ("<", 0.2), "dsr": (">", 0.95), "O_test_median": (">=", 0.0),
                 "pos_path_ratio": (">=", 0.8)},
    }
    blocks = build_blocks(0, 8 * 90 * 24 * MS_HOUR, n_blocks=8, gap_ms=10 * 24 * MS_HOUR)
    logger.info("[BLOCKS] %d block, gap=10 ngay, block0=[%d,%d)", len(blocks),
                blocks[0].start_ms, blocks[0].end_ms)
    assert blocks[1].start_ms - blocks[0].end_ms == 10 * 24 * MS_HOUR

    class FakeEval:
        """Config có TP thấp = có edge thật, đều qua mọi block. Còn lại là nhiễu."""

        def __init__(self, edge: bool, seed: int):
            self.edge = edge
            self.rng = np.random.default_rng(seed)

        def evaluate(self, knobs, block):
            base = (0.9 if (self.edge and knobs["TP"] < 0.02) else 0.0)
            c = base + self.rng.normal(0, 0.6)
            # sd nhỏ để edge giả đủ mạnh về mặt Sharpe -> DSR phân biệt được (edge thật vs nhiễu)
            return {"pnl": c * 1000, "maxdd_pct": 0.1, "calmar": c, "trades": 120,
                    "daily": list(self.rng.normal(base / 90, 0.05, 90))}

    got: dict[str, dict] = {}
    for tag, edge in (("CO-EDGE", True), ("TOAN-NHIEU", False)):
        with tempfile.TemporaryDirectory() as td:
            led = TrialLedger(os.path.join(td, "t.jsonl"))
            res = run_campaign(spec=spec, evaluator=FakeEval(edge, 7), ledger=led,
                               campaign=f"self-{tag}", dataset_epoch="fake", phase="EXPLORE",
                               blocks=blocks, n_configs=12, k_test=2, seed=1)
            ok, reasons = check_pass(res, spec["pass"])
            logger.info("[%s] PASS=%s | %s", tag, ok, " ; ".join(reasons))
            got[tag] = res
    # winner_stability KHÔNG ép cao: space [0.01,0.06] có ~20% config rơi vào vùng edge, nên inner
    # đổi winner giữa vài config cùng tốt là ĐÚNG, không phải bất ổn.
    assert got["CO-EDGE"]["pbo"] < 0.35 < got["TOAN-NHIEU"]["pbo"]
    assert got["CO-EDGE"]["O_test_median"] > 0.2 > got["TOAN-NHIEU"]["O_test_median"]
    assert got["CO-EDGE"]["dsr"] > 0.8 and got["TOAN-NHIEU"]["dsr"] < 0.5
    logger.info("[SO SANH] edge vs nhieu: PBO %.2f vs %.2f | O_test %.3f vs %.3f | DSR %.3f vs %.3f",
                got["CO-EDGE"]["pbo"], got["TOAN-NHIEU"]["pbo"],
                got["CO-EDGE"]["O_test_median"], got["TOAN-NHIEU"]["O_test_median"],
                got["CO-EDGE"]["dsr"], got["TOAN-NHIEU"]["dsr"])

    # resume: chạy lại cùng campaign phải TÁI DÙNG ô cũ, không đẻ trial mới
    with tempfile.TemporaryDirectory() as td:
        led = TrialLedger(os.path.join(td, "t.jsonl"))
        kw = dict(spec=spec, ledger=led, campaign="resume", dataset_epoch="fake",
                  phase="EXPLORE", blocks=blocks, n_configs=6, k_test=2, seed=3)
        run_campaign(evaluator=FakeEval(True, 1), **kw)
        n1 = led.n_trials("fake")
        run_campaign(evaluator=FakeEval(True, 1), **kw)
        n2 = led.n_trials("fake")
        logger.info("[RESUME] n_trials lan1=%d lan2=%d (phai bang nhau)", n1, n2)
        assert n1 == n2 == 6

    logger.info("HARNESS SELF-TESTS PASSED")


if __name__ == "__main__":
    _selftest()
