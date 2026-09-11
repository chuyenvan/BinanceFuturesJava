# QUEUE — hang doi thi nghiem DEV, theo thu tu

Doc `docs/AGENT_RUNBOOK.md` truoc. Moi job phai co `docs/PREREG_*.md` commit TRUOC khi chay.
Lay job DAU TIEN co status `READY`. Job `BLOCKED` phai cho user duyet trong chat.
Sau khi xong: doi status thanh `DONE <commit>`, ghi ket qua vao doc rieng, commit.

---

## AUDIT_GATEDYN — ro soat doc lap claim "GD92 THANG" (272d8f1/1c1ecca/41d5d76)  [DONE / `docs/AUDIT_GATEDYN_GD92.md`]

Chay lai GD92 tu dau tren dataset build lai: **byte-identical** (`c18314d661…`, n=2,355) => so lieu
cua GATEDYN/GATEDYN2 tai lap 100%, scope sach (SIM_END_DATE=20251231, khong cham 2026, bins X1
khong rebuild, `GateRollingThreshold.java` khong sua, nBeforeFirst=0), pre-reg commit TRUOC run o
ca hai dot. Nhung phan quyet **KHONG PHAN BIET DUOC**: paired block-bootstrap (block 21, 2000 rep,
seed 20260903) cho `d = CAGR(GD92) - CAGR(PARITY_R) = +4.98pp`, `CI95 [-4.47, +16.09]` **chua 0**,
`sd_boot 5.20`, cach nguong hieu chinh boi k=9 (`2.0963*sd = 10.90`) hon 2 lan; theo nam dau doi
chieu (2022 **-10.06pp**, CI [-20.97,-1.10] = GD92 XAU hon o nam gau; 2023 +13.69; 2024 -0.97;
2025 +20.38), deu KHONG DAT. Bang chung quyet dinh cua OpenClaw la **UW** — so quan sat mot lan,
`PREREG_CI` 2.5 cam coi la co CI — va GD92 dat 116/nguong 120 (du 4 ngay) trong khi lang gieng
cung pct cho 153 (W=120) va 183 (W=60). Dot GATEDYN2 (grid pct x W quanh winner) **vi pham**
`B4_RESULT` 179-180 ("noi cua so, doi phan vi ... = leak L2"); ket qua "6/6 FAIL" la dau hieu
**dinh nhieu**, khong phai vung on dinh (3 metric dat dinh o 3 diem khac nhau). PRIMARY (do deu,
CV quy 0.712->0.518) la THAT va tai lap duoc — nhung khong duoc suy ra "THANG".
**KHUYEN NGHI: khong chot GD92 vao production** bang bang chung DEV hien co; muon nang len ket luan
thi can VALIDATION/holdout voi pre-reg rieng, mot cau hinh duy nhat (0.92/90), khong quet them.
Artifact: `research/analysis/ci_gatedyn.py`, `devrun/X1_C3_FULL_GD92_R/`, `/home/ubuntu/wfo_ds_x1`
(4.0G, GIU — dataset canonical khung X1).

---

## G015ABL -- ro soat 45 feature net015, bo dan funding-drift cluster (f23, f18/f21/f22)  [DONE / `docs/RESULT_G015ABL.md`]

Pre-reg `docs/PREREG_G015ABL.md`. Them Stage 0 (control, retrain 45 feature) sau khi phat
hien retrain-noise (G4_RECIPE_C4.md: spearman 0.986 vs model goc = trong nen nhieu seed) --
so Stage 1/2 VOI Stage 0, khong so truc tiep X1_C3_FULL_PARITY. Cong hoi quy Stage 0 PASS
(spearman fold 20240101 = 0.985997, khop 6 chu so voi G4_RECIPE_C4.md). Stage 1 (bo f23):
0/5 rate thang ngoai CI, mMargin am ca 4 nam (~-10%), vi pham UW 2022 (+108 ngay) -- NULL
"sach". Stage 2 (bo them f18/f21/f22): 0/5 rate thang, mMargin am manh hon (~-21%), nam 2022
VO NANG (maxDD -27.74% vs -10.61% control, UW +196 ngay, nam AM duy nhat trong ca thi
nghiem, quy moi vi pham -15.1%) -- NULL "nang". Gia thuyet: cum funding-drift mang tin hieu
regime that (dac biet nam dau DEV, funding bien dong manh), khong chi la time-proxy nhu
FEAT40_LOOKAHEAD.md canh bao. => GIU NGUYEN net015 45-feature. Model/code 3 stage giu lai
tren Oracle (~3.4GB) + Kaggle kernel de tham khao. Dataset tam da xoa het.

---

## 5MGRID -- predict net015 luoi 5 phut (model 15 phut) + S1 train lai 5 phut  [DONE / `docs/RESULT_5MGRID.md`]

Pre-reg `docs/PREREG_5MGRID.md` (cap nhat 2026-09-08 sau khi Kaggle GPU train net015 o 5
phut OOM-kill 2 lan -- user chi dao doi huong: GIU model net015 15-phut, chi predict-only
tren feature 5-phut; S1 van train lai day du 5 phut). Doi chung `X1_C3_FULL_PARITY`
(15 phut, equity 111,428/n=2,266) vs `X1_C3_5M` (5 phut, equity 74,150/n=2,464), cung
`TICKER_SOURCE=file`. Ket qua: 2/5 rate ngoai CI toan cua so -- CA HAI THEO HUONG XAU cho
5M (win% -2.02pp, TSloss% +1.92pp), 0/5 theo tung nam. Rang buoc cung VI PHAM CA 4 NAM
(te hon K12): 2022 UW +39 ngay, 2023 maxDD +3.63pp, 2024 UW +97 ngay, 2025 maxDD +12.13pp
+ nam am (-3.68%) + quy moi vi pham -5.78%. Co che: STRONG% tang (76.5%->80.8%, nhieu
candidate hon nhung chat luong thap hon) -> mMargin giam 20% -> DCA leg2+ PnL 2025 dao
chieu hoan toan (+4,813 -> -7,031). => NULL, GIU luoi 15 phut cho `X1_C3_FULL`. Giu lai
cong cu (`g015_predict5m.py`, S1 5-phut, `x1_c3_full_5m.properties`) vi da xac nhan dung
ky thuat, chi khong sinh loi. Dataset tam (`wfo_ds_x1_5m` 4.0G) da xoa.

---

## K12 -- SELECTOR_RANK_TOPK 8->12 tren C3_FULL 48 thang  [DONE / `docs/K12_RESULT.md`]

Pre-reg `docs/PREREG_K12.md` (`bc9d066`). Cong parity K=8 PASS (khop X1_EXTEND tung so).
Ket qua: chi 1/5 rate ngoai CI toan cua so, 0/5 theo tung nam -- khong dat nguong thang.
Rang buoc cung VI PHAM nhieu: 2022 maxDD -12.46->-17.09 (+123 ngay UW), 2024 UW 121->239
+ quy MOI vi pham -6.31%. Co che: TSloss% xau don dieu 4/4 nam (giong F1_FLOW, nay THAY
tren nen C3_FULL co DCA -- DCA leg2+ PnL giam vi budget loang). => NULL, DONG huong,
GIU SELECTOR_RANK_TOPK=8 cho C3_FULL. Dataset tam da xoa.

---

## Q00000 — L4: `build_map` chay LIVE (shadow = C3 o tang entry)  [DONE / `docs/L4_LIVE_BUILDMAP.md`]

Khong pre-reg rieng: day la **sua mot loi da duoc do** (`G4_RECIPE_C4` muc 6.5 — shadow dung
thang gia tri SAI ho o tang admission), khong phai thi nghiem moi. Cong deu la cong TAI LAP.
- **Quy uoc `build_map`** rut tu code + kiem 3 duong doc lap: `symbolPred = 1 − P(win)`;
  coin rank k (S1, thap=tot) nhan `P(win)` lon thu k; `rank(method="first")` pha the theo
  THU TU DONG. Xem `AGENT_RUNBOOK` muc 0 diem 11.
- **REPLAY 3 ngay DEV PASS**: port `build_map` **byte-exact** (`max|d| = 0`, 150,084 dong);
  end-to-end spearman **1.000000**, top-8 **100.0000%**, multiset `max|d| = 4.768e-07`.
- **105/105 unit test** (97 cu + 8 moi), fixture vang do chinh pandas sinh.
- Goi `/home/ubuntu/deploy_242_l3/` da cap nhat (jar moi + 2 model + 2 feature-order + sha,
  `verify.sh` co cong `[MAP]`). **242 CHUA DEPLOY** — 3 lenh o `README_DEPLOY.md` muc 1.

Viec DE LAI (**KHONG tu chay**):
- 🔴 **Cong 45 feature live vs Tool1 CHUA DO DUOC** — `oi_feat_*` 242 chi giu 2 thang.
  Hai duong, ca hai deu can USER DUYET: (1) backfill `ComputeOiFeat2Live242` cho 2025-11/12
  (**GHI len 242**); (2) do tren 2026-08 (**can `HOLDOUT_UNSEAL`**). Agent khong tu mo.
- ⚠️ Sau khi user deploy: bat `tools/pull_242_shadow.sh` de keo log ve doi chung.

---

## Q0000 — G5: nhan/horizon cho VALUE MODEL  [DONE / `docs/G5_VALUE_LABELS.md`]

