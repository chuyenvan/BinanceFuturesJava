# RISK_APPETITE — nguong RUI RO (khau vi) dung cho MOI bai cham diem

Chot 2026-09-16 boi user (chat): *"nới maxdd lên 30 và uw dãn ra 200, ci vẫn 2 cho chuẩn"*.
Day la thay doi **KHAU VI RUI RO**, KHONG phai thay doi **NGUONG BANG CHUNG**.

## 1. Nguong moi (thay nguong cu)

| rang buoc | CU | MOI |
|---|---|---|
| `maxDD` (theo nam) | <= 15% | **<= 30%** |
| `UW` (ngay) | <= 120 | **<= 200** |
| nam am | khong | khong (GIU) |
| quy xau nhat | >= -5% | >= -5% (GIU) |
| NGUONG BANG CHUNG | >= 2 rate ngoai CI | **GIU NGUYEN** (`>=2`, bootstrap block-72h, x1.21, 2000 rep, seed 20260905) |

Ghi chu: nguong cu `UW <= 120` da duoc ghi nhan la **KHONG dat duoc** tren cua so 48 thang
(`docs/AGENT_RUNBOOK.md` muc 3: ca hai arm FAIL — 2024=121 ngay, 2025=302/227 ngay). Nguong 200
phu hop hon voi do dai cua so hien tai.

## 2. HAU QUA — phai biet truoc khi dung

- Nguong rui ro la **cua PHU QUYET (veto)**, khong phai bang chung. Noi rong veto => chap nhan
  nhieu ung vien di tiep hon.
- Cu the: `C3_mom006` (maxDD -20.75%, UW 133 ngay, 2024Q2 -8.3%) truoc day bi **LOAI vi FAIL 3/4
  rang buoc cung**; duoi nguong MOI **no PASS cong rui ro**. No van bi loai — nhung bi loai bang
  **bang chung** (0/5 rate chat luong ngoai CI), khong con bang rui ro.
- => Tu nay cac ung vien rui ro cao nhung "chua chung minh duoc gi" se duoc dua sang vong cham
  BANG CHUNG thay vi bi chan som. Day la lua chon da duoc chap nhan (doi lay quyen thu nhieu ung
  vien hon), nhung lam tang nguy co false-positive neu vong bang chung bi noi long sau nay.
- **CANH BAO noi bo:** thay doi nay duoc dua ra SAU khi da nhin thay ket qua `DROP` (equity +28%).
  Vi vay no chi duoc dung o tang **khau vi**; **KHONG** duoc dung de dien giai lai bang chung cua
  `DROP`/`SIZE`.

## 3. Cham lai 6 bien the gan nhat duoi nguong MOI (chi doc lai `sim.out`, KHONG chay sim)

MaxDD nam xau nhat / UW dai nhat (tu `sim.out` tung run, da co san):

| bien the | maxDD nam xau nhat | UW dai nhat | nguong CU | nguong MOI |
|---|---|---|---|---|
| PARITY (T170) | -11.84 (2022) | 92 (2024) | PASS | PASS |
| SIZE `DOWN50` | -11.89 (2022) | 119 (2024) | PASS | PASS |
| SIZE `DOWN25` | -11.87 (2022) | 119 (2024) | PASS | PASS |
| SIZE `UP50` | -11.80 (2022) | 88 (2024) | PASS | PASS |
| SEL `DROP` | -11.65 (2022) | 119 (2024) | PASS | PASS |
| SEL `MIX` | -11.66 (2022) | 119 (2024) | PASS | PASS |
| SEL `DROP_TOP8` | -11.56 (2022) | 119 (2024) | PASS | PASS |

- Ca 7 dong deu **PASS ca nguong CU lan MOI**; khong nam nao am. => Noi nguong **khong doi ket qua**
  cua 6 bien the nay (chung da PASS tu truoc).
- Ket luan PRIMARY van la **0/3 rate ngoai CI** cho ca 6 bien the => **NULL, giu T170**.
  Nguong rui ro **khong the** bien mot ket qua 0/3 thanh WIN.
- Nguong MOI chi tro thanh rang buoc **binding** khi mot bien the co `maxDD > 11.89%` hoac
  `UW > 119 ngay`.

## 4. Con treo (chua chot)

- Hai rang buoc `khong nam am` va `quy >= -5%` CHUA duoc noi (user chi noi maxDD/UW). Luu y bat
  nhat quan: chap nhan maxDD 30% ma cam nam am la hoi cang — neu muon noi tiep thi noi rieng.
- Bang `quy xau nhat` khong co trong `sim.out` cua 6 run nay o dang doc truc tiep => **chua do lai**
  cho 6 bien the; giu nguyen ket luan cu (khong bien the nao cham quy).
- Nguong trong `docs/AGENT_RUNBOOK.md` muc 0.3 da duoc cap nhat tro ve file nay.
