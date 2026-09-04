# SELECTOR_LADDER_Q — bo chi tiet theo QUY/NAM + danh gia hieu qua & leak

Ngay: 2026-09-04. Nguon: 125 sim runs tren dia `/home/ubuntu/java/devrun/<TAG>/`.
Script: `research/analysis/qret_ladder.py` (moi), doc thang tu `logs/sim.out` va
`storage/printDone.csv`. DEV = 2022-01 -> 2024-06 (10 quy). Vao 35,000.

`sumPNL` doc tu `printDone.csv` khop chinh xac equity gain (C2b 25,391 = 60,390-35,000),
nen moi so quy ben duoi la USDT thuc, khong phai uoc luong.

## 1. Bang quy (return % tren equity cuoi ngay)

TAG            END    22Q1  22Q2  22Q3  22Q4  23Q1  23Q2  23Q3  23Q4  24Q1  24Q2  maxDD   UW
v2_g1         32956   -0.7 -39.4  +2.0  -3.6  +9.9 +19.8  +3.7  +8.1 +14.1  -5.5  -51.1  898
v3_g1         38471   -1.4  -4.4  +2.2  -0.6  +2.6  +4.4  +1.7  +1.8  +4.6  -1.0  -16.1  461
map_vol7d_g1  41876   -4.0  -6.0  +3.4  -1.8  +3.3 +13.8  +3.6  +3.2  +7.2  -3.2  -16.3  452
G1_giveback5  48352   -1.9  -2.8  +4.9  -2.7  +3.3  +8.8  +5.4  +7.1  +9.5  +2.3  -15.6  256
map_s1a_g1    49581   -1.9  +3.1  +6.2  -5.6  +3.8 +11.6  +4.3  +6.0  +5.4  +3.5  -12.8  164
map_s1a2_g1   50891   +0.2  +1.3  +5.6  -2.8  +4.5 +11.4  +4.2  +5.6  +6.0  +2.7  -10.7  114
C3            45287   +0.7 -18.0  +3.2  -5.2 +15.6 +14.9  +9.4  +6.6 +10.3  -6.2  -29.5  367
C2_g015       51903   -3.2  -4.8  +6.2  -5.4  +8.0 +12.0  +9.0  +9.9 +11.3  -0.8  -20.8  406
C2a           59471   +0.6  +3.3  +8.6  -3.8  +8.3 +15.1  +7.4  +8.1  +7.6  +0.5  -13.4   95
C2b           60390   +0.7  +4.4 +10.2  -3.7  +7.4 +15.4  +8.1  +8.6  +7.8  -1.4  -13.1   93

Thu tu bang xep hang duoc quyet dinh bang MOT quy: 22Q2 (LUNA, 5/2022). Spread
22Q2 tu v2_g1 (-39.4) den C2b (+4.4) = 43.8pp, rong hon moi quy khac. Nghia la
n_eff cho cau hoi "selector nao tot hon" gan 1 episode hon la gan 970 trades.

## 2. PHAT HIEN CHINH: uu the cua S1 nam gon trong 2022

Nam %:            2022    2023    2024(6m)
  C2_g015         -7.4   +44.9   +10.5
  C2b            +11.6   +45.4    +6.3
  G1_giveback5    -2.7   +26.8   +12.0
  map_s1a2_g1     +4.2   +28.1    +8.9

Rebase moc 2023-01-01 (bo han 2022 ra):
  C2_g015   1.449 x 1.105 = x1.6011  (+60.1%)
  C2b       1.454 x 1.063 = x1.5456  (+54.6%)   -> C2b THUA 5.5pp
  G1_gb5    1.268 x 1.120 = x1.4202  (+42.0%)
  map_s1a2  1.281 x 1.089 = x1.3950  (+39.5%)   -> map THUA 2.5pp

Phan ra ti le: C2b/C2_g015 = 1.1635 = 1.2052 (2022) x 0.9653 (2023-24).
              map/G1_gb5   = 1.0525 = 1.0709 (2022) x 0.9816 (2023-24).
=> 2022 tao +20.5pp / +7.1pp uu the tuong doi; 18 thang sau tra lai -3.5pp / -1.8pp.
Hai exit doc lap (G1 va C2) cho CUNG dau => khong phai nhieu cua mot run.

