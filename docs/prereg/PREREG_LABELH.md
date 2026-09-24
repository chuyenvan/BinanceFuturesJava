# PREREG_LABELH — tien dang ky: CHAN TROI NHAN co doi selector khong (72h vs 4h)

Chot 2026-09-04, **TRUOC khi train bien the nao**. Commit nay phai co truoc `docs/result/LABELH_RESULT.md`.
CHI DEV. Khong cham VALIDATION/HOLDOUT. Khong rebuild OI. Output ra duong MOI.

## 0. CAU HOI — va vi sao phai train, khong do bang tuong quan nua

`LABEL_ROI3` da do tuong quan(nhan, ROI that) va **phai rut ket luan** vi **CHONG LAN CUA SO**:
ROI hien thuc hoa toi 168h nen nhan chan troi dai co hoc trung nhieu hon voi no. Cach duy nhat
tach duoc "muc tieu tot hon" khoi "nhin thay nhieu hon" la **train tren tung nhan roi cham bang
tieu chi KHONG phai nhan do**.

`SELECTOR_FEATURES §B.2`: moi the he tung train deu o **72h** => **chua bao gio co S1 train tren
nhan 4h**. Va khong duoc dung "G015 vs S1" thay the (khac **4** thu cung luc: chan troi, nhan,
thuat toan, feature).

**Ba nhanh khong phai null co hoc** (do truoc khi chot): `spearman(hang g1lite, hang maxFav_72h)`
**trong tick = 0.897**, chi **67.7%** dong giu dung hang, va **28.9%** dong co `maxFav_72h < 0.05`
— dung vung `g1lite` doi sang `retEnd`.

## 1. BA BIEN THE — chot cung, chi khac NHAN

Moi thu con lai **y nguyen** `s1_rank.py`: **9 feature** `KEEP`, `XGBRanker rank:ndcg`,
`n_estimators=300 max_depth=4 lr=0.05 subsample=0.8 colsample_bytree=0.8 min_child_weight=50
n_jobs=4 tree_method=hist random_state=42 lambdarank topk-8`, group = tick, 10 fold cutoff
`20220101..20240401`, OOS 3 thang, **purge 72h**, `assert tr.ts.max() < cutoff`.

Nhan qua **CUNG MOT phep bien doi**: `rel = X - median_tick(X)`;
`rel5 = min(int(rank_pct(rel) * 5), 4)`.

| ma | `X` | ghi chu |
|---|---|---|
| **`L72_g1lite`** | `g1lite` (72h) | = **S1 dang chay**. Dung lam **cong tai lap** |
| `L72_maxfav` | `maxFav_72h` | cung chan troi, khac cong thuc |
| `L4_maxfav` | `maxFav_4h` | **khac chan troi** — cau hoi chinh |

`maxFav_4h` join tu `label_15m/funding_label_202[2-4]*.pb` (`usecols` co `maxFav_4h`,`nBars_4h`),
loc `nBars_4h >= 16`. **Khong** doi pool: giu dung pool `cand_dev.parquet` de ghep cap sach.

**M = 2** phep so (moi bien the vs `L72_g1lite`) => `k = sqrt(2 ln 2) = 1.1774`.

## 2. CONG TAI LAP — chan tren, bat buoc

`L72_g1lite` phai cho `spearman(pred, -score cua ledger/pred_s1a2.parquet) >= 0.999` tren cac dong
chung (S1_PROVENANCE da chung minh = 1.0). **Truot => DUNG JOB**, khong bao cao bien the nao.

## 3. 🔴 KHONG CO TIEU CHI TRUNG LAP — khai bao truoc, day la gioi han THAT

Moi tieu chi kha dung deu o **ho 72h** (`g1_replay`, `pathq_72h`) hoac la **ROI that** (tap lenh
do **chinh S1 hien tai** chon => thien lech chon co loi cho `L72_g1lite`). **Khong co tieu chi
nao trung lap ve chan troi.** Vi vay:

- **CAM tuyen bo "nhan X tot hon"** neu bang chung duy nhat den tu mot tieu chi **cung chan troi**
  voi X. Ghi ro tieu chi nao thien vi ai.
- Bao cao **ca ba** tieu chi duoi, khong chon mot cai roi bo cac cai khac.

