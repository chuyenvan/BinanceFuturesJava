# BINS_MANIFEST — predwf_map_s1a2 + pred_s1a2.parquet

Sinh luc: 2026-09-03 (Oracle). Ly do ton tai: bins la **394 MB, khong commit vao git**, va
dia Oracle dang **91% day (19 GB trong / 194 GB)**. Neu bins bi xoa thi C2b (equity 60390)
KHONG the tai lap va toan bo edge S1 mat. File nay + ban sao Kaggle la luoi an toan.

## 1. Dung luong

| Duong dan | Byte | Nguoi doc thay |
|---|---|---|
| `/home/ubuntu/predwf_map_s1a2/` (10 file `.bin`) | **403,940,914** (tong 10 file; `du -sb` = 403,945,010 vi cong 4096 B inode thu muc) | 386 MiB / 394 MB |
| `/home/ubuntu/ledger/pred_s1a2.parquet` | **7,401,294** | 7.1 MiB / 7.4 MB |
| **Tong** | **411,342,208** | **~392 MiB / 411 MB** |

Duoi nguong 20 GB => duoc phep upload (khong phai dung de bao so).

## 2. Bins — `/home/ubuntu/predwf_map_s1a2/`

Dinh dang: ban ghi 26 byte big-endian `[ts:int64][symId:int16][p4h,p12h,p24h,p72h:float32]`.
Engine dung slot `p0` (= p4h) voi `WFO_SEL_HORIZON_IDX=0`; `score = 1 - P(win)` (dao dau).
Ngay sinh: **2026-09-02 22:50:32..37 (+0700)**.

| File | Byte | Ban ghi | sha256 | md5 | ts range (ms) | span |
|---|---|---|---|---|---|---|
| predict_wf_20220101.bin | 29,220,204 | 1,123,854 | `beb9b1ad87920837c37a4fbad987d7266a8fdc65e872901f23bff6e877b9fca4` | `a71cb93cfc580442418320eb0c9f8d04` | 1640970000000..1648745100000 | 89d |
| predict_wf_20220401.bin | 30,472,260 | 1,172,010 | `46d74f5af24408e29c4c89a5b0578e6b3b510ebd49341746368cbd88d1e54703` | `3cedf730b1fdff2bf3b3272a212ffe2d` | 1648746000000..1656607500000 | 90d |
| predict_wf_20220701.bin | 30,898,868 | 1,188,418 | `bba6d88bb55475d2b27524a8745a9cd1cd5e1c3a81246f98ac43749a928d8de6` | `e723614e9df757e1437408f2b199a780` | 1656608400000..1664556300000 | 91d |
| predict_wf_20221001.bin | 32,308,276 | 1,242,626 | `52de4cf735a16ff3f35c7db01278ffa6740defccc28817d48c2f46af50d3b3c8` | `6cf85dffa9a94aa8d3fd4ed73940b09c` | 1664557200000..1672505100000 | 91d |
| predict_wf_20230101.bin | 33,867,782 | 1,302,607 | `5fbeeb76e766885a9f25003937f79aa5f97fe56fbe46d4be5c6bcaa9b44b21a1` | `942ea9e3d579403fd2e267922f684aa9` | 1672506000000..1680281100000 | 89d |
| predict_wf_20230401.bin | 39,639,730 | 1,524,605 | `9dc70e5173d55e56f07b5e2d8dc57eccee8368887c2d54b819cabf146306697a` | `f801c640ab68cc07c757b1d43112cb08` | 1680282000000..1688143500000 | 90d |
| predict_wf_20230701.bin | 43,461,964 | 1,671,614 | `f34966245a911853967e8028bf54b4be294ba150ece54f16ff8e93cc3e4ee264` | `1e062b4ae5816f3f6cfc0ff2b6e5949d` | 1688144400000..1696092300000 | 91d |
| predict_wf_20231001.bin | 49,736,934 | 1,912,959 | `48d51834bb718cac1b4b089a33ebd953bbce2bb83348c7a2f62fb083f5e55005` | `2b766454030610e148f38fc951d73a70` | 1696093200000..1704041100000 | 91d |
| predict_wf_20240101.bin | 55,665,792 | 2,140,992 | `ac1fadf2c90836a8b6f13f470910785504de111e3d7449e9a3990ac60a148f08` | `53e100a0edac33701795f638fa1590c5` | 1704042000000..1711903500000 | 90d |
| predict_wf_20240401.bin | 58,669,104 | 2,256,504 | `82d1b979cabda8aa3a5ee94ccdec95a00483150d93657a33189ceaa9f733e6ae` | `1a717a07615d37a777356d87c412ef68` | 1711904400000..1719765900000 | 90d |
| **TONG** | **403,940,914** | **15,536,189** | — | — | 1640970000000..1719765900000 | 10 fold |

- Cot `md5` doc tu `devrun/logs/build_min.out` (manifest ma `WfoDataset.export` da tu stamp) —
  bang chung doc lap rang bins tren dia dung la bins ma dataset C2b duoc build tu do.
