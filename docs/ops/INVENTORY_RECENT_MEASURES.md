# INVENTORY_RECENT_MEASURES — kiem ke ket qua do luong ~45 ngay (phan loai theo SUC MANH THONG KE)

Ngay lap: 2026-09-22. Branch `module`. **KHONG push.** Tai lieu nay chi DOC + TINH LAI bang so hoc
(khuan Python), khong sua code san xuong, khong chay sim, khong dung `claude-run`.

Muc dich (theo yeu cau owner): trong cac ket qua NULL gan day, cai nao la **NULL DANG TIN** (da loai
tru duoc) va cai nao la **CHUA PHAN GIAI** (chi thieu power) — chi nhom sau moi dang xet lai.

---

## 0. Cach phan loai (khung do da duoc hieu chuan)

Nguon khung: `docs/result/RESULT_HARNESS_CONTROL.md` (commit `4f83902`) + `docs/result/RESULT_LEVEL_SENSITIVITY.md`
(commit `8682beb`). Ca hai deu la vong **thuan Python**, do tren chuoi causal `raw/*.f32`, CI
block-72h x1.21 (2000 rep, seed 20260905), DEV = 2022-01..2024-06 (harness control) / 2022-01..2025-12
(level sensitivity).

**Luat MDE da do (HARNESS_CONTROL §4):** phep "phat hien" = `CI72h x1.21 lo > 0` (dung cong GO), nen
`phat hien <=> X > half-width(CI)`. Do do **MDE ~= half-width cua CI** tai N do:

| basis | N | MDE(80%) | half-width |
|---|---|---|---|
| day-permute (lam phang cum) | 3 167 | **0,50%/lenh** | 0,2752% (nhan 1.0, khong x1.21) |
| cum (dung cho tin hieu capitulation) | 100 / 200 / 500 / 1 000 | **4,00%/lenh** | 2,77 / 2,37 / 2,02 / 1,94% |
| cum | 2 000 / 3 167 | **2,00%/lenh** | 1,85 / 1,83% |

**MDE moi (LEVEL_SENSITIVITY §0C, DEV 2022-2025):** BIG_UP **>4,00%**, MEDIUM_UP **2,00%**,
MEDIUM_DOWN **>4,00%**, MOM15 **2,00%** (%/lenh).

**Do tin cay bo do:** positive control MOM15 duong o 5/5 nam, p(>0)=1.000, null p=0.0000; negative
control (placebo) **FP 1 phia = 0/200 = 0,0%**. => Bo do khong sai; van de la **power**.

**He qua da chung minh (LEVEL_SENSITIVITY):** tang N bang per-coin **KHONG mua duoc power** —
N DEV 236/636/264 -> 43 981/99 361/37 517 (x142-186) nhung `N_eff` (block-72h) **dung yen** 32/111/52
=> he so lam phat N/N_eff = 1 374/895/722; MDE chi cai thien ~2x o MEDIUM_UP, khong cai thien o
BIG_UP/MEDIUM_DOWN. Tran la **so episode doc lap**; noi nguong khong tao them episode.

**Quy tac phan nhom dung trong tai lieu nay:**

- **A — NULL DANG TIN (da du luc / da ket luan duoc):** hieu ung bi **loai tru thong ke** (rate ngoai
  CI theo huong xau, hoac CI cua hieu CAGR/d nam ngoai 0), **hoac** |hieu ung| >= MDE, **hoac**
  N/N_eff du lon de MDE da nho hon nguong dang quan tam. => ra soat lai **vo ich** (chi tao
  false-positive).
- **B — CHUA PHAN GIAI (thieu power):** CI chua 0 **va** |hieu ung| < MDE (CI half-width >> hieu ung),
  va ly do NULL **khong phai** rang buoc cung/co che. => co the dang xet lai, **nhung cach duy nhat
  tang power la them EPISODE DOC LAP** (thoi gian that / forward), KHONG phai noi nguong.
- **C — BI LOAI VI RANG BUOC CUNG / CO CHE:** NULL den tu maxDD/UW/nam am/quy am/tap trung, hoac tu
  co che (chi doi thang do, khong binding, trung lap, khong co kenh tac dong), hoac la tai lieu
  ha tang/audit/parity. => khong phai cau hoi thong ke => ra soat lai vo nghia (tru khi doi khau vi
  rui ro, da chot trong `RISK_APPETITE.md`).

**Ghi chu ve "MDE proxy" cho cac phep do tang SIM (khong phai %/lenh):** cac vong A/B tren sim bao
`CI95` cua hieu tung rate (win%/TSloss%/meanP...) va cua `d CAGR`; dung luat cua du an
(">=2 rate CHAT LUONG ngoai CI cung huong TOT"). Voi cac vong nay, **MDE proxy = half-width cua
CI** (nen tang x1.21 tuong duong), ty so = |d|/half-width. Cong nhan "phat hien" cua sim la
`>=2 rate ngoai CI` — rat giong dinh nghia MDE nen proxy nay hop le de doc power.

