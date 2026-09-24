# PREREG ? Chay lai GD92 tren dataset chuan (MOT phep thu DUY NHAT)

Viet TRUOC khi build/chay. Khoa tham so. Ngay 2026-09-15.

User: *"toi thay GD92 ok ma, chay lai voi dataset chuan xem sao va phan bien nhe."*

**Muc dich la mot phep thu CONG BANG, khong phai "cho GD92 co hoi thu hai toi khi nao dep".**
GD92 truoc day chay tren `wfo_ds_x1` (2022-01..2025-12) va so voi baseline cua thoi do.
Lan nay doi CA HAI thu cho dung chuan hien hanh: dataset `wfo_ds_x1_2021` (2021-07..2025-12,
them 1.5 nam GD92 chua tung thay) va baseline `T170` (incumbent hien tai).
Day la bai test **KHO HON** cho GD92, khong phai de hon.

---

## 1. Xac dinh cau hinh GD92 GOC (truoc vu grid-search GATEDYN2 gay leak)

Doc `docs/audit/AUDIT_GATEDYN_GD92.md`. Ket luan cua audit do: **dot 1 (GATEDYN) chap nhan duoc** ve
thu tuc (pre-reg truoc, quota dong); **dot 2 (GATEDYN2) vi pham** vi la grid 6 diem quanh GD92
=> chinh no la cho sinh leak. Vay cau hinh "goc" can dung la cau hinh cua **dot 1**, commit
`272d8f1`, tuc **GD92 = pct 0.92, window 90 ngay**.

Xac minh bang file, khong bang tri nho:

```
$ diff profiles/x1_c3_full.properties profiles/archive/x1_gd92.properties
32a33,34
> SIM_GATE_ROLLING_PCT=0.92
> SIM_GATE_ROLLING_DAYS=90
```

`x1_c3_full` = 19 key; `archive/x1_gd92` = 21 key. Khac **dung 2 dong**, khong gi khac.
Run GD92 cu (`devrun/X1_C3_FULL_GD92`) co `PROFILE_HASH=52ee74bb5477b363 keys=21` ? khop file nay.

**=> Se dung `profiles/archive/x1_gd92.properties` NGUYEN VAN, khong soan profile moi.**

### KHOA PHAM VI (chong lap lai dung loi cu)
Chay **DUNG 1 cau hinh**: pct=0.92, days=90. **KHONG** chay 0.88/0.90/0.94/0.96,
**KHONG** chay W=60/120/180, **KHONG** chay bat ky lang gieng nao. Neu GD92 that bai =>
dong lai, khong mo vong 2. Day chinh xac la thao tac ma `AUDIT_GATEDYN_GD92` da vach ra
la vi pham o dot GATEDYN2.

---

## 2. Doi chieu code phuc hoi voi git history ? DA LAM, KHOP 100%

Master yeu cau khong tin file `.md` mu quang. Da doi chieu:

| Nguon | Dong | md5 |
|---|---|---|
| `git show f1c43a3^:src/main/java/com/binance/chuyennd/ai_ml/onnx/entry/GateRollingThreshold.java` | 149 | `e1e99295c76bfd066493ca25ebeb1243` |
| Block java trich tu `/home/ubuntu/gate_feat_study/GD92_CODE_AND_RESULTS.md` | 149 | `e1e99295c76bfd066493ca25ebeb1243` |

`diff` = **rong**. File trong goi tai lieu **khop 100% voi git history**. Dung ban `git show`
(khong dung ban trich tu .md) de tranh moi rui ro ky tu an.

