# RESULT_GRAVEYARD — om bag + DCA 1:1 (toi da 2 leg) THUA cat time-stop; "ve bo" dung 63-86% nhung EV am

Pre-reg `docs/PREREG_GRAVEYARD.md` (`2e031f1`, 19:47 11/09) — chay 20:xx. Script `research/analysis/graveyard.py`, log
`/home/ubuntu/x1log/graveyard.out`. 285 lenh PST time-stop cua X1_C3_FULL canonical; hourly close `CLOSES_1H.bin`; 108 su kien
BIG_DOWN (proxy); delist = 0. Khong sim, khong 2026.

## 1. PRE-REG (quyet dinh) — EV cua von DANG GIU tai diem cat neu giu tiep (sell-vs-hold, khong tinh lo da chim)
| bien the | 90d | 180d | 365d | den cuoi | veBE(gia cat)180d | delist_or<=-80 @365d |
|---|---|---|---|---|---|---|
| H0 om | +0.1% | -13.9% | -29.6% | -46.2% | 23% | 20.3% |
| D1 (<=1 leg 1:1) | -5.2% | -11.6% | -22.2% | -45.1% | 27% | 11.0% |
| **D2 (<=2 leg 1:1) PRIMARY** | -6.2% | **-11.1%** | -22.2% | -45.9% | 30% | 8.7% |
D2 180d CI95 = **[-21.3%, +1.7%]** (can duoi > 0). Theo nam D2 180d: 2022 -27.8 / 2023 **+17.4** / 2024 -10.0 / 2025 -15.7.
> **PHAN QUYET: DONG.** Giu tiep tu diem cat co EV am (chi 2023 duong). DCA 1:1 ha lo mot chut so voi om suong, khong dao chieu.

## 2. MO TA (ngoai pre-reg) — dung frame cua user: "ve bo" = ve GIA VON TRUNG BINH tinh tu gia vao goc e0, so voi CAT
PnL tren cung 285 vi the (von goc U = margin), horizon tinh tu luc bi time-stop:
| bien the | ve bo 90d / 180d / 365d | chenh (om - CAT) / von goc: 90d | 180d | 365d | den cuoi | CI95 180d | von DCA them |
|---|---|---|---|---|---|---|---|---|
| H0 om, thoat khi ve e0 | **62.7% / 69.1% / 76.7%** (TB 18-47 ngay) | -3.8% | -2.9% | -2.4% | -6.1% | [-7.4, +1.5] | 0 |
| D2 1:1 <=2 leg, thoat khi ve avg | 67.6% / 76.0% / **86.0%** | -14.1% | **-13.3%** | -10.6% | -24.9% | **[-22.0, -4.5]** | +53..80% von goc |
| D2, thoat khi +7% tren avg | 56.6% / 66.5% / 76.2% | -15.5% | -16.3% | -15.1% | -31.7% | **[-27.0, -5.5]** | +64..100% |
| D2, om toi cung (write-off) | ~1-2% | -13.6% | -25.4% | -53.8% | **-98.1%** | [-49.3, +3.9] | +81..173% |
Theo nam 180d (D2 ve bo): 2022 -20.0 / 2023 -5.6 / 2024 -11.9 / 2025 -15.1 — **am ca 4 nam, ke ca nam hoi phuc 2023**.

## 3. DOC DUNG
1. **Truc giac "phan lon coin se ve bo" la DUNG**: om khong DCA, 63% ve e0 trong 90 ngay, 77% trong 1 nam. DCA 1:1 nang len 86%.
2. **Nhung EV van am**, vi bat doi xung: ve bo = lai **0** (chi go lo), that bai (23-37%) = lo **-58% -> -88%** median va keo dai;
   DCA nhan von 1.5-2x dung vao nhom that bai => D2 thua CAT **13% von goc** sau 180 ngay, CI loai 0. Write-off "om toi cung" = mat gan het.
3. Tra loi "giam duoi -60% roi kho giam tiep": nhom chua ve bo o 90d median -58%, 180d -68%, 365d -76%, cuoi -88% — coin low-cap
   khong co day; "chia 2" lap lai nhieu lan (2025 minloser -91%, 2022 ANC/FTT/LUNA2 ve 0).
