# PREREG_GATESCALE — gate dyn scale: nguong `predReturn15M` co nen chat/long hon 0.0687*symbolPred?

Chot: 2026-09-12, commit TRUOC khi cai code / chay. Nen `X1_C3_FULL` (canonical `devrun/X1_C3_FULL_PARITY_R`, md5 ca file
`2478e90d...` / bo header `e13bc39e...`, equity 111,428 / n=2,266). Cua so 2022-01..2025-12, bins `predwf_map_s1a2_x1` KHONG
rebuild, dataset `wfo_ds_x1`, TICKER_SOURCE=file. KHONG cham HOLDOUT 2026, KHONG cham 242.

## 0. Cau hoi + vi sao KHONG phai open-search
User muon gate "hieu qua hon". Gate that su dang chay (sau LEAN L7) = `predReturn15M >= dyn_thr`, `dyn_thr = 0.008 *
max(0.26787, symbolPred/0.15 * 1.28760)` => voi symbolPred>0.0312 la `predReturn15M >= 0.0686720 * symbolPred`. Day la
gate scale-theo-selector (RESULT_FLATGATE: bo no => -61pp CAGR, vo 4/4 nam). Cau hoi hop le DUY NHAT chua do: **do doc**
cua gate co toi uu chua — chat hon (loc gay hon) hay long hon co tot hon incumbent?
**KHONG lam open-search "harness tim config thang baseline"**: B4_RESULT + AUDIT_GATEDYN_GD92 da chung minh do la leak L2
(chon tren nhieu); CI_REAUDIT: sd_boot 3-5pp, DEV khong phan biet duoc thay doi gate 3pp. Rolling gate va 5m-grid da DONG
(B4, GATEDYN, RESULT_5MGRID) — bai nay KHONG mo lai chung, chi do 1 chieu = do doc gate, dung dung 3 diem, hieu chinh boi.
**Ky vong ghi truoc:** NULL (khong phan biet duoc) hoac cac diem chat lam giam so lenh -> UW/variance xau. Neu thang ro => bat ngo.

## 1. Co che — chot cung (byte-identical khi khong khai)
- 1 key `SIM_GATE_DYN_SCALE` (float, qua `Cfg.get`, khai trong PROFILE; khong khai/`<=0` => 1.0). Trong `EntryGate`:
  nguong hieu dung = `dyn_thr * SIM_GATE_DYN_SCALE`. **Chi NHAN mot he so vao ket qua dyn_thr da tinh** — KHONG dung bieu thuc
  goc (floor/MULT/RATE_MAX giu nguyen). `scale=1.0` => `x*1.0` IEEE-exact => **byte-identical** (khong dung lai floor/ULP cua
  LEAN_GATE_AUDIT). Ap o CA sim va live (cung `EntryGate.pass`), nhung bai nay CHI chay sim.
- `SIM_GATE_DYN_SCALE > 1` = gate CHAT hon (nguong cao hon, it lenh hon); `< 1` = LONG hon (nhieu lenh hon, ve phia flat).
- Java SLF4J; log `[GATE] scale=.. base=.. n_cand n_pass`. Khong sua selector/bins/exit/trailing.
- **CONG NGHIEM THU**: jar moi + `x1_c3_full.properties` (khong khai key) => dir `X1_GS_OFF`, `cmp` printDone bo header vs
  PARITY_R rc=0, md5 khop. FAIL => sua code, KHONG chay bien the.

## 2. Bien the — DUNG 3, KHOA (khac nhau CHI o SIM_GATE_DYN_SCALE)
| tag | profile | scale | y nghia |
|---|---|---|---|
| `X1_GS_L80` | `profiles/x1_gs_l80.properties` | 0.80 | gate LONG 20% (nhieu lenh hon, ve phia flat-gate da biet la xau) |
| `X1_GS_T130` | `profiles/x1_gs_t130.properties` | 1.30 | gate CHAT 30% (it lenh hon, loc gay hon) |
| `X1_GS_T170` | `profiles/x1_gs_t170.properties` | 1.70 | gate CHAT 70% |
Moi key khac y `x1_c3_full.properties`. `scale=1.0` = PARITY_R (KHONG chay lai). Khong them bien the, khong doi 0.80/1.30/1.70 sau khi thay so.

## 3. Cham
- `research/analysis/x1_rates.py X1_C3_FULL_PARITY_R <tag>` (5 rate + CI khoi-72h, bang nam, rang buoc cung tuyet doi
  HARD_DD 15 / UW 120 / nam>=0 / quy>=-5).
- Equity ngay MTM: paired block-bootstrap (khuon `research/analysis/ci_bookcap.py`: block 21, 2000 rep, seed 20260903),
  d CAGR toan cua so + tung nam, hieu chinh boi k=3 => nguong **1.4823 * sd_boot**.
- Co che: so lenh/nam, entries/ngay, % slot top-8 bi gate chan, mMargin, vi the mo max/p90, collapse-day.

## 4. QUY TAC QUYET DINH (chot)
Bien the **PASS** <=> (i) `d CAGR > 1.4823 * sd_boot` (paired, block 21, toan cua so) VA (ii) qua het rang buoc cung tung nam.
Cach doc (khuon B4 muc 7): (a) >=1 PASS => de xuat so giay thu 2 forward (KHONG doi production, KHONG mo holdout). (b) 0 PASS,
khong vi pham => "khong phan biet duoc / do doc incumbent la hop ly" — DONG, GIU gate hien tai. (c) gate chan <5% hoac >99%
top-8 o 1 bien the => diem do vo nghia, ghi ro. d CAGR am ro (CI tren < 0) => "chat/long hon THUA". Khong them bo loc hau kiem,
khong doi nguong 1.4823, khong doi scale sau khi thay so.

## 5. Thu tu — bat buoc
1. Commit file nay. 2. Cai key + 3 profile, build, `check_cfg_gateway.sh` OK. 3. Cong nghiem thu (byte-identical).
4. 3 run (1 slot java, `pgrep -a java` rong, disk >=8G). 5. Cham. 6. `docs/RESULT_GATESCALE.md` + entry QUEUE.md. Commit SAU. Khong push.
## 6. Khong lam
Khong mo lai rolling/5m-grid. Khong doi bins/exit/selector/trailing. Khong cham 242/shadow_c3/SHADOW_NO_PUSH. Khong git push.
