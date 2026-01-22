
import google.generativeai as genai
import os
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.live import Live

# --- CẤU HÌNH ---
# Dùng tên model ổn định nhất của bạn
MODEL_NAME = 'gemini-flash-latest' 
API_KEY = 'AIzaSyBZyW7TEi-pNcXBq4hD3l83M1RluXvMmJk'

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(MODEL_NAME)
chat = model.start_chat(history=[])

# Khởi tạo công cụ in ấn đẹp
console = Console()

def start_chat():
    console.print(Panel.fit(f"[bold cyan]🤖 GEMINI CLI - Giao diện Rich[/bold cyan]\n[dim]Model: {MODEL_NAME}[/dim]"))
    console.print("[italic green]Gõ 'exit' để thoát. Gõ '/doc <path>' để đọc file.[/italic green]\n")

    while True:
        # 1. Nhập liệu
        user_input = console.input("[bold yellow]Bạn:[/bold yellow] ")
        
        if user_input.lower() in ['exit', 'quit']:
            break
        
        if not user_input.strip():
            continue

        # 2. Xử lý hiển thị
        print("") # Xuống dòng cho thoáng
        
        try:
            # Dùng Live display để render Markdown ngay khi text đang chạy
            with Live(console=console, refresh_per_second=10) as live:
                accumulated_text = ""
                response = chat.send_message(user_input, stream=True)
                
                for chunk in response:
                    if chunk.text:
                        accumulated_text += chunk.text
                        # Render Markdown liên tục
                        md = Markdown(accumulated_text)
                        live.update(Panel(md, title="Gemini", border_style="blue"))
            
            print("") # Xuống dòng kết thúc

        except Exception as e:
            console.print(f"[bold red]❌ Lỗi:[/bold red] {e}")

if __name__ == "__main__":
    start_chat()