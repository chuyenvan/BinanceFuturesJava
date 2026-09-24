# AUDIT_GATE_DYN_PARITY — gate tang 2 (dyn) SIM vs LIVE trong rank-mode

Read-only: khong sua code, khong deploy, khong chay sim moi; live 242 chi doc. Repo
`/home/ubuntu/src/BinanceFuturesJava` branch `module`, HEAD = `1a7847d`.
Goi y tu `docs/analysis/BRIEF_GATE_SELECTOR_20260911.md` muc B.

## 1. KET LUAN

**CO LECH, va do lon nhat trong moi diem venh sim<->live da ghi.** Voi `SELECTOR_RANK_TOPK=8` va
`levelChange=PREDICT_SYMBOL_TRADE`, SIM **luon** goi `checkSignalDynamic` (nguong `dyn_thr` **tang
theo `symbolPred`**), LIVE **bo qua** no va roi xuong `checkSignal` (nguong phang `0.008`). Vi
`symbolPred` cua top-8 nam o **0.25-0.35**, gate sim cho top-8 la **0.0172-0.0240** = **2.1-3.0
lan** nguong phang. Do tren 48 thang X1 (luoi 1 phut, forward-fill nhu engine): **95.62%** slot
top-8 ma gate phang cho qua thi gate dyn **CHAN** (2022 89.6% / 2023 94.9% / 2024 93.6% / 2025
97.6%). Do tren 78 lenh so giay C3 tren 242 (07-11/09/2026): **77/78 = 98.7%** bi chan neu live
chay gate nhu sim. Vay equity `X1_C3_FULL_PARITY_R` = 111,428 / n = 2,266 la so cua **chien luoc
CO gate dyn**, con so giay 242 la cua **chien luoc gate PHANG** — **hai chien luoc khac nhau**,
khong phai hai lan do cua cung mot thu. Comment `[PARITY]` trong live (653-655) **SAI**: no suy tu
buoc CHON ung vien (tang 1, `maxThres`) sang buoc ENTRY-FILTER (tang 2) — sim bo tang 1 khi
`TOPK>0` nhung **giu nguyen tang 2**. Khong tu sua; de xuat o muc 5.

## 2. CODE + SO THAT

### 2.1 SIM — `SimulatorMarketLevelTicker1MStopLoss.createOrder` (dong 962-968)
```java
962 if (!levelChange.equals(MarketLevelChange.BIG_DOWN)) {
963     AIRejectFilter.FilterResult filterResult = null;
964     if (levelChange == MarketLevelChange.PREDICT_SYMBOL_TRADE) {
965         filterResult = aiRejectFilter.checkSignalDynamic(predict, symbolPred);
966     }
967     if (filterResult == null)
968         filterResult = aiRejectFilter.checkSignal(predict);
```
**KHONG co dieu kien `Configs.SELECTOR_RANK_TOPK <= 0`.** `grep -n "SELECTOR_RANK_TOPK"` tren file
nay ra 4 vi tri (156-157 log; 331/336/339-340 selector tang 1) — **khong cai nao quanh 964-968**.
`git log -S"checkSignalDynamic"` tren file: **1 commit duy nhat** `8fa930b` — **chua bao gio sua**.

### 2.2 LIVE — `DetectEntrySignal2TradeNormal.createOrderBuyRequest` (dong 652-662)
```java
652 if (levelChange == MarketLevelChange.PREDICT_SYMBOL_TRADE) {
653     // [PARITY] rank-mode (SELECTOR_RANK_TOPK>0): backtest RANK-TOPK BO nguong per-symbol,
654     //   chi dung market gate => KHONG goi checkSignalDynamic, de roi xuong checkSignal (market-only).
655     //   TOPK<=0: giu checkSignalDynamic cu (byte-identical).
656     if (symbolPred != null && Configs.SELECTOR_RANK_TOPK <= 0) {
657         filterResult = aiRejectFilter.checkSignalDynamic(predict, symbolPred);
658     }
659 }
660 if (filterResult == null) {
661     filterResult = aiRejectFilter.checkSignal(predict);
662 }
```
=> `TOPK=8` (`conf/env.sh:71` tren 242) **=> nhanh 657 KHONG BAO GIO chay** tren live.

