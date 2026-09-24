# LEAK L1 REPORT — nghi van leak o model G015 (A2c / A2e)

Ngay do: 2026-09-03. Pham vi du lieu: **CHI DEV** (`/home/ubuntu/ledger/cand_dev3.parquet`,
2021-12-31 .. 2024-06-30). Khong cham VALIDATION (2024-07-15..2025-12-31), khong cham HOLDOUT 2026.
Khong chay java, khong backtest, khong train lai. Script do: `/home/ubuntu/leakprobe/{lpm.py,lpm2.py,lpp.py}`.

---

## CAU 1 — G015 duoc huan luyen the nao, chinh xac

**KET LUAN: tim duoc day du. G015 = 16 fold walk-forward expanding, nhan 1-CHIEU `maxFav_4h >= 0.06`
(KHONG co stop-loss), luoi mau 15m, purge 72h wall-clock. Script that la nhanh `_1m`, KHONG phai ban
CANON trong repo — day la mot lo hong provenance can ghi nhan.**

### Duong day code (da xac dinh, khong suy doan)

| Lop | File | Bang chung |
|---|---|---|
| Kernel Kaggle (dat env) | `/home/ubuntu/kB15/net015/selector-15mtr-pred15-net015-gpu.py` | ten kernel khop `wfo_canonical_config_2026-08-15.md:8` ("predwf = predwf_G015") |
| Script that duoc exec | `/home/ubuntu/claudedata/gen_funding_wf_predictions_1m.py` | kernel dong 36: `exec(open(.../gen_funding_wf_predictions_1m.py).read())` |
| Ban CANON trong repo — **KHONG duoc dung** | `ml/training/gen_funding_wf_predictions.py` | `wfo_train_code_provenance_versions_2026-08-16.md:13`: "Kernel ... exec `_1m` (khong phai CANON)" |
| Bins deployed | `/home/ubuntu/claudedata/predwf_G015x26/*.bin` (16 file, mtime 14/08 15:03-15:05) | `AUDIT_APPLIED.md:41` tro ve `dev_c4.sh:23` (`predwf_G015x26`) |

Link count cua cac bin la 33-34 => cac tag `predwf_G015x26`, `x26e`, `x26q2`, `G015K5`... la **hardlink
cung mot lo bins** tu run 14/08. Doi chieu `predwf_G015x26` chi co 16 fold (20220101..20251001).

### Tham so THAT (lay tu code, khong tu doc)

| Muc | Gia tri | file:line |
|---|---|---|
| Feature | 45 = `f0..f39` (Tool1) + 5 OI (`oi_delta24h, oi_z, ls_global, ls_toptrader, taker_buy`) | `gen_..._1m.py:70` (`FEAT`) |
| OI ghep vao feature | `merge_asof(direction="backward", tolerance=2h)` — **chi lay OI qua khu** | `gen_..._1m.py:374` |
| Nhan | `y = (maxFav_h >= WIN)`, `WIN = 0.06` **hardcode**; loc `nBars >= H_STEPS` | `gen_..._1m.py:37`, `:303-304` |
| Nhan — stop-loss | **KHONG CO.** `maxAdv` khong bao gio duoc doc | `gen_..._1m.py:293`, `:310` chi lay `maxFav_{h}` + `nBars_{h}` |
| Cua so nhan | `maxFav_H = max(high(tau)/close(t) - 1)`, `tau` thuoc **(t, t+H]** — thuan tien ve tuong lai, anchor `close(t)` biet tai t | `ExportFundingLabel.java:37`, `:40-41` |
| Horizon dung | 4h (`H_BASE_MIN["4h"]=240` phut / GRID 15 = 16 buoc) | `gen_..._1m.py:36`, `:41` |
| Luoi lay mau | 15m (`SELECTOR_GRID_MIN=15`) | kernel dong 26; `gen_..._1m.py:36-37` |
| Chia train/test | expanding WFO, OOS block = `[cutoff, cutoff+3m)` **disjoint** | `gen_..._1m.py:467-471` |
| **Purge** | `PURGE_STEPS=288` x 15m = **72h wall-clock** | kernel dong 27; `gen_..._1m.py:53`; `tr_cut = cutoff_ms - PURGE_MS` `:414` |
| Embargo | 0 (khong can: expanding => train LUON truoc test) | `gen_..._1m.py:415` |
| Guard leak | `assert int(j["ts"].max()) < cutoff_ms` — chay moi fold | `gen_..._1m.py:421` |
| Model | XGBoost `n_est=400, depth=5, lr=0.05, subsample=0.8, colsample=0.8, min_child_weight=20, scale_pos_weight=(1-pos)/pos, seed=42` | `gen_..._1m.py:384-388` |
| So vong | 16 fold (FIRST_CUTOFF=20220101, OOS 3 thang) | 16 file bin; kernel dong 28 |

