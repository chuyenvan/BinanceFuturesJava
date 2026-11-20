"""stats3_extra.py - ham bo sung cho S3 (KHONG sua stats.py cua S1).
Dieu kien PASS (e') (S3_MASTER_DECISIONS S3-6): M cua o sau khi bo KHOI 20 ngay KHONG CHONG LAN co tong net LON NHAT cua o do
(khoi dem tu ngay dau cua nua, khoi cuoi cat cho du D ngay - cung phan hoach voi SE goc cua stats.py) phai > 4 bps o CA hai nua.
R2 (MASTER P1): dieu kien (e'') = M sau khi bo CUA SO TRUOT 20 ngay lien tiep co tong net lon nhat > 4 o CA hai nua.
"""
import numpy as np

BLOCK = 20


def block_partition(D, block=BLOCK):
    """[(lo, hi)) cac khoi khong chong lan tu ngay 0; khoi cuoi cat."""
    return [(a, min(a + block, D)) for a in range(0, D, block)]


def drop_top_block(S, N, block=BLOCK):
    """S, N (D, J): tong net / so don vi da khop theo ngay. Tra dict: M_drop (J,), top_block (J,) chi so khoi, top_lo/top_hi
    (ngay trong nua), top_share = tong net khoi do / tong net o (NaN neu tong = 0). Khoi top = argmax tong net (hoa: khoi dau).
    O khong co don vi nao ngoai khoi top -> M_drop NaN (khong qua dieu kien > 4)."""
    S = np.asarray(S, np.float64)
    N = np.asarray(N, np.float64)
    D, J = S.shape
    parts = block_partition(D, block)
    Sb = np.array([S[a:b].sum(0) for a, b in parts])          # (nb, J)
    Nb = np.array([N[a:b].sum(0) for a, b in parts])
    top = np.argmax(Sb, axis=0)
    St, Nt = S.sum(0), N.sum(0)
    S_rest = St - Sb[top, np.arange(J)]
    N_rest = Nt - Nb[top, np.arange(J)]
    with np.errstate(invalid="ignore", divide="ignore"):
        M_drop = np.where(N_rest > 0, S_rest / np.where(N_rest > 0, N_rest, 1.0), np.nan)
        share = np.where(St != 0, Sb[top, np.arange(J)] / np.where(St != 0, St, 1.0), np.nan)
    return dict(M_drop=M_drop, top_block=top, top_lo=np.array([parts[k][0] for k in top]),
                top_hi=np.array([parts[k][1] for k in top]), top_share=share, top_N=Nb[top, np.arange(J)])


def drop_top_window(S, N, win=BLOCK):
    """(e''): bo cua so TRUOT win ngay lien tiep (trong nua) co tong net lon nhat (hoa: cua so som nhat). Khong con don vi -> NaN.
    Tra M_drop (J,), start (J,)."""
    S = np.asarray(S, np.float64)
    N = np.asarray(N, np.float64)
    D, J = S.shape
    w = min(win, D)
    cs = np.vstack([np.zeros((1, J)), np.cumsum(S, 0)])
    cn = np.vstack([np.zeros((1, J)), np.cumsum(N, 0)])
    ws = cs[w:] - cs[:-w]
    wn = cn[w:] - cn[:-w]
    st = np.argmax(ws, axis=0)
    S_rest = S.sum(0) - ws[st, np.arange(J)]
    N_rest = N.sum(0) - wn[st, np.arange(J)]
    with np.errstate(invalid="ignore", divide="ignore"):
        M_drop = np.where(N_rest > 0, S_rest / np.where(N_rest > 0, N_rest, 1.0), np.nan)
    return dict(M_drop=M_drop, start=st)


def mean_excluding_days(S, N, keep):
    """M tren cac ngay keep (bool D)."""
    S = np.asarray(S, np.float64)[keep]
    N = np.asarray(N, np.float64)[keep]
    Nt = N.sum(0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(Nt > 0, S.sum(0) / np.where(Nt > 0, Nt, 1.0), np.nan)