File bi xoa o commit `f1c43a3` ("L7 B1+B2: gate entry ve MOT class EntryGate + xoa 4 co che tro
? PARITY byte-identical"), **khong phai bi xoa vi sai**, ma vi don kien truc.

---

## 3. Ke hoach phuc hoi (branch rieng, KHONG merge vao `module`)

Branch `gd92-recheck` tach tu `module` HEAD. **Dung 3 thay doi**, khong hon:

1. **Them lai file** `src/main/java/com/binance/chuyennd/ai_ml/onnx/entry/GateRollingThreshold.java`
   ? nguyen van tu `f1c43a3^`, **khong sua mot ky tu**.
2. **`AIRejectFilter.java`** (1 cho, dong 63). Kien truc da doi: cu la
   `thres15M(prediction)` tra ve nguong CO SO; nay la `EntryGate.threshold(thrBase, sp)`.
   Phuc hoi tuong duong ngu nghia = bom nguong truot vao **dung cho `thrBase`**:
   ```java
   // CU (f1c43a3^, AIRejectFilter.thres15M):
   //   GateRollingThreshold.isOn() ? GateRollingThreshold.threshold(prediction.timestamp)
   //                               : Configs.MIN_MOMENTUM_15M
   float thrBase = GateRollingThreshold.isOn()
           ? GateRollingThreshold.threshold(prediction.timestamp)
           : Configs.MIN_MOMENTUM_15M;
   return evaluate(prediction.predReturn15M, EntryGate.threshold(thrBase, sp));
   ```
   Tuong duong vi: (a) ban cu ap nguong truot cho CA nhanh `symbolPred==null` (nguong co so) lan
   nhanh dyn ? ban moi cung vay vi `EntryGate.threshold(thrBase, null)` tra thang `thrBase`;
   (b) `f1c43a3` da duoc chung nhan PARITY byte-identical nen phan nhan he so khong doi ngu nghia.
3. **`SimulatorMarketLevelTicker1MStopLoss`** ? goi lai `GateRollingThreshold.init(predictionMap)`
   dung 2 cho nhu `f1c43a3^` (ngay sau khi `predictionMap` duoc gan, truoc `preprocessFundingData`).

Khong sua `Configs.java` (class doc thang qua `Cfg.get`, khong qua Configs).
Khong xoa/sua test cu.

---

## 4. Cong parity (BAT BUOC, chay truoc khi doc ket qua GD92)

Voi `SIM_GATE_ROLLING_PCT` **khong khai bao**, `init()` thoat som, `hour2thr` = null,
`isOn()` = false => `thrBase` == `Configs.MIN_MOMENTUM_15M` => bieu thuc y het HEAD.
Parity phai la **byte-identical**, khong phai "gan giong".

- Build jar tren branch `gd92-recheck`, chay tag `GD_PARITY_C3` voi profile
  `x1_c3_full.properties` tren `wfo_ds_x1_2021`.
- **PASS khi** `md5sum storage/printDone.csv` == `dc16e4da6ff6cb7b8d41c592bc3d9c45`
  (= md5 cua `devrun/X1_C3_FULL_2021/storage/printDone.csv`, da xac minh truoc khi viet doc nay).
- Chon `x1_c3_full` lam cong parity vi do CHINH LA nen ma GD92 dap len (GD92 = x1_c3_full + 2 key).
- LECH => **DUNG**, khong dien giai ket qua GD92.

---

## 5. Thiet ke thi nghiem (khoa)

| Tag | Profile | Dataset |
|---|---|---|
| `GD_PARITY_C3` | `profiles/x1_c3_full.properties` | `wfo_ds_x1_2021` |
| `GD_GD92_2021` | `profiles/archive/x1_gd92.properties` | `wfo_ds_x1_2021` |

- So sanh: **GD92 vs T170** (incumbent) va **GD92 vs T100** (cung gate scale 1.0 ? doi chung tu
  nhien, tach duoc "cong cua rolling" khoi "cong cua gate scale").
- **k = 2**. `CI_INFLATE = sqrt(2 x ln 2) = 1.177410`. Dung DUNG tu dau ?
  **khong** dung hang so `1.21` sai trong `c3_rates.py` (xem `docs/audit/AUDIT_READJUDICATE_CI_RESCORE.md`).
- Block-72h paired bootstrap, `BLOCK_H=72`, `NREP=2000`, `SEED=20260905` ? y het moi vong truoc.
- 3 ty le: `win%`, `TSloss%`, `meanP`.
- **Luat THANG:** >= 2/3 ty le ngoai CI theo huong tot vs T170 **VA** rang buoc cung PASS
  **ca 5 nam 2021-2025** (lan truoc chi cham 4 nam vi dataset ngan hon).
- Rang buoc cung moi nam: `maxDD <= 15%`, `UW <= 120 ngay`, `return nam >= 0`, `return quy >= -5%`.

### Bao cao bat buoc kem
In `GateRollingThreshold.stats()` (so moc gio, `nQuery`, `nBeforeFirst`). Dataset moi bat dau
2021-07-01 ma cua so la 90 ngay => truoc ~2021-10 khong co moc; cac truy van do roi ve hang so
`MIN_MOMENTUM_15M`. Phai bao con so nay, khong duoc giau ? no quyet dinh phan nao cua 2021 that
su co rolling.

---

## 6. Du doan ghi truoc (chap nhan sai)

GD92 truoc day thang o `wfo_ds_x1` chu yeu nho **UW 227 -> 116** va CV quy ? nhung
`AUDIT_GATEDYN_GD92` da ket luan d CAGR +4.98pp voi CI `[-4.47, +16.09]` **chua 0**
(khong phan biet duoc). Du doan: tren dataset dai hon va so voi T170 (chu khong phai T100),
GD92 se **NULL** (0-1 ty le ngoai CI) va nhieu kha nang **FAIL rang buoc cung o 2025**
(cua so underwater 2025-03-04 -> 2025-10-11 la su kien he thong, rolling gate khong cham toi).

## 7. Phan bien BAT BUOC trong RESULT (viet truoc, khong duoc bo du ket qua the nao)

- **Neu GD92 THANG:** phai ghi ro day la **1 trong ~22+ phep thu da chay chong T170** trong toan
  bo chuong trinh nay; multiplicity **cap-chuong-trinh chua he duoc tinh** (k=2 chi phu cho vong
  nay). Mot chien thang don le **KHONG du** de dao incumbent; phai qua holdout 2026 truoc.
- **Neu GD92 THUA/NULL:** phai ghi ro day la **bang chung doc lap thu hai** ? khac dataset, khac
  baseline, khac thoi diem, khac nguoi chay ? cung cho ket luan cua `AUDIT_GATEDYN_GD92`;
  khong phai trung hop.

## 8. Dieu KHONG lam
Khong push. Khong merge `gd92-recheck` vao `module`. Khong cham 242. Khong dong holdout 2026.
Khong do them bien the GD92. Khong doi incumbent.
