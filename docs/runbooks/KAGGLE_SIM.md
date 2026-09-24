# KAGGLE_SIM — chay Java sim SONG SONG tren Kaggle CPU kernel

Do that 2026-09-05. API: `tools/kaggle_sim.py`. Doc `docs/runbooks/KAGGLE_RULES.md` truoc (slot, 12h kill,
mount layout) — file nay chi noi phan RIENG cua sim.

## 0. Rui ro / gioi han — doc TRUOC

1. **Neo la 60395, KHONG phai 60390.** Kaggle khong co Aerospike ticker nen sim luon chay
   `TICKER_SOURCE=file` => lech dung 1 lenh/970 (FTT BUY 2022-11-09) so voi `aerospike`.
   Xem `docs/runbooks/KAGGLE_RULES.md` §3e va `docs/analysis/GS_BASELINE_NOTE.md`.
2. **Kernel BAT BUOC `enable_internet=True`.** `SimpleSymbolMapper.init()` VAN doc Aerospike —
   khong co nhanh `TICKER_SOURCE=file` cho symbol mapper. Kernel doc mapper qua
   `AEROSPIKE_HOST_226=161.118.212.3` (Oracle) trong `config.properties` cua dataset.
   **Aerospike Oracle chet => mapper rong => id symbol tu sinh => ket qua LECH AM THAM.**
   `tools/kaggle_sim.py` da cai guard: kernel `exit 2` neu log khong co
   `Loaded Symbol Mapper: N symbols` voi N >= 800 (do thuc: **863**).
3. **`PROFILE_HASH` Kaggle KHAC Oracle** (`8d617ad2b6677b83` vs `a2f859b2463108fe`) vi
   `WFO_FUNDING_PRED_DIR` tro vao mount Kaggle. **Dung md5 `printDone.csv` de so parity,
   KHONG dung `PROFILE_HASH`.**
4. **Dataset `sim-c2b-bundle` la snapshot.** Doi code (`target/*.jar`) hay doi
   `profiles/` thi PHAI `dataset_create_version` lai, khong tu cap nhat.
5. 5 slot CPU / account (dung chung voi MOI job khac); 12h hard kill; dataset moi tao co
   do tre mount vai phut.

## 1. Do thuc 2026-09-05 — parity PASS

Jar `target/binance-java-sdk-1.2.4.jar` tu HEAD `bd20e42`. Profile `c2b_min` (16 key).

| run | moi truong | ticker | equity cuoi | lenh | md5 printDone |
|---|---|---|---|---|---|
| `C2b` | Oracle | aerospike | 60390 | 970 | `8f7afdfb27b15f5b6d4c886700def93c` |
| `KGF_REF` | Oracle | **file** | **60395** | 970 | `910f1aa6f76b5e6797d97a31a7ea5f5a` |
| `sim-parity` | **Kaggle** | **file** | **60395** | 970 | `910f1aa6f76b5e6797d97a31a7ea5f5a` |

- **Kaggle == Oracle+file byte-for-byte** (`diff` = 0 dong).
- Kaggle vs `C2b` (aerospike): **dung 2 dong** = 1 lenh FTT BUY 2022-11-09 (exit
  `20221116 01:01` / PnL -1080.387 thay vi `20221114 11:00` / -1084.846). Dung nhu §3e.

Hai bien the chay cung luc, doi chieu `docs/result/E1_EXIT_RESULT.md` (Oracle + aerospike):

| run | override | equity Kaggle | equity Oracle (E1) | lenh | md5 printDone |
|---|---|---|---|---|---|
| `sim-x96` | `SIM_LOSER_TIME_STOP_HOURS=96` | **62370** | 62370 | 1002 | `358ed9fc…` = **KHOP** |
| `sim-x120` | `SIM_LOSER_TIME_STOP_HOURS=120` | **60812** | 60812 | 982 | `1696a477…` = **KHOP** |

=> o 96h/120h lenh FTT khong con la diem lech, printDone **giong het tung byte** ban Oracle.

## 2. Wall-clock / throughput