Doi chieu USDT tho (C2b - C2_g015 sumPNL theo quy):
  22Q1 +1209  22Q2 +3342  22Q3 +1761  22Q4  +340   -> 2022 = +6,652 (78% tong)
  23Q1  +280  23Q2 +2459  23Q3  +168  23Q4  +278   -> 2023 = +3,185
  24Q1  -884  24Q2  -465                           -> 2024 = -1,349
  tong +8,487 (khop 25,391 - 16,904)
2022 chiem 78% uu the tho; sau khi chuan hoa base compound thi 2023-24 la AM.
2022 dong thoi la nam universe mong nhat (155 coin/h) va OI features non nhat
(bat dau 2021-12) => vung du lieu yeu nhat lai la vung sinh ra ket luan.

## 3. Co che thuc: KHONG phai "chon coin tot hon"

Doc tu printDone.csv (margin = entry x quantity, leverage 1, `profit` = % gia):
                    n      margin_med   medP    meanP   p5      TSloss%
  C2b              970        969       5.50    3.48   -21.18    15.2
  C2_g015         1583        525       5.49    2.61   -19.47    23.2

- medP GIONG HET (5.50 vs 5.49): trade dien hinh khong tot hon chut nao.
- C2b danh IT hon 39% nhung margin/trade LON hon 1.85x (fewer concurrent
  positions -> U thap -> (1-U/U_MAX) lon -> size to hon). Tong margin trien khai
  con NHIEU hon 13% (939,736 vs 830,918). Day la hieu ung CO DAC hoan toan
  co hoc tu tuong tac gate/sizing, khong phai ky nang xep hang.
- p5 C2b XAU hon (-21.18 vs -19.47): khi lo thi lo dam hon (vi size to hon).
- Khac biet duy nhat co that: TSloss% (ty le bi time-stop 168h) 15.2 vs 23.2.

### TSloss% theo quy — day la tin hieu ben nhat trong toan bo ladder
              22Q1  22Q2  22Q3  22Q4  23Q1  23Q2  23Q3  23Q4  24Q1  24Q2
  C2b         24.6  13.0   5.8  29.4   8.6  16.2  12.5  10.5  12.3  22.2
  C2_g015     31.9  18.6  21.6  42.4  18.3  32.6  19.7  14.6  11.4  30.0
  -> C2b thap hon 9/10 quy (sign test P(X>=9)=0.0107, 2-sided ~0.021)

  map_s1a2    18.8   9.4   2.0  20.0   4.8   9.9  11.1   8.3   7.8  12.3
  G1_gb5      24.8  13.2   9.6  25.3  11.1  18.4  11.8   8.0   6.2  19.1
  -> map thap hon 8/10 quy, exit KHAC, cung dau

KET LUAN CO CHE: dong gop that cua S1 = giam ty le bi time-stop 168h khoang
5-8pp, on dinh qua quy va qua 2 cau hinh exit. Day la mot RATE tren hang tram
trade nen n_eff lon hon nhieu so voi terminal equity => song sot duoc.
NHUNG loi do bi trung hoa: medP bang nhau, p5 xau hon, n it hon 39%. Nen
KHONG chuyen thanh return chuan hoa cao hon sau 2022 (muc 2).

## 4. Cai gi THUC SU dat duoc (khong phai selector)

a) GATE la load-bearing, hieu ung khong lo: `v3_g1_nomom` = 10,305 voi 13,960
   trades (tat momentum). Khong phai nhieu.
b) EXIT G1 -> C2 la cai tien that: medP nhay 3.5-4.0 -> 5.5-6.0 o CA 10/10 quy,
   moi selector. +16.9% equity o S1a2, +7.3% o G015.
c) Path metrics: UW 93-114d (S1) vs 256-406d (G015), maxDD -10.7/-13.1 vs
   -15.6/-20.8. Nhat quan qua 2 ladder. Nhung phan lon la he qua cua muc 2
   ("ngoi ngoai 2022"), khong phai thuoc tinh doc lap.
d) SELECTOR ladder: KHONG THIET LAP DUOC. Xem muc 5.

## 5. Rui ro leak / overfit, xep theo thiet hai ky vong

