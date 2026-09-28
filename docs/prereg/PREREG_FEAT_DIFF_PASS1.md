# PRE-REG PASS 1 — DIFF 33 FEATURE: LIVE (feat_dump) vs EXPORT DEV

Trang thai: **CHOT TRUOC** khi nhin bat ky thong ke feature nao. Tep nay **KHONG duoc sua** sau khi co so.
Muc tieu: tim **feature nao trong 33 lam p15 cua LIVE bi CUT DUOI** (live max ~2,30% vs DEV ~12,26%) ⇒
nguyen nhan goc khien gate khong bao gio pass (shadow dong bang) va khien **moi nguong hieu chuan tren DEV
vo hieu voi live** (tiep noi `docs/result/RESULT_P15_SOURCE.md` muc 4, gia thuyet (iii) "pipeline feature khac").

## 0. Nguon du lieu

| | duong dan | ghi chu |
|---|---|---|
| LIVE shadow Oracle | `/home/ubuntu/shadow_c3/app/feat_dump/feat_dump_*.csv.gz` | 36 cot = `ts,symbol` + 33 feat + `p15_out` |
| LIVE 242 | `/home/chuyennd/java/v_t_m/feat_dump/feat_dump_*.csv.gz` | doc qua ssh read-only |
| DEV export | `~/claudedata/gate15m_v2_full.csv` | 2.846.462 dong, ts 2021-01-01 → 2026-06-01, cot: `timestamp` + 33 feat (`volatilityRegime`, `label_*` la cot phu) |

⚠️ Thu tu cot CSV DEV **KHAC** live (`basket*` dung TRUOC `fundingRate*` o DEV; nguoc o live) ⇒ **align theo TEN**,
khong theo vi tri. DEV **khong co cot `symbol`** ⇒ symbol DEV = `--anchor` (BTCUSDT).

Ghi chu LOGISTIC da biet truoc khi do (khong phai ket qua): dump mo 08:41 (shadow) / 08:46 (242) ngay 2026-09-28,
`LIVE_FEAT_DUMP=3000`, toc do ghi rat cham ⇒ **du kien so dong nho**.

## 1. Gia thuyet

- **H_cut (chinh):** mot vai feature trong 33, o duong LIVE, bi **kep/gia tri bien mat o vung cao** (clip, sai
  don vi/scale, hoac nguon du lieu Aerospike tra ve dai gia tri hep) ⇒ dau vao model bi nen ⇒ p15 khong bao gio
  vuot nguong ⇒ gate `n_pass=0` tat dinh. Du bao: feature nghi pham co **duoi tren bi cat** so voi DEV
  (max live << p99 DEV; qmax_rel lon; hang so/std ~0; NaN-rate cao).
- **H_src:** lech do **nguon du lieu** (Aerospike ticker/breadth/funding thieu) — du bao NaN-rate cao hoac
  feature hang so tai gia tri trung tinh (0).
- **H_formula:** lech do **cong thuc tinh** o duong live — du bao lech **he thong mot chieu** (mean/scale),
  nhung hinh dang (rank) van tuong quan.
- **H0:** khong feature nao lech ⇒ gia thuyet "feature cut duoi" SAI, phai tim nguyen nhan khac (model/store goc).

## 2. Cach align + so sanh (chot truoc)

1. **PRIMARY — cap khop `(ts, symbol)` chinh xac.** Bao cao so cap khop. Neu **0 cap khop** (du kien cao, vi DEV
   ket thuc 2026-06-01 con live 2026-09-28) ⇒ ghi ro **khong the so cap**, chuyen FALLBACK.
2. **FALLBACK (chot truoc) — so PHAN BO tren cung ten feature, hai cua so DEV:**
   - `DEV_recent` = 2026-03-01 → 2026-06-01 (90 ngay cuoi cua export, gan live nhat ve che do thi truong).
   - `DEV_w20` = 2025-10-01 → 2026-06-01 (cua so fold_20 dung cho train/test gan nhat).
   So sanh thong ke mo ta live vs DEV; **KHONG** dung fallback nay de ket luan cung, chi de **xep hang nghi pham**.
