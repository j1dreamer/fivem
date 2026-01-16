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
from datetime import datetime

THRESHOLD = 0.8
CONFIG_FILE = 'final_zones.json'
TEMPLATE_FOLDER = 'mau_vat'
GAME_WINDOW_TITLE = 'YouTube'  # Đổi tên theo game nếu cần

class ArrowDetectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Arrow Detector GUI")
        self.root.geometry("900x600")
        self.root.configure(bg="#2c3e50")
        self.root.attributes('-topmost', True)
        self.running = False
        self.thread = None
        self.last_states = {}
        self.zone_labels = {}
        self.log_box = None
        self.debug_snapshot = False
        self.setup_ui()  # Tạo GUI trước
        self.arrow_templates = self.load_templates()  # Tải mẫu sau khi có log_box
        self.zones = self.load_zones()  # Tải config sau khi có log_box
        self.ensure_debug_folder()
        self.update_zone_labels()  # Luôn tạo đủ 5 zone

    def setup_ui(self):
        frm = ttk.Frame(self.root, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        btn_frame = ttk.Frame(frm)
        btn_frame.pack(fill=tk.X, pady=5)
        self.btn_start = ttk.Button(btn_frame, text="BẮT ĐẦU", command=self.start_detection)
        self.btn_start.pack(side=tk.LEFT, padx=5)
        self.btn_stop = ttk.Button(btn_frame, text="DỪNG LẠI", command=self.stop_detection, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=5)
        self.btn_debug = ttk.Button(btn_frame, text="DEBUG SNAPSHOT", command=self.trigger_debug_snapshot)
        self.btn_debug.pack(side=tk.LEFT, padx=5)

        zone_frame = ttk.LabelFrame(frm, text="Zone Status")
        zone_frame.pack(fill=tk.X, pady=10)
        self.zone_frame = zone_frame
        # self.zone_labels = {}  # Đã khởi tạo ở __init__

        log_frame = ttk.LabelFrame(frm, text="Log")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        self.log_box = ScrolledText(log_frame, height=10, state="normal", font=("Consolas", 11), bg="black", fg="#00ff00")
        self.log_box.pack(fill=tk.BOTH, expand=True)
        self.log_box.config(state="disabled")

    def ensure_debug_folder(self):
        if not os.path.exists('debug_crops'):
            os.makedirs('debug_crops')

    def trigger_debug_snapshot(self):
        self.debug_snapshot = True
        self.log_to_gui("Sẽ lưu ảnh crop ở lần quét tiếp theo!")

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
        return templates

    def load_zones(self):
        if not os.path.exists(CONFIG_FILE):
            self.log_to_gui(f"LỖI: Không tìm thấy file cấu hình {CONFIG_FILE}")
            return []
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        zones = data.get("sub_zones", [])
        self.log_to_gui(f"Đã tải cấu hình: {len(zones)} zones.")
        return zones

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

    def start_detection(self):
        if not self.running:
            self.running = True
            self.btn_start.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)
            self.thread = threading.Thread(target=self.detect_loop, daemon=True)
            self.thread.start()
            self.log_to_gui("Bắt đầu nhận diện...")

    def stop_detection(self):
        self.running = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.log_to_gui("Đã dừng nhận diện.")

    def detect_loop(self):
        GAME_WINDOW_TITLE = 'YouTube'
        self.log_to_gui(f"Đang tìm cửa sổ game với tiêu đề: '{GAME_WINDOW_TITLE}'...")
        windows = gw.getWindowsWithTitle(GAME_WINDOW_TITLE)
        if not windows:
            self.log_to_gui(f"LỖI: Không tìm thấy cửa sổ '{GAME_WINDOW_TITLE}'")
            self.stop_detection()
            return
        win = windows[0]
        self.log_to_gui(f"Đã tìm thấy cửa sổ: {win.title} tại ({win.left}, {win.top})")
        with mss.mss() as sct:
            while self.running:
                win_left = win.left
                win_top = win.top
                states = {}
                for i in range(5):
                    z_id = i+1
                    zone = next((z for z in self.zones if z.get('id') == z_id), None)
                    if not zone:
                        states[z_id] = None
                        continue
                    monitor = {
                        "top": win_top + zone['y'],
                        "left": win_left + zone['x'],
                        "width": zone['w'],
                        "height": zone['h']
                    }
                    try:
                        sct_img = sct.grab(monitor)
                    except Exception as e:
                        self.log_to_gui(f"LỖI grab màn hình zone {z_id}: {e}")
                        states[z_id] = None
                        continue
                    img_np = np.array(sct_img)
                    gray_frame = cv2.cvtColor(img_np, cv2.COLOR_BGRA2GRAY)
                    # Winner takes all
                    scores = {}
                    for d, template in self.arrow_templates.items():
                        res = cv2.matchTemplate(gray_frame, template, cv2.TM_CCOEFF_NORMED)
                        _, max_val, _, _ = cv2.minMaxLoc(res)
                        scores[d] = max_val
                    winner = max(scores, key=scores.get)
                    max_score = scores[winner]
                    if max_score > 0.8:
                        percent = int(max_score * 100)
                        states[z_id] = winner.upper()
                        self.log_to_gui(f"Zone {z_id}: {winner.upper()} ({percent}%)")
                    else:
                        states[z_id] = None
                    # Visual debug: save crop if requested
                    if self.debug_snapshot:
                        cv2.imwrite(f"debug_crops/zone_{z_id}_capture.png", img_np)
                if self.debug_snapshot:
                    self.log_to_gui("Đã lưu ảnh crop cho 5 zone!")
                    self.debug_snapshot = False
                self.update_dashboard(states)
                time.sleep(0.05)

    def update_dashboard(self, states):
        for z_id, lbl in self.zone_labels.items():
            state = states.get(z_id)
            if state:
                lbl.config(bg="green", text=f"Zone {z_id}: {state}")
            else:
                lbl.config(bg="gray", text=f"Zone {z_id}: Waiting...")
        # Log trạng thái thay đổi
        if states != self.last_states:
            msg = " | ".join([f"Z{z}: {states[z] if states[z] else '--'}" for z in self.zone_labels])
            self.log_to_gui(f"Trạng thái: {msg}")
            self.last_states = states.copy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ArrowDetectorApp(root)
    root.mainloop()