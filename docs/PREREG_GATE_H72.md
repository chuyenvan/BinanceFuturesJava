# PREREG_GATE_H72 — Huong B: doi HORIZON cua gate tu 4h sang 72h

Pre-registration, viet TRUOC khi chay bat ky train/sim nao cua vong nay.
Repo `BinanceFuturesJava`, branch `module`, nen `2e3bef8` (DESIGN_GATE_TARGET_ALIGNMENT).
Baseline/parity: **T170** = `devrun/X1_GS_T170_2021`, profile `profiles/x1_gs_t170.properties`,
`printDone.csv` md5 **`efb793e2468ca3a7318da0f0ad23d4fc`** (1090 dong / 1089 lenh, `b:111070`).
Nguong cham: `docs/RISK_APPETITE.md` (maxDD <= 30%/nam, UW <= 200, khong nam am, quy >= -15%,
1 coin <= 15% equity) + bang chung >= 2 rate ngoai CI (bootstrap khoi-72h, 2000 rep).
**KHONG push. Khong cham 2026. Chi DEV.**

---

## 1. Cau hoi & gia thuyet (Hướng B cua `DESIGN_GATE_TARGET_ALIGNMENT` muc 5/B)

Gate G015 hien tai hoc `y = (retEnd_4h > 0.015)`; selector S1 hoc `rel5` = ngu phan vi
cross-sectional cua `g1lite` (**horizon 72h**). Gia thuyet:

> **H_B**: Neu gate duoc train cung horizon 72h voi selector, tin hieu gate "nhat quan" hon
> => gate phan biet duoc "tick tot cho 72h" thay vi "tick tot cho 4h" => he thong tot hon.

Thay doi DUY NHAT so voi recipe G015: **cot nhan** `retEnd_4h` -> `retEnd_72h` (giu nguyen
`thr=0.015`, 45 feature, hyperparam, fold, purge, device-class).

## 2. Nhan chinh xac (dinh nghia dong bang)

```
y = (retEnd_72h > 0.015)        # KHONG dung g1lite, KHONG dung maxFav
loc: nBars_72h >= 288           # 288 buoc x 15m = 72h
nguon: /home/ubuntu/label_15m/funding_label_*.pb, cot `retEnd_72h`
```

- Base rate ky vong: **0.3932** (do duoc, `g5_summary_net015_72h.json`), vs `net015_4h` = 0.1849.
- Purge 288 buoc = 72h = DUNG bang horizon nhan => bien an 0 buoc (train `ts <= cutoff-72h`
  => nhan train ket thuc <= cutoff). Hop le nhung KHONG con bien; ghi ro de khong doc nham.

## 3. Thiet ke neu chay (dong bang)

1. Train: `research/pipeline/g5/g5_pool_train.py --label-h 72 --label-mode net --thr 0.015
   --out-bins` (± `--pool /home/ubuntu/ledger/cand_dev_x1.parquet`), 16 fold `CUT16`
   (`20220101..20251001`), 45 feature, `XGBClassifier` nguyen recipe, seed 42, nest 400.
   Device: Kaggle GPU (= device goc cua x26) hoac Oracle CPU — ghi ro, khong tron 2 moi truong.
2. Bins: `predict_wf_<cut>.bin` 16 file (26B/rec, `p0 = P(retEnd_72h > 1.5%)`).
3. Map (giu dung duong dang chay): `c4_build_map.py s1a2 <out_dir>` voi
   `G015_BINS_DIR=<bins 72h>`, `X1_CUTS=<16 cut>`; score = `ledger/pred_s1a2.parquet`.
   => thu tu trong tick do S1 quyet dinh, GIA TRI `p` lay tu gate 72h.
4. Sim: `profiles/x1_gs_t170.properties` (gate scale 1.70), `configs/sim_dev_file_2021.properties`,
   `WFO_DATA_DIR=wfo_ds_x1_2021`, `TIME_RUN=20210701`, `SIM_END_DATE=20251231`,
   `TICKER_SOURCE=file`. Build dataset RIENG tu bins 72h roi chay 1 arm.
5. Cong truoc khi doc so: (a) chay lai T170 voi bins CU => md5 `efb793e2`;
   (b) `pass_raw` cua gate 72h phai tai lap duoc con so proxy `83,193` (x0.80 parity).

## 4. Cach cham + tieu chi quyet dinh (chot TRUOC)

- 5 rate: `n`, `win%`, `TSloss%`, `mean(P|SM)`, `mean(P|SL)`, `mean(margin)`; CI khoi-72h
  (x1.21, 2000 rep) ghep cap vs T170; bao cao 5 nam + tung nam.
