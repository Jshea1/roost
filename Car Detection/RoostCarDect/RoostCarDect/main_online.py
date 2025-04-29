import os
import time
import cv2
import torch
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
from all_spots import all_spots  # your master polygon list

# —————————————————————————————————————————————
# CONFIGURATION
# —————————————————————————————————————————————
RTSP_URL        = "rtsp://admin:2025@ROOST11@169.254.109.34:681/Streaming/channels/101"
UPDATE_INTERVAL = 4   # seconds between heavy work

JSON_KEY_FILE   = os.path.join(os.path.dirname(__file__),
                               "test1roost-0c848c46550d.json")
SPREADSHEET_ID  = "1Kb-Vu3I1DIRUix-8swzzwJcqiEAkBGkW8JaDrD7r4bo"

ACTIVE_IDS      = [62, 64, 66, 65, 63]  
active_spots    = [s for s in all_spots if s["id"] in ACTIVE_IDS]
# —————————————————————————————————————————————

# Load YOLOv5 once
model = torch.hub.load('ultralytics/yolov5', 'yolov5l', pretrained=True)
device = 'cuda' if torch.cuda.is_available() else 'cpu'
model = model.to(device)
model.conf = 0.10
model.iou  = 0.40

# Authenticate Google Sheets once
creds = Credentials.from_service_account_file(
    JSON_KEY_FILE,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
sheet = gspread.authorize(creds).open_by_key(SPREADSHEET_ID).sheet1
colA  = sheet.col_values(1)

# Helper: ray-casting point-in-polygon
def is_point_in_polygon(px, py, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if ((y1 > py) != (y2 > py)) and (px < (x2 - x1)*(py - y1)/(y2 - y1) + x1):
            inside = not inside
    return inside

# Open the RTSP stream
cap = cv2.VideoCapture(RTSP_URL)
if not cap.isOpened():
    raise RuntimeError("Could not open RTSP stream")

cv2.namedWindow("Live Parking Monitor", cv2.WINDOW_NORMAL)
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
cv2.resizeWindow("Live Parking Monitor", w, h)

last_update     = 0.0
last_detections = None        # store detections between updates
spot_status     = [(s["id"], 0) for s in active_spots]

while True:
    ret, frame = cap.read()
    if not ret:
        print("⚠️  Frame decode failed, skipping...")
        time.sleep(0.1)
        continue

    now = time.time()
    display = frame.copy()

    # Only run heavy inference & sheet updates at interval
    if now - last_update >= UPDATE_INTERVAL:
        # YOLO inference
        rgb       = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results   = model(rgb, size=1280)
        dets      = results.pandas().xyxy[0]
        last_detections = dets

        # Compute occupancy
        new_status = []
        for spot in active_spots:
            occ = 0
            poly = spot["polygon"]
            for _, r in dets.iterrows():
                if r["name"] in ["car","truck"]:
                    cx = (r.xmin + r.xmax) / 2
                    cy = (r.ymin + r.ymax) / 2
                    if is_point_in_polygon(cx, cy, poly):
                        occ = 1
                        break
                    # corner test
                    for px, py in [(r.xmin,r.ymin),
                                   (r.xmin,r.ymax),
                                   (r.xmax,r.ymin),
                                   (r.xmax,r.ymax)]:
                        if is_point_in_polygon(px, py, poly):
                            occ = 1
                            break
                    if occ:
                        break
            new_status.append((spot["id"], occ))
        spot_status = new_status
        print("Live spot statuses:", spot_status)

        # Update Google Sheets
        for sid, occ in spot_status:
            try:
                row = colA.index(str(sid)) + 1
                sheet.update_cell(row, 2, occ)
            except ValueError:
                print(f"  ! Spot {sid} not found in column A")
            except Exception as e:
                print(f"  ! Error updating spot {sid}: {e}")

        last_update = now

    # Always draw the latest overlay + centers
    # 1) Stall outlines
    for sid, occ in spot_status:
        poly = next(s["polygon"] for s in active_spots if s["id"] == sid)
        pts  = np.array(poly, np.int32).reshape((-1,1,2))
        color= (0,0,255) if occ else (0,255,0)
        cv2.polylines(display, [pts], True, color, 2)
        M = cv2.moments(pts)
        if M["m00"] != 0:
            lx = int(M["m10"]/M["m00"])
            ly = int(M["m01"]/M["m00"])
            cv2.putText(display, str(sid), (lx-10, ly+5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    # 2) Detection centers (from last inference)
    if last_detections is not None:
        for _, r in last_detections.iterrows():
            cx = int((r.xmin + r.xmax) / 2)
            cy = int((r.ymin + r.ymax) / 2)
            cv2.circle(display, (cx, cy), 3, (0,255,255), -1)

    cv2.imshow("Live Parking Monitor", display)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
