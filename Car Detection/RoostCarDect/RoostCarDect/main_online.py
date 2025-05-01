import os
import time
import cv2
import torch
import numpy as np
import pandas as pd
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

# Which spot IDs to monitor
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
        x1,y1 = poly[i]
        x2,y2 = poly[(i+1)%n]
        if ((y1>py) != (y2>py)) and (px < (x2-x1)*(py-y1)/(y2-y1)+x1):
            inside = not inside
    return inside

# Open the RTSP stream
cap = cv2.VideoCapture(RTSP_URL)
if not cap.isOpened():
    raise RuntimeError("Could not open RTSP stream")

# Grab frame size + set up window
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
cv2.namedWindow("Live Parking Monitor", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Live Parking Monitor", w, h)

# 1) Split into top-half vs bottom-half spots
top_spots    = []
bottom_spots = []
for s in active_spots:
    ys = [p[1] for p in s["polygon"]]
    if np.mean(ys) < h/2:
        top_spots.append(s)
    else:
        bottom_spots.append(s)

# 2) Precompute rotated versions of bottom-half polygons
rotated_spots = []
for s in bottom_spots:
    rp = [(w - x, h - y) for x, y in s["polygon"]]
    rp.reverse()  # maintain winding order
    rotated_spots.append({"id": s["id"], "polygon": rp})

last_update     = 0.0
last_top_status = [(s["id"],0) for s in top_spots]
last_bot_status = [(s["id"],0) for s in bottom_spots]
last_detections = None

while True:
    ret, frame = cap.read()
    if not ret:
        time.sleep(0.1)
        continue

    now = time.time()
    display = frame.copy()

    if now - last_update >= UPDATE_INTERVAL:
        # --- detect top-half spots on the normal frame ---
        rgb1 = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        d1   = model(rgb1, size=1280).pandas().xyxy[0]

        top_status = []
        for spot in top_spots:
            occ = 0
            for _, r in d1.iterrows():
                if r["name"] in ("car","truck"):
                    cx = 0.5*(r.xmin + r.xmax)
                    cy = 0.5*(r.ymin + r.ymax)
                    if is_point_in_polygon(cx, cy, spot["polygon"]):
                        occ = 1; break
                    for px,py in [(r.xmin,r.ymin),(r.xmin,r.ymax),
                                  (r.xmax,r.ymin),(r.xmax,r.ymax)]:
                        if is_point_in_polygon(px, py, spot["polygon"]):
                            occ = 1; break
                    if occ: break
            top_status.append((spot["id"], occ))

        # --- detect bottom-half spots on the 180°-rotated frame ---
        rot180 = cv2.rotate(frame, cv2.ROTATE_180)
        rgb2   = cv2.cvtColor(rot180, cv2.COLOR_BGR2RGB)
        d2     = model(rgb2, size=1280).pandas().xyxy[0]

        bot_status = []
        for spot in rotated_spots:
            occ = 0
            for _, r in d2.iterrows():
                if r["name"] in ("car","truck"):
                    cx = 0.5*(r.xmin + r.xmax)
                    cy = 0.5*(r.ymin + r.ymax)
                    if is_point_in_polygon(cx, cy, spot["polygon"]):
                        occ = 1; break
                    for px,py in [(r.xmin,r.ymin),(r.xmin,r.ymax),
                                  (r.xmax,r.ymin),(r.xmax,r.ymax)]:
                        if is_point_in_polygon(px, py, spot["polygon"]):
                            occ = 1; break
                    if occ: break
            bot_status.append((spot["id"], occ))

        # map bottom statuses back to original bottom_spots order
        last_top_status = top_status
        last_bot_status = bot_status
        last_detections = pd.concat([d1,
            pd.DataFrame([{
                "xmin": w-r.xmax, "ymin": h-r.ymax,
                "xmax": w-r.xmin, "ymax": h-r.ymin,
                "confidence": r.confidence, "name": r.name
            } for _,r in d2.iterrows()])],
            ignore_index=True
        )
        # update sheet with merged statuses
        for sid, occ in top_status + bot_status:
            try:
                row = colA.index(str(sid)) + 1
                sheet.update_cell(row, 2, occ)
            except:
                pass

        last_update = now

    # — draw top-half overlays —
    for sid, occ in last_top_status:
        poly = next(s["polygon"] for s in top_spots if s["id"]==sid)
        pts  = np.array(poly, np.int32).reshape((-1,1,2))
        col  = (0,0,255) if occ else (0,255,0)
        cv2.polylines(display, [pts], True, col, 2)
        M = cv2.moments(pts)
        if M["m00"] != 0:
            cx = int(M["m10"]/M["m00"]); cy=int(M["m01"]/M["m00"])
            cv2.putText(display, str(sid), (cx-10,cy+5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, col, 2)

    # — draw bottom-half overlays (original coords) —
    for sid, occ in last_bot_status:
        poly = next(s["polygon"] for s in bottom_spots if s["id"]==sid)
        pts  = np.array(poly, np.int32).reshape((-1,1,2))
        col  = (0,0,255) if occ else (0,255,0)
        cv2.polylines(display, [pts], True, col, 2)
        M = cv2.moments(pts)
        if M["m00"] != 0:
            cx = int(M["m10"]/M["m00"]); cy=int(M["m01"]/M["m00"])
            cv2.putText(display, str(sid), (cx-10,cy+5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, col, 2)

    # — draw detection centers —
    if last_detections is not None:
        for _, r in last_detections.iterrows():
            cx = int(0.5*(r.xmin + r.xmax))
            cy = int(0.5*(r.ymin + r.ymax))
            cv2.circle(display, (cx, cy), 3, (0,255,255), -1)

    cv2.imshow("Live Parking Monitor", display)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