Pre-reg `docs/PREREG_G5.md` (`f0b088b`). Thiet ke: **hieu chuan CO DINH** (multiset x26/tick),
**ung vien chi quyet dinh THU TU**. 7 model train moi tren Kaggle GPU (16 fold, ~30'/model),
10 sim 48 thang tren Oracle.
- **Cong leak 18/18 fold PASS** (`ts_max <= cutoff−72h`, bien an dung 15'); OOS thuan, khong
  chong lan (kiem doc lap tu `ts_min/ts_max` cua 16 bins). Wrapper user cung cap ghi
  `FIRST_CUTOFF=20230101` — **LECH**, log goc la `20220101`; da dung `20220101`.
- **Cong parity PASS byte-identical** `X1_C3` (md5 `d39da294…`, 2,058, 98,523).
- **Kiem cau truc PASS TUYET DOI 8/8**: quantile-map cho `pass=103,840` / `adm_top8=5,906`
  bang tung don vi voi parity.
- 🔴 **KHONG ung vien nao thang**: 8/8 arm co >= 1 rate chat luong XAU ngoai CI, **0 rate TOT**;
  8/8 FAIL rang buoc cung >= 2 nam (parity PASS 4/4). Ho **72h** xau nhat (2025 thanh nam AM
  20-25%). `maxfav06_4h` it xau nhat (1/5, equity 86,047) nhung van FAIL 2 nam.
- 🔴 **`G5_x26_order` thua parity 4/5 rate** => **thong tin COIN do S1, khong do value model**.
  Value model = bo sinh nguong gate theo tick. Xac nhan cau truc voi `L1` (trailing: khong
  load-bearing) va `C4` (gate: hieu chuan load-bearing).

Viec DE LAI (chua co pre-reg, **KHONG tu chay**):
- ⚠️ Ghep S1 (thu tu) voi `maxfav06_4h` (hieu chuan) — o trong duy nhat con lai cua truc nay.
- ⚠️ Nhan **168h** van chua ai kiem (`LABELH` muc 4.3, `T1_LABEL3` muc 9, G5 chi 4h/72h).
- ⚠️ `C4_maxfav` 48 thang: kernel `g015v2-maxfav-cpu` DA FAIL (argparse). G5 da tra loi
  cau hoi do o duong khac (`maxfav06_4h` 16 fold) => **khong can chay lai**.

---

## Q000 — G4: recipe net015 tai dung + C4 thang GIA TRI  [DONE / `docs/G4_RECIPE_C4.md`]

Pre-reg `docs/PREREG_C4.md` (`4da1486`). Ba viec:
- **Recipe `net015` DUNG LAI DUOC** (`docs/G015_RECIPE.md` + `research/pipeline/g015_net_train.py`).
  Cong GPU-vs-GPU tren fold 8: spearman **0.985997**, top-8 **0.8296** — **PASS**, vi nen nhieu
  giua SEED tren cung GPU la 0.984931 / 0.8246. Nhan xac minh doc lap: `KEEP=48,724,373`,
  `base=0.1849`. Bang 18 fold: `pos` tu log khop `scale_pos_weight` tu model 18/18.
- **`C4_parity` byte-identical `X1_C3`** (md5 `d39da294…`, 2,058, 98,523) — moi truong khong troi.
- **`C4_regen`**: n giong het, trung khoa `(sym,start)` 99.90%, `win%`/`TSloss%`/`mP|SL` bang 0
  tuyet doi, chi `mean(margin)` +0.18% ngoai CI => **1/5 — FAIL van ban, PASS noi dung**.
  Nguyen nhan goc: `build_map.py` khuech dai 1 ULP thanh 0.3715 (thu tu dong).

- 🔴 **`C4_maxfav30` (30 thang, 10 fold co san): THANG GIA TRI CO LOAD-BEARING O GATE.**
  admit **x5.05** (4,857 vs 961), `win%` −8.04pp, `TSloss%` +8.44pp => **3/5 rate ngoai CI**;
  chi **13.11%** lenh cua parity con ton tai; FAIL rang buoc cung moi nam; equity 28,384 (am).
  **NGUOC voi `L1` o tang trailing** (o do gia tri KHONG load-bearing, 0/5). Arm 48 thang van
  dang train (`chuyendinh/g015v2-maxfav-cpu`) — bo sung, khong thay the.

Bon viec DE LAI, deu can pre-reg rieng, **KHONG duoc tu chay**:
- 🔴 **Thay `Funding_Classifier_Final.onnx` cua duong live bang ONNX cua net015** — model live
  thuoc ho `maxFav` (spearman 0.961 voi `G015_v2`, 0.854 voi net015). Day la DEPLOY, phai co user.
- 🔴 **On dinh hoa `build_map.py` + `sort_values`** (`kind="stable"` + sort phu theo `symId`) —
  se doi bins deploy hien tai, phai do lai baseline.
- ⚠️ Hoan tat `C4_maxfav` roi cham bang `research/analysis/c4_rates.py`.
- ⚠️ Khoi dong lai shadow C3 Oracle (`shadow_c3/app/bin/daemon.sh start`) — dang TAT.

---

## Q00 — X3 trailing cap theo RANK + pre-arm SL -50%  [DONE / `docs/X3_RANKCAP_SL50.md`]

Pre-reg `docs/PREREG_X3.md` (`e622926`). 5 run tuan tu tren Oracle, 48 thang, nen `X1_C3`.
Cong hoi quy PASS byte-identical (`X3_PARITY` = `X1_C3`, md5 `d39da294...`, 2,058 lenh).
**CA HAI VIEC NULL.** Da them vao engine: `TS_CAP_STRONG_RANK` (mac dinh 0 = TAT).
**Khong de cu baseline moi.**

Bon viec DE LAI, deu can pre-reg rieng, **KHONG duoc tu chay**:
- 🔴 **R4 (UW) phai dua len user** — bang chung dinh luong moi: `X3_R6` khong phan biet duoc voi
  PARITY o **moi** rate muc lenh (0/8 ngoai CI, `n` va `win%` giong het) nhung `UW 2022` 64 -> 159.
- **Tin hieu cho pha SAU-ARM van la vung trang.** X3 chi chung minh rank selector KHONG phai tin
  hieu do. Huong con lai: dai luong sinh ra tu chinh pha sau-arm (bien dong realized cua cum,
  `maePeak`/thoi gian tu luc arm). Trung mot phan voi `SIM_COND_EXIT_*` cua F2.
- **`TS_MAX_GAP` / `TS_MAX_GAP_WEAK` (0.08 / 0.03) chua bao gio duoc quet tren 48 thang.** X3 chi
  doi AI duoc cap nao, khong doi cap la BAO NHIEU. `W1` truc A/C van trang.
- ⚠️ **Duong Kaggle 48 thang: code DA THONG, nut that la BANG THONG.** `tools/kaggle_sim.py` da sua
  (`TICKER_DS` + guard 1,461 day qua `CFG["ticker_min_days"]`). Nhung bundle X3 = **5.32 GB** va
  throughput Oracle -> Kaggle do duoc **3.23 MB/s** => **27.5 phut upload thuan**, khong nhanh hon
  52 phut chay tuan tu. Sau khi upload MOT lan thi doi jar chi ton 95MB — luc do Kaggle moi thang.

---

## Q0 — X2 exit 48 thang  [DONE c633861 / `docs/X2_EXIT48.md`]

Hai truc exit (time-stop T, pre-arm hard SL S), 6 run one-at-a-time tren nen `C3` / 48 thang.
**CA HAI TRUC NULL** theo quy tac da chot: `win%` giam ngoai CI o 5/5 muc va **0/5 muc PASS
rang buoc cung**. Cong hoi quy byte-identical PASS (`X2_PARITY` = `X1_C3`, md5 `d39da294...`).
Da them vao engine: `SIM_PRE_ARM_SL` (mac dinh 0 = TAT). **Khong de cu baseline moi.**

Ba viec DE LAI, deu can pre-reg rieng, **KHONG duoc tu chay**:
- 🔴 **Nguong UW can user quyet lai.** X2 dung R4 TUONG DOI (<= 1.2x UW parity cung nam)
  vi nguong tuyet doi 120 khong con dat duoc (`X1_EXTEND` muc 7). Voi R4 tuong doi: parity PASS,
  moi arm FAIL. Rang buoc nay **chua tung duoc user duyet**. `T120` la ung vien neu user chap
  nhan danh doi "UW 2025 302 -> 137, doi lay UW 2022 64 -> 99".
- **SL PHU THUOC TRANG THAI** (`SIM_COND_EXIT_HOURS` / `SIM_COND_EXIT_MIN_FAV`, co san tu F2,
  **chua bao gio quet tren 48 thang**) — huong con lai sau khi SL TINH da bi bac bo.
- ~~Sua `tools/kaggle_sim.py` cho cua so 48 thang~~ — **DA TRA o X3** (`X3_RANKCAP_SL50` muc 11).

---

## Q1 — Chot horizon time-stop  [BLOCKED: can user duyet mo lai quota] — LUU Y: F2/T1/W1 deu thay cat som keo UW len 150-190d; mo lai chi khi rang buoc UW<=120 duoc chap nhan la tieu chi

E1 da dung het quota 4/4 (`docs/PREREG_EXIT.md`) va ra phan quyet TS_H=72.
Nhung pre-reg co 2 loi dac ta, agent tu phat hien va KHONG sua sau:
- P2 do **count tuyet doi** cua `STOP_MARKET_DONE` nen bo qua win rate tut
  84.85% -> 79.21% (tong lenh tang 970 -> 1010 vi cat som giai phong margin).
- Rang buoc cung dat theo **NAM** nen X72 pass, du underwater dai ra
  **93 -> 156 ngay** va 2022Q1 di tu +0.7% xuong **−4.4%**. Neu dat theo QUY thi
  X96 va X72 deu bi loai.

Day la van de vi underwater 93 ngay la **ly do duy nhat** con bien minh cho viec
giu C2b (xem AGENT_RUNBOOK muc 4). X72 danh doi dung cai do.

**Can user quyet:** mo lai quota voi pre-reg sua 2 loi tren (P2 do TY LE thang,
rang buoc theo QUY + underwater <= 120 ngay), hay chot X96 (maxDD −10.7%, tot nhat
trong 4 run, mean(profit|SL) −13.99 vs −18.90 parity), hay giu 168h.
KHONG duoc tu chon X96 sau khi da thay so — do la sin.

---

## Q2 - Ban le STRONG/WEAK `TS_PNOPUMP_WEAK_THR`  [READY - key DA SONG sau fix B1 (C3). Vung trang: 71.5% lenh di STRONG. Quet LAI TU DAU tren nen C3, KHONG dung so W1 cu]

**Co che:** ban le dang 0.29 ma **88.55% hang duoc admit co score < 0.30**. Tuc ban le
nam dung giua dai van hanh — dich mot chut la lat hang loat lenh giua cap giveback
8% (STRONG) va 3% (WEAK). Chua tung co run don le nao. Sobol hang 10 (0.0099).

**Runs: dung 3.** `SIM_TS_PNOPUMP_WEAK_THR` in {0.05 (tat ca STRONG), 0.29 (parity),
0.60 (tat ca WEAK)}. Nen C2b, 1 dataset build. Tag `W005` / `W029_parity` / `W060`.
Dat qua **profile copy**, khong qua env (bay so 2).

**Tieu chi PRIMARY (rate tren 800+ lenh):** `mean(profit | STOP_MARKET_DONE)` va
`sd(profit | STOP_MARKET_DONE)`. Gia thuyet: cap rong hon (STRONG) => giu winner lau
hon => mean cao hon nhung sd cao hon. Neu mean **khong** doi qua 0.5pp giua 0.05 va
0.60 thi ban le nay TRO va dong lai vinh vien.
**Rang buoc cung:** maxDD <= 15%, underwater <= 120 ngay, khong quy nao < −5%.
**Parity gate:** `W029_parity` phai byte-identical C2b (md5 8f7afdfb...).
**Quy tac quyet dinh:** chon bien the co mean(profit|STOP_MARKET_DONE) cao nhat MA
thoa het rang buoc cung. Neu ca 3 trong sai so thi ghi null va dong huong.

---

## Q3 - Siet momentum gate  [DONE - do LAI tren engine da sua (C3_mom006): noi 0.006 -> 5/5 rate chat luong TRONG CI, FAIL 3/4 rang buoc cung. Gate 0.008 KHONG bo qua chat. Dong huong]

**Co che:** chieu NOI da thu va xau: 0.006 -> equity cao hon (60,953) nhung maxDD
**−21.1%** (vuot tran 15%); 0 -> 10,305 voi 14,007 lenh. Chieu SIET **chua tung thu**
tren nen C2b. Gia thuyet: siet cat dung nhom lenh bien — nhom chiem phan lon 147 lenh
bi time-stop (66.6% chua tung vuot +3% lai).

**Runs: dung 3.** `SIM_MIN_MOMENTUM_15M` in {0.008 (parity), 0.010, 0.012}.
Tag `M008_parity` / `M010` / `M012`. Profile copy.

**Tieu chi PRIMARY (deu la rate):** `TSloss%` (= n STOP_LOSS_DONE / n tong) phai
GIAM don dieu khi siet; `win%` phai TANG; `mean(profit|STOP_MARKET_DONE)` khong
duoc giam qua 0.3pp.
**Rang buoc cung:** so lenh khong duoi 600 (duoi nua thi mat het power do luong);
maxDD <= 15%; underwater <= 120 ngay.
**Quy tac quyet dinh:** chon muc siet cao nhat thoa het dieu tren. Neu TSloss%
khong giam don dieu => co che sai, ghi null, dong huong.

---

## Q4 — Mo DEV ve 2021-07  [BLOCKED: can user quyet danh doi]

Chi tiet `docs/D1_DATA_AUDIT.md`. Trang thai:
- Moc som nhat kha thi = **`20210701`** (train 329,882). `20210401` train = 0 vi
  `wfo_gate_pred.csv` bat dau 2021-03-31. => **duoc +6 thang, khong phai +11.**
- Aerospike da du 2021, **khong can copy gi**.
- `rk_oi_delta24h`: cat mat ~0 (mean IC 0.0000, doi dau, |IC| max 0.0165).
- `ls_global`: cat mat THAT — mean IC −0.0396, manh thu 4/9, 1 trong 4 feature
  nhat quan dau, ~13% tong |IC| cua nhom nhat quan. Sau khi cat, S1 con 3 feature
  nhat quan => gan nhu thuan volatility/drawdown.
- Trong 2021 CA HAI = noise (OI 1 coin/thang toi 2021-11) => giu chung khi mo ve
  2021H2 con **te hon** cat.
- **BLOCKER cho tang tien:** `predwf_G015x26` khong co bin 2021 (som nhat 20220101)
  va G015x26 ~~KHONG reproduce duoc~~ (**DA GO** 2026-09-06, `docs/G3_X26_RECOVERY.md` —
  tai lap duoc spearman 1.0; van thieu bin 2021 vi `FIRST_CUTOFF=20220101`, nhung gio
  SINH duoc bang `g015x26_train.py` neu can). => mo 2021 chi validate duoc **tang selector**
  (rank-IC / edge5) qua Python, **KHONG chay duoc Java sim**. Muon co equity 2021
  phai train G015 moi cho 2021Q3/Q4 — luc do khong con la G015x26 va provenance
  cua C2b doi.

**Can user quyet:** (a) chi lam tang Python de biet selector co on dinh qua regime
bull khong — nhung da chot la selector khong quan trong, nen gia tri thap; hoac
(b) train G015 moi cho 2021 va chap nhan doi provenance baseline; hoac (c) bo qua.

---

## Q5 — Sizing  [DONG — khong chay]

`F_BASE` (importance #1 Sobol, PDP don dieu −4.83 -> +8.12pp), `U_MAX` (#4),
`DCA_GRID_SCALE` (#3, 1.5 -> 2.0 cho 59,227 nhung maxDD −15.55 vuot tran).
**Ly do dong:** sizing khong doi chat luong tung lenh, chi doi thang do. Tieu chi
duy nhat con lai la maxDD/underwater — deu single-realization, n_eff nho, khong co
power. Day la nut risk preference user dat, khong phai bai toan toi uu.
Mo lai chi khi user noi ro muc rui ro muc tieu (vd "chap nhan maxDD 20% de doi CAGR").

---

## Q6 — No ky thuat, khong sinh alpha nhung phai lam  [READY, uu tien thap]

1. Patch `VisionMetricsClient.parseDay` (lo 5-phut forward) — BAT BUOC truoc moi
   rebuild OI.
2. Rotate API key trong git history.
3. Don 5 key chet khoi `configs/c2b.properties` + `c2b_ticklog.properties` roi bat
   `CONFIG_STRICT=1` lam gate mac dinh.
4. Dong venh K=8 (sim) vs K=5 (live).
5. Giai phong dia: an toan cao ~9.5 GiB, can xac nhan ~30 GiB (`docs/D1_DATA_AUDIT.md`
   muc D). **2 bay:** `up5/*.zip` va `up_zip/*` cung inode (nlink=2) => xoa 1 ben
   duoc 0 byte; truncate set Aerospike KHONG shrink `.dat`.

---

## F1 — Nới dòng cơ hội ở tổng exposure không đổi  [DONE `d6935ef`]

**Kết luận:** NULL — `SELECTOR_RANK_TOPK` 8→16/24/32 (bù `SIM_F_BASE` giữ
`K × F_BASE = 0.24`, C1 lệch chỉ +4%) làm `sd(daily)` giảm đúng dự đoán
(0.008098→0.006913) nhưng `mean` giảm gấp 3 lần thế, Sharpe 1.491→0.980, và cả 3
biến thể LOẠI ở ràng buộc cứng (underwater 195/227/254d vs 93d) ⇒ **giữ K=8, đóng
hướng**. Cơ chế: `medP`=5.50 không đổi nhưng `TSloss%` tăng đơn điệu 15.2→21.7%
trên 970→2,779 lệnh — rank sâu chết bằng time-stop nhiều hơn, không phải thắng ít hơn.
Pre-reg `576e6c2`, chi tiết `docs/F1_FLOW_RESULT.md`.

---

## F2 — Conditional exit: cắt lệnh KHÔNG CHẠY tại giờ H  [DONE `7d0eb38`]

**Kết luận:** NULL — luật "chưa arm + giữ > 72h + đỉnh đạt được < 5%/4% ⇒ đóng market"
cắt TRÚNG nhóm chết (`mean(profit|STOP_LOSS_DONE)` −18.90 → −13.95%, `mean(profit|
STOP_MARKET_DONE)` chỉ −0.034pp) nhưng **FAIL 2/3 PRIMARY** (`TSloss%` 15.15→19.04,
`win%` 85.26→81.66) và **FAIL ràng buộc cứng** (underwater 93→156 ngày, cùng con số của
E1 `X72`) ⇒ **đóng hướng**. Cơ chế hỏng ở đường truyền: margin giải phóng sớm KHÔNG quay
vòng đủ (tổng lệnh chỉ 970→1,003, +3.4%) nên không pha loãng được mẫu số — lần thứ hai
sau F1 một hướng chết vì kênh tái triển khai vốn yếu hơn giả định. Equity cao hơn
(60,390→61,851/62,317) nhưng đi NGƯỢC phán quyết và nằm trong nhiễu 2.57pp ⇒ không dùng.
Đo offline `docs/F2_COND_EXIT_MEASURE.md` (join nhãn 100%, dự báo số lệnh bị cắt 146 vs
thực tế 148 — công cụ dùng được). Pre-reg `a4b3b05`, chi tiết `docs/F2_RESULT.md`.
Param `SIM_COND_EXIT_HOURS` / `SIM_COND_EXIT_MIN_FAV` giữ trong code, mặc định 0 = TẮT.

---

## F3 — Nguồn cung hay tầng quyết định?  [DONE `5a32d0e`]

**Kết luận:** hệ bị giới hạn bởi **CUNG**, nhưng trục khan hiếm là **THỜI GIAN gate thị
trường mở** (`p15` là scalar mức-tick, `sd` trong tick = 0; `spearman(npass,p15)`=+0.454 vs
`spearman(npass,U)`=+0.021) — **không phải universe**: mục A không khử được confound
(`spearman(U,tháng)`=+0.995, mọi spec khử confound MDE80 ≥ 1.09 ⇒ **không kết luận được**),
và A7 cho thấy U to hơn cải thiện ĐIỂM của top-8 (t=−4.9) nhưng KHÔNG cải thiện kết quả
thực (`g1lite` +0.03 CI[−0.16,+0.22]) ⇒ **đóng hướng mở universe**. 86.6 coin good/giờ-gate-mở
nhưng chỉ 2.90 qua gate và **94.85% giờ-gate-mở có 0 cơ hội**; vị thế đang giữ = **6.275**
trong giờ-gate-mở (1.894 trên mọi giờ) ⇒ vốn KHÔNG nằm không lúc có cơ hội — lý do E1/F1/F2
đều null. B bác lại cách đọc "medP bất biến": `P(good)` 0.699→0.565 và `mean(g1lite|good)`
0.1778→0.1070 theo độ sâu rank (t=24.8); median là đại lượng trơ. D: hạ K=8→5 mất **33.54%**
nguồn cung good qua gate và **32.0%** khối lượng `g1lite` ⇒ khe K=8/K=5 là lỗ hổng
**fidelity** (`Q6.4`), không phải nguồn alpha. Chi tiết `docs/F3_SUPPLY.md`, script
`research/analysis/f3_supply.py`. **Không pre-reg** (đo offline thuần, không chạy sim).

---

## F4 — Tầng timing có phải nơi chứa alpha?  [DONE `0c649e0`]

**Kết luận:** NULL — nhưng là **null KHÔNG CÓ POWER**, và đó mới là kết quả chính. Dựng lưới tick
mở rộng **86,971 tick** DEV (từ `wfo_gate_pred.csv` + `predwf_G015x26` + `label_15m`, vì
`cand_dev.parquet` chỉ có 4,639/87,552 tick) rồi đo rank-IC với `Y_tick` = `mean(g1lite)` top-8:
`p15` **+0.1000**, `br_lag3` +0.1553, `p15_ma24h` +0.1088, `mkt_vol7` +0.0901, `mkt_dd7` +0.0186
(dấu LỆCH). **Không ứng viên nào đạt ngưỡng** (CI của hiệu, block 72h × 2000 rep × f=1.21, đều
chứa 0) ⇒ `p15` giữ nguyên. Lý do thật: `sd_boot = 0.033` ⇒ **`n_eff ≈ 908`, KHÔNG phải 86,615**
(hệ số phóng đại 95×) ⇒ **MDE80 của hiệu ≈ 0.13 > chính rank-IC của incumbent (0.100)** — cuộc thi
gần như không thể thắng. **Giả thuyết "chuyển sang mức tick sẽ phá tường power" là SAI**; `n_eff`
tỷ lệ với số khối 72h (tức độ dài lịch sử), không với tần suất lấy mẫu. Ứng viên khá nhất
`br_lag3` mất **38%** rank-IC khi bịt rò rỉ ~1 ngày (`br_lag4` +0.0973, 2022 sụt +0.138→+0.031)
và khi đó **thấp hơn** `p15`. Model tổ hợp 5-biến (XGB CPU, WFO quý, purge 72h) **THUA biến đơn**:
+0.0866 vs +0.1297 OOS. `mkt_dd7` bị loại dứt khoát (CI hiệu trên `Y2` nằm trọn dưới 0).
**False negative (cả 2 định nghĩa gate):** gate CÓ chọn lọc thật — `q = P(Y|ĐÓNG > median(Y|MỞ))`
= **0.3534** (Gate-A `p15>=0.008`) và **0.2277** (Gate-B `gate_dyn_ok`), giảm đơn điệu từ 0.5;
`mean(Y|MỞ)−mean(Y|ĐÓNG)` = +0.0224 / +0.0727; `P(good)` 0.669/0.544 và 0.782/0.549. NHƯNG khối
lượng tick trên-trung-vị ngoài gate = **29,115** (12.67× so mốc) / **19,694** (83.98×) vì tập ĐÓNG
lớn gấp 18×/184× ⇒ đây là bài toán **đặt ngưỡng**, không phải **chọn biến**. Cảnh báo: đếm TICK
chứ không phải cơ hội độc lập (~101 đợt sau khi khử chồng lấn 72h), `Y_tick` là danh mục KHÔNG
giao dịch được, không có xác nhận P&L. Hướng mở duy nhất: **sweep ngưỡng `p15`** trên lưới đã dựng
`/home/ubuntu/ledger/f4_ticks.parquet` — chi phí ~0, nhưng chỉ chạy nếu viết được công thức đánh
đổi precision/coverage TRƯỚC. Pre-reg `1fa042d`, chi tiết `docs/F4_TIMING.md`, script
`research/analysis/f4_timing.py`.

---

## G1 — Tầng đặt GIÁ TRỊ gate có nên chuyển sang horizon 72h?  [DONE]

**Kết luận:** NULL **có hướng NGƯỢC** — không phải null thiếu power. Train lại đúng recipe
G015 (45 feature, XGBClassifier, 10 cutoff, purge 72h, CPU, seed 42), đổi **duy nhất** nhãn
`maxFav_4h>=0.06` → `maxFav_72h>=0.07` (0.07 = đúng `SIM_RATE_PROFIT_STOP_MARKET`), được `G72`.
`G72` xếp hạng **KÉM HƠN** `G4_repro` **ngay trên outcome 72h mà nó được train**:
AUC **0.6259 vs 0.6558**, hiệu **−0.0299** CI95×1.21 **[−0.0459, −0.0145]** (nằm trọn dưới 0),
`P(d>0)=0.0000`, dấu nhất quán **3/3 năm** (2022 −0.0332 / 2023 −0.0326 / 2024 −0.0277).
spearman vs `Y72` −0.0498 [−0.0763, −0.0243]; vs `g1lite` −0.0290 [−0.0579, +0.0013].
`n=15,442,092` dòng OOS DEV, join nhãn **100.00%**, **304 khối 72h**, 2000 rep, seed 20260906.
**Cổng GO/NO-GO FAIL ⇒ 0/2 sim run đã chạy**; `PREREG_G1_SIM.md` không được thực thi, không có
số parity/PRIMARY/equity. **`predwf_G015x26` giữ nguyên, C2b không đổi gì.**
**Cổng REPRO PASS tuyệt đối:** `g72_train.py` với nhãn cũ ra **byte-identical 10/10** với
`predwf_G015_v2`, `spearman=1.00000000` trên 15,536,189 bản ghi, `rho=0.18991` khớp
`G015_PROVENANCE §0` ⇒ đổi nhãn là biến duy nhất. Đây cũng là **xác nhận độc lập thứ ba**
rằng pipeline G015 deterministic.
⚠️ Pre-reg §1 đã cảnh báo trước "H1 gần như hiển nhiên đúng vì G72 train trên chính họ nhãn
dùng để chấm" — **cảnh báo đó SAI ở dấu**, ghi lại nguyên vẹn.
Bác bỏ **đúng một mệnh đề**: "đổi nhãn G015 sang 72h/7% thì gate tốt hơn". **Không** bác bỏ
"horizon là trục có tác dụng" — mới chạm 1 họ nhãn / 1 ngưỡng / 1 kiến trúc.
Hướng gate còn mở vẫn là **hiệu chuẩn ngưỡng theo phân vị của chính S1** (`C2B_SPEC §1`).
⚠️ Caveat window overlap: bảng động cơ "so horizon trên 970 lệnh thật" bị nhiễm (ROI tới 168h),
`LABEL_ROI2 §2` đã retract vì đúng lý do đó — **không trích làm bằng chứng**.
Pre-reg `f931265` + `6519c22`, chi tiết `docs/G1_HORIZON.md`, script
`research/pipeline/g72_train.py`, `research/analysis/g1_repro_check.py`,
`research/analysis/g1_horizon_eval.py`.

---

## BD — Train ở đâu được: Oracle hay Kaggle?  [DONE]

**Kết luận:** **Kaggle CPU == Oracle CPU byte-for-byte** ⇒ được train ở bất kỳ đâu trên CPU,
vô điều kiện. 3 môi trường × 3 seed trên cùng một file đã đóng băng (`bench_s1.parquet`,
1,220,490 dòng, sha256 file + sha256 mảng X **khớp tuyệt đối** cả 3 nơi). Oracle (aarch64,
py3.10.12, numpy 2.2.6) vs Kaggle CPU (x86_64, py3.12.13, numpy 2.0.2): per-tick
`mean|ΔrankIC|` = **0.0 chính xác**, `ic_sha256` trùng cả 3 seed, cây đầu tiên trùng sha256.
Số cũ `0.17040 vs 0.1723` là **lệch dữ liệu/pipeline, không phải lệch máy** — không được dùng
để khoá vào Oracle. **GPU lệch thật nhưng vì lý do khác lệnh cấm cũ:** per-tick 0.02185 chỉ
**×1.07–×1.20** nhiễu seed và `edge5` 0.198pp chỉ **×1.21**, nhưng `|Δ mean rank-IC|` = 0.00448
là **×3.7** nền seed của CPU, và GPU **tự nó nhiễu gấp 4.8 lần** CPU (0.00586 vs 0.00121).
Nguyên nhân chỉ ra được từ cây đầu tiên: `Cover` lệch **31/31 node** (RNG `subsample`/
`colsample_bytree` khác) + `Split` lệch 11/31 (quantile sketch `hist` khác).
**`nthread` không ảnh hưởng gì:** `n_jobs=1` vs `4` cho tree1 trùng sha, `ΔIC` = 0.0.
**Cổng `spearman >= 0.999` bị bỏ:** đo lại đúng thống kê đó trên 774,270 dòng OOS —
CPU-vs-GPU cùng seed **0.9813**, CPU seed42-vs-seed43 **cùng máy cùng device 0.9817**. Đổi
device tốn đúng bằng đổi seed; ngưỡng 0.999 loại cả việc re-seed chính mô hình, nên nó đo
"có phải cùng một mô hình không" chứ không đo "môi trường có lệch không". Chính cổng này tạo
2 false positive, không phải GPU. Thay bằng: **hiệu ứng phải vượt CI multi-seed (≥3 seed) đo
trong cùng một môi trường**. Giữ nguyên: không ghép số từ 2 môi trường trong một so sánh;
GPU thì CẢ phép so phải trên GPU; parity/byte-identity chạy trên đúng device sinh ra neo;
Java sim ở lại Oracle (data host + neo 60390).
⚠️ Chưa đo: XGBClassifier (G015), Java sim, và GPU không phải T4 (chỉ đo T4 của Kaggle).
Chi tiết `docs/BENCH_DEVICE.md`, script `research/kaggle/bench_device/`,
Kaggle: dataset `chuyendinh/bench-device-pool`, kernel `bench-device-{cpu,gpu,pgpu}`.

---

## W1 — Quét các trục CHƯA TỪNG SWEEP trên nền C2b  [DONE]

**Kết luận lớn nhất KHÔNG phải một tham số tốt hơn — mà là một BUG.**
`SIM_TS_MAX_GAP` (trục A, 3 mức) và `SIM_TS_PNOPUMP_WEAK_THR` (trục C, 2 mức) cho
`printDone.csv` **byte-identical với parity ở cả 5 run**. Nguyên nhân:
`SimulatorMarketLevelTicker1MStopLoss.mergeOrder()` (dòng 730-777) tạo object cụm mới mà
**không chép `symbolPred`**, trong khi `trailRate()` chạy trên chính object cụm đó và có
fallback `pnp = (symbolPred != null) ? symbolPred : 1f`. ⇒ `1f > thres` luôn đúng ⇒
**100% lệnh đi nhánh WEAK, cap = 0.03; nhánh STRONG chưa bao giờ được gọi.**
⚠️ Vậy mô tả exit trong `AGENT_RUNBOOK §3` và `C2B_SPEC` ("cap 0.08 STRONG / 0.03 WEAK,
bản lề `symbolPred < 0.29`") **SAI cho sim**. Cột `symbolPred` trong printDone vẫn có số thật
vì `closeOrder()` ghi từ object LEG — nhìn CSV sẽ tưởng trailing đã dùng nó, nó chưa từng dùng.
`DumpConfig` đổi giá trị cho cả 2 key ⇒ **DumpConfig-đổi KHÔNG đủ để kết luận key sống**.

**Trục D và E không độc lập:** gate chỉ phụ thuộc TỈ SỐ `MIN_MOMENTUM_15M / PREDICT_SYMBOL_RATE_MAX`
(nhánh sàn `AI_DYNAMIC_MIN` không bao giờ chạy vì `symbolPred` min 0.0723). `E010` byte-identical
`D012`, `E012` byte-identical `D010` ⇒ 4 run = 2 điểm thông tin.

Phán quyết: **A, C = key chết** (đóng trục, chờ sửa `mergeOrder` rồi quét LẠI TỪ ĐẦU).
**B (`TS_MAX_GAP_WEAK`) = null** — 0/7 rate pre-reg đơn điệu (chỉ `medP` và `maxDD` đơn điệu,
cả hai đều ngoài danh sách pre-reg; `medP` đơn điệu là hệ quả số học của `exit = peak - min(peak/2, cap)`).
**D+E = đơn điệu mạnh nhưng bị ràng buộc cứng loại** (win% 85.26→85.56→86.90, TSloss% 15.15→15.06→13.29,
mean(profit|SM) 7.48→7.83→7.86 đều đơn điệu; nhưng underwater 93→172→223 ngày, cả 2 mức FAIL).
**F (`DCA_GRID_WEIGHTS`) = có tín hiệu nhưng CONFOUND sizing** — tổng trọng số giữ 1.0 nên leg đầu
tụt còn 0.5/0.4 lần budget, `mean(margin)` 971→593→497; maxDD −13.12→−9.12→−7.62 là thứ bất kỳ lệnh
nhỏ hơn nào cũng tạo ra, mà sizing KHÔNG đo được trên DEV (`RUNBOOK §4`). Mảnh duy nhất không giải
thích được bằng sizing: `mean(profit|STOP_LOSS_DONE)` −18.90→−18.09→−17.37 (đơn điệu, bớt lỗ 1.53pp)
— DCA hạ giá vốn của đúng nhóm time-stop, kênh mất tiền lớn nhất.
**G (`N4_a8s175`) = LOẠI**: underwater 140 > 120 và quý 2022Q4 = −5.3% < −5%. Arm 7%→8% đẩy thêm
4pp lệnh sang time-stop (TSloss 15.15→19.17). Số cũ 61,148/974 lệnh **không tái lập** (chạy lại:
61,592/918) vì khác jar + khác đường cấu hình — không được ghép 2 số này.

**Không đề cử ứng viên baseline mới** (quét khám phá). Hai thẻ mở:
(1) sửa `mergeOrder` chép `symbolPred` rồi quét lại A và C từ đầu — hiện là vùng trắng;
(2) pre-reg riêng cho DCA **tách khỏi sizing** (bù `DCA_GRID_SCALE` để `mean(margin)` không đổi),
chỉ kiểm một giả thuyết: DCA có hạ `|mean(profit|STOP_LOSS_DONE)|` không.
Parity OK (md5 `8f7afdfb27b15f5b6d4c886700def93c`, b:60390, 970 lệnh). 16 run, 1 dataset dùng chung.
Pre-reg `e606b76`, chi tiết `docs/W1_SWEEP.md`, script `research/analysis/w1_rates.py`.

---

## T1 — 3 chan C2b vs "maxfav6" 4h/72h, DI HET TOI SIM  [DONE]

`LABELH` dung o rank-IC va ket luan null; T1 di het luong (train S1 -> build_map -> bins -> sim
-> rate + equity). Pre-reg `26a45ee`, chi tiet `docs/T1_LABEL3.md`.

**Cong REPRO PASS**: `spearman(harness L_g1, pred_s1a2)` = **1.000000** / 774,270 dong.
**Parity PASS hai duong**: Oracle `T1_g1o` **byte-identical** `C2b` (b:60390, 970,
md5 `8f7afdfb…`); Kaggle `t1-g1` = neo 60395/970/`910f1aa6…`.

**Phan quyet**: `L_f4` (`1{maxFav_4h>=0.06}`, dung cau hoi user) **KHAC C2b theo huong XAU HON** —
2/4 rate PRIMARY ngoai CI cung huong o khoi 72h va 24h (`TSloss%` +2.53pp, `win%` -2.47pp;
o 168h chi con 1/4). `L_f4q` (ngu phan vi 4h = ban `LABELH`) va `L_f72` (`1{maxFav_72h>=0.06}`)
**KHONG PHAN BIET DUOC tren rate** (0/4). **Ca ba FAIL rang buoc cung**: maxDD -16.47 / -15.02 /
-15.12, underwater 161 / 187 / 95 ngay, quy min -5.0 / -6.0 / -4.1. => khong chan nao thay C2b.

**Ba thu hoc duoc, quan trong hon ket qua chinh:**
1. 🔴 **Bay #13 — bins KHONG di qua duong Kaggle.** `WFO_FUNDING_PRED_DIR` bi tieu thu o
   `ExportWfoDataset`, kernel Kaggle chi chay sim tren dataset DA BUILD => 3 chan bins khac nhau
   deu ra md5 printDone y het parity, **im lang khong loi**. Da bo 3 run do va chay lai o Oracle.
   `docs/KAGGLE_SIM.md §6`. Bay #14: `/kaggle/input` khong phang.
2. **"Null o rank-IC" KHONG dong nghia "vo hai".** `L_f4q` khong phan biet duoc o CA rank-IC lan
   rate, nhung underwater 93 -> **187 ngay** va maxDD -13.12 -> -15.02. `LABELH` dung o rank-IC
   nen khong the thay dieu do.
3. **rank-IC selector la proxy yeu cho rate**: `L_f4` khong phan biet duoc o moi tieu chi rank-IC
   (CI chua 0) nhung o sim thi khac that.

Cau hoi goc cua `CEIL_RESULT §3` (nhan **168h**) van nguyen — T1 chi kiem 4h va 72h.

---

## T2 — ghep selector C2b vao LUONG DAY DU (big_down + DCA)  [DONE]

Cau hoi user: "ghep c2b vao luong sim hien tai... thay c2b voi selector cu".
Pre-reg `8aa20e3`, chi tiet `docs/T2_FULLFLOW.md`. 4 run, Oracle, 2 dataset build.

**Kham pha (muc 1)** — `big_down` KHONG phai key config: no la `MarketLevelChange.BIG_DOWN`
(`rateDownAvg < MS_DOWN_BIG_AVG = -0.03157`), bat/tat bang **`SELECTOR_ONLY_ENTRY`**
(`Simulator...:271`). Leg BIG_DOWN **BO QUA gate AI** (`Simulator...:817`). DCA tat bang
**`DCA_GRID_WEIGHTS=1,0,0,0`** (cong `gridLegWeightRatio<=0` chan moi leg >= 2). **Hai co doc
lap** — dinh chinh `C2B_SPEC:73` (dong do ghi `SELECTOR_ONLY_ENTRY` tat ca BIG_DOWN lan DCA_LEVEL1).
"Luong day du" duoc **dinh nghia lai** = `c2b_min` tru 2 cong nghien cuu (delta 2 key), KHONG
dung `D0_full`/`G1_giveback5` lich su (khac jar, dataset da xoa — bay da dinh o `N4_a8s175`).
"Selector cu" = **`predwf_G015_v2`** (ban `G015x26` goc ~~KHONG tai lap duoc~~ — **SAI, da go**
2026-09-06: x26 tai lap duoc, va v2 la model KHAC NHAN chu khong phai ban tai lap cua x26,
`docs/G3_X26_RECOVERY.md`), kem hieu chuan gate
`SIM_MIN_MOMENTUM_15M=0.014052` cua `c3.properties`.

**Parity PASS**: `T2_c2b_ref` byte-identical `C2b` (b:60390, 970, md5 `8f7afdfb…`).

**Phan quyet cau hoi user (`T2_full_c2b` vs `T2_full_old`): KHONG PHAN BIET DUOC** — 1/6 rate
PRIMARY ngoai CI (`mean(profit)` +2.05, CI [+0.06,+4.01]); can >= 2. `TSloss%` -4.46 va `win%`
+4.57 nghieng ve C2b nhung cham bien CI.

**Nhung phep so do duoc thuc hien o diem van hanh gan nhu vo hieu:** luoi DCA thiet ke `1,1,3,8`
lam leg dau chi con `1/13` suat budget ma `DCA_GRID_SCALE` van 1.5 (khong bu) =>
**`mean(margin)` 971 -> 9.21 (105 lan nho hon)**, `total margin deployed` 941,920 -> 9,908,
**CAGR 24.48% -> 0.36%** (`full_old` 0.32%). maxDD -0.1% cua chung **khong phai an toan** —
la khong co gi de mat. `T2_full_old` van **FAIL** rang buoc cung (underwater **147** > 120).

**Ket qua sach nhat cua batch — `T2_full_c2b_noDCA` (big_down BAT, DCA TAT):**
**0/6 rate ngoai CI** so voi `c2b_min`. 120 leg BIG_DOWN (11.7% so lenh, y het 120 o ca 3 chan
vi tin hieu market-level khong phu thuoc selector), maxDD -12.9 vs -13.1, underwater 93 = 93,
equity 61,287 vs 60,390 (trong mien nhieu 4.28pp cua N=4). => **bat big_down mot minh vo hai
va gan nhu vo ich** — dang chu y vi no bo qua gate.

Status moi duy nhat cua luong day du: **`REQUEST` 1/2709** o `T2_full_old` (lenh chua dong toi
`SIM_END_DATE`). Khong co status exit moi nao khac.

**Khong de cu ung vien baseline moi.** The mo: chay lai luong day du voi `DCA_GRID_SCALE` **duoc
bu** (~19.5 cho luoi 1,1,3,8) de giu `mean(margin)` ~971, kiem `CapacityProbe` truoc — dung the
ma `W1_SWEEP muc 10` da mo.

---

## T2b — luong DAY DU voi SIZE DUOC BU: C2b vs selector cu  [DONE]

Chua T2 de lai: `DCA_GRID_WEIGHTS=1,1,3,8` khong bu `DCA_GRID_SCALE` => `mean(margin)`
971 -> 9.21, ca hai chan chay o ~1% von nen phep so selector vo nghia.
Pre-reg `0058c35`, chi tiet `docs/T2B_FULLFLOW.md`. 3 sim run (parity tai dung `T2_c2b_ref`).

**🔴 BUG SIZING — tong trong so DCA bi chia HAI LAN.** `TradeUtils.managerBudget` da chia
`/dcaGridTotalWeight()` (comment: "chua cho du ladder DCA"), roi `DcaUtils.gridLegWeightRatio`
chia tiep `w[i]/total` => `margin(leg i) = 35000 x F_BASE x throttle x SCALE x w[i] / total^2`.
Voi `1,1,3,8` thi **`total^2` = 169, khong phai 13**. He so do duoc 106.19 = 169 / 1.59 (1.59 =
`throttle` noi lai tu 0.6165 -> 0.9812 vi gan nhu khong dung von) — **khop tuyet doi**.
`balanceBasic` la HANG SO 35000 => size khong compound. `getBudget()`/`BASE_BUDGET=700` la
**tham so chet** (`managerBudget` khong doc no).
=> **Dinh chinh `W1_SWEEP muc 10` va `T2_FULLFLOW muc 5`: scale bu dung la 253.5 (=1.5 x 169),
KHONG phai 19.5.**

**Hieu chuan PASS lan dau, khong dung quyen sua 1-lan**: `SCALE=253.5` cho `mean(margin)`
leg 1 = **947.00** vs muc tieu 971.05 (**-2.5%**, cong ±20%). Ap y het cho ca 3 chan.

**Parity PASS**: `T2_c2b_ref` byte-identical `C2b` (b:60390, 970, md5 `8f7afdfb…`); jar sha256
khong doi, `find src -newer <jar>` rong.

**PHAN QUYET CAU CHINH (`T2b_full_c2b` vs `T2b_full_old`): KHAC — selector C2b THANG.**
Hai duong doc lap: (1) **2/6 rate PRIMARY ngoai CI cung huong** (`mean(profit)` 3.79 vs 1.45,
+2.34 CI[+0.30,+4.39]; `mean(margin)` +192 CI[+57,+320]) — vuot nguong `>=2`; (2) `T2b_full_old`
**FAIL 4/4 rang buoc cung** (maxDD **-41.6%** @2022-11-10, UW **390 ngay**, nam 2022 **-29.7%**,
quy 2022Q2 **-27.3%**) => loai truc tiep. `T2b_full_c2b` PASS het (maxDD -11.5, UW 81, quy min
-1.4, n=1068). Equity 64,809 (CAGR 28.05%, Sharpe(q) 1.28) vs 42,687 (8.30%, 0.15) — **khong
phai tieu chi**, chan tren nam trong nhieu 4.28pp so voi ref.

**Bien so DUY NHAT doi so voi T2 la size.** T2 = 1/6 ngoai CI ("khong phan biet duoc"), T2b =
2/6 + FAIL 4/4. => **mot phep so o diem van hanh sai co the tra null ma khong phai vi hai vat
giong nhau.** Canh bao khi trich: `mean(margin)` la bien KIEM SOAT (lech vi `full_old` mo 2.5x
so lenh => `throttle` thap hon), nen bang chung CHAT LUONG chi la `mean(profit)`; "selector cu"
la **goi bins `G015_v2` + gate 0.014052** (2 bien, ghi truoc); va **uu the cua C2b van la hien
tuong 2022** — bo 2022 ra thi ban cu con cao hon (65.5+4.8 vs 41.5+6.8), dung hinh dang ma
`SELECTOR_LADDER_Q` da canh bao.

**PHAN QUYET CAU PHU (DCA co dang bat khong): KHONG DANG** — `T2b_dca_c2b` vs ref **0/6 rate
ngoai CI** (dieu kien `sum(pnl)` leg 2+ duong thi DAT: +3,177). Bat ca hai co che
(`T2b_full_c2b`) cung 0/6 vs ref. Ghep voi `T2_full_c2b_noDCA` (big_down mot minh, 0/6):
**khong co che nao trong luong day du phan biet duoc voi `c2b_min` tren rate.**

**PnL tach theo leg — dau DAO CHIEU theo selector** (tai lap leg index bang gom `(sym,end)`,
khop 100% so dong `DCA_LEVEL1`): leg 2+ lai **+3,398 USD / 21 leg** (`full_c2b`, mean profit%
**+17.9**) nhung **-4,239 USD / 45 leg** (`full_old`, **-3.3**). DCA chi no trong quy sap
(2022Q2 + 2022Q4 + 2024Q2, **0 leg suot 2023**) va cham rat it (1.7-2.0% so leg) vi luoi
`-50/-75/-90%`. Bu size KHONG lam DCA cham nhieu hon (21 leg o T2 = 21 leg o T2b).
`BIG_DOWN` = **dung 120 leg** o moi chan bat no (tin hieu market-level, khong phu thuoc selector).

**Khong de cu ung vien baseline moi.** The mo: `mean(profit|STOP_LOSS_DONE)` -18.90 -> -16.37
va maxDD -13.1 -> -11.6 / UW 93 -> 81 cua chan DCA **o cung muc size** (lech 1.1%) — lan dau
hieu ung nay khong giai thich duoc bang sizing, nhung van trong CI. Muon dong the nay phai
pre-reg rieng va co nhieu hon 21 leg.


---

## BUGS phat hien 2026-09-05 - B1/B2/B3  [DONE `5a001e5` -> baseline moi C3, `docs/C3_BASELINE.md`]

B1. `mergeOrder()` (`SimulatorMarketLevelTicker1MStopLoss.java:730-777`) KHONG chep `symbolPred`
    => `trailRate()` fallback `pnp=1f` => 100% lenh nhanh WEAK (cap 0.03). Nhanh STRONG (cap 0.08)
    CHUA BAO GIO chay. `SIM_TS_MAX_GAP` + `SIM_TS_PNOPUMP_WEAK_THR` la key chet. (W1 bd20e42)
B2. Sizing chia tong trong so DCA HAI LAN: `TradeUtils.managerBudget:62` /total va
    `DcaUtils.gridLegWeightRatio:53` /total nua => margin ~ w[i]/total^2. Voi weights 1,0,0,0
    total=1 nen vo hinh; bat DCA la sap size 169x. (T2b 16836eb)
B3. `balanceBasic` = hang so 35000 => size KHONG compound theo equity. `getBudget()`/
    `BASE_BUDGET=700` la tham so chet. Fitness hien tai khong phan anh he compound. (T2b)
Sua B1 hoac B3 se doi C2b (khong con byte-identical 60390) => phai pre-reg nhu baseline moi
va do lai toan bo. Khong tu quyet.

## T2b [DONE 16836eb] — ket qua dang chu y nhat hom nay
`full_c2b` (big_down + DCA bu size, selector C2b): 64,809 / CAGR 28.05% / maxDD -11.5 / UW 81d
vs `c2b_min` 60,390 / 24.48% / -13.1 / 93d. Trong nhieu N=4 (4.3pp) nhung PASS het rang buoc cung.
Selector C2b THANG selector cu trong luong day du (2/6 rate ngoai CI; cu FAIL 4/4 rang buoc).
DCA va big_down TU THAN khong phan biet duoc voi c2b_min (0/6 rate). Khong de cu baseline moi.


---

## C3 - Sua 3 bug B1/B2/B3, do lai baseline  [DONE `5a001e5`]

**Cong hoi quy PASS byte-identical**: `C3_regress` (jar moi + 3 co `false`) = 60395 / 970 /
md5 `910f1aa6f76b5e6797d97a31a7ea5f5a` = neo Kaggle. 5 arm chay song song (5/5 slot Kaggle -
lan dau do duoc tran 5 that su). Pre-reg `docs/PREREG_C3.md`, chi tiet `docs/C3_BASELINE.md`,
script `research/analysis/c3_rates.py`.

**BASELINE MOI `C3`** = `profiles/c3_min.properties` = **68,278 / CAGR 30.76% / maxDD -13.31% /
UW 96d / n=961**, md5 printDone `38be0cb3195984e1000e61d9cdef54da`. **PASS 4/4 rang buoc cung**
nhung **sat bien o quy: -4.8% vs tran -5.0%** (bien 0.2pp; C2b cu -3.7%) - compound da an gan
het bien do. `C2b` = 60,390 tu day chi con la SO LICH SU.

**Phan tach hieu ung (day moi la ket qua chinh):**
- **B1 mot minh: 0/7 rate ngoai CI, va equity GIAM** 60,395 -> 59,722. KHONG phan biet duoc.
  Nhung **doi HINH DANG phan bo winner**: p10 4.46->3.50, p25 4.99->4.00, med 6.00->5.00,
  **p90 11.00->12.06**. So hoc: `exit = peak - min(peak*0.5, cap)`, voi `peak` trong 6%..16%
  thi STRONG chot THAP hon WEAK dung 5pp. **Danh doi median-doi-duoi, khong phai cai tien.**
  => "null tren rate" KHONG dong nghia "khong doi gi" (cung mach `T1` bai hoc 2).
- **B3 mot minh: hieu = 0.000 TUYET DOI o MOI rate muc lenh**, chi `mean(margin)` doi
  (+424, CI [+287,+562]). `mean(margin)` theo nam 892 -> 1,609 -> 1,785 (chan khong compound:
  892 -> 1,120 -> **924**, quay dau). => compound di qua DUNG MOT kenh, khong ro ri sang
  quyet dinh vao/ra. Ly do: `throttle = 1 - marginRunning/(equity*U_MAX)`, tu va mau cung
  nhan theo equity => throttle bat bien.
- **B2 vo hinh o `1,0,0,0`** (total=1) - dung nhu du doan; chi hien o `C3_FULL`.

**Toan bo phan tang equity la B3, KHONG phai B1.** Ai doc luot va quy cong cho B1 la doc nguoc.

**`DCA_GRID_SCALE` bu dung sau B2 = 19.5** (`1.5 x 13`), KHONG phai 253.5 (`1.5 x 169` - so do
bu cho chinh cai bug). Hieu chuan `C3_FULL` PASS lan dau: leg-1 `mean(margin)` 1,428.01 vs
muc tieu 1,397.41 (**+2.19%**, cong +-20%). => `W1_SWEEP muc 10` (19.5) hoa ra DUNG cho engine
moi; `T2B_FULLFLOW muc 1.4` (253.5) dung cho engine CU. Ca hai deu khong sai.

**The mo manh nhat: `C3_FULL`** (big_down + DCA, size da bu) = 72,699 / maxDD -12.46 / **UW 81**
(tot nhat 5 chan) / PASS 4/4, va **`mean(profit|SL)` -16.24 vs -18.83 (+2.59pp, CI [+0.035,
+5.841] - LAN DAU vuot CI o cung muc size)**. KHONG de cu baseline (pre-reg cam). Pre-reg tiep
theo phai tach **DCA** khoi **120 leg BIG_DOWN**; CI cham 0 nen bang chung con yeu.

⚠️ **No ky thuat moi:** moi ket luan cua E1/W1/T1/T2/T2b sinh tu engine co 3 bug. Phan lien quan
**trailing** (E1, W1 A/B/C, T2b DCA) can do lai tren engine moi.
---

## X1 — keo dai cua so do 30 -> 48 thang (2026-09-05) — **XONG**

Pre-reg `docs/PREREG_X1.md` (`91d7b93`) · ket qua `docs/X1_EXTEND.md`.

- **DEV moi = 2022-01-01 -> 2025-12-31.** Khong con VAL sach. Holdout duy nhat = 2026.
- **Chan B (2021H2) BO** — cat 2 OI feature khoi S1 KEEP se pha cong parity voi `C3`.
- **4/4 cong byte-identical PASS** (featv2 / ledger / pred_s1a2 / bins) + **parity noi bo
  IDENTICAL** ca hai arm (961 va 1,059 dong).
- **PHAN QUYET: GIU `C3`.** `C3_FULL` truot tieu chi 1 (1/5 rate ngoai CI) va 3 (UW).
  Nhung **gia thuyet "DCA an FTX mot lan" DA BI BAC BO** (DCA duong o 2022 va 2025).
- `n_eff` muc lenh: 89 -> **167** khoi 72h (x1.88, CI hep ~x1.37). Van khong du de doi ket luan.

### Mo ra tu X1 — chua lam

1. 🔴 **Nguong `UW <= 120` phai duoc user quyet lai** — ca `C3` lan `C3_FULL` deu FAIL o
   2024 (121) va 2025 (302 / 227) tren cua so 48 thang. **Khong duoc tu ha nguong.**
2. 🟢 `predwf_G015x26` (~~khong tai lap duoc~~ — **da go 2026-09-06**) nay da lan sang ca 6 fold moi. Muon go phai do
   lai toan bo baseline voi `predwf_G015_v2` mo rong — job rieng, `C3` se doi so.
3. ⚠️ Do sau lenh thua 2025 (`mean(profit|SL)` -28.94) la kenh mat tien lon nhat cua cua so
   moi. Truc `SIM_TS_MAX_GAP` / `SIM_TS_PNOPUMP_WEAK_THR` (vung trang cua `W1`) lien quan
   truc tiep — **nhung dong vao chung SAU KHI da thay bang X1 la tune-after-the-fact**;
   phai pre-reg rieng, khong duoc coi la tiep tuc X1.
4. ⚠️ `wfo_gate_pred.csv` het o 2025-12-31 23:59. Do 2026 = dot holdout cuoi cung.
5. ⚠️ `research/pipeline/ledger.py` (ban goc) van co glob `funding_label_202[1-4]*.pb` —
   chay no voi `T1` sau 2025 se **lang le thieu 2025**. Ban `x1/x1_ledger.py` da sua.

---

## H1 — dung INPUT cho holdout 2026 (2026-09-06) — **PREP DONE, cho user mo seal**

Pre-reg `docs/PREREG_H1.md` · bao cao `docs/H1_HOLDOUT_PREP.md`. **Khong mo seal, khong chay
sim nao qua 2025-12-31, khong doc outcome 2026 nao.**

- **Cua so kha dung = 2026-01-01 -> 2026-07-01 GMT+7 = 6 THANG, 2 fold** (`20260101`,
  `20260401`). Chan cung la feature store gate + Tool1 + OI (deu het 2026-07-01), **khong
  phai ticker** (ticker co toi 2026-08-13 nhung vo dung).
- ✅ **`p15` 2026 DA DUNG XONG**: `claudedata/wfo_gate_pred_2026_H1.csv`, 260,183 dong,
  sha256 `4cc62c14f95f...` — khop doan bi cat ghi trong seal manifest (260,182 + 1 dong bien).
  Sinh tu `fold_19`/`fold_20` ONNX da co, **khong train lai, khong replay Aerospike**.
- ✅ **Cong P1 PASS**: tai tao `p15` cua 2024Q2 va 2025Q4 tu feature store + ONNX ra
  **spearman = 1.000000** ca hai fold. **Byte-identity KHONG dat** (92.75% / 97.82% chuoi
  `%.8f` trung) — phan du la lam tron chu so thu 8 cua float32 (`p50 |d| = 2.5e-09`), chi
  21-46 phut/quy lech that.
- 🔴 **`p15` la OUTPUT cua model gate, khong phai tinh tu gia.** Va **2026 khong con la holdout
  sach o tang gate**: model gate duoc ghi 2026-08-06, ke hoach fold chay 2026-08-19 voi
  `end=20260701` — chot trong luc 2026 dang nhin thay; seal chi dat 2026-09-01. Khong go lai duoc.
- 🔴 **BLOCKER 1: `CLOSES_1H.bin` khong co generator** — grep toan van toan bo dia + git log
  `-S`: moi file khop deu la READER. Va neo da do (`PREREG_FS` muc 0) noi nguon la **kline 1h
  Vision**, KHONG phai ticker 1m. => `featv2`/`cand_dev`/bins deu chan tai day.
- 🔴 **BLOCKER 2: bins fold 2026 lay P(win) tu dau?** fold `20260101`/`20260401` cua
  `predwf_G015x26` da bi seal xoa, va bo do ~~**khong tai lap duoc**~~ (**da go 2026-09-06** —
  `docs/G3_X26_RECOVERY.md`, tai sinh bang `research/pipeline/g015x26_train.py`). Train moi bang
  `g72_train.py` = ho `G015_v2`, hieu chuan khac — ma ban le trailing `0.29` la nguong
  **tuyet doi** tren chinh P(win) do. Phai do hieu chuan tai cutoff `20251001` (chi DEV) truoc.
- ⛔ Cong P2/P3/P4/P5 **chua chay** (chan boi hai blocker). Parity dataset `SIM_END_DATE=20251231`
  chua chay.
- Lenh mo seal chinh xac + chuoi 2 arm: `docs/H1_HOLDOUT_PREP.md` muc 7.

### Cho user quyet — H1 khong chay duoc neu chua co

1. `CLOSES_1H` dung lai theo duong nao (Vision 1h kline = giu neo, hay Aerospike 1m = mat neo).
2. Chap nhan bins tron nguon (16 fold G015x26 + 2 fold G015_v2) hay khong.
3. Mo seal hay khong — mot lan, khong hoan tac.

---

## Q7 — Shadow C3 chay forward tren Oracle  [BLOCKED: 4 chan ky thuat, can user quyet]

Khao sat day du: `docs/L1_SHADOW_C3.md`. Pre-reg run doi chung da chay: `docs/PREREG_L1.md`.
**KHONG duoc bat shadow roi goi la C3** cho toi khi bon chan duoi day mo het.

| chan | viec de mo | pre-reg rieng? |
|---|---|---|
| Model S1 khong co file | train lai tai cutoff `20251001` + `save_model` + manifest sha256 | khong (tai lap artifact) |
| Khong co bo tinh 9 feature S1 real-time | do nguon gia truoc (`CLOSES_1H` = kline 1h, KHONG phai ticker 1m gop), roi viet sidecar | **CO** |
| Duong live khong doc `WFO_FUNDING_PRED_DIR` | cam score S1 vao `selectorRankPool` | **CO** |
| `BUDGET_PER_ORDER = 0` khi khong co API key (`PrivateConfig` la STUB tren Oracle) | key read-only, **hoac** co `PAPER_EQUITY` mac dinh TAT + cong hoi quy `X1_C3` byte-identical | **CO** |

Hai khac biet CO CHE phai ghi vao moi bao cao, khong go duoc bang cau hinh:
- live co dead-zone ratchet `5.21847 x arm` (= 26.1% khi arm 5%), sim da go;
- live **khong co** time-stop 168h (code chi o `Simulator...:672`).

Cai gia phai chap nhan truoc khi bat: moi tuan shadow chay tieu mot tuan holdout 2026.

### Q7 cap nhat 2026-09-06 — **4 chan DA MO**, shadow DANG CHAY (`docs/L2_PORT_C3.md`)

| chan (L1) | trang thai | bang chung |
|---|---|---|
| Model S1 khong co file | ✅ MO | `x1_s1_save_model.py` -> `/home/ubuntu/s1_model/s1a2x1_cut20251001.{json,onnx}` + manifest sha256. Cong: JSON spearman **1.000000**, max\|d\| **0** tren 3,499,202 dong OOS 2025Q4 |
| Khong co bo tinh 9 feature S1 real-time | ✅ MO cho **7 feature GIA** | `S1FeatureLive` + `S1FeatParityProbe`: 2025-12, 421,344 cap, spearman **1.000000** cho 5 feature tho, **>= 0.9997** cho 2 feature rank. ⚠️ 2 feature OI **CHUA DO** (`oi_feat_*` tren 242 chi giu 2 thang) |
| Duong live khong doc `WFO_FUNDING_PRED_DIR` | ✅ MO (khac cach) | `S1RankerLive` chay ONNX **thang** trong tick, thay THU TU `selectorRankPool`. Khong di qua bins. Cong top-8: **6800/6800 tick trung tuyet doi** |
| `BUDGET_PER_ORDER = 0` (key STUB) | ✅ MO | co `PAPER_EQUITY` + `ShadowBookC3.equityNow()`, bo hoan toan `getAccountUMInfo()` khi profile bat. Cong hoi quy: 81/81 test PASS, co TAT = HEAD |

Con lai (**KHONG mo duoc trong dot nay**):
1. 🔴 `symbolPred` van la `Funding_Classifier_Final.onnx`, khong phai `predwf_G015x26` — **lech hieu
   chuan**, phai tach STRONG/WEAK khi ghep cap. (L1 muc 4: truc nay 0/5 rate ngoai CI.)
2. 🔴 Model S1 train toi 2025-09-28, chay forward 2026-09 = **ngoai mep train 11 thang**.
3. 🔴 Cong ONNX truot |delta| tuyet doi (2.62e-06 > 1e-6) — nhung **thu hang trung 100%**.
4. ⚠️ 2 feature OI chua co cua so nao do khop duoc ma khong cham 242 hoac khong mo seal.
5. ⚠️ Time-stop 168h tren duong dat lenh THAT moi chi la **mot dong log**, chua noi vao lenh dong.

### Cho user quyet — Q7
1. Deploy jar moi len 242 hay khong (co mac dinh TAT nen hanh vi bot that khong doi) — can runbook + pre-reg rieng.
2. Do 2 feature OI: backfill `oi_feat_*` tren 242 (GHI len live) **hay** mo seal 2026-08 de do gian tiep.
3. Chap nhan gia holdout: moi tuan shadow chay tieu mot tuan 2026.

---

## Q8 — L3: cô lập LEGACY + gói deploy 242  [DEPLOYED 07/09/2026 06:29:57 / xac minh 08/09/2026 `docs/L3_DEPLOY_VERIFY_20260908.md`]

User quyết: một JVM trên 242 chạy `LIVE_PROFILE=c3_shadow` — 66 vị thế thật cũ (**LEGACY**) đóng
THẬT theo luật HEAD, sổ giấy C3 chạy song song, không lệnh thật mới.

Đã xong trên Oracle (agent **không** SSH 242):
- `LegacySymbols` + tách cờ C3 theo symbol (arm / dead-zone / time-stop) + `[SHADOW] skip-LEGACY`
  + legacy không chiếm slot top-K + nhánh giấy bỏ Redis queue của bot + không dùng chung
  `BUDGET_PER_ORDER`/`balanceBasic`. `mvn -o test` **97/97 PASS**, `check_cfg_gateway.sh` OK.
- Gói `/home/ubuntu/deploy_242_l3/` (`sim.jar` sha256 `c8cec398...`, `s1_c3/`, `env.sh.new`,
  `deploy.sh`/`verify.sh`/`rollback.sh`/`README_DEPLOY.md`).
- `tools/pull_242_shadow.sh` (Oracle) — cron **chưa bật**, đợi deploy.

**Chờ user:**
1. Chạy 3 lệnh deploy (README_DEPLOY.md mục 1) rồi báo lại.
2. Quyết có bật `DCA_GRID_WEIGHTS=1,0,0,0` + `TIER_FLAT=1` không — không bật thì sizing sổ giấy
   242 lệch ~13 lần so với C3/shadow Oracle (2 key này chỉ vào đường sizing ENTRY, không thể chạm
   đường đóng legacy).
3. Một lệnh CHỈ ĐỌC: `grep -i TS_GIVEBACK config.properties conf/env.sh` trên 242 —
   `TS_GIVEBACK_RATIO` là trục **dùng chung** giữa hai đường, không tách được bằng env.

Sau khi 242 verify PASS: bật cron `pull_242_shadow.sh`, và (tuỳ user) tắt shadow Oracle
`cd /home/ubuntu/shadow_c3/app && bin/daemon.sh stop` + xoá cron health.

**Cap nhat 08/09/2026**: da xac minh 242 dang chay dung rev6/c3_shadow (deploy tu 07/09 06:29:57, ~37h sach, 0 exception, LEGACY on dinh N=65, RSS/RAM/[MAP] p50 deu trong nguong). Chi tiet: `docs/L3_DEPLOY_VERIFY_20260908.md`. Con mo: quyet dinh co tat shadow Oracle hay khong (chua kiem tra no con chay khong).

## G3 — Khoi phuc `predwf_G015x26` (2026-09-06) — **XONG, TAI LAP DUOC**

Bao cao: `docs/G3_X26_RECOVERY.md`. Script: `research/pipeline/g015x26_train.py`.

**Ket qua:** 16/16 fold `spearman = 1.00000000`, `max|d| = 1.192e-07` (1 ULP float32), so record
khop tuyet doi manifest. Cong `>= 0.999` DAT voi bien rat rong.

**Hai tuyen bo cu bi bac bo bang bang chung truc tiep:**
1. "Ban export Tool1 2021 da mat" — SAI. `sha256(features_20210101_to_20210401.t1c)` giong het nhau
   o Kaggle **v1**, Kaggle **v5**, va ban tren dia (`eca5b024...638c5c`). mtime 2026-08-16 chi la
   lan tai ve lai sau khi dataset v4 bo 4 file 2021 va v5 them lai.
2. "Khong con source de dung lai" — SAI o phan quan trong. **18 model da train** cua chinh lan chay
   08-14 con nguyen o `/home/ubuntu/claudedata/predwf_G015/` kem **log day du**. Tai sinh bins =
   predict lai, khong can train.

**Nguyen nhan that su lam lan rebuild truoc "khong khop":** dung **SAI NHAN**. x26 =
`retEnd_4h > 0.015` (base 0.1849); ban rebuild `G015_v2` = `maxFav_4h >= 0.06` (base 0.0457).
=> `predwf_G015_v2` **khong phai** ban tai lap cua x26 ma la mot model khac; `rho` 0.16752 vs
0.18991 la hai model khac nhan, khong so truc tiep duoc.

**Con thieu (khong chan gi):** source code cua TRAINER ban 08-14 (`gen_funding_wf_predictions_1m.py`
nhanh `LABEL_MODE=net`) — bi ghi de tren dia 2026-08-16 va Kaggle dataset `sel1m-code` da bi tao lai;
API `kernels/pull?version_number=` tra 400. Muon TRAIN LAI tu dau (vd doi feature) thi phai viet lai
phan nhan (3 dong, cot `retEnd_4h` co san trong `label_15m/*.pb`). Muon SINH LAI bins thi khong can.

**Viec co the mo tiep (chua lam, can pre-reg):**
- Sinh fold 2021 cho x26 (`FIRST_CUTOFF` cu = 20220101 nen chua co) => go blocker "mo DEV ve 2021"
  o muc Q4 — nhung phai train model moi cho 2021, khong phai predict, nen KHONG con la x26.
- Doi chieu lai moi ket luan tung dua tren "x26 khong tai lap duoc" (F4_TIMING §9, L1_SHADOW_C3 (c),
  T2_FULLFLOW, AUDIT_APPLIED uu tien 1).

---

## SHADOW-HEALTH — kiem tra shadow C3 tren 242  [READY — LAP LAI MOI NGAY, READ-ONLY, khong bao gio DONE]
Scheduled task chay job nay MOI LAN fire (khong lay job khac neu job nay READY). Chi doc 242, khong sua gi.
Lenh (Git ssh tu Windows, viet .sh -> scp -> bash; KHONG nhung &,>,<,| trong ssh inline):
  A=/home/chuyennd/java/v_t_m
  pgrep -fc 'BinanceOrderTradingManager'                      # phai = 1
  cat $A/run/*.pid; ps -o pid,rss,etime -C java               # pidfile = pid trading; RSS < 5G
  tail -n 20000 $A/logs/full.log | grep -a 'Update all position:' | tail -1      # N (66 giam dan khi legacy dong)
  tail -n 20000 $A/logs/full.log | grep -a '\[LEGACY\] managed' | tail -1 | cut -c1-60
  tail -n 200000 $A/logs/full.log | grep -a '\[MAP\]' | grep -aoE 'p50=[0-9.]+' | tail -96   # 1 ngay = 96 tick; p50 phai trong [0.20,0.70]
  tail -n 200000 $A/logs/full.log | grep -ac 'would-BUY'   # THEO DOI, KHONG phai canh bao = 0 (tu 07/09 day la log hop le cua so giay C3 song song that; xem docs/L3_DEPLOY_VERIFY_20260908.md muc 5.2)
  grep -ac 'skip tick' ...   # phai = 0
  grep -acE 'API-key format invalid|OutOfMemory' ...   # phai = 0 (bo 'Create order market' khoi nguong nay -- tu 21/08 day la log dat lenh THAT hop le cua LEGACY, khong con dung de bao loi duoc)
  wc -l /home/chuyennd/java/shadow_c3/ledger.csv; tail -3 /home/chuyennd/java/shadow_c3/ledger.csv
  free -m | head -2
Ghi 1 dong/ngay vao docs/SHADOW_LOG.md: ngay | pid | n_jvm | N_legacy | p50_min/med/max | would-BUY | skip | loi | ledger_rows | RSS | ghi chu.
  **MTM (them 11/09/2026):** chay `tools/shadow_mtm_242.sh` TREN 242 (pipe qua ssh stdin) va dan dong tom tat + 3 lenh te nhat
  vao cung dong SHADOW_LOG. Ly do: ledger chi co lenh DA DONG (100%% TRAILING_STOP) — realized la survivorship; phai doc
  realized+unrealized (docs/SHADOW_EVAL_20260911.md, DEV_COLLAPSE_CHECK_20260911.md). CANH BAO them: net%% <= -8%% (= muc collapse-day
  te nhat DEV 2025-11-12) hoac open >= 30 (= max DEV) -> bao user, KHONG tu sua gi.
CANH BAO ngay (bao user) neu: n_jvm != 1; 'API-key format invalid' > 0; p50 ngoai [0.20,0.70] >= 4 tick lien tiep; RSS >= 5G; OOM; khong co [MAP] trong 2 gio. (Da bo 'Create order market' khoi dieu kien canh bao 08/09/2026 -- xem Q8.)
KHONG restart, KHONG sua env, KHONG rollback tu dong — chi bao.