- Rang buoc cung theo `RISK_APPETITE` muc 1 (nguong MOI) + tap trung 1 coin <= 15% equity.
- **QUYET DINH**: `H72` duoc goi la **TOT HON** chi khi co **>= 2 rate CHAT LUONG cung huong
  TOT, NGOAI CI** VA PASS rang buoc cung; la **XAU HON** khi >= 2 rate chat luong ngoai CI
  cung huong XAU hoac FAIL rang buoc cung; con lai = **NULL**.
- Multiplicity: **toi da k=2 bien the** (72h `net015` + tuy chon 72h `net020`). Khong them
  bien the sau khi thay so.

## 5. SU THAT KIEM TRA TRUOC (artifact nao la gi) — buoc 1 cua de bai

| ho so | ket luan |
|---|---|
| Trainer hien tai | `research/pipeline/g015_net_train.py` (label `retEnd_4h`, `NEED=16`, `H_BASE_MIN={"4h":240}`). **Khong co** `--label-h`. |
| Trainer dung duoc cho 72h | `research/pipeline/g5/g5_pool_train.py` = ban sao + `--label-h`, `--pool`, `--out-bins` (KHONG dong vao, sha ghim). |
| Bins ma sim doc | `predwf_map_s1a2_x1` (16 bin, S1 order + multiset x26). T170 tro vao day. |
| `g5_summary_net015_72h.json` | **KHONG phai probe doc lap.** No la `g5_summary_net015_72h.json` cua arm G5, byte-identical voi `/home/ubuntu/g5/out/g5-net015-72h/`: `label_h=72`, `thr=0.015`, 16 fold, 6,554,089 dong pool, 31.2 phut, Kaggle GPU, `sha_bin=null` (vi chay `--pool` khong `--out-bins`). |
| Probe co dung duoc khong | Dung de doc base rate/phuong sai; **KHONG** dung de ket luan horizon — chua co IC, chua co bins. |

## 6. 🔴 PHAT HIEN TRUNG LAP — VONG NAY **KHONG CHAY**

Trong khi kiem buoc 1, phat hien: **dung nhan nay da duoc pre-register VA da chay xong.**

1. **`docs/PREREG_G5.md`** (commit **`f0b088b`**, 2026-09-06, viet TRUOC moi run) liet ke
   `net015_72h` (net, h=72, thr=0.015) nhu 1 trong 8 ung vien, trainer `g5_pool_train.py`.
2. Ket qua da cong bo: **`docs/G5_VALUE_LABELS.md`** (commit **`5d1afa7`**), muc 2 va muc 4:
   `net015_72h` base rate 0.3932, train 31.2', **co bins + co sim 48 thang**.
3. Truc horizon **da duoc dong doc lap o tang offline** boi **G1**: `docs/PREREG_G1.md`
   (commit **`f931265`**), `docs/PREREG_G1_SIM.md` (**`6519c22`**), ket qua
   `docs/G1_HORIZON.md` (**`3b13de6`**) — "NULL co huong NGUOC", cong GO/NO-GO **FAIL**,
   `gate_pass=False` => **0/2 sim duoc cap phep**.
4. Vi vay §5/B cua `DESIGN_GATE_TARGET_ALIGNMENT` ("chi la summary, chua sinh bins, chua co
   IC/lift") la **SAI so voi repo**: bins va sim deu da co.

**Quyet dinh: KHONG chay.** Chay lai mot cau hoi da chot = them bien the SAU khi da thay so
(vi pham luat multiplicity/pre-reg cua chinh repo), va dot 1 slot JVM cho mot cau da co dap an.
Ket qua tong hop o `docs/RESULT_GATE_H72.md`. Muc 3-4 o tren giu nguyen lam thiet ke dong bang
neu owner quyet dinh van muon con so T170.

## 7. Chan van hanh (ghi lai, khong tu xu ly)

`docs/AGENT_RUNBOOK.md` bay #4: **1 slot JVM**, `pgrep java` phai rong. Luc kiem (2026-09-20
02:5x GMT+7) co tien trinh song `pid 1198675` = `BinanceOrderTradingManager` (start 00:12).
Dung no la thao tac ngoai pham vi job nay => moi buoc sim deu bi chan ve mat van hanh.

## 8. Toi co the sai o dau

- Neu `c4_build_map` thuc te KHONG bo thu tu cua gate (toi doc sai), thi Hướng B co kenh
  tac dong va muc 6 phai xet lai. Bang chung nguoc lai: `c4_build_map.py` gan `p_new` theo
  `r_score` cua S1 trong tick (dong `sub["p_new"]=key.reindex(...r_score)`).
- Neu `pass_raw` proxy khong tai lap duoc tren bins that (covariance cua tap con), thi cong (b)
  o muc 3.5 se bat.
- Neu owner da co ly do RIENG de do dung bien the hieu chuan nay (khong phai vi horizon), thi
  viec dung lai la khong dung — nhung khi do ten goi va tieu chi phai doi, khong con la Hướng B.
