# PREREG_S1PROV — tien dang ky: ghim provenance TAI LAP DUOC cho S1 (model that cua C2b)

Chot luc: 2026-09-04, **TRUOC khi rebuild bins bat ky lan nao**. Commit nay phai co truoc moi
commit ket qua (kiem bang timestamp). Day la VIEC VE SINH, **KHONG** phai di tim cai thien.

Pham vi: **CHI DEV**. KHONG cham VALIDATION (2024-07-15..2025-12-31), KHONG cham HOLDOUT 2026.
Khong rebuild file OI. Moi output ra duong dan MOI, khong ghi de bat cu bins/ledger/parquet cu nao.

## 0. TAI SAO — va dinh chinh mot nham lan

Dieu phoi truoc do cho mot agent ghim provenance nham model: agent do rebuild **G015**
(`docs/G015_PROVENANCE.md`, `predwf_G015_v2/`). Nhung **G015 KHONG phai model ma C2b dung**.

Bang chung (file:line, tu xac nhan lai trong job nay):
- `profiles/c2b.properties:23` va `profiles/c2b_min.properties:23`:
  `WFO_FUNDING_PRED_DIR=/home/ubuntu/predwf_map_s1a2` = **bins S1**.
- Bien nay di qua cong `Cfg`: `tradecore/Cfg.java:62-67`; doc boi
  `ai_ml/wfo/framework/WfoDataset.java:74` (thieu bins = fail cung `:88-94`).
- `SELECTOR_ONLY_ENTRY=1` (`c2b.properties:12`) + `SELECTOR_RANK_TOPK=8` (`:11`) =>
  bins S1 lam **ca selector rank lan gate** cua C2b. G015 chi xuat hien o tang PHAN TICH
  ledger (`research/pipeline/ledger.py` dung `p_g015`), KHONG o duong C2b java dang chay.
- `docs/G015_PROVENANCE`/`PREREG_G015REBUILD.md §7` **da ghi** dieu nay: "C2b THAT dat
  WFO_FUNDING_PRED_DIR = S1, khong phai G015".

=> Model can ghim provenance byte-identical dung chuan la **S1**. Day la NEN cho viec cat feature
(sau) va them nguon du lieu. File nay ghim S1 len dung chuan da ap cho G015.

**Khung dien giai bat buoc (NBETS / `power_wall`):** viec nay tuyen bo **dung mot dieu**:
*he S1 TAI LAP DUOC*. KHONG phat bieu gi ve "S1 tot hon". Moi so equity/rank chi de sanity.

## 1. INPUT DUOC GHIM — sha256 chot cung

Bang sha256 day du: `research/analysis/s1prov_inputs_sha.json` (commit CUNG commit nay).
Manifest digest chot cung:

> `sha256(s1prov_inputs_sha.json) = ca1d262d347d04b6c8c8c0516897f763dd9c8f272b77f596c8f98a47354bb809`

Cac hash then chot (16 ky tu dau):

| nhom | file | sha256_16 | bytes |
|---|---|---|---|
| feature hourly (KHONG rebuild) | `featv2/feat_v2.parquet` | `29d2c1e09c1b320e` | 955,376,251 |
| meta feature | `featv2/feat_v2.meta.json` | `eb8643c17de225e1` | 816 |
| candidate ledger (dau vao s1_rank) | `ledger/cand_dev.parquet` | `31876176cd60205c` | 30,494,120 |
| gate pred p15 (nguon cua cand_dev) | `claudedata/wfo_gate_pred.csv` | `ac5f6365dee520ec` | 92,509,649 |
| symbol map (ledger) | `selector_pred_out/symbol_map.csv` | `41ee8f1b96b8a01c` | 10,964 |
| symbol map (feat/oi) | `claudedata/oi/symbol_map.csv` | `3f8175512f385d83` | 11,232 |
| OI (SACH, KHONG rebuild) | `claudedata/oi/oi_percoin_full.bin` | `e3887f6309729965` | 4,227,723,300 |
| G015 source bins DEV (build_map tai phan phoi) | `claudedata/predwf_G015x26/predict_wf_{10 fold}.bin` | xem json | — |
| label DEV (nguon cua cand_dev) | `label_15m/funding_label_{14 file <= 20240401_to_20240701}.pb` | xem json | — |

**Ghi chu DEV-only:** `ledger.py:33` glob `funding_label_202[1-4]*.pb` co the cham file VAL
`20240701_to_20241001.pb`, nhung `ledger.py:17,28` loc `ts < T1 = 2024-07-01` => 0 dong VAL duoc
giu. Pin nay **chi hash 14 file label DEV** (den `20240401_to_20240701`), KHONG hash file VAL.
Tuong tu chi hash **10 G015 source bins DEV** (`predwf_G015x26` co 16 file; 6 file VAL khong hash).

**OI sha:** dung lai `e3887f63...b305ec` da xac nhan tu `G015_PROVENANCE §2` (prefix doi chieu
khop). KHONG rebuild OI (code hien tai gay leak — `docs/OI_FIX_LOG.md`).

## 2. TIEU CHI "TAI LAP THANH CONG" — chot truoc