- 10 fold **ROI NHAU** (disjoint), fold dai nhat 91 ngay < nguong 100 ngay =>
  `buildFundingFromWfFiles` khong bao `LEAK-SUSPECT`.
- KHONG co fold `20240701` / `20241001` => bins nay khong the cham VALIDATION.

## 2b. sha256 GOP cua ca bo bins (dau vet ma moi run tu khai)

    bins.sha256 = 0f8721558fbd87ef0bca8d2507b6eb0ed394efd746f59d4bc024e68b461d86ec
    bins.sha256_16 = 0f8721558fbd87ef
    bins.files = 10   bins.bytes = 403940914

Cach tinh: sha256 tren noi dung NOI TIEP cua moi `predict_wf_*.bin` sort theo ten
(`com.binance.chuyennd.tradecore.BinsProvenance.sha256`). Tu 2026-09-03:

- `DumpConfig` in dong `bins.dir= bins.files= bins.bytes= bins.sha256_16= bins.sha256=`
- `WfoDataset.export` stamp `binsSha256=` vao `manifest.txt` cua dataset
  (bang chung: `devrun/logs/build_C2b_PIN.out` -> `binsSha256=0f8721558fbd87ef0bca...`)
- `CONFIG_HASH` **doi** khi doi bins-dir: co bins = `6f5ba81442f7e80c`,
  khong khai bao bins = `202118d9d1623cb0`. Truoc 2026-09-03 doi selector ma CONFIG_HASH
  KHONG he doi.
- Ban than `bins.sha256` **KHONG** nam trong `CONFIG_HASH` (co y): node Kaggle chi nhan
  dataset da build, khong co bins tren dia => neu cho vao thi CONFIG_HASH cua CUNG mot
  cau hinh se khac nhau giua Oracle va Kaggle.

## 2c. CONG NGHIEM THU BYTE-IDENTITY (2026-09-03)

Sau khi pin bins vao profile + bo fallback Aerospike, chay LAI C2b tren DEV:

    bash tools/run_c2b_dev.sh            # profile=profiles/c2b.properties, tag=C2b_PIN
    cmp -s <(tail -n +2 devrun/C2b_PIN/storage/printDone.csv) \
           <(tail -n +2 devrun/C2b/storage/printDone.csv)

| | |
|---|---|
| Ket qua | **PASS — BYTE-IDENTICAL** |
| equity cuoi `C2b_PIN` | **b:60390**  `done:147/970/970` |
| equity cuoi baseline `C2b` | **b:60390**  `done:147/970/970` |
| md5 `printDone.csv` (ca hai) | `8f7afdfb27b15f5b6d4c886700def93c` |
| `md5_funding` cua dataset | `7b9ba20f7a5b49ec3d5aaafed60d45be` — **giong y** ban build cu (`build_min.out`) |
| PROFILE_HASH `c2b` | `1bc17b5075511263` -> **`7fd2895a1e7fefe0`** (22 -> 23 key) |
| PROFILE_HASH `c2b_min` | `531b4ae7b4b64885` -> **`a2f859b2463108fe`** (15 -> 16 key) |
| CONFIG_HASH | `28f7c17882b0b339` -> **`6f5ba81442f7e80c`** |
| jar | md5 `99d96825428f` |

Kiem fail cung (`ExportWfoDataset` khong co bins): **rc=1**, thong bao
`java.io.IOException: THIEU BINS SELECTOR: WFO_FUNDING_PRED_DIR khong duoc khai bao...`
(truoc day: `LOG.warn` roi fallback Aerospike, rc=0, so KHAC ma khong bao loi).

## 3. `pred_s1a2.parquet` (dau vao cua build_map)

| | |
|---|---|
| Duong dan | `/home/ubuntu/ledger/pred_s1a2.parquet` |
| Byte | 7,401,294 |
| sha256 | `bab6e88f792dd42c4c2c1b0dc0c396564c0685cafe5638e493edae0bcad9d311` |
| Ngay sinh | 2026-09-02 22:49:41 (+0700) |
| Cot | `ts` (int64 ms), `sym` (int64 symId), `score` (float, THAP = tot) |
| So dong | **774,270** |
| So tick 15m | **4,595** |
| So symbol | **288** |
| `ts` min..max | 1640971800000 .. 1719261900000 (2022-01-01 .. 2024-06-25 GMT+7) |

## 4. Provenance — code nao sinh ra chung

| | |
|---|---|
| Commit repo luc bins duoc sinh | **`e2c8fde`** ("feat(live/pin): LIVE_LOSER_TIME_STOP_HOURS + EXCHANGE_INFO_PATH env override") |
| Bang chung | `dev_map2.sh:18` dat `WFO_CODE_SHA=e2c8fde-maps1a2`; `git log --until='2026-09-02 23:00 +0700' -1` = `e2c8fde` |
| Script sinh bins | `build_map.py s1a2 /home/ubuntu/predwf_map_s1a2` (buoc 4, `research/pipeline/README.md`) |
| Script sinh pred | `s1_rank.py 2` (buoc 3) |
| Jar dung cho C2b | `target/binance-java-sdk-1.2.4.jar` |