4. Mau: 285 vi the trong ~6 cum sap => CI rong; nhung dau -/CAT thua nhat quan ca 4 nam, va CI D2 loai 0. Huong chac, do lon khong.
5. Khong test duoc "luoi 1 phut co nhip" (hourly). Nhip vao leg khac nhau doi THOI DIEM mua, khong doi ban chat: that bai mat gan het.

## 4. Cai gi trong y "edge o DCA" la THAT
Sleeve **BIG_DOWN** (mua coin MOI khi thi truong sap, 216 leg, +9,884, win 82-100%, 0/216 trung coin dang giu) va DCA_LEVEL1 hiem
(54 leg, +7,407) — edge nay ton tai vi mua dip bang von MOI vao coin do S1 chon, khong phai do them von vao bag. Bag la chi phi cua
sleeve PST, khong phai co hoi.

## 5. Khong lam
Khong doi profile/exit/DCA. Khong cham 242. Khong mo them bien the (nguong 0.80/24h/2 leg giu nguyen).

## 6. BO SUNG (NGOAI PRE-REG, 11/09 toi, theo y user) — "ve bo" = ARM 7% tren avg roi TRAILING nhu C3, khong phai thoat tai gia von
Luat: om, DCA 1:1 <= K leg theo BIG_DOWN (gia <= 0.80 avg, cooldown 24h), chua arm => khong SL; gia >= avg*1.07 => arm, trail voi
giveback = min(0.5*peak, cap 0.08 STRONG / 0.03 WEAK), SL = avg*(1+peak-giveback). Hourly close. So voi CAT (profit thuc cua lenh).
| K | armed | chenh vs CAT / von goc: 180d | 365d (n=172, chi cohort 2022-24) | den cuoi (n=283) | CI95 180d | theo nam 180d (22/23/24/25) | von them | top-5%% lenh / |PnL CAT| | chua thoat den cuoi |
|---|---|---|---|---|---|---|---|---|---|
| 0 (om suong) | 61% | -0.6% | -0.7% | -3.9% | [-6.1, +4.9] | -4.8 / +7.7 / -2.6 / +0.6 | 0 | 9-12% | 39%, med -88% |
| 2 | 70% | +0.9% | +11.3% | -9.7% | [-11.2, +13.8] | -18.1 / +11.1 / +6.1 / -2.4 | +84..98% | 39-45% | 30%, med -68% |
| 3 | 72% | +4.4% | +14.2% | -8.7% | [-10.7, +21.5] | -22.7 / +19.9 / +8.6 / +2.9 | +104..128% | 57-58% | 28%, med -63% |
| 4 | 73% | +5.5% | **+24.2%** | -5.4% | [-10.5, +22.8] | -23.1 / +24.6 / +12.6 / +0.3 | +119..153% | **63-94%** | 27%, med -58% |
Doc dung:
1. **User dung**: arm+trail doi ket qua tu "thua CAT 13%" (thoat tai gia von) thanh **hoa CAT trong nhieu** (CI chua 0 rong ca hai phia).
   Lenh thoat trail co median +5..+9%, p90 +18..+37%, max +66..+158%.
2. **Toan bo edge nam o ~12 lenh** (top 5%) = 39-94% |PnL CAT|; bo chung di la am. Dung nghi ngo cua user: "an lon ti le be".
3. **Phu thuoc regime**: 2022 am -18..-23% o moi K (coin chet), 2023/2024 duong, 2025 ~0. Horizon 365d chi co cohort 2022-24 (2025 bi censor)
   => +24% cua K=4 la so lac quan; horizon "den cuoi" (du 283) am o moi K.
4. **Von**: K=3-4 can them 104-153% von goc, khoa hang thang; 27-30% vi the khong bao gio arm (med -58..-68%). Tinh tren TONG von
   (2.2-2.5x) loi 365d cua K=4 ~ +3%/nam, trong khi CAT giai phong 83% von ngay lap tuc cho engine PST (CAGR 33.6%). Neu engine PST
   con hap thu duoc von thi CAT + tai su dung von thang ro; neu PST da bao hoa (thanh khoan low-cap) thi om+DCA la cach dung von thua.
5. Cac bien the nay them SAU khi thay so => **khong duoc dung lam phan quyet**. Muon di tiep: PREREG SIM Java rieng (time-stop off + DCA 1:1
   K leg + arm/trail + budget parts nang len de khong bop PST), tieu chi chot truoc, 48 thang; rui ro ghi truoc: 2022-type regime va
   ~12 lenh gánh edge.