### 2.3 Ai/khi nao tach
`311bb29` "fix(live): K5 selector parity voi backtest RANK-TOPK", chuyenvan, **21/08/2026 16:55**,
1 file / +19 -5. Than commit: *"1) Nguong per-symbol: live loc maxThres (predictAllCandidates) +
checkSignalDynamic truoc khi vao; backtest RANK-mode BO nguong, lay top-K theo score"*.
**Suy dien sai o day**: cai backtest bo khi `TOPK>0` la `maxThres = RATE_MAX*AI_DYNAMIC_MAX` o
**tang 1 selector** (`Simulator:324-345`), **khong phai** `checkSignalDynamic` o tang 2. Cung
commit da sua DUNG phan cap-then-skip (314-330).

### 2.4 Cong thuc + tham so THAT
`AIRejectFilter` — `thres15M(t)` (44-48) = rolling neu `GateRollingThreshold.isOn()` else
`Configs.MIN_MOMENTUM_15M`. `checkSignal` (63-65,106-114): PASS <=> `p15 >= thres15M(t)`.
`checkSignalDynamic` (70-92): EARLY (76-83) `p15 < thres15M && symbolPred > RATE_MAX` => REJECT;
roi `scale = max(AI_DYNAMIC_MIN, symbolPred/RATE_MAX*AI_DYNAMIC_MULTIPLIER)` (85-89) va
`dyn_thr = thres15M(t) * scale` (90) — **CHI CAN DUOI**, khong `Math.min(...,AI_DYNAMIC_MAX)`.

| tham so | gia tri | nguon (SIM **va** LIVE deu lay day — khong ben nao override) |
|---|---|---|
| `MIN_MOMENTUM_15M` | **0.008** | profile `x1_c3_full.properties:32`; 242 `conf/env.sh:32` (**cung 0.008**) |
| `AI_DYNAMIC_MIN` / `AI_DYNAMIC_MULTIPLIER` | **0.26787** / **1.28760** | `Configs.java:341` / `:340` (khong profile/env nao khai `SIM_AI_DYNAMIC_*`) |
| `PREDICT_SYMBOL_RATE_MAX_THRESHOLD` | **0.15** | `Configs.java:367` |
| `AI_DYNAMIC_MAX` | 2.14135 | `Configs.java:342` — **khong phai tran gate**; la tran ung vien tang 1, ma tang 1 bi bo khi `TOPK>0` |
| `SELECTOR_RANK_TOPK` | **8** | profile:9; 242 `conf/env.sh:71` |
| `GateRollingThreshold` | **OFF** | khong noi nao khai `SIM_GATE_ROLLING_PCT` |

**`dyn_thr = 0.008 * max(0.26787, symbolPred/0.15 * 1.28760)`**, don dieu tang, khong tran:
`sp` 0.0312 (san) -> **0.00214** (x0.27) | 0.1165 (hoa) -> **0.00800** (x1.00) |
**0.25 -> 0.01717 (x2.15)** | **0.30 -> 0.02060 (x2.58)** | **0.35 -> 0.02404 (x3.01)**.

