# E0 - Counterfactual do luong horizon time-stop (offline)

Nguon: `printDone.csv` (970 lenh, C2b) + `CLOSES_1H.bin` (hourly closes UTC).
Logic exit tai tao: ARM +7%, trailing giveback = min(peak*0.5, cap), cap 0.08 STRONG / 0.03 WEAK (symbolPred < 0.29 => WEAK), time-stop khi chua bao gio arm.
Khong chay Java sim, khong train model. Chi horizon time-stop thay doi.

## M3. Kiem tinh dung (gate) - **FAIL**

| Kiem tra | Nguong | Do duoc | Ket qua |
|---|---|---|---|
| Khop `status` (armed vs timestop) @ TS_H=168 | >= 95% | 92.47% | FAIL |
| corr(profit_sim, profit_thuc) | >= 0.95 | 0.7727 | FAIL |
| sum(pnl) sim vs 25391 USDT thuc | (bao cao) | 20897 USDT | lech -17.70% |
| corr(exit_hour_sim, `time_order`) | (bao cao) | 0.8004 | - |

Confusion (hang = thuc, cot = sim):

```
sim_armed   False  True 
thuc_armed              
False         146      1
True           72    751
```

### Tai sao gate FAIL (chan doan, khong tune)

- **72 lenh thang thuc te ma sim khong bao gio arm.** Max gain tren hourly close cua chung: median 5.81%, p75 6.52%, **max 6.98% - khong mot lenh nao cham nguong 7%**. He thuc te arm bang gia trong gio (hoac mot chuoi min hon, vd 15m); hourly close khong bao gio voi toi nguong do.
- **153 / 823 lenh thang co `time_order` == 0, 223 co `time_order` <= 1 gio**: arm VA chot ngay trong 1-2 gio dau. Phan giai 1H khong the quan sat duoc nhung lenh nay.
- Gia `entry` trong printDone lech so voi hourly close tai gio entry: median ~2%. `CLOSES_1H.bin` khong phai chuoi gia ma Java sim da dung.
- **DCA bi loai tru**: `lastentry == entry` cho ca 970 lenh, nen nguyen nhan khong phai DCA. Funding/fee cung khong phai: chung chi la mot hang so ~0.80% tren pnl.
- Chi 1 / 147 lenh time-stop thuc te co max hourly-close gain >= 7%: huong lech gan nhu MOT chieu - sim bo sot arm, chu khong arm khong.

**Gate khong dat => M1/M2/M4 duoi day chi la tham khao, KHONG du tin cay de quyet dinh doi horizon.**

## M1. Phan bo thoi diem ARM (lenh thang thuc te, n=823; sim arm duoc 751)

| Bin gio | So lenh | % |
|---|---|---|
| 0-24 | 535 | 71.2% |
| 24-48 | 96 | 12.8% |
| 48-72 | 55 | 7.3% |
| 72-96 | 21 | 2.8% |
| 96-120 | 14 | 1.9% |
| 120-144 | 19 | 2.5% |
| 144-168 | 11 | 1.5% |

**Arm SAU gio 72: 64 / 751 = 8.52%** cua cac lenh thang -> day la phan se mat neu cat time-stop ve 72h.

Chan tren tu ground-truth (**khong phu thuoc vao viec dung lai duong gia**): 55 / 823 lenh thang co `time_order` > 72h = 6.68%. Mot lenh arm som nhung chot muon van song sot duoi time-stop 72h, nen day la CHAN TREN cua so lenh thang bi cat. No khop bac do lon voi 8.52% do tu duong gia o tren, nen ket luan M1 la phan vung nhat cua bao cao nay.

## M2. Counterfactual PnL theo horizon

| TS_H | n_armed | n_timestop | mean%(armed) | mean%(timestop) | sum_pnl_USDT | TSloss_rate% |
|---|---|---|---|---|---|---|
| 48 | 633 | 337 | +9.54% | -9.13% | 21761 | 34.7% |
| 72 | 687 | 283 | +9.49% | -12.99% | 20494 | 29.2% |
| 96 | 708 | 262 | +9.48% | -14.18% | 21561 | 27.0% |
| 120 | 722 | 248 | +9.43% | -16.21% | 19989 | 25.6% |
| 144 | 740 | 230 | +9.41% | -18.07% | 19457 | 23.7% |
| 168 | 752 | 218 | +9.36% | -18.86% | 20897 | 22.5% |

Delta sum_pnl so voi TS_H=168 (20897 USDT):

| TS_H | delta_USDT | delta% |
|---|---|---|
| 48 | +864 | +4.1% |
| 72 | -403 | -1.9% |
| 96 | +664 | +3.2% |
| 120 | -908 | -4.3% |
| 144 | -1440 | -6.9% |
| 168 | +0 | +0.0% |

**Canh bao**: sum_pnl KHONG don dieu theo horizon (48h > 72h; 96h > 120h/144h). Bien do dao dong giua cac horizon (2304 USDT = 11.0% cua baseline) NHO HON sai so cua chinh phep do o gate (17.7%). Vi vay M2 khong the xep hang cac horizon; no bi tail cua vai lenh loi rat lon chi phoi.

## M4. 147 lenh bi time-stop: maxFav trong 168h

| maxFav | So lenh | % | gio dat maxFav (median) |
|---|---|---|---|
| <1% | 54 | 36.7% | 4 |
| 1-3% | 44 | 29.9% | 2 |
| 3-5% | 36 | 24.5% | 10 |
| 5-7% | 12 | 8.2% | 26 |
| >7% | 1 | 0.7% | 168 |

maxFav: median 1.83%, p75 3.91%, p90 4.77%, max 8.45%. Gio dat maxFav: median 4, p75 24.

Suyt arm (5-7%): 12 lenh (8.2%). Khong bao gio chay (<1%): 54 lenh (36.7%).

## Gioi han cua phep do

1. **Giu nguyen `margin` tung lenh, KHONG mo phong lai sizing.** Horizon ngan hon giai phong von som hon -> sizing va ca tap lenh mo ra se khac. Hieu ung bac hai nay khong nhin thay o day.
2. **Tap lenh dong bang**: cung 970 entry duoc replay cho moi horizon. Thuc te horizon ngan hon se doi chuoi entry tuong lai (capital rotation).
3. **Duong gia la hourly close**. Bien dong trong gio khong thay duoc: gio ARM la gioi han tren, va trailing exit bi lam tho. Median |close_1h/entry - 1| tai gio entry la ~2%, tuc CLOSES_1H.bin khong phai chuoi gia ma Java sim dung.
4. **pnl mo hinh hoa** = margin * (profit% - 0.80%)/100, hang so cost hieu chinh tu baseline (median cua pnl/margin*100 - profit == -0.800). Funding/fee thuc te tung lenh khong tai tao.
5. Khong co stop-loss truoc ARM trong logic nay; neu live co thay doi khac thi phep do lech.

