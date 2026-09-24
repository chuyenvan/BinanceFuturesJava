# PRE-REG — LIVE/SHADOW (forward) vs SIM: kiem tra KHOP/NOI SUY

Ngay 2026-09-23. Chot TRUOC khi tinh bat ky chi so nao. Moi so duoi day la **MO TA**,
KHONG phai cuoc thi giua hai nhanh. **KHONG tune** — neu sau khi doc so muon doi bat ky
tham so nao (gate, DCA, time-stop, selector...) thi phai mo PREREG MOI.

## 0. LUAT CUNG
- Chi Oracle. KHONG SSH ghi/sua/kill tren 242 (neu can lay `archive_flatgate_*` thi ssh **chi doc**
  `cat`/`scp` ve `/home/ubuntu/live242/`).
- KHONG chay Java tren Oracle (shadow dang active). **Thuan Python.**
- KHONG dung `claude-run` / Claude Code.
- KHONG push. Khong sua du lieu nguon.
- Holdout 2026 KHONG bi mo: du lieu live/shadow KHONG phai backtest 2026.

## 1. PHAN DINH BANG CHUNG — DAY LA FORWARD, KHONG PHAI HOLDOUT BACKTEST
- `/home/ubuntu/shadow_c3/ledger.csv` la **lenh THAT cua nhanh live** (paper: `SHADOW_NO_PUSH=true`,
  khong push lenh len san) chay tren du lieu ticker that 2026. Day la **bang chung FORWARD**.
- **KHONG** phai ket qua backtest, **KHONG** mo seal holdout 2026 cua sim (sim T170 ket thuc
  2025-12-01).
- He qua bat buoc: **KHONG duoc dung tap nay de chon/tune bat cu tham so nao** (neu tune theo no
  thi mat tinh forward). Moi ket luan chi o muc "khop hay lech, lech o dau".

## 2. NGUON DU LIEU (da xac minh ton tai)
| Nguon | Noi dung | Hash |
|---|---|---|
| `/home/ubuntu/shadow_c3/ledger.csv` | **65 lenh da dong** (TRAILING_STOP 58, TIME_STOP_168H 7) | md5 `11121bf9e3b164d41dbd342c1273a947` |
| `/home/ubuntu/shadow_c3/ledger_from_log.csv` | **60 dong entry** (18-19/09, 100% `PREDICT_SYMBOL_TRADE`) | md5 `922fdfc1ca3c96ccef007961bd198233` |
| `/home/ubuntu/shadow_c3/open_positions.csv` | 9 vi the mo + dong `#realized` | md5 `96e3d3f87a57662749bbe3562911f0bb` |
| `/home/ubuntu/java/devrun/X1_GS_T170_2021/storage/printDone.csv` | sim T170, **n=1089 leg / 1069 cum** | md5 `efb793e2468ca3a7318da0f0ad23d4fc` |
| 242 `archive_flatgate_20260912_060749/ledger.csv` | 51 lenh (11/09) — **chi lay neu can them mau** | (chua lay) |

Da xac minh:
- `ledger.csv` chi co lenh vao **3 ngay**: 06/09 (14), 18/09 (25), 19/09 (26).
  07-17/09 = process shadow CHET (xem `docs/result/RESULT_SHADOW_T170_FIX.md`) ⇒ **khong co du lieu**.
- Shadow vao lenh tren luoi 15m (phut :14/:29/:44/:59), toi da **8 lenh/tick** (= TOPK).
- 65 lenh chi tren **24 coin** (AKE 10, BR 8, ONE 7, SYN 6, G 5...) ⇒ co chuoi re-entry.

## 3. CHUAN HOA — SO THEO NOTIONAL, KHONG SO PnL TUYET DOI
Von hai ben khac nhau (live/paper `PAPER_EQUITY`+`CAPITAL_START`=14000 tren 242 goc, sim 35000)
⇒ **KHONG** so PnL tuyet doi, KHONG so equity.
- Shadow: `notional = qty × entry`; `ret_gross = (exit_price - entry)/entry` (== `pnl/(qty*entry)`).
- Sim: cot `margin` **THUC RA la NOTIONAL** (`calMargin() = quantity*priceEntry/leverage`,
  leverage=1; da kiem: `margin/(quantity*entry)` = 1.0 tren 200 dong dau —
  xac nhan doc lap voi `research/analysis/beta_decomp_t170.py`).
  `notional = quantity × entry` (= cot `margin`).
  `ret_gross = profit/100` (cot `profit` = `rateOf2Double(priceTP, priceEntry)*100`, **gross**).
- Moi chi so PnL bao bang **% notional**.

### 3.1 BAT DOI XUNG CHI PHI (phai ghi ro, khong duoc giau)
- **Shadow `pnl` = GROSS**: `ShadowBookC3.closeAt` tinh `pnl = (exit - entry)*qty`, KHONG tru phi.
  (Kiem so cheo 2 dong dau ledger: FLOCK 0.07354→0.0775847 qty 12717 ⇒ 51.4364 = dung cot `pnl`.)
- **Sim `pnl` = NET**: `OrderTargetInfoTest.calTp()` = gross − `RATE_FEE`(0.002, 2 chan)
  − `SLIPPAGE_RATE`(0.003×2, `APPLY_SLIPPAGE=true`) − funding ⇒ **~0.8% notional/lenh**.