### Hai canh bao provenance (phat hien phu, that)

1. Kernel dat `LABEL_MODE="net"` va `NET_THR="0.015"` (dong 31-32) nhung **hai bien nay khong ton tai
   trong script duoc exec** — grep `LABEL_MODE|NET_THR` tra ve 0 dong tren
   `gen_funding_wf_predictions_1m.py`, tren ban CANON, va tren `ml/training/gen_funding_wf_predictions.py`.
   => **env chet, bi bo qua im lang.** Ten model "net015" KHONG phan anh nhan that.
   Nhan that la `maxFav >= 0.06`.
2. Log `selector-15mtr-pred15-net015-gpu.log` in `Label 4h: 48724373 rows | base=0.0457` — dung dinh dang
   log cua nhanh 1-chieu (`gen_..._1m.py:306`). Ban 2-chieu trong repo in dinh dang khac han
   (`... win=%.4f lose=%.4f timeout=%.4f`, `train_funding_selector_wfo.py:166`). => xac nhan doc lap
   rang nhanh 1-chieu da chay.

---

## CAU 2 — co leak that hay chi la chong lap cua so?

**KET LUAN: chi (a) CHONG LAP CUA SO. KHONG co (b) leak that. Danh dau "A2e = L1 leak" trong
`PHASE1_DECISION_SURFACE.md:17` va `AUDIT_APPLIED.md:112,382` la **SAI**: no gop lam mot hai thu khac
nhau. Purge that la 72h, gap 18 lan horizon nhan 4h.**

### (b) Leak that — KHONG CO. Ba dieu kien deu dong.

**b1. Cua so nhan cua mau TRAIN co lan sang thoi gian mau TEST khong? KHONG.**

Code chia du lieu (`gen_funding_wf_predictions_1m.py:414-415`):
```
tr_cut = cutoff_ms - PURGE_MS                     # PURGE_MS = 288 * 15m = 72h
tr_meta = metadf[tsv < tr_cut]
```
Mau train cuoi cung o `ts <= cutoff - 72h - 15m`. Nhan cua no phu **(ts, ts+4h]**, ket thuc o
`cutoff - 68h15m`. Mau test dau o `ts = cutoff`. => cua so nhan train ket thuc **68h15m TRUOC** khi
test bat dau. Con co `assert ... < cutoff_ms` (`:421`) chay that moi fold lam chot chan.

**b2. Feature co dung du lieu sau thoi diem quyet dinh khong? Phan do duoc: KHONG.**
- OI: `merge_asof(direction="backward", tolerance=2h)` (`:374`) — chi lay ban ghi OI gan nhat **<= t**.
- Nhan: `ExportFundingLabel.java:37,40-41` — cua so **(t, t+H]** thuan tien, anchor `close(t)`;
  dong `:115` ghi ro "snapshot(h, NaN) cho moc chua cham ... **KHONG bao gio dung nen tuong lai**".
- `f0..f39`: **khong tim thay bang chung** — xem muc "Con lai chua dong" cuoi bao cao.

**b3. Purge co du moi vong khong? DU, 16/16 vong.** (`lpp.py`, hang so lay tu code, cutoff lay tu ten
file bin that)

