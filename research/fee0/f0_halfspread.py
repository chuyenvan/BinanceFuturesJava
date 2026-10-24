"""FEE0 step0(d) -> half_spread.json: hs[sym] = 0.5 * mean over sampled days of (time-sampled 1s mean relative spread), fraction.
ALT_DEFAULT = max hs over measured USDC alts (khong gom BTC/ETH) -> bao thu cho symbol khong co bookTicker."""
import json, os
WK = os.path.expanduser("~/claude_master/fee0_wk")
d = json.load(open(WK + "/step0_d.json"))["bookTicker"]
acc = {}
for k, v in d.items():
    s = k.split("|")[0]
    acc.setdefault(s, []).append(v["spread_bps_mean"])
hs = {s: 0.5 * sum(x) / len(x) * 1e-4 for s, x in acc.items()}
alts = [v for s, v in hs.items() if s.endswith("USDC") and s not in ("BTCUSDC", "ETHUSDC")]
hs["ALT_DEFAULT"] = max(alts)
json.dump(hs, open(WK + "/half_spread.json", "w"), indent=1)
for s, v in sorted(hs.items(), key=lambda x: x[1]):
    print(f"{s:14s} hs {v*1e4:.4f} bps  n_days {len(acc.get(s, []))}")