⇒ Vi vay **chi so CHINH la gross** (so duoc hai ben). Chi so net chi bao kem, va khi bao phai
neu ro shadow khong co mo hinh phi. Khi so net: dung them 2 muc phi gia dinh cho shadow
`c ∈ {0.008 (bang sim), 0.001 (xap xi taker 2 chan that)}` — day la **gia dinh**, ghi ro.

## 4. ANH XA `reason` (shadow) ↔ `status` (sim)
| shadow | sim | Chat luong anh xa |
|---|---|---|
| `TRAILING_STOP` (58) | `STOP_MARKET_DONE` (983) | **1-1 ve y nghia** (thoat khi da arm duong) |
| `TIME_STOP_168H` (7) | `STOP_LOSS_DONE` (106) | **KHONG 1-1**: sim gop ca hard priceSL + loser time-stop 168h (`SimulatorMarketLevelTicker1MStopLoss:869/977` deu set `STOP_LOSS_DONE`), sim KHONG co nhan rieng cho time-stop |
⇒ Bao ca (a) **toan bo** va (b) **tap map duoc** (`TRAILING_STOP` vs `STOP_MARKET_DONE`).

## 5. CAC CHI SO SO SANH (chot truoc)
1. **Tan suat** — bao DONG THOI 4 cach dem de tach "khac cach dem" khoi "khac that":
   (i) lenh/ngay theo **lich** (span ngay dau→cuoi); (ii) lenh/**ngay hoat dong**;
   (iii) lenh/**slot vao lenh** + so lenh/slot; (iv) **so coin khac nhau**/ngay.
2. `win%` (ret_gross > 0), theo 2 tap cua muc 4.
3. `PnL/notional` **mean + median** (gross), va net theo muc 3.1.
4. Phan bo theo `market_level`/`level` (shadow vs sim).
5. **Thoi gian giu lenh** (gio): shadow `ts_exit - ts_entry`; sim `end - start` (GMT+7 naive).

## 6. CI — BLOCK BOOTSTRAP THEO NGAY (72h), VA CANH BAO N
- Bootstrap block 72h co hoan lai, `NREP=2000`, `seed=20260923`; **moi ben rut doc lap**
  (khong ghep cap duoc: hai ben khac lich su + khac universe).
- **N RAT NHO**: shadow chi co 3 ngay co lenh (18-19/09 = 2 ngay cho cau hinh T170) ⇒ so block
  ~2-3 ⇒ CI gan nhu bang toan bo mien gia tri. **Ket qua chi la MO TA, khong phai ket luan
  thong ke.** Se bao ca CI cua sim (rong hon) de doi chieu, va noi ro khi CI chong lan nhau
  thi KHONG duoc doc la "khac biet".
- Do lech phu thuoc block: bao them mean tung ngay de lo tinh khong-dung.

## 7. KET LUAN — TIEU CHI DOC (chot truoc)
Day la **kiem tra khop/noi suy**, khong phai cuoc thi. Phai ket luan theo 3 nhanh:
- **R1 KHOP** (mean/median `ret_gross`, `win%` nam trong vung chong lan CI / chenh < 1pp):
  ⇒ shadow noi suy duoc sim o muc ket qua moi lenh.
- **R2 LECH, shadow XAU HON**: goi y entry/exit live khong tai lap duoc sim (hoac `gate`/selector
  khac) hoc phi sim dat hon that ⇒ **cung dau** voi gia thuyet "sim tinh chi phi 2-5× that".
- **R3 LECH, shadow TOT HON**: xem co phai do (a) shadow khong tru phi (gross) —
  TRUONG HOP NAY KHONG CHUNG MINH DUOC GIA THUYET CHI PHI, vi khac biet nam hoan toan o muc
  dinh nghia chi phi; hay (b) that su khac alpha.
Quy tac: **neu khac biet gross ≈ 0 nhung net lech ~0,8pp/lenh ⇒ chi la khac biet MO HINH PHI**,
KHONG duoc goi la bang chung "sim dat hon that 2-5×" (muon vay phai co bang chung phi THUC cua
san, khong co trong tap nay).

## 8. GIAI THICH CHENH LECH TAN SUAT "7×" — kiem 4 gia thuyet (chot truoc)
(a) **khac cach dem**: "32 lenh/tuan" = 65 lenh ÷ **14 ngay lich** × 7; nhung 12/14 ngay shadow CHET.
(b) **khac config**: lo 06/09 (14 lenh) chay **gate phang 0.008** (truoc fix 18/09, xem
    `docs/analysis/SHADOW_EVAL_20260911.md` + `docs/experiment/L6_GATE_DYN_FIX.md`); lo 18-19/09 chay gate dyn 1.70
    (env + jar co `entryGate`). Them: `DCA_GRID_WEIGHTS/SCALE` doi sang FLATGRID KEEPLEG0 tu 19/09.
(c) **co che dien book**: 1 tick co the dien du TOPK=8 khi book trong (8 lenh luc 18/09 11:29).
(d) **regime**: 18-20/09 la dot hoi phuc sau dump ⇒ gate/selector de pass hon trung binh 4,4 nam.

## 9. SAN PHAM
- `docs/result/RESULT_LIVE_VS_SIM.md`: bang so sanh + CI + ket luan (khop/lech, lech o dau, co dau hieu
  gi ve gia thuyet chi phi khong), ghi RO N nho va KHONG de xuat tune.
- Commit (KHONG push), don temp.
