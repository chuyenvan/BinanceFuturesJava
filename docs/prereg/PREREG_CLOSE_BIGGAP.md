# PREREG_CLOSE_BIGGAP — quet "dinh do bang CLOSE × GIVEBACK LON" tren harness offline

Viet **TRUOC** khi do bat ky so nao (chot 2026-09-23). **Khong sua thiet ke sau khi thay ket qua.**
Nguon: brief owner 2026-09-23 + `docs/result/RESULT_EXIT_FIT.md` (`8f3194f`, `eb4c0de`),
`docs/result/RESULT_CAPACITY_DIAG.md` (`1416031`), `docs/result/RESULT_PEAK_CLOSE.md` (`fa26996`),
`docs/prereg/PREREG_PEAK_CLOSE.md` (`1fcabe4`).

## 0. Cau hoi cua owner (nguyen van)

> Gap hien bi **CAP o 3%/8%** ⇒ lenh 2x/3x chi cach dinh **3-8 diem** ⇒ **rung la bi cat**.
> Muon giveback **to len theo dinh** (dinh do bang CLOSE, theo F3).

Da thu RIENG va deu NULL: cap phang 0.05/0.12 (`RESULT_TRAIL_HINGE`), bac thang L1/L2/L3
(`RESULT_TRAIL_LADDER`), dinh CLOSE (`RESULT_PEAK_CLOSE`, **NO-GO** tren sim that: TSloss% +1.72 ngoai
CI, n −50). **Chua tung thu: dinh CLOSE + gap KHONG bi chan o 3%/8% (cap lon hoac bo cap).**
Vong nay do **dung cai do** — va do bang **thuoc MOI** vi `RESULT_CAPACITY_DIAG` vua chung minh thuoc
rate cu (`meanP`/`win%`/`TSloss%`) **SAI cho exit** (Kendall tau 0.333, 7/21 cap dao hang; F3 hang 2/7
theo `meanP` → **7/7 (cuoi)** theo `Calmar`).

## 1. Rang buoc (chot TRUOC)

1. **KHONG** dung `claude-run`/Claude Code.
2. **KHONG chay Java/sim tren Oracle** (shadow dang `active`) ⇒ vong nay **thuan Python offline**, dung
   lai harness da kiem chung parity. Ket qua **duong** ⇒ chi **de xuat 1 sim Kaggle**, **khong tu chay**,
   **khong tu tich hop**.
3. **DEV only** (2021-07..2025-12); **khong cham 2026**.
4. Trung gian ghi ra **ngoai repo**: `/home/ubuntu/exitfit/biggap/`.
5. **KHONG push**.

## 2. Cong parity (dieu kien tien quyet, phai PASS lai truoc khi quet)

`research/exitfit/parity.py` vs `printDone.csv` T170 (`md5 efb793e2…`, n=1089 leg) phai **PASS** nguyen
cac nguong cua `PREREG_EXIT_FIT` §2.3 (status ≥99%, phut khop ≥97%, ≤2' ≥99%, `tp` ≥95%,
median |ΔPnL no-funding| ≤0.02). Neu FAIL ⇒ **dung**, khong doc so quet.

## 3. Ho tham so (chot TRUOC: 15 policy chinh + 3 phu)

Dinh `peak` luon do bang **CLOSE nen 1m** (nhu F3). Ham gap:

```
gap_rate = min(ratio × peak_rate , cap)          # peak_rate = (peak_close/entry) - 1
rate_SL  = lam_tron_buoc_0.005( peak_rate - gap_rate )
```

Bat bien giu nguyen: `gap ≤ 0.9 × peak_rate` (SL luon > entry), ratchet lien tuc (guard `sl_new > sl` VA
`> entry`), arm 0.07 (theo CLOSE vi dinh do bang close — dung nhu F3), loser time-stop 168h,
`BLOCK_INTRABAR_LOOKAHEAD=true`, khop SL = `min(priceSL, bar.open)`, delist guard, gom leg→cum.

**(A) 15 policy chinh** — tich Descartes `ratio × cap`:

| | cap=0.08 | cap=0.12 | cap=0.20 | cap=0.35 | cap=None |
|---|---|---|---|---|---|
| **ratio 0.5** | BB_50_08 | BB_50_12 | BB_50_20 | BB_50_35 | BB_50_nc |
| **ratio 0.7** | BB_70_08 | BB_70_12 | BB_70_20 | BB_70_35 | BB_70_nc |
| **ratio 0.9** | BB_90_08 | BB_90_12 | BB_90_20 | BB_90_35 | BB_90_nc |

`cap=None` ⇒ gap = `ratio × peak_rate` (chi con chan cung `0.9×peak`). Luu y: `cap=0.08 + ratio=0.5`
= "F3 bo split weak/strong" (F3 dung cap 0.03 khi pred null/yeu, 0.08 khi manh) ⇒ day la diem neo giua
F3 va ho mo rong.

**(B) 3 policy phu (chi de doc, KHONG dung de tuyen nguoi thang)** — bac thang voi dinh CLOSE, tai dung
`TS_LADDER_LO/TS_LADDER_GAPS` cua L1/L2/L3 (`profiles/x1_tl_l1|l2|l3.properties`), chi doi dinh high→close.

**Moc so sanh (chay qua CUNG harness, cung thuoc)**:
- **T170 / P0** = dinh HIGH, `min(peak×0.5, 0.03 weak / 0.08 strong)`.
- **F3** = dinh CLOSE, ham gap P0 (cap 0.03/0.08 theo pred).

**Tong so policy do = 20** (15 chinh + 3 phu + 2 moc) ⇒ multiplicity phai bao cao.

## 4. Split (chot TRUOC, y nhu vong fit)