| vong (cutoff) | mau train cuoi | het nhan train | mau test dau | gap ts | horizon | THIEU purge | du ra |
|---|---|---|---|---|---|---|---|
| 20220101 | 2021-12-28 16:45 | 2021-12-28 20:45 | 2021-12-31 17:00 | 72.25h | 4h | **0** | 68.25h |
| 20220401 | 2022-03-28 16:45 | 2022-03-28 20:45 | 2022-03-31 17:00 | 72.25h | 4h | **0** | 68.25h |
| 20220701 | 2022-06-27 16:45 | 2022-06-27 20:45 | 2022-06-30 17:00 | 72.25h | 4h | **0** | 68.25h |
| 20221001 | 2022-09-27 16:45 | 2022-09-27 20:45 | 2022-09-30 17:00 | 72.25h | 4h | **0** | 68.25h |
| 20230101 | 2022-12-28 16:45 | 2022-12-28 20:45 | 2022-12-31 17:00 | 72.25h | 4h | **0** | 68.25h |
| 20230401 | 2023-03-28 16:45 | 2023-03-28 20:45 | 2023-03-31 17:00 | 72.25h | 4h | **0** | 68.25h |
| 20230701 | 2023-06-27 16:45 | 2023-06-27 20:45 | 2023-06-30 17:00 | 72.25h | 4h | **0** | 68.25h |
| 20231001 | 2023-09-27 16:45 | 2023-09-27 20:45 | 2023-09-30 17:00 | 72.25h | 4h | **0** | 68.25h |
| 20240101 | 2023-12-28 16:45 | 2023-12-28 20:45 | 2023-12-31 17:00 | 72.25h | 4h | **0** | 68.25h |
| 20240401 | 2024-03-28 16:45 | 2024-03-28 20:45 | 2024-03-31 17:00 | 72.25h | 4h | **0** | 68.25h |
| 20240701 .. 20251001 (6 vong con) | (y het) | | | 72.25h | 4h | **0** | 68.25h |

`so vong THIEU purge: 0 / 16`. Neu horizon la 72h (moc dai nhat) thi gap 72.25h van du sat nhung du.
Voi horizon 4h dang dung => **du ra 68.25h**.

### (a) Chong lap cua so — CO THAT, va no la van de duy nhat

Luoi 15m + nhan 4h => **16 mau lien tiep chia nhau cung khoang tuong lai**. Nang hon: outcome dung de
do hieu chuan la `g1lite`, dung cua so **72h** (`featv2/ledger.py.bak:33`:
`g1lite = maxFav_72h - min(0.5*maxFav_72h, 0.08) neu maxFav_72h>=0.05, nguoc lai retEnd_72h`)
=> **288 mau lien tiep** chia nhau cung tuong lai.

Hau qua dung: DEV 2021-12..2024-06 chi co **302 khoi 72h doc lap** that, du bang co 15.44M dong.
Day la sai ve **do tin cay thong ke**, KHONG phai leak: no khong lam diem uoc luong lech (do o Cau 3).

**Phan biet: (a) CO, (b) KHONG.**

---

## CAU 3 — thiet hai bao nhieu?

**KET LUAN: diem uoc luong hieu chuan SONG NGUYEN. spearman tren mau khong chong lap = 0.1718 +- 0.0187
so voi moc 0.1675 (lech +0.0042, nam sat giua CI). Don dieu 20/20 cung khong phai artifact cua chong lap.
Thiet hai duy nhat: CI cua 0.1675 rong hon **74 lan** so voi CI naive => moi ket luan dua tren "n = 15 trieu
dong" phai doc lai voi n hieu dung ~ **302 khoi 72h**.**

Khong can train lai. Tat ca do bang cach re, tren DEV.

### 3.1 Tai lap moc + do lai tren mau khong chong lap (`lpm.py`)

Tai lap chinh xac: `spearman toan pool = 0.1675` (khop moc 0.1675), don dieu **1.00 (20/20 bucket)**,
theo nam `2021 0.1807 / 2022 0.1570 / 2023 0.1647 / 2024 0.1985` — khop het so ban da cho.

Mau khong chong lap = giu 1 tick moi S buoc 15m, quet nhieu offset:

| khoang cach | S | n/mau | spearman tb | sd | min | max | don dieu tb |
|---|---|---|---|---|---|---|---|
| 4h (= horizon nhan G015) | 16 | 965,130 | **0.1676** | 0.0020 | 0.1641 | 0.1706 | 0.974 |
| 24h | 96 | 160,859 | **0.1676** | 0.0092 | 0.1520 | 0.1836 | 0.855 |
| **72h (khong chong lap THAT cho g1lite)** | 288 | 53,614 | **0.1718** | 0.0187 | 0.1437 | 0.2251 | 0.739 |

=> Bo hoan toan chong lap: **0.1718 vs 0.1675**. Khong mat gi.

