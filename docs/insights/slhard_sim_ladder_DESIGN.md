# DESIGN — Java sim SL-cung + baseline ladder (CHO UNI DUYET truoc khi code/build)

> Muc dich: 1 harness Java do CA 5 nac thang baseline bang doi config → moi tru quy duoc cong,
> apples-to-apples, cung pass-criteria (70% OOS-duong / WFE median ≥0.5 / worst OOS maxDD ≤50%).
> Draft — chua code. Cho Uni chot dinh nghia REF/B0 + cac diem [?] truoc khi trien khai.

## 1. Input contract
- **Entry preds**: `ev2_preds_n6.csv.gz` (kernel sl4h-ev2-export): `win, ts, symbol, p6, p9`.
  Leak-free (train IS < cut−purge, predict OOS). 1 dong = 1 co-hoi entry tren luoi 15m.
- **Path that**: 1m kline doc tu nguon SAN CO (Aerospike ns ticker / kline_1m_opt — xac nhan lai
  class doc dung: `DataManagerAerospikeFloatSim`?). Sim KHONG dung label proxy — dung gia 1m that.
- Window map: win → [cut, cut+3m) khop build_folds Kaggle (17 window 12m-IS/3m-OOS, FIRST_OOS=202301).

## 2. Vong doi 1 lenh (state machine — long-only, 1x, no DCA)
Entry tai (coin, ts) neu `p6 >= P*` (REF: P*=0.7). **Entry tre 1 nen** (fill tai open nen ts+1m)
— BAT BUOC vi edge = momentum ngan (f36 ret15m), fill ngay = lac quan. [?] xac nhan 1 nen = 1m hay 15m.
Sau entry, duyet 1m kline toi het horizon H (REF: 4h; bien the 12h):
- **TP-cung** (neu bat): cham +N% intrabar → chot +N%. [REF: TAT TP — de winner chay, theo phat hien E1>E2]
- **Disaster-SL** (tru SL): cham −L% intrabar → chot −L%. [REF: TAT. +SL bat: L co dinh 5/8 hoac adaptive q90]
- **Arm-trailing** (tru trailing): cham +A% (A=3) → arm; sau do trailing sàn/give-back. [REF: TAT. +TR bat]
- **Time-stop**: het H ma chua thoat → dong tai close nen H. (luon bat — day la "SL-cung" goc)
Phi: tru 0.2% (2 chan) moi lenh. Funding: TAT trong ladder (bat o Golden cuoi).

## 3. Nam thang (chi doi CONFIG, cung harness/cung WFO)
| Nac | entry | TP | disaster-SL | trailing | time-stop | do duoc gi |
|---|---|---|---|---|---|---|
| B0 | take-all candidate (p bo qua) | off | off | off | 4h | thi truong tu than |
| REF | p6≥0.7 | off | off | off | 4h | ENTRY edge = REF−B0 |
| +SL | p6≥0.7 | off | **on** (best tail) | off | 4h | SL edge = (+SL)−REF |
| +TR | p6≥0.7 | off | off | **on** (best trail) | 4h/12h | TR edge = (+TR)−REF |
| FULL | p6≥0.7 | off | on | on | 4h/12h | interaction |

Bien the horizon 12h chay song song (giai TOO_FEW). Ung vien SL/TR chot tu 2 kernel dang chay
(sl4h-tail-sl, sl4h-trail-cond) → moi tru dua DUNG 1 ung vien vao ladder, khong grid trong Java.

## 4. Do & pass-criteria (pre-register)
- Moi nac: chay 17 window WFO → per-window OOS PnL, maxDD, #trades, note.
- Metric: % window OOS-duong, WFE median, worst OOS maxDD, PnL/keo trade-weighted, #keo/quy.
- **PASS** (da chot): %OOS-duong ≥70%, WFE median ≥0.5, worst maxDD ≤50%.
- Gate-check: B0/REF phai cho ra so KHOP xap xi Kaggle proxy (REF ≈ +0.72/keo trade-weighted) —
  neu lech nhieu → sai integration (entry timing, universe, capital lock), dieu tra TRUOC khi tin.

## 5. Diem can Uni chot [?]
1. **REF co nen la no-SL that khong**, hay REF nen co san disaster-SL (vi no-SL nhanh chua-arm =
   lo hong duoi trai 2026)? Neu REF=no-SL: +SL do dung dong gop SL. Neu REF co-SL: doi B0.
   → **Draft chon REF = no-SL** (do sach dong gop tung tru), disaster-SL thuoc nac +SL.
2. **Entry tre 1 nen = 1m hay 15m?** (edge 15m → tre 15m la thuc te vao lenh sau khi thay tin hieu).
3. **Universe B0 "take-all"**: toan ff-candidate (da qua EntrySignalFilter) hay toan coin? (anh huong
   B0 lam moc so sanh entry-edge).
