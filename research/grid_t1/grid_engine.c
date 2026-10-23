/* GRID_T1 engine: G-RANGE (arithmetic S/R grid, fixed size, hard stop, ADX filter)
 *                G-DYN   (paper 2506.11921 dynamic grid; geometric or arithmetic levels)
 * 1m bars, long-only, no leverage. Limit fills on touch (low<buy / high>sell).
 * Funding applied on inventory at real funding timestamps.
 * Also provides a block-bootstrap random-walk path generator (block = B bars).
 *
 * Build: gcc -O3 -march=native -shared -fPIC -o libgridsim.so grid_engine.c -lm
 */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define MAXLEV 11
#define RING 336

typedef struct {
    int64_t day_ts;
    double eq;
} DayRec;

typedef struct {
    long trades, stops, stops_lo, stops_hi, stops_adx, builds, active_bars, all_bars;
    double fees, funding, turnover, inv_sum;
} Stats;

static inline uint64_t sm64(uint64_t x) {
    x += 0x9E3779B97F4A7C15ULL;
    x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9ULL;
    x = (x ^ (x >> 27)) * 0x94D049BB133111EBULL;
    return x ^ (x >> 31);
}

/* ---------------- RANGE ---------------- */
typedef struct {
    double cash, coin;
    double lot_amt;
    double lvl[MAXLEV];
    int armed[10];
    double qty[10];
    int active;
    int64_t off_until;
    double lo, hi, step;
    double ring_h[RING], ring_l[RING];
    int hp, hcnt;
    double cur_hh, cur_ll;
    int hour_bars;
    /* 4h ADX */
    double atr, spdm, sndm, adx;
    double ph, pl, pc;
    int nb, have_adx;
    int h4;
    double h4o, h4h, h4l, h4c;
} Range;

static void range_build(Range *r, double lo, double hi, double px, double fee, double M) {
    r->lo = lo; r->hi = hi;
    r->step = (hi - lo) / 10.0;
    for (int i = 0; i < MAXLEV; i++) r->lvl[i] = lo + r->step * i;
    r->lot_amt = M / 10.0;
    r->coin = 0.0;
    for (int i = 0; i < 10; i++) {
        r->qty[i] = 0.0;
        r->armed[i] = (r->lvl[i] < px) ? 1 : 0;
    }
    r->active = 1;
}

static void range_flat(Range *r, double px, double fee_taker, Stats *st) {
    if (r->coin > 0) {
        double v = r->coin * px;
        r->cash += v * (1.0 - fee_taker);
        st->fees += v * fee_taker;
        st->turnover += v;
        r->coin = 0;
    }
    for (int i = 0; i < 10; i++) { r->qty[i] = 0.0; r->armed[i] = 0; }
    r->active = 0;
}

static void adx_push(Range *r, double h, double l, double c) {
    if (r->h4 == 0) { r->h4o = c; r->h4h = h; r->h4l = l; }
    else { if (h > r->h4h) r->h4h = h; if (l < r->h4l) r->h4l = l; }
    r->h4c = c; r->h4++;
    if (r->h4 < 4) return;
    double H = r->h4h, L = r->h4l, C = r->h4c;
    double tr = H - L;
    double a1 = fabs(H - r->pc), a2 = fabs(L - r->pc);
    if (a1 > tr) tr = a1;
    if (a2 > tr) tr = a2;
    double up = H - r->ph, dn = r->pl - L;
    double pdm = (up > dn && up > 0) ? up : 0.0;
    double ndm = (dn > up && dn > 0) ? dn : 0.0;
    if (r->nb == 0) { r->atr = tr; r->spdm = pdm; r->sndm = ndm; }
    else {
        r->atr = (r->atr * 13.0 + tr) / 14.0;
        r->spdm = (r->spdm * 13.0 + pdm) / 14.0;
        r->sndm = (r->sndm * 13.0 + ndm) / 14.0;
    }
    if (r->atr > 1e-12) {
        double pdi = 100.0 * r->spdm / r->atr;
        double ndi = 100.0 * r->sndm / r->atr;
        double dx = 100.0 * fabs(pdi - ndi) / (pdi + ndi + 1e-12);
        if (r->nb >= 13) {
            if (!r->have_adx) { r->adx = dx; r->have_adx = 1; }
            else r->adx = (r->adx * 13.0 + dx) / 14.0;
        }
    }
    r->nb++;
    r->ph = H; r->pl = L; r->pc = C;
    r->h4 = 0;
}

