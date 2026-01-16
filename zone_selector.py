import tkinter as tk
import json
import pygetwindow as gw
import sys
import threading
import time

# --- CẤU HÌNH DPI ĐỂ KHÔNG BỊ LỆCH TỌA ĐỘ TRÊN WINDOWS 10/11 ---
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except:
    pass
# -------------------------------------------------------------

def get_target_window():
    # Lấy danh sách tất cả cửa sổ có tiêu đề
    windows = [w for w in gw.getAllWindows() if w.title != '']
    
    print("\n--- DANH SÁCH CỬA SỔ ĐANG MỞ ---")
    for i, w in enumerate(windows):
        print(f"[{i}] {w.title}")
    print("--------------------------------")
    
    while True:
        try:
            choice = int(input("Nhập số thứ tự (ID) cửa sổ bạn muốn vẽ: "))
            if 0 <= choice < len(windows):
                target = windows[choice]
                # Nếu cửa sổ đang thu nhỏ thì restore lại
                if target.isMinimized:
                    target.restore()
                # Active cửa sổ lên trên cùng
                try:
                    target.activate()
                except:
                    pass
                return target
            else:
                print("Số không hợp lệ!")
        except ValueError:
            print("Vui lòng nhập số!")

class WindowZoneSelector:
    def __init__(self):
        # 1. Chọn cửa sổ trước
        self.target_win = get_target_window()
        print(f"\nĐã chọn: '{self.target_win.title}'")
        print(f"Vị trí: {self.target_win.left}, {self.target_win.top}, {self.target_win.width}x{self.target_win.height}")
        print("Đang khởi tạo lớp phủ...")
        time.sleep(1) # Chờ 1 chút để cửa sổ ổn định

        # 2. Setup Tkinter khớp vị trí cửa sổ chọn
        self.root = tk.Tk()
        
        # Đặt vị trí tool đè đúng lên cửa sổ target
        # Cú pháp geometry: "WidthxHeight+X+Y"
        geo_str = f"{self.target_win.width}x{self.target_win.height}+{self.target_win.left}+{self.target_win.top}"
        self.root.geometry(geo_str)
        
        self.root.overrideredirect(True) # Mất thanh tiêu đề (chỉ còn khung nội dung)
        self.root.attributes('-topmost', True) # Luôn nằm trên cùng
        self.root.attributes('-alpha', 0.3) # Trong suốt
        self.root.configure(bg='black')
        
        self.root.bind('<Escape>', self.quit_tool)
        self.root.bind('<Return>', self.save_zones)

        # Biến vẽ
        self.start_x = None
        self.start_y = None
        self.current_rect = None
        self.zones = [] 

        self.canvas = tk.Canvas(self.root, cursor="cross", bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

        self.canvas.create_text(
            self.target_win.width//2, 30, 
            text=f"Đang vẽ trên: {self.target_win.title} (Enter lưu, Esc thoát)", 
            fill="#00ff00", font=("Arial", 10, "bold")
        )

        self.root.mainloop()

    def on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.current_rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=2)

    def on_move_press(self, event):
        cur_x, cur_y = (event.x, event.y)
        self.canvas.coords(self.current_rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        x1, y1 = self.start_x, self.start_y
        x2, y2 = event.x, event.y
        
        # Đây là tọa độ TƯƠNG ĐỐI so với cửa sổ game (Rất quan trọng)
        x = min(x1, x2)
        y = min(y1, y2)
        w = abs(x1 - x2)
        h = abs(y1 - y2)

        if w > 5 and h > 5:
            self.zones.append({'x': x, 'y': y, 'w': w, 'h': h})
            self.canvas.itemconfig(self.current_rect, outline='green', width=2)
            self.canvas.create_text(x + w/2, y + h/2, text=str(len(self.zones)), fill="green")
            print(f"Zone {len(self.zones)} (Relative): x={x}, y={y}, w={w}, h={h}")

    def save_zones(self, event):
        data = {
            "window_title": self.target_win.title,
            "zones": self.zones
        }
        with open('zones_relative.json', 'w') as f:
            json.dump(data, f, indent=4)
        print(f"--> Đã lưu {len(self.zones)} vùng vào 'zones_relative.json'")
        self.root.destroy()

    def quit_tool(self, event):
        self.root.destroy()

if __name__ == "__main__":
    # Chạy bằng Python 3.11 nhé: py -3.11 window_selector.py
    WindowZoneSelector()