### 3.2 Doi chung: don dieu tut la do CO MAU NHO, KHONG phai do chong lap (`lpm2.py`)

Nghi van hop ly: don dieu tut 1.00 -> 0.739. La chong lap tung "do" hieu chuan len? **Khong.**
Doi chung = mau ngau nhien CUNG CO MAU nhung VAN chong lap:

| co mau | don dieu — mau ngau nhien (CO chong lap) | don dieu — mau khong chong lap | chenh |
|---|---|---|---|
| 53,614 | 0.730 (min 0.632) | 0.739 | +0.009 |
| 160,859 | 0.864 (min 0.737) | 0.855 | -0.009 |
| 965,130 | 0.969 (min 0.842) | 0.974 | +0.005 |

Hai cot **trung nhau trong pham vi nhieu**. => do tut don dieu la **100% hieu ung co mau** (20 bucket
tren 53k dong thi moi bucket ~2.7k dong, nhieu tu nhien lan buoc). Don dieu 20/20 o toan pool la THAT.

### 3.3 Thiet hai that: CI bi hep gia

Block-bootstrap 400 rep, don vi resample = khoi 72h (302 khoi, dung don vi doc lap that):

| | gia tri |
|---|---|
| diem | 0.1662 |
| sd block-bootstrap | 0.0187 |
| **CI95 that** | **[0.1260, 0.2005]** |
| CI95 naive (coi 15.44M dong doc lap) | +-0.00050 |
| **CI that / CI naive** | **74 lan rong hon** |
| spearman > 0 trong so rep | 100.0% |
| spearman > 0.10 trong so rep | 100.0% |

Doc dung: dau va do lon cua tin hieu la **ben vung** (100% rep > 0.10). Cai bi thoi phong la **do chinh
xac**: khong duoc phat bieu "0.1675" nhu mot con so 4 chu so co nghia; phai la **0.17 +- 0.02**.

### 3.4 Khong can train lai

Khong co hang muc nao trong Cau 3 doi train lai. Neu ve sau muon do (a) o tang STRATEGY (vi du dung lai
CPCV voi don vi block 72h thay vi gia dinh dong doc lap) thi do la viec cua pre-reg khac, khong phai leak.

---

## CAU 4 — A2c: label stop-loss 0.03 la placeholder. Anh huong gi?

**KET LUAN: KHONG anh huong gi toi score dang cap cho gate, vi model G015 deployed **khong dung
stop-loss chut nao**. `SEL_ADV_PCT = 0.03` la placeholder trong hai script KHAC (chua tung sinh ra bins
dang chay). A2c la mot **quyet dinh treo tren giay**, khong phai mot quyet dinh dang co hieu luc.**

### 4.1 Bang chung: nhan cua G015 deployed la 1-CHIEU, khong co SL

Script duoc exec (`gen_funding_wf_predictions_1m.py`):
- `:293` `cols = ["tEpochMs","symbol"] + [f"maxFav_{h}"...] + [f"nBars_{h}"...]` — **khong doc `maxAdv`**
- `:310` `d = df[["tEpochMs","symbol", f"maxFav_{h}", f"nBars_{h}"]]`
- `:304` `d["y"] = (d["maxFav"] >= WIN)`, voi `:37` `WIN = 0.06` hardcode

Kiem ca ban `_1m` cu (ban dang song ngay 14/08 khi sinh bins):
`/home/ubuntu/sel1m_code/gen_funding_wf_predictions_1m.py.bak2:26,100-101` — **y het**: `WIN=0.06`,
chi doc `maxFav`+`nBars`. => du run 14/08 dung ban nao trong hai ban `_1m`, nhan van la 1-chieu khong SL.

### 4.2 Vay `SEL_ADV_PCT=0.03` nam o dau?

| File | Co dung SL 0.03? | Da sinh ra bins dang chay? |
|---|---|---|
| `ml/training/gen_funding_wf_predictions.py` (CANON, trong repo) | CO — `:38` `SEL_ADV_PCT`, `:316` `adv_hit` | **KHONG** — provenance doc `:13` ghi ro kernel exec `_1m`, khong phai CANON |
| `ml/funding_selector/train_funding_selector_wfo.py` | CO — `:38`, `:157` | **KHONG** — day la script do do on dinh (LIFT/rankIC per-fold), khong xuat `predict_wf_*.bin` |
| `gen_funding_wf_predictions_1m.py` (**da chay**) | **KHONG** | **CO** |