- **TRAIN 2022-01..2023-12** · **TEST 2024-01..2025-12** · burn-in 2021-07..2021-12 (khong dung chon).
- Theo gio **GMT+7**; don vi = **cum** (=1 lenh vao, gom ca leg DCA).
- **Chi tin ket qua TEST.** TRAIN chi dung de **chan** (policy khong duoc xau di o TRAIN).

## 5. Thuoc do (chot TRUOC — THUOC MOI, khong dung rate exit-lam-tieu-chi)

Chinh (dung de ket luan):

| # | thuoc | dinh nghia |
|---|---|---|
| M1 | `SumPnL` | tong PnL tung cum (no-funding) tren tap |
| M2 | `maxDD%` | dinh-am cua duong **equity proxy** (xem duoi) |
| M3 | `Calmar` = `CAGR% / \|maxDD%\|` | tren chinh equity proxy |
| M4 | `capture ratio` nhom dinh ≥20/50/100% | `exit_rate / peak_high_rate`, lay **trung vi**; **nhom xac dinh bang peak HIGH** (co dinh giua moi policy ⇒ so duoc voi `RESULT_CAPACITY_DIAG` §2.3) |
| M5 | `n` cum, `hold` (gio giu, trung vi + tong), `turnover` | `Σ(end−start)/(so ngay×24h)` |

Phu (chi bao cao, **khong** dung de chon): `meanP`, `win%`, `TSloss%`, `avg_peak`, `avg_exit_rate`.

**Equity proxy (chot TRUOC dinh nghia):** xep cum theo **thoi diem THOAT**, cong don `SumPnL` theo **ngay
thoat** ⇒ `equity(t) = 35000 + cumPnL(t)`; `CAGR% = (eq_end/35000)^(365/so_ngay) − 1`;
`maxDD%` = dinh-am lon nhat cua `equity(t)` so voi dinh chay.
🔴 **Gioi han ghi TRUOC:** proxy nay **khong** co sizing/compound va **khong** mark-to-market vi the dang
mo ⇒ `maxDD%` la **can duoi** cua maxDD that. No chi dung de **SO SANH giua cac policy** (cung mot do
phan giai), khong doc nhu so tuyet doi.

**Cong kiem chung thuoc (chot TRUOC, phai bao cao):**
1. `SumPnL` P0 (toan DEV) phai ~ `equity_final − 35000 = 76 070` (sim that) — sai lech < 2% ⇒ thuoc khop.
2. **Huong Calmar proxy** cua P0 phai **> F3** — vi sim THAT da do P0 Calmar 4.64 > F3 3.52
   (`RESULT_CAPACITY_DIAG` §2.1). Neu proxy dao huong nay ⇒ **bao RO proxy khong dung duoc**, va **khong**
   dung M2/M3 de ket luan (chi con M1 + M4), ghi ro.

## 6. TIEU CHI KET LUAN (chot TRUOC)

Voi moi policy `X` (so voi **P0/T170**, tren TEST):

- **(a) huong tot o TEST:** `SumPnL_X > SumPnL_P0` **VA** `Calmar_X > Calmar_P0`.
- **(b) khong xau di o TRAIN:** `SumPnL_X ≥ SumPnL_P0` **VA** `Calmar_X ≥ Calmar_P0` (TRAIN).
- **(c) y nghia thong ke:** CI bootstrap **block-ngay** (2000 rep, seed `20260923`, nhan do rong **×1.21**
  theo chuan repo, **×sqrt(2 ln 15)** cho multiplicity 15 policy) cua hieu `net/trade` TEST
  (`X − P0`) phai **khong chua 0**.

| ket qua | phan quyet |
|---|---|
| (a)+(b)+(c) | **CO policy hon** ⇒ **de xuat 1 sim Kaggle** (khong tu chay) |
| (a)+(b) nhung khong (c) | **"CHUA DU KET LUAN"** + ghi so, **khong** de xuat |
| chi `capture` (M4) tang, M1/M3 khong | **"CHUA DU KET LUAN (capture-only)"** + ghi so |
| khong policy nao dat (a) | **NULL** — ghi RO + dong huong (co nen quay lai nua khong) |

**Bat buoc bao cao:** so policy da thu (multiplicity), va **bao cao ket qua xau nhat** (khong chi khoe
ket qua dep).

## 7. Ket qua ghi vao

`docs/result/RESULT_CLOSE_BIGGAP.md`; trung gian: `/home/ubuntu/exitfit/biggap/` (resume duoc; script
`research/exitfit/sweep_biggap.py`). Commit tren branch `module`, **khong push**. Don temp sau khi xong.

## 8. Gioi han (ghi TRUOC, khong phai bao chua sau)

1. Replay **khong** mo phong entry/sizing/von ⇒ `SumPnL` la tong PnL tung lenh; `Calmar` la proxy (§5).
2. **Funding** bi loai (khong co nguon rate offline) — funding phu thuoc thoi diem dong nen chenh giua
   cac policy la bac 2; ghi ro neu chenh lon.
3. Moi so la **in-sample DEV** ⇒ ket qua duong van chi la **UNG VIEN**, can forward/sim xac nhan.
4. Nhom `≥ X%` la **hau-chon theo dinh da xay ra** ⇒ **khong** duoc doc nhu bang chung GO.
5. Harness da parity voi **P0 (high)**; che do **close** (F3) da duoc chay **sim that** va khop harness
   (xem `RESULT_PEAK_CLOSE`) ⇒ khong can parity lai cho close, nhung harness **khong** tai hien duoc phan
   entry bi doi do giu lenh lau hon (n −50 cua F3 tren sim that) — ghi ro: n cua harness la **n cua T170**.