| tieu chi | thien vi | n |
|---|---|---|
| (A) rank-IC vs **`g1_replay`** tren full DEV | 72h | 4,595 tick |
| (B) rank-IC vs **`pathq_72h`** = `maxFav_72h/abs(maxAdv_72h)` tren full DEV | 72h | 4,595 tick |
| (C) rank-IC vs **ROI THAT** cua 970 lenh C2b, trong tick >= 4 lenh | tap do S1 chon | ~115 tick |

## 4. THUOC DO + CI

rank-IC = trung binh **theo tick** cua `spearman(pred, outcome)`, tick >= 10 dong
(tieu chi C: >= 4 lenh). CI: **block-bootstrap khoi 72h** (chinh) + 24h/168h (do ben),
**ghep cap** (cung danh sach khoi cho ca hai nhanh), 2000 rep, seed **20260904**,
percentile 2.5/97.5 **CUA HIEU**.
⚠️ `COV_RESULT` da do: ho chuoi DAY nay **duoi phu o MOI do dai khoi**, `sd` hieu thieu ~21%
=> **bao cao kem `f = 1.21`**, va **khong** duoc trinh CI 72h tho nhu la chuan.

## 5. DIEU KIEN CHOT — chot TRUOC khi thay so

- **PHAN BIET DUOC** khi CI da hieu chinh (`d +- 1.96*f*sd`) **loai tru 0** o **ca 3** do dai khoi,
  **VA** `|d| > k*f*sd` voi `k = 1.1774`.
- **KHONG PHAN BIET DUOC** trong moi truong hop khac. `L4_maxfav` khong phan biet duoc
  => **chan troi khong phai truc dang theo duoi** o tang selector, va do la ket qua co gia tri
  (null co thong tin), khong phai that bai.
- Neu `L4_maxfav` **KEM phan biet duoc** => xac nhan chan troi 72h dung, va giai thich duoc
  vi sao nhan G015 (4h) yeu.
- Neu `L4_maxfav` **HON phan biet duoc** tren (A) va (B) => **canh bao**: ca hai tieu chi do deu
  o ho 72h, nen ket qua "nhan 4h thang tren tieu chi 72h" la manh; khi do moi tinh den bins+java.

## 6. RANG BUOC CUNG — chi ap cho bien the THANG (neu co)

Sinh bins duong MOI `/home/ubuntu/predwf_s1lh_<ma>/` (KHONG dung `predwf_map_s1a2`), profile moi
tu `c2b_min` chi doi `WFO_FUNDING_PRED_DIR`, **1 run java DEV**
(`pgrep java` rong truoc; `df -h /` >= 8G), cham `qret.py`, **maxDD >= -15.12%**.
Truot => bo do khong thay duoc, bao thang, **khong vi CAGR**.
⚠️ Cong byte-identity cua `run_c2b_dev.sh` **se FAIL va do la dung du kien** (doi bins).

## 7. GPU BI CAM — va day la ly do bang so

`power_wall` quy tac 1: `XGBRanker(device="cuda")` khong tai lap CPU — spearman **0.985490**
(nguong 0.999), **sai lech tuyet doi trung binh per-tick rank-IC = 0.01843**, va tren GPU da tung
tao **2 ung vien vuot nguong GIA**. Hieu ung job nay san (theo `S1CUT`) co `sd_boot`
**0.0032-0.0096**, do lon 0.001-0.027 => **nhieu GPU nhan chim no**. Va `Kaggle CPU != Oracle CPU`
(0.17040 vs 0.1723) => phep so ghep cap phai **cung mot moi truong**.
Toc do khong phai ly do: S1 10 fold tren Oracle CPU do duoc **286s** => 3 bien the ~15 phut.
=> **Chay CPU tren Oracle, `n_jobs=4`, `random_state=42`.**

## 8. THU TU + GIOI HAN

1. Commit file nay. 2. Train 3 bien the CPU, ghi per-tick IC. 3. Cong tai lap §2 — truot thi dung.
4. Bootstrap 3 tieu chi §3 kem `f=1.21`. 5. Chi khi co bien the thang moi lam §6.
6. `docs/result/LABELH_RESULT.md` + commit.

Gioi han cung: chi DEV; khong ghi de `predwf_map_s1a2/`, `ledger/pred_s1a2.parquet`,
`featv2/feat_v2.parquet`, `claudedata/predwf_G015x26/`; khong rebuild OI; **GPU cam**;
Python dung `logging`; git chi add file cua minh; **KHONG push**.
