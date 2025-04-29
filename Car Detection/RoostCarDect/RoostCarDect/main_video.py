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
from all_spots import all_spots  # your master polygon list

# —————————————————————————————————————————————
# CONFIGURATION
# —————————————————————————————————————————————
VIDEO_PATH          = os.path.join(os.path.dirname(__file__), "input_video.mp4")
OUT_VIDEO_PATH      = os.path.join(os.path.dirname(__file__), "output_video.mp4")
MAP_PATH            = os.path.join(os.path.dirname(__file__), "image_spot_map.json")
JSON_KEY_FILE       = os.path.join(os.path.dirname(__file__), "test1roost-0c848c46550d.json")
SPREADSHEET_ID      = "1Kb-Vu3I1DIRUix-8swzzwJcqiEAkBGkW8JaDrD7r4bo"
DETECTION_INTERVAL  = 5   # seconds between detections
# —————————————————————————————————————————————

# 1) Load the video→spot map once
video_key = os.path.splitext(os.path.basename(VIDEO_PATH))[0]
with open(MAP_PATH) as f:
    image_map = json.load(f)
active_ids = image_map.get(video_key, [])
if not active_ids:
    raise RuntimeError(f"No spot mapping found for video '{video_key}' in {MAP_PATH}")

# 2) Filter your master list once
active_spots = [s for s in all_spots if s["id"] in active_ids]
if not active_spots:
    raise RuntimeError(f"No polygons in all_spots.py for IDs {active_ids}")

# 3) Initialize YOLOv5 model (only once)
model = torch.hub.load('ultralytics/yolov5', 'yolov5l', pretrained=True)
model.conf = 0.15   # lower confidence threshold
model.iou  = 0.45   # NMS IoU threshold

# 4) Authenticate Google Sheets (once)
creds = Credentials.from_service_account_file(
    JSON_KEY_FILE,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
sheet = gspread.authorize(creds).open_by_key(SPREADSHEET_ID).sheet1
colA = sheet.col_values(1)  # for exact matching

# 5) Helpers
def intersection_area(poly, box):
    pxmin = max(min(p[0] for p in poly), box[0])
    pymin = max(min(p[1] for p in poly), box[1])
    pxmax = min(max(p[0] for p in poly), box[2])
    pymax = min(max(p[1] for p in poly), box[3])
    if pxmax <= pxmin or pymax <= pymin:
        return 0
    return (pxmax - pxmin) * (pymax - pymin)

# 6) Open video & prepare writer
cap = cv2.VideoCapture(VIDEO_PATH)
if not cap.isOpened():
    raise RuntimeError(f"Could not open video '{VIDEO_PATH}'")

width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps    = cap.get(cv2.CAP_PROP_FPS) or 30.0

# Calculate display delay (ms) to match video FPS
delay = int(1000 / fps)

# Calculate how many frames between detections
frames_between    = int(fps * DETECTION_INTERVAL)
prev_spot_status  = None

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out    = cv2.VideoWriter(OUT_VIDEO_PATH, fourcc, fps, (width, height))

# Create a resizable window for live preview
cv2.namedWindow("Annotated Video", cv2.WINDOW_NORMAL)

frame_idx = 0
while True:
    ret, frame = cap.read()
    if not ret:
        break
    frame_idx += 1
    print(f"\n=== Frame {frame_idx} ===")

    # Decide whether to run a fresh detection
    do_detect = (prev_spot_status is None) or ((frame_idx - 1) % frames_between == 0)

    if do_detect:
        # 6a) Manual TTA: original + 180° rotation

        # -- original frame inference
        rgb1  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res1  = model(rgb1, size=1280)
        d1    = res1.pandas().xyxy[0]

        # -- 180° rotated inference
        rot180 = cv2.rotate(frame, cv2.ROTATE_180)
        rgb2   = cv2.cvtColor(rot180, cv2.COLOR_BGR2RGB)
        res2   = model(rgb2, size=1280)
        d2     = res2.pandas().xyxy[0]

        # map rotated detections back to original coords
        mapped = []
        for _, r in d2.iterrows():
            mapped.append({
                "xmin": width  - r.xmax,
                "ymin": height - r.ymax,
                "xmax": width  - r.xmin,
                "ymax": height - r.ymin,
                "confidence": r.confidence,
                "name": r.name
            })
        d2m = pd.DataFrame(mapped)

        # combine and run NMS
        all_dets = pd.concat([d1, d2m], ignore_index=True)
        boxes    = torch.tensor(all_dets[["xmin","ymin","xmax","ymax"]].values)
        scores   = torch.tensor(all_dets.confidence.values)
        keep     = nms(boxes, scores, iou_threshold=model.iou)
        dets     = all_dets.iloc[keep].reset_index(drop=True)

        # 6b) Compute occupancy per spot
        spot_status = []
        for spot in active_spots:
            occ = 0
            poly = spot["polygon"]
            for _, r in dets.iterrows():
                if r["name"] in ("car", "truck"):
                    xmin, ymin, xmax, ymax = r.xmin, r.ymin, r.xmax, r.ymax
                    box_area = (xmax - xmin) * (ymax - ymin)
                    if box_area <= 0:
                        continue
                    ov = intersection_area(poly, (xmin, ymin, xmax, ymax))
                    if (ov / box_area) > 0.30:
                        occ = 1
                        break
            spot_status.append((spot["id"], occ))
        print("  Detected statuses:", spot_status)

        # 6c) Update Google Sheets
        for sid, occ in spot_status:
            sid_str = str(sid)
            try:
                row = colA.index(sid_str) + 1
                sheet.update_cell(row, 2, occ)
            except ValueError:
                print(f"    • Spot {sid} not in column A—skipping")
            except Exception as e:
                print(f"    ! Error updating spot {sid}: {e}")

        prev_spot_status = spot_status
    else:
        # reuse last-known results
        spot_status = prev_spot_status

    # 6d) Draw overlay on every frame
    annot = frame.copy()
    for sid, occ in spot_status:
        poly  = next(s["polygon"] for s in active_spots if s["id"] == sid)
        pts   = np.array(poly, np.int32).reshape((-1,1,2))
        color = (0,0,255) if occ else (0,255,0)
        cv2.polylines(annot, [pts], True, color, 2)
        M = cv2.moments(pts)
        if M["m00"] != 0:
            cx = int(M["m10"]/M["m00"])
            cy = int(M["m01"]/M["m00"])
            cv2.putText(
                annot, str(sid),
                (cx-10, cy+5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2
            )

    # 6e) Write & show
    out.write(annot)
    cv2.imshow("Annotated Video", annot)
    if cv2.waitKey(delay) & 0xFF == ord('q'):
        break

    time.sleep(0.02)  # small throttle if desired

# 7) Cleanup
cap.release()
out.release()
cv2.destroyAllWindows()
print(f"Finished! Output video at {OUT_VIDEO_PATH}")
