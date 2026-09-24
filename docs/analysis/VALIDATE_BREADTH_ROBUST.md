# VALIDATE_BREADTH_ROBUST — kiem tra robustness breadth-regime (2026-09-21, executor Sonnet, 0-sim)

Nhiem vu giao boi MASTER sau khi TASK B2 Buoc 5.2/5.3/6 xac dinh breadth top-50/MA200/50% (dinh
nghia A) la regime DUY NHAT (trong 7 cach) phu duoc ca UW-2022 lan UW-2025 (>=60%). Cau hoi: ket
luan do co ROBUST khi doi universe/tham so hay chi dung o mot diem cau hinh (top-50/50%)? Day la
VALIDATE ROBUSTNESS — bao TAT CA to hop, KHONG chon winner.

HOAN TOAN 0-sim: khong chay Java, khong xgboost, khong build, khong sua `.java`. Tai dung nguyen
van `research/analysis/trend_rank_ic.load_closes()` va cac ham cua `research/analysis/breadth_regime.py`
(`day_id`, `build_daily_close_by_sym`, `up_matrix`, `breadth_from_up_matrix`, `pct_notup_by_year`,
`window_pct_notup`, `gate_verdict`) — khong sua 2 file goc do. Script moi:
`research/analysis/breadth_robust.py`. Ket qua so: `research/analysis/out/breadth_robust.json`,
chuoi breadth-score: `research/analysis/out/breadth_score_series.csv`.

Du lieu: `CLOSES_1H.bin` loc `ts<2026-01-01` (HOLDOUT rule, nguyen van). SIM range = `2021-07-01`..
`2025-12-31` (1645 ngay), giong cac round breadth truoc. UW-2022 = `2021-11-16..2022-07-21` (248
ngay), UW-2025 = `2025-03-04..2025-10-16` (227 ngay) — khong tinh lai, dung nguyen dinh nghia da
khoa o Buoc 1/chan doan UW-2025. Nguong GO/NO-GO cho tung to hop = phu >=60% CA HAI chuoi UW
(giong nguong da dung o Buoc 5.2/5.3, KHONG doi).

Universe: `top30`/`top50`/`top100` = symId 1..N theo thu tu niem yet Binance Futures (PROXY, giong
cac round truoc — KHONG phai xep hang volume rolling thuc, xem `docs/prereg/PREREG_BREADTH_REGIME_DIAG.md`
SS1). `all` = **all-coin-song** — TOAN BO 627 symId co du lieu trong `CLOSES_1H.bin` (khong gioi
han topN), moi ngay chi tinh tren so coin thuc su "song" (co gia) tai t — giai quyet dung van de
ty le phu: so coin song/ngay tang manh 2021->2025 (xem bang duoi).

## 0. So coin "song"/ngay theo universe (2021-2025)

| universe | 2021 (min/median/max) | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| top30 | 30/30/30 | 30/30/30 | 30/30/30 | 29/30/30 | 29/29/29 |
| top50 | 50/50/50 | 50/50/50 | 50/50/50 | 48/50/50 | 48/48/48 |
| top100 | 98/100/100 | 100/100/100 | 100/100/100 | 98/100/100 | 97/98/98 |
| **all** | **112/123/130** | 129/136/146 | 144/187/239 | 239/267/347 | **347/463/588** |

top30/50/100 (proxy theo thu tu niem yet) gan nhu KHONG doi so luong qua 5 nam (day la nhom coin
niem yet som nhat, hau nhu tat ca con song lien tuc) — day chinh la diem yeu cua proxy: no KHONG
phan anh viec thi truong 2021 thuc te chi co ~110-130 coin con 2025 co ~470-590 coin. **all-coin**
thi bam sat dung thuc te tang truong universe nay (112->588), nen la phep thu robustness dung dan
nhat cho van de "ty le phu doi theo nam" ma nhiem vu neu ra.

## 1. Sweep robustness day du — 24 to hop (4 universe x 2 MA x 3 nguong)

Cot GO = phu >=60% CA UW-2022 lan UW-2025.