static void range_buys(Range *r, double low, double fee, Stats *st) {
    for (int i = 9; i >= 0; i--) {
        if (r->lvl[i] <= low) break;
        if (!r->armed[i]) continue;
        if (r->cash < r->lot_amt - 1e-15) continue;
        r->cash -= r->lot_amt;
        r->qty[i] = r->lot_amt * (1.0 - fee) / r->lvl[i];
        r->coin += r->qty[i];
        r->armed[i] = 0;
        st->trades++; st->fees += r->lot_amt * fee; st->turnover += r->lot_amt;
    }
}

static void range_sells(Range *r, double high, double fee, Stats *st) {
    for (int i = 0; i < 10; i++) {
        if (r->qty[i] <= 0.0) continue;
        double s = r->lvl[i + 1];
        if (high <= s) continue;
        double v = r->qty[i] * s;
        r->cash += v * (1.0 - fee);
        st->fees += v * fee;
        st->turnover += v;
        r->coin -= r->qty[i];
        r->qty[i] = 0.0;
        r->armed[i] = 1;
        st->trades++;
    }
}

/* ---------------- DYN ---------------- */
typedef struct {
    double cash, coin, principal, wallet, money_input;
    double lvl[MAXLEV];
    int L;
    double k;
    int variant; /* 0 geometric, 1 arithmetic */
} Dyn;

static void dyn_levels(Dyn *d, double P) {
    if (d->variant == 0) {
        for (int i = 0; i < MAXLEV; i++) d->lvl[i] = P * pow(1.0 + d->k, (double)(i - 5));
    } else {
        for (int i = 0; i < MAXLEV; i++) d->lvl[i] = P + (double)(i - 5) * P * d->k;
    }
    d->L = 5;
}

static void dyn_start(Dyn *d, double P, double cap, double fee, int fresh_coin) {
    /* cap = grid principal; buy half of it at P (already-held coin stays) */
    d->principal = cap;
    dyn_levels(d, P);
    if (!fresh_coin) {
        double buy = cap * 0.5;
        if (buy > d->cash) buy = d->cash;
        d->coin += buy * (1.0 - fee) / P;
        d->cash -= buy;
    }
}

/* ---------------- main sim ---------------- */
/* mode: 0 RANGE, 1 DYN.  variant: DYN 0 geometric / 1 arithmetic.
 * i_start..i_end = evaluation window (i_end exclusive). i_hist = start of history scan.
 * Returns number of daily records. */
