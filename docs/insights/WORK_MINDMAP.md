# WORK MINDMAP — trạng thái & phân tích song song (2026-06-16)

> Ảnh chụp trạng thái THỰC sau phiên TASK-035 (forward OI/LS/taker + migration + fill-gap).
> Lưu ý: `docs/AGENTS.md` còn ghi 013/035/040 = TODO — LỆCH thực tế; cần cập nhật (xem cuối file).

## 1. Mindmap tổng (theo nhóm năng lực)

```mermaid
mindmap
  root((Rebuild BinanceFutures))
    Data integrity B0
      Exit-fix trailing clamp DONE
      Backfill OI/LS/taker 013 DONE
      Sync 226 to 242 040 DONE
      Forward ingest 035 DONE deployed
      Migration keySYM to chunk DONE 242+226
      Fill-gap 242 RUNNING
      Fill-gap 226 NEXT
      Golden multi-range 003.1 WAIT user
    Gate model WHEN
      Label return 012 DONE
      Feature A 015 DONE
      Feature B gia/funding 017 DONE
      Feature B OI/LS-market 018 UNBLOCK
      Ghep dataset 025 WAIT
      Train 3-class 026 WAIT
    Funding selector WHICH
      Label triple-barrier 024 DONE
      F1F2 go basket+ten 036 RUN-NOW
      F3 feature non-OI 037 WAIT
      F4 feature OI/LS/taker 038 WAIT
      F5 ghep+train 039 WAIT
    Live deploy
      Deploy dot1 016/019 DONE
      Deploy dot2 027-031/033 WAIT user
      Basis 1m 022 REVIEW
      ADR-0008+ extraction TODO
```

## 2. Chuỗi phụ thuộc + trạng thái (cái gì khoá cái gì)

```mermaid
graph TD
    classDef done fill:#1b5e20,color:#fff;
    classDef run fill:#0d47a1,color:#fff;
    classDef next fill:#e65100,color:#fff;
    classDef wait fill:#424242,color:#fff;
    classDef user fill:#4a148c,color:#fff;

    EXIT[Exit-fix DONE]:::done
    B13[013 backfill DONE]:::done
    B40[040 sync 226-242 DONE]:::done
    B35I[035 forward ingest DONE]:::done
    MIG[migration keySYM-chunk DONE]:::done
    FG242[fill-gap 242 RUNNING]:::run
    FG226[fill-gap 226 NEXT]:::next
    B0[B0 integrity CLOSURE]:::next

    B13 --> B40 --> B35I --> MIG --> FG242 --> FG226 --> B0
    EXIT --> B0
    B0 --> B1[B1b / B2 / B4 mo khoa]:::wait

    L12[012 label DONE]:::done
    F15[015 feat A DONE]:::done
    F17[017 feat B DONE]:::done
    F18[018 feat B OI/LS TODO]:::next
    D25[025 ghep dataset WAIT]:::wait
    T26[026 train gate WAIT]:::wait
    B13 --> F18
    L12 --> D25
    F15 --> D25
    F17 --> D25
    F18 --> D25 --> T26

    L24[024 label funding DONE]:::done
    F36[036 F1F2 RUN-NOW]:::next
    F37[037 F3 feat non-OI WAIT]:::wait
    F38[038 F4 feat OI/LS/taker WAIT]:::wait
    F39[039 F5 ghep+train WAIT]:::wait
    F36 --> F37
    B13 --> F38
    F37 --> F38
    F37 --> F39
    F38 --> F39
    L24 --> F39

    G003[003.1 golden Crash range WAIT user]:::user
    DEP2[033 deploy dot2 WAIT user]:::user
```

## 3. Phân tích SONG SONG — làm gì trong lúc fill-gap 242 chạy (~1h)

Nguyên tắc: fill-gap 242 đang poll Binance + ghi 242. Việc song song KHÔNG được đụng (a) Binance REST cùng lúc (đụng guard/ban), (b) ghi nặng vào 226/242.

| Việc | Song song? | Lý do |
|---|---|---|
| 036 F1/F2 (xác minh export path thật + sửa tên feature) | NGAY | Thuần local (đọc code + sửa tên), không đụng Binance/Aerospike. AGENTS ghi "chạy ngay song song". |
| ADR-0008+ extraction (slippage/filter-C/dd4h/AI-filter/funding-decode) | NGAY | Thuần viết tài liệu. |
| Cập nhật AGENTS.md (013/035/040 -> DONE) | NGAY | Doc; đang lệch thực tế. |
| 018 spec (B6 OI-market + B8 LS-market gate feature) | NGAY (chỉ spec) | 013 done -> unblock; viết spec không đụng infra. |
| fill-gap 226 | ĐỢI | Cùng poll Binance với 242 -> đụng guard/gấp đôi tải/ban. Chạy sau khi 242 xong. |
| 037/038 (feature funding Kaggle) | 038 đọc 5 set OI 226 -> đợi fill-gap xong cho data đủ | Tránh đọc khi đang ghi. |
| 025/026 (gate train) | ĐỢI | Cần 018 xong trước. |

Đề xuất: chạy 036 song song ngay (local, tiền đề cho 037/039, và F1 trùng open-item "đường export getTopCoin vs findPotentialLosers" đang treo). Kèm cập nhật AGENTS.md.

## 4. Việc treo cần user quyết (không phải Claude)
- 003.1: chốt độ rộng Crash range (Q2-only vs Q2-Q4).
- 033: duyệt deploy đợt 2 (027/028/029/030/031) — build+runbook sẵn, chỉ restart 2 live.
- 022: chốt dùng basis 1m + schema -> mở B2 backfill.
- 039: chốt target funding (+6%/+40%) trước khi train.
</content>