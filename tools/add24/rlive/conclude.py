#!/usr/bin/env python3
"""ADD24 gop ket luan prereg s10 phan R-LIVE BANG SCRIPT (ERRATA3 A1 / A1 m8).
BB: L-E, L-N, L-S, L-S2, L-K (L0) + L-E, L-N, L-S, L-S2 (L0-DRY, cung tieu chi entry/size). BB co phu: L-D (phu: C0b S-DCA va R-SIM S-D),
L-T / L-SL / L-X (phu: R-SIM S-X va C0b). FAIL > INSUFFICIENT > PASS; INSUFFICIENT co phu chi khi MOI muc phu PASS. Cong V truot => HUY.
usage: conclude.py --gates gates.json --score score_L0/score.json [--score-dry score_L0DRY/score.json] [--c0b C0B.json] [--rsim rsim.json] --out
  rsim.json: {"S-X": "PASS|FAIL|INSUFFICIENT", "S-D": "...", ...} (DEV-B / MASTER cung cap; thieu => muc phu = CHUA CO)
"""
import argparse, json

BB = ('L-E', 'L-N', 'L-S', 'L-S2', 'L-K')
BB_DRY = ('L-E', 'L-N', 'L-S', 'L-S2')
COVER = {'L-D': ('C0b', 'S-D'), 'L-T': ('S-X', 'C0b'), 'L-SL': ('S-X', 'C0b'), 'L-X': ('S-X', 'C0b')}


def worst(xs):
    for v in ('FAIL', 'INSUFFICIENT', 'PASS'):
        if v in xs:
            return v
    return 'PASS'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gates', required=True); ap.add_argument('--score', required=True); ap.add_argument('--score-dry', default='')
    ap.add_argument('--c0b', default=''); ap.add_argument('--rsim', default=''); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    g = json.load(open(a.gates)); s = json.load(open(a.score))['status']
    sd = json.load(open(a.score_dry))['status'] if a.score_dry else None
    cov = {'C0b': (json.load(open(a.c0b)).get('verdict') if a.c0b else 'CHUA CO')}
    if a.rsim:
        cov.update(json.load(open(a.rsim)))
    out = {'gates_ok': g.get('ok'), 'items': {}, 'cover': cov}
    if not g.get('ok'):
        out['R_LIVE'] = 'HUY (cong V truot - khong cham)'
    else:
        for k in BB:
            out['items']['L0 ' + k] = s[k]
        if sd:
            for k in BB_DRY:
                out['items']['L0-DRY ' + k] = sd[k]
        else:
            out['items']['L0-DRY'] = 'INSUFFICIENT'      # thieu luot DRY
        for k, cv in COVER.items():
            v = s[k]
            if v == 'INSUFFICIENT' and k == 'L-D' and json.load(open(a.score)).get('L-D_no_cover'):
                out['items'][k] = 'INSUFFICIENT'   # ERRATA5 B(i): > 3 cum tiem tier3 => khong phu
            elif v == 'INSUFFICIENT':
                ok = all(cov.get(c) == 'PASS' for c in cv)
                out['items'][k] = 'INSUFFICIENT-CO-PHU' if ok else 'INSUFFICIENT'
            else:
                out['items'][k] = v
        vals = [('PASS' if v == 'INSUFFICIENT-CO-PHU' else v) for v in out['items'].values()]
        out['R_LIVE'] = worst(vals)
    out['warn'] = json.load(open(a.score)).get('warn', [])
    out['rui_ro_A11'] = json.load(open(a.score)).get('rui_ro_A11', [])
    json.dump(out, open(a.out, 'w'), indent=1)
    print(json.dumps({'R_LIVE': out['R_LIVE'], 'items': out['items']}))


if __name__ == '__main__':
    main()
