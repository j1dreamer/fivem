import customtkinter as ctk
import tkinter as tk
from tkinter import StringVar
import threading
import time
import json
import cv2
import numpy as np
import mss
import os
import pygetwindow as gw
import pydirectinput
import keyboard
from datetime import datetime

CONFIG_FILE = 'final_zones.json'
TEMPLATE_FOLDER = 'mau_vat'
THRESHOLD = 0.85
ZONE_COUNT = 5

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")

class FishingProApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Auto Fishing Pro")
        self.geometry("400x550")
        self.resizable(False, False)
        self.configure(fg_color="#FFC0CB")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.running = False
        self.fishing_thread = None
        self.hotkey_thread = None
        self.arrow_templates = {}
        self.zones = []
        self.trigger_pixel = None
        self.window_title = "YouTube"
        self.cast_key = "1"
        self.hotkey = "F9"
        self.status_var = StringVar(value="Trạng thái: ĐANG NGHỈ")
        self.status_color = "#e74c3c"
        self.action_btn_text = StringVar(value="BẮT ĐẦU (F9)")
        self.action_btn_color = "#27ae60"
        self.load_config()
        self.load_templates()
        self.create_widgets()
        self.listen_hotkey()

    def create_widgets(self):
        # Header
        ctk.CTkLabel(self, text="HỆ THỐNG CÂU CÁ", font=("Arial", 22, "bold"), text_color="#333333", fg_color="#FFC0CB").pack(pady=(25, 10))
        # Status
        self.status_label = ctk.CTkLabel(self, textvariable=self.status_var, font=("Arial", 18, "bold"), text_color=self.status_color, fg_color="#FFC0CB")
        self.status_label.pack(pady=(0, 20))
        # Main Action Button
        self.action_btn = ctk.CTkButton(self, textvariable=self.action_btn_text, fg_color=self.action_btn_color, hover_color="#16a085", font=("Arial", 20, "bold"), corner_radius=20, height=60, width=260, command=self.toggle_fishing)
        self.action_btn.pack(pady=(0, 30))
        # Settings Frame
        settings_frame = ctk.CTkFrame(self, fg_color="white", corner_radius=18)
        settings_frame.pack(pady=(0, 20), padx=20, fill="x")
        # Row 1: Cast Key
        ctk.CTkLabel(settings_frame, text="Phím quăng cần:", font=("Arial", 14), text_color="#333333", fg_color="white").grid(row=0, column=0, padx=(18, 5), pady=18, sticky="w")
        self.cast_key_var = StringVar(value=self.cast_key)
        self.cast_key_menu = ctk.CTkOptionMenu(settings_frame, variable=self.cast_key_var, values=[str(i) for i in range(1,7)], width=80, command=self.save_settings)
        self.cast_key_menu.grid(row=0, column=1, padx=(0, 18), pady=18, sticky="e")
        # Row 2: Hotkey
        ctk.CTkLabel(settings_frame, text="Phím tắt Bật/Tắt:", font=("Arial", 14), text_color="#333333", fg_color="white").grid(row=1, column=0, padx=(18, 5), pady=(0, 18), sticky="w")
        self.hotkey_var = StringVar(value=self.hotkey)
        self.hotkey_menu = ctk.CTkOptionMenu(settings_frame, variable=self.hotkey_var, values=[f"F{i}" for i in range(1,13)], width=80, command=self.save_settings)
        self.hotkey_menu.grid(row=1, column=1, padx=(0, 18), pady=(0, 18), sticky="e")
        # Footer
        ctk.CTkButton(self, text="Hide UI", fg_color="#888888", hover_color="#555555", font=("Arial", 14), corner_radius=16, command=self.iconify).pack(side="bottom", pady=18)

    def set_status(self, running):
        if running:
            self.status_var.set("Trạng thái: ĐANG CHẠY")
            self.status_label.configure(text_color="#27ae60")
            self.action_btn.configure(fg_color="#e74c3c")
            self.action_btn_text.set(f"DỪNG LẠI ({self.hotkey_var.get()})")
        else:
            self.status_var.set("Trạng thái: ĐANG NGHỈ")
            self.status_label.configure(text_color="#e74c3c")
            self.action_btn.configure(fg_color="#27ae60")
            self.action_btn_text.set(f"BẮT ĐẦU ({self.hotkey_var.get()})")

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            return
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.zones = data.get("sub_zones", [])
        self.trigger_pixel = data.get("trigger_pixel", None)
        self.cast_key = str(data.get("cast_key", "1"))
        self.hotkey = data.get("hotkey", "F9")
        self.window_title = data.get("window_title", "YouTube")

    def save_settings(self, *_):
        # Save cast_key and hotkey to config
        if not os.path.exists(CONFIG_FILE):
            return
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["cast_key"] = self.cast_key_var.get()
        data["hotkey"] = self.hotkey_var.get()
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        self.cast_key = self.cast_key_var.get()
        self.hotkey = self.hotkey_var.get()
        self.action_btn_text.set(f"BẮT ĐẦU ({self.hotkey})")

    def load_templates(self):
        templates = {}
        for name in ['up', 'down', 'left', 'right']:
            path = os.path.join(TEMPLATE_FOLDER, f"{name}.png")
            if os.path.exists(path):
                img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                templates[name] = img
        self.arrow_templates = templates

    def listen_hotkey(self):
        def hotkey_worker():
            while True:
                try:
                    keyboard.wait(self.hotkey_var.get().lower())
                    self.toggle_fishing()
                    time.sleep(0.5)  # Debounce
                except Exception:
                    time.sleep(1)
        self.hotkey_thread = threading.Thread(target=hotkey_worker, daemon=True)
        self.hotkey_thread.start()

    def toggle_fishing(self):
        if self.running:
            self.running = False
            self.set_status(False)
        else:
            if not self.fishing_thread or not self.fishing_thread.is_alive():
                self.running = True
                self.set_status(True)
                self.fishing_thread = threading.Thread(target=self.fishing_state_machine, daemon=True)
                self.fishing_thread.start()

    def check_color(self, x, y):
        with mss.mss() as sct:
            monitor = {"top": y, "left": x, "width": 1, "height": 1}
            img = np.array(sct.grab(monitor))
            b, g, r, _ = img[0, 0]
            return (r, g, b)

    def fishing_state_machine(self):
        # Find game window
        windows = gw.getWindowsWithTitle(self.window_title)
        if not windows:
            self.set_status(False)
            return
        win = windows[0]
        while self.running:
            # STATE 1: CASTING
            pydirectinput.press(self.cast_key)
            time.sleep(2)
            if not self.running: break
            # STATE 2: WAITING
            found_fish = False
            while self.running:
                x = self.trigger_pixel['x']
                y = self.trigger_pixel['y']
                r, g, b = self.check_color(x, y)
                if r > 200:
                    found_fish = True
                    break
                time.sleep(0.5)
            if not self.running: break
            if not found_fish:
                continue
            # STATE 3: PREPARE
            time.sleep(1.5)
            if not self.running: break
            # STATE 4: SCAN & CATCH
            start_time = time.time()
            arrows = [None]*ZONE_COUNT
            while self.running and time.time() - start_time < 5:
                win_left = win.left
                win_top = win.top
                for i in range(ZONE_COUNT):
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
                    except Exception:
                        arrows[i] = None
                if all(a is not None for a in arrows):
                    break
                time.sleep(0.05)
            if not self.running: break
            if not all(a is not None for a in arrows):
                time.sleep(1)
                continue
            for arrow in arrows:
                pydirectinput.press(arrow.lower())
                time.sleep(0.1)
            # STATE 5: COOLDOWN
            for _ in range(60):
                if not self.running:
                    break
                time.sleep(0.1)
        self.set_status(False)

    def on_close(self):
        self.running = False
        self.destroy()

if __name__ == "__main__":
    app = FishingProApp()
    app.mainloop()