| universe | MA | nguong | UW-2022 % | UW-2025 % | GO | %yeu/nam 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|:---:|---:|---:|---:|---:|---:|
| top30 | 100 | 40% | 81.5 | 50.7 | KHONG | 38.6 | 85.2 | 53.7 | 53.6 | 61.6 |
| top30 | 100 | 50% | 91.1 | 55.5 | KHONG | 50.0 | 90.7 | 56.7 | 57.7 | 65.5 |
| top30 | 100 | 60% | 94.4 | 65.2 | **DAT** | 53.8 | 93.2 | 59.2 | 61.7 | 73.2 |
| top30 | 200 | 40% | 87.9 | 63.4 | **DAT** | 41.3 | 98.9 | 54.8 | 47.3 | 68.2 |
| top30 | 200 | 50% | 92.3 | 70.5 | **DAT** | 56.5 | 100.0 | 66.3 | 55.5 | 72.6 |
| top30 | 200 | 60% | 95.6 | 80.6 | **DAT** | 71.7 | 100.0 | 71.8 | 57.9 | 79.2 |
| top50 | 100 | 40% | 84.7 | 52.9 | KHONG | 40.2 | 89.3 | 53.2 | 54.1 | 63.3 |
| top50 | 100 | 50% | 92.7 | 56.4 | KHONG | 50.0 | 92.3 | 57.0 | 57.1 | 66.3 |
| top50 | 100 | 60% | 96.0 | 67.0 | **DAT** | 54.9 | 94.2 | 58.4 | 60.7 | 74.0 |
| **top50** | **200** | **40%** | 91.9 | 64.8 | **DAT** | 53.3 | 100.0 | 56.4 | 48.1 | 69.0 |
| **top50** | **200** | **50%** | **92.7** | **70.9** | **DAT (dinh nghia A goc)** | 63.0 | 100.0 | 66.0 | 55.2 | 72.9 |
| top50 | 200 | 60% | 97.6 | 81.9 | **DAT** | 79.3 | 100.0 | 72.9 | 58.2 | 79.7 |
| top100 | 100 | 40% | 87.1 | 53.7 | KHONG | 38.6 | 91.5 | 55.6 | 54.1 | 65.5 |
| top100 | 100 | 50% | 91.1 | 61.7 | **DAT (sat)** | 45.7 | 93.4 | 56.4 | 56.6 | 71.2 |
| top100 | 100 | 60% | 96.0 | 71.8 | **DAT** | 52.7 | 94.5 | 58.4 | 60.4 | 78.6 |
| top100 | 200 | 40% | 89.9 | 72.7 | **DAT** | 50.5 | 100.0 | 56.2 | 47.3 | 74.0 |
| top100 | 200 | 50% | 92.3 | 83.3 | **DAT** | 64.7 | 100.0 | 63.6 | 54.1 | 81.1 |
| top100 | 200 | 60% | 92.3 | 94.3 | **DAT** | 73.9 | 100.0 | 69.9 | 58.5 | 88.2 |
| **all** | 100 | 40% | 88.3 | 64.3 | **DAT** | 39.7 | 92.1 | 55.9 | 51.1 | 75.3 |
| **all** | 100 | 50% | 93.1 | 72.7 | **DAT** | 47.8 | 93.7 | 57.5 | 57.4 | 81.1 |
| **all** | 100 | 60% | 96.4 | 85.9 | **DAT** | 53.8 | 94.8 | 60.3 | 61.7 | 90.1 |
| **all** | **200** | **40%** | 91.9 | 87.2 | **DAT** | 52.2 | 100.0 | 57.3 | 47.3 | 86.6 |
| **all** | **200** | **50%** | 92.3 | 97.4 | **DAT** | 64.7 | 100.0 | 64.9 | 56.6 | 94.2 |
| **all** | 200 | 60% | 93.1 | 100.0 | **DAT** | 76.1 | 100.0 | 72.6 | 61.7 | 97.5 |

**19/24 to hop DAT (79%).** 5 to hop KHONG dat deu la **MA=100 + nguong thap (40% hoac 50%)** o
`top30`/`top50`/`top100` — UW-2025 roi duoi 60% (50.7-56.4%) trong khi UW-2022 van rat cao
(81.5-92.7%). `top100/MA100/thr50%` sat nguong (61.7%, "DAT sat"). **KHONG co to hop nao o MA=200
that bai** — ca 12/12 to hop MA=200 (moi universe x moi nguong) deu DAT.

**Per-universe pass rate (tren 6 to hop moi universe = 2 MA x 3 nguong):**

