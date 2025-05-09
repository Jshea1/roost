import os
import glob
import time
import random
import json
import cv2
import torch
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import numpy as np

# —————————————————————————————————————————————
# CONFIGURATION
# —————————————————————————————————————————————
IMAGE_TEST_DIR   = os.path.join(os.path.dirname(__file__), "Annotations", "test_img")
VIDEO_TEST_DIR   = os.path.join(os.path.dirname(__file__), "Annotations", "test_vid")
IMAGE_MAP_PATH   = os.path.join(os.path.dirname(__file__), "image_spot_map.json")
VIDEO_MAP_PATH   = os.path.join(os.path.dirname(__file__), "video_spot_map.json")
from all_spots_images import all_spots as image_spots_list
from all_spots_videos import all_spots as video_spots_list
JSON_KEY_FILE    = os.path.join(os.path.dirname(__file__), "test1roost-0c848c46550d.json")
SPREADSHEET_ID   = "1Kb-Vu3I1DIRUix-8swzzwJcqiEAkBGkW8JaDrD7r4bo"
YOLO_MODEL       = 'yolov5l'
YOLO_CONF_THRESH = 0.15
YOLO_IOU_THRESH  = 0.45
DETECTION_INTERVAL = 5     # seconds between detections in video
IMAGE_PAUSE      = 1000    # ms to display each image
CYCLE_PAUSE      = 5.0     # seconds after each full cycle
# —————————————————————————————————————————————

# INITIALIZATION
# —————————————————————————————————————————————
with open(IMAGE_MAP_PATH) as f:
    image_map = json.load(f)
with open(VIDEO_MAP_PATH) as f:
    video_map = json.load(f)

model = torch.hub.load('ultralytics/yolov5', YOLO_MODEL, pretrained=True)
model.conf = YOLO_CONF_THRESH
model.iou  = YOLO_IOU_THRESH

creds = Credentials.from_service_account_file(
    JSON_KEY_FILE,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
sheet = gspread.authorize(creds).open_by_key(SPREADSHEET_ID).sheet1
colA  = sheet.col_values(1)

# Create resizable window
WINDOW_NAME = "Annotated Demo"
cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)

# HELPERS
# —————————————————————————————————————————————
def intersection_area(poly, box):
    pxmin = max(min(p[0] for p in poly), box[0])
    pymin = max(min(p[1] for p in poly), box[1])
    pxmax = min(max(p[0] for p in poly), box[2])
    pymax = min(max(p[1] for p in poly), box[3])
    if pxmax <= pxmin or pymax <= pymin:
        return 0
    return (pxmax - pxmin) * (pymax - pymin)

# Batch update to avoid rate limits
def batch_update_sheet(statuses):
    updates = []
    for sid, occ in statuses:
        try:
            row = colA.index(str(sid)) + 1
        except ValueError:
            continue
        updates.append({
            "range": f"Sheet1!B{row}",
            "values": [[occ]]
        })
    if updates:
        body = {"valueInputOption": "USER_ENTERED", "data": updates}
        sheet.spreadsheet.values_batch_update(body)

