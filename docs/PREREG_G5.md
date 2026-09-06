# PREREG_G5 — nhan/horizon nao cho VALUE MODEL, va value model dung de LAM GI

Viet TRUOC khi chay bat ky sim nao cua dot nay. Khong sua noi dung da chot; chi them phu luc dinh chinh.
Doc kem: `docs/G015_RECIPE.md` (recipe net015), `docs/G4_RECIPE_C4.md` (C4 — gia tri load-bearing o GATE),
`docs/G3_X26_RECOVERY.md`, `docs/T1_LABEL3.md` (T1 — doi nhan o tang SELECTOR), `docs/AGENT_RUNBOOK.md`.

## 0. Cau hoi

C4 do duoc: doi HO NHAN cua value model (`net015` -> `maxFav06`) lam **hong** he thong o tang GATE
(admit x5.05, 3/5 rate ngoai CI, FAIL rang buoc cung moi nam). Nhung C4 doi **dong thoi hai thu**:
(i) THU TU coin trong tick, (ii) MUC hieu chuan (phan phoi `symbolPred` trong tick).
Da biet (ii) mot minh du de pha he thong. **Chua biet (i) co mang thong tin khong.**

G5 tach hai kenh do:
- **Hieu chuan CO DINH**: moi arm dung DUNG multiset `P(win)` cua `predwf_G015x26` trong tung tick.
- **Ung vien chi quyet dinh THU TU**: coin nao nhan gia tri nao trong tick, theo `p` cua chinh no.

Neu khong ung vien nao thang S1-parity ma `G5_x26_order` cung khong thang, thi cau
"value model = hieu chuan gate, thong tin coin do S1" la DUNG.

## 1. Co so co hoc (do TRUOC, khong phai gia dinh)

1. `WfoDataset.export`: `floatBits(1 - P(win))` — **`symbolPred = 1 - p0`**, engine chon score THAP.
2. `AIRejectFilter`: `dyn_thr = SIM_MIN_MOMENTUM_15M * max(AI_DYNAMIC_MIN, symbolPred/RATE_MAX*MULT)`,
   **KHONG co tran** => `dyn_thr` tang don dieu theo `symbolPred`, tuc **giam don dieu theo `p`**.
3. `predReturn15M` (`p15`) la dai luong **theo TICK**, khong theo coin.
   => trong mot tick, "qua gate" <=> `p >= nguong_tick`. **So luong qua gate trong tick chi phu thuoc
   MULTISET cua `p` trong tick do.**
4. `c4_build_map.py` giu NGUYEN multiset `p` cua x26 trong tung tick.
   => **arm quantile-map co so candidate-minute qua gate GIONG HET parity, theo cau truc.**
   `SELECTOR_RANK_TOPK=8` lay 8 `symbolPred` thap nhat = 8 `p` cao nhat = 8 coin tot nhat theo ung vien,
   ma 8 coin do cung la 8 coin co `dyn_thr` thap nhat => `n_admit(tick) = min(8, n_pass(tick))` cung bat bien.
   **Chi COIN NAO duoc vao la doi.** Day chinh la thiet ke: tach THONG TIN khoi HIEU CHUAN.
5. Bat bien o (4) la o tang GATE. `n` cuoi cung **van co the lech nhe** vi sizing compound
   (`AGENT_RUNBOOK` muc 4: doi thoi diem thoat -> doi `marginRunning` -> doi `throttle` -> lat
   admission o vai tick sat tran von). Do duoc o L1: 0.1%-0.9%. **Khong dat cong "n giong het".**

## 2. Ung vien (8) — chi doi NHAN, moi thu khac giu nguyen `G015_RECIPE` muc 2

| ma | LABEL_MODE | horizon | thr | nguon |
|---|---|---|---|---|
| `net015_4h` | net | 4h | 0.015 | = x26 dang deploy. `p` lay TRUC TIEP tu bins goc (`cand_dev_x1.p_g015`, `max\|d\|=0.0`) |
| `net020_4h` | net | 4h | 0.020 | train moi |
| `net030_4h` | net | 4h | 0.030 | train moi |
| `net015_72h` | net | 72h | 0.015 | train moi |
| `net020_72h` | net | 72h | 0.020 | train moi |
| `net030_72h` | net | 72h | 0.030 | train moi |
| `maxfav06_4h` | maxfav | 4h | 0.06 | train moi (= ho `predwf_G015_v2`) |
| `maxfav06_72h` | maxfav | 72h | 0.06 | train moi |

