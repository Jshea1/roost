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
RTSP_URL       = "rtsp://admin:2025@ROOST11@169.254.109.34:681/Streaming/channels/101"
UPDATE_INTERVAL = 5  # seconds between detections & sheet updates

# Google Sheets credentials & ID
JSON_KEY_FILE  = os.path.join(os.path.dirname(__file__), "test1roost-0c848c46550d.json")
SPREADSHEET_ID = "1Kb-Vu3I1DIRUix-8swzzwJcqiEAkBGkW8JaDrD7r4bo"

# Which spots to monitor on the live feed
ACTIVE_IDS = [31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 51]  # <-- replace with the IDs you want live
active_spots = [s for s in all_spots if s["id"] in ACTIVE_IDS]
# —————————————————————————————————————————————

# Load YOLOv5 once
model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
model.conf = 0.15   # lower confidence threshold
model.iou  = 0.45   # NMS IoU threshold

# Authenticate Google Sheets once
creds = Credentials.from_service_account_file(
    JSON_KEY_FILE,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
sheet = gspread.authorize(creds).open_by_key(SPREADSHEET_ID).sheet1
colA = sheet.col_values(1)  # Column A for exact-match lookup

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

# make it resizable and set initial size
cv2.namedWindow("Live Parking Monitor", cv2.WINDOW_NORMAL)
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
cv2.resizeWindow("Live Parking Monitor", w, h)

last_update = 0.0

while True:
    ret, frame = cap.read()
    if not ret:
        print("Stream ended or failed; exiting")
        break

    now = time.time()
    display = frame.copy()

    # Only run heavy detection & sheet updates at interval
    if now - last_update >= UPDATE_INTERVAL:
        # 1) Run YOLOv5 inference at higher resolution
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = model(rgb, size=1280)
        detections = results.pandas().xyxy[0]

        # 2) Compute occupancy: center OR any corner inside polygon
        spot_status = []
        for spot in active_spots:
            occ = 0
            poly = spot["polygon"]
            for _, r in detections.iterrows():
                if r["name"] in ["car", "truck"]:
                    # center test
                    cx = (r.xmin + r.xmax) / 2
                    cy = (r.ymin + r.ymax) / 2
                    if is_point_in_polygon(cx, cy, poly):
                        occ = 1
                    else:
                        # corner tests
                        corners = [
                            (r.xmin, r.ymin),
                            (r.xmin, r.ymax),
                            (r.xmax, r.ymin),
                            (r.xmax, r.ymax),
                        ]
                        for px, py in corners:
                            if is_point_in_polygon(px, py, poly):
                                occ = 1
                                break
                    if occ:
                        break
            spot_status.append((spot["id"], occ))

        print("Live spot statuses:", spot_status)

        # 3) Draw debug overlay
        for sid, occ in spot_status:
            poly = next(s["polygon"] for s in active_spots if s["id"] == sid)
            pts = np.array(poly, np.int32).reshape((-1, 1, 2))
            color = (0, 0, 255) if occ else (0, 255, 0)
            cv2.polylines(display, [pts], True, color, 2)
            # label
            M = cv2.moments(pts)
            if M["m00"] != 0:
                lx = int(M["m10"] / M["m00"])
                ly = int(M["m01"] / M["m00"])
                cv2.putText(display, str(sid), (lx - 10, ly + 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        # draw detection centers
        for _, r in detections.iterrows():
            cx = int((r.xmin + r.xmax) / 2)
            cy = int((r.ymin + r.ymax) / 2)
            cv2.circle(display, (cx, cy), 3, (0, 255, 255), -1)

        # 4) Update Google Sheets
        for sid, occ in spot_status:
            try:
                row = colA.index(str(sid)) + 1
                sheet.update_cell(row, 2, occ)
                print(f"  • Updated spot {sid} → {occ} (row {row})")
            except ValueError:
                print(f"  ! Spot {sid} not found in column A")
            except Exception as e:
                print(f"  ! Error updating spot {sid}: {e}")

        last_update = now

    # Show live annotated feed
    cv2.imshow("Live Parking Monitor", display)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
