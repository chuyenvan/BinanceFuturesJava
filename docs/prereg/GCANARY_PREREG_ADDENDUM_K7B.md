# GCANARY_PREREG — ADDENDUM K7B (2026-10-31, MASTER duyệt; viết TRƯỚC lần chạy canary kế tiếp, gói canary_3l)

- **Gốc:** `docs/prereg/GCANARY_PREREG.md` (2dd69ff0) + §ADD-1…§ADD-4. Mọi điều không nhắc ở đây giữ nguyên.
- **Phạm vi:** CHỈ tiêu chí "symbol chính bị chặn lớp (B) ngay sau khi chốt" của K7b. **Không nới bất kỳ bước K nào khác**
  (K0–K7, K6b, K8, các kiểm còn lại của K7b — symbol phụ vào được, không (A) dưới 10′, gỡ chặn, dọn — y nguyên).

## 1. Lý do (bằng chứng phiên canary 3k, 2026-10-30, tài khoản chính)
Nguồn: 242 `c3canary/run/canary/canary_jvm.log`, journal `canary_20261030_232923_step_K7B.jsonl`, kết quả
`~/claude_master/canary/canary_early_result_20261030_231654.txt` ("K7B: TRUOT | ZECUSDT KHONG bi chan (phai B) ngay sau khi chot").
- 23:30:01.749 `K7B_INJECT_ON` (positionRisk lỗi phía client); 01.761 Flattener: `positions() loi … => dung qty trong so`.
- Lệnh đóng `c3x-ZECUSDT-29889630-1`: khớp trên sàn `T=1793377801806`; CALL_W `status=FILLED executedQty=0.016` (= qty cụm 0.016).
- Sàn TỰ kết thúc stop closePosition: ALGO_UPDATE `caid=c3s-ZECUSDT-29889630-1 X=EXPIRED T=1793377801810` (**+4 ms** sau khớp;
  WS tới máy 02.212).
- 01.952 sổ đóng cụm; 02.059 `stop c3s-: 1 xu ly, 0 GIU` — guard đọc openStops (không bị tiêm lỗi) thấy stop đã final ⇒ GONE,
  không còn stop nào để GIỮ ⇒ không sinh lớp (B). Production đúng thiết kế: (B) chỉ sinh khi guard phải GIỮ stop c3s- còn mở
  (không xác minh được phẳng) hoặc positionRisk còn vị thế cho symbol vừa chốt.
- Hành vi sàn này đã ghi nhận ở K5 ngày 10-29 (§3k R1: stop closePosition bị sàn EXPIRE ~4 ms sau khớp lệnh đóng); checker K7b
  viết trước đó nên đòi (B) vô điều kiện. Kết quả phụ thuộc thứ tự REST openStops của guard so với lúc sàn EXPIRE stop.

## 2. Tiêu chí mới — "symbol chính sau khi chốt" ĐẠT khi thoả ĐÚNG MỘT trong hai đường

**Đường KEPT_B** (như cũ) — bằng chứng bắt buộc:
1. Ngay sau khi sổ hết giữ cụm symbol chính: `allowsEntry(symbol chính) = false` (bị chặn lớp B, `symbolBlocks` chứa symbol);
2. Không có chặn toàn hệ (A) (`UNKNOWN_POSITION`) lúc đó;
3. Các kiểm sau của K7b như cũ (gỡ chặn sau khi đọc phẳng; nếu (B) kéo dài ≥ 10′ phải leo thang (A) + Telegram).

**Đường EXCHANGE_TERMINAL** (mới) — chỉ khi symbol chính KHÔNG bị chặn; bắt buộc ĐỦ cả 5:
1. Lệnh đóng `c3x-` của cụm (CALL_W `newMarketOrder:SELL:RO` cuối cùng của symbol trong journal) có `status=FILLED` và
   `executedQty ≥ confirmedQty` cụm chụp TRƯỚC khi đóng;
2. Stop của cụm (clientAlgoId chụp trước khi đóng) là stop `c3s-` **closePosition** (không phải stop qty);
3. Journal có sự kiện WS `ALGO_UPDATE` đúng `caid` đó, đúng symbol, `X ∈ {EXPIRED, CANCELED}`;
4. Sự kiện đó có `ts ≥` mốc GỬI lệnh đóng (`firstSentMs` của c3x-; không có ⇒ ts ACK — chặt hơn), chờ tối đa
   `fillEventWaitMs` (5 s) cho sự kiện WS tới;
5. Không có chặn toàn hệ (A) lúc đó (như đường KEPT_B).
Ghi data: `s1.stopEnd` (`KEPT_B`|`EXCHANGE_TERMINAL`), `s1.stopEndWhy`, `s1.closeFull`, `s1.closeSince`.

**Không có bằng chứng ⇒ TRƯỢT:** symbol chính không bị chặn mà thiếu BẤT KỲ mục nào trong 5 mục của đường EXCHANGE_TERMINAL
(kể cả sự kiện WS không tới trong thời hạn) ⇒ K7b TRƯỢT như bản gốc (fail-closed).

## 3. Hiện thực
Code: `CanaryEngine.k7b` + `lastCloseCall`, `k7bCloseFull` (v1.2/c3-live `82145028`); test `CanaryK7bExchangeExpiryR4iTest`
(tái hiện chuỗi 10-30 bằng mock `expireStopsOnSellFill`; đường cũ KEPT_B; thiếu bằng chứng bị từ chối). Jar r4i md5
`2487acdb3a7fe770db27f949a6983156`, gói `~/claude_master/canary_3l`. Áp từ phiên canary kế tiếp; phiên 10-30 giữ verdict TRƯỢT trong sổ.
