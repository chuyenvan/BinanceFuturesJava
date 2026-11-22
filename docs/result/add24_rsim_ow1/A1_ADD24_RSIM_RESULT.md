# A1 - ADD24 R-SIM official OW1 - independent check (R5) - 2026-11-22
Run: official_rsim_20261122_192102 (19:21->19:59), A1_REF 78f5b74f..., errata 29152e39,bb91e639,050912ca,03bb65e0,0740e790. RESULT = FAIL (S-G2, S-X).
Scripts: ~/claude_master/w3/add24_audit/r5/{sg2.py,sx.py} (read-only on add24/ and /dev/shm/add24/).

## 1. Integrity + recompute
- sha256sum -c vs SHA256_A1_APPROVED_RSIM.txt: rc 0, all OK. official_code_sha256.txt: 35 entries == approved list, 0 diff. DEV2W/env_used.sh fccc3ef1 OK.
  Note: DEV-A test-classes at 29e05d4f used (fullFromLive default off -> no behavior change in R-SIM).
- EB24: no timestamp > 2026-09-30 23:59:59 +07 in fx_ow1_n10/*, out_ow1/OW1_sim, OW1_p1. trace_dec gated rows span 07-01 00:00 .. 09-30 23:59 +07.
| metric | A1 from raw | RESULT | eq |
| sim PREDICT OW1 [07-01,09-16) (printDone) | 67 (16 min) | 67/16 | Y |
| jar PASS at those (trace_dec) | 67/67 | S-G PASS fail 0 | Y |
| sim PREDICT Q3 (printDone) | 94 | - | = log |
| sim.out.gz GATE-RATIO 2026Q3 | 94/3041795 | 94/3041795 | Y |
| jar Q3 (+07) gated pass/seen | 101/3045377 | 101/3045377 | Y |
| (UTC quarter would give seen 3035297 -> +07 convention is the right one) | | | |
| S-X n / same / N8 / other | 79/65/14/0 | 79/65/14/0 | Y |
| S-X mean Delta exit px | +0.528% | +0.5277% | Y |
| S-SZ | n 79 matched; naive qty compare not the EB2 metric -> accept scorer max 2.275e-5 (code audited R3/R4) | PASS | n only |

## 2. S-G2 (+7 pass, +3582 seen)
- jar PASS not in sim entries: 7, sim entries without jar PASS: 0. All 7 on 08-22, all INSIDE a sim hold interval of the same symbol:
  12:11 BEAT, 12:11 BOME, 12:13 HEMI, 12:15 BEAT, 12:15 PEOPLE, 12:26 AKE -> each right after an N8 (K8) rig exit 1 min earlier than sim (rig flat, sim still holds).
  12:12 USELESS -> rig stop filled at open of bar 12:13 (12:13:00.000, scored dmin 0) before the 12:12 decision; sim still holds until end 12:13.
- seen rows inside (symbol, sim hold interval): 3671 = GUA 2694 + BICO 960 (sim clusters leg0 2026-06-25, still open 07-01..07-02; follow.csv starts 07-01 -> rig starts flat, symbols stay candidates) + 17 rows (08-09 2, 08-22 10, 08-29 1, 09-10 1, 09-16 2, 09-23 1; rig-exited-earlier cascade). 0 pass among GUA/BICO rows.
- MASTER hypothesis "after 09-16 rig no longer follows": REJECTED (rig follows sim entries to 10-01; only 3 rows after 09-16). "leg0 before 07-01 (GUA 06-25)": CONFIRMED, it is ~all of the seen excess.
- Residual: 3045377-3671 = 3041706 vs 3041795 -> -89 rows (rel -2.9e-5), not explained, inside 1e-4.
- Classification: NOT a gate-logic difference. seen excess = HARNESS (initial hold state not seeded from sim clusters open at window start). pass excess = cascade of the K8 exit-timing difference (already measured by S-X), i.e. candidate set differs, gate decisions on common rows not shown to differ.
- Minimal fix (errata candidate): gate held-set in rig follows SIM hold state for the whole quarter (seed clusters open at 07-01 incl. leg0 < 07-01; symbol held until sim end); scoring of S-G/S-X/S-SZ unchanged (OW1 entries only). Equivalent scorer-side alternative: extend the existing n10_cascade adjustment to "hold-divergence" rows (symbol in sim hold interval while rig flat), reported next to the raw number.
- Hand estimate after fix: pass 101-7 = 94 (== sim); seen 3041706 vs 3041795 rel -2.9e-5 <= 1e-4 -> PASS. Caveat: rolling-ratio threshold depends on history; removing 3654 rows on 07-01..02 can shift r later -> only a rerun proves it.

## 3. S-X
- classify_sx: 14/14 K8_INTRABAR; REF-sim == sim minute 14/14 (ref_sim reproduces sim exit 67/67 trail), REF-nhip == rig minute 14/14. REF is python, independent of Java.
| sym | start | sim exit | rig exit | dpx% | exit-bar (H-L)/O % |
| CYS | 09-10 05:08 | 05:10 | 05:09 | 1.456 | 12.1 |
| BTR | 08-28 23:25 | 10:53 | 10:52 | 0.035 | 2.9 |
| VELVET | 08-22 12:11 | 16:43 | 16:42 | 1.275 | 36.2 |
| ZAMA | 08-22 12:13 | 14:34 | 14:33 | 1.606 | 6.5 |
| BTW | 08-22 12:28 | 12:34 | 12:33 | 1.782 | 5.2 |
| AKE | 08-22 12:10 | 12:27 | 12:26 | 0.042 | 7.1 |
| PEOPLE | 08-22 12:11 | 12:16 | 12:15 | 0.160 | 3.1 |
| BEAT | 08-22 12:12 | 12:16 | 12:15 | 1.516 | 6.7 |
| TRUMP | 08-22 12:10 | 12:15 | 12:14 | 0.735 | 6.2 |
| HEMI | 08-22 12:10 | 12:14 | 12:13 | 3.229 | 11.0 |
| BOME | 08-22 12:10 | 12:12 | 12:11 | 8.015 | 15.0 |
| BEAT | 08-22 12:10 | 12:12 | 12:11 | 19.760 | 24.9 |
| BICO | 08-09 14:24 | 14:29 | 14:28 | 1.192 | 8.8 |
| TUT | 08-09 14:24 | 14:26 | 14:25 | 0.654 | 17.9 |
- Mechanism (all 14): in the exit bar H raises the trailing SL, then C (path O-L-H-C) is below the new SL -> jar stops in the same bar at the raised SL (rig px == REF-nhip SL); sim applies the SL from the next bar and exits at min(SL, next open) -> 1 min later, lower price. dpx >= 0 in all 14.
- Mean: all 79 +0.528%; N8 14 mean +2.96% (contributes +0.525 pt of 0.528); same-minute 65 mean +0.0035% (61 exact 0, 4 time-stop tiny +0.02..0.09%), no bias. Without BEAT 08-22 12:10 outlier: +0.28% (still > 0.2%).
- 10/14 N8 on crash day 08-22; median exit-bar range ~8%. DEV 6.1%/+0.07%, DEV-2 14%/+0.42%, OW1 17.7%/+0.53%: N8 share and mean rise with high-range (crash) bars (descriptive).
- Verdict: (III) known real difference K8 (jar moves stop intrabar, sim from next bar), not harness (I) nor jar bug (II). It exceeds pre-registered tolerances (N8 <= 10%, mean in +-0.2%) -> FAIL by the letter is CORRECT, no errata basis. No threshold loosening proposed.
- Meaning for real bot: in ~18% of trail exits (crash-like bars) jar exits ~1 min earlier than sim, at the raised SL, under main path (O-L-H-C) at a price >= sim (mean +2.96% on those). Under the sensitivity path (O-H-L-C) 23/79 clusters change exit minute, Delta vs main mean -0.30%, p05 -2.75%, min -6.19%: the sign of the price effect depends on the unknown intrabar path, so sim results do not transfer 1:1 to the jar on crash days.

## 4. R-LIVE E1 -> see A1_ADD24_HARNESS_R5.md (closed).

## 5. Conclusion
- Official R-SIM OW1 = FAIL stands. S-X FAIL is (III) real K8 difference -> stays FAIL regardless of S-G2.
- S-G2 FAIL contains a harness defect (initial hold state) + K8 cascade; per s10 it may get an errata + rerun reporting both numbers, but this cannot change the overall verdict.
- Per prereg s10: FAIL -> no pilot, no tuning, no criteria change. Next: MASTER records S-G2 errata (optional transparency rerun), report to owner; any further step (e.g. pre-registering a new test that models K8 in sim) is a new prereg, not this one.
