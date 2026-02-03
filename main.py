import cv2
import numpy as np
import mss
import time
import json
import os
import pydirectinput
import keyboard
import logging
import re

# --- CONFIGURATION (SYNC WITH modern_bot.py) ---
CONFIG_FILE = 'final_zones.json'
TEMPLATE_FOLDER = 'mau_vat'
MATCH_THRESHOLD = 0.80
BINARY_THRESHOLD_VAL = 175
TURBO_SCALE = 0.5
ZONE_COUNT = 5

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SimpleFisher:
    def __init__(self):
        self.config = self.load_config()
        self.templates = self.load_templates()
        self.running = True

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
             print(f"Error: {CONFIG_FILE} not found!")
             return {}
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_templates(self):
        """Load -> Grayscale -> Resize 50% -> Binary Threshold 175"""
        templates = {}
        if not os.path.exists(TEMPLATE_FOLDER):
            print(f"Error: {TEMPLATE_FOLDER} missing!")
            return {}

        for f in os.listdir(TEMPLATE_FOLDER):
            if f.lower().endswith('.png'):
                name = os.path.splitext(f)[0]
                path = os.path.join(TEMPLATE_FOLDER, f)
                img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                
                if img is not None:
                    # 1. Resize 50%
                    h, w = img.shape
                    new_h, new_w = int(h * TURBO_SCALE), int(w * TURBO_SCALE)
                    img_small = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                    
                    # 2. Binary Threshold 175
                    _, img_binary = cv2.threshold(img_small, BINARY_THRESHOLD_VAL, 255, cv2.THRESH_BINARY)
                    
                    templates[name] = img_binary
                    logging.info(f"Loaded Template: {name}")
        return templates

    def scan_spam_solve(self):
        """Continuous Scan for Max 180s"""
        logging.info(">>> SPAM SCANNING (Max 180s) <<<")
        start_time = time.time()
        found_arrows = [None] * ZONE_COUNT
        
        while time.time() - start_time < 180:
            for i in range(ZONE_COUNT):
                if found_arrows[i]: continue

                z_id = i + 1
                sub_zones = self.config.get('sub_zones', [])
                zone = next((z for z in sub_zones if z['id'] == z_id), None)
                if not zone: continue

                monitor = {
                    "top": zone['y'], "left": zone['x'], 
                    "width": zone['w'], "height": zone['h']
                }

                try:
                    with mss.mss() as sct:
                        # Capture -> Gray
                        img = np.array(sct.grab(monitor))
                        gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)

                        # 1. Resize 50%
                        h, w = gray.shape
                        nh, nw = int(h * TURBO_SCALE), int(w * TURBO_SCALE)
                        gray_small = cv2.resize(gray, (nw, nh), interpolation=cv2.INTER_LINEAR)

                        # 2. Binary 175
                        _, binary = cv2.threshold(gray_small, BINARY_THRESHOLD_VAL, 255, cv2.THRESH_BINARY)

                        # Match
                        best_score = 0
                        best_name = None
                        
                        for name, tmpl in self.templates.items():
                            # Using CCORR per latest fix
                            res = cv2.matchTemplate(binary, tmpl, cv2.TM_CCORR_NORMED)
                            _, max_val, _, _ = cv2.minMaxLoc(res)
                            if max_val > best_score:
                                best_score = max_val
                                best_name = name
                        
                        if best_score > MATCH_THRESHOLD:
                            found_arrows[i] = best_name
                except Exception as e:
                    print(e)
            
            if all(found_arrows):
                return found_arrows
            
            time.sleep(0.01)
        
        return None # Timeout

    def run(self):
        print("Simple Fisher Running (Spam Mode)... Press 'q' to quit.")
        cast_key = str(self.config.get('cast_key', '1'))
        
        while not keyboard.is_pressed('q'):
            # 1. Cast
            logging.info("[1] Casting...")
            pydirectinput.press(cast_key)
            time.sleep(2.0)

            # 2. Spam Scan (Replaces Sentinel)
            logging.info("[2] Scanning...")
            results = self.scan_spam_solve()
            
            if results and all(results):
                logging.info(f"SUCCESS: {results}")
                for raw_key in results:
                    key = re.sub(r'\d+', '', raw_key).lower()
                    logging.info(f"Pressing: {key}")
                    pydirectinput.keyDown(key)
                    time.sleep(0.15)
                    pydirectinput.keyUp(key)
                    time.sleep(0.1)
            else:
                logging.info("TIMEOUT: Arrows missed.")

            # 3. Cooldown
            logging.info("[3] Cooldown 5s...")
            time.sleep(5)

if __name__ == "__main__":
    if not os.path.exists(CONFIG_FILE):
        print("Please run modern_bot.py first to generate config or ensure files exist.")
    else:
        bot = SimpleFisher()
        bot.run()