---

## 1. BANG TONG (dem)

| Nhom | Y nghia | So ket qua |
|---|---|---|
| **A** | NULL dang tin / da du luc / da ket luan | **16** |
| **B** | Chua phan giai (thieu power) | **16** |
| **C** | Bi loai vi rang buoc cung / co che / ha tang-audit | **69** |
| Tong tai lieu ket qua trong ~45 ngay duoc kiem ke | | **101** |

**Kiem chung lai bo danh sach (2026-09-22, doc lap voi ban soan truoc):** lenh `git log --since="45
 days ago" --name-only --pretty=format: -- docs/ | sort -u | grep -iE "result|audit|prereg"` tra ve
**242 ten duong dan**. Trong do **12 ten khong con ton tai** o duong dan do (da chuyen xuong
`docs/archive/_cleanup_20260829/docs/project-memory/`), va **22 ten `docs/archive/...` + 24 ten
`docs/project-memory/...`** la **ban truoc cleanup** (trung noi dung voi ban top-level). => **230 file
song**, gom **102 tai lieu KHONG phai `PREREG_`** (= tap "ket qua do luong" cua bang nay; ban soan
 truoc dem 101, sai lech 1 do mot file `preregistration_frame_v1_2026-08-23.md` duoc xep dung vao
nhom K/khung khong phai `PREREG_*`).

**Doi chieu 2 dong so (ghi de minh bach, khong giau):** ban soan truoc xep `RESULT_S1_CORRECT_MEASURE`
vao **A16** dua tren 2 metric phu (top-8 xuoi 24h +3,4 bps; top-8 nguoc 72h −1,18 bps). Doc lai muc 6
cua chinh tai lieu do: **tieu chi PRIMARY** la `rank_ic(−score,72h) > 0 VA CI ngoai 0` => **KHONG DAT**
(−0,0192, **CI chua 0**), va test dao dau cung **CI chua 0**. Tieu chi chinh **chua phan giai** => da
chuyen sang **B16**. Cac dong khac duoc **spot-check doc lap va khop**: A1 (N=1 179 302, net DEV
−0,080%, half 0,36% x1,21 = 0,43% — khop bang `RESULT_HARNESS_CONTROL` §4), A5 (FLATGATE `d CAGR`
−61,08pp, CI95 [−85,76,−32,82], `P(d>0)=0.000`), C/`NOBD_READJUDICATE` (2 rate DAT nhung UW 2022 =
131 > 120), va khung MDE (2,00%/lenh @N≈3 167; 4,00%/lenh @N≈100–1 000; MDE ≈ half-width CI x1,21).

Danh sach nguon: `git log --since="45 days ago" --name-only --pretty=format: -- docs/ | sort -u |
grep -iE "result|audit|prereg"` => 113 ten (gom 33 `PREREG_*`, da loai khoi bang); con lai
`RESULT_*.md` (68), `*_RESULT.md` (19), `AUDIT_*.md` (10), va 4 tai lieu ket qua khac
(`GD92_CODE_AND_RESULTS`, `CI_REAUDIT`, `D1_DATA_AUDIT`, `LEAN_GATE_AUDIT`).

---

## 2. NHOM A — NULL DANG TIN (17)