=> A2c dung la "chua tung chot", nhung no cung **chua tung co hieu luc**. Canh bao trong
`AUDIT_APPLIED.md:224` ("moi no cua G015: label SL 0.03 placeholder chua chot") la **mo ta sai** ve
model deployed.

### 4.3 Anh huong tam ly nguoc: no THAT su la gi

Van de that cua nhan G015 khong phai "SL = 0.03 chua chot" ma la **khong co SL nao ca**: nhan chi hoi
"gia co tung cham +6% trong 4h khong", bo qua hoan toan viec truoc do co sut -X% hay khong. Do la mot
**quyet dinh nhan chua bao gio duoc ghi vao bang quyet dinh** — nghiem trong hon A2c nhu dang ghi,
vi no lech khoi cach strategy that su exit (co moveSL 0.05, arm, giveback).
Day la mot muc MOI can vao `PHASE1_DECISION_SURFACE.md`, khong phai sua A2c.

### 4.4 Neu doi gia tri do thi phai train lai model nao? Chi phi?

- **Doi 0.03 -> X (giu 1-chieu):** khong phai train lai gi ca, vi 0.03 khong vao model deployed.
  Chi can sua 2 script chua chay (CANON + `train_funding_selector_wfo.py`).
- **Doi nhan sang 2-chieu (dung SL that):** phai train lai **G015: 16 fold** (1 model XGBoost/fold,
  `n_est=400 depth=5`, 45 feature, train set tang dan toi ~48.7M dong nhan cho horizon 4h).
  - **KHONG can xuat lai label**: `maxAdv_H`, `tHitFav_H`, `tHitAdv_H` DA CO san trong file label `.pb`
    (CANON doc chung o `gen_funding_wf_predictions.py:299`). Tiet kiem toan bo buoc export Java.
  - Viec phai lam: tro kernel sang CANON (khuyen nghi san co o
    `wfo_train_code_provenance_versions_2026-08-16.md:56`), set `SEL_ADV_PCT`, chay 16 fold.
  - **Chi phi thuc te: khong tim thay bang chung** — log `selector-15mtr-pred15-net015-gpu.log`
    chi con 1 cutoff (run regen 16/08), khong co log wall-clock cua run 16-fold ngay 14/08. Chi biet
    16 bin duoc GHI trong khoang 15:03-15:05 (thoi gian ghi, khong phai thoi gian train).
  - **Va: doi nhan G015 => doi phan phoi P(win) => doi `dyn_thr` => doi nguong vao lenh C2b
    => moi so DEV/VAL cua C2b phai chay lai.** Day la chi phi lon nhat, khong phai chi phi train.
- **Toi KHONG chay gi trong muc nay** (theo yeu cau): Kaggle dang het 5 slot, Oracle 1 slot java dang bi
  job khac dung.

---

## MUC DO ANH HUONG TOI C2b

### => **ANH HUONG DO TIN CAY THONG KE** (muc 2/3)

Khong phai "khong anh huong", cung **khong phai "vo hieu hoa ket qua"**. Bao ve bang so:

**Vi sao KHONG phai "vo hieu hoa":**
1. Purge that = **72h**, horizon nhan = **4h**, du ra **68.25h** tren **16/16 vong** (`lpp.py`).
   Khong co dong nhan train nao lan sang vung test. Con `assert` chay that moi fold.
2. Gate cua C2b dung **do tu tin tuyet doi** cua G015:
   `dyn_thr = MIN_MOMENTUM_15M * max(AI_DYNAMIC_MIN, score/RATE_MAX * AI_DYNAMIC_MULTIPLIER)`
   (`research/analysis/gate_cfg.py`, doc truc tiep tu `AIRejectFilter.java`). Cai gate phu thuoc la
   **hieu chuan tuyet doi** cua G015. Do lai tren mau khong chong lap: **0.1718 vs 0.1675**, don dieu
   20/20 tai lap duoc khi doi chung dung co mau. => nguong vao lenh cua C2b **khong** duoc xay tren mot
   tin hieu nhin thay tuong lai.
