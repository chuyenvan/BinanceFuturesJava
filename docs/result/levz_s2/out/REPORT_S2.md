# REPORT_S2 (CHUA AUDIT) - tieu chi S-a..S-e (PREREG_LEVZ_S2 sec 5) + REF

Chon cau hinh = select_b1.rule NGUYEN VEN; "gop nam train" = min qua cac fold train (nhu B1 gop F1 + F2). Chi tinh cac nam CHAM DUOC.

| tap | nam cham | top20 med 2023/24/25 | S-a | S-b | p_wfo | S-c | S-d | S-e | ket luan | p_max [in-sample] |
|---|---|---|---|---|---|---|---|---|---|---|
| REF | 0 | n/a/n/a/n/a | False | True | nan | False | False | False | KHONG HON D0 | 0.13 |
| P5 | 1 | -0.392/n/a/n/a | False | False | 0.96 | False | False | False | KHONG HON D0 | 0.99 |
| P5b | 2 | -0.326/-0.079/n/a | False | False | 0.59 | False | False | False | KHONG HON D0 | 0.96 |
| P6a | 2 | -0.306/-0.215/n/a | False | False | 0.43 | False | False | False | KHONG HON D0 | 0.97 |
| P6b | 2 | -0.176/-0.278/n/a | False | False | 0.32 | False | False | False | KHONG HON D0 | 0.89 |

**REF khong cham du nam qua quy trinh S2 => doi chieu lay tu B1 (da audit): WFO top-20 2024 -23,0 %, 2025 +6,1 %, khong co 2023 - QUY TRINH KHAC (ERRATA2 F2)** (REF cham duoc: khong nam nao)

p_wfo (ERRATA2 F1): luot ngau nhien chi cong tren DUNG cac nam tap that cham duoc; thieu nam nao => KHONG >= that.
Chi tiet (top-1, mo ta muc 6, ban do tham so, tuong quan thu hang): report_s2.json