**Diem mau chot (khac G015):** bins S1 sinh boi `build_map.py`, ma `build_map` (dong 39-41)
**chi dung THU HANG** cua score S1 trong tung tick de tai phan phoi lai chinh tap gia tri `p`
cua G015 trong tick do. Gia tri score tuyet doi KHONG vao bins; chi thu tu hang vao. Vi vay
tieu chi tai lap dung **KHONG** phai "parquet trung gian byte-identical" ma la **BINS byte-identical**.

Chay **2 lan doc lap** (`r1`, `r2`) tron pipeline tu input ghim (`s1_rank.py` -> pred ->
`build_map.py` -> bins), ra 2 thu muc rieng. THANH CONG khi:

1. **Xac dinh (deterministic):** bins **byte-identical** giua r1 va r2 o **ca 10 fold**
   (`sha256(predict_wf_<c>.bin)` r1 == r2). XGBRanker CPU `hist` nthread=4 co dinh ky vong dat.
2. **Khop ARTIFACT deploy + backup (muc tieu chinh):** `sha256` bins r1 == bins deploy
   `predwf_map_s1a2/` == backup Kaggle `predwf-map-s1a2-bins`, o **ca 10 fold**.
   - KHOP het => S1 tai lap byte-identical end-to-end; lo `cand_dev` (muc 3) la lanh tinh.
   - KHONG khop => bao ro **fold nao khac, khac bao nhieu ban ghi**, va kiem: co phai chi do
     **pha the hang** (tie-break) o cac coin score sat nhau. Neu pred r1 **dong nhat thu hang
     trong tick** voi pred deploy (spearman trong tick = 1 va argsort `method="first"` trung)
     thi bins PHAI byte-identical; neu bins khac ma rank khac => bao ro fold + so ban ghi lech,
     va ghim ban r1 lam nguon chinh thuc MOI (giai thich: bins chi phu thuoc hang).
3. **Sanity gia tri:** `edge5 g1lite OOS` cua pred r1 nam quanh **+6.80%** da ghi (`BINS_MANIFEST`,
   `S1v2.out`); spearman(pred_r1, `-score` cua `pred_s1a2.parquet` deploy) tren dong chung.
   Day KHONG phai pass/fail chinh xac — chi chan sai pipeline.

**Lo da biet (`cand_dev`):** `ledger/cand_dev.parquet` bi build lai 2026-09-03 17:53, SAU khi
`pred_s1a2.parquet` sinh 2026-09-02 22:49. Ban `cand_dev` sinh ra pred deploy **da bi ghi de**,
khong con. Vi vay tieu chi (2) la phep kiem RETROACTIVE: neu bins r1 (tu `cand_dev` HIEN TAI) khop
byte deploy, thi `cand_dev` hien tai sinh **cung thu hang** voi ban 09-02 => lo dong lai bang
bang chung. Neu khong khop, do la dau vet cua lo, se bao nguyen trang. **KHONG** ghi de `cand_dev`,
**KHONG** rerun `ledger.py build` (no ghi de `cand_dev`).

## 3. THU TU + GIOI HAN

1. Commit file nay + `s1prov_inputs_sha.json`. Ghi commit hash.
2. Chay r1, r2 tu input ghim (CPU). Sinh bins ra `/home/ubuntu/predwf_s1_v2/` (r1) +
   `/home/ubuntu/predwf_s1_v2_r2/` (r2, so xong xoa). So (§2).
3. So bins r1 vs deploy `predwf_map_s1a2/` vs backup Kaggle. Ghi `docs/S1_PROVENANCE.md` +
   `predwf_s1_v2/MANIFEST.sha256`.
4. Khoi phuc ly do cat 40->9 cua S1 (grep git/docs/`PROCESS_LOG*`); khong tim thay => ghi thang
   "ly do KHONG tai lap duoc, 9 feature la du kien". KHONG bia.
5. Cap nhat memory: S1 co provenance byte-identical; G015 KHONG phai model C2b.

**Giói hạn cứng:** chi DEV; KHONG ghi de `predwf_map_s1a2/`, `ledger/pred_s1a2.parquet`,
`featv2/feat_v2.parquet`, `predwf_G015_v2/`; KHONG rebuild OI; KHONG rerun `ledger.py build`
(ghi de cand_dev); KHONG cham live/shadow (242 read-only); **GPU cam cho rankIC** (CPU hist);
Kaggle: chi backup dataset, KHONG submit kernel; khong cham `/home/ubuntu/{gs,tick,nbets,g015,fcut}/`;
`df -h /` truoc moi buoc sinh du lieu, duoi 6G thi DUNG + don `wfo_ds_*`; JVM: khong dung (chi can
bins, khong can java); Python logging (cam print).

## 4. GIA DINH CO THE SAI — ghi truoc de khong troi

- Neu bins r1 KHONG khop deploy VA pred cung KHONG dong nhat thu hang => co the ban featv2 script
  da doi giua 09-02 va nay, hoac `cand_dev` hien tai that su khac ban 09-02 o muc doi hang.
  Se bao ro, KHONG ep ghim.
- Neu phat hien S1 KHONG phai model C2b (khac lai gia dinh) => DUNG, bao ngay.
