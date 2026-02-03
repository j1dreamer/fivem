import customtkinter as ctk
import tkinter as tk
from tkinter import StringVar, messagebox
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
import re

# --- CONFIGURATION ---
CONFIG_FILE = 'final_zones.json'
TEMPLATE_FOLDER = 'mau_vat'
MATCH_THRESHOLD = 0.80      # CCORR works well with higher thresholds, but binary is strict. 0.80 is safe.
BINARY_THRESHOLD_VAL = 175
ZONE_COUNT = 5
TURBO_SCALE = 0.5           # 50% Scaling

# --- THEME SETUP ---
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")

class FishingProApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Auto Fishing Pro (Spam Scan)")
        self.geometry("400x600")
        self.resizable(False, False)
        self.configure(fg_color="#FFB6D9")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # --- STATE VARIABLES ---
        self.running = False
        self.fishing_thread = None
        self.hotkey_thread = None
        self.arrow_templates = {}  # Stores BINARY templates
        self.zones = []
        self.window_title = "FiveM® by Cfx.re - LUQUY Roleplay"
        self.cast_key = "1"
        self.hotkey = "F9"
        
        # UI Variables
        self.status_var = StringVar(value="Trạng thái: ĐANG NGHỈ")
        self.status_color = "#e74c3c"
        self.action_btn_text = StringVar(value="BẮT ĐẦU (F9)")
        self.action_btn_color = "#27ae60"
        
        # --- INITIALIZATION ---
        self.load_config()
        self.load_templates()
        self.create_widgets()
        self.listen_hotkey()

    def create_widgets(self):
        # Header
        header_label = ctk.CTkLabel(self, text="HỆ THỐNG CÂU CÁ", font=("Arial", 24, "bold"), 
                                    text_color="#333333", fg_color="#FFB6D9")
        header_label.pack(pady=(30, 10))
        
        # Status Label
        self.status_label = ctk.CTkLabel(self, textvariable=self.status_var, font=("Arial", 18, "bold"), 
                                         text_color=self.status_color, fg_color="#FFB6D9")
        self.status_label.pack(pady=(0, 20))
        
        # Main Action Button
        self.action_btn = ctk.CTkButton(self, textvariable=self.action_btn_text, fg_color=self.action_btn_color, 
                                        hover_color="#16a085", font=("Arial", 20, "bold"), corner_radius=20, 
                                        height=60, width=280, command=self.toggle_fishing)
        self.action_btn.pack(pady=(0, 30))
        
        # Settings Frame
        settings_frame = ctk.CTkFrame(self, fg_color="white", corner_radius=18)
        settings_frame.pack(pady=(0, 20), padx=25, fill="x")
        
        # Grid Layout
        settings_grid = ctk.CTkFrame(settings_frame, fg_color="transparent")
        settings_grid.pack(pady=15, padx=20)

        # Cast Key
        ctk.CTkLabel(settings_grid, text="Phím quăng:", font=("Arial", 14), text_color="#333333").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.cast_key_var = StringVar(value=self.cast_key)
        self.cast_key_menu = ctk.CTkOptionMenu(settings_grid, variable=self.cast_key_var, values=[str(i) for i in range(1, 10)], width=80, fg_color="#FFB6D9", button_color="#FF9EBF", button_hover_color="#FF85AF", text_color="black", command=self.save_settings)
        self.cast_key_menu.grid(row=0, column=1, pady=10, sticky="e")
        
        # Hotkey
        ctk.CTkLabel(settings_grid, text="Phím tắt:", font=("Arial", 14), text_color="#333333").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.hotkey_var = StringVar(value=self.hotkey)
        self.hotkey_menu = ctk.CTkOptionMenu(settings_grid, variable=self.hotkey_var, values=[f"F{i}" for i in range(1, 13)], width=80, fg_color="#FFB6D9", button_color="#FF9EBF", button_hover_color="#FF85AF", text_color="black", command=self.save_settings)
        self.hotkey_menu.grid(row=1, column=1, pady=10, sticky="e")
        
        # Hide UI
        ctk.CTkButton(self, text="Ẩn UI", fg_color="#888888", hover_color="#555555", font=("Arial", 14), corner_radius=16, height=35, command=self.iconify).pack(side="bottom", pady=25)

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
            print("Config file not found.")
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.zones = data.get("sub_zones", [])
            # Trigger pixel removed
            self.cast_key = str(data.get("cast_key", "1"))
            self.hotkey = data.get("hotkey", "F9")
            self.window_title = data.get("window_title", "FiveM® by Cfx.re - LUQUY Roleplay")
        except Exception as e:
            print(f"Error loading config: {e}")

    def save_settings(self, *_):
        if not os.path.exists(CONFIG_FILE): return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["cast_key"] = self.cast_key_var.get()
            data["hotkey"] = self.hotkey_var.get()
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            self.cast_key = self.cast_key_var.get()
            self.hotkey = self.hotkey_var.get()
            self.action_btn_text.set(f"BẮT ĐẦU ({self.hotkey})")
        except Exception as e:
            print(f"Error saving settings: {e}")

    # === CORE: EXTREME TURBO LOAD LOGIC ===
    def load_templates(self):
        """Load templates -> Grayscale -> Resize 50% -> Binary Threshold 175"""
        print(f"Loading templates from: {TEMPLATE_FOLDER}")
        templates = {}
        
        if not os.path.exists(TEMPLATE_FOLDER):
             print(f"Template folder missing: {TEMPLATE_FOLDER}")
             return

        loaded_names = []
        try:
            files = os.listdir(TEMPLATE_FOLDER)
            for filename in files:
                if filename.lower().endswith(".png"):
                    name = os.path.splitext(filename)[0]
                    path = os.path.join(TEMPLATE_FOLDER, filename)
                    
                    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        # 1. Resize 50%
                        h, w = img.shape
                        new_h, new_w = int(h * TURBO_SCALE), int(w * TURBO_SCALE)
                        img_resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                        
                        # 2. Binary Threshold (Use 175)
                        _, img_binary = cv2.threshold(img_resized, BINARY_THRESHOLD_VAL, 255, cv2.THRESH_BINARY)
                        
                        templates[name] = img_binary
                        loaded_names.append(name)
        except Exception as e:
            print(f"Error reading templates: {e}")
        
        self.arrow_templates = templates
        print(f"Loaded {len(templates)} BINARY templates: {', '.join(loaded_names)}")

    def listen_hotkey(self):
        def hotkey_worker():
            while True:
                try:
                    if keyboard.is_pressed(self.hotkey_var.get().lower()):
                        self.toggle_fishing()
                        time.sleep(0.5)
                    time.sleep(0.05)
                except:
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

    def activate_game_window(self):
        try:
            windows = gw.getWindowsWithTitle(self.window_title)
            if not windows: return None
            win = windows[0]
            if not win.isActive:
                win.activate()
                time.sleep(0.2)
            if not win.isMaximized:
                win.maximize()
                time.sleep(0.2)
            # Click Center
            pydirectinput.click(x=win.left + win.width//2, y=win.top + win.height//2)
            return win
        except:
            return None

    # === CORE: SPAM SCANNER (180s Timeout) ===
    def scan_spam_process(self, win_left, win_top):
        print(">>> STARTING CONTINUOUS SCAN (180s Limit) <<<")
        start_time = time.time()
        found_arrows = [None] * ZONE_COUNT
        
        while self.running and (time.time() - start_time < 180):
            # Check Timeout
            
            # For each zone
            for i in range(ZONE_COUNT):
                if found_arrows[i] is not None: continue # Skip found

                z_id = i + 1
                zone_def = next((z for z in self.zones if z.get('id') == z_id), None)
                if not zone_def: continue

                monitor = {
                    "top": win_top + zone_def['y'],
                    "left": win_left + zone_def['x'],
                    "width": zone_def['w'],
                    "height": zone_def['h']
                }

                try:
                    with mss.mss() as sct:
                        # Capture & Grayscale
                        img_gray = cv2.cvtColor(np.array(sct.grab(monitor)), cv2.COLOR_BGRA2GRAY)
                        
                        # 1. Resize 50%
                        h, w = img_gray.shape
                        new_h, new_w = int(h * TURBO_SCALE), int(w * TURBO_SCALE)
                        img_small = cv2.resize(img_gray, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                        
                        # 2. Binary Threshold (Same as Templates: 175)
                        _, img_binary = cv2.threshold(img_small, BINARY_THRESHOLD_VAL, 255, cv2.THRESH_BINARY)
                        
                        # 3. Match
                        best_match = None
                        best_val = 0
                        
                        for name, tmpl in self.arrow_templates.items():
                            # NOTE: Using TM_CCORR_NORMED per latest fix
                            res = cv2.matchTemplate(img_binary, tmpl, cv2.TM_CCORR_NORMED)
                            _, max_val, _, _ = cv2.minMaxLoc(res)
                            
                            if max_val > best_val:
                                best_val = max_val
                                best_match = name
                        
                        # Early Exit
                        if best_val > MATCH_THRESHOLD:
                            found_arrows[i] = best_match
                            # Continue to next zone
                except Exception as e:
                    print(f"Scan Error: {e}")

            # Check if We Found ALL 5
            if all(a is not None for a in found_arrows):
                return found_arrows
            
            # Reset found array if only partially found after a short partial burst? Use logic:
            # If arrows appear sequentially, we hold `found_arrows`.
            # If they disappear, `found_arrows` retains old values?
            # Actually, typically arrows appear 1-by-1 or all at once. 
            # If we assume they persist until solved, keeping state is fine.
            # If they flash and disappear, we might act on partials, but requirement says "If 5 arrows found".

            # Ultra Fast Loop (No sleep or tiny sleep)
            time.sleep(0.01)

        return None # Timeout

    def fishing_state_machine(self):
        print("FISHING STARTED (Strategic Mode: Spam Scan)")
        win = self.activate_game_window()
        if not win:
            messagebox.showerror("Error", "Game not found!")
            self.running = False; self.set_status(False); return

        while self.running:
            # STATE 1: CAST
            print("[1] Casting...")
            if not win.isActive: 
                try: win.activate() 
                except: pass
            pydirectinput.press(self.cast_key)
            time.sleep(2.0)
            if not self.running: break

            # STATE 2: SPAM SCAN (Replaces Sentinel & Reaction)
            # Immediately start looking for arrows for up to 180s
            print("[2] Scanning for arrows (Max 180s)...")
            results = self.scan_spam_process(win.left, win.top)
            
            # STATE 3: ACT or TIMEOUT
            if results and all(results):
                print(f"[3] SUCCESS: {results}")
                # Batch Press
                for raw_key in results:
                    # Clean key name (remove digits)
                    key = re.sub(r'\d+', '', raw_key).lower()
                    print(f"Pressing: {key}")
                    pydirectinput.keyDown(key)
                    time.sleep(0.15) # Hold duration for FiveM
                    pydirectinput.keyUp(key)
                    time.sleep(0.1)  # Gap between keys
            else:
                print("[3] TIMEOUT: No arrows found in 180s.")

            # STATE 4: COOLDOWN
            print("[4] Cooldown 5s...")
            for _ in range(50):
                if not self.running: break
                time.sleep(0.1)

        print("FISHING ENDED")
        self.set_status(False)

    def on_close(self):
        self.running = False
        self.destroy()
        os._exit(0)

if __name__ == "__main__":
    app = FishingProApp()
    app.mainloop()
