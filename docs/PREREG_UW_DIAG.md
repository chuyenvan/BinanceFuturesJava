# PREREG_UW_DIAG — TASK B2 Buoc 1: chan doan nguon UW (2026-09-21)

Nguoi soan: executor Sonnet, theo thiet ke MASTER `TASK_B2_breadth_UW_design.md` muc 2.
Khoa dinh nghia/cong thuc TRUOC khi doc ket qua so; script chay 1 lan, sua 1 bug bien
(`streak_dynamics("T100", ...)` -> `streak_dynamics(TAGS["T100"], ...)`, KHONG doi logic/nguong)
roi chay lai — khong co nguong/dinh nghia nao bi sua SAU khi thay so.

## 0. Pham vi — 0-SIM, chi doc du lieu da co

Nguon: `printDone.csv`/`sim.out` cua 3 run da co san trong `/home/ubuntu/java/devrun/`:

| Ten ngan | Run tag | Y nghia |
|---|---|---|
| T170 | `X1_GS_T170_2021` | incumbent, gate=1.70, UW=92 (moc TASK B) |
| T100 | `X1_C3_FULL_2021` | gate=1.0 KHONG pacing (baseline TASK A/B), UW=248 |
| P3 | `X1_C3_FULL_2021_PACING_P3` | gate=1.0 + pacing bigdown BD1a gamma=0.5 (TASK B), UW=248 |

BTC 1h: `CLOSES_1H.bin` qua `bigdown_struct.hourly_grid()` (TAI DUNG NGUYEN VAN, khong sua).
KHONG chay sim, KHONG xgboost, KHONG sua `.java`. KHONG dung P0 (da co so trong
`docs/RESULT_PACING_BIGDOWN.md`: UW=221, cung bac do — khong doi ket luan, khong can do lai).

## 1. Ham tai dung NGUYEN VAN (khong sua 2 file goc)

Tu `research/analysis/bigdown_struct.py`: `hourly_grid()`, `build_bd_flags()`, `load_trades_utc()`,
`block_boot_mean()`. Tu `research/analysis/c3_rates.py`: `trades()`, `equity()`.

## 2. Dinh nghia khoa — script moi `research/analysis/uw_source.py`

**Q1 — chuoi UW (RLE tren `C.equity(tag)`, CUNG dinh nghia UW da dung trong `x1_rates.py`
va PREREG_PACING_BIGDOWN — khong bia dinh nghia moi)**: voi `uw = equity < equity.cummax()`,
gom cac ngay lien tuc `uw=True` thanh 1 chuoi; ghi start/end/do dai/do sau (min drawdown% trong
chuoi)/ngay trough. Lay top-5 chuoi dai nhat moi tag.

**Q2 — regime BTC (CAUSAL, TRAILING — dung duoc lam dinh nghia cho pacing buoc 2)**: tu gia BTC
1h quy ve ngay LOCAL (GMT+7, khop lich equity): `close` = gia dong cua cuoi ngay; `MA200` =
trung binh truot 200 ngay (min_periods=60); `dd_from_peak365` = `close/rolling_max(365d)-1`
(rolling max TRUOT, khong nhin truoc); `ret30`/`ret60` = % thay doi gia so voi 30/60 ngay truoc.
Bao cao cho chuoi UW dai nhat cua T100/P3 (cung 1 cua so lich) va cua T170 (cua so rieng cua no)
de doi chieu.

**Q3 — core/marginal/unscaled (TAI HIEN CONG THUC `EntryGate.threshold()`, KHONG khoa
(sym,start) — thay the phep khoa key da biet KHONG dang tin cay o TASK A M7, match_rate 32.6%)**:

```
thr(symbolPred) = THR_BASE * max(DYN_MIN, (symbolPred/SCORE_BASE)*DYN_MULT) * gateScale
PASS <=> pred15m >= thr
THR_BASE=0.008 (SIM_MIN_MOMENTUM_15M, giong het o ca x1_c3_full*.properties va x1_gs_t170.properties)
DYN_MIN=0.26787, SCORE_BASE=0.15, DYN_MULT=1.28760 (hang so EntryGate.java, doc-only)
```

Voi tung dong co `symbolPred`/`pred15m` (nhanh dyn cua gate): **core** = pass ca gateScale=1.70
(se duoc T170 nhan); **marginal** = pass gateScale=1.0 nhung FAIL 1.70 (CHI duoc gate-1.0 nhan).
Dong `symbolPred` rong (BIG_DOWN/DCA_LEVEL1/leg market-signal, theo javadoc EntryGate.java —
nhanh nay KHONG bi gate scale) -> **unscaled** (co mat o CA hai gate nhu nhau). Day la phep
phan loai CHINH XAC tung dong (khong xap xi, khong key-match) vi dung dung cong thuc gate that.
Bao cao: so luong + ROI trung binh (block-72h bootstrap CI90 qua `block_boot_mean`) + ty trong
dong gop vao tong PnL AM, TRONG cua so UW dai nhat vs NGOAI cua so, cho ca T100 va P3.

**Q4 — dao sau hay khong phuc hoi**: trong chinh cua so UW dai nhat cua tag, tren `C.equity(tag)`:
ty le ngay tang/giam/dung yen; do lech chuan return ngay (so voi ca ky); so "rally" (>=3 ngay
tang lien tuc); `max_partial_recovery_pct_of_depth` = (dinh cao nhat dat duoc trong cua so -
day)/(dinh truoc do - day) *100 — gan 100% nghia la co luc hoi gan sat dinh cu ma van chua vuot;
so lenh MO trong cua so (tren ngay) so voi trung binh ca ky, va thoi gian giu lenh trung binh
(ngay) cua lenh mo TRONG cua so so voi NGOAI cua so.

**Q5 — T170 trong CUNG lich (dung cua so cua T100, la nguon UW=248)**: so lenh T170 mo/ngay
trong cua so so voi trung binh ca ky (ty le, KHONG phai hieu so tuyet doi) + thoi gian giu lenh
trung binh cua lenh mo trong cua so so voi ca ky; doi chieu chuoi UW rieng cua T170 (o dau, sau
bao nhieu) de xem T170 co dung UW trong CHINH cua so nay khong.

## 3. Khong co nguong GO/NO-GO o buoc nay

Day la chan doan MO TA (khong phai kiem dinh gia thuyet co nguong PASS/FAIL) — cong quyet dinh
cho buoc 2 la ĐINH TINH: co dinh nghia duoc mot bien regime CAUSAL, do duoc, giai thich duoc phan
lon UW hay khong; va cau tra loi Q3/Q4 chi ra co che dung la admission-filter hay exit. Ket luan
ghi trong `docs/DIAG_UW_SOURCE.md` sau khi chay, KHONG sua lai file nay retroactive.

## 4. An toan

Khong dung P0/P3 khac tag runtime, khong ssh 242, khong push, khong holdout 2026 (grid dung
`hourly_grid()` da chan cung ap dung nhu cac script khac, t1=2026-01-01 exclusive). `free -g`
kiem truoc khi chay (16G available luc chay), `pgrep java` chi thay shadow-c3 dang chay (khong
dung shadow-c3 — 0-sim, dung tai nguyen it). Khong sua `bigdown_struct.py`/`c3_rates.py`.