### sha256 script: ban DA CHAY (tren `/home/ubuntu/featv2/`) vs ban trong repo

| Script | sha256 ban DA CHAY | sha256 ban repo | Khac vi |
|---|---|---|---|
| `ledger.py` | `357adcbdda6b75926b9c5b947e91f22273e10d29e096058b8034abd27ac06d72` | giong y | — |
| `ledger3.py` | `f935aa939ffba87c1fd99d4ce89f12cacc01631b215134bcbb9ed03cb2d590df` | giong y | — |
| `admit_rate.py` | `da4344092b0743fad8ddbb2b828cbe2a888e72601399d6eb26b705cd669a776e` | giong y | — |
| `feat_v2_build.py` | `b230b6b1c9c057549d679e243519cab55a2fc38f343e5a8e5fa518b3325f0271` | khac | print -> logging |
| `s1_rank.py` | `e61120940109bb599bfffcf2979766809406489c16a84baa3324f6f675a9b7b3` | khac | print -> logging |
| `build_map.py` | `f5323b1f3e3a0c0f04c9ea2c132a4f29baaf71df81eabcef2e398739945619fd` | khac | print -> logging |
| `path_labels.py` | `33f009c432cb562aa8aed3566a8c9968451d70b66e0232409eeecb2d2666b8fe` | khac | print -> logging |
| `label_pick.py` | `70c45b6112e8e0d1f12d8350fb8adb905abeb4bd4ebdb6802755ed623fbe27ad` | khac | print -> logging |
| `s1_eval.py` | `5fef9c050fa3efcb150007ef2fcd9296d76648c51a6d76c54b37bea585b066c6` | khac | print -> logging |

`ledger.py.bak` / `ledger3.py.bak` / `admit_rate.py.bak` tren dia la ban TRUOC khi doi sang
`logging` (2026-09-03 17:50) — khong commit, chi ghi nhan la chung ton tai.

## 5. SAO LUU NGOAI MAY — Kaggle dataset PRIVATE

| | |
|---|---|
| **Slug** | **`chuyendinh/predwf-map-s1a2-bins`** |
| URL | `https://www.kaggle.com/datasets/chuyendinh/predwf-map-s1a2-bins` |
| **Version** | **1** (lan tao dau tien) |
| Trang thai | `kaggle datasets status` = **`ready`** |
| Che do | **PRIVATE** (`kaggle datasets create` mac dinh private; API xac nhan "Your private Dataset is being created") |
| Ngay upload | 2026-09-03 11:18 UTC |
| Account | `chuyendinh` |
| So file | 11 (10 bins + `pred_s1a2.parquet`) |
| Tong byte theo Kaggle | 411,342,208 — **khop tung file voi bang muc 2 va 3** |

Lenh da chay:

    mkdir -p /home/ubuntu/kbak/predwf_map_s1a2
    # hardlink de khong ton them 400MB tren dia 91% day
    ln /home/ubuntu/predwf_map_s1a2/predict_wf_*.bin /home/ubuntu/kbak/predwf_map_s1a2/
    ln /home/ubuntu/ledger/pred_s1a2.parquet        /home/ubuntu/kbak/predwf_map_s1a2/
    # dataset-metadata.json: id = chuyendinh/predwf-map-s1a2-bins
    /home/ubuntu/.local/bin/kaggle datasets create -p /home/ubuntu/kbak/predwf_map_s1a2 -r skip

Lenh lay lai khi mat bins:

    /home/ubuntu/.local/bin/kaggle datasets download -d chuyendinh/predwf-map-s1a2-bins \
        -p /home/ubuntu/predwf_map_s1a2 --unzip
    cd /home/ubuntu/predwf_map_s1a2 && sha256sum -c BINS_SHA256   # doi chieu bang muc 2

Ban kiem tra dung tung file: `kaggle datasets files chuyendinh/predwf-map-s1a2-bins` — 11 dong,
byte tung file khop 100% voi bang muc 2 va 3.

## 6. Kiem tra nhanh (chay bat cu luc nao)

    cd /home/ubuntu/predwf_map_s1a2 && sha256sum predict_wf_*.bin
    sha256sum /home/ubuntu/ledger/pred_s1a2.parquet

Bat ky sha256 nao lech bang muc 2/3 => bins **KHONG** phai bins cua C2b 60390. DUNG, dung chay
backtest, lay lai tu Kaggle version 1.

Tu 2026-09-03 moi run cung TU KHAI bins: `DumpConfig` in `bins.sha256_16` va
`WfoDataset.export` stamp `binsSha256` vao `manifest.txt` cua dataset. Xem
`docs/C2B_SPEC.md` va `research/pipeline/README.md` muc 0.
