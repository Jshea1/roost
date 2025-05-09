import os
import time
import cv2
import torch
import numpy as np
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from all_spots_images import all_spots  # your master polygon list

# —————————————————————————————————————————————
# CONFIGURATION
# —————————————————————————————————————————————
RTSP_URL        = "rtsp://admin:2025@ROOST11@169.254.109.34:681/Streaming/channels/101"
UPDATE_INTERVAL = 4   # seconds between heavy work
OVERLAP_THRESH  = 0.20  # minimum fraction of bbox overlapping polygon to count as occupied
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

# Helper: area of overlap
#   returns intersection area between polygon and bbox
#   box = (xmin, ymin, xmax, ymax)
def intersection_area(poly, box):
    pxmin = max(min(p[0] for p in poly), box[0])
    pymin = max(min(p[1] for p in poly), box[1])
    pxmax = min(max(p[0] for p in poly), box[2])
    pymax = min(max(p[1] for p in poly), box[3])
    if pxmax <= pxmin or pymax <= pymin:
        return 0
    return (pxmax - pxmin) * (pymax - pymin)

# Helper: ray-casting point-in-polygon (unused now, but available)
def is_point_in_polygon(px, py, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i+1) % n]
        if ((y1 > py) != (y2 > py)) and (px < (x2-x1)*(py-y1)/(y2-y1) + x1):
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
spot_status     = [(s["id"], 0) for s in active_spots]
last_detections = None

while True:
    ret, frame = cap.read()
    if not ret:
        time.sleep(0.1)
        continue

    now = time.time()
    display = frame.copy()

    if now - last_update >= UPDATE_INTERVAL:
        # --- YOLO on original frame ---
        rgb1 = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        d1   = model(rgb1, size=1280).pandas().xyxy[0]

        # --- YOLO on 180° rotated frame ---
        rot180 = cv2.rotate(frame, cv2.ROTATE_180)
        rgb2   = cv2.cvtColor(rot180, cv2.COLOR_BGR2RGB)
        d2     = model(rgb2, size=1280).pandas().xyxy[0]

        # --- map rotated detections back ---
        mapped = []
        for _, r in d2.iterrows():
            mapped.append({
                "xmin": w - r.xmax,
                "ymin": h - r.ymax,
                "xmax": w - r.xmin,
                "ymax": h - r.ymin,
                "confidence": r.confidence,
                "name": r.name
            })
        d2m = pd.DataFrame(mapped)

        # --- combine & NMS ---
        all_dets = pd.concat([d1, d2m], ignore_index=True)
        boxes    = torch.tensor(all_dets[["xmin","ymin","xmax","ymax"]].values)
        scores   = torch.tensor(all_dets.confidence.values)
        from torchvision.ops import nms
        keep     = nms(boxes, scores, iou_threshold=model.iou)
        dets     = all_dets.iloc[keep].reset_index(drop=True)
        last_detections = dets

        # --- occupancy via overlap ---
        new_status = []
        for spot in active_spots:
            occ = 0
            poly = spot["polygon"]
            for _, r in dets.iterrows():
                if r["name"] in ("car","truck"):
                    xmin, ymin, xmax, ymax = r.xmin, r.ymin, r.xmax, r.ymax
                    box_area = (xmax - xmin) * (ymax - ymin)
                    if box_area > 0:
                        ov = intersection_area(poly, (xmin, ymin, xmax, ymax))
                        if (ov / box_area) > OVERLAP_THRESH:
                            occ = 1
                            break
            new_status.append((spot["id"], occ))

        # --- update Google Sheets with logging ---
        for sid, occ in new_status:
            sid_str = str(sid)
            try:
                row = colA.index(sid_str) + 1
                sheet.update_cell(row, 2, occ)
                print(f"  • Updated spot {sid} → {occ} (row {row})")
            except ValueError:
                print(f"  • Spot {sid} not found in sheet; skipping")
            except Exception as e:
                print(f"  ! Error updating spot {sid}: {e}")

        spot_status = new_status
        last_update = now

    # draw overlays
    for sid, occ in spot_status:
        poly  = next(s["polygon"] for s in active_spots if s["id"]==sid)
        pts   = np.array(poly, np.int32).reshape((-1,1,2))
        color = (0,0,255) if occ else (0,255,0)
        cv2.polylines(display, [pts], True, color, 2)
        M = cv2.moments(pts)
        if M["m00"] != 0:
            cx = int(M["m10"]/M["m00"])
            cy = int(M["m01"]/M["m00"])
            cv2.putText(display, str(sid), (cx-10, cy+5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    # draw detection centers
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
