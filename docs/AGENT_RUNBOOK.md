# AGENT_RUNBOOK — doc DAU TIEN moi session/agent moi

Muc dich: mot session moi (ke ca model yeu hon) doc file nay la du de tiep tuc,
khong can hoi lai user, khong can doc lai 30 doc khac.

## 0. LUAT CUNG — vi pham la sai, khong phai lua chon

1. **KHONG chay VAL.** Moi thu trong pham vi DEV (2022-01 -> 2024-06, hoac 2021-07
   sau khi mo rong). VAL da cham 5 lan, khong con la holdout. Muon chay VAL phai
   co user duyet TRUC TIEP trong chat. Khong tu quyet.
2. **Pre-register TRUOC khi chay.** Viet `docs/PREREG_<TEN>.md`, commit, ROI moi chay.
   Khong sua pre-reg sau khi thay ket qua. Null co tinh thong tin — bao cao null.
3. **Equity KHONG phai tieu chi.** `sd(dCAGR)` exit params = 2.57pp;
   `E[max nhieu]` = 2.57*sqrt(2 ln N) => N=50 cho +7.2pp. DEV da chay ~125 run.
   Tieu chi phai la RATE tren hang tram trade (TSloss%, win%, mean(profit|status),
   admit%). Equity bao cao rieng, dan nhan "khong phai tieu chi".
4. **Bao rui ro/lo hong TRUOC**, khong khen, tieng Viet + thuat ngu Anh nguyen ban.
5. **Khong `print()` trong Python** — dung module `logging`. Java dung SLF4J.
6. **Khong push.** Commit branch `module`, de user push.
7. Model cho agent: Opus cho task nhieu buoc/co side-effect (chay sim, sua file,
   xoa file). Sonnet/Haiku cho doc-va-tom-tat. **KHONG dung Fable.**

## 1. Kenh truy cap Oracle

Repo o box Oracle, chi toi duoc qua desktop bridge cua may Windows.
Load: `ToolSearch select:mcp__remote-devices__plugin_desktop-commander_desktop-commander__start_process,...__write_file,...__read_file`

```
1. write_file  -> C:\Users\pc\AppData\Local\Temp\<PREFIX>_<n>.sh   (prefix rieng moi agent)
2. start_process timeout_ms 25000:
   powershell.exe -NoProfile -Command "Start-Process powershell.exe -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','C:\Users\pc\AppData\Local\Temp\runsh.ps1','-Sh','<sh>','-Out','<log>' -WindowStyle Hidden; 'launched'"
3. read_file <log>   (ENOENT = chua xong, cho roi doc lai)
```
BAT BUOC `Start-Process` roi poll. Goi runsh.ps1 truc tiep => chet o timeout 60s
cua device bridge. `runsh.ps1` tu strip BOM + CRLF (2 cai bay cu).

Duong dan: repo `/home/ubuntu/src/BinanceFuturesJava` (branch `module`),
sim runs `/home/ubuntu/java/devrun/<TAG>/`, jar `$R/target/binance-java-sdk-1.2.4.jar`.

## 2. Chay mot sim run

```bash
R=/home/ubuntu/src/BinanceFuturesJava; JAR=$R/target/binance-java-sdk-1.2.4.jar
B=/home/ubuntu/java/devrun; PROF=$R/profiles/c2b_min.properties; DS=/home/ubuntu/wfo_ds_<x>
# build dataset 1 LAN (dung chung cho N sim neu chi doi param exit/gate/sizing)
cd $B && cp -f $R/configs/sim_dev.properties $B/config.properties
env TRADING_PROFILE=$PROF WFO_SET_PRED=ai_pred_market_gate_wfo WFO_SEL_HORIZON_IDX=0 \
  WFO_CODE_SHA=$(cd $R && git rev-parse --short HEAD) java -Duser.timezone=Asia/Ho_Chi_Minh \
  -Xmx14g -cp $JAR com.binance.chuyennd.ai_ml.wfo.framework.ExportWfoDataset $DS > logs/build.out 2>&1
# moi run
D=$B/<TAG>; mkdir -p $D/storage $D/logs; cd $D
cp -f $R/configs/sim_dev.properties config.properties; rm -f storage/*
env WFO_DATA_DIR=$DS WFO_SMART_CACHE=1 SIM_END_DATE=20240630 \
  EXCHANGE_INFO_PATH=/home/ubuntu/java/exchange_info_pin.json TRADING_PROFILE=$PROF \
  java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx14g -cp $JAR \
  com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss > logs/sim.out 2>&1
```

### 8 cai bay bat buoc biet
1. **`rc=1` KHONG phai fail.** Sim in rc=1 du hoan tat. Tieu chi: log co `done:` + `b:`
   va `storage/printDone.csv` co dong.
2. **Da co `TRADING_PROFILE` thi KHONG duoc dat bien env tien to `SIM_`** (tru
   `INFRA_KEYS`) — `Cfg` fail-fast `exit 2`. Muon doi param => COPY profile, sua 1 dong.
