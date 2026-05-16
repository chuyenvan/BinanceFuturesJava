import os

# Đường dẫn thư mục của bạn (Sử dụng r'' để tránh lỗi dấu gạch chéo Windows)
input_dir = r'E:\educa\source\github\20260415\BinanceFuturesJava\src\main\java\com\binance\chuyennd\ai_ml\hpo\kaggle'
output_file = 'Binance_Futures_Full_Code.txt'

def combine_java_files(source_dir, output_path):
    count = 0
    with open(output_path, 'w', encoding='utf-8') as outfile:
        # Duyệt qua tất cả thư mục con
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                if file.endswith('.java'):
                    file_path = os.path.join(root, file)
                    # Lấy đường dẫn tương đối để AI dễ hiểu cấu trúc package
                    relative_path = os.path.relpath(file_path, source_dir)

                    outfile.write(f"\n\n{'='*50}\n")
                    outfile.write(f"FILE PATH: {relative_path}\n")
                    outfile.write(f"{'='*50}\n\n")

                    try:
                        with open(file_path, 'r', encoding='utf-8') as infile:
                            outfile.write(infile.read())
                        count += 1
                        print(f"Đã gộp: {relative_path}")
                    except Exception as e:
                        print(f"Lỗi khi đọc file {relative_path}: {e}")

    print(f"\n--- HOÀN THÀNH ---")
    print(f"Tổng số file đã gộp: {count}")
    print(f"File kết quả lưu tại: {os.path.abspath(output_path)}")

if __name__ == "__main__":
    combine_java_files(input_dir, output_file)