**SAI LECH so voi de bai — khai bao TRUOC khi thay so:**
- De bai ghi "can train moi **5** model". Thuc te **7**:
  (a) `maxfav06_4h` (`predwf_G015_v2`) chi con **10/16 fold** (`20220101..20240401`, `TS_HI` hardcode
      2024-07-01 trong `g72_train.py`); thu muc `claudedata/predwf_G015_v2/` **khong con tren dia Oracle**
      (chi con Kaggle dataset `predwf-g015-v2-bins`). Cua so DEV la 48 thang => phai co 16 fold.
      Kernel 48 thang `chuyendinh/g015v2-maxfav-cpu` (2026-09-06) **DA FAIL** — `--fold` truyen ca
      danh sach thanh MOT chuoi, `AssertionError` o giay thu 2.5. Chua bao gio co so.
  (b) `maxfav06_72h`: `G72` da train nhung o nguong **0.07** (base 0.4041), khong phai 0.06, va chi
      10 fold, va chi co `pred_pool.npy` tren pool CU (`pool_dev.parquet`, 30 thang). Phai train lai.
- Trainer: `research/pipeline/g5/g5_pool_train.py` = ban SAO `g015_net_train.py` + DUNG 3 thay doi
  (`--label-h`, `--pool`, `--out-bins` tuy chon). Ly do xuat pool-pred thay vi bins day du: bins 16 fold
  = 888 MB/model x 7; ma `c4_build_map.py` **chi dung THU TU** cua ung vien tren dong co score
  (GIA TRI lay tu x26). XGBoost du doan tung dong doc lap => `p` tren tap con giong het `p` tren toan bo.
- Device: **Kaggle GPU** = device GOC cua x26 (`G015_RECIPE` muc 7.1). Neu het quota GPU thi chuyen
  Kaggle CPU va **ghi ro** — so sanh GIUA ung vien chi can cung device.

## 3. Viec 1 — cong LEAK 18 fold (khong ton compute)

Cong: `ts_max(train) <= cutoff - 72h` cho **18/18** fold, doc tu log kernel goc
`claudedata/predwf_G015/selector-15mtr-pred15-net015-gpu.log`. Kem: OOS cua fold i phai nam tron trong
`[cutoff_i, cutoff_i + 3 thang)` va khong fold nao sinh du doan cho quy truoc cutoff cua no.

## 4. Viec 2 — PROXY nhanh (phut, khong sim). Do tren pool OOS DEV 48 thang

Pool = `ledger/cand_dev_x1.parquet` (7,020,129 dong, 21,396 tick; 6,554,089 dong co `p_g015`).
1. **(a) phan phoi `p`**: toan pool `p10/50/90`, `mean/sd`; va **per-tick** (trung binh cua
   `p10/50/90` trong tick, trung binh `sd` trong tick).
2. **(b) rank-IC per-tick vs `g1lite`** (nhu `s1_rank.py`/`t1_label3.py`) + `edge5`.
   CI = block-bootstrap **ghep cap** theo khoi 72h, 2000 rep, `d +- 1.96*f*sd`, `f = 1.21`.
3. **(c) admission**:
   - **raw**: `symbolPred = 1 - p` cua CHINH ung vien -> `dyn_thr` -> dem candidate-minute `p15 >= dyn_thr`.
   - **quantile-map**: `p` doi sang multiset x26 cua tick theo thu hang cua ung vien -> dem lai.
     Theo muc 1.4 con so nay phai **BANG parity tuyet doi**; lech > 0 = MAP SAI, **dung**.

## 5. Viec 3 — 10 arm sim, 48 thang, profile `c3_min` sua 1 dong `WFO_FUNDING_PRED_DIR`

| arm | bins |
|---|---|
| `G5_parity_S1` | `predwf_map_s1a2_x1` (= X1_C3). Cong: **byte-identical** 98,523 / 2,058 / md5 `d39da294…` |
| `G5_<ung vien>` x8 | `c4_build_map.py` voi `pred_<ung vien>.parquet` (score = `-p`), `G015_BINS_DIR=predwf_G015x26` |
| `G5_x26_order` | `claudedata/predwf_G015x26` NGUYEN BAN (x26 quyet dinh ca thu tu lan gia tri; khong S1) |

`SIM_END_DATE=20251231`, Oracle, `TICKER_SOURCE=file`, neo cung ho voi `X1_C3`.
Dia 15G => build dataset RIENG tung arm roi `rm -rf` ngay (bay #5 + bay #13: bins **khong** di qua
duong Kaggle, phai build dataset o noi tieu thu bins).

### 5.1 Tieu chi (rate + CI khoi 72h x1.21, toan cua so VA theo nam)
`win%`, `TSloss%`, `mean(P|SM)`, `mean(P|SL)`, `mean(margin)`.
`n` va do trung khoa `(sym,start)` voi parity: **bao cao, KHONG phai tieu chi**.
**Kiem cau truc bat buoc**: `symbolPred` `p10/50/90` cua moi arm quantile-map phai ~ parity;
lech > 5% => map sai => **DUNG, khong doc so**.

### 5.2 Rang buoc cung
`maxDD <= 15%/nam`, khong nam am, khong quy < -5%. (`UW <= 120 ngay` KHONG con la nguong dat duoc
tren 48 thang — `AGENT_RUNBOOK` muc 3 — nen bao cao UW nhung khong dung lam cong.)

