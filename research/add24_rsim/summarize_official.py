#!/usr/bin/env python3
"""ERRATA4 (DEV-B): bang ket qua R-SIM chinh thuc (KHONG PnL). In ro: S-G, S-G2 (quy, THO), S-SZ (+N11), S-X a/b/c (+N8, lane do nhay),
S-D, N10, V-TIER, co SIM_TIER_STALE (LUON bat), V1-V3, V5, V6, V9. usage: summarize_official.py <run_main> <run_sens> <lane_diff.json> <vtier.json> <out.json>"""
import json, sys, logging
logging.basicConfig(level=logging.INFO, format='%(message)s'); L = logging.getLogger()
dm, ds, ld, vtp, outp = sys.argv[1:6]
sc = json.load(open(dm + '/score.json')); ve = json.load(open(dm + '/verdict_e3.json')); g = json.load(open(dm + '/gates.json'))
ves = json.load(open(ds + '/verdict_e3.json')); vt = json.load(open(vtp)); lane = json.load(open(ld))
sx = sc['S-X']; sxs = sc['S-X_summary']
out = {
    'SIM_TIER_STALE': dict(flag=True, note='ERRATA4 1c: sim HO5 cap nhat tier luoi; ADD24 chi PASS khi owner chap nhan bang van ban (OWNER_DECISION_*) hoac sim sua tier + HO5 chay lai'),
    'V-TIER': dict(status=vt['status'], TIER_DIV=vt['TIER_DIV'], TIER_DIV_cums=vt['TIER_DIV_cums'], excluded=vt['exclude'],
                   dca_eligible_minutes=vt['dca_eligible_minutes'], TIER_DIV_all_held=vt['TIER_DIV_all_held'], moments_sim=vt['moments_sim'],
                   moments_match_printDone00=vt['moments_match_printDone00']),
    'S-G': {k: v for k, v in sc['S-G'].items() if k != 'fail_list'},
    'S-G2_raw': ve['B3_SG2_raw'],
    'S-SZ': dict(status_EB2=sc['S-SZ']['status'], official_EB2_rounded=sc['S-SZ']['official_EB2_rounded'], N11=ve['B4_SSZ_N11'], verdict=ve['B4_SSZ_N11']['status']),
    'S-X_a_reason': dict(n=sxs['n'], reason_eq_share=sxs['reason_eq_share'], reason_diff=sx['reason_diff']),
    'S-X_b_minute': ve['B1_SX_b'],
    'S-X_c_price': ve['B2_SX_c'],
    'S-X_sens_lane': dict(lane_diff=lane, verdict_b=ves['B1_SX_b']['status'], verdict_c=ves['B2_SX_c']['status'], note='bao cao, khong cham (ERRATA3 B6)'),
    'S-E': sc['S-E'], 'S-D': {k: v for k, v in sc['S-D'].items()}, 'N10': sc['N10'],
    'V': {k: g[k] for k in ('V1', 'V2', 'V3', 'V5', 'V6', 'V9', 'ALL_OK') if k in g},
}
json.dump(out, open(outp, 'w'), indent=1, default=str)
for k, v in out.items():
    L.info('%-14s %s', k, json.dumps(v if not isinstance(v, dict) else {a: b for a, b in v.items() if a not in ('lane_diff', 'events')}, default=str)[:600])