int grid_sim(const float *o, const float *h, const float *l, const float *c, int n,
             int64_t ts0, int i_hist, int i_start, int i_end,
             int mode, int variant, double fee, double fee_taker, double M,
             const int64_t *fts, const double *frat, int nf,
             int64_t *day_ts, double *day_eq, int maxday,
             double *stats_out /* [trades,stops,fees,funding,turnover,0,0,0] */
             , uint64_t seed, int boot, const float *ro, const float *rh,
             const float *rl, const float *rc)
{
    Stats st; memset(&st, 0, sizeof(st));
    Range r; Dyn d;
    float *bo = NULL, *bh = NULL, *bl = NULL, *bc = NULL;
    if (boot) {
        bo = malloc(sizeof(float) * (size_t)(i_end - i_hist));
        bh = malloc(sizeof(float) * (size_t)(i_end - i_hist));
        bl = malloc(sizeof(float) * (size_t)(i_end - i_hist));
        bc = malloc(sizeof(float) * (size_t)(i_end - i_hist));
        if (!bo || !bh || !bl || !bc) return -1;
        /* start price = real close at i_hist-1 */
        double px = (double)c[i_hist > 0 ? i_hist - 1 : 0];
        const int B = 60;
        uint64_t rs = seed;
        int k = 0;
        while (k < i_end - i_hist) {
            int span = i_end - i_hist - k;
            int blk = span < B ? span : B;
            /* sample a start such that the whole block is inside [i_hist, i_end) */
            rs = sm64(rs);
            int avail = i_end - i_hist - blk;
            int s0 = i_hist + (int)(rs % (uint64_t)(avail > 0 ? avail + 1 : 1));
            for (int j = 0; j < blk; j++) {
                int si = s0 + j;
                double op = px * (double)ro[si];
                double hi = px * (double)rh[si];
                double lo = px * (double)rl[si];
                double cl = px * (double)rc[si];
                if (hi < op) hi = op;
                if (hi < cl) hi = cl;
                if (lo > op) lo = op;
                if (lo > cl) lo = cl;
                bo[k + j] = (float)op; bh[k + j] = (float)hi;
                bl[k + j] = (float)lo; bc[k + j] = (float)cl;
                px = cl;
            }
            k += blk;
        }
        o = bo; h = bh; l = bl; c = bc;
    }

    /* ---- init ---- */
    memset(&r, 0, sizeof(r));
    memset(&d, 0, sizeof(d));
    if (mode == 0) {
        r.cash = M;
        r.cur_hh = -1e300; r.cur_ll = 1e300;
        r.ph = r.pl = r.pc = 0; r.nb = 0;
        for (int i = 0; i < RING; i++) { r.ring_h[i] = 0; r.ring_l[i] = 0; }
    } else {
        d.cash = M; d.coin = 0; d.wallet = 0; d.money_input = M;
        d.k = 0.02; d.variant = variant;
        dyn_start(&d, (double)c[i_start], M, fee, 0);
    }

    int nd = 0;
    int fi = 0;
    if (nf > 0) { while (fi < nf && fts[fi] < ts0 + (int64_t)i_hist * 60000) fi++; }

    int have_init = 0;
    double eq_prev = M;
    (void)eq_prev;

    for (int i = i_hist; i < i_end; i++) {
        double op = (double)o[i], hi = (double)h[i], lo = (double)l[i], cl = (double)c[i];
        int64_t t = ts0 + (int64_t)i * 60000;

        /* hourly aggregate */
        if (mode == 0) {
            if (hi > r.cur_hh) r.cur_hh = hi;
            if (lo < r.cur_ll) r.cur_ll = lo;
            r.hour_bars++;
            adx_push(&r, hi, lo, cl);
        }

        if (i >= i_start) {
            if (mode == 0) {
                if (r.active) {
                    if (cl < op) { range_sells(&r, hi, fee, &st); range_buys(&r, lo, fee, &st); }
                    else { range_buys(&r, lo, fee, &st); range_sells(&r, hi, fee, &st); }
                }
            } else {
                if (cl < op) {
                    while (d.L > 0 && lo < d.lvl[d.L - 1]) {
                        d.L--;
                        double G = (double)(d.L + 1);
                        double spend = d.cash / G;
                        d.coin += spend * (1.0 - fee) / d.lvl[d.L];
                        st.fees += spend * fee; st.turnover += spend; st.trades++;
                        d.cash -= spend;
                    }
                    while (d.L < 10 && hi > d.lvl[d.L + 1]) {
                        d.L++;
                        double G = (double)(10 - d.L + 1);
                        double q = d.coin / G;
                        double v = q * d.lvl[d.L];
                        d.cash += v * (1.0 - fee);
                        st.fees += v * fee; st.turnover += v; st.trades++;
                        d.coin -= q;
                    }
                } else {
                    while (d.L < 10 && hi > d.lvl[d.L + 1]) {
                        d.L++;
                        double G = (double)(10 - d.L + 1);
                        double q = d.coin / G;
                        double v = q * d.lvl[d.L];
                        d.cash += v * (1.0 - fee);
                        st.fees += v * fee; st.turnover += v; st.trades++;
                        d.coin -= q;
                    }
                    while (d.L > 0 && lo < d.lvl[d.L - 1]) {
                        d.L--;
                        double G = (double)(d.L + 1);
                        double spend = d.cash / G;
                        d.coin += spend * (1.0 - fee) / d.lvl[d.L];
                        st.fees += spend * fee; st.turnover += spend; st.trades++;
                        d.cash -= spend;
                    }
                }
                /* resets at bar close */
                if (cl > d.lvl[10] || d.L == 10) {
                    double eq = d.cash + d.coin * cl;
                    double v = d.coin * cl;
                    d.cash += v * (1.0 - fee_taker); st.fees += v * fee_taker; st.turnover += v;
                    d.coin = 0;
                    double cap = d.cash < M ? d.cash : M;
                    d.wallet += d.cash - cap;
                    d.cash = cap;
                    dyn_start(&d, cl, cap, fee, 0);
                    st.stops++;
                    (void)eq;
                } else if (cl < d.lvl[0] || d.L == 0) {
                    double pr = d.wallet; d.wallet = 0;
                    if (pr < 0.01 * M) { double inj = 0.01 * M - pr; d.money_input += inj; d.cash += inj; pr = 0.01 * M; }
                    dyn_start(&d, cl, pr, fee, 0);
                    st.stops++;
                }
            }
        }

        if (i >= i_start) {
            st.all_bars++;
            double iv = (mode == 0) ? r.coin : d.coin;
            st.inv_sum += iv * cl;
            if (mode == 0 && r.active) st.active_bars++;
        }
        /* funding */
        while (fi < nf && fts[fi] <= t + 60000) {
            double inv = (mode == 0) ? r.coin : d.coin;
            if (inv > 0) {
                double notional = inv * cl;
                double pay = frat[fi] * notional;
                if (mode == 0) r.cash -= pay; else d.cash -= pay;
                st.funding += pay;
            }
            fi++;
        }

        /* hourly decisions */
        if (mode == 0 && ((i + 1) % 60 == 0)) {
            /* push completed hour */
            r.hp = (r.hp + 1) % RING;
            r.ring_h[r.hp] = r.cur_hh; r.ring_l[r.hp] = r.cur_ll;
            if (r.hcnt < RING) r.hcnt++;
            r.cur_hh = -1e300; r.cur_ll = 1e300;
            int trend = (r.have_adx && r.adx >= 20.0);
            if (i >= i_start) {
                if (r.active) {
                    if (cl < r.lo - r.step) { range_flat(&r, cl, fee_taker, &st); st.stops++; st.stops_lo++; r.off_until = t + 86400000; }
                    else if (cl > r.hi + r.step) { range_flat(&r, cl, fee_taker, &st); st.stops++; st.stops_hi++; r.off_until = t + 86400000; }
                    else if (trend) { range_flat(&r, cl, fee_taker, &st); st.stops++; st.stops_adx++; r.off_until = t + 86400000; }
                } else if (t >= r.off_until && !trend && r.hcnt >= RING) {
                    double lo2 = 1e300, hi2 = -1e300;
                    for (int j = 0; j < RING; j++) {
                        if (r.ring_h[j] > hi2) hi2 = r.ring_h[j];
                        if (r.ring_l[j] < lo2) lo2 = r.ring_l[j];
                    }
                    if (cl >= lo2 && cl <= hi2 && hi2 > lo2) {
                        range_build(&r, lo2, hi2, cl, fee_taker, M);
                        st.builds++;
                    }
                }
            } else if (i < i_start) {
                /* build at period start handled below (first bar of period) */
            }
        }

        if (i == i_start && mode == 0) {
            if (r.hcnt >= RING) {
                double lo2 = 1e300, hi2 = -1e300;
                for (int j = 0; j < RING; j++) {
                    if (r.ring_h[j] > hi2) hi2 = r.ring_h[j];
                    if (r.ring_l[j] < lo2) lo2 = r.ring_l[j];
                }
                int trend = (r.have_adx && r.adx >= 20.0);
                if (!trend && cl >= lo2 && cl <= hi2 && hi2 > lo2) { range_build(&r, lo2, hi2, cl, fee_taker, M); st.builds++; }
                else { r.active = 0; r.off_until = t; }
            }
        }

        /* record day end */
        if (i >= i_start && ((i + 1) % 1440 == 0 || i == i_end - 1)) {
            if (nd < maxday) {
                double eq;
                if (mode == 0) eq = r.cash + r.coin * cl;
                else eq = d.cash + d.coin * cl;
                day_ts[nd] = t + 60000;
                day_eq[nd] = eq;
                nd++;
                have_init = 1;
            }
        }
    }

    if (boot) { free(bo); free(bh); free(bl); free(bc); }
    stats_out[0] = (double)st.trades;
    stats_out[1] = (double)st.stops;
    stats_out[2] = st.fees;
    stats_out[3] = st.funding;
    stats_out[4] = st.turnover;
    stats_out[5] = (mode == 0) ? r.cash : d.cash;
    stats_out[6] = (mode == 0) ? r.coin : d.coin;
    stats_out[7] = (mode == 0) ? (double)r.active : d.principal;
    stats_out[8] = (double)st.stops_lo;
    stats_out[9] = (double)st.stops_hi;
    stats_out[10] = (double)st.stops_adx;
    stats_out[11] = (double)st.builds;
    stats_out[12] = (double)st.active_bars;
    stats_out[13] = st.all_bars > 0 ? st.inv_sum / (double)st.all_bars : 0.0;
    stats_out[14] = (double)st.all_bars;
    stats_out[15] = 0.0;
    return nd;
}

/* Convenience wrappers for ctypes (avoid 20-arg call style in Python). */
typedef struct {
    const float *o, *h, *l, *c;
    const float *ro, *rh, *rl, *rc;
    int n; int64_t ts0;
    int i_hist, i_start, i_end;
    int mode, variant, boot;
    double fee, fee_taker, M;
    const int64_t *fts; const double *frat; int nf;
    int64_t *day_ts; double *day_eq; int maxday;
    double *stats; uint64_t seed;
} SimArgs;

int grid_sim_args(const SimArgs *a) {
    return grid_sim(a->o, a->h, a->l, a->c, a->n, a->ts0, a->i_hist, a->i_start, a->i_end,
                    a->mode, a->variant, a->fee, a->fee_taker, a->M,
                    a->fts, a->frat, a->nf, a->day_ts, a->day_eq, a->maxday,
                    a->stats, a->seed, a->boot, a->ro, a->rh, a->rl, a->rc);
}
