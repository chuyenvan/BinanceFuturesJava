"""
cpcv_validation.py — Lõi validate chống-leak cho khung đấu (pre-registration v1).
Độc lập pipeline: chỉ nhận (timestamps, label-span, per-period returns/perf) → trả về
  - CombinatorialPurgedCV: sinh các (train_idx, test_idx) với PURGE + EMBARGO (López de Prado, AFML ch.7/12)
  - deflated_sharpe_ratio (DSR, Bailey & López de Prado 2014): điều chỉnh Sharpe theo SỐ TRIAL + skew/kurtosis
  - pbo_cscv (PBO qua CSCV, Bailey et al. 2015): xác suất overfit (config tốt nhất IS lại dưới median OOS)

Không phụ thuộc device/Oracle. Chạy: python3 cpcv_validation.py  -> self-test bằng data giả.
Logging: dùng module `logging` (không print ở phần thư viện), theo rule dự án.
"""
from __future__ import annotations
import logging
from itertools import combinations
from math import comb, erf, sqrt, log
import numpy as np

logger = logging.getLogger("cpcv")

EULER_MASCHERONI = 0.5772156649015329


# ----------------------------------------------------------------------------
# 1) Combinatorial Purged CV  (purge + embargo)
# ----------------------------------------------------------------------------
class CombinatorialPurgedCV:
    """
    Chia N block thời gian liên tiếp, chọn k block làm TEST -> C(N,k) tổ hợp path.
    Mỗi tổ hợp: test = hợp k block; train = phần còn lại SAU KHI:
      - PURGE: bỏ mẫu train có cửa sổ nhãn [t0,t1] chồng lấn bất kỳ khoảng test nào.
      - EMBARGO: bỏ thêm mẫu train nằm trong `embargo` NGAY SAU mỗi khối test (rò rỉ xuôi chiều).
    Tham số:
      t_event : mảng thời điểm ra-quyết-định của mẫu (đơn vị bất kỳ, tăng dần khuyến nghị).
      t_label_end : mảng thời điểm KẾT THÚC cửa sổ nhãn của mẫu (= t_event + horizon).
                    Đây là cốt lõi chống leak label-overlap.
      n_blocks (N), k_test (k), embargo (cùng đơn vị t_event).
    """

    def __init__(self, n_blocks: int, k_test: int, embargo: float = 0.0):
        if k_test < 1 or k_test >= n_blocks:
            raise ValueError("cần 1 <= k_test < n_blocks")
        self.N = n_blocks
        self.k = k_test
        self.embargo = float(embargo)

    def n_paths(self) -> int:
        return comb(self.N, self.k)

    def _blocks(self, n_samples: int):
        # ranh giới block theo CHỈ SỐ mẫu (đã sắp theo thời gian)
        edges = np.linspace(0, n_samples, self.N + 1).astype(int)
        return [(edges[i], edges[i + 1]) for i in range(self.N)]

    def split(self, t_event: np.ndarray, t_label_end: np.ndarray):
        t_event = np.asarray(t_event, dtype=float)
        t_label_end = np.asarray(t_label_end, dtype=float)
        n = len(t_event)
        if len(t_label_end) != n:
            raise ValueError("t_event và t_label_end phải cùng độ dài")
        order = np.argsort(t_event, kind="mergesort")  # ổn định
        inv = np.empty(n, dtype=int); inv[order] = np.arange(n)
        te = t_event[order]; tle = t_label_end[order]
        blocks = self._blocks(n)

        for combo in combinations(range(self.N), self.k):
            test_mask = np.zeros(n, dtype=bool)
            test_intervals = []  # (t_start, t_end) theo thời gian thật của mỗi block test
            for b in combo:
                s, e = blocks[b]
                if e <= s:
                    continue
                test_mask[s:e] = True
                test_intervals.append((te[s], te[e - 1]))
            if not test_intervals:
                continue

            train_mask = ~test_mask
            # PURGE: bỏ train có [t0,t1] = [te, tle] chồng lấn bất kỳ interval test
            for (ts, tend) in test_intervals:
                overlap = train_mask & (tle >= ts) & (te <= tend)
                train_mask &= ~overlap
            # EMBARGO: bỏ train trong (tend, tend+embargo] sau mỗi block test
            if self.embargo > 0:
                for (ts, tend) in test_intervals:
                    emb = train_mask & (te > tend) & (te <= tend + self.embargo)
                    train_mask &= ~emb

            # map ngược về chỉ số gốc (chưa sort)
            train_idx = order[np.flatnonzero(train_mask)]
            test_idx = order[np.flatnonzero(test_mask)]
            yield np.sort(train_idx), np.sort(test_idx)