3. `WFO_FUNDING_PRED_DIR` dat CA env VA profile => exit 2. Chi de trong profile.
   Thieu bins => `ExportWfoDataset` THROW. Kiem `grep -q '^WFO_FUNDING_PRED_DIR=' $PROF`.
4. Chi **1 slot JVM**. `pgrep java` phai rong. Chay TUAN TU. `run_c2b_dev.sh` tu exit 3.
5. **Dia 92% (con ~16G)**. `rm -rf $DS` sau khi xong. `df -h /` truoc khi build;
   duoi 5G free thi DUNG.
6. Neo: **60390** voi `TICKER_SOURCE=aerospike`; **60395** voi `TICKER_SOURCE=file`
   (lech 1 lenh/970, FTT 2022-11-09). So sanh Oracle<->Kaggle chi tin toi ~0.01%.
7. **Device: CPU o dau cung duoc; GPU chi de QUET.** Do lai 2026-09-05, 3 moi truong
   x 3 seed, cung mot file hash khop (`docs/BENCH_DEVICE.md`).
   - **Kaggle CPU == Oracle CPU byte-for-byte**: per-tick `|dIC|` = **0.0 chinh xac**,
     `ic_sha256` trung ca 3 seed, cay dau tien trung sha — du khac arch (x86 vs aarch64),
     python (3.12 vs 3.10), numpy (2.0.2 vs 2.2.6). => **train S1 tren Kaggle CPU vo dieu
     kien**. So cu `0.17040 vs 0.1723` la lech DU LIEU/pipeline, KHONG phai lech may;
     khong duoc dung no de khoa vao Oracle.
   - **GPU lech that, nhung ly do khac lenh cam cu**: per-tick lech ngang nhieu seed
     (x1.07-x1.20), `edge5` cung nam trong nhieu seed (x1.21); cai lech that la
     `|d mean rank-IC|` = **0.00448 ~ x3.7** nen seed cua CPU, va GPU **tu no nhieu gap
     4.8 lan** CPU. Nguyen nhan: `Cover` lech 31/31 node (RNG `subsample`/`colsample`
     khac) + `Split` lech 11/31 (quantile sketch `hist` khac). Ghim seed khong cuu duoc.
   - **`nthread` khong anh huong**: `n_jobs=1` vs `4` cho ket qua giong het (tree1 sha
     trung, `dIC` = 0.0).
   - **Cong `spearman >= 0.999` DA BO.** Doi seed tren cung mot may cho spearman
     **0.9817** (774,270 dong) — cong do loai ca viec re-seed chinh mo hinh. Chinh no
     tao 2 false positive, khong phai GPU. Thay bang: **hieu ung phai vuot CI multi-seed
     (>= 3 seed) do trong cung moi truong**; chua co CI thi chua duoc ket luan.
   - **Van giu nguyen**: khong ghep cap so tu 2 moi truong trong mot so sanh; GPU thi CA
     phep so phai tren GPU; parity/byte-identity phai chay tren dung device sinh ra neo;
     Java sim o lai Oracle (data host + neo 60390).
8. `TIME_RUN` (ngay bat dau DEV) o `configs/sim_dev.properties:39`, KHONG co
   `SIM_START_DATE`, va `TIME_RUN` khong trong whitelist `Cfg.java:50` => chi doi
   qua file config.

### Chay SONG SONG tren Kaggle (thoat rang buoc 1 slot JVM Oracle)

