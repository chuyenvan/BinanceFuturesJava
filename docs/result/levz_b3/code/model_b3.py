"""LEVZ B3 step 5 - models (PREREG_LEVZ_B3 sec 5; no HPO, no early stopping, no feature selection).
M1: LightGBM L2 regression, fixed params, seeds 0..9, score = mean of the 10 seeds; sample weight = dot weight.
M2: Ridge(alpha 10) on features mapped to percentile ranks of the TRAIN distribution (NaN -> 0.5, CHOICES_B3), same weights.
OOF on the train set: GroupKFold(5) with groups = calendar quarter (sklearn order, no shuffle). Per-seed OOF and per-seed test
predictions are kept so the single-seed models (P6 / Q6) run the whole procedure on their own (own OOF threshold, own final model).
Thresholds: T20 = 80th pct of OOF scores (unweighted), T10 = 90th pct, T0 = 0 (rule: score > 0)."""
import logging
import numpy as np

log = logging.getLogger('levz_b3.model')
SEEDS = tuple(range(10))
LGB = dict(objective='regression', num_leaves=8, max_depth=3, min_child_samples=100, learning_rate=0.03, n_estimators=300,
           subsample=0.7, subsample_freq=1, colsample_bytree=0.7, reg_lambda=10.0, verbose=-1, deterministic=True,
           force_row_wise=True, n_jobs=4)
RIDGE_ALPHA = 10.0
NFOLD = 5


def fit_m1(X, y, w, seed):
    import lightgbm as lgb
    m = lgb.LGBMRegressor(random_state=int(seed), **LGB)
    m.fit(np.asarray(X, dtype=np.float64), np.asarray(y, dtype=np.float64), sample_weight=np.asarray(w, dtype=np.float64))
    return m


class RankRidge:
    def fit(self, X, y, w):
        from sklearn.linear_model import Ridge
        X = np.asarray(X, dtype=np.float64)
        self.ref = [np.sort(X[np.isfinite(X[:, j]), j]) for j in range(X.shape[1])]
        self.m = Ridge(alpha=RIDGE_ALPHA).fit(self.rank(X), y, sample_weight=w)
        return self

    def rank(self, X):
        X = np.asarray(X, dtype=np.float64)
        R = np.full(X.shape, 0.5)
        for j, srt in enumerate(self.ref):
            v = X[:, j]
            fin = np.isfinite(v)
            if len(srt) == 0:
                continue
            r = (np.searchsorted(srt, v[fin], 'left') + np.searchsorted(srt, v[fin], 'right')) / 2.0 / len(srt)
            R[fin, j] = r
        return R

    def predict(self, X):
        return self.m.predict(self.rank(X))


def _fit(kind, X, y, w, seed):
    if kind == 'M1':
        return fit_m1(X, y, w, seed)
    return RankRidge().fit(X, y, w)


def folds(groups, nfold=NFOLD):
    from sklearn.model_selection import GroupKFold
    groups = np.asarray(groups)
    assert len(np.unique(groups)) >= nfold, 'fewer groups than folds'
    return list(GroupKFold(n_splits=nfold).split(np.zeros(len(groups)), groups=groups))


def train_predict(kind, Xtr, ytr, wtr, gtr, Xte, seeds=SEEDS):
    """returns dict oof_s (nseed, ntr), te_s (nseed, nte), oof, te (seed means), models (final, per seed)."""
    seeds = tuple(seeds) if kind == 'M1' else (0,)
    Xtr = np.asarray(Xtr, dtype=np.float64)
    Xte = np.asarray(Xte, dtype=np.float64)
    fl = folds(gtr)
    oof = np.full((len(seeds), len(ytr)), np.nan)
    te = np.full((len(seeds), len(Xte)), np.nan)
    models = []
    for i, sd in enumerate(seeds):
        for tr, va in fl:
            m = _fit(kind, Xtr[tr], ytr[tr], wtr[tr], sd)
            oof[i, va] = m.predict(Xtr[va])
        m = _fit(kind, Xtr, ytr, wtr, sd)
        models.append(m)
        if len(Xte):
            te[i] = m.predict(Xte)
    assert np.isfinite(oof).all()
    return dict(kind=kind, seeds=seeds, oof_s=oof, te_s=te, oof=oof.mean(axis=0), te=te.mean(axis=0), models=models)


def predict(R, X):
    X = np.asarray(X, dtype=np.float64)
    return np.mean([m.predict(X) for m in R['models']], axis=0)


def thresholds(oof):
    return dict(T20=float(np.quantile(oof, 0.80)), T10=float(np.quantile(oof, 0.90)), T0=0.0)


def select(score, thr_name, thr):
    """T0 rule is score > 0; T20 / T10 are score >= percentile (prereg sec 6)."""
    return score > 0.0 if thr_name == 'T0' else score >= thr


def gain_importance(R, names):
    if R['kind'] != 'M1':
        return {n: float(abs(c)) for n, c in zip(names, R['models'][0].m.coef_)}
    g = np.mean([m.booster_.feature_importance(importance_type='gain') for m in R['models']], axis=0)
    return {n: float(v) for n, v in zip(names, g)}


def wspearman(x, y, w):
    """Spearman with weights: plain average ranks, then weighted Pearson of the ranks (CHOICES_B3)."""
    from scipy.stats import rankdata
    x, y, w = np.asarray(x, float), np.asarray(y, float), np.asarray(w, float)
    if len(x) < 3:
        return np.nan
    rx, ry = rankdata(x), rankdata(y)
    w = w / w.sum()
    mx, my = (w * rx).sum(), (w * ry).sum()
    cov = (w * (rx - mx) * (ry - my)).sum()
    vx, vy = (w * (rx - mx) ** 2).sum(), (w * (ry - my) ** 2).sum()
    return float(cov / np.sqrt(vx * vy)) if vx > 0 and vy > 0 else np.nan