# ----------------------------------------------------------------------------
# 2) Deflated Sharpe Ratio (DSR)
# ----------------------------------------------------------------------------
def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def _norm_ppf(p: float) -> float:
    # Acklam inverse-normal approximation (đủ chính xác cho DSR)
    if not (0.0 < p < 1.0):
        raise ValueError("p in (0,1)")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = sqrt(-2 * log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > phigh:
        q = sqrt(-2 * log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5; r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def expected_max_sharpe(sharpe_std: float, n_trials: int) -> float:
    """SR kỳ vọng LỚN NHẤT nếu true edge=0, với n_trials thử độc lập (Bailey-LdP)."""
    if n_trials < 2:
        return 0.0
    e = EULER_MASCHERONI
    z1 = _norm_ppf(1.0 - 1.0 / n_trials)
    z2 = _norm_ppf(1.0 - 1.0 / (n_trials * np.e))
    return sharpe_std * ((1 - e) * z1 + e * z2)


def deflated_sharpe_ratio(returns: np.ndarray, n_trials: int,
                          sharpe_std_across_trials: float | None = None) -> dict:
    """
    DSR: xác suất Sharpe quan sát VƯỢT được mức max-kỳ-vọng-dưới-null của n_trials.
    returns: chuỗi lợi nhuận per-period của config THẮNG (để lấy SR, skew, kurtosis, T).
    n_trials: TỔNG số cấu hình đã thử (phải đếm thật — gồm cả lần bỏ).
    sharpe_std_across_trials: std của SR giữa các trial (nếu None -> ước lượng =1, thô).
    Trả: {sr, sr0(=expected max under null), dsr, T}. DSR>0.95 = có bằng chứng.
    """
    r = np.asarray(returns, dtype=float)
    T = len(r)
    if T < 8:
        return {"sr": float("nan"), "sr0": float("nan"), "dsr": float("nan"), "T": T}
    mu, sd = r.mean(), r.std(ddof=1)
    sr = mu / sd if sd > 0 else 0.0
    # moment chuẩn hoá
    z = (r - mu) / sd if sd > 0 else r * 0
    skew = float((z**3).mean())
    kurt = float((z**4).mean())  # kurtosis THÔ (chuẩn=3)
    std_trials = 1.0 if sharpe_std_across_trials is None else float(sharpe_std_across_trials)
    sr0 = expected_max_sharpe(std_trials, n_trials)
    denom = sqrt(max(1e-12, 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr * sr))
    dsr = _norm_cdf((sr - sr0) * sqrt(T - 1) / denom)
    return {"sr": sr, "sr0": sr0, "dsr": dsr, "skew": skew, "kurt": kurt, "T": T}


# ----------------------------------------------------------------------------
# 3) PBO qua CSCV (Probability of Backtest Overfitting)
# ----------------------------------------------------------------------------
def pbo_cscv(perf_matrix: np.ndarray, s_blocks: int = 8) -> dict:
    """
    perf_matrix: (T, C) — hiệu năng per-period của C cấu hình (vd daily Sharpe-contrib / returns).
    Chia T thành S block; với MỌI tổ hợp chọn S/2 block làm IS, phần còn lại OOS:
      - chọn config tốt nhất theo tổng IS -> tìm RANK của nó trong OOS.
      - logit = ln(rank/(1-rank)); PBO = P(logit <= 0) = config best-IS rớt xuống <= median OOS.
    Trả {pbo, n_combos}. PBO < 0.2 = tốt.
    """
    M = np.asarray(perf_matrix, dtype=float)
    T, C = M.shape
    if s_blocks % 2 != 0:
        raise ValueError("s_blocks phải chẵn")
    if C < 2:
        return {"pbo": float("nan"), "n_combos": 0}
    edges = np.linspace(0, T, s_blocks + 1).astype(int)
    blocks = [np.arange(edges[i], edges[i + 1]) for i in range(s_blocks)]
    logits = []
    for is_sel in combinations(range(s_blocks), s_blocks // 2):
        is_idx = np.concatenate([blocks[b] for b in is_sel])
        oos_idx = np.concatenate([blocks[b] for b in range(s_blocks) if b not in is_sel])
        is_perf = M[is_idx].sum(axis=0)
        oos_perf = M[oos_idx].sum(axis=0)
        c_star = int(np.argmax(is_perf))                    # best in IS
        # rank của c_star trong OOS (1=tệ nhất ... C=tốt nhất) -> tỉ lệ (0,1)
        order = np.argsort(oos_perf, kind="mergesort")
        rank = int(np.flatnonzero(order == c_star)[0]) + 1  # 1..C
        w = rank / (C + 1.0)                                 # (0,1)
        logits.append(log(w / (1.0 - w)))
    logits = np.asarray(logits)
    pbo = float((logits <= 0).mean())
    return {"pbo": pbo, "n_combos": len(logits), "logit_mean": float(logits.mean())}


# ----------------------------------------------------------------------------
# SELF-TEST bằng data giả (chứng minh đúng, không cần device)
# ----------------------------------------------------------------------------
def _selftest():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    rng = np.random.default_rng(42)

    # --- CPCV: 1000 mẫu, horizon=20, embargo=10 ---
    n = 1000; horizon = 20
    t_event = np.arange(n, dtype=float)
    t_label_end = t_event + horizon
    cv = CombinatorialPurgedCV(n_blocks=8, k_test=2, embargo=10)
    paths = list(cv.split(t_event, t_label_end))

    def _contiguous_runs(sorted_events):
        # gom các event test thành các đoạn liền mạch (mỗi đoạn = 1 block test)
        runs = []
        start = prev = sorted_events[0]
        for x in sorted_events[1:]:
            if x == prev + 1:
                prev = x
            else:
                runs.append((start, prev)); start = prev = x
        runs.append((start, prev))
        return runs

    # KIỂM leak: train KHÔNG được có [te,tle] chồng lấn BẤT KỲ đoạn test liền mạch nào
    max_overlap = 0
    for tr, te in paths:
        runs = _contiguous_runs(np.sort(t_event[te]).astype(int))
        bad = 0
        for (lo, hi) in runs:
            bad += int(np.sum((t_label_end[tr] >= lo) & (t_event[tr] <= hi)))
        max_overlap = max(max_overlap, bad)
    logger.info("[CPCV] n_paths=%d (kỳ vọng C(8,2)=28)  max train-overlap-test=%d (phải 0)",
                cv.n_paths(), max_overlap)
    assert cv.n_paths() == 28 and max_overlap == 0

    # --- DSR: cùng 1 Sharpe, tăng n_trials -> DSR phải GIẢM (deflate) ---
    r = rng.normal(0.05, 1.0, 500)  # SR ~ 0.05
    d_low = deflated_sharpe_ratio(r, n_trials=1, sharpe_std_across_trials=0.5)
    d_hi = deflated_sharpe_ratio(r, n_trials=500, sharpe_std_across_trials=0.5)
    logger.info("[DSR] sr=%.3f | n=1 -> dsr=%.3f ; n=500 -> dsr=%.3f (phải giảm khi n tăng)",
                d_low["sr"], d_low["dsr"], d_hi["dsr"])
    assert d_hi["dsr"] <= d_low["dsr"]

    # --- PBO: (a) toàn noise -> PBO cao ; (b) 1 config có edge THẬT -> PBO thấp ---
    T, C = 480, 20
    noise = rng.normal(0, 1, (T, C))
    pbo_noise = pbo_cscv(noise, s_blocks=8)
    edge = noise.copy(); edge[:, 0] += 0.5      # config 0 có edge ổn định
    pbo_edge = pbo_cscv(edge, s_blocks=8)
    logger.info("[PBO] noise -> pbo=%.2f (cao) ; có-edge -> pbo=%.2f (thấp)",
                pbo_noise["pbo"], pbo_edge["pbo"])
    assert pbo_edge["pbo"] < pbo_noise["pbo"]

    logger.info("ALL SELF-TESTS PASSED ✅")


if __name__ == "__main__":
    _selftest()
