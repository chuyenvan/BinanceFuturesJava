# PREREG_E2E_REPLAY_V12 — ERRATA 4 (CHỐT 2026-11-17 ~01:45 +07, MASTER; TRƯỚC khi dựng fixture 11-05 và trước lượt chính thức)

**Căn cứ:** A1 vòng 3 (`~/claude_master/v12/A1_E2E_V12_R3.md`): DUYỆT harness `def1f034` cho lượt chính thức, kèm cảnh báo về cách gắn nhãn E2.
Chưa có lượt replay nào trên fixture 11-05. Errata này chỉ làm rõ một câu tự mâu thuẫn của ERRATA 3; không đổi ngưỡng nào.

## E14. Cách gắn nhãn lệch của E2 (làm rõ ERRATA 3 E9)
- Prereg §5 E2: "MỌI SUBMIT lệch phải thuộc đúng một nhãn khai trước … Lệch không gán được nhãn ⇒ FAIL" — tức TẬP NHÃN được khai trước, còn việc
  gán một lệch cụ thể vào nhãn chỉ làm được sau khi biết lệch nào xảy ra. Câu của ERRATA 3 "không được thêm nhãn sau khi thấy kết quả" đọc
  theo nghĩa đen sẽ khiến không lệch nào gán được nhãn (file nhãn theo symbol phải commit trước khi biết symbol) ⇒ mâu thuẫn với §5.
- Làm rõ:
  1. Lượt chính thức chạy với `labels_1105.csv` rỗng (md5 ghi trong result.json). Bộ chấm in E2 THÔ (số khớp, danh sách lệch).
  2. Nếu E2 thô có lệch: việc gán nhãn do **A1 độc lập** làm (không phải dev, không phải MASTER), CHỈ trong tập nhãn đã khai
     {`LEGACY-11-05`; khác jar r4q↔fin2 ở BIG_DOWN-SEL / universe A1; exchangeInfo}. Mỗi nhãn phải kèm bằng chứng KHÔNG lấy từ output replay:
     dòng log dry thật ngày 11-05, hoặc khác biệt exchangeInfo (bản fixture 10-27 so với bản ngày 11-05), hoặc file:dòng của `git diff`
     giữa commit jar r4q và 5e10325b giải thích đúng symbol + phút đó. Không có bằng chứng ⇒ lệch đó KHÔNG có nhãn ⇒ E2 FAIL.
  3. Ngưỡng giữ nguyên: ≥ 20/23 SUBMIT thật khớp (symbol + phút) và budget |Δ|/b ≤ 1e-4 trên các SUBMIT khớp; mọi lệch còn lại phải có nhãn
     theo điểm 2. Không được thêm LOẠI nhãn mới.
  4. Báo cáo ghi cả E2 thô và E2 sau gán nhãn, kèm bảng bằng chứng.

## E15. Ghi chú vận hành lượt chính thức
- Ngay trước khi chạy phải xác nhận `oracle_heavy.lock` trống (script ghi khoá chính thức trước khi chờ lock). Mất lượt vì lỗi HẠ TẦNG
  (không phải do jar / harness / tiêu chí): ghi errata nêu nguyên nhân, chạy lại với `E2E_ERRATA=<tên>`, báo cáo cả hai lượt (prereg §2).
- Lượt chính thức không có lượt S-TS. Nếu X1 trên R0 "KHÔNG ĐỦ MẪU" (thiếu time-stop hoặc trailing tự nhiên, hoặc n < 10): theo prereg §5,
  bổ sung bằng đường giá tổng hợp phải được khai trong errata TRƯỚC khi chạy bổ sung; cho tới đó (iii) chưa PASS.
- `E2E_REPLAY_V12_RESULT.md` do MASTER / agent viết từ `result.json` + `check_v12.json` sau lượt chạy và commit cùng md5 đầu vào.