| universe | so to hop DAT / 6 |
|---|---:|
| top30 | 4/6 |
| top50 | 4/6 |
| top100 | 5/6 |
| **all-coin** | **6/6** |

**Ket luan Phan 1**: ket luan breadth bat duoc ca UW-2022 lan UW-2025 la **ROBUST voi MA=200**
(100% - 12/12 to hop qua moi universe/moi nguong), va **all-coin la universe ON DINH NHAT** (6/6,
kem ca 3 to hop MA=100 ma top30/50/100 deu that bai). Diem yeu duy nhat la MA=100 ket hop nguong
thap (40-50%) — day la vung tham so it lien quan den ket luan chinh (dinh nghia A dung MA=200/50%
tu dau). **KHONG phai fragile chi-dung-top50/50%**: dinh nghia A (top50/MA200/50%) chi la MOT
trong 19 to hop DAT, khong phai diem duy nhat.

## 2. Chuoi breadth-score lien tuc

Da tinh xong (`research/analysis/out/breadth_score_series.csv`, 1645 dong, `2021-07-01..2025-12-31`)
cho 2 cau hinh chinh, ca hai causal (dung close[D-1] va MA200 tinh den D-1, khong nhin tuong lai):

- `breadth_score_allcoin` = %coin (tren toan bo coin con song tai t) co close[D-1] >= MA200_causal.
- `breadth_score_top50` = %coin (tren top-50 theo symId) co close[D-1] >= MA200_causal.

Minh hoa anh xa `gate(t) = gate_up + (gate_down-gate_up) x clip((thr - score(t))/thr, 0, 1)` voi
`gate_up=1.0` (long, giong dinh nghia A khi breadth >= nguong), `gate_down=1.7` (chat nhat, giong
BR truoc), `thr=0.5` (50%, giong dinh nghia A) — **CONG THUC MASTER de xuat trong nhiem vu, chi de
minh hoa, KHONG phai sim that**.

### Vai ngay mau

| ngay | boi canh | score (all-coin) | gate (all-coin) | score (top50) | gate (top50) |
|---|---|---:|---:|---:|---:|
| 2022-06-18 | day bear (Celsius/3AC, trong UW-2022) | 0.000 | **1.700** | 0.000 | **1.700** |
| 2022-11-09 | sau FTX sup do | 0.056 | 1.622 | 0.080 | 1.588 |
| 2025-04-07 | dau UW-2025 (tariff selloff) | 0.034 | 1.652 | 0.042 | 1.642 |
| 2025-06-15 | giua UW-2025 (chop) | 0.092 | 1.571 | 0.125 | 1.525 |
| 2025-08-05 | cuoi UW-2025 (hoi phuc mot phan) | 0.283 | 1.303 | 0.438 | **1.088** |
| 2023-08-15 | 2023 (day tich luy, chua khoe han) | 0.165 | 1.469 | 0.260 | 1.336 |
| 2023-11-15 | 2023 cuoi nam (pump truoc halving) | 0.802 | **1.000** | 0.840 | **1.000** |
| 2024-03-01 | 2024 dinh bull (post-halving run-up) | 0.964 | **1.000** | 0.980 | **1.000** |
| 2024-07-15 | 2024 giua nam (dieu chinh) | 0.096 | 1.565 | 0.200 | 1.420 |

### Thong ke ca cua so

| cau hinh | window | n ngay | score mean | score median | gate mean | gate median |
|---|---|---:|---:|---:|---:|---:|
| all-coin/MA200 | UW-2022 | 248 | 0.138 | 0.065 | 1.524 | 1.610 |
| all-coin/MA200 | **UW-2025** | 227 | 0.200 | 0.129 | **1.421** | **1.519** |
| all-coin/MA200 | 2023 | 365 | 0.394 | 0.244 | 1.274 | 1.358 |
| all-coin/MA200 | 2024 | 366 | 0.459 | 0.435 | 1.250 | 1.091 |
| top50/MA200 | UW-2022 | 248 | 0.141 | 0.080 | 1.510 | 1.588 |
| top50/MA200 | **UW-2025** | 227 | 0.301 | 0.167 | **1.327** | **1.467** |
| top50/MA200 | 2023 | 365 | 0.422 | 0.300 | 1.247 | 1.280 |
| top50/MA200 | 2024 | 366 | 0.517 | 0.420 | 1.225 | 1.112 |

