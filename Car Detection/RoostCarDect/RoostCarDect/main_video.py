import os
import cv2
import json
import time
import torch
import numpy as np
import pandas as pd
import gspread
from torchvision.ops import nms
from google.oauth2.service_account import Credentials
from all_spots import all_spots  # master polygon list

# —————————————————————————————————————————————
# CONFIGURATION
# —————————————————————————————————————————————
VIDEO_PATH         = os.path.join(os.path.dirname(__file__), "input_video3.mp4")
OUT_VIDEO_PATH     = os.path.join(os.path.dirname(__file__), "output_video3.mp4")
MAP_PATH           = os.path.join(os.path.dirname(__file__), "image_spot_map.json")
JSON_KEY_FILE      = os.path.join(os.path.dirname(__file__), "test1roost-0c848c46550d.json")
SPREADSHEET_ID     = "1Kb-Vu3I1DIRUix-8swzzwJcqiEAkBGkW8JaDrD7r4bo"
DETECTION_INTERVAL = 5  # seconds between re-runs of YOLO
# —————————————————————————————————————————————

# 1) Load video→spot map
video_key = os.path.splitext(os.path.basename(VIDEO_PATH))[0]
with open(MAP_PATH) as f:
    image_map = json.load(f)
active_ids = image_map.get(video_key, [])
if not active_ids:
    raise RuntimeError(f"No spot mapping for '{video_key}' in {MAP_PATH}")

# 2) Filter your master list once
active_spots = [s for s in all_spots if s["id"] in active_ids]
if not active_spots:
    raise RuntimeError(f"No polygons in all_spots.py for IDs {active_ids}")

# 3) Initialize YOLOv5
model = torch.hub.load('ultralytics/yolov5', 'yolov5l', pretrained=True)
model.conf = 0.15
model.iou  = 0.45