### 2.5 `symbolPred` la gi — giai mau thuan "dyn_thr ~0.02 thi sim sao co noi 2,266 lenh"
`symbolPred = 1 - P(win)`, **dao dau** tai `WfoDataset.buildFundingFromWfFiles:248`
(`float score = 1.0f - pwin;`), horizon slot 0 (kiem tren bins: `p0` co so that, `p1/p2/p3` NaN
toan bo); xac nhan doc lap `L4_LIVE_BUILDMAP.md:49-50,61-66`. Sim sort **tang** va lay K phan tu
**dau** (`Simulator:336-337,355-357`) => **rank 1 = symbolPred THAP nhat**.
Do tren bins `predwf_map_s1a2_x1`: `p0` in [0.024,0.775] (mean 0.309) => `symbolPred` in
[0.225,0.976]; **median cua top-8** = 0.497/0.447/0.360/0.312 theo nam — **khong ai < 0.1165**,
nen gate dyn luon **SIET**. Mau thuan giai nhu sau: sim co 2,266 lenh **dung vi** no chi vao o
cac phut hiem hoi ma `p15` that su cao. Kiem chung tren chinh `printDone.csv` cua `PARITY_R`
(1,996 leg PST): **100.00%** so leg thoa `pred15m >= dyn_thr(symbolPred)`, va `pred15m` median
theo nam = **0.01916/0.02181/0.01695/0.01625** — gap doi nguong phang (neu chay gate phang thi
median phai quanh 0.008-0.010). **Bang chung tu chinh ket qua sim**, doc lap voi doc code.

## 3. TAC DONG TRONG SIM THEO NAM (offline, KHONG chay sim)

Script `research/analysis/gate_dyn_parity.py`. Nguon: bins `predwf_map_s1a2_x1` (16 fold,
2022-01..2025-12, 15m) + `claudedata/wfo_gate_pred.csv` (luoi 1 phut); tham so doc THANG tu repo
qua `gate_cfg`. Moi moc selector lay top-8 theo `symbolPred` tang; `slot_flat` = slot top-8 tai
tick `p15>=0.008` (= gate LIVE cho qua), `slot_dyn` = trong do thoa `p15>=dyn_thr` (= gate SIM).
**KHONG dung `ledger/cand_dev_x1.parquet`**: cot `score_g015`/`dyn_thr` o do dung bins
`predwf_G015x26` **chua qua S1 remap** (`x1_ledger.py:35,45-46`), khong phai bins cua profile.

**Luoi 1 phut** (= engine: `WfoDataset.forwardFillToGrid` carry-forward moc 15m ra moi phut
market, stale <= 15m, `WfoDataset:123-134`):

| nam | phut | phut gate-phang MO | slot_flat | slot_dyn | **% slot bi dyn CHAN** | slot dyn-mo-ngoai-flat |
|---|---|---|---|---|---|---|
| 2022 | 525,542 | 42,750 | 342,000 | 35,696 | **89.56%** | 38 |
| 2023 | 525,586 | 7,115 | 56,920 | 2,878 | **94.94%** | 293 |
| 2024 | 526,952 | 31,752 | 254,016 | 16,167 | **93.64%** | 55 |
| 2025 | 525,586 | 166,301 | 1,330,408 | 32,163 | **97.58%** | 167 |
| **48 thang** | | | **1,983,352** | **86,904** | **95.62%** | 553 (0.6%) |

Luoi 15m (chi moc selector): 89.95/94.11/93.87/97.60%, tong **95.71%** — hai luoi khop => ket qua
khong phu thuoc lua chon luoi.

**Doc bang**: gate dyn quyet dinh **~96%** co hoi vao lenh cua sleeve selector; go no ra (= chay
nhu live) thi sleeve co **~23 lan** so co hoi entry. Chieu nguoc lai (dyn **noi** hon flat) chi
553/86,904 = **0.6%** slot — khong dang ke, vi `symbolPred` top-8 khong bao gio < 0.1165.

**Doi chieu so lenh THAT** (`printDone.csv` cua `PARITY_R`, 2,266 dong, 1,996 leg PST):
366/258/596/776 theo nam — thap hon `slot_dyn` vi con `isSymbolRunning`/ticker/ngan sach/gop leg,
dung chieu. Nhip **1.37 entry PST/ngay** vs so giay 242 **78 entry / 4.6 ngay = 17.0/ngay** =
**~12 lan**, khop bac do lon cua ti so 23x. Day la **bang chung thu ba**, doc lap.

> Khong chay sim `X1_C3_FULL_TICKLOG`: hai duong doc lap da cho cung ket luan voi bien do rat
> lon (95.6% vs 0%). Neu master muon con so `D_GATE_REJECT` tach dyn/flat thi `TickDecisionLog.ON`
> la duong dung.