3. Nhan cua G015 khong dung `maxAdv` => A2c (SL 0.03) khong vao model => khong co duong lay nhiem tu A2c.

**Vi sao KHONG phai "khong anh huong":**
1. CI cua moc 0.1675 rong hon **74 lan** so voi CI naive: **[0.1260, 0.2005]** thay vi **+-0.0005**.
   n hieu dung la **302 khoi 72h**, khong phai 15.44M dong.
2. Moi phep so sanh da dung "n lon" de tuyen bo y nghia thong ke tren pool nay dang **hep gia CI**.
   Cu the, hai con so trong `AUDIT_APPLIED.md:45` (A10/H3) duoc so truc tiep voi nhau:
   `rho(pred,g1lite) = 0.1667` (model H3) vs `G015 = 0.1675`. Voi sd block-bootstrap **0.0187**,
   chenh lech **0.0008** nay la **NHIEU HOAN TOAN** (~0.04 sd). Ket luan "H3 khong hon G015" van dung
   (no FAIL 4/5 tieu chi vi ly do khac), nhung **rieng phep so 0.1667 vs 0.1675 khong co suc phan biet**
   va khong nen duoc dung nhu bang chung.
3. Tuong tu, `rank-IC S1 +0.150 vs G015 +0.055` (`AUDIT_APPLIED.md:144`) can duoc do lai voi CI block
   72h truoc khi dung lam co so cho quyet dinh freeze. Chenh 0.095 co the van song, nhung **chua ai do CI**.

**Tom lai:** con so DEV/VAL cua C2b (b:60390 / VAL b:47681, CAGR 23.60%, maxDD -7.28%) **khong bi vo hieu
hoa boi L1**. Nhung moi phat bieu "y nghia thong ke" dua tren pool 15M dong nay deu phai tinh lai voi
n hieu dung ~302; dac biet cac phep so hai model chenh nhau < 0.02 spearman la **khong phan biet duoc**.

---

## CON LAI CHUA DONG (khong du bang chung — ghi de khong troi)

1. **Tinh nhan qua cua `f0..f39`: khong tim thay bang chung.** Da kiem: OI ghep backward (SACH), nhan
   forward-only (SACH). Nhung 40 feature Tool1 duoc tinh trong Java va
   `PHASE1_DECISION_SURFACE.md:13` tu ghi la "con lai opaque". Grep `shift|lookahead|leak` tren
   `ml/lib/tool1_col.py` (decoder) va `ExportTool1Master.java` (orchestrator) => 0 dong.
   Chua doc duoc noi tinh feature. **Day la lo hong leak con lai duy nhat toi khong dong duoc o phien nay.**
   Bang chung gian tiep (yeu): rho ~0.17 la muc do tin hieu hop ly cho tin hieu that, khong phai muc
   cua leak; va A10 co shuffle control. Ca hai **khong phai chung minh**.
2. **Provenance run 14/08: khong co log.** Toi suy ra tham so tu (i) file kernel, (ii) doc provenance,
   (iii) dinh dang log cua run 16/08. Ba nguon dong quy, nhung **khong co log truc tiep cua chinh run
   sinh 16 bins**. Neu can chac 100% thi phai regen 1 fold va so md5 — chua lam.
3. Kernel dat 2 env **chet** (`LABEL_MODE`, `NET_THR`) khong duoc script doc. Chua ro con env chet nao
   khac; toi chi kiem 2 cai nay.

---

## VIEC CAN QUYET

1. **Dong A2e nhu la KHONG PHAI leak** — sua `PHASE1_DECISION_SURFACE.md:17,43` va
   `AUDIT_APPLIED.md:112,224,382`: doi "overlap = L1 leak" thanh "overlap = tuong quan chuoi, purge 72h
   DU; anh huong CI khong anh huong diem uoc luong". (Toi khong sua repo theo gioi han.)
2. **Viet lai A2c**: gia tri 0.03 khong co hieu luc. Muc THAT can quyet la
   "nhan G015 1-chieu `maxFav>=0.06`, KHONG co stop-loss" — mot quyet dinh chua tung duoc ghi.
3. **Quyet co dong lo hong `f0..f39` khong** (muc 1 phan tren). Day la rui ro leak duy nhat con mo.
4. **Quyet co do lai CI block-72h cho cac phep so model** (S1 vs G015 rank-IC) truoc khi freeze.
