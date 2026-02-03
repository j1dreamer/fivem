import customtkinter as ctk
import cv2
import numpy as np
import mss
import json
import os
import time

# --- CONFIG ---
CONFIG_FILE = 'final_zones.json'
TEMPLATE_FOLDER = 'mau_vat'
DEBUG_FOLDER = 'debug_output'
BINARY_THRESHOLD_VAL = 175
TURBO_SCALE = 0.5
ZONE_COUNT = 5

class VisionDebugger(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Vision Debugger - Binary Analysis")
        self.geometry("400x300")
        self.configure(fg_color="#2c3e50")

        # Create output dirs
        os.makedirs(os.path.join(DEBUG_FOLDER, "templates"), exist_ok=True)
        os.makedirs(os.path.join(DEBUG_FOLDER, "zones"), exist_ok=True)

        self.btn = ctk.CTkButton(self, 
                                 text="CHỤP ẢNH & PHÂN TÍCH", 
                                 font=("Arial", 20, "bold"),
                                 height=80, 
                                 width=300,
                                 fg_color="#e74c3c", 
                                 hover_color="#c0392b",
                                 command=self.run_analysis)
        self.btn.pack(pady=100)
    
    def load_config(self):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)

    def run_analysis(self):
        print("\n" + "="*40)
        print(">>> STARTING VISION ANALYSIS <<<")
        print("="*40)
        
        config = self.load_config()
        sub_zones = config.get('sub_zones', [])
        
        # 1. PROCESS & SAVE TEMPLATES
        print(f"\n[PHASE 1] Processing Templates (Threshold {BINARY_THRESHOLD_VAL})...")
        templates = {}
        for f in os.listdir(TEMPLATE_FOLDER):
            if f.lower().endswith('.png'):
                name = os.path.splitext(f)[0]
                path = os.path.join(TEMPLATE_FOLDER, f)
                
                # Load -> Resize -> Binary
                img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                if img is None: continue
                
                h, w = img.shape
                nh, nw = int(h * TURBO_SCALE), int(w * TURBO_SCALE)
                img_small = cv2.resize(img, (nw, nh))
                
                _, img_binary = cv2.threshold(img_small, BINARY_THRESHOLD_VAL, 255, cv2.THRESH_BINARY)
                
                templates[name] = img_binary
                
                # Save Debug Image
                out_path = os.path.join(DEBUG_FOLDER, "templates", f"{name}_binary.png")
                cv2.imwrite(out_path, img_binary)
                print(f" Saved: {out_path}")

        # 2. CAPTURE & ANALYZE ZONES
        print(f"\n[PHASE 2] Capturing Screen & Matching...")
        
        # We assume standard window position or check running game... 
        # Using pure screen coordinates from config
        
        with mss.mss() as sct:
            for i in range(ZONE_COUNT):
                z_id = i + 1
                zone = next((z for z in sub_zones if z['id'] == z_id), None)
                if not zone: continue

                print(f"\n--- Analyzing ZONE {z_id} ---")
                monitor = {
                    "top": zone['y'], "left": zone['x'], 
                    "width": zone['w'], "height": zone['h']
                }

                # Capture
                raw_screen = np.array(sct.grab(monitor))
                raw_gray = cv2.cvtColor(raw_screen, cv2.COLOR_BGRA2GRAY)
                
                # Save Original
                cv2.imwrite(os.path.join(DEBUG_FOLDER, "zones", f"zone_{z_id}_original.png"), raw_gray)

                # Resize -> Binary
                h, w = raw_gray.shape
                nh, nw = int(h * TURBO_SCALE), int(w * TURBO_SCALE)
                gray_small = cv2.resize(raw_gray, (nw, nh))
                
                _, gray_binary = cv2.threshold(gray_small, BINARY_THRESHOLD_VAL, 255, cv2.THRESH_BINARY)
                
                # Save Binary
                cv2.imwrite(os.path.join(DEBUG_FOLDER, "zones", f"zone_{z_id}_binary.png"), gray_binary)

                # Match
                for t_name, t_img in templates.items():
                    res = cv2.matchTemplate(gray_binary, t_img, cv2.TM_CCOEFF_NORMED)
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
                    
                    status = "FAIL"
                    if max_val > 0.8: status = "SUCCESS"
                    if max_val > 0.9: status = "PERFECT"
                    
                    print(f" Match {t_name.upper():<10}: Score {max_val:.4f}  [{status}]")

        print("\n" + "="*40)
        print("Analysis Complete. Check 'debug_output' folder.")
        print("="*40)
        self.btn.configure(text="Finished! Check Console")

if __name__ == "__main__":
    app = VisionDebugger()
    app.mainloop()
