Bạn là orchestrator CPCV PARITY GATE, chạy trực tiếp trên máy Oracle (Ubuntu). Nhiệm vụ: chứng minh Kaggle chạy CpcvBatchRunner ra kết quả KHỚP baseline Oracle, rồi DỪNG. TUYỆT ĐỐI KHÔNG fanout full 1600 cell.

== SCOPE CỨNG (vi phạm = dừng ngay) ==
- Chỉ thao tác trong: /home/ubuntu/cpcv/ (đọc/ghi), /home/ubuntu/wfo_ds_VAL/ (chỉ đọc), /home/ubuntu/java/cpcv.jar (chỉ đọc), và Kaggle datasets/kernels của user chuyendinh.
- CẤM: đụng bất cứ thứ gì thuộc module trading/bot/DB/đặt lệnh; git add/commit/push; ghi/xóa ngoài /home/ubuntu/cpcv/ (được phép tạo thư mục con /home/ubuntu/cpcv/kg/); chạy bất cứ thứ gì liên quan tiền thật; sửa cpcv.jar hay code Java.
- Cần làm gì ngoài scope trên -> DỪNG, ghi lý do vào /home/ubuntu/cpcv/orch_parity.log, không tự quyết.
- Đây là SERVER PRODUCTION. Thận trọng tối đa.

== BẪY CHÍ MẠNG (đã làm hỏng 1 lần, đừng lặp) ==
1. Worker BẮT BUỘC set env SELECTOR_RANK_TOPK=8. Quên -> rơi về -1 (rank OFF) -> kết quả SAI recipe -> parity lệch. Chính lỗi này đã làm hỏng wf_full/results.jsonl cũ (b00 ra 168 trades thay vì 69).
2. Java BẮT BUỘC chạy với -Duser.timezone=Asia/Ho_Chi_Minh. Thiếu -> lệch múi giờ -> ZERO_TRADES/kết quả sai.
3. TICKER_SOURCE=file phải có trong config.properties dùng cho Kaggle (đọc ticker từ ./kaggle_data_hpo/ relative CWD).

== BỐI CẢNH ĐÃ XÁC MINH ==
- Kaggle CLI: /home/ubuntu/kaggle_latest_venv/bin/kaggle (user chuyendinh, auth sẵn).
- Baseline reference ĐÚNG recipe (K=8): /home/ubuntu/cpcv/baseline_oracle.jsonl — 16 dòng, mỗi dòng {block,knobs,metrics:{note,maxdd_pct,calmar,trades,pnl},seq}. Ví dụ b00 seq0: note=SUCCESS calmar=1.7404 trades=69 pnl=68.4131 maxdd_pct=0.0011.
- Parity input cells: /home/ubuntu/cpcv/baseline_cells.jsonl — 16 dòng {block,end,knobs,seq,start}. ĐÂY là shard cho parity.
- jar: /home/ubuntu/java/cpcv.jar, class chính com.binance.chuyennd.ai_ml.wfo.CpcvBatchRunner.
- config: /home/ubuntu/cpcv/run/config.properties (đã có TICKER_SOURCE=file).
- Dataset VAL (market/pred/funding.bin + manifest.txt): /home/ubuntu/wfo_ds_VAL/.
- Ticker ĐÃ CÓ trên Kaggle, KHÔNG upload lại: chuyendinh/wfo-ticker-2024h1, -2024h2, -2025h1, -2025h2 (đủ cho VAL window 2024-07 -> 2025-12; nếu parity lệch nghi thiếu lookback thì thêm chuyendinh/wfo-ticker-2023). Ticker per-file dạng ticker_2*.bin*, symlink vào /kaggle/working/kaggle_data_hpo.
- Scaffold THAM KHẢO (KHÔNG copy nguyên): /home/ubuntu/claudedata/.run/kernels/wfo-worker-1/run_worker.py — nó chạy WfoWorker+jobstore với env recipe CŨ (K=5). Bạn chỉ mượn phần glob dataset + chuẩn ticker symlink; phần chạy phải thay bằng CpcvBatchRunner + K=8 + shard file, KHÔNG jobstore, KHÔNG WFO_STATE_HOST.

== LỆNH CHẠY CpcvBatchRunner (đối chiếu cách baseline Oracle đã chạy đúng) ==
env CPCV_CELLS=<shard.jsonl> CPCV_OUT=<out.jsonl> WFO_DATA_DIR=<ds_dir chứa manifest.txt> WFO_SMART_CACHE=1 SELECTOR_RANK_TOPK=8 java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx20g -cp <cpcv.jar> com.binance.chuyennd.ai_ml.wfo.CpcvBatchRunner
(CpcvBatchRunner tự set các frozen flags trong main: DCA_GRID_ENABLED/SCALAR=true, OFF_FLAT_HARD=true, FILTER_MODE=A, BREAKER_MODE=OFF, APPLY_FUNDING_FEE=true. Nếu nghi ngờ thì đọc code trong jar để xác nhận, ĐỪNG tự thêm env đè.)