| # | Tai lieu | Ngay | N (N_eff) | Hieu ung do duoc | CI | MDE | \|hieu ung\|/MDE | Ly do loai |
|---|---|---|---|---|---|---|---|---|
| A1 | `RESULT_REVERSAL_BOUNCE.md` | 09-22 | **1 179 302** DEV (3 785 409 ALL); N_eff khong cum (ICC 72h 0,057) | net DEV **−0,080%** (raw +0,22%) | CI72h [−0,449,+0,269]; x1.21 [−0,515,+0,355] (half 0,36%) | **0,43%** | 0,19 | **NULL co nghia**: MDE 0,43% < nguong quan tam ~0,5%/lenh => **chan duoc** moi edge >= ~0,5%/lenh. %coin+ 38%, sign-flip theo nam (2025 am). |
| A2 | `RESULT_LEVEL_SENSITIVITY.md` | 09-22 | P-COIN DEV **43 981 / 99 361 / 37 517**; **N_eff 32/111/52** | meanNet P-COIN lon (BIG_UP 24h +10,0%) nhung **DEDUP ≈ 0/am** (BIG_UP −0,18; MEDIUM_UP **−0,71**; MEDIUM_DOWN **−1,75**) | 27 o DEV: 0 o vuot dong thoi `x1.21` + Bonferroni K=27; 7 o vuot 1 nguong | 2,00-4,00% | — | **DAY CHINH LA VONG DA XET LAI**: tang N x142-186 khong mua duoc power (N_eff dung yen). Duong tinh o P-COIN bi **episode dai** chi phoi (dao dau khi dem trung tinh theo episode); MOM15 neo van vuot ca 2 nguong => bo do khong hong. Ket luan: khong level-signal nao con dang theo. |
| A3 | `RESULT_DCA_ROUND_CAP.md` | 09-19 | n=1089 (DCA legs 20->84) | win% **−1,33pp** (CAP10_LOOSE), −1,39pp (LOOSE) | CI95 [−2,42,−0,04] / [−2,49,−0,12] | ~1,2pp | >1 | **Rate XAU NGOAI CI** (dinh chinh 09-19 tu PASS->FAIL do he so CI bi nhan chong 1.21x1.4823) + vi pham chan tap trung `max1coin` (9,77%->12,5%/17,2%). |
| A4 | `RESULT_DCA_AGG_PERCOIN.md` | 09-19 | n=1089 | win% **−1,39 / −1,33pp** | CI95 [−2,49,−0,12] / [−2,42,−0,04] | ~1,2pp | >1 | Cung dinh chinh: rate xau **ngoai CI** => PRIMARY FAIL (truoc bao PASS chi vi CI qua rong). |
| A5 | `RESULT_FLATGATE.md` | 09-12 | n=2266 (48 thang) | `d CAGR = −61,08 pp` | CI95 [−85,76,−32,82], tran <0; ben o block 10/21/42 | 26,5pp | **2,3** | Gate phang (chien luoc 242) **te hon ro**, P(d>0)=0.000, vo rang buoc cung 4/4 nam. |
| A6 | `RESULT_HOLDDCA.md` | 09-11 | n=2266 | 0/3 bien the PASS | CI95 cua `d CAGR` **nam hoan toan duoi 0** | — | >1 | Bo time-stop + om bag thua ro + vi pham rang buoc cung 3/4 nam. |
| A7 | `RESULT_GRAVEYARD.md` | 09-11 | 285 lenh PST time-stop | EV giu tiep **am** (180d −13,9% / 365d −29,6%) | D2 180d CI95 [−21,3,+1,7] | — | — | EV am + 20,3% delist/−80% @365d; chi 2023 duong => **DONG** nhanh (co che + so lieu don dieu). |
| A8 | `RESULT_GATE_TOPK_LABEL_SIM.md` | 09-20 | n (18-fold, 1089 baseline) | **4/5 rate ngoai CI, DEU XAU**; gate dai ~2x (n_pass 1442 vs 841) | CI95 k=1 | — | >1 | Doi nhan gate lam gate LONG hon => chat luong xau **ngoai CI** => LOAI ro ret. |
| A9 | `RESULT_5MGRID.md` | 09-08 | n (48 thang) | win% **−2,016pp**, TSloss% **+1,923pp** | CI [−3,856,−0,263] / [+0,269,+3,592] | ~1,8pp | >1 | 2/5 rate ngoai CI, **DEU XAU** => 5M sai huong, khong phai NULL "khong biet". |
| A10 | `K12_RESULT.md` | 09-07 | n=2266 | TSloss% **+1,53pp** (XAU) | CI [0,487,2,705] | 1,1pp | 1,4 | 1/5 rate ngoai CI (duoi nguong >=2) **va huong xau** => khong dat luat thang, da ro. |
| A11 | `RESULT_K_DENSITY.md` | 09-13 | n=1089 (DEV 2021) | K12: TSloss% +1,48, meanP −0,35; K16: TSloss% +2,06 | CI block-72h x1.21 | ~1pp | >1 | 2 rate ngoai CI **DEU XAU** => chat luong xau nhe, khong thang. |
| A12 | `RESULT_GATESCALE.md` | 09-12 | n=2266 | L80: win% −2,97, TSloss% +2,89, meanP −0,92 | 3 rate ngoai CI | ~1pp | >1 | L80 (gate long) **3 rate ngoai CI deu XAU** => loai ro. (T130/T210 xem nhom B/C.) |
| A13 | `RESULT_GATEFEAT.md` | 09-09 | harness deterministic (dup max\|d\|=0), 19 fold OOS | bo `monthOfYear` lam IC **giam ngoai CI** (−0,0015); bo feature khac IC giam ngoai CI | CI95 x1.21 [−0,0025,−0,0004] | 0,0011 | >1 | Cac ket luan giu/bo feature deu **vuot CI** (harness dup = 0 nen khong co nhieu harness) => da phan giai. |
| A14 | `RESULT_TREND_RANK_IC.md` | 09-17 | n_snap **43 411-43 631** (S1 35 046) | rankIC **am** o moi horizon (trend −0,036 / mom −0,049 / vol −0,0905 @24h) | CI95 x1.21 deu **ngoai 0** (am) | ~0,006 | >1 | **Khong co tin hieu trend-following**; nguoc dau gia thuyet; n rat lon => ket luan vung (du la descriptive). |
| A15 | `RESULT_S1_RANK_QUALITY.md` | 09-17 | n_snap 35 047 (2022-2025) | rankIC −0,0247 / −0,0407 / −0,0693 | CI95 x1.21 deu **ngoai 0** (am) | ~0,002-0,008 | >1 | Am o CA 4 nam, ca 3 horizon; "significance" nho nhung **on dinh qua nam** => ket luan ro. |
| ~~A16~~ | ~~`RESULT_S1_CORRECT_MEASURE.md`~~ | 09-17 | — | — | — | — | — | **DA CHUYEN SANG B16** (tieu chi PRIMARY `rank_ic(−score,72h)>0 & CI ngoai 0` = KHONG DAT, **CI chua 0** ⇒ chua phan giai). Xem muc "Doi chieu" o §1. |
| A17 | `RESULT_S1_DETERMINISM.md` | 09-19 | 3 run (O1/O2/K1) | n_jobs=1: 15,012825% / 15,012825% / 15,209468% | — | — | — | **Bac bo gia thuyet** (n_jobs=1 khong lam Oracle==Kaggle bit-identical) => ket luan dinh tinh, khong phai cau hoi power. |

