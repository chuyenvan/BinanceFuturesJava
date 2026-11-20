"""stats.py - thong ke Giai doan 1 (PREREG_GRIDV2_S1_DRAFT3 muc 7): M theo o, circular block bootstrap 20 ngay lich (chon lai
ca mat cat coin), bootstrap-t STUDENTIZED (moi replicate chia SE* uoc tu tong khoi cua CHINH replicate do - R3-1),
Romano-Wolf stepdown max-t (FWER danh nghia ALPHA_FWER = 4 %), can tren dong thoi max-t (ALPHA_UPPER = 5 % -> 95 %, R3-2),
nhan INSUFFICIENT (R3-3, R4-2: < 200 don vi | khoi co don vi < ceil(nb/3) | M khong huu han | SE goc = 0) va o INSUFFICIENT
bi LOAI khoi max-t moi buoc RW + can tren (R4-1); replicate SE* = 0 / khong don vi -> t* = 0 (R4-2), MDE.
Dau vao: ma tran theo NGAY x O: S (tong PnL bps cua don vi da khop dat ngay do) va N (so don vi da khop).
SE goc: tong theo khoi KHONG chong lan 20 ngay (khoi cuoi cat cho du D): SE = sqrt(sum_b (S_b - M N_b)^2) / sum N.
SE*: cung cong thuc tren cac khoi da chon cua replicate. t = (M - san) / SE; t*_j = (M*_j - M_j) / SE*_j.
"""
import warnings
import numpy as np
from math import erf, sqrt

BLOCK = 20          # ngay; >= do ben che do thang (phan bien N8)
NBOOT = 2000
ALPHA_FWER = 0.04   # R3-1: FWER danh nghia co dinh (prereg)
ALPHA_UPPER = 0.05  # R3-2: can tren dong thoi 95 % cho L-A (hang so rieng)
MIN_UNITS = 200     # R3-3: o co < 200 don vi da khop trong nua -> INSUFFICIENT
MIN_BLOCK_FRAC_DEN = 3  # R4-2 (ii): so khoi khong chong lan co don vi < ceil(tong khoi / 3) -> INSUFFICIENT
Z80 = 0.8416212335729143


def norm_sf(z):
    return 0.5 * (1.0 - erf(z / sqrt(2.0)))


