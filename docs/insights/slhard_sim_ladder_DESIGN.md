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