3. **KIEM INSTRUMENT (khong can DEV):**
   - (a) `p15_out` cua live vs phan bo live da do (`RESULT_P15_SOURCE.md`: p50 0,910 / p99 1,770 / max 2,300).
   - (b) 4 feature thoi gian `hourOfDay/dayOfWeek/weekOfMonth/monthOfYear` **PHAI khop** ham xac dinh tu `ts`
     (gio theo `user.timezone=Asia/Ho_Chi_Minh`; tuan/thang) — **sai ⇒ instrument ghi nham vector**.
   - (c) `p15_out == fold_20(live 33 feat)` bang `onnxruntime` local (nhe, chi ~40 dong). Khop ⇒ dump ghi DUNG
     gia tri model xuat ⇒ loi khong o buoc dump; lech ⇒ loi o buoc ghi/duong p15.
   - (d) feature hang so (std = 0) tren toan bo live trong khi DEV co phuong sai.

## 3. Chi so doi chieu (chot truoc, moi feature)

`n`, `mean`, `std`, `p5`, `p50`, `p95`, `max`, `NaN-rate`, `rank-corr (spearman)` (chi khi co cap khop).
Suy ra: `shift_sd = |mean_live-mean_dev| / std_dev`; `qmax_rel = max|q_live-q_dev| / IQR_dev`;
`tail_ratio = max_live / p99_dev`.

**NGUONG NGHI NGO (chot truoc):**
- `shift_sd > 0.5` ⇒ lech vi tri.
- `qmax_rel > 1.0` ⇒ lech phan vi (nang).
- `spearman < 0.9` (khi co cap) ⇒ lech hinh dang.
- `NaN-rate_live > 0.01` ⇒ thieu du lieu (nghi H_src).
- `std_live == 0` (hang so) ⇒ feature chet.
- `tail_ratio < 0.5` ⇒ **nghi cut duoi** (duoi tren live hep hon han DEV).
- `tail_ratio > 1.5` ⇒ live no hon DEV (nguoc lai).

`score = shift_sd + 0.5*qmax_rel + (0 neu spearman>0.99 khac 1.0)` (dung lai ham cua
`research/analysis/feat_diff_live_vs_dev.py`). Bang xep hang nghi pham = sort `score` giam dan.

## 4. LUAT KET LUAN (chot truoc)

1. Neu **co cap khop >= 1** ⇒ dung PRIMARY; `spearman` + `shift_sd` la bang chung chinh.
2. Neu **khong co cap khop** ⇒ ket qua la **PASS 1 / chi de nghi, KHONG ket luan cung** (mau nho + so phan bo).
3. Neu **< 200 dong live** ⇒ **khai RO "chua du"**, khong ket luan cung du feature co lech ro.
4. **H_cut duoc coi la KHOP** khi: >=1 feature co `tail_ratio < 0.5` (hoac hang so) **VA** co ly do co che
   (clip/scale/nguon) **VA** p15 live khong cham toi nguong gate (2,947%) trong khi DEV co.
5. Neu tat ca 33 feature deu `tail_ratio >= 0.5` ⇒ **H_cut KHONG duoc ung ho** ⇒ nghi (ii) model/store goc.
6. Moi ket luan cung chi co sau khi **nguon khop** (xem `RESULT_P15_SOURCE.md` §4.4): hieu chuan lai **chi co y
   nghia SAU khi** nguon live ≈ nguon DEV. Pass 1 nay **khong** hieu chuan lai, **khong** deploy.

## 5. Ranh gioi (CUNG)

- **CHI DOC** tren Oracle + 242 (khong ghi/sua/restart/kill; khong doc key). Copy file NHO ve Oracle de phan tich.
- **KHONG** chay Java / sim / WFO. Python nhe local (pandas/onnxruntime) duoc phep.
- **KHONG** push du lieu len git (chi code/doc; khong commit `*.csv.gz`/parquet). `git push` cho code/doc duoc phep.
- Don file tam sau khi dung (`df -h /` = 93%). Output tool **rat nho** (<= ~60 dong/file).
- Cac tham so fit deu `<= 2025-12-31`; 2026 **chi chan doan**.

## 6. Ket qua ghi o

`docs/result/RESULT_FEAT_DIFF_PASS1.md` (+ `RESULT_FEAT_DIFF_PASS1.json`). Muc "bo / ly do" khai RO.
