# G015X26_PROVENANCE — phan phoi gate THAT cua C2b (DONG BANG)

Sinh luc: 2026-09-04 (Oracle). VIEC BAO TON, KHONG train / KHONG rebuild / KHONG doi model.
Chi: hash 16 file + backup off-disk + ghi provenance.

## 0. G015x26 la gi trong C2b

`predwf_G015x26/` la **phan phoi gate P(win) per-tick** ma cau hinh tot nhat C2b dang THAT SU chay.
Duong dan (da xac minh bang file:line):

1. `profiles/c2b.properties:23` va `profiles/c2b_min.properties:23`:
   `WFO_FUNDING_PRED_DIR=/home/ubuntu/predwf_map_s1a2` (bins S1, xem `docs/S1_PROVENANCE.md`).
2. `predwf_map_s1a2` sinh boi `research/pipeline/build_map.py`. Dong 28:
   `glob("/home/ubuntu/claudedata/predwf_G015x26/predict_wf_*.bin")` la INPUT.
3. build_map GIU NGUYEN multiset phan phoi P(win) trong tung tick cua G015x26 (gate khong doi),
   chi doi coin nao nhan gia tri nao theo thu hang S1. => **G015x26 CHINH LA phan phoi gate cua C2b.**

## 1. Artifact DONG BANG — KHONG tai lap duoc

- G015x26 train tren ban export Tool1 2021 **da mat**. bins mtime **2026-08-14 15:03-15:05**, TRUOC
  khi export 2021 bi sinh lai 2026-08-16 (xem `docs/G015REBUILD_RESULT.md`). => khong the tai lap
  byte-identical, va khong the tai lap dung ca phan phoi. Day la **output cua mot seed da mat** —
  giu duoc, khong dung lai duoc.
- Phan biet ro voi **`predwf_G015_v2/`** (ban tai lap, rho=0.18991, hash file dau `aed0732c...`):
  v2 la ban tai lap duoc dung cho phan tich / tuong lai, **KHONG phai** cai dang deploy.
  G015x26 (file dau `199ad42e...`) moi la cai deploy that.

**CANH BAO:** ai lo xoa `predwf_G015x26/` la **mat gate cua C2b VINH VIEN**, tru khi phuc hoi tu
backup Kaggle o muc 3 duoi. KHONG co source de dung lai.

## 2. Manifest — sha256 + so record (16/16 file)

Co-located: `/home/ubuntu/claudedata/predwf_G015x26/MANIFEST.sha256`.
Dinh dang record: 26 B/rec big-endian `[ts:int64][sym:int16][p0,p1,p2,p3:float32]`; `rec = filesize/26`.

| File | rec | sha256 |
|---|---|---|
| predict_wf_20220101.bin | 1,123,854 | `199ad42e6682dc257e1754737944823ca271a3e16b7e67deb1452827e88acc5a` |
| predict_wf_20220401.bin | 1,172,010 | `5f89f6dcb2fd40852916133b5559a0d3367f7bec46b6e49c0227d16be470b255` |
| predict_wf_20220701.bin | 1,188,418 | `998d5b0c37aafdf6131079bdc99ce2367c45df06bb9635ead4cabdf078958bbf` |
| predict_wf_20221001.bin | 1,242,626 | `efd240f6261b2548e6f57988202f5f56b41dde35b18937f31aecb4223450bea6` |
| predict_wf_20230101.bin | 1,302,607 | `8534693f77ddca2c74d235583f38d245b5eaa0067471c578998892b4b0613ff8` |
| predict_wf_20230401.bin | 1,524,605 | `36939bfce9e33d67ea41730608e67c6019736ab20cfa931c9aa6208ffc4ecbb8` |
| predict_wf_20230701.bin | 1,671,614 | `a389367dc34cfb8afef5c0c8a5b86ae5ab67862f0d44d50c1df68c6005cf49cd` |
| predict_wf_20231001.bin | 1,912,959 | `2fcd7b95e1887effc401359889695e770ba02841f3eb67ca23d5f3386d43329f` |
| predict_wf_20240101.bin | 2,140,992 | `e5a684f4132996ea47cc2341960cf0fd3a5dc0262c65368bac5cf63a4117f131` |
| predict_wf_20240401.bin | 2,256,504 | `d76d5f929df9571af8c1674a4b27f771c74d5c800e15088b735334cff11d60ad` |
| predict_wf_20240701.bin | 2,362,741 | `a21f81fe6c2aa4853ff943e0b8564b6cf388a6cb1ab3f6aa7fe38b79b2a46008` |
| predict_wf_20241001.bin | 2,719,452 | `108eb9a131976780940eadb8f5c344cf27c3fca3036b0556892d0b9e13f3db53` |
| predict_wf_20250101.bin | 3,056,303 | `b33bcce028a77fbc76800bd8baddc5a7dc3cc19028e27d5522bbcef4f7d71b53` |
| predict_wf_20250401.bin | 3,535,785 | `f59047c99fcbd6a43566a30c44c3089cff4542bba13c13c04e23db5b986a9029` |
| predict_wf_20250701.bin | 4,078,299 | `8e7d1154fbc72665f38a23c8f4254de3b4c28f1b736c88c3374ee1245ff176c7` |
| predict_wf_20251001.bin | 4,517,610 | `e03f0e58ed35f86929059cc349ceb18121df8b48ba3035293d7e6c9140da283a` |

TONG: 16 file, `bytes=930965854` (~888 MiB). Cac quy 2024Q3/Q4 va 2025/2026 (VAL/HOLDOUT) chi
DUOC HASH + BACKUP de bao ton artifact; KHONG doc gia tri de danh gia hieu qua.

## 3. Backup off-disk — Kaggle dataset PRIVATE

- Slug: **`chuyendinh/predwf-g015x26-gate`** (version 1, PRIVATE), URL
  `https://www.kaggle.com/datasets/chuyendinh/predwf-g015x26-gate`.
- Noi dung: 16 file `predict_wf_*.bin` + `MANIFEST.sha256` (co-located trong backup).
- Cach upload: hardlink 16 file + manifest sang stage (cung fs `/dev/sda1`, KHONG nhan doi dia),
  `kaggle datasets create --dir-mode skip`. Dia truoc/sau: 16G avail (khong tut).
- **VERIFY tai-lai-so-hash (KHONG tin trang thai "ready" suong):** tai lai
  `predict_wf_20220101.bin` tu Kaggle -> sha256 =
  `199ad42e6682dc257e1754737944823ca271a3e16b7e67deb1452827e88acc5a` == manifest. **PASS.**

## 4. Rang buoc da tuan

KHONG train / java / backtest / rebuild. Chi doc + them `MANIFEST.sha256` vao trong
`predwf_G015x26/` (khong sua/xoa/ghi de file bin nao). KHONG cham live/shadow, VAL/HOLDOUT (ve
danh gia). Backup toan bo 16 file la BAO TON artifact, khong phai danh gia.
