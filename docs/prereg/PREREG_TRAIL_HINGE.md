# PREREG_TRAIL_HINGE — bản lề trailing STRONG/WEAK (SIM_TS_MAX_GAP / SIM_TS_PNOPUMP_WEAK_THR) trên gate T170 / DEV 2021

Viet va commit TRUOC khi chay bat ky sim nao. Khong sua sau khi thay ket qua.

Nen: dataset `wfo_ds_x1_2021` (18 fold 2021Q3..2025Q4), baseline THANG cua readjudicate
`X1_GS_T170_2021` (profile `profiles/x1_gs_t170.properties`, md5 printDone `efb793e2`, n=1089).
Jar HEAD hien tai (KHONG rebuild). SIM_END_DATE=20251231, holdout 2026 nguyen ven. KHONG cham 242,
KHONG tune, KHONG push, KHONG doi code Java.

## 0. Vi sao mo nhanh nay + kiem key bind (BAT BUOC truoc khi chay)

Co che trailing STRONG/WEAK theo `symbolPred` (P(no-pump)) chi THAT SU chay tu khi vá bug B1
(`docs/experiment/C3_BASELINE.md` B1): truoc do `symbolPred` khong duoc chep sang object CUM, nen
`trailRate()` luon fallback `pnp=1f > TS_PNOPUMP_WEAK_THR (0.29)` => 100% lenh di nhanh WEAK,
nhanh STRONG (`TS_MAX_GAP`) CHUA BAO GIO chay. T170 co `SIM_FIX_B1=true` nen co che nay dang
THAT SU hoat dong tu do den nay, nhung CHUA CO RESULT nao do rieng no. `docs/experiment/C3_BASELINE.md` §9
goi truc A (`SIM_TS_MAX_GAP`) va truc C (`SIM_TS_PNOPUMP_WEAK_THR`) la "vung trang".

Phan phoi `symbolPred` cua lenh T170 (do tu printDone.csv): p10 0.087 / p50 0.170 / p90 0.289;
90.6% lenh co symbolPred < 0.29 => ban le mac dinh 0.29 hau nhu KHONG cat (chi ~9.4% lenh la WEAK).

**Kiem tra bind (`grep -rn` + doc code, 2026-09-19, jar/HEAD `2fd7357`):**
- `Configs.java:662-663`: `SIM_TS_MAX_GAP` / `SIM_TS_MAX_GAP_WEAK` override `TS_MAX_GAP` /
  `TS_MAX_GAP_WEAK` (mac dinh 0.08 / 0.03) — BIND, khong co co nao tat khoi env parse.
- `Configs.java:659`: `SIM_TS_PNOPUMP_WEAK_THR` override `TS_PNOPUMP_WEAK_THR_OVR`, doc qua
  `Configs.tsPnoPumpWeakThr()` (`OVR ?? TS_PNOPUMP_WEAK_THR` mac dinh 0.29) — BIND.
- **Canh bao quan trong (rank-cap co the vo hieu ban le):** `Configs.java:429-441` — neu
  `TS_CAP_STRONG_RANK > 0`, `OrderTargetInfoTest.trailRate()` (dong 373) RE VE nhanh RANK
  (`TradeUtils.calRateLossDynamicBuyRank`) va **BO QUA HOAN TOAN** ban le `TS_PNOPUMP_WEAK_THR`
  (chi con `SIM_TS_MAX_GAP` tham gia qua cap STRONG). T170 **KHONG dat `TS_CAP_STRONG_RANK`**
  trong profile => mac dinh 0 => nhanh RANK KHONG kich hoat => duong pNoPump-threshold (ca 2 key)
  dang chay. XAC NHAN: key bind dung cho ca 3 variant.
- `SIM_TS_GIVEBACK=1` (T170 co dat) KHONG vo hieu `TS_MAX_GAP`: `TradeUtils.trailFromCap()`
  (dong 41) van dung `maxGap` (=`TS_MAX_GAP` hoac `TS_MAX_GAP_WEAK` tuy nhanh) lam CAP tren cua
  `peak * TS_GIVEBACK_RATIO`; giveback chi doi CONG THUC gap, khong doi CAP.
- **Ket luan §0: CA HAI KEY BIND DUNG trong duong sim cho T170.** Khong co co nao vo hieu.
  => TIEP TUC chay theo thiet ke duoi day.

## 1. Thiet ke — 3 bien the, moi cai = T170 + DUNG 1 key

Sinh bang `cp` + `echo >>` tu `profiles/x1_gs_t170.properties` (khong sua tay noi dung goc,
diff = DUNG 1 dong moi file, da xac nhan bang `diff`):

| tag profile | devrun | key doi | tu (T170) | den |
|---|---|---|---|---|
| `x1_th_gap05` | `X1_TH_GAP05_2021` | `SIM_TS_MAX_GAP` | 0.08 (default) | **0.05** |
| `x1_th_gap12` | `X1_TH_GAP12_2021` | `SIM_TS_MAX_GAP` | 0.08 (default) | **0.12** |
| `x1_th_weak17` | `X1_TH_WEAK17_2021` | `SIM_TS_PNOPUMP_WEAK_THR` | 0.29 (default) | **0.17** |

