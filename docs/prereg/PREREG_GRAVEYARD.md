# PREREG_GRAVEYARD — counterfactual OFFLINE: "khong cat, om bag + DCA 1:1 toi da 2 leg, chap nhan mat" co EV duong khong?

Chot: 2026-09-11, commit TRUOC khi chay. Khong sim Java, khong 2026, khong doi profile. De xuat cua user (11/09): thay time-stop
bang OM vi the kep dinh; DCA 1:1 (khong martingale 1,1,3,8) toi da 2-3 lan theo nhip BIG_DOWN roi DUNG; chap nhan bag do mat luon
(delist) hoac ve bo neu pump manh. Cau hoi do duoc bang du lieu co san: **von bo vao "nghia dia" nay sinh loi hay mat, bao nhieu?**

## 1. Du lieu / don vi
- 285 lenh PREDICT_SYMBOL_TRADE `STOP_LOSS_DONE` cua X1_C3_FULL canonical (`devrun/X1_C3_FULL_PARITY_R`, md5 2478e90d...).
  Moi lenh = 1 vi the doc lap tu **thoi diem cat t0 = `end`** voi **gia cat p0 = `tp`**, gia vao goc e0 = `entry`, don vi von U = `margin`.
- Gia: `/home/ubuntu/java/fsrun/CLOSES_1H.bin` (hourly close, toi 2026-01-01). symId qua `selector_pred_out/symbol_map.csv`.
- Su kien BIG_DOWN: tap thoi diem `start` (unique) cua cac leg `level == BIG_DOWN` trong cung printDone (216 leg) — proxy cho "thi
  truong sap" ma sim da phat hien. Gioi han ghi truoc: chi co su kien luc sim con budget => co the thieu su kien.
- Delist: coin het gia truoc moc horizon > 7 ngay => gia tri = **0** (PRIMARY, than trong); phu: gia cuoi cung.

## 2. Ba bien the (chot)
- **H0 hold**: giu U tu p0, khong them gi.
- **D1**: them toi da 1 leg U khi (a) co su kien BIG_DOWN tai t > t0 + 1h, (b) gia <= 0.80 x gia von trung binh hien tai, (c) >= 24h ke
  tu leg truoc. Sau do giu.
- **D2 (PRIMARY)**: nhu D1, toi da 2 leg. (= "DCA 1:1 lan 2-3 roi dung" cua user.)
Khong co bien the thu 4. Khong doi nguong 0.80 / 24h / so leg sau khi thay so.

## 3. Do
Horizon 90 / 180 / 365 ngay sau t0 va "den cuoi" (2026-01-01 hoac delist). Cho tung bien the:
- **Loi tren von khoa** (capital-weighted) = (tong gia tri - tong von) / tong von; median loi tung vi the; % ve BE (gia tri >= von);
  % >= +50%; % delist hoac <= -80%; von-ngay bi khoa (U x ngay) so voi cung von neu quay vong trong engine PST.
- Bootstrap theo vi the (2000 rep, seed 20260911) cho loi tren von khoa 180d. Theo nam cat va theo bin do sau luc cat.
- n theo horizon (2025 bi censor: horizon 365d chi co cho lenh cat truoc 2025-01).

## 4. QUY TAC QUYET DINH (chot)
> "NGHIA DIA DANG PRE-REG SIM" <=> D2 co loi tren von khoa **180d** (delist = 0) voi **CI95 duoi > 0** VA ti le
> (delist hoac <= -80%) tai 365d **< 15%** (tren tap co du 365d).
> Nguoc lai => **DONG**: om+DCA khong co EV duong do duoc; ly do duy nhat con lai la khau vi (chap nhan lo bounded) — la quyet dinh
> chinh sach, khong phai thi nghiem.
Ky vong ghi truoc: H0 am (HOLD_TO_DIE: 38% khong ve BE 180d, mdd tiep sau); D1/D2 ha BE nen % ve BE tang, nhung von gap doi/ba
dung vao nhom delist 11.5% => loi tren von khoa quanh 0 hoac am. Neu duong ro => bat ngo, dang di tiep.

## 5. Gioi han (ghi truoc)
Hourly close (khong test "luoi 1 phut co nhip" — do trong sim neu qua cong); khong phi; funding bo qua (do 285 lenh SL: median
+0.09%/tuan, p10 2025 long DUOC nhan 5%/tuan — khong phai chi phi); khong mo hinh slot/budget bi khoa (bao cao von-ngay de nguoi
doc tu can); mau 285 vi the trong ~6 cum sap => CI rong, doc theo huong, khong doc theo so le.
