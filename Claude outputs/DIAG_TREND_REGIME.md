# DIAG_TREND_REGIME — ket qua Buoc 1 (TASK B2 Buoc 5, 2026-09-21)

Theo `docs/PREREG_TREND_REGIME_DIAG.md` (khoa TRUOC khi tinh so). 0-sim (khong Java, khong
xgboost, khong build). Code: `research/analysis/trend_regime.py`, json:
`research/analysis/out/trend_regime.json`.

## 0. Xac nhan detector (da doc `git show 157cf4d:...`)

`TrendDetector.isBtc/EthTrendBuyProduction`: SMA7 vs SMA100 (`Configs.SMA_SHORT=7`,
`Configs.SMA_LONG=100`, ca `157cf4d` va `config.properties` hien tai), khung 1D VA 4H, OR, causal
(chi dung nen da dong truoc thoi diem t, qua `Utils.getDate`/`Utils.get4Hour`, bien UTC-epoch).
Tai hien Python tu `trend_rank_ic.load_closes()` (CLOSES_1H.bin, BTC symId=1, ETH symId=2, loc
ts<2026-01-01). Du lieu BTC/ETH co tu 2021-01-01 02:00 den 2026-01-01 00:00 (holdout dung).
SIM range danh gia: 2021-07-01..2025-12-31 (1645 ngay, giong `regime_build_ma200.py`). So ngay
thieu du lieu causal (min_periods_floor=30) trong SIM range: BTC 1d=0 4h=2, ETH 1d=0 4h=3 — khong
dang ke (~0%, dung nhu du kien vi da co 181 ngay lich su truoc SIM0).

## 1. %ngay detector_up moi nam (BTC/ETH/BTC-OR-ETH) vs MA200

| Nam  | MA200 (Buoc 4, tham chieu) | Detector BTC | Detector ETH | Detector BTC-OR-ETH |
|------|------:|------:|------:|------:|
| 2021 | 64.7% | 79.3% | 92.9% | 92.9% |
| 2022 |  0.0% | 39.2% | 50.1% | 54.8% |
| 2023 | 80.3% | 86.8% | 81.4% | 89.0% |
| 2024 | 80.1% | 84.7% | 75.1% | 89.1% |
| 2025 | 73.4% | **67.4%** | 64.7% | 73.2% |

**Cau chinh (detector BTC goi 2025 up bao nhieu %?): 67.4%** — THAP HON MA200 (73.4%), dung
huong ky vong (bat bull-nhieu 2025 nhieu hon MA200 mot chut, ~6 diem %). NHUNG: **detector goi
2022 up toi 39.2% ngay** (MA200 = 0%, hoan hao) — detector NHANH HON (SMA100<MA200, co them khung
4H) nen NHIEU nhieu hon trong chinh giai doan bear 2022 ma MA200 bat rat gon. Day la trade-off ro:
detector nhay hon voi 2025 nhung tra gia bang do nhay/nhieu o 2022.

## 2. %phu not-up cua 2 chuoi UW dai (cong quyet dinh)

| Detector | UW-2022 (248 ngay, 2021-11-16..2022-07-21) | UW-2025 (227 ngay, 2025-03-04..2025-10-16) |
|---|------:|------:|
| **BTC (chinh)** | **60.9%** (PASS >=60%) | **19.8%** (FAIL, xa duoi 60%) |
| ETH | 50.4% (FAIL) | 19.8% (FAIL) |
| BTC-OR-ETH | 45.2% (FAIL) | 14.1% (FAIL) |

Detector BTC vua du nguong 60% o UW-2022 (60.9%, sat nguong) nhung **FAIL nang o UW-2025 (19.8%,
chi hon 1/3 nguong can)**. Doi chieu tham khao: theo chan doan UW-2025 truoc do, MA200 chi phu
~15.9-16.1% cua dung cua so nay (Mar-Oct 2025) — detector BTC (19.8%) nhinh hon MA200 mot chut
nhung VAN THAT BAI o cung mot cho: **detector KHONG bat duoc giai doan UW-2025 ma MA200 miss**,
chi cai thien nhe (+3.7-3.9 diem %) chu khong giai quyet duoc van de goc.

## 3. Edge doc lap (khong qua sim)

**Forward return BTC theo detector_up (BTC-detector, chinh)**:

| | n | fwd1D mean | fwd7D mean |
|---|---:|---:|---:|
| up=True | 1162/1160 | +0.138% | +0.889% |
| up=False (notup) | 483/480 | -0.012% | +0.172% |

Detector CO tach duoc huong: ngay "up" theo sau boi return trung binh duong ro (1D/7D), ngay
"notup" theo sau boi return gan-0/thap hon ro ret — day la edge THAT (khong phai nhieu tuy tien),
nhung do lech nho (std ~2.5-7.5%/ngay >> chenh lech trung binh), khong du de tu no lam gate manh.

**ROI so T100 (`X1_C3_FULL_2021`) theo regime luc mo lenh**:

| Detector | Regime | n | ROI mean (CI90) | loss rate | phi (dong-thua) |
|---|---|---:|---|---:|---:|
| BTC | up | 1710 | +3.16% [+1.99, +4.32] | 15.6% | 2.07 |
| BTC | notup | 849 | +1.27% [-0.18, +2.68] | 16.6% | 1.90 |
| ETH | up | 1686 | +3.12% [+1.94, +4.28] | 15.6% | 2.04 |
| ETH | notup | 873 | +1.40% [-0.06, +2.81] | 16.5% | 2.04 |
| BTC-OR-ETH | up | 1830 | +3.15% [+2.09, +4.16] | 15.3% | 2.08 |
| BTC-OR-ETH | notup | 729 | +0.99% [-0.63, +2.54] | 17.4% | 1.90 |

Lenh mo trong regime "notup" **VAN CO ROI trung binh DUONG** (khong am), chi thap hon regime "up"
(khoang 1/2 den 1/3), CI90 cham/vuot 0 (khong tach biet chac chan khoi 0). Loss-rate va phi
(dong-thua) GAN NHU KHONG DOI giua 2 regime (15-17%, phi ~1.9-2.1 ca hai). ⇒ regime nay KHONG
phai loai "danh dau lenh xau" ro net nhu regime MA200/bear-multi-week o TASK B2 Buoc 1 — no chi
lam giam nhe bien do loi nhuan trung binh, khong dao duoc thua-lo tap trung.

## 4. Sweep mo ta (BTC, SMA_SHORT=7 co dinh, KHONG chon winner) — %2025 goi not-up

| SMA_LONG | 1D-only | 4H-only | 1D+4H-OR |
|---:|---:|---:|---:|
| 50  | 54.8% | 47.7% | 30.7% |
| 100 (goc) | 46.3% | 53.2% | **32.6%** |
| 150 | 36.7% | 56.4% | 28.2% |
| 200 | 25.8% | 56.4% | 21.9% |

Quan sat: khung OR (1D+4H) LUON thap hon ca 2 khung don le (dung ban chat OR — de len-up hon),
nen cau hinh goc (100, 1D+4H-OR) khong phai la mien "chat nhat" cua luoi nay; **ngay ca gia tri
cao nhat trong toan luoi (56.4%, SMA_LONG={150,200}, 4H-only) van duoi nguong 60%** dung cho phan
quyet — tuc CA HO detector-tren-ho-nay (khong doi khung/SMA_LONG trong pham vi kiem) cung khong
co cau hinh nao phu UW-2025 dat 60% NEU chi doi tham so nay. Day la mo ta, KHONG dung de chon
lai cau hinh phan quyet (theo luat PREREG).

## 5. Cong GO/NO-GO (khoa truoc, §1.3 PREREG)

```
detector = BTC, config = SMA7/100, 1D+4H-OR (production goc)
pct_notup(UW-2022) = 60.9%  (>= 60% -> PASS)
pct_notup(UW-2025) = 19.8%  (< 60%  -> FAIL)
=> GO doi hoi CA HAI dat >=60%. UW-2025 FAIL nang.
```

**VERDICT: NO-GO.**

Detector production (SMA7/100, 1D+4H-OR, BTC) KHONG hon MA200 mot cach co y nghia cho van de UW-
2025: no goi 2025 la up it hon MA200 (67.4% vs 73.4%, dung huong ky vong) va phu UW-2025 nhinh hon
MA200 mot chut (19.8% vs ~16%), nhung ca hai deu **rat xa** nguong 60% can de mot gate-chat cat
duoc phan lon phoi nhiem xau trong giai doan bull-nhieu-song-lon 2025 (dung nhu chan doan UW-2025
truoc day da ket luan: nguon UW-2025 la nen alpha-bien theo CHE DO thi truong bull-nhieu, khong
phai mot tin hieu trend/huong don gian nao bat duoc — SMA-crossover, du nhanh hon MA200, van dung
CHUNG loai tin hieu "huong gia" nen khong the phan biet duoc "tang manh nhung chop cao" khoi "tang
on dinh"). Detector cung dua doi 2022 (39.2% up, MA200=0%) de doi lay cai thien nho o 2025 — mot
trade-off khong dang.

Bien-the ETH va BTC-OR-ETH deu TE HON BTC ca hai cua so (BTC-OR-ETH: UW2022=45.2%, UW2025=14.1%)
— dung nhu du kien vi OR lam tang %up (de len-up hon), giam kha nang phu not-up.

**Theo §1.3 PREREG: NO-GO ⇒ dung, KHONG lam Buoc 2 (sim regime-gate voi detector nay). Ghi
power_wall cho huong "TrendDetector production lam regime thay MA200". Chuoi NULL/NO-GO breadth-
improvement gio la 5/5 (TASK B → Buoc 2 → Buoc 3 → Buoc 4 → Buoc 5.1).**

## 6. Han che phuong phap (da neu trong PREREG)

`daily_close`/`close4h` la RESAMPLE tu luoi 1H (khong phai kline 1D/4H goc Binance); voi du lieu
lien tuc (CLOSES_1H.bin BTC/ETH khong gap dang ke trong pham vi kiem tra), sai khac voi kline goc
duoc ky vong toi thieu. Quy uoc "detector_up cho ngay D" danh gia MOT gia tri/ngay tai 00:00 UTC
(dung nen 1D/4H da dong gan nhat) de so 1-1 voi chuoi MA200 hang-ngay; trong thuc te san xuat,
detector duoc goi lien tuc (moi lan EntryGate danh gia mot ung vien trong ngay) nen gia tri THAT
co the doi trong ngay khi bucket 4H moi dong — quy uoc nay la don gian hoa hop ly cho muc dich so
sanh %ngay/nam va phu chuoi UW, khong anh huong toi ket luan NO-GO (bien do sai khac do quy uoc
nay nho hon rat nhieu so voi khoang cach 19.8% vs 60% can).
