# PREREG_INGEST_HYBRID — tiêu chí nghiệm thu ingestor lai (WS chính + REST bổ trợ) TRƯỚC khi chuyển collectData 242

Ngày chốt: 2026-10-30 (trước khi viết code). Thiết kế: `docs/plan/INGESTOR_HYBRID.md`. Mọi ngưỡng dưới đây KHÔNG được sửa sau khi
thấy số; đổi ngưỡng = addendum có lý do, ký trước khi đo cửa sổ kế tiếp. Người chấm: agent đo (Sonnet/Opus) + MASTER duyệt.

## 1. Đối tượng & giai đoạn đo
- **H** = ingestor lai (`INGEST_IMPL=hybrid`). **B** = collectData hiện tại (đối chứng, không gate).
- **S1 (Oracle, sink files)**: tối thiểu **14 ngày lịch** liên tục, phải chứa ≥1 **ngày biến động** (định nghĩa §4). Không có ngày biến động trong 14 ngày ⇒ kéo dài tới 28 ngày; vẫn không có ⇒ kết luận XÁM (không chuyển).
- **S2 (242, set `*_hyb`)**: tối thiểu **3 ngày** sau S1 ĐẠT, cùng tiêu chí (trừ chaos).
- Ngày = ngày UTC. Cửa sổ chỉ bắt đầu sau khi jar H md5 + env được ghi vào doc kết quả; đổi jar ⇒ cửa sổ mới (trừ sửa thuần công cụ đo, khai addendum).

## 2. Tập tham chiếu
- **U(t)** = symbol USDT PERPETUAL status TRADING theo `exchangeInfo` snapshot mỗi 15′ (lưu lại, PIT), trừ symbol niêm yết <5′ trước t.
- **Final chuẩn**: Vision daily `klines 1m` (O,H,L,C,quoteVolume → float32); symbol/ngày Vision chưa có ⇒ REST `klines` lấy ≥10′ sau đóng nến (≤100 weight/giờ từ Oracle, tuần tự, dừng ngay khi 429/418).
- So sánh float32, cho phép ≤1 ulp (khớp quy ước `kline_rest_check_242`).

## 3. Tiêu chí ĐẠT (tất cả phải đạt, từng ngày và cả cửa sổ)
| # | Chỉ số | Ngưỡng ĐẠT |
|---|---|---|
| K1 | Độ phủ nến 1m tại +60 s: ô (symbol∈U(t), phút) có final | **100 %** (0 ô thiếu) |
| K2 | Độ phủ tại +5 s (trước live đọc +6 s) | ≥ 99,9 % ô/ngày và mọi phút ≥ 99 % |
| K3 | Độ trễ chốt (đóng nến → ghi xong): p50 / p99 / max theo ngày | ≤ 1,5 s / ≤ 4,5 s / ≤ 6,0 s ở ≥ 99,95 % phút |
| K4 | Sai khác 5 trường vs final chuẩn (sau +60 s) | **0 ô** |
| K5 | Đồng nhất với B (`kline_1m_opt` 242) | ≥ 99,99 % ô trùng; mọi ô khác: H = chuẩn (nếu B = chuẩn ⇒ TRƯỢT) |
| P1 | Tuổi `price` (now − ts) lấy mẫu mỗi 10 s, mọi symbol∈U | p99 ≤ 2 s; max ≤ 10 s (≤ 30 s trong đúng 1 lần reconnect có log) |
| P2 | |price H − ticker/price REST| lấy mẫu 20 symbol/giờ cùng giây | median ≤ 0,05 %, p99 ≤ 0,3 % |
| F1 | Funding `r`,`T` vs `premiumIndex` (mỗi 30′, mọi symbol) | 100 % trùng `T`; `r` trùng ≤1 ulp ở ≥ 99,9 % |
| F2 | Mốc settle funding ghi vào `funding_data` vs REST `fundingRate` lịch sử | 0 thiếu, 0 sai (kể cả qua restart chaos) |
| O1 | OI/LS/taker: điểm 5m (symbol×metric) có trong ≤ 40′ | ≥ 99,9 %; giá trị = REST cùng điểm 100 % |
| W1 | Weight REST tự đếm của H/phút | mean ≤ 150, **max ≤ 300** |
| W2 | 429 / 418 / -1003 do H | **0** |
| R1 | JVM H thoát/restart ngoài kế hoạch | **0**; RSS sau ngày 2 tăng ≤ 50 MB/ngày |
| R2 | Restart luồng nội bộ (`thread_restarts`) | ≤ 3/ngày, mỗi lần không vi phạm K1/P1 |
| C1 | (S1) Chaos: `INGEST_CHAOS=1` cắt 1 shard mỗi 2h + 1 lần/ngày cắt toàn bộ WS 60 s | K1 vẫn 100 %; mỗi sự cố ≤ 1 phút vi phạm K2 |
| C2 | Xoay chủ động 24h | ≥ 1 lần/shard trong cửa sổ, 0 phút vi phạm K2 do xoay |

## 4. Ngày biến động (kiểm hành vi khi sập)
- Định nghĩa (tính từ Vision sau khi xong ngày): ∃ cửa sổ 30′ có BTC giảm ≥ 2 % HOẶC median 50 alt thanh khoản cao nhất giảm ≥ 4 %.
- Ngày này chấm RIÊNG với cùng ngưỡng (không nới). Thêm: H không tăng weight >2× trung vị ngày thường; 0 restart JVM; B (đối chứng) ghi lại số restart/ban để so.

## 5. Kết luận
- **ĐẠT**: mọi dòng §3 đạt ở S1 (có ngày biến động) và S2 ⇒ được viết script chuyển S3.
- **XÁM**: thiếu dữ liệu đo (lỗi công cụ, Vision chậm) hoặc không có ngày biến động ⇒ không chuyển, kéo dài/addendum.
- **TRƯỢT**: bất kỳ vi phạm K1, K4, W2, R1, F2, hoặc K5 nghiêng về B ⇒ sửa code, cửa sổ MỚI từ đầu (không cộng dồn ngày cũ).

## 6. Sau chuyển (S3) — giám sát 7 ngày & điều kiện ROLLBACK
Rollback ngay (`rollback_ingest_hybrid.sh <TS>`, 1 lệnh, owner hoặc watchdog tự gọi) nếu một trong:
- phút có K1 < 100 % không tự lành trong 3′; `price_age_max` > 30 s quá 1 phút; bất kỳ 429/418 trên IP 242 sau chuyển;
- JVM collectData restart ngoài kế hoạch; v_t_m log lỗi đọc `kline_1m_opt`/`price_realtime` mới phát sinh; OI-GUARD-2 kích hoạt;
- header `X-MBX-USED-WEIGHT-1M` > 1 800 ở ≥ 3 phút/giờ.
Sau 7 ngày sạch: gỡ code legacy ở bản sau (không trong cùng deploy).
