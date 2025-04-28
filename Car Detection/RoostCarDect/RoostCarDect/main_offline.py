import os
import glob
import cv2
import json
import time
import torch
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
from all_spots import all_spots  # your master polygon list

# —————————————————————————————————————————————
# CONFIGURATION
# —————————————————————————————————————————————
TEST_FOLDER    = os.path.join(os.path.dirname(__file__), "Annotations", "test_img")
MAP_PATH       = os.path.join(os.path.dirname(__file__), "image_spot_map.json")
JSON_KEY_FILE  = os.path.join(os.path.dirname(__file__), "test1roost-0c848c46550d.json")
SPREADSHEET_ID = "1Kb-Vu3I1DIRUix-8swzzwJcqiEAkBGkW8JaDrD7r4bo"
# —————————————————————————————————————————————

# 1) Load the image→spot map once
with open(MAP_PATH) as f:
    image_map = json.load(f)

# 2) Initialize YOLOv5 model (only once)
model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
model.conf = 0.15   # lower confidence threshold (default 0.25)
model.iou  = 0.45   # NMS IoU threshold (default 0.45) 

# 3) Authenticate Google Sheets (once)
creds = Credentials.from_service_account_file(
    JSON_KEY_FILE,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
sheet = gspread.authorize(creds).open_by_key(SPREADSHEET_ID).sheet1
# Pre-load column A for exact matching
colA = sheet.col_values(1)

# 4) Helper: Point-in-Polygon (ray-casting)
def is_point_in_polygon(px, py, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if ((y1 > py) != (y2 > py)) and (px < (x2 - x1) * (py - y1) / (y2 - y1) + x1):
            inside = not inside
    return inside

# 5) Gather all test images
image_paths = sorted(glob.glob(os.path.join(TEST_FOLDER, "*.png")))
if not image_paths:
    raise RuntimeError(f"No .png files found in {TEST_FOLDER}")

# 6) Process each image in turn
for IMAGE in image_paths:
    image_key = os.path.splitext(os.path.basename(IMAGE))[0]
    print(f"\n=== Processing '{image_key}' ===")

    # 6a) Which spot IDs to test here?
    active_ids = image_map.get(image_key, [])
    if not active_ids:
        print(f"  ! No active spots defined for '{image_key}', skipping.")
        continue

    # 6b) Filter your master list
    active_spots = [s for s in all_spots if s["id"] in active_ids]
    if not active_spots:
        print(f"  ! No polygons in all_spots.py for IDs {active_ids}, skipping.")
        continue

    # 6c) Load the frame
    frame = cv2.imread(IMAGE)
    if frame is None:
        print(f"  ! Could not load image '{IMAGE}', skipping.")
        continue

    # 6d) YOLO inference (lower conf, bigger size)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = model(rgb, size=1280)
    detections = results.pandas().xyxy[0]

    # ── OPTIONAL DEBUG: draw detection centers in yellow ─────────────
    annot = frame.copy()  # ensure annot exists before drawing
    for _, r in detections.iterrows():
        cx = int((r.xmin + r.xmax) / 2)
        cy = int((r.ymin + r.ymax) / 2)
        cv2.circle(annot, (cx, cy), 3, (0, 255, 255), -1)
    # ───────────────────────────────────────────────────────────────────

    # 6e) Compute occupancy by testing center OR any corner inside the spot
    spot_status = []
    for spot in active_spots:
        occ = 0
        poly = spot["polygon"]
        for _, r in detections.iterrows():
            if r["name"] in ["car", "truck"]:
                # 1) center point
                cx, cy = (r.xmin + r.xmax) / 2, (r.ymin + r.ymax) / 2
                if is_point_in_polygon(cx, cy, poly):
                    occ = 1
                else:
                    # 2) corners
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
    print("  Spot statuses:", spot_status)

    # 6f) Visual debug overlay (unchanged, but draws on `annot`)
    for sid, occ in spot_status:
        poly = next(s["polygon"] for s in active_spots if s["id"] == sid)
        pts = np.array(poly, np.int32).reshape((-1,1,2))
        color = (0,0,255) if occ else (0,255,0)
        cv2.polylines(annot, [pts], True, color, 2)
        M = cv2.moments(pts)
        if M["m00"] != 0:
            cx = int(M["m10"]/M["m00"])
            cy = int(M["m01"]/M["m00"])
            cv2.putText(annot, str(sid), (cx-10, cy+5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    cv2.imshow("Annotated", annot)
    cv2.imwrite(f"annotated_final_{image_key}.png", annot)

    # 6g) Update Google Sheets with exact match
    for sid, occ in spot_status:
        sid_str = str(sid)
        try:
            row_to_update = colA.index(sid_str) + 1
            sheet.update_cell(row_to_update, 2, occ)
            print(f"    • Updated spot {sid} → {occ} (row {row_to_update})")
        except ValueError:
            print(f"    ! Spot {sid} not in column A; skipped.")
        except Exception as e:
            print(f"    ! Error updating spot {sid}: {e}")

    time.sleep(0.5)  # small delay before next image

cv2.destroyAllWindows()
