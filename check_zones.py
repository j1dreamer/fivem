import json
import pygetwindow as gw
import mss
import cv2
import numpy as np
import time

# Load cấu hình
with open('final_zones.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

print("--- ĐANG TÌM CỬA SỔ GAME ---")
# Tìm cửa sổ có tên chứa từ khóa (ví dụ "YouTube" hoặc tên đầy đủ)
# Bạn có thể sửa từ khóa dưới đây cho ngắn gọn nếu cần
target_keyword = "FiveM® by Cfx.re - LUQUY Roleplay" 
windows = gw.getWindowsWithTitle(target_keyword)

if not windows:
    print(f"Không tìm thấy cửa sổ nào chứa tên '{target_keyword}'")
    exit()

win = windows[0]
if win.isMinimized:
    win.restore()
try:
    win.activate()
except:
    pass

print(f"Đã tìm thấy: {win.title}")
print(f"Vị trí: {win.left}, {win.top}")
time.sleep(1) # Chờ cửa sổ ổn định

# Bắt đầu chụp và vẽ demo
with mss.mss() as sct:
    while True:
        # 1. Tính toán vùng chụp TOÀN MÀN HÌNH (để vẽ lên cho dễ nhìn)
        # Hoặc chụp đúng vùng Main Zone để xử lý
        
        # Ở đây mình chụp 1 tấm ảnh to bao trùm tất cả để vẽ demo vị trí
        main_z = config['main_zone']
        
        # Tọa độ thực trên màn hình = Tọa độ cửa sổ + Tọa độ Relative
        real_x = win.left + main_z['x']
        real_y = win.top + main_z['y']
        
        # Mở rộng vùng chụp ra một chút để nhìn bao quát (padding 50px)
        monitor = {
            "top": real_y - 20, 
            "left": real_x - 20, 
            "width": main_z['w'] + 100, 
            "height": main_z['h'] + 50
        }
        
        # Lấy ảnh màn hình
        sct_img = sct.grab(monitor)
        img = np.array(sct_img)
        
        # --- VẼ KHUNG MAIN ZONE (Màu Xanh Lá) ---
        # Do ảnh chụp đã bị crop theo monitor, nên tọa độ vẽ phải trừ đi monitor['left']
        cv2.rectangle(img, 
                      (20, 20), # Bắt đầu tại 20,20 do nãy mình padding 20
                      (20 + main_z['w'], 20 + main_z['h']), 
                      (0, 255, 0), 2) # Green
        
        # --- VẼ 5 Ô NHỎ (Màu Đỏ) ---
        for sub in config['sub_zones']:
            # Tính tọa độ tương đối trong tấm ảnh vừa cắt
            # Tọa độ tuyệt đối của sub = win.left + sub['x']
            # Tọa độ trong ảnh = (win.left + sub['x']) - monitor['left']
            
            sub_real_x = (win.left + sub['x']) - monitor['left']
            sub_real_y = (win.top + sub['y']) - monitor['top']
            
            cv2.rectangle(img,
                          (sub_real_x, sub_real_y),
                          (sub_real_x + sub['w'], sub_real_y + sub['h']),
                          (0, 0, 255), 1) # Red
            
            # Viết số 1, 2, 3, 4, 5
            cv2.putText(img, str(sub['id']), (sub_real_x, sub_real_y - 5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        # Hiển thị
        cv2.imshow("Kiem tra Zone (Nhan 'q' de thoat)", img)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cv2.destroyAllWindows()