L1. MULTIPLE-COMPARISON tren cung mot DEV path. N ~ 125 runs,
    sd(CAGR diff giua selectors) = 4.45pp.
    E[max nhieu] = 4.45 x sqrt(2 ln 125) = 13.8pp
    Quan sat C2b - C2_g015 ~ +6.95pp CAGR (CI [-1.72,+15.61] chua 0).
    6.95 < 13.8 => quan sat NAM TRON trong vung nhieu-lay-max.
    Ngay ca N=20 thi nguong da la 4.45 x 2.45 = 10.9pp > 6.95.
    Giam nhe: N4_a8s175 (61,148) va H1a_mom006 (60,953) DEU thang C2b va da bi
    loai bang pre-reg => khong phai thuan maximize, N_effective < 125.
    Nhung khong triet tieu duoc.

L2. PURGE 72h < HOLDING 168h. Purge da kiem 16/16 rounds, du 68.25h spare —
    nhung do la spare so voi LABEL 72h. Time-stop thuc la 168h, nen position mo
    sat bien fold van con mo vao trong test window. Label duoc purge; EQUITY PATH
    thi khong. Va (muc 3) co che sinh loi cua S1 CHINH LA time-stop 168h — dung
    cai ma label 72h khong nhin thay va purge 72h khong che. Day la leak channel
    truc tiep nham vao co che dang duoc credit.
    => Job uu tien so 1: regen label tu CLOSES_1H.bin voi NH=168 + purge 168h,
       chay lai. Truoc day xep "nice to have", gio la then chot.

L3. `Constants.diedSymbol` trong G015 f3/f4/f5 = danh sach coin delist hardcode
    => thong tin tuong lai. Chua do luong. Luu y ve HUONG: leak nay giup
    C2_g015 (dat gia tri leak vao dung coin) NHIEU HON C2b (build_map giu
    multiset nhung xao lai theo rank S1). Nen neu co, no LAM NHE uu the cua C2b,
    khong phong dai. Van phai giet vi no o trong baseline.

L4. `f23 fundingPersistence` = proxy thoi gian => cho phep memorize regime tren
    mot duong lich su duy nhat. Leak truc tiep thap, dong gop overfit cao.

L5. OI features. File OI dang deploy DA kiem sach (commit a0fc56f) nen ket qua
    tren khong co leak dang hoat dong. NHUNG `VisionMetricsClient.parseDay` con
    lo 5-phut forward chua patch => KHONG duoc rebuild OI truoc khi patch.
    Ngoai ra `SELECTOR_FEATURES` muc D chia vung "clean/contaminated" dua tren
    mot claim SAU DO DA BI RETRACT => coi muc D nhu VOID.

L6. VAL da chay. Cham 5 lan, bins dir khac (`predwf_map_val`), config qua env
    khong tu git => khong con la holdout, va khong reproduce duoc.

L7. PROVENANCE VO. `predwf_G015x26` khong reproduce duoc (mat training export),
    disk 92%. Day la input quan trong nhat cua C2b va khong rebuild duoc.
    Moi so trong doc nay do tren mot input khong dung lai duoc.

## 6. Ket luan hieu qua

- Noi dung THAT cua C2b so voi C2_g015 sau khi rebase qua 2022 va tru selection
  bias 125-run: ~0. Selector ladder phai coi la CHUA THIET LAP.
- Cai da kiem duoc va nen giu: GATE (a) va EXIT C2 (b).
- Cai duy nhat cua selector song sot statistical: TSloss% -5..-8pp, 9/10 va 8/10
  quy, 2 exit doc lap. Nhung no khong bien thanh tien sau 2022.
- C2b van la baseline hop ly de deploy (path muot nhat, UW 93d), nhung KHONG
  duoc phat bieu la "selector co edge". Ly do giu C2b la path risk, khong phai
  alpha.

## 7. Job tiep theo, dung thu tu

1. NH=168 label + purge 168h (L2). Danh trung co che dang duoc credit.
2. Control run: G015 order + gate that chat lai cho ra ~970 trades. Neu no tai
   tao duoc 2022 cua C2b thi selector dong gop = 0 va muc 3 duoc chung minh.
3. Giet `Constants.diedSymbol` trong f3/f4/f5, chay lai G015 pred -> C2b (L3).
4. Pre-reg lai tieu chi tren cua so 2023-01 -> 2024-06 thay vi full DEV.
   LUU Y: tac gia doc nay DA XEM so 2023-24, nen bat ky test tren cua so do tu
   nay la DESCRIPTIVE, khong phai confirmatory. Muon confirmatory phai dung
   VAL sach hoac du lieu 2020-2021 mo rong.