| do | gia tri |
|---|---|
| Oracle 1 run (`c2b_min`, file, `-Xmx14g`) | **329s** JVM (read 69% / sim 30%), RAM 9.8GB |
| Kaggle 1 run (`-Xmx22g`) | **426s** parity · 447s x96 · 545s x120 |
| Kaggle: push -> JVM bat dau | ~75s (queue + mount + symlink 912 ticker) |
| Kaggle: push -> COMPLETE | **~9 phut** (parity), 3/3 xong trong ~13 phut |
| Kaggle / Oracle moi run | **1.29x cham hon** |
| Throughput 5 slot | **~3.9x** Oracle tuan tu, va GIAI PHONG han slot JVM Oracle |

**So kernel song song do duoc: 3/3 cung `RUNNING` mot luc** (push 04:43:58Z, ca 3 COMPLETE
truoc 04:57:19Z). Tran cua account la **5** (`docs/runbooks/KAGGLE_RULES.md` §1);
`kaggle_sim.free_slots()` doc so slot con trong truoc khi push.

**Chi phi: 0.** Kaggle CPU kernel khong tinh quota (chi GPU co quota).

## 3. Dau vao — kiem ke khi `TICKER_SOURCE=file`

Dataset **`chuyendinh/sim-c2b-bundle`** (private, 58 file, 2.3GB) — layout PHANG
(kaggle upload bo qua thu muc con):

| file | nguon tren Oracle | kich thuoc |
|---|---|---|
| `sim.jar` | `target/binance-java-sdk-1.2.4.jar` | 95MB |
| `config.properties` | `configs/sim_dev.properties`, sua 2 dong: `TICKER_SOURCE=file`, `AEROSPIKE_HOST_226=161.118.212.3` | 2.4KB |
| `prof_<ten>.properties` x40 | `profiles/*.properties` | ~3KB moi |
| `exchange_info_pin.json` | `/home/ubuntu/java/exchange_info_pin.json` | 297KB |
| `market.bin` / `pred.bin` / `funding.bin` / `manifest.txt` | `/home/ubuntu/wfo_ds_clean/` (`ExportWfoDataset`) | 49MB / 38MB / **1.7GB** / 2KB |
| `predict_wf_2022*..2024*.bin` x10 + `BINS_SHA256` | `/home/ubuntu/predwf_map_s1a2/` (bins selector S1) | 386MB |

Ticker (**KHONG** trong bundle — da co san 3 dataset rieng, tong 4.07GB cho 912 ngay
2022-01-01..2024-06-30, KHONG thieu ngay nao):
`chuyendinh/wfo-ticker-2022`, `wfo-ticker-2023`, `wfo-ticker-2024h1`
(nguon: `/home/ubuntu/java/simulator/kaggle_data_hpo/daily/ticker_YYYYMMDD.bin.gz`).

Kernel symlink chung vao `/kaggle/working/kaggle_data_hpo/` vi `KaggleDataLoader` doc
**relative** `kaggle_data_hpo/` tu CWD. Kaggle tu giai nen `.gz` => glob `ticker_2*.bin*`.

**KHONG can** `core_market_data` / `core_ai_pred` / `core_funding_pred` (da co `WFO_DATA_DIR`
offline). `core_symbol_lifecycle` khong ton tai tren dia va sim chay binh thuong khong co no
(cache rong, giong het duong Oracle+file).

### Stage lai bundle khi jar/profile doi
Thu muc stage: `/home/ubuntu/simbundle` (hardlink toi `wfo_ds_clean` + `predwf_map_s1a2`,
chi ton them ~95MB cho jar). Cap nhat: copy jar/profiles moi vao do roi
`KaggleApi().dataset_create_version(folder='.', version_notes=..., dir_mode='skip')`.

## 4. Cach dung `tools/kaggle_sim.py`

```python
import sys; sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks

ks.free_slots()                       # con may slot trong 5 (DUNG neu = 0)

r1 = ks.submit("x96",  "c2b_min", {"SIM_LOSER_TIME_STOP_HOURS": 96},  code_sha="bd20e42")
r2 = ks.submit("x120", "c2b_min", {"SIM_LOSER_TIME_STOP_HOURS": 120}, code_sha="bd20e42")
ks.wait([r1, r2])                     # {"chuyendinh/sim-x96": "COMPLETE", ...}

out = ks.fetch("x96")
out["result"]      # {"equity_final": 62370, "n_trades": 1002, "secs": 446.6, "ok": true, ...}
out["print_done"]  # /home/ubuntu/kaggle_sim/out/x96/storage/printDone.csv
out["sim_out"]     # /home/ubuntu/kaggle_sim/out/x96/logs/sim.out (da giai nen)
```