**Ket luan Phan 2**: chuoi da tinh xong day du. Voi cau hinh `gate_up=1.0/gate_down=1.7/thr=50%`,
UW-2025 nhan gate trung binh **~1.42 (all-coin) den ~1.33 (top50)** — **VUA PHAI, RO RANG KHONG
phai 1.7 cung nhu gate nhi phan cu** (BR truoc dung notup=1.7 co dinh cho MOI ngay trong UW-2025).
UW-2022 (bear that su) nhan gate cao hon ro ret (~1.51-1.52 trung binh, va CHAM DAY 1.7 vao ngay
sau nhat 2022-06-18) — dung huong: bear sau nhan gate chat gan max, chop 2025 nhan gate trung
gian. all-coin cho gate UW-2025 chat hon top50 mot chut (1.42 vs 1.33) vi score all-coin thap hon
(0.20 vs 0.30) — top50 (chi 50 coin niem yet som, thanh khoan on dinh) phuc hoi breadth nhanh hon
phan con lai cua thi truong trong giai doan chop 2025.

## 3. Proxy co du tot khong?

Tu Phan 1: dinh nghia A (top50/MA200/50%) DAT, va **12/12 to hop MA200 (ca 4 universe) DAT**, va
rieng **all-coin/MA200 DAT ca 3/3 nguong**. Ket luan pha duoc UW-2022 va UW-2025 **KHONG phu
thuoc vao viec chon dung top-N chinh xac** — chuyen tu top-50 sang top-30, top-100, hay toan bo
all-coin (627 symId, giai quyet dung van de ty le phu 2021->2025) deu giu duoc ket luan khi dung
MA=200. Diem yeu duy nhat (MA=100 + nguong thap) khong lien quan den cau hinh dang dung (dinh
nghia A dung MA=200/50% tu dau).

**Ket luan: PROXY (symId thu tu niem yet) DU TOT cho muc dich regime-detection nay — KHONG can
volume that (JVM) o vong nay.** Ly do: (1) ket luan robust qua ca 4 universe khi MA=200, (2)
all-coin (khong phu thuoc chon topN nao ca) la universe ON DINH NHAT (6/6), chinh no da giai quyet
noi lo "ty le phu doi theo nam" ma khong can volume that — bang cach lay MAU SO la so coin thuc su
song tai t thay vi mot tap co dinh theo thu tu niem yet. Neu MASTER van muon dung volume that de
chon dung "top-N theo thanh khoan" o vong sau, do la CAI THIEN chinh xac (co the giup phan biet ro
hon "altcoin thanh khoan thap gia tao bien dong" khoi breadth), KHONG phai dieu kien BAT BUOC de
tin ket luan robust hien tai.

## Khuyen nghi cho MASTER (thiet ke sim gate-lien-tuc vong sau)

Theo ly le robust (khong theo so dep):
- **Universe**: `all-coin-song` (khong phai top-50 co dinh) — vi la universe ON DINH NHAT qua
  sweep (6/6) VA giai quyet dung van de ty le phu ma nhiem vu neu, khong can chon N tuy y. Neu
  MASTER muon giu su tuong dong voi cac round sim da chay (BR/BR0 dung top50), `top50/MA200` van
  la lua chon hop ly thu hai (DAT ro rang, sweep 200-series 3/3, va la cau hinh da co tien le sim
  that o Buoc 6) — nhung khuyen nghi CHINH la doi sang all-coin vi tinh proxy-independent.
- **MA window**: **200** (KHONG phai 100) — day la tham so quyet dinh su robust, 12/12 to hop
  MA200 DAT so voi chi 7/12 to hop MA100.
- **Nguong/gate_thr**: 50% (0.5) — trung tam cua sweep, ca ba nguong (40/50/60%) deu DAT o MA200
  nen khong nhay cam, giu 50% de tuong thich voi dinh nghia A da khoa truoc.
- **Gate continuous**: chuoi `breadth_score_series.csv` (cot `breadth_score_allcoin` va
  `breadth_score_top50`, ca hai da tinh san `gate_*_ma200` minh hoa voi gate_up=1.0/gate_down=1.7)
  san sang de MASTER thiet ke sim gate-lien-tuc — khong can tinh lai, chi can quyet dinh gate_up/
  gate_down/thr that su se dung trong sim (gia tri trong file hien tai CHI la minh hoa).