== CÁC BƯỚC (làm tuần tự, ghi log mỗi bước vào /home/ubuntu/cpcv/orch_parity.log) ==
1. VERIFY tiền đề: cpcv.jar tồn tại và `unzip -l /home/ubuntu/java/cpcv.jar | grep -c CpcvBatchRunner` > 0; baseline_cells.jsonl và baseline_oracle.jsonl đều 16 dòng; /home/ubuntu/wfo_ds_VAL có manifest.txt + 3 file .bin. Thiếu gì -> DỪNG, ghi ERROR.
2. UPLOAD 2 Kaggle dataset nếu chưa có (kiểm bằng `kaggle datasets status chuyendinh/<id>`; lỗi 403/404 = chưa có):
   a. cpcv-jar: tạo /home/ubuntu/cpcv/kg/ds_jar/, cp /home/ubuntu/java/cpcv.jar và /home/ubuntu/cpcv/run/config.properties vào; viết dataset-metadata.json {id:"chuyendinh/cpcv-jar", title:"cpcv-jar", licenses:[{name:"CC0-1.0"}]}; `kaggle datasets create -p /home/ubuntu/cpcv/kg/ds_jar`.
   b. wfo-ds-val: viết /home/ubuntu/wfo_ds_VAL/dataset-metadata.json {id:"chuyendinh/wfo-ds-val", title:"wfo-ds-val", licenses:[{name:"CC0-1.0"}]}; `kaggle datasets create -p /home/ubuntu/wfo_ds_VAL --dir-mode zip` (300MB, chờ status=ready, poll mỗi 30s tối đa ~15 phút).
   c. cells-parity: tạo /home/ubuntu/cpcv/kg/ds_cells/, cp baseline_cells.jsonl vào (đổi tên cells.jsonl); metadata id chuyendinh/cpcv-cells-parity; create.
3. VIẾT worker /home/ubuntu/cpcv/kg/parity/run_cpcv_worker.py (Python, dùng logging chứ không print nếu tiện; nhưng đây là kernel script nên print ra stdout để xem log Kaggle là chấp nhận được):
   - glob /kaggle/input/**: cpcv.jar, config.properties, manifest.txt (-> ds_dir = dirname), cells.jsonl.
   - chuẩn ticker: glob /kaggle/input/**/ticker_2*.bin*, tạo /kaggle/working/kaggle_data_hpo, symlink từng file vào đó; in số file; nếu 0 -> exit 1.
   - shutil.copy config.properties -> /kaggle/working/config.properties; os.chdir('/kaggle/working').
   - chạy lệnh CpcvBatchRunner y như mục "LỆNH CHẠY" ở trên, với CPCV_CELLS=<cells.jsonl>, CPCV_OUT=/kaggle/working/out.jsonl, WFO_DATA_DIR=<ds_dir>, SELECTOR_RANK_TOPK=8, -Duser.timezone=Asia/Ho_Chi_Minh, -cp <cpcv.jar>.
   - sys.exit tường minh theo returncode (KAGGLE cần exit rõ).
4. Tạo kernel-metadata.json trong /home/ubuntu/cpcv/kg/parity/: {id:"chuyendinh/cpcv-w-parity", title:"cpcv-w-parity", code_file:"run_cpcv_worker.py", language:"python", kernel_type:"script", is_private:true, enable_gpu:false, enable_internet:true, dataset_sources:["chuyendinh/cpcv-jar","chuyendinh/wfo-ds-val","chuyendinh/cpcv-cells-parity","chuyendinh/wfo-ticker-2024h1","chuyendinh/wfo-ticker-2024h2","chuyendinh/wfo-ticker-2025h1","chuyendinh/wfo-ticker-2025h2"]}.
5. `kaggle kernels push -p /home/ubuntu/cpcv/kg/parity`. Poll `kaggle kernels status chuyendinh/cpcv-w-parity` mỗi 30s tới complete hoặc error (tối đa ~40 phút). error -> pull log, ghi ERROR, DỪNG.
6. Pull output: `kaggle kernels output chuyendinh/cpcv-w-parity -p /home/ubuntu/cpcv/kg/parity/out`. Đọc out.jsonl.
7. SO SÁNH out.jsonl (Kaggle) vs baseline_oracle.jsonl, join theo (seq,block): trades phải BẰNG CHÍNH XÁC; note phải khớp; calmar và pnl reltol <= 1e-3 (chấp nhận sai số float nhỏ). Sim tất định nên kỳ vọng khớp gần tuyệt đối.
8. GHI /home/ubuntu/cpcv/parity_result.json: {"verdict":"MATCH"|"MISMATCH"|"ERROR","n_cells":N,"n_match":M,"mismatches":[{"seq":..,"block":"..","field":"trades|calmar|pnl|note","oracle":..,"kaggle":..}],"kaggle_kernel":"chuyendinh/cpcv-w-parity","note":"..."}.
9. DỪNG. In ra tóm tắt cuối: verdict + số cell khớp/lệch + vài dòng mismatch nếu có. TUYỆT ĐỐI KHÔNG chạy fanout 1600 cell — đó là bước sau, chờ người duyệt.

Nếu bất kỳ bước nào lỗi: DỪNG ngay tại đó, ghi lỗi rõ ràng vào orch_parity.log và parity_result.json (verdict ERROR), KHÔNG nhảy bước, KHÔNG "chữa cháy" bằng cách đổi recipe/config.
