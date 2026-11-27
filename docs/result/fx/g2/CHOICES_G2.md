# CHOICES_G2 - DEV choices where PREREG_FX_G2 (+ MASTER chot, ERRATA1-3) is silent or ambiguous (for MASTER / A1)

R1  Re-use by import (no copy, g1/ untouched): load_g1 (quote direction C1, OECD rates, cutoff + --holdout guard,
    is_real flag), sim_g1.run_sim (constant-units engine, carry per calendar day /360, margin 1 %/yr per leg, cost
    EURUSD 0.8 pip else max(3 pip, 3 bp), x2 doubles spread+margin), sim_g1.check_real, eval_g1.metrics / p_value
    (ERRATA3 K1, NaN counted >=) / drop_best_months (ERRATA2 J3). Path via env G1_CODE (default ~/.../g1/code).
R2  Universe(m) = G1 universe (rate m-1 for ccy AND USD, >= 1 valid price in m, no run > 3 missing days, EUR from 1999)
    AND valid FRED price on the signal row T(m) (prereg sec 3). Missing rate => out (MASTER chot).
R3  Signal row T(m) = last row of m with any valid price; execution row = T+1 (next calendar business row); a ccy
    with no price on T+1 trades at its next valid price (G1 engine). Last signal needs a following row.
R4  s(L) = sign(log(Pf[T(m)] / Pf[T(m-L)])) with T(m-L) the signal row of month m-L (Pf = last valid price);
    undefined (no price at T(m-L)) => no position. C = sign(mean(s1, s3, s12)).
R5  vol = std (ddof=1) of the ccy's last 63 valid log returns up to AND including T, x sqrt(252); < 63 returns => no
    position that month.
R6  Value filter: REER narrow basket (BIS 'N', 1964+, EUR = XM) of month m-1 vs mean of months m-60..m-1 (60 values,
    includes m-1; all 60 required else no filter for that ccy-month). Filtered sign -> 0, gross renormalised.
R7  Selection ties: F0 < V10 < V20, then L12 < L3 < L1 < C (prereg "it bien hon; L dai truoc"; C treated as most complex).
R8  Main control (prereg sec 5): per ccy circular shift of the WFO post-filter monthly sign series (168 months, signals
    2005-12..2019-11) by independent k in [12, 156]; positions whose target month is outside the universe dropped;
    same inverse-vol sizing (vols of the target month), costs, engine; N = 1000 (prereg >= 1000; D2 requires >= 1000).
    The control runs start at the 2005-12 signal, so the 'real' statistic for p is the same config run WFO-only
    (real_sharpe_wfo_only); D1 uses the full-run WFO slice. Both reported.
R9  Secondary (descriptive): iid random signs per ccy-month (N_IID = 1000), equal-weight buy-hold (1/n long all ccys
    with a defined signal/vol), F0 same L. Filter-improves-Sharpe-in-both-halves reported "mo ta, ngoai tieu chi".
R10 Criteria: D1 Sharpe > 0.3 ; D2 p <= 0.05 with N >= 1000 ; D3 maxDD <= 25 % ; D4 >= 60 % of configs WFO CAGR > 0 ;
    D5 drop ceil(5 %) best WFO months, compounded rest > 0 ; D6 x2 CAGR > 0. Verdict DAT / CO TIN HIEU (D1+D2) / KHONG DAT.
    If REER were missing, only the 4 F0 configs are evaluated (D4 over 4).
R11 Descriptive splits: TRAIN 1975-1989 / 1990-2005, WFO halves, periods 2006-08 / 2009-12 / 2013-19.
R12 2008-10 real PnL hand check left to A1-results (as ERRATA2 J6); DEV logs 2008-09/10 signal records only.
