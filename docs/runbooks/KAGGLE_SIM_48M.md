# KAGGLE_SIM_48M — chay T170 cua so 48/54 thang tren Kaggle + parity byte-identical

Lam 2026-09-22 (executor Sonnet). Muc tieu vong nay CHI la ha tang + cong parity cho **T170**
(cua so DEV thuc te 2021-07-01..2025-12-31, ~54 thang/1,645 ngay — goi tat "48 thang" theo
brief cua Uni). KHONG chay bien the BRC trong task nay (de MASTER giao rieng sau khi parity
xac nhan). Tien le 912-ngay (2022-01-01..2024-06-30) da co san o `docs/runbooks/KAGGLE_SIM.md`; file
nay ghi tiep phan MO RONG len cua so day du cua T170.

## 0. Ket qua tom tat

| | |
|---|---|
| Profile | `x1_gs_t170` (incumbent, `PROFILE_HASH` Oracle goc `0d0fa22158b1d8c0`) |
| Cua so | `TIME_RUN=20210701` .. `SIM_END_DATE=20251231` (1,645 ngay lich, 1,089 lenh) |
| Bundle Kaggle | `chuyendinh/sim-x1-2021-bundle` (private, moi tao 2026-09-22, 25 file, ~5.3GB) |
| Kernel | `chuyendinh/sim-t170-x1-2021` |
| **Oracle reference (`X1_GS_T170_2021`)** | `equity_final=111070` `n_trades=1089` md5 `printDone.csv` = **`efb793e2468ca3a7318da0f0ad23d4fc`** |
| **Kaggle (`t170-x1-2021`)** | `equity_final=111070` `n_trades=1089` md5 `printDone.csv` = **`efb793e2468ca3a7318da0f0ad23d4fc`** |
| **PARITY** | **`diff` = 0 dong, md5 KHOP TUNG BYTE — PASS** |
| Wall-clock | Oracle JVM 771s · Kaggle JVM 1216.9s (**1.58x** cham hon) · tong kernel (push→COMPLETE) ~1228s (~20.5') |
| Symbol Mapper | 863 symbols (>= guard 800) ca hai ben |
| Slot dung | 1/5 (con 4 slot ranh cho vong sau) |
| Chi phi | 0 (Kaggle CPU kernel khong tinh quota) |

**KET LUAN: GO.** Kaggle sim T170 tren cua so day du (2021-07-01..2025-12-31) la
**byte-identical** voi Oracle. Tu nay so Kaggle cho T170/X1 (voi bundle nay) dung duoc TRUC
TIEP lam so-sanh Oracle-tuong-duong, KHONG can chay lai baseline rieng tren Kaggle. Luu y:
ket luan nay CHI ap dung cho profile/cua so da do (`x1_gs_t170`, dataset `wfo_ds_x1_2021`
build 2026-09-12) — bien the moi (BRC hay cua so khac) van phai do lai parity truoc khi tin,
theo dung luat da lap o `docs/runbooks/KAGGLE_PARITY.md`/`docs/result/RESULT_S1_DETERMINISM.md` (Oracle=ARM64
vs Kaggle=x86_64 lech that neu la S1/XGBoost — nhung SIM JAVA (khong dung xgboost o luc chay)
da duoc do la khong lech, dung y nhu tien le 912-ngay).

## 1. Sua `tools/kaggle_sim.py` (commit `00b60a9`, branch `module`, CHUA push)

Truoc khi sua, `TICKER_DS` (6 dataset: 2022/2023/2024h1/2024h2/2025h1/2025h2) da CO trong repo
tu commit truoc (khong phai "chua wire" nhu AGENT_RUNBOOK cu 2026-09-06 con ghi) — nhung van
**THIEU nua dau 2021** (T170 bat dau tu 2021-07-01, khong phai 2022-01-01). Kiem tra thuc te
bang KaggleApi (`dataset_list_files` + phan trang `page_token`, 2026-09-22):

| dataset | so file | khoang ngay |
|---|---:|---|
| `wfo-ticker-2021` | 365 | 2021-01-01..2021-12-31 |
| `wfo-ticker-2022` | 365 | 2022-01-01..2022-12-31 |
| `wfo-ticker-2023` | 365 | 2023-01-01..2023-12-31 |
| `wfo-ticker-2024h1` | 182 | 2024-01-01..2024-06-30 |
| `wfo-ticker-2024h2` | 184 | 2024-07-01..2024-12-31 |
| `wfo-ticker-2025h1` | 181 | 2025-01-01..2025-06-30 |
| `wfo-ticker-2025h2` | 184 | 2025-07-01..2025-12-31 |
| **TONG** | **1,826** | **2021-01-01..2025-12-31, KHONG thieu ngay nao** |

Da sua:
1. Them `chuyendinh/wfo-ticker-2021` vao `TICKER_DS` (giu nguyen 6 dataset cu).
2. `TICKER_MIN_DAYS` 1461 → **1826** (tong CA 7 dataset — dung quy uoc cu: hang so nay la
   tong so file cua toan bo `TICKER_DS`, khong phai so ngay rieng cua 1 cua so; run cua so
   ngan hon van truyen `ticker_min_days=` nho hon qua `submit()`).
3. Them tham so `submit(..., bundle_ds=<ten dataset>)` de doi bundle du lieu chinh sang
   dataset KHAC `BUNDLE_DS` (`sim-c2b-bundle`) ma khong sua hang so module — dung de tro sang
   `sim-x1-2021-bundle` cho T170 ma khong dung chung bundle voi cac job `c2b_min` khac.

Verify tren Oracle (`python3 -m py_compile` + import truc tiep): `TICKER_MIN_DAYS=1826`,
`len(TICKER_DS)=7`, `BUNDLE_DS` khong doi. Khong dong nao trong `KERNEL_TEMPLATE` (phan sinh ra
code chay TREN Kaggle) bi sua — chi doi hang so module + them 1 tham so tuy chon o `submit()`.

## 2. Bundle `sim-x1-2021-bundle` (moi, 2026-09-22)

Stage tai `/home/ubuntu/simbundle_x1_t170` (hardlink, khong ton them dia — theo dung co che
`docs/runbooks/KAGGLE_SIM.md` §"Stage lai bundle"). 25 file, ~5.3GB:

| file | nguon Oracle | ghi chu |
|---|---|---|
| `sim.jar` | `target/binance-java-sdk-1.2.4.jar` (HEAD `ba3d7ba`, build 2026-09-21 17:50) | 95MB |
| `config.properties` | `configs/sim_dev_file_2021.properties`, sua 1 dong `AEROSPIKE_HOST_226` 127.0.0.1→161.118.212.3 | `TICKER_SOURCE=file`, `TIME_RUN=20210701` co san |
| `prof_x1_gs_t170.properties` | `profiles/x1_gs_t170.properties` (khong sua) | |
| `exchange_info_pin.json` | `/home/ubuntu/java/exchange_info_pin.json` | 297KB |
| `market.bin`/`pred.bin`/`funding.bin`/`manifest.txt` | `/home/ubuntu/wfo_ds_x1_2021/` | 49MB/38MB/**4.14GB**/3KB, `leakFreeFrom=2021-07-01` |
| `predict_wf_*.bin` x16 + `BINS_SHA256` | `/home/ubuntu/predwf_map_s1a2_x1/` | 888MB — CHI de thoa man guard file-exists cua kernel (bins THAT da nam trong `funding.bin` tu luc build dataset, xem `docs/runbooks/KAGGLE_SIM.md` §6 — doi thu muc bins KHONG doi ket qua sim) |

Tao dataset moi qua `KaggleApi().dataset_create_new(folder=..., public=False, dir_mode="skip")`
(khong dung `dataset_create_version` vi day la dataset MOI, khac han `sim-c2b-bundle`). Verify
sau upload: `dataset_list_files` tra dung 25 file, kich thuoc TUNG file khop byte-for-byte voi
file nguon tren Oracle (vd `funding.bin` 4,446,783,456 bytes ca hai ben).

## 3. Chay T170 tren Kaggle

```python
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks
ks.free_slots()   # 5 (rang truoc khi chay)
ref = ks.submit("t170-x1-2021", "x1_gs_t170", {}, bundle_ds="sim-x1-2021-bundle",
                sim_end_date="20251231", code_sha="00b60a9")
ks.wait([ref]); out = ks.fetch("t170-x1-2021")
```

Kernel log xac nhan wire dung: `ticker=1826` (== TICKER_MIN_DAYS, khong thieu file nao),
`jar=`/`ds=`/`predwf=` deu tro dung vao `sim-x1-2021-bundle`. Khong can `enable_internet`
rieng — `submit()` mac dinh `True`; `SimpleSymbolMapper` doc Aerospike qua
`AEROSPIKE_HOST_226=161.118.212.3` (public IP Oracle, container `aerospike-wfo`, cong 3222 mo
`0.0.0.0`) — xac nhan ket noi duoc ca cuc local (`127.0.0.1:3222`) lan public truoc khi chay.

`result.json`: `java_rc=1` (KHONG phai fail — dung tieu chi RUNBOOK bay #1: `ok=true` vi
`equity_final` + `n_trades>0` co gia tri), `symbol_mapper=863` (>= guard 800).

## 4. CONG PARITY

```
md5sum /home/ubuntu/kaggle_sim/out/t170-x1-2021/storage/printDone.csv \
       /home/ubuntu/java/devrun/X1_GS_T170_2021/storage/printDone.csv
efb793e2468ca3a7318da0f0ad23d4fc  .../t170-x1-2021/storage/printDone.csv   (Kaggle)
efb793e2468ca3a7318da0f0ad23d4fc  .../X1_GS_T170_2021/storage/printDone.csv (Oracle, tham chieu Uni giao)

diff ... | wc -l   => 0
```

**PASS byte-identical.** Oracle reference (`X1_GS_T170_2021`) ban than da chay voi
`TICKER_SOURCE=file` (kiem trong `config.properties` cua devrun do) — nen day la so sanh
file-vs-file dung nghia, KHONG dinh phai "neo 60395 vs 60390" (do la lech aerospike-vs-file
cua tien le `c2b_min`/912-ngay, mot profile/cua so khac han, KHONG ap dung truc tiep cho
T170). `PROFILE_HASH` hai ben KHAC nhau nhu du kien (`0d0fa22158b1d8c0` Oracle vs
`38eafebee1dcfa6a` Kaggle, vi `WFO_FUNDING_PRED_DIR` tro vao 2 duong khac nhau) — dung y
canh bao cua `docs/runbooks/KAGGLE_SIM.md` §0.3: **so parity bang md5 `printDone.csv`, KHONG bang
`PROFILE_HASH`.**

=> **GO: dung so Kaggle T170 (bundle `sim-x1-2021-bundle`) lam tuong duong Oracle, khong can
chay baseline rieng cho profile/cua so nay.**

## 5. Tai nguyen / thoi gian (de MASTER uoc luong vong BRC sau)

| | Oracle | Kaggle |
|---|---:|---:|
| JVM sim | 771s | 1216.9s (**1.58x**) |
| RAM | 6.5GB (`-Xmx14g` du) | `-Xmx22g` (Kaggle 31GB/4 core) |
| Tong wall (push→COMPLETE, gom queue+mount+symlink 1826 ticker) | — | ~1228s (~20.5') |
| Slot dung/con lai | 1 JVM (doc quyen) | 1/5 (4 slot con ranh) |
| Chi phi | dien+may | 0 (CPU kernel khong tinh quota) |

Ty le cham hon (1.58x) cao hon tien le 912-ngay (1.29x) — hop ly vi bundle nay lon hon nhieu
(~5.3GB vs ~2.3GB, `funding.bin` rieng 4.14GB) => I/O doc dataset chiem ty trong lon hon tren
Kaggle (dia mang cham hon Oracle local). Neu MASTER can chay N bien the BRC song song, uoc
luong throughput: 5 kernel × (1216.9s/kernel) ≈ **~4x Oracle tuan tu** cho cua so nay (thap
hon 3.9x/5slot cua tien le vi JVM cham hon, nhung van la loi ich chinh: GIAI PHONG hoan toan
Oracle JVM slot, khong con phai dung shadow-c3).

## 6. Khong dung shadow-c3

Toan bo task nay KHONG systemctl/kill/sua gi lien quan `shadow-c3.service` hay
`aerospike-wfo` (container Aerospike-local rieng, khac shadow). Ghi nhan mot su kien KHONG
lien quan: `shadow-c3` tu restart luc 2026-09-22 02:52:47 +07 (`systemd: Scheduled restart
job, restart counter is at 2` — tu than tien trinh, KHONG phai lenh cua agent nay; ung dung co
san 1 thread ten `ThreadAutoRestartProgram` va loi `-2015 IP-whitelist` da biet tu truoc,
`khong chan paper loop` theo memory 2026-09-20). Kernel Kaggle chi doc Aerospike qua cong
3222 (read-only, symbol mapper) — khong tuong tac voi JVM `shadow-c3` (`BinanceOrderTradingManager`,
process rieng). Xac nhan `shadow-c3` van `active (running)` xuyen suot va sau khi task hoan
tat.

## 7. Con lai / vong sau

- Bundle `sim-x1-2021-bundle` hien dung `predwf_map_s1a2_x1` (888M, KHONG phai
  `predwf_map_s1a2_x1_2021` ma `wfo_ds_x1_2021/manifest.txt` ghi la nguon build that —
  KHONG anh huong ket qua vi ly do da neu o muc 2, nhung neu muon `PROFILE_HASH` khop het
  Oracle thi phai doi sang `predwf_map_s1a2_x1_2021` (941M) — chi la my quan, khong bat buoc).
- Chua do throughput 5/5 kernel song song cho bundle nay (moi do 1/5); neu vong BRC can nhieu
  bien the cung luc, nen do truoc mot lan 5 kernel that de xac nhan khong vo tran (dataset
  5.3GB × 5 co the cham mount hon tien le 2.3GB × 5).
- Theo dung brief: KHONG chay bien the BRC trong task nay — de MASTER giao rieng sau khi
  parity da xac nhan GO o tren.