4. **Sim moi hay tai dung `SimulatorMarketLevelTicker1MStopLoss`?** Class do da co logic 1m+SL+trailing
   — neu khop, harness chi = adapter doc ev2_preds + config 5-nac, KHONG viet sim tu dau (re + it bug).
   → **Draft: uu tien tai dung**, chi viet adapter + config. Xac nhan sau khi doc class.

## 6. Buoc trien khai (sau khi Uni chot)
a. Doc `SimulatorMarketLevelTicker1MStopLoss` + nguon kline → chot tai-dung hay viet moi.
b. Adapter: doc ev2_preds_n6.csv.gz → danh sach entry per-window; config 5-nac (enum LADDER_STAGE).
c. Function-test 1 window (validate small): so PnL vs Kaggle proxy REF.
d. wfo_fanout 17 window cho tung nac → bang ladder + pass-criteria.


---

## 7. INTEGRATION CHOT (2026-07-17) — tai dung WFO hien co, KHONG viet sim moi

### Duong cam EV2 preds vao sim (da co san infra)
`WfoDataset.buildFundingFromWfFiles(predDir, horizonIdx)` doc `predict_wf_*.bin` (26B BE: q ts, h symId,
4f p4/p12/p24/p72), encode long=(symId<<32)|floatBits(1−p_win), forward-fill 15m->phut. Engine chon
score THAP = P(win) CAO. → EV2 chi can convert CSV -> predict_wf format la cam thang, KHONG dung data pipeline.
- Converter: `orchestrator/tools/ev2_csv_to_predictwf.py` (cam p6 vao ca 4 slot).
- Build dataset: WfoDataset.export voi WFO_FUNDING_PRED_DIR=<predict_wf moi> -> funding.bin moi;
  tai dung market.bin+pred.bin cu (hoac re-scan Aerospike ~40s). Sim doc qua WFO_DATA_DIR.

### ⚠️ RUI RO PHAI VERIFY TRUOC: symId alignment
symId trong predict_wf PHAI khop symId-space cua sim (SimpleSymbolMapper/226). ev2 export dung
symbol_map.csv cua funding-label-full. Gate-check: so symId trung + range vs predict_wf CU truoc khi tin.
Neu lech -> entry gan sai coin -> ket qua rac.

### Ladder -> Configs mapping (da doc code OrderTargetInfoTest.updateStatusNew)
- `HARD_STOP_LOSS_RATE` (disaster-SL lenh chua-arm, chi PREDICT_SYMBOL_TRADE): REF=0. BO price-SL (chan 3
  da chung minh hai) -> giu 0 moi nac.
- `TIME_STOP_HOURS` (time-stop lenh CHUA-arm): dat 4 (REF) / 24 (+TR horizon).
- Trailing arm: tu dong khi co lai (updateStatusNew set priceSL -> updateTPSL keo len), dieu boi
  `TS_PROFIT_MULTIPLIER`. RATE_PROFIT_STOP_MARKET gate khi nao bat dau xet.
- **BO SUNG CAN CODE (nho): `LADDER_FORCE_TIMESTOP`** — hien time-stop CHI ap lenh chua-arm; mac dinh
  logic = "arm roi let-winner-run" (≈ +TR). De co REF thuan dong-4h phai buoc time-stop CA lenh da-arm.
  1 flag env + 1 nhanh if trong updateStatusNew/updateTPSL. TAT (=0) -> hanh vi cu (=+TR).

### Ladder config cu the
| Nac | HARD_STOP_LOSS_RATE | TIME_STOP_HOURS | FORCE_TIMESTOP | trailing |
|---|---|---|---|---|
| REF (dong 4h) | 0 | 4 | 1 (buoc dong ca da-arm) | off (bi force-timestop cat) |
| +TR nuoi24 | 0 | 24 | 0 (let-winner-run) | on (mac dinh) |
| +TR nuoi72 | 0 | 72 | 0 | on |
- B0 (take-all) = bo gate selector (nhan moi candidate) — cach tat gate can xac nhan trong entry logic.

### Buoc trien khai con lai (cho Uni gat build)
a. Convert + build 1 WFO dataset (EV2 funding) + gate-check symId. [safe, chua build jar]
b. Them flag LADDER_FORCE_TIMESTOP (nho, TAT=hanh vi cu bat bien). [code]
c. Build jar local -> function-test 1 window REF -> gate-check PnL/keo ≈ Kaggle proxy REF (+0.72 TW). [build]
d. Neu khop -> wfo_fanout 17-window cho REF, +TR24, +TR72. [chay full]
