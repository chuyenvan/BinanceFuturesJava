# CHOICES_G1 - DEV choices where PREREG_FX_G1 / ERRATA1 is silent or ambiguous (for MASTER / A1 review)

C1  Price convention: every DEX* converted to USD per 1 foreign unit (USD_PER as is: DEXUSEU/UK/AL/NZ; CCY_PER inverted:
    DEXJPUS/SZUS/CAUS/NOUS/SDUS). LONG foreign vs USD earns P_t/P_{t-1}-1. Test (a).
C2  Calendar = union of FRED DEX* rows (all weekdays incl. US holidays with empty value). Rebalance date T(m) = last row of
    month m with >= 1 valid price (holiday rows skipped). A ccy whose price is missing at T trades at its next valid
    price (sec 3); MTM uses forward-filled last valid price (no >3-day staleness occurs 1994-2019 per DATA_REPORT).
C3  Universe(m) at T(m): rate(m-1) + USD rate(m-1) present, >= 1 valid price in month m and no run > 3 missing rows in m,
    only rows <= T (causal). Identical to data/derived/universe_by_month.csv for all 312 months 1994-01..2019-12 (test e).
C4  Carry rates: the rate vector (month m-1) fixed at rebalance T(m) is used for daily carry over the whole holding month
    (sec 6 "r = thang m-1"); i.e. carry uses a 1-2 month old OECD monthly average, not the contemporaneous rate.
    Per leg per calendar day: |notional_{t-1}| * (sign * (r_ccy - r_USD) - 1.0) / 360 / 100 (margin 1 %/yr on every leg).
C5  Positions held in constant foreign-ccy UNITS between trades (weights drift intramonth; rebalance trades the drift back
    to 1/(2k)). Units sized on pre-trade equity; costs deducted after. Gross 1 = of pre-trade equity.
C6  [ERRATA2 J1 applied] Cost: one-way = 0.5 x round trip; EURUSD RT = 0.8 pip / quote; others RT = max(3 pip / quote, 3 bp);
    pip = 0.01 for USDJPY, 0.0001 otherwise. Charged on |delta notional|. Gate-close trades (intramonth gate AND gate
    closing at a rebalance) x2. Scenario x2 doubles spread/commission AND margin (1 -> 2 %/yr).
    (Old flag "3 pip too cheap for USDNOK/SEK/JPY" resolved by ERRATA2 J1; hand answers in test c.)
C7  [ERRATA2 J2 applied] Gate FX_VOL: per-ccy 21-obs realized vol on its own valid prices (log returns, ddof=1,
    x sqrt(252)), equal mean over EVERY ccy with a valid FRED price on row t (EUR from 1999), no rate condition; history
    from 1971. Rows with no valid price at all (US holidays) carry the previous v (DEV choice).
C8  [accepted ERRATA2 J4] Gate VIX: VIX close (16:15 ET) is after the FRED noon fix, so day t uses VIX of the previous row (lag 1). Without the
    lag the gate would look ahead ~4 h. FX_VOL at t uses the noon fix of t and trades at that fix (same as rebalance).
C9  q_t = numpy linear quantile over rows with date in [t - N calendar years, t) (t excluded, holiday rows included,
    NaN dropped). Gate inactive (OFF) when the first valid v is later than t - N years. VIX from 1990 => VIX N3 active
    from 1993; FX_VOL N10 needs vol history from <= 1984.
C10 Gate timing: checked every row; trigger => close all at that row; re-open only at a rebalance where v <= q. If the
    trigger fires ON a rebalance day the new book is not opened (flat, gate flag, x2 cost on closing).
C11 Ranking tie-break: by ccy code (deterministic). Long = top k of d, short = bottom k; need n >= 2k else flat.
C12 Metrics: Sharpe = mean/std of daily returns x sqrt(rows per year) (rows ~261/yr incl. holiday rows, which earn carry);
    "loi suat nam hoa" reported both arithmetic and CAGR; D4, D6, D7 use CAGR / compounded total (stricter sign test).
    maxDD on daily compounded equity; Calmar = CAGR / maxDD; skew on monthly compounded returns.
C13 Random control: same k, same gate arrays, same costs, same engine; at each rebalance draws k long + k short without
    replacement from the universe (numpy default_rng seed 20261126, 500 runs over the full 1994-2019 sim); statistic =
    WFO Sharpe; p = #(random >= real) / 500 (literal "ti le", no +1 correction; n_ge also reported).
C14 Buy-hold control: long 1/n every universe ccy vs USD, monthly rebalanced, carry + costs, no gate.
C15 D5 when selected config is gate OFF: compare best-TRAIN-Sharpe gated config with the same k (prereg note).
    D5 = Calmar(gated) > Calmar(k_OFF) in BOTH 2006-2012 and 2013-2019.
C16 [= ERRATA2 J3] D6: monthly series of selected config on WFO, drop ceil(5 % x months) highest months (168 -> 9),
    compounded remainder > 0.
C17 ERRATA1 H1 descriptive: flags recomputed per day from ECB_eurofxref_cut.csv (|log FRED - log ECB| > 1.5 %, any ccy);
    flagged rows dropped from the selected config's WFO daily series, metrics recomputed (description only, no rule).
C18 Prereg 10.4(iii) hand check 2008-10: on real data only universe / d / ranking / weights are logged (test b,
    HANDCHECK lines). The PnL / cost part of the hand check is done on a synthetic month (test c) because DEV may not
    compute returns on real data; the real 2008-10 PnL hand check is done by A1-results (ERRATA2 J6).
C19 Sim starts with the rebalance at end 1993-12 (first PnL 1994-01). Last rebalance needs a following row (no trade on
    the final row 2019-12-31). TRAIN/WFO slicing is on daily rows by date.

## ERRATA3 (after A1_G1_CODE PASS-WITH-MINOR)
C13 -> [ERRATA3 K1 applied] p = (1 + #(random Sharpe >= real)) / (N + 1); NaN random Sharpe counted as >= (NHO-2, NHO-8).
C20 [K5] eval adds DESCRIPTIVE run "mo ta, ngoai tieu chi": selected config with carry at the rates of the holding row's
    own calendar month (fallback to the signal rate if missing); not in D1-D7.
C21 [K6] test i: q_t exclusion at a non-max v_t, TRAIN-only selection, random runs with selected k+gate, D6 drops best
    months, x2 doubles costs, D1-D7 thresholds as constants + boundary tests, K1 p-value.
C22 [NHO-7] load() marks data is_real; simulate()/evaluate() raise PermissionError on real data without
    real_token=I_HAVE_A1_PASS. build_schedule (positions only) stays allowed for causality tests.
C23 NHO kept as is (A1 noted, not changed): NHO-4 first entry cost on 1993-12-31 outside TRAIN slice; NHO-5 state[]
    1-row offset in % gate time (report only); NHO-6 delayed exec uses new carry diff (no >3-day gap 1994-2019).