### 5.3 Quy tac phan quyet
Ung vien **THANG** `G5_parity_S1` khi **>= 2 rate CHAT LUONG cung huong TOT, ngoai CI** VA **PASS
rang buoc cung**. `mean(margin)` mot minh khong tinh (kenh THANG DO cua sizing compound, `AGENT_RUNBOOK` muc 4).
So theo TRUC: 4h vs 72h cung nhan; net 0.015/0.020/0.030; net vs maxFav cung horizon.
Bao cau truc don dieu (co / khong), khong chon o max theo equity.
**Equity KHONG phai tieu chi**: N=10 => `E[max nhieu]` = 2.57*sqrt(2 ln 10) = **5.5pp** CAGR.

## 6. DU DOAN GHI TRUOC (chua chay dong nao)

### 6.1 Viec 1
Leak gate **PASS 18/18** voi bien an dung **15 phut** (mot buoc luoi) o moi fold, vi
`ts < tr_cut` la bat dang thuc NGHIEM va luoi la 15m. OOS lien tuc, khong chong lan.

### 6.2 Viec 2 (proxy)
1. **(b) moi ung vien chenh nhau TRONG CI** (`n_eff` ~ 600-900 khoi 72h). Ly do: `T1_LABEL3` muc 3 da do
   4 chan nhan khac nhau va **khong chan nao** phan biet duoc tren `g1lite`/`edge5`.
2. **72h > 4h ve rank-IC vs `g1lite`** — nhung day la **thien vi CO HOC, khong phai bang chung**:
   `g1lite` duoc dinh nghia tu `maxFav_72h`/`retEnd_72h` (`x1_ledger.py`), tuc **cung ho 72h**.
   Ghi ro; **khong duoc dung o nay de ket luan nhan 72h tot hon.**
3. **(c) raw p lech admission HANG LAN theo base rate**: base cang cao => `p` cang cao =>
   `symbolPred = 1-p` cang thap => `dyn_thr` cang thap => admit cang NHIEU.
   Thu tu du doan (admit tang dan): `net030_4h` < `net020_4h` < `net015_4h` < `maxfav06_4h`
   < cac ban 72h (`maxFav_72h >= 0.06` co base **0.657**; `retEnd_72h > 0.015` du doan base ~0.45-0.55).
   `maxfav06_4h` phai tai lap duoc hieu ung C4 (~x5 so parity).
4. **(c) quantile-map admission = parity CHINH XAC** (muc 1.4). Neu khong bang thi map hong.

### 6.3 Viec 3 (sim)
5. **`n` cua 8 arm quantile-map ~ parity, lech < 1.5%** (chi qua kenh sizing compound).
   `symbolPred` `p10/50/90` **giong parity trong sai so lam tron**.
6. **KHONG ung vien nao thang parity theo quy tac 5.3.** Ky vong: 0-1 arm co 1/5 rate ngoai CI
   (nhieu o muc N=8 arm x 5 rate = 40 phep so; ky vong duong tinh gia ~2 o alpha 5%).
7. **`G5_x26_order` LA arm khac biet nhat**, va **xau hon parity**: no la "C2_g015 tren jar C3".
   So lich su `C2_g015 b:51903` vs `C2a b:59471` o cung thang exit (`c3_min` chu thich) => du doan
   >= 2 rate chat luong xau ngoai CI, `n` doi dang ke (khong bi rang buoc muc 1.4 vi thu tu doi
   nhung multiset van la cua chinh x26 — `n_pass` bat bien, con COIN thi doi han).
8. **Ket luan du doan**: cau "value model = hieu chuan gate; thong tin COIN do S1" **DUNG**.
   Bang chung se la: (6) + (7) + `L1` (gia tri khong load-bearing o trailing) + `C4` (hieu chuan
   load-bearing o gate).
9. Neu (6) SAI — mot ung vien thang that — thi phai doc no la **thong tin COIN moi**, va buoc tiep
   theo la ghep no voi S1 (khong phai thay S1).

### 6.4 Toi co the sai o dau
- Neu `n` lech > 5% o arm quantile-map thi muc 1.4 sai o mot cho toi chua thay (vi du `p15` khong
  hoan toan theo tick, hoac forward-fill 15m->phut lam lech tick). Do la thong tin, phai truy.
- `net030` co the co phan phoi `p` **rong hon** (`sel_models_net03` `p10/50/90 = 0.161/0.397/0.646`
  vs net015 `0.290/0.475/0.620`) => thu tu trong tick on dinh hon, co the thang o rank-IC ma
  khong thang o rate.

## 7. Job nay KHONG lam
Khong cham 2026 / `HOLDOUT_UNSEAL`. Khong deploy, khong cham 242, khong push. Khong sua bins dang
deploy. Khong them ung vien sau khi thay so. Khong tune tham so sau khi thay so.
Khong sua `research/pipeline/g015_net_train.py` (artifact da ghim sha256).