def block_lengths(D, block=BLOCK):
    nb = -(-D // block)
    ln = np.full(nb, block, np.int64)
    ln[-1] = D - block * (nb - 1)
    return ln


def block_sums(X, starts, block, D):
    """X (D, J); starts (B, nb) chi so ngay bat dau (vong tron). Tra tong theo khoi (B, nb, J); khoi cuoi dai D - block*(nb-1)."""
    X = np.asarray(X, np.float64)
    cs = np.vstack([np.zeros((1, X.shape[1])), np.cumsum(np.vstack([X, X]), 0)])
    e = starts + block_lengths(D, block)[None, :]
    return cs[e] - cs[starts]


def block_indices(rng, D, B, block=BLOCK):
    """Circular block bootstrap (Politis-Romano 1992): (B, D) chi so ngay (dung cho kiem tra / tham khao)."""
    nb = -(-D // block)
    st = rng.integers(0, D, size=(B, nb))
    idx = (st[:, :, None] + np.arange(block)[None, None, :]) % D
    return idx.reshape(B, nb * block)[:, :D]


def _se_from_blocks(Sb, Nb):
    """Sb, Nb (..., nb, J) -> M (..., J), SE (..., J)."""
    Nt = Nb.sum(-2)
    with np.errstate(invalid="ignore", divide="ignore"):
        M = np.where(Nt > 0, Sb.sum(-2) / np.where(Nt > 0, Nt, 1.0), np.nan)
        u = Sb - M[..., None, :] * Nb
        SE = np.where(Nt > 0, np.sqrt((u * u).sum(-2)) / np.where(Nt > 0, Nt, 1.0), np.nan)
    return M, SE


def tstar(Ms, Mt, SEs):
    """t*_r = (M*_r - M) / SE*_r; R4-2: SE*_r = 0 hoac replicate khong co don vi (M* / SE* khong huu han) -> t* = 0."""
    with np.errstate(invalid="ignore", divide="ignore"):
        tb = (Ms - np.asarray(Mt)[None, :]) / SEs
    ok = np.isfinite(Ms) & np.isfinite(SEs) & (SEs > 0) & np.isfinite(tb)
    return np.where(ok, tb, 0.0)


def cell_stats(S, N, floor, seed, B=NBOOT, block=BLOCK, alpha=ALPHA_FWER, alpha_upper=ALPHA_UPPER, min_units=MIN_UNITS):
    """Thong ke cho mot ho o (cung tap ngay). H0_j: M_j <= floor. Tra M, SE, t, p_marg (1 phia, bootstrap-t studentized),
    p_rw (Romano-Wolf stepdown max-t), rw_reject (p_rw <= alpha), can tren dong thoi (1 - alpha_upper), insufficient."""
    S = np.asarray(S, np.float64)
    N = np.asarray(N, np.float64)
    D, J = S.shape
    rng = np.random.default_rng(seed)
    nb = -(-D // block)
    st0 = (np.arange(nb, dtype=np.int64) * block)[None, :]
    N0 = block_sums(N, st0, block, D)[0]
    Mt, SE = _se_from_blocks(block_sums(S, st0, block, D)[0], N0)
    Ntot = N.sum(0)
    nblk_units = (N0 > 0).sum(0)
    min_blocks = -(-nb // MIN_BLOCK_FRAC_DEN)
    ins_i = ~(Ntot >= min_units)
    ins_ii = nblk_units < min_blocks
    ins_iii = ~np.isfinite(Mt) | ~np.isfinite(SE) | ~(SE > 0)
    insuff = ins_i | ins_ii | ins_iii
    with np.errstate(invalid="ignore", divide="ignore"):
        t = np.where(insuff, -np.inf, (Mt - floor) / np.where(SE > 0, SE, 1.0))
    starts = rng.integers(0, D, size=(B, nb))
    Ms, SEs = _se_from_blocks(block_sums(S, starts, block, D), block_sums(N, starts, block, D))
    tb = tstar(Ms, Mt, SEs)
    ok = ~insuff
    p_marg = np.array([np.mean(tb[:, j] >= t[j]) if ok[j] else np.nan for j in range(J)])
    # Romano-Wolf stepdown CHI tren o du du lieu (R4-1): o INSUFFICIENT p_rw = 1, t* KHONG vao max
    order = [j for j in np.argsort(-t, kind="stable") if ok[j]]
    p_rw = np.ones(J)
    prev = 0.0
    for r, j in enumerate(order):
        mx = tb[:, order[r:]].max(1)
        p = max(prev, float(np.mean(mx >= t[j])))
        p_rw[j] = p
        prev = p
    rej = (p_rw <= alpha) & ~insuff
    crit_all = float(np.quantile(tb[:, ok].max(1), 1 - alpha)) if ok.any() else np.nan
    # can tren dong thoi (max-t cua -t*, chi tren o du du lieu); o INSUFFICIENT: NaN
    if ok.any():
        c_up = float(np.quantile((-tb[:, ok]).max(1), 1 - alpha_upper))
    else:
        c_up = np.nan
    upper = np.where(ok, Mt + c_up * SE, np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        tbf = tb
        q_hi = np.nanquantile(tbf, 0.975, axis=0)
        q_lo = np.nanquantile(tbf, 0.025, axis=0)
        sd_boot = np.nanstd(Ms, axis=0, ddof=1)
    lo95 = np.where(ok, Mt - q_hi * SE, np.nan)
    hi95 = np.where(ok, Mt - q_lo * SE, np.nan)
    mde = (crit_all + Z80) * SE
    return dict(M=Mt, SE=SE, SE_boot_sd=sd_boot, t=t, p_marg=p_marg, p_rw=p_rw, rw_reject=rej,
                insufficient=insuff, insufficient_reason=["+".join(k for k, f in (("i", a), ("ii", b), ("iii", c)) if f)
                                                          for a, b, c in zip(ins_i, ins_ii, ins_iii)],
                n_blocks=nb, min_blocks_with_units=min_blocks, n_blocks_with_units=nblk_units, crit_rw=crit_all, c_upper=c_up, upper_sim95=upper, ci95_lo=lo95, ci95_hi=hi95,
                mde_above_floor=mde, n_units=Ntot, n_days_with_units=(N > 0).sum(0), D=D, B=B, block=block, seed=seed,
                alpha=alpha, alpha_upper=alpha_upper, min_units=min_units, method="studentized_block_bootstrap_RW_maxt")


def single_p(S, N, floor, seed, B=NBOOT, block=BLOCK, min_units=MIN_UNITS):
    """p 1 phia cho 1 o (nua XAC NHAN A): H0 M <= floor, bootstrap-t studentized. INSUFFICIENT -> p NaN."""
    r = cell_stats(np.asarray(S)[:, None], np.asarray(N)[:, None], floor, seed, B, block, min_units=min_units)
    return float(r["M"][0]), float(r["SE"][0]), float(r["p_marg"][0])
