# Xác nhận jar dataset cho `nup-a7r-s21` (trước khi push, 2026-10-27)

Yêu cầu MASTER: kernel A7 phải chạy jar `ce4bcc17…`, không phải `66740305…`.

## Cách xác nhận (3 lớp, độc lập)

1. **Dataset version hiện hành** — `GET https://www.kaggle.com/api/v1/datasets/view/chuyendinh/sim-jar-nup-tier2`:
   - `currentVersionNumber = 3`
   - `lastUpdated = 2026-10-26T04:21:14.267Z`
   - `totalBytes = 99 802 213`
   - `versions[0].versionNotes = "A7 q2 cache fix (jar ce4bcc17)"`
2. **Số học byte khớp tuyệt đối**:
   - local `~/claude_master/nup2_wk/sim.jar` = 99 797 653 byte, sha256 `ce4bcc17b824862d5f2b828d244dc7bb51dc6434420697d608b2196ea1012329`
   - profile `prof_r4_kg0_k16_f015_g155.properties` = 4 560 byte
   - tổng = 99 802 213 = `totalBytes` của version 3.
   - (jar cũ `sim-jar-tsx` = 99 795 936 byte; cộng profile = 99 800 496 ≠ 99 802 213 ⇒ loại.)
3. **Sau khi chạy** — `~/kaggle_sim/out/nup-a7r-s21/result.json` phải có
   `jar_sha256 = ce4bcc17…`; nếu khác ⇒ run KHÔNG dùng để chấm.

## Ghi chú
- `kaggle datasets download` cho dataset này trả `404 No gcs url found` (cả API lẫn CLI, thử 2 lần);
  không tải được zip để băm trực tiếp. Vì vậy dùng 3 lớp trên, lớp 3 là bằng chứng quyết định.
- Kernel metadata của Kaggle không pin version dataset (`dataset_sources: ["chuyendinh/sim-jar-nup-tier2"]`),
  nên phải kiểm version hiện hành ngay trước push + kiểm `jar_sha256` trong result.json sau chạy.
- Tag mới `nup-a7r-s21` (slug mới) để không tái dùng kernel cũ `nup-a7-s21` — chính lỗi tái dùng slug
  đã khiến lần trước kéo về output NUP cũ (jar 66740305, dừng ở 20210823).