## 4. TAC DONG TREN LIVE (242, read-only) — so giay C3 07-11/09/2026

Nguon: `shadow_c3/ledger.csv` (51 lenh dong) + `open_positions.csv` (27 dang mo) = **78 entry**;
`p15` lay tu dong `Predict: {"return15M":...}` cung phut voi `[SHADOW] would-BUY ... time:...`
trong `v_t_m/logs/full.log`. Ghep **78/78**, 0 dong thieu.
`symbol_pred` cua 78 entry: **0.2519..0.3484** (dung vung du doan o 2.5).
`p15` tai tick vao lenh: **min 0.00805 / mean 0.01005 / max 0.02379**. Ap
`dyn_thr = 0.008*max(0.26787, sp/0.15*1.2876)`:

| nhom | n | pnl da dong (USDT) |
|---|---|---|
| **QUA** gate dyn | **1** (BULLAUSDT 10/09 03:29, sp 0.2963, thr 0.02035, p15 0.02379) | +21.24 (1 lenh) |
| **BI CHAN** | **77 (98.7%)** | +2,224.09 (50 lenh dong) + 27 lenh dang mo |

Tuc **77/78 lenh cua so giay C3 se KHONG bao gio ton tai** neu live chay gate nhu sim; lenh duy
nhat song sot co `p15` cao bat thuong (2.38%, thuoc ~0.1% phut cao nhat 2025-2026).

**Khong dien giai outcome**: n=1 vs 77 khong cho so sanh "nhom nao tot hon"; ca 51 lenh dong deu
`TRAILING_STOP` duong (cua so 5 ngay, regime mot chieu). pnl o day chi de noi **quy mo**, khong
phai bang chung ve chat luong gate.

## 5. HE QUA + DE XUAT (KHONG sua)

### 5.1 Cai nao la "C3 that"?
- `X1_C3_FULL_PARITY_R` (equity 111,428 / n 2,266) = **C3 CO gate dyn**. Moi ket qua DEV/VAL da
  dung de ra quyet dinh (C2b 60,390; X1_C3_FULL; GD92; GF27; K12; 5MGRID; HOLDDCA...) deu sinh tu
  engine nay => **deu la C3 co gate dyn**.
- So giay 242 = **C3 gate PHANG** — **mot chien luoc chua tung duoc backtest**. Goi no la
  "so giay C3" la **sai ten**: no khong phai C3_FULL.
- => Ket luan L1/L2/L3/L4 ve "shadow bam sat sim" phai doc lai: 9 diem venh o
  `L4_LIVE_BUILDMAP.md` muc 7 **thieu diem nay**, va no lon hon ca 9 diem kia cong lai (doi ~96%
  tap entry). Can them **diem 10: gate tang 2**.
- Comment `[PARITY]` o `DetectEntrySignal2TradeNormal:653-655`: **SAI**. Phai sua chu thich du
  chon huong nao o 5.2.

### 5.2 Ba huong — **master chot**, KHONG tu sua

| huong | viec | rui ro |
|---|---|---|
| **A. Sua LIVE cho khop SIM** (bo dieu kien `TOPK<=0` o dong 656) | 1 dong | Tan suat live tut ~12-23 lan (17 -> ~1.4 entry/ngay). **Nhung** day la chien luoc DUY NHAT da co bang chung 48 thang. Rui ro: neu bins/`p15` live lech sim (diem 4/8 muc 7 L4) thi gate siet se **khuech dai** lech do, vi no cat o duoi 4% duoi cung cua phan phoi `p15`. |
| **B. Sua SIM cho khop LIVE** (them `&& TOPK<=0` o `Simulator:964`) | 1 dong | **Huy toan bo lich su DEV/VAL**: moi so da chot (C2b, X1, GD92, GF27, K12, HOLDDCA, X3...) deu phai chay lai; nhung "DONG" cu thanh vo hieu. Va ban gate-phang **chua tung co equity 48 thang**. Khong duoc lam viec nay ma khong chay lai baseline truoc. |
| **C. Chot spec truoc, do sau** | pre-reg 1 run sim `X1_C3_FULL_FLATGATE` (chi doi gate tang 2 sang phang), so voi `PARITY_R` bang dung cong CI cua `AGENT_RUNBOOK` | Re nhat, khong dung live. **De xuat uu tien**: no bien cau hoi "sua ben nao" thanh mot phep do thay vi mot niem tin. |

