# SHADOW_EVAL_20260911 — danh gia so giay C3 tren 242 sau 4.3 ngay (07/09 06:29 -> 11/09 14:00)

> ## 🚨 CANH BAO DOC LAI (audit `3a36f02`, 2026-09-11)
>
> **So giay C3 tren 242 trong cua so 07-11/09 chay GATE PHANG, khong phai gate dong cua sim.**
> `DetectEntrySignal2TradeNormal:656` bo `checkSignalDynamic` khi `SELECTOR_RANK_TOPK>0`
> (commit `311bb29`), con sim LUON goi no. `dyn_thr = 0.008*max(0.26787, symbolPred/0.15*1.28760)`
> = **0.0172-0.0240** voi top-8 vs nguong phang **0.008**. He qua do duoc:
> **77/78 entry** cua cua so nay se KHONG ton tai neu live chay gate nhu sim, va nhip vao lenh
> **17.0 entry/ngay** vs **1.37 entry PST/ngay** cua `X1_C3_FULL_PARITY_R` = **~12 lan**.
> => **So giay nay KHONG phai `C3_FULL`**; goi no la "so giay C3" la sai ten.
>
> **Doc the nao:**
> - 🟢 **VAN DUNG**: cau truc **lo tung lenh** / hinh dang phan phoi ret / co che collapse
>   (chung do tren tung lenh da vao, doc lap voi so luong lenh).
> - 🔴 **KHONG DUNG**: moi so sanh ve **NHIP** (entry/ngay), **SO BAG dang mo**, ty le
>   lenh mo tren equity, va moi ket luan dang "live bam sat sim" dua tren dem so lenh.
> - Con so 48 thang cua chien luoc gate phang: `docs/prereg/PREREG_FLATGATE.md` / `docs/result/RESULT_FLATGATE.md`.
> - Patch sua live cho khop sim: `docs/experiment/L6_GATE_DYN_FIX.md` (**chua deploy**).


READ-ONLY (grep log + ledger + MTM qua Binance fapi ticker). Du lieu tho: `/root/shadow_eval_20260911/` tren 242.
Benchmark cung ky: BTC -3.83%, ETH -1.84% (open 07/09 -> 11/09 14:00).

## 1. KET QUA CHINH — realized dep, mark-to-market AM
| | gia tri |
|---|---|
| Lenh da dong | **51**, 51/51 TRAILING_STOP co lai, realized **+$2,245** (avg +$44, ret median **+7.00%** = dung nguong arm, min +3.5%, max +56%) |
| Hold lenh dong | median **2.9h** (min 0.3h, max 59h) |
| Lenh dang mo | **27**, notional $14,104 (40% paperEquity 35k), **26/27 duoi gia von**, ret trung binh **-22.5%** |
| Unrealized | **-$3,319** (SOPH -64%, IOST -55%, COLLECT -52%, CYS -40%, MARSCOIN -36%, USELESS -32%, 4 -32%...) |
| **MTM net** | **-$1,074 = -3.07%** paperEquity (deployed -7.6%) — CHUA tinh phi/funding |
| Time-stop 168h | lo dau tien 14/09 07:14 (5 lenh 07/09: PONS -21%, MARSCOIN -36%, FLOCK -20%, ARB -24%...) => realized se giam manh tu 14/09 |

**Doc dung:** "100% win" chi la survivorship cua tap DA DONG — exit duy nhat la trailing (arm +7%), loser
khong bao gio dong truoc 168h. Ket qua that = realized + unrealized = **am**.

## 2. CO CHE SINH LO — 3 diem cau truc (khong phai bug, backtest cung the)
1. **Re-entry chain tren cung coin dang pump**: IOST 9 lenh dong + 1 mo (-55%), USELESS 6+1 (-32%), BULLA 6+1 (-24%),
   SOPH 5+1 (-64%), AKE 4+1 (-27%), BTR 4+1 (-22%), UAI 4+1 (-20%), VVV 3+1 (-13%). Moi lan trailing thoat +7% thi
   S1 lai xep coin do top (feature ret_3d/hrs_since_high/dd_7d thuong coin gan dinh) => vao lai => nguoi cuoi giu bag.
2. **Bat doi xung payoff**: thang bi cap ~+7% (median dung bang arm, trailing lien tuc thoat ngay khi arm), lo khong
   cap toi 168h (-20..-64%). 51 thang x $44 = $2,245 < 27 lo x -$123.
3. **Book bi ket (cap-then-skip)**: [MAP] top-8 luc 11/09 13:45 = CYS/COLLECT/MARSCOIN/STAR/BTR/RAYSOL/FF/VELVET — 7/8
   la coin DANG GIU (deu am nang) hoac LEGACY. S1 xep coin da sap manh len dau (dd_7d lon = maxFav_72h ky vong cao).
   Vi the dang giu VAN chiem slot rank => moi tick chi mo duoc <=1 lenh moi: entries/ngay 23 -> 21 -> 18 -> 12 -> 4.

## 3. TUNG TANG — van hanh SACH
- **Process**: 28 lan JVM start (auto-restart 4h + 3 lan deploy dau 07/09), 0 loi warm-up S1, RSS 1.73G, 0 lenh that (SHADOW_NO_PUSH OK).
- **Selector pred / gate**: return15M median 0.0084-0.0093/ngay, p25 0.0072-0.0084 vs Min15M 0.008 => gate nam SAT nguong,
  lat 9-39 tick/ngay bi [PREDICT fail] (10-40%). OI-GUARD 0. Day la dieu kien drift ma nhanh rolling gate nham tro
  (xem `docs/audit/AUDIT_GATEDYN_GD92.md` — chua chung minh duoc loi o DEV).
- **S1**: 96 tick/ngay, score 610-634 coin, ready 599-624, 0 skip tick. [MAP] p50 0.33-0.62 (trong [0.20,0.70]),
  n_coins 502-694.
- **Trade/parity**: entry px = close nen 1m truoc ts log: 4/5 KHOP tuyet doi (BTR, FF, XAN, RAYSOL); **VTHO lech 0.12%**
  (0.0006865 vs 0.0006857) — coin mong, can xem nguon gia (kline_1m_opt vs REST). Rank ledger khop quy uoc cap-then-skip.
- **Trailing**: arm ~= would-CLOSE moi ngay (7/7, 19/19, 17/16, 6/7, 2/2): arm xong thoat gan nhu ngay trong ngay,
  peak 7-22%, exit ~ +7-9% => give-back lon o lenh pump manh (IOST peak 22.5% thoat +19.5%, SOPH peak ? thoat +56%).
- **LEGACY**: 66 -> 63 (3 vi the that dong theo HEAD). ERR non-HTTP: 1 (P2P GOAWAY, vo hai).

## 4. KET LUAN / RUI RO
- 4.3 ngay, 51+27 lenh: **KHONG du de ket luan edge**; nhung buc tranh MTM am va co che ket book la THAT, khop canh bao
  "collapse-risk" runbook §11. Neu day la tien that: -$1,074 tren 35k, va se hien thuc hoa dan tu 14/09.
- Cau hoi cho backtest (KHONG tune live): (a) backtest C3_FULL co tai hien duoc phan phoi "27 lenh mo avg -22% sau 4 ngay"
  trong tuan alt-dump khong (do MTM theo ngay, khong chi printDone)? (b) re-entry cung coin sau trailing co bi gioi han
  trong sim khong? (c) hard SL / time-stop ngan hon co pre-reg duoc khong — la thay doi luat dong, phai qua PREREG.
- KHONG sua gi tren 242. KHONG doi env. Chi bao.