CLI tuong duong:
```bash
cd /home/ubuntu/src/BinanceFuturesJava
python3 tools/kaggle_sim.py slots
python3 tools/kaggle_sim.py submit --tag x96 --profile c2b_min --set SIM_LOSER_TIME_STOP_HOURS=96
python3 tools/kaggle_sim.py wait  --tag x96
python3 tools/kaggle_sim.py fetch --tag x96
```

- `tag` -> kernel `chuyendinh/sim-<tag>`; push lai cung tag = version moi, **idempotent**.
- `profile` la TEN file trong `profiles/` (bo duoi `.properties`), da co trong dataset.
- `overrides` ghi de len BAN COPY cua profile trong kernel — **khong bao gio** dat qua env
  (`Cfg` fail-fast `exit 2` neu co env tham so giao dich kem `TRADING_PROFILE`).
  `WFO_FUNDING_PRED_DIR` luon bi ghi de sang duong mount Kaggle.
- Tieu chi thanh cong (bay #1 cua RUNBOOK): `java_rc=1` **KHONG** phai fail; kernel tu cham
  bang `equity_final != None` VA `n_trades > 0` -> `result["ok"]`.

## 5. Chua lam / no lai

- Chua do tran 5 slot bang phep do rieng trong dot nay (do 3, tran lay tu `KAGGLE_RULES` §1
  do 2026-06-13). Muon chac phai push 5 va dem.
- `SimpleSymbolMapper` van phu thuoc Aerospike Oracle — nut don le that su cua duong Kaggle.
  Sua tan goc = them nhanh `TICKER_SOURCE=file` doc `core_symbol_mapper` snapshot
  (`KaggleDataLoader.loadSymbolMapperFile()` da co san, **chua ai goi**) + tool export
  snapshot (`ExportKaggleBootstrapSnapshots` duoc nhac trong javadoc nhung **khong ton tai**
  trong `src/`). Chua lam trong dot nay vi phai rebuild jar + do lai neo.
- WFO/HPO worker tren Kaggle van la chuyen khac (`docs/runbooks/KAGGLE_RULES.md` §3d).

## 6. 🔴 BINS KHONG DI QUA DUONG KAGGLE (do thuc 2026-09-05, `docs/experiment/T1_LABEL3.md`)

`WFO_FUNDING_PRED_DIR` duoc **tieu thu o `ExportWfoDataset`** (noi sinh `funding.bin`),
**KHONG** o luc sim. Kernel Kaggle chi chay sim tren dataset **DA BUILD**:

    OFFLINE BIN: doc market/pred/funding tu WfoDataset tai /kaggle/input/.../sim-c2b-bundle

=> **doi bins trong bundle / trong profile khong lam doi ket qua tren Kaggle.** Do thuc: 3 chan
bins khac nhau day len Kaggle deu ra `equity 60395 / 970 lenh / md5 printDone 910f1aa6…`,
**y het parity** — im lang, khong loi. Ba run do vo hieu.

Muon chay bien the **bins** thi chi co hai duong:
1. **Chay o Oracle** (noi build dataset) — job T1 da lam vay: build dataset rieng moi chan roi sim,
   ~5 phut/chan, xoa dataset sau moi chan (`/home/ubuntu/t1_oracle.sh`).
2. Upload **dataset DA BUILD** rieng cho tung chan (`funding.bin` ~1.7GB/chan) roi tro
   `WFO_DATA_DIR` vao do — chua lam, ton bang thong.

Bien the **exit/gate/sizing** (nhu `x96`/`x120`) van chay Kaggle binh thuong: chung khong cham bins.

Kem theo: `tools/kaggle_sim.py` nay co tham so `bins_ds` (chon dataset bins rieng) — no chi doi
`WFO_FUNDING_PRED_DIR` khai bao trong profile (=> doi `PROFILE_HASH`), **khong** doi ket qua sim.
Giu lai vi `Cfg` van bat khai bao bins, nhung **dung tuong no la mot truc do duoc**.

`/kaggle/input` KHONG phang: dataset nam duoi `/kaggle/input/datasets/<user>/<slug>/`.