Oracle chi co **1 slot JVM** (bay #4) => moi sim phai xep hang. Kaggle CPU chay duoc
**5 kernel cung luc**, moi kernel 4 core / 31GB. Do that 2026-09-05: Kaggle+file ra
`b:60395` va `printDone.csv` **giong Oracle+file tung byte** (`md5 910f1aa6...`);
`x96`/`x120` con giong ca ban Oracle+aerospike (`docs/E1_EXIT_RESULT.md`) tung byte.

```python
import sys; sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks
ks.free_slots()                                                    # DUNG neu = 0
r = ks.submit("x96", "c2b_min", {"SIM_LOSER_TIME_STOP_HOURS": 96}, code_sha="bd20e42")
ks.wait([r]); out = ks.fetch("x96")      # out["result"]["equity_final"], out["print_done"]
```

**Bay rieng cua duong Kaggle (them vao 8 bay o tren):**
9. **Neo Kaggle la 60395**, khong phai 60390 — Kaggle bat buoc `TICKER_SOURCE=file`.
10. **Kernel phai `enable_internet=True`**: `SimpleSymbolMapper` van doc Aerospike Oracle.
    Mapper rong => ket qua lech am tham; `kaggle_sim` da guard (`exit 2` neu < 800 symbol).
11. **`PROFILE_HASH` Kaggle KHAC Oracle** (duong `WFO_FUNDING_PRED_DIR` khac) — so parity
    bang md5 `printDone.csv`, KHONG bang `PROFILE_HASH`.
12. Doi jar/profile => phai `dataset_create_version` lai `chuyendinh/sim-c2b-bundle`.

Chi tiet + kiem ke dau vao + wall-clock: **`docs/KAGGLE_SIM.md`**.

### Cham diem
```bash
python3 $R/research/analysis/qret_ladder.py C2b <TAG>...   # quy/nam/TSloss/margin/medP
python3 /home/ubuntu/java/fsrun/qret.py C2b <TAG>...        # + underwater, quy>=5%
bash    /home/ubuntu/java/fsrun/ev.sh   C2b <TAG>...        # phan bo exit
md5sum $B/C2b/storage/printDone.csv $B/<TAG>/storage/printDone.csv   # parity
java -cp $JAR com.binance.chuyennd.tradecore.DumpConfig     # PROFILE_HASH + derived.*
```

## 3. Baseline hien tai

`C2b` = equity 35,000 -> **60,390**, CAGR 24.48%, maxDD −13.12%, 970 lenh,
underwater 93 ngay. Profile `profiles/c2b_min.properties` (16 key,
`PROFILE_HASH=a2f859b2463108fe`), md5 printDone `8f7afdfb27b15f5b6d4c886700def93c`.

Kien truc: **S1** (9 feature, XGBRanker rank:ndcg, label `rel5` = quintile trong tick
cua `g1lite − median`) quyet dinh THU TU coin; **G015x26** (45 feature, XGBClassifier,
label `maxFav_4h >= 0.06`) quyet dinh GIA TRI gate. `build_map.py` giu nguyen multiset
P(win) cua G015x26 trong moi tick, chi gan lai theo rank cua S1 (`changed` 4.9%).

Exit: arm +7% roi trailing `giveback = min(peak*0.5, cap)`, cap 0.08 STRONG /
0.03 WEAK (ban le `symbolPred < 0.29`). **Khong co stop-loss truoc arm.**
`STOP_LOSS_DONE` = **time-stop 168h**, KHONG phai SL.

## 4. Ket luan da chot — DUNG lam lai

- **Selector ladder CHUA THIET LAP.** 78% uu the C2b−C2_g015 nam trong 2022; rebase
  2023-01 thi C2b THUA 5.5pp. medP giong het (5.50 vs 5.49). Khac biet la co dac
  co hoc: it lenh hon 39%, margin/trade lon 1.85x. Xem `docs/SELECTOR_LADDER_Q.md`.
  => **KHONG lam them selector variant / rank-IC / feature selection.**
- **Gate la load-bearing**: `v3_g1_nomom` = 10,305 voi 14,007 lenh. Giu.
- **Exit G1 -> C2 la cai tien that**: medP 3.5-4.0 -> 5.5-6.0 o 10/10 quy.
- **Time-stop 168h la kenh mat tien lon nhat**, va `mean(profit|SL_DONE)` giam don
  dieu khi rut ngan: 168h −18.90% / 120h −16.15% / 96h −13.99% / 72h −12.31%.
  Xem `docs/E1_EXIT_RESULT.md`.
- Nhom bi time-stop chet vi **khong bao gio chay**: 66.6% chua tung vuot +3%,
  maxFav median 1.83% dat o gio thu 4. Ha nguong arm KHONG cuu duoc. `docs/E0_EXIT_CF.md`.
- **Aerospike Oracle da du 2021** (`test/funding_data` 88-136 coin/thang). Khong
  can copy set nao ve. `docs/D1_DATA_AUDIT.md`.
- **Sizing (F_BASE / U_MAX / DCA_GRID_SCALE) KHONG do duoc tren DEV.** Sizing khong
  doi chat luong tung lenh, chi doi thang do => tieu chi duy nhat la maxDD/underwater,
  deu la single-realization n_eff nho. Day la nut RISK PREFERENCE user dat, khong
  phai bai toan toi uu. **DUNG dot sim run vao day.**

## 5. Leak / no ky thuat con mo
- `predwf_G015x26` KHONG reproduce duoc (mat training export). Single point of failure.
- `VisionMetricsClient.parseDay` con lo 5-phut forward. **KHONG rebuild OI truoc khi patch.**
- purge 72h < holding 168h => train/test overlap tren equity path.
- `Constants.diedSymbol` trong G015 f3/f4/f5 = danh sach delist hardcode (future info).
  Huong: lam NHE uu the C2b, khong phong dai.
- `f23 fundingPersistence` = proxy thoi gian.
- `SELECTOR_FEATURES` muc D dua tren claim da retract => coi la VOID.
- API key trong git history chua rotate. K=8 (sim) vs K=5 (live) chua dong.
- `configs/c2b.properties` co 5 key chet (`DISABLE_PREDICT_SYMBOL`,
  `HARD_STOP_LOSS_RATE`, `TIME_STOP_HOURS`, `TS_GAP_CONST`, `TS_MIN_GAP`) =>
  `CONFIG_STRICT=1` se STOP. `c2b_min` (16 key) va `c2c_round` (19) pass.