Khong doi gate (`SIM_GATE_DYN_SCALE=1.70` giu), khong doi S1 9-feat, khong doi net015, khong doi
DCA/sizing/bins. Dataset dung CHUNG `wfo_ds_x1_2021` (KHONG rebuild — 2 key nay la exit-param,
ap o SIM-time trong `SimulatorMarketLevelTicker1MStopLoss`/`TradeUtils`, khong bake vao
`ExportWfoDataset`).

V3 (`weak17`) ha ban le tu 0.29 xuong 0.17: theo phan phoi p10/p50/p90 (0.087/0.170/0.289),
nguong 0.17 nam gan p50 => day khoang **~50%** lenh (thay vi ~9.4%) sang nhanh WEAK (gap 0.03
thay 0.08) — cat loi/chot lai som hon cho khoang mot nua so lenh.

## 2. Cong (gates) — PASS truoc khi doc variant

(a) **KEY BIND**: da PASS o muc 0 — neu KHONG PASS thi DUNG, khong chay sim nao (da xac nhan PASS).
(b) **REPRODUCTION**: re-run T170 (profile `x1_gs_t170.properties`, dataset `wfo_ds_x1_2021`, jar
    hien tai, config `configs/sim_dev_file_2021.properties`, `TIME_RUN=20210701`,
    `SIM_END_DATE=20251231` theo `docs/result/RESULT_DEV2021_READJUDICATE.md` §7) -> devrun
    `X1_GS_T170_2021_REPRO` -> `md5sum storage/printDone.csv` PHAI bat dau **`efb793e2`**. Sai lech
    bat ky byte nao => DUNG, dieu tra (bins troi / jar khac / code-sha khac), KHONG chay variant.
(c) **CHI doi 1 key**: diff moi profile clone vs goc T170 = DUNG 1 dong (da xac nhan o muc 1). Sai
    => DUNG.
(d) Neu V1 hoac V2 cho `md5 printDone == efb793e2` (byte-identical voi T170) => key KHONG bind
    trong duong sim thuc te (mau thuan voi ket luan §0) => VIET RO "VO HIEU", van chay variant con
    lai, KHONG suy dien them.

## 3. Cham diem

### (i) CHAT LUONG — CI khoi-72h block, `inflate(k)=sqrt(2 ln k)`, **k=3** (3 ung vien: gap05,
gap12, weak17; baseline T170 khong tinh) => he so **1.482304** (`docs/audit/AUDIT_CI_INFLATE_STANDARDIZATION.md`).
`python3 research/analysis/x1_rates.py --k 3 X1_GS_T170_2021 <variant>` cho tung variant (script
chi so sanh tag[0] vs tag[1], nen chay rieng cho moi variant voi T170 lam tag dau).
Rate chat luong: win%, TSloss%, meanP, mP|SL. `n`, `mMargin` la bien KIEM SOAT.

**Luat THANG** (giu luat du an, WIN-test): variant THANG <=> **>=2 rate chat luong ngoai CI
CUNG HUONG TOT** VA **PASS rao cung theo nam theo khau vi MOI** (`docs/runbooks/RISK_APPETITE.md`:
maxDD<=30%, UW<=200 ngay, khong nam am, quy>=-15%, tap trung 1 coin <=15% equity). Ghi THEM cot
rao cung CU (maxDD<=15%, UW<=120, quy>=-5%) de tham khao (khong phai tieu chi quyet dinh).
Nguoc lai NULL; **>=2 rate ngoai CI huong XAU** = THUA.

Equity/CAGR chi bao cao, KHONG phai tieu chi (luat cung #3 AGENT_RUNBOOK).

### (ii) Tap trung 1 coin: dung ham `conc_max()` (mau `research/analysis/dca_agg_percoin_score.py`,
DCA_AGG_PERCOIN/CONCENTRATION) — max % equity vao 1 coin (group theo sym+cluster end, chia equity
dau ngay).

## 4. Du doan ghi truoc (chep nguyen tu MASTER)

"MASTER dự đoán NULL cho cả 3 (P≥1 thắng ≈ 25%); nếu V1/V2 ra byte-identical với T170 ⇒ key không
bind trong đường sim ⇒ VÔ HIỆU, dừng và báo; V3 kỳ vọng TSloss% giảm nhưng meanP giảm (cắt sớm),
nhiều khả năng trong CI."

## 5. Pham vi

DEV only (`SIM_END_DATE=20251231`). KHONG dung holdout 2026 (`HoldoutSeal`). KHONG cham 242.
KHONG deploy. KHONG sua code Java / rebuild jar. KHONG git push, KHONG ssh 242. Chi them 3 file
profile + 1 pre-reg + 1 result + chay 4 sim (1 repro + 3 variant). KHONG tune sau khi thay so.
KHONG xoa `wfo_ds_x1_2021`.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UoVRjusfNM2USSVNKQrm7z