**Khuyen nghi**: **C truoc, roi A hoac B theo ket qua C.** Trong luc cho, live 242 dang chay mot
chien luoc **chua co bang chung backtest** — rui ro nay can ghi vao `QUEUE.md`.

### 5.3 Cong parity phai co (theo `AGENT_RUNBOOK.md` dong 204, 244, 421)
(1) `md5sum printDone.csv` run moi vs `PARITY_R` phai **KHAC** (giong => co chua ap dung).
(2) Cat toi moc chung, dem dong IDENTICAL. (3) Bao ca 8 ung vien + parity **theo tung nam**, du
bo rang buoc cung 4 muc, khong cherry-pick. (4) Stamp `PROFILE_HASH` + `BinsProvenance` sha256.
(5) Sau khi chot: them **diem 10 (gate tang 2)** vao `L4_LIVE_BUILDMAP.md` muc 7 va sua chu thich
`[PARITY]` o live.

## 6. TAI LAP

**Code** (Oracle, HEAD `1a7847d`): `sed -n '960,975p' .../research/Simulator...StopLoss.java`;
`sed -n '645,665p' .../trading/DetectEntrySignal2TradeNormal.java`;
`grep -n "SELECTOR_RANK_TOPK" <file sim>`; `git log -S"checkSignalDynamic" --oneline -- <2 file>`;
`git show 311bb29 --stat`.

**Bang muc 3** (~20 giay, chi ghi vao `ledger/`; script tu in `gate_cfg.describe()` = nguon tung
tham so truoc khi tinh):
`cd /home/ubuntu/src/BinanceFuturesJava && python3 research/analysis/gate_dyn_parity.py`
-> `/home/ubuntu/ledger/gate_dyn_parity_year.csv`.

**Doi chieu printDone** (`PARITY_R`, loc `level=PREDICT_SYMBOL_TRADE`), voi
`t = 0.008*max(0.26787, symbolPred/0.15*1.28760)`: `(pred15m>=t).mean()=1.0000`,
`(pred15m>=0.008).mean()=0.9895`.

**Bang muc 4** (242, CHI DOC; chi `grep/awk/date`, chi ghi `/root/tmp_*.txt`):
`grep "return15M" logs/full.log` (8,746 dong) + `grep "SHADOW] would-BUY" logs/full.log` (1,108);
awk ghep theo key `"DD/MM/YYYY HH:MM"` cua dong log; `ledger.csv`/`open_positions.csv` doi
`ts_entry` bang `date -d @(ts/1000)` de lay `symbol_pred`; loc `>=20260907` -> 78 entry, ghep 78/78.

**Tham so tra nhanh**: `Configs.java:340-342,367,374-375,400`;
`profiles/x1_c3_full.properties:9,32`; 242 `conf/env.sh:32,71`;
`AIRejectFilter.java:44-48,63-65,70-92`; `WfoDataset.java:70-71,123-134,245-249`.

**GIOI HAN**: (1) muc 3 do **offline** tren bins + gate csv, khong mo hinh
`isSymbolRunning`/ngan sach/ticker => 95.62% la **ty le slot co hoi**, KHONG phai ty le lenh
(ty le lenh chi do duoc bang `TickDecisionLog`, chua chay). (2) muc 4 n=78, 4.6 ngay, 1 regime =>
**chi mo ta**, khong ket luan edge. (3) `p15` live (ONNX) vs `p15` offline (`wfo_gate_pred.csv`)
**chua chung minh dong nhat** (`L4` muc 7 diem 8) — da giam thieu bang cach lay `p15` tu **chinh
log live**. (4) Audit KHONG dung toi "gate nao TOT hon" — do la thi nghiem 5.2 huong C.
