import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import threading
import time
import json
import cv2
import numpy as np
import mss
import os
import pygetwindow as gw
import pydirectinput
from datetime import datetime

CONFIG_FILE = 'final_zones.json'
TEMPLATE_FOLDER = 'mau_vat'
THRESHOLD = 0.85

class FishingBotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Fishing Bot")
        self.root.geometry("900x600")
        self.root.configure(bg="#2c3e50")
        self.root.attributes('-topmost', True)
        self.running = False
        self.thread = None
        self.last_states = {}
        self.zone_labels = {}
        self.log_box = None
        self.arrow_templates = {}
        self.zones = []
        self.trigger_pixel = None
        self.cast_key = {}
        self.window_title = 'YouTube'
        self.setup_ui()
        self.load_config()
        self.load_templates()
        self.update_zone_labels()
        self.ensure_debug_folder()

    def setup_ui(self):
        frm = ttk.Frame(self.root, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        btn_frame = ttk.Frame(frm)
        btn_frame.pack(fill=tk.X, pady=5)
        self.btn_start = ttk.Button(btn_frame, text="BẮT ĐẦU", command=self.start_bot)
        self.btn_start.pack(side=tk.LEFT, padx=5)
        self.btn_stop = ttk.Button(btn_frame, text="DỪNG LẠI", command=self.stop_bot, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        zone_frame = ttk.LabelFrame(frm, text="Zone Status")
        zone_frame.pack(fill=tk.X, pady=10)
        self.zone_frame = zone_frame

        log_frame = ttk.LabelFrame(frm, text="Log")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        self.log_box = ScrolledText(log_frame, height=10, state="normal", font=("Consolas", 11), bg="black", fg="#00ff00")
        self.log_box.pack(fill=tk.BOTH, expand=True)
        self.log_box.config(state="disabled")

    def ensure_debug_folder(self):
        if not os.path.exists('debug_crops'):
            os.makedirs('debug_crops')

    def log_to_gui(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        if hasattr(self, 'log_box') and self.log_box:
            self.log_box.config(state="normal")
            self.log_box.insert(tk.END, log_msg + "\n")
            self.log_box.see(tk.END)
            self.log_box.config(state="disabled")
        else:
            print(log_msg)

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            self.log_to_gui(f"LỖI: Không tìm thấy file cấu hình {CONFIG_FILE}")
            return
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.zones = data.get("sub_zones", [])
        self.trigger_pixel = data.get("trigger_pixel", None)
        self.cast_key = data.get("cast_key", "f6")
        self.window_title = data.get("window_title", "YouTube")
        self.log_to_gui(f"Đã tải cấu hình: {len(self.zones)} zones, trigger_pixel: {self.trigger_pixel}, cast_key: {self.cast_key}, window_title: {self.window_title}")

    def load_templates(self):
        templates = {}
        for name in ['up', 'down', 'left', 'right']:
            path = os.path.join(TEMPLATE_FOLDER, f"{name}.png")
            if os.path.exists(path):
                img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                templates[name] = img
                self.log_to_gui(f"Đã tải mẫu: {name}.png")
            else:
                self.log_to_gui(f"CẢNH BÁO: Thiếu file {path}")
        self.arrow_templates = templates

    def update_zone_labels(self):
        # Luôn tạo đủ 5 zone
        for lbl in self.zone_labels.values():
            lbl.destroy()
        self.zone_labels = {}
        for i in range(5):
            z_id = i+1
            lbl = tk.Label(self.zone_frame, text=f"Zone {z_id}: Waiting...", width=18, height=2, bg="gray", fg="white", font=("Arial", 14, "bold"))
            lbl.grid(row=0, column=i, padx=5, pady=5)
            self.zone_labels[z_id] = lbl

    def start_bot(self):
        if not self.running:
            self.running = True
            self.btn_start.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)
            self.thread = threading.Thread(target=self.state_machine, daemon=True)
            self.thread.start()
            self.log_to_gui("Bắt đầu tự động hóa câu cá...")

    def stop_bot(self):
        self.running = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.log_to_gui("Đã dừng bot.")

    def check_color(self, x, y):
        with mss.mss() as sct:
            monitor = {"top": y, "left": x, "width": 1, "height": 1}
            img = np.array(sct.grab(monitor))
            b, g, r, _ = img[0, 0]
            return (r, g, b)

    def state_machine(self):
        # Find game window
        self.log_to_gui(f"Đang tìm cửa sổ game với tiêu đề: '{self.window_title}'...")
        windows = gw.getWindowsWithTitle(self.window_title)
        if not windows:
            self.log_to_gui(f"LỖI: Không tìm thấy cửa sổ '{self.window_title}'")
            self.stop_bot()
            return
        win = windows[0]
        self.log_to_gui(f"Đã tìm thấy cửa sổ: {win.title} tại ({win.left}, {win.top})")
        while self.running:
            # STATE 1: CASTING
            self.log_to_gui("Casting rod...")
            pydirectinput.press(self.cast_key)
            time.sleep(2)
            if not self.running: break

            # STATE 2: WAITING
            self.log_to_gui("Đang chờ cá cắn...")
            found_fish = False
            while self.running:
                x = self.trigger_pixel['x']
                y = self.trigger_pixel['y']
                r, g, b = self.check_color(x, y)
                if r > 200:
                    found_fish = True
                    break
                time.sleep(0.25)
            if not self.running: break
            if not found_fish:
                self.log_to_gui("Không phát hiện cá, thử lại...")
                continue

            # STATE 3: PREPARE
            #self.log_to_gui("Fish bitten! Preparing to catch...")
            #time.sleep(30)
            #if not self.running: break

            # STATE 4: SCAN & CATCH
            self.log_to_gui("Đang quét mũi tên...")
            start_time = time.time()
            arrows = [None]*5
            while self.running and time.time() - start_time < 30:
                win_left = win.left
                win_top = win.top
                for i in range(5):
                    z_id = i+1
                    zone = next((z for z in self.zones if z.get('id') == z_id), None)
                    if not zone:
                        arrows[i] = None
                        continue
                    monitor = {
                        "top": win_top + zone['y'],
                        "left": win_left + zone['x'],
                        "width": zone['w'],
                        "height": zone['h']
                    }
                    try:
                        with mss.mss() as sct:
                            sct_img = sct.grab(monitor)
                        img_np = np.array(sct_img)
                        gray_frame = cv2.cvtColor(img_np, cv2.COLOR_BGRA2GRAY)
                        scores = {}
                        for d, template in self.arrow_templates.items():
                            res = cv2.matchTemplate(gray_frame, template, cv2.TM_CCOEFF_NORMED)
                            _, max_val, _, _ = cv2.minMaxLoc(res)
                            scores[d] = max_val
                        winner = max(scores, key=scores.get)
                        max_score = scores[winner]
                        if max_score > THRESHOLD:
                            arrows[i] = winner.upper()
                        else:
                            arrows[i] = None
                    except Exception as e:
                        self.log_to_gui(f"Lỗi quét zone {z_id}: {e}")
                        arrows[i] = None
                if all(a is not None for a in arrows):
                    break
                time.sleep(0.05)
            if not self.running: break
            if not all(a is not None for a in arrows):
                self.log_to_gui("Không nhận diện đủ mũi tên, bỏ qua lượt này!")
                time.sleep(1)
                continue
            self.log_to_gui(f"Nhận diện: {'-'.join(arrows)}. Đang bấm phím...")
            for arrow in arrows:
                pydirectinput.press(arrow.lower())
                time.sleep(0.1)

            # STATE 5: COOLDOWN
            self.log_to_gui("Resting...")
            for _ in range(60):
                if not self.running:
                    break
                time.sleep(0.1)
        self.log_to_gui("Bot đã dừng hoàn toàn.")

if __name__ == "__main__":
    root = tk.Tk()
    app = FishingBotApp(root)
    root.mainloop()