# 4) Authenticate Google Sheets
creds = Credentials.from_service_account_file(
    JSON_KEY_FILE,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
sheet = gspread.authorize(creds).open_by_key(SPREADSHEET_ID).sheet1
colA  = sheet.col_values(1)

# 5) Helper: area of overlap
def intersection_area(poly, box):
    pxmin = max(min(p[0] for p in poly), box[0])
    pymin = max(min(p[1] for p in poly), box[1])
    pxmax = min(max(p[0] for p in poly), box[2])
    pymax = min(max(p[1] for p in poly), box[3])
    if pxmax <= pxmin or pymax <= pymin:
        return 0
    return (pxmax-pxmin)*(pymax-pymin)

# 6) Open video & prep writer
cap = cv2.VideoCapture(VIDEO_PATH)
if not cap.isOpened():
    raise RuntimeError(f"Could not open {VIDEO_PATH}")

width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps    = cap.get(cv2.CAP_PROP_FPS) or 30.0
delay  = int(1000/fps)
frames_between = int(fps * DETECTION_INTERVAL)
prev_status    = None

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out    = cv2.VideoWriter(OUT_VIDEO_PATH, fourcc, fps, (width, height))
cv2.namedWindow("Annotated Video", cv2.WINDOW_NORMAL)

# 7) Split into top-half vs bottom-half spots
top_spots    = []
bottom_spots = []
for s in active_spots:
    ys = [p[1] for p in s["polygon"]]
    if np.mean(ys) < height/2:
        top_spots.append(s)
    else:
        bottom_spots.append(s)

# 8) Precompute rotated versions of the bottom-half polygons
rotated_spots = []
for s in bottom_spots:
    rot_poly = [(width - x, height - y) for (x, y) in s["polygon"]]
    # reverse order so polylines close correctly
    rot_poly.reverse()
    rotated_spots.append({"id": s["id"], "polygon": rot_poly})

frame_idx = 0
while True:
    ret, frame = cap.read()
    if not ret:
        break
    frame_idx += 1
    print(f"\n=== Frame {frame_idx} ===")

    # only re-run YOLO every DETECTION_INTERVAL seconds
    do_detect = (prev_status is None) or ((frame_idx-1) % frames_between == 0)

    if do_detect:
        # —— 1) detect top half on the normal frame
        rgb1  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        r1    = model(rgb1, size=1280)
        d1    = r1.pandas().xyxy[0]

        top_status = []
        for spot in top_spots:
            occ = 0
            for _, r in d1.iterrows():
                if r["name"] in ("car","truck"):
                    bx = (r.xmin, r.ymin, r.xmax, r.ymax)
                    area = (r.xmax-r.xmin)*(r.ymax-r.ymin)
                    if area>0 and intersection_area(spot["polygon"], bx)/area>0.30:
                        occ = 1
                        break
            top_status.append((spot["id"], occ))

        # —— 2) detect bottom half on the 180° rotated frame
        rot180 = cv2.rotate(frame, cv2.ROTATE_180)
        rgb2   = cv2.cvtColor(rot180, cv2.COLOR_BGR2RGB)
        r2     = model(rgb2, size=1280)
        d2     = r2.pandas().xyxy[0]

        bottom_status = []
        for spot in rotated_spots:
            occ = 0
            for _, r in d2.iterrows():
                if r["name"] in ("car","truck"):
                    bx = (r.xmin, r.ymin, r.xmax, r.ymax)
                    area = (r.xmax-r.xmin)*(r.ymax-r.ymin)
                    if area>0 and intersection_area(spot["polygon"], bx)/area>0.30:
                        occ = 1
                        break
            bottom_status.append((spot["id"], occ))

        # merge and save
        prev_status = top_status + bottom_status

        # --- update Google Sheets with logging ---
        for sid, occ in prev_status:
            sid_str = str(sid)
            try:
                row = colA.index(sid_str) + 1
                sheet.update_cell(row, 2, occ)
                print(f"  • Updated spot {sid} → {occ} (row {row})")
            except ValueError:
                print(f"  • Spot {sid} not found in sheet; skipping")
            except Exception as e:
                print(f"  ! Error updating spot {sid}: {e}")


    else:
        top_status = [s for s in prev_status if s[0] in {sp["id"] for sp in top_spots}]
        bottom_status = [s for s in prev_status if s[0] in {sp["id"] for sp in bottom_spots}]

    # —— draw all overlays onto the _original_ frame
    annot = frame.copy()
    # top half
    for sid, occ in top_status:
        poly  = next(s["polygon"] for s in top_spots if s["id"]==sid)
        pts   = np.array(poly, np.int32).reshape((-1,1,2))
        c     = (0,0,255) if occ else (0,255,0)
        cv2.polylines(annot, [pts], True, c, 2)
        M = cv2.moments(pts)
        if M["m00"]!=0:
            cx = int(M["m10"]/M["m00"]); cy=int(M["m01"]/M["m00"])
            cv2.putText(annot, str(sid), (cx-10,cy+5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, c, 2)

    # bottom half (use the original polygon coords)
    for sid, occ in bottom_status:
        poly  = next(s["polygon"] for s in bottom_spots if s["id"]==sid)
        pts   = np.array(poly, np.int32).reshape((-1,1,2))
        c     = (0,0,255) if occ else (0,255,0)
        cv2.polylines(annot, [pts], True, c, 2)
        M = cv2.moments(pts)
        if M["m00"]!=0:
            cx = int(M["m10"]/M["m00"]); cy=int(M["m01"]/M["m00"])
            cv2.putText(annot, str(sid), (cx-10,cy+5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, c, 2)

    out.write(annot)
    cv2.imshow("Annotated Video", annot)
    if cv2.waitKey(delay) & 0xFF == ord('q'):
        break
    time.sleep(0.02)

cap.release()
out.release()
cv2.destroyAllWindows()
print("Done →", OUT_VIDEO_PATH)