# Draw overlay for frame & statuses
def show_overlay(frame, statuses, spots):
    annot = frame.copy()
    for sid, occ in statuses:
        poly = next((s['polygon'] for s in spots if s['id']==sid), None)
        if not poly:
            continue
        pts = np.array(poly, np.int32).reshape((-1,1,2))
        color = (0,0,255) if occ else (0,255,0)
        cv2.polylines(annot, [pts], True, color, 2)
        M = cv2.moments(pts)
        if M['m00']:
            cx = int(M['m10']/M['m00']); cy = int(M['m01']/M['m00'])
            cv2.putText(annot, str(sid), (cx-10, cy+5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    cv2.imshow(WINDOW_NAME, annot)

# PROCESS_IMAGE
# —————————————————————————————————————————————
def process_image(path):
    key = os.path.splitext(os.path.basename(path))[0]
    ids = image_map.get(key, [])
    spots = [s for s in image_spots_list if s['id'] in ids]
    frame = cv2.imread(path)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    dets = model(rgb, size=1280).pandas().xyxy[0]
    statuses = []
    for s in spots:
        occ = 0
        for _,r in dets.iterrows():
            if r['name'] in ('car','truck'):
                box=(r.xmin,r.ymin,r.xmax,r.ymax)
                area=(r.xmax-r.xmin)*(r.ymax-r.ymin)
                if area>0 and intersection_area(s['polygon'],box)/area>0.3:
                    occ=1; break
        statuses.append((s['id'],occ))
    batch_update_sheet(statuses)
    show_overlay(frame, statuses, spots)
    cv2.waitKey(IMAGE_PAUSE)

# PROCESS_VIDEO with top/bottom split
# —————————————————————————————————————————————
def process_video(path):
    key = os.path.splitext(os.path.basename(path))[0]
    ids = video_map.get(key, [])
    all_spots = [s for s in video_spots_list if s['id'] in ids]
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        return
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frames_between = int(fps * DETECTION_INTERVAL)

    # split top & bottom
    top_spots    = [s for s in all_spots if np.mean([p[1] for p in s['polygon']])<height/2]
    bottom_spots = [s for s in all_spots if s not in top_spots]
    # precompute rotated bottom
    rotated = []
    for s in bottom_spots:
        rp=[(width-x, height-y) for x,y in s['polygon']]
        rp.reverse()
        rotated.append({'id':s['id'],'polygon':rp})

    idx=0; prev_status=None
    while True:
        ret,frame = cap.read()
        if not ret: break
        idx+=1
        if prev_status is None or idx%frames_between==0:
            # detect top
            rgb1=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
            d1=model(rgb1,size=1280).pandas().xyxy[0]
            top_status=[]
            for s in top_spots:
                occ=0
                for _,r in d1.iterrows():
                    if r['name'] in ('car','truck'):
                        box=(r.xmin,r.ymin,r.xmax,r.ymax)
                        area=(r.xmax-r.xmin)*(r.ymax-r.ymin)
                        if area>0 and intersection_area(s['polygon'],box)/area>0.3:
                            occ=1; break
                top_status.append((s['id'],occ))
            # detect bottom on rotated
            rot=cv2.rotate(frame,cv2.ROTATE_180)
            rgb2=cv2.cvtColor(rot,cv2.COLOR_BGR2RGB)
            d2=model(rgb2,size=1280).pandas().xyxy[0]
            bot_status=[]
            for s in rotated:
                occ=0
                for _,r in d2.iterrows():
                    if r['name'] in ('car','truck'):
                        box=(r.xmin,r.ymin,r.xmax,r.ymax)
                        area=(r.xmax-r.xmin)*(r.ymax-r.ymin)
                        if area>0 and intersection_area(s['polygon'],box)/area>0.3:
                            occ=1; break
                bot_status.append((s['id'],occ))
            statuses = top_status + bot_status
            batch_update_sheet(statuses)
            prev_status=statuses
        else:
            statuses = prev_status
        # draw on original
        show_overlay(frame, statuses, all_spots)
        if cv2.waitKey(1)&0xFF==ord('q'):
            break
    cap.release()

# RANDOMIZE ALL SPOTS
# —————————————————————————————————————————————
def randomize_sheet():
    statuses=[]
    for sid_str in colA:
        if sid_str.isdigit():
            sid=int(sid_str)
            statuses.append((sid,random.choice([0,1])))
    batch_update_sheet(statuses)
    blank=np.zeros((480,640,3),dtype=np.uint8)
    show_overlay(blank,statuses,image_spots_list+video_spots_list)
    cv2.waitKey(IMAGE_PAUSE)

# MAIN LOOP
# —————————————————————————————————————————————
if __name__=='__main__':
    imgs=sorted(glob.glob(os.path.join(IMAGE_TEST_DIR,'*.png')))
    vids=sorted(glob.glob(os.path.join(VIDEO_TEST_DIR,'*.mp4')))
    print('=== DEMO RUNNER ===')
    while True:
        print('-- Images --')
        for img in imgs:
            process_image(img)
        print('-- Videos --')
        for vid in vids:
            process_video(vid)
        print('-- Randomize --')
        randomize_sheet()
        print(f'Sleep {CYCLE_PAUSE}s')
        time.sleep(CYCLE_PAUSE)
    cv2.destroyAllWindows()