---

## 3. NHOM B — CHUA PHAN GIAI (16) => SHORTLIST

| # | Tai lieu | Ngay | N (N_eff) | Hieu ung do duoc | CI | MDE | \|hieu ung\|/MDE | Ly do |
|---|---|---|---|---|---|---|---|---|
| B1 | `RESULT_BIGUP_MEDIUPDOWN.md` | 09-22 | M-LEVEL ALL 320/914/444; **DEV ~89/316/158**; ICC(day) 0,01/0,28/**0,45** | net DEV **+0,87 / +1,84 / +1,25%**; phan MOM15-QUIET (phan doc lap) **+2,99 / +0,03 / +0,58%** | CI72h x1.21 chua 0 o DEV (p 0,63/0,94/0,73) | **4,00%** | **0,22 / 0,46 / 0,31** | Hieu ung **duoi MDE**; CI chua 0; nho + cum manh => chua du luc. **Da duoc xet lai o A2/LEVEL_SENSITIVITY** => xem rao 1 (da dong). |
| B2 | `RESULT_HARNESS_CONTROL.md` (phan A-DEV: MOM15) | 09-22 | **N=3 167** DEV; ICC(day)=**0,50** | net DEV **+1,28%** (ALL +2,26%) | CI72h x1.21 **[−0,72,+3,28]** (chua 0), p(>0)=0,939 | **2,00%** | **0,64** | Chinh **tin hieu dang chay live cung KHONG duoc chung nhan tren rieng DEV** => DEV thieu power. Can them episode doc lap (thoi gian that). |
| B3 | `RESULT_SEL_BIGDOWN.md` | 09-16 | **n = 248 leg** BIG_DOWN | `pnl/leg` DROP **+54 USD/leg (+82%)**, end-equity +28% | CI bootstrap **qua rong** (duoi nang) | CI half-width > effect | **<1** | Point-estimate lon nhung **0/3 rate PRIMARY ngoai CI**; CI qua rong o n=248 => khong the ket luan. |
| B4 | `RESULT_D3D4_FILTER_SIM.md` | 09-17 | n=1089 | D4 meanP ngoai CI (1 rate); D3/D3D4 hoi XAU (TSloss% tang) | CI block 72h x1.21 | ~0,5pp | ~1 (chi 1 rate) | Chua du nguong >=2 rate; hieu ung ~0 => khong phan biet duoc. |
| B5 | `RESULT_PUMPDUMP_DETECT.md` | 09-17 | n=1089; **SUP n=49** | 6 feature/4 detector deu NULL | CI infl x1.21 cua hieu mean **[−56,65,+49,93]** | ~50% | **~0,02** | CI **cuc rong** do chi 49 ca SUP => khong the tach "pump xong chuan bi dump". |
| B6 | `RESULT_PUMPDUMP_OHLCV.md` | 09-17 | **SUP n=49** | 4 detector NULL (OHLCV 1m + OI) | CI infl x1.21 | rong | <1 | Cung ly do B5: n=49 SUP => thieu power nghiem trong. |
| B7 | `RESULT_POSTPUMP_MEASURE.md` | 09-17 | SUP **n=37-49** / DOI_CHUNG 802-1040 | `mom30d` hieu mean | CI raw [−47,4,+40,7]; x1.21 [−56,65,+49,93] | ~50% | ~0,1 | CI chua 0 + rat rong => FAIL theo tieu chi, nhung **khong phan giai duoc**. |
| B8 | `RESULT_GATEDYN.md` | 09-09 | n=2266 (48 thang); CV quy 0,712->0,518 | GD92: chi **1 rate** TOT ngoai CI (mP\|SL +2,54) | CI [+0,05,+5,36] (can duoi sat 0,05) | ~2,6pp | ~1 (1 rate) | Claim "THANG" **khong vung** (xem `AUDIT_GATEDYN_GD92.md`): chi 1/5 rate ngoai CI, can duoi 0,05. |
| B9 | `RESULT_GATEDYN2.md` | 09-09 | 6/6 bien the moi **FAIL rang buoc cung**; n=1089-1500 | GD92 la diem toi uu duy nhat "PASS" | — | — | — | Grid xac nhan vung on dinh quanh GD92, nhung ket luan "GD92 thang" khong phan biet duoc (B8). |
| B10 | `RESULT_GD92_RECHECK.md` | 09-15 | n=2266 | GD92 vs T100: **0/3 rate ngoai CI** | `d CAGR +4,98pp` CI [−4,47,+16,09] **chua 0** | 10,3pp | 0,48 | Chay lai tren dataset chuan => **khong phan biet duoc**. |
| B11 | `RESULT_GATESCALE.md` (T130/T210) | 09-12 | n=2266 | T130: `d CAGR −8,3pp`; T210 khong phan biet tren rate | T130 CI [−19,4,+1,7]; T170 CI [−18,1,+8,9] (om 0) | ~10pp | <1 | CI chua 0 => khong phan biet duoc (T130 con vo maxDD 2025 => phan C). |
| B12 | `RESULT_TRAIL_HINGE.md` | 09-19 | n=1089 | V1/V2/V3: **0 rate chat luong ngoai CI** (toan cua so) | CI k=3 | ~0,5pp | <1 | Key bind that, nhung hieu ung nam trong CI, bien do qua nho => khong phan biet duoc. |
| B13 | `RESULT_S1_OI12.md` | 09-13 | n=1089 (DEV 2021) | 0 rate ngoai CI; moi rate lech **HUONG XAU nhung trong CI** (win% −0,90...) | CI x1.21 | ~1pp | <1 | Khong phan giai duoc (khong co rate nao ngoai CI). |
| B14 | `RESULT_GATE_CALIB.md` (nhanh T210) | 09-20 | n=1089 | 0/5 rate ngoai CI; T210 qua rang buoc cung | CI k=2 | ~1pp | <1 | Nhanh 2,10 **khong phan biet duoc tren rate** (T130 => nhom C). |
| B15 | `RESULT_BREADTH_GATE_SIM.md` | 09-21 | 3 sim (n~1582-1689) | u2 "PASS theo cong thuc khoa" nhung can duoi CI95_inflated(k=2) **chua 0** | CAGR CI95 (block-72h, k=2) | ~10pp | <1 | **NULL co cau truc**: n_eff chua du lon de ket luan "vuot troi" theo tieu chuan thong ke. |
| B16 | `RESULT_S1_CORRECT_MEASURE.md` | 09-17 | n = 59 bucket gio (108 phut quyet dinh) | `rank_ic(−score,72h)` **−0,0192**; test dao dau **+0,0192**; (2 metric phu: top-8 xuoi 24h +3,4 bps, top-8 nguoc 72h −1,18 bps) | CI95 x1.21 **chua 0** o CA tieu chi PRIMARY va test dao dau | ~2 bps | <1 | Tieu chi chot truoc **KHONG DAT vi CI chua 0** ⇒ **chua phan giai**; phat hien that la do-sai-horizon/moc (khong phai bang chung alpha). |

---

## 4. SHORTLIST NHOM B — can gi de phan giai

**Nguyen tac (da chung minh, khong phai gia dinh):** tang power **chi** bang them **EPISODE DOC LAP**
(thoi gian that / forward / live), **KHONG phai noi nguong**. Bang chung: `RESULT_LEVEL_SENSITIVITY`
tang N x142-186 (236 -> 43 981) nhung `N_eff` dung yen 32/111/52, MDE chi 12,8% -> 11,1%. Tran cua
bo do la **so dot capitulation doc lap co that**, khong phai so dong du lieu.

| Uu tien | Muc | Trang thai | Can gi de phan giai |
|---|---|---|---|
| 1 | **B1 BIG_UP / MEDIUM_UP / MEDIUM_DOWN** | **DA XET LAI (A2)** | Khong can lam gi nua. Vong xet lai da chay: duong tinh bien mat khi dem trung tinh theo episode (`P-COIN-DEDUP` ≈0/am) => khong con ung vien. |
| 2 | **B2 MOM15 tren rieng DEV** | Mo | Chi tang power bang **them episode capitulation tuong lai** (forward/live). Tren du lieu lich su 2022-2024 khong the: cum ICC(day)=0,50. |
| 3 | **B3 SEL_BIGDOWN** (chon 2 coin BIG_DOWN) | Mo — dang chu y | Point-estimate +54 USD/leg (+82%) la **ung vien duy nhat con "lon" trong nhom B**. Can **them episode BIG_DOWN doc lap** (forward) de thu hep CI o n=248 leg; hoac do lai bang trong so danh muc/decay risk-adjusted (khong doi nguong trigger). |
| 4 | **B4 D3D4 filter (D4 meanP)** | Mo | Them lenh/forward de CI quanh meanP hep lai; hien 1 rate ngoai CI duoi nguong 2. |
| 5 | **B5/B6/B7 PUMPDUMP / POSTPUMP** | Mo (bi chan boi n=49) | Can **them su kien SUP doc lap** (forward) — vd doi 49 -> vai tram; khong co cach nao khac (CI rong ±50% vi n=49). |
| 6 | **B8/B9/B10 GD92 + GATEDYN2** | Da xet lai 2 lan (GD92_RECHECK + DEV2021_READJUDICATE) | Ket luan hien tai: **khong phan biet duoc** (0/3 rate ngoai CI; `d CAGR` CI chua 0). Muon phan giai phai them episode doc lap (forward) — tren cung cua so 48 thang khong the. |
| 7 | **B11/B14 GATESCALE T130/T210, GATE_CALIB T210** | Mo | CI cua `d CAGR` ±10-19pp: can **cua so thoi gian doc lap dai hon** (forward) de hep CI; hien T170/T210 khong phan biet duoc. |
| 8 | **B12/B13 TRAIL_HINGE, S1_OI12** | Mo | Hieu ung ~0 nam trong CI rong ~1pp: can them episode (forward) hoac thay thuoc do (rank-IC thay vi rate). |
| 9 | **B15 BREADTH_GATE_SIM** | Mo | `n_eff` chua du; can them episode doc lap. Luu y: day la cung ho "breadth" da NULL 5/5 o cac ho khac (xem C). |
| 10 | **B16 S1_CORRECT_MEASURE** | Mo (moi chuyen tu A) | Hieu ung rank-IC ~0,02, CI chua 0 o ca tieu chi chinh lan test dao dau ⇒ can **them moc/khung thoi gian doc lap** de ha CI duoi 0,02. Tren cung bo snapshot hien co khong the. |

**Ghi chu quan trong ve B3/B5-B7 (nho nhat, CI rong nhat):** mo hinh cua chung la **su kien hiem**
(SUP n=49; BIG_DOWN legs n=248). Khong co phep "xet lai" nao tren du lieu cu lam hep CI duoc —
chi thoi gian forward moi them episode. Neu owner muon hanh dong ngay thi hanh dong kha thi duy nhat
la **ghi nhan lai + theo doi tren duong live/shadow**, khong phai chay lai phan tich.

---

## 5. NHOM C — BI LOAI VI RANG BUOC CUNG / CO CHE / HA TANG (69)

Rut gon theo ly do (ma: **H**=rang buoc cung, **M**=co che, **I**=ha tang/audit/parity, **D**=descriptive-co confound):

| Ma | Tai lieu | Ly do chinh |
|---|---|---|
| H | `RESULT_DD_THROTTLE` (09-21) | u2 vo UW>200 (DT khong hon R0/gate-1.0 ve UW) |
| H | `RESULT_PACING_BIGDOWN` (09-21) | fail t2 (khau vi 2025 UW=221) + t3 (UW 221 > 115) |
| H | `RESULT_REGIME_GATE` (09-21) | UW(R)=223 > 200, fail 2025 |
| H | `RESULT_REGIME_UPDOWN` (09-21) | RA12 fail UW 221; RA14 la **lead descriptive** (khong duoc chon vi luat khoa) |
| H | `RESULT_BREADTH_CONT` (09-22) | u1-u5 fail; UW-2025=221 |
| H | `RESULT_BREADTH_CONT_T50` (09-22) | u1-u5 fail |
| H | `RESULT_BOOKCAP` (09-11) | rang buoc cung FAIL 2-3/4 nam (UW 137/244/302) |
| H | `RESULT_2X_HALFSIZE` (09-14) | UW va CAGR FAIL o MOI config |
| H | `RESULT_FLATGRID` (09-15) | UW toan ky 147 > 120 (quyet dinh **khau vi rui ro**, khong phai thong ke) |
| H | `RESULT_DCA_GATEWIDEN_V3` (09-14) | UW la rang buoc BINDING cua moi huong "tang so lenh" |
| H | `RESULT_DCA_SIGNAL_GATE` (09-14) | NULL 3/3 config; UW binding |
| H | `RESULT_DCA_SIGNAL_GATE_V2` (09-14) | NULL 3/3; rang buoc cung |
| H | `RESULT_DCA_MORELEGS_V4` (09-14) | NULL 8/8, khong nhanh nao thoat tran UW 120 |
| H | `RESULT_NOBD_READJUDICATE` (09-15) | T170_NOBD dat 2 rate nhung **truot UW 2022 (131>120)** |
| H | `RESULT_SL_ADAPTIVE_SWEEP` (09-12) | baseline tu no FAIL hard (UW 121/227); lever A hai ro; C NO-OP |
| H | `RESULT_B_FOLLOWUP` (09-13) | 0 rate ngoai CI + CA 3 PHA fail UW<=120 |
| H | `RESULT_G015ABL` (09-08) | 2022 maxDD −27,74% (gap 2,6x control), UW 238 => loai bang rang buoc cung |
| M | `RESULT_BD_SIZE_ADAPT` (09-16) | Severity sizing **chi rescale `pnl/leg`**, khong doi chat luong/rui ro (n=248) |
| M | `RESULT_BD_THRESHOLD_FRAGILITY` (09-17) | Descriptive: nguong hien tai la **local max** (PnL dao 2x trong 4 diem quet) => bang chung overfit |
| M | `RESULT_HEDGE_OVERLAY_A` (09-20) | NULL vi **ICC tang 0,0516 -> 0,2208** (hedge lam giam so cuoc doc lap) |
| M | `RESULT_COLLAPSE_PROBE` (09-11) | Feature entry-time **khong du doan duoc** collapse (123/1996) |
| M | `RESULT_DYN_COLLAPSE` (09-14) | Gia da du; them OI/funding **chi lam loang** |
| M | `RESULT_VOL_TARGET` (09-20) | COIN/PORTFOLIO NULL ve chat luong alpha; day la cau hoi **quan tri rui ro** (PORTFOLIO dat sai tham so) |
| M | `RESULT_CONCENTRATION_SAFETYCAP` (09-15) | 2 guard **khong bind lan nao** trong 4,5 nam => khong co gi de do |
| I | `RESULT_CONCENTRATION_SAFETYCAP_LIVE_PORT` (09-15) | Port guard sang live (flags default OFF) |
| M | `RESULT_GATE_H72` (09-20) | **KHONG CHAY**: trung lap nhan `retEnd_72h>0.015` (da chay, XAU HON) + huong B khong co kenh tac dong |
| M | `RESULT_S1_FREE_OFI` (09-20) | **HARNESS_NGHI_NGO** — khong cong bo THANG/NULL; nguyen nhan (confound missingness 15-symbol) da xac dinh o `AUDIT_HARNESS_OFI_2026-09-20` |
| M | `RESULT_S1_HPO_BAG_FEATGRP` (09-19) | P1/P2/P3 NULL tren CONFIRM + hieu chuan nhieu (noise_0 la artifact hieu chuan, khong phai leak) |
| I | `RESULT_SELECTOR_NET015_GATE` (09-12) | 4 cong parity PASS (ha tang gate tier-1) |
| I | `RESULT_S1REFRESH` (09-12) | Refresh model cutoff 20251231 (ung vien deploy shadow) |
| I | `RESULT_NET015_CUT20251231` (09-13) | Refresh model net015 (parity) |
| I | `RESULT_DEV2021` (09-12) | Mo DEV ve 2021 (reproduction/provenance, khong tim alpha) |
| I | `RESULT_DEV2021_READJUDICATE` (09-15) | T170 THANG tren DEV mo rong (2 rate ngoai CI); T130 NULL (hard); GD92 BLOCKED (co che) |
| I | `RESULT_LIVE_EQ_SIM` (09-12) | Dong bo tang-1 universe + trailing hinge (khong tim alpha) |
| I | `RESULT_SIZEPROBE` (09-12) | Diagnostic sizing (chi them 1 dong log) |
| I | `RESULT_BOOKFIX` (09-13) | Sua so giay LIVE ShadowBookC3 (ke toan, khong doi chien luoc) |
| I | `RESULT_SHADOW_T170_FIX` (09-18) | Fix shadow T170 + watchdog (ha tang) |
| I | `D1_DATA_AUDIT` (09-05) | Audit du lieu |
| I | `CI_REAUDIT` (09-03) | Audit phuong phap CI / block length |
| I | `AUDIT_APPLIED` (09-03) | Audit "da danh gia tot roi co apply duoc khong" |
| I | `AUDIT_BIGDOWN_DECOMPOSE_READJUDICATE` (09-15) | Phan ra entry-gate vs leg BIG_DOWN |
| I | `AUDIT_BIGDOWN_DEEP` (09-17) | Dao sau co che BIG_DOWN + nghi van leak/overfit |
| I | `AUDIT_CI_INFLATE_STANDARDIZATION` (09-17) | Chuan hoa `CI_INFLATE` (khong cuu duoc case n=248) |
| I | `AUDIT_GATEDYN_GD92` (09-11) | Ro soat doc lap claim "GD92 THANG" => khong vung |
| I | `AUDIT_GATE_DYN_PARITY` (09-11) | Parity gate tang 2 SIM vs LIVE |
| I | `AUDIT_HARNESS_OFI_2026-09-20` (09-20) | Bac bo population mismatch + non-determinism; tim ra confound that |
| I | `AUDIT_OI_FEAT_PARITY` (09-13) | Parity feature OI live vs training (KHONG VENH) |
| I | `AUDIT_READJUDICATE_CI_RESCORE` (09-15) | Cham lai T170 bang he so CI dung (3 rate ngoai CI) |
| I | `AUDIT_SELECTOR_MODEL_PARITY` (09-12) | Parity model selector live vs sim (KHAC) |
| I | `GD92_CODE_AND_RESULTS` (09-16) | Chua ket qua code GD92 (tai lieu tham chieu) |
| I | `LEAN_GATE_AUDIT` (09-12) | Audit gate tinh gon |
| D | `LABELH_RESULT` (09-04) | Doi chan troi nhan 72h->4h: **khong phan biet duoc**, cong tai lap mau thuan thiet ke |
| D | `LABEL_ROI_RESULT` / `LABEL_ROI2` / `LABEL_ROI3` (09-04) | CI cho phep so nhan + confound chong lan thuan se (khong dung ket luan) |
| D | `CEIL_RESULT` (09-04) | Tran oracle theo tung outcome; `retEnd_72h` CI [−6,0,+5,8] ≈ 0 |
| D | `C4_RESULT` / `C4H_RESULT` (09-04) | No ve sinh parity + do lai chan troi 4h (descriptive) |
| D | `G015CUT_RESULT` (09-06) | Bo 5 feature OI: **KHONG KET LUAN DUOC** (cong tai lap FAIL + khoang qua rong) |
| I | `G015REBUILD_RESULT` (09-06) | G015 tai lap duoc (khong phai phep so alpha) |
| D | `GS_WAVE1_RESULT` (09-04) | **Khong the phan biet bang du lieu DEV hien co** |
| I | `COV_RESULT` (09-04) | Kiem phu nhom TICK / xep hang |
| I | `NBETS_RESULT` (09-04) | Do dai block phu thuoc that / kiem phu CI |
| I | `TICKLOG_RESULT` (09-03) | Ha tang log quyet dinh tung tick |
| I | `E1_EXIT_RESULT` (09-05) | Batch loser time-stop horizon (parity) |
| I | `F1_FLOW_RESULT` / `F2_RESULT` (09-05) | F1 flow / F2 conditional exit = NULL |
| D | `B4_RESULT` (09-03) | Mo lai nhanh B4 rolling-percentile gate |
| D | `FS_RESULT` (09-04) | Tim feature moi S1 (co ung vien: `fs_taker_buy_7d`, `fs_body_ratio_7d` vuot nguong tren ca 2 thuoc do) |

---

## 6. KET LUAN

1. **Nhom B KHONG rong — nhung hop "dang xet lai" gan nhu da dong.**
   - Muc lon nhat tung bi treo la **BIG_UP / MEDIUM_UP / MEDIUM_DOWN** (B1) **da duoc xet lai ngay
     trong vong `LEVEL_SENSITIVITY` (A2)**: tang N x142-186 khong mua duoc power (N_eff dung yen
     32/111/52), va khi dem trung tinh theo episode thi duong tinh **bien mat** (≈0/am) => khong con
     ung vien nao.
   - Ung vien "con lon" nhat trong nhom B hien nay la **SEL_BIGDOWN (B3)**: point-estimate
     +54 USD/leg (+82%) nhung CI qua rong o n=248 leg.

2. **Cach duy nhat de tang power la them EPISODE DOC LAP (thoi gian that / forward) — da chung minh,
   khong phai gia dinh.** Noi nguong/tang so dong du lieu *khong* mua duoc power (x142-186 N, N_eff
   dung yen, MDE 12,8% -> 11,1%). Vi vay **"chay lai phan tich" tren du lieu cu la vo nghia**; cac muc
   B3-B16 chi co the phan giai bang tich luy forward/live response.

3. **Da so ket qua NULL gan day la DANG TIN (nhom A: 16) hoac bi loai vi rang buoc cung/co che
   (nhom C: 69).** Trong nhom C, phan lon la **rang buoc cung UW/maxDD/nam am** (khong phai cau hoi
   thong ke) => ra soat lai vo nghia tru khi doi khau vi rui ro (`RISK_APPETITE.md`, da chot).

4. **Khuyen nghi (1 cau):** Khong mo them vong "ra soat lai" nao tren du lieu hien co. Neu muon theo
   duoi tiep, chi co 2 viec hop le: (i) **theo doi forward** de them episode doc lap cho
   SEL_BIGDOWN/PUMPDUMP-POSTPUMP/MOM15-DEV (nho nhat, CI rong nhat), va (ii) ghi nhan **RA14**
   (`RESULT_REGIME_UPDOWN` §5, lead descriptive bi luat khoa chan) nhu mot gia thuyet can pre-reg
   rieng — khong phai ket luan.

---

## 7. Tuan thu

- Chuan **Python** (doc + so hoc), khong `claude-run`, khong chay Java tren Oracle (shadow dang chay),
  khong chay sim, **khong sua code san xuong**, **khong push**.
- Moi so lieu deu dan chieu tai lieu goc trong bang (cot "Tai lieu"/"Ngay"). Cac MDE lay nguyen tu
  `RESULT_HARNESS_CONTROL.md` §4 va `RESULT_LEVEL_SENSITIVITY.md` §0/§3; cac "MDE proxy" cho vong sim
  la **half-width CI da cong bo**, ghi ro la proxy.
