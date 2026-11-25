# MASTER_NOTE LEVZ - 2026-11-25 17:41 +0700
Prereg 5e1031bc. RUN agent a2fc6ec6 (16:56-17:21 +07), A1 agent a36035e7 (PASS-WITH-MINOR). VERDICT: NO-GO, DONG ho LEVZ.
- 4 nhanh deu truot C1 (p Holm 0,52-0,80) va C5 (bo 5 % lenh tot nhat => am o ca hai ky).
- XAC NHAN mean net_ex 24h: A1 +0,44 % [-0,58; 1,62] n 469; A2 +0,85 % [-0,37; 2,54] n 340; A3 -0,08 % n 577; A4 +0,16 % n 406.
  KHAM PHA: +0,30..+0,40 %, n 122-180, CI chua 0. MDE80 ~ 1,1-1,8 %/lenh.
- MASTER tu kiem tu events_*.parquet (8 cap nhanh x ky): n, mean, bo 5 % khop RUN va A1. Them: median DUONG (+0,7..+1,6 %) trong khi mean ~ 0
  va bo 5 % tot nhat thi am => phan phoi lech trai: da so lenh lai nho, mot so lenh lo lon (squeeze). 2022 chi 2-6 dot; 2024 chiem phan lon XAC NHAN.
- A1 tai lap doc lap: tap lenh trung 100 % (8/8), 44/44 lenh tinh tay khop; khong loi dau / gio / join; funding theo chu khong doi verdict.
- Duoc noi: dong theo luat; tin hieu co chieu dung nhung nho, khong phan biet duoc voi 0. KHONG duoc noi: "chung minh khong co tin hieu",
  "A2 co edge", bat cu gi dua vao nguong cung / guong long; khong mo lai voi nguong / cua so / phi khac.
- Chi mo ta: nguong CUNG (f >= 0,05 % + dOI24h >= 25 %) KP +2,02 % (n 64) -> XN -2,04 % (n 392) = dao dau; z-score on dinh dau hon nguong cung
  nhung van khong tach 0.
- Gioi han: MAE do bang close 1m (du lieu khong co high) = can duoi; C7 khong ket luan (khong doi verdict).
