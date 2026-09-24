"""REGIME_BUILD_MA200 (TASK B2 Buoc 2, docs/prereg/PREREG_REGIME_GATE.md) - sinh file regime causal
MA200-trailing cho GATE_REGIME_ADAPTIVE (khac han regime_build.py cu = BTC ret30, khong sua file
do). KHONG fit tren du lieu sim - MA200 la chuan nganh (trend-following), dd_from_peak365<=-25%
la dinh nghia "bear" pho bien, ca hai khoa TRUOC trong PREREG_REGIME_GATE.md.

Input: CSV daily close BTC (cot utcDay,dateUTC,lastTs,close) da MO RONG ve 2021-01-01 (som nhat
ma kaggle_data_hpo co) qua DumpBtcDaily (khong sua file .java, chi chay lai voi khoang ngay rong
hon). Vi du chi co du lieu tu 2021-01-01, MA200 CHUA DU 200 quan sat cho ~19 ngay dau cua so sim
(2021-07-01..~2021-07-19): dung trailing-window NGAN HON (min_periods=30, con lai la KHONG lookahead,
chi la MA tinh tren it ngay hon 200) - ghi ro han che nay, KHONG anh huong toi tinh causal.

Cong thuc (causal, ap dung cho UTC-day D, dung du lieu <= D-1):
  ma200(D) = mean(close[D-200 .. D-1])  (hoac it hon neu chua du 200, toi thieu 30)
  not_up_ma200(D) = close[D-1] < ma200(D)   [DINH NGHIA CHINH]
  peak365(D)      = max(close[D-365 .. D-1])
  dd365(D)        = close[D-1] / peak365(D) - 1
  not_up_dd25(D)  = dd365(D) <= -0.25        [ROBUSTNESS PHU, chi bao cao]
  regime(D) = "NOTUP" neu not_up_ma200(D) else "UP"   (dung DINH NGHIA CHINH de quyet dinh)
  scale(D)  = 1.70 neu NOTUP else 1.00 (= REGIME_SCALE_NOTUP/UP trong EntryGate, KHONG fit)

Output CSV cot: utcDay,dateUTC,ma200,regime,scale,close,dd365,not_up_dd25,n_obs_ma
(RegimeSchedule.java CHI doc cot 0=utcDay va cot 3=regime - cac cot con lai la audit-only).

Chay: python3 regime_build_ma200.py <btc_daily_close_full.csv> <out_csv>
"""
import csv
import datetime
import sys

DAY = 86400000
MA_WINDOW = 200
MA_MIN_OBS = 30
DD_WINDOW = 365
DD_THRESHOLD = -0.25


def ud(datestr):
    d = datetime.datetime.strptime(datestr, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
    return int(d.timestamp() * 1000 // DAY)


def main():
    src, out = sys.argv[1], sys.argv[2]
    close = {}
    with open(src) as f:
        r = csv.DictReader(f)
        for row in r:
            close[int(row["utcDay"])] = float(row["close"])
    days_have = sorted(close)
    print("close days=%d range=%d..%d (%s..%s)" % (
        len(days_have), days_have[0], days_have[-1],
        datetime.datetime.utcfromtimestamp(days_have[0] * DAY / 1000).date(),
        datetime.datetime.utcfromtimestamp(days_have[-1] * DAY / 1000).date()))

    D0 = ud("2021-06-01")
    D1 = ud("2025-12-31")
    SIM0 = ud("2021-07-01")

    rows = []
    n_partial_ma = 0
    nup = nnu = 0
    for D in range(D0, D1 + 1):
        # trailing window ket thuc tai D-1 (causal: KHONG dung close cua ngay D tro di)
        win_ma = [close[d] for d in range(D - MA_WINDOW, D) if d in close]
        win_dd = [close[d] for d in range(D - DD_WINDOW, D) if d in close]
        c_prev = close.get(D - 1)
        if c_prev is None or len(win_ma) < MA_MIN_OBS:
            raise SystemExit("thieu du lieu causal cho D=%d (c_prev=%s, n_ma=%d)" %
                              (D, c_prev, len(win_ma)))
        ma200 = sum(win_ma) / len(win_ma)
        if len(win_ma) < MA_WINDOW:
            n_partial_ma += 1
        peak365 = max(win_dd) if win_dd else c_prev
        dd365 = c_prev / peak365 - 1.0
        not_up_ma200 = c_prev < ma200
        not_up_dd25 = dd365 <= DD_THRESHOLD
        reg = "NOTUP" if not_up_ma200 else "UP"
        scale = "1.70" if reg == "NOTUP" else "1.00"
        dt = datetime.datetime.utcfromtimestamp(D * DAY / 1000).strftime("%Y-%m-%d")
        rows.append((D, dt, "%.4f" % ma200, reg, scale, "%.4f" % c_prev,
                     "%.4f" % dd365, "1" if not_up_dd25 else "0", len(win_ma)))
        if D >= SIM0:
            if reg == "UP":
                nup += 1
            else:
                nnu += 1

    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["utcDay", "dateUTC", "ma200", "regime", "scale", "close_prevday",
                    "dd365", "not_up_dd25", "n_obs_ma"])
        w.writerows(rows)

    tot = nup + nnu
    print("wrote %d rows -> %s (partial-MA ngay <200 obs trong toan bo output: %d)" %
          (len(rows), out, n_partial_ma))
    print("SIM-range(%s..%s) days=%d UP=%d(%.1f%%) NOTUP=%d(%.1f%%)" % (
        "2021-07-01", "2025-12-31", tot, nup, 100 * nup / tot, nnu, 100 * nnu / tot))

    from collections import Counter
    yc, yu = Counter(), Counter()
    yd25 = Counter()
    for (D, dt, ma, reg, sc, cprev, dd365, nd25, nobs) in rows:
        if D < SIM0:
            continue
        y = dt[:4]
        yc[y] += 1
        if reg == "UP":
            yu[y] += 1
        if nd25 == "1":
            yd25[y] += 1
    print("Theo nam (MA200) UP%% | (robustness) %%ngay dd365<=-25%%:")
    for y in sorted(yc):
        print("  %s: UP %d/%d = %.1f%% | dd25 %d/%d = %.1f%%" % (
            y, yu[y], yc[y], 100 * yu[y] / yc[y], yd25[y], yc[y], 100 * yd25[y] / yc[y]))


if __name__ == "__main__":
    main()
