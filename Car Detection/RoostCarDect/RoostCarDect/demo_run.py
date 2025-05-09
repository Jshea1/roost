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
YOLO_CONF_THRESH = 0.10
YOLO_IOU_THRESH  = 0.45
DETECTION_INTERVAL = 5     # seconds between detections in video
IMAGE_PAUSE      = 1000    # ms to display each image
CYCLE_PAUSE      = 8.0     # seconds after each full cycle
# Path to your logo to display during rest
LOGO_PATH        = os.path.join(os.path.dirname(__file__), 'roost_icon.png')
# Path to Haar cascade for face detection
FACE_CASCADE_XML = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'

# —————————————————————————————————————————————
# INITIALIZATION
# —————————————————————————————————————————————
def fix_winding(poly):
    arr = np.array(poly, np.int32)
    hull = cv2.convexHull(arr)
    return hull.reshape(-1, 2).tolist()

with open(IMAGE_MAP_PATH) as f:
    image_map = json.load(f)
with open(VIDEO_MAP_PATH) as f:
    video_map = json.load(f)
for spot in video_spots_list:
    spot["polygon"] = fix_winding(spot["polygon"])
for spot in image_spots_list:
    spot["polygon"] = fix_winding(spot["polygon"])

model = torch.hub.load('ultralytics/yolov5', YOLO_MODEL, pretrained=True)
model.conf = YOLO_CONF_THRESH
model.iou  = YOLO_IOU_THRESH
creds = Credentials.from_service_account_file(
    JSON_KEY_FILE,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
sheet = gspread.authorize(creds).open_by_key(SPREADSHEET_ID).sheet1
colA  = sheet.col_values(1)

# Load logo and face detector
logo = cv2.imread(LOGO_PATH)
if logo is None:
    raise FileNotFoundError(f"Logo not found at {LOGO_PATH}")
face_cascade = cv2.CascadeClassifier(FACE_CASCADE_XML)

# Create resizable window
WINDOW_NAME = "Annotated Demo"
cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)

# —————————————————————————————————————————————
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

# Redact faces by blurring
def redact_faces(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # scaleFactor 1.1 → 1.05, minNeighbors 5 → 3
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=3)
    for (x,y,w,h) in faces:
        roi = img[y:y+h, x:x+w]
        blur = cv2.GaussianBlur(roi, (99,99), 30)
        img[y:y+h, x:x+w] = blur
    return img


# Redact entire people by blurring using YOLO person detection
def redact_people(img):
    # temporarily lower the confidence & enable TTA
    old_conf = model.conf
    model.conf = 0.05
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = model(rgb, size=1280, augment=True)
    # restore your normal threshold
    model.conf = old_conf

    df = results.pandas().xyxy[0]
    for _, r in df.iterrows():
        if r['name'] == 'person':
            x1, y1, x2, y2 = map(int, (r.xmin, r.ymin, r.xmax, r.ymax))
            roi = img[y1:y2, x1:x2]
            blur = cv2.GaussianBlur(roi, (99,99), 30)
            img[y1:y2, x1:x2] = blur
    return img


# Draw overlay for frame & statuses and redact faces + people
def show_overlay(frame, statuses, spots):
    # apply people blur first, then face blur for any missed areas
    redacted = redact_people(frame.copy())
    redacted = redact_faces(redacted)
    annot = redacted.copy()
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


# —————————————————————————————————————————————
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

# —————————————————————————————————————————————
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
    # split spots
    top_spots = [s for s in all_spots if np.mean([p[1] for p in s['polygon']])<height/2]
    bottom_spots = [s for s in all_spots if s not in top_spots]
    rotated = []
    for s in bottom_spots:
        rp=[(width-x, height-y) for x,y in s['polygon']]
        rp.reverse()
        rotated.append({'id':s['id'],'polygon':rp})
    idx=0; prev_status=None
    while True:
        ret, frame = cap.read()
        if not ret: break
        idx += 1
        if prev_status is None or idx % frames_between == 0:
            # top detection
            rgb1 = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            d1 = model(rgb1,size=1280).pandas().xyxy[0]
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
            # bottom detection
            rot = cv2.rotate(frame, cv2.ROTATE_180)
            rgb2 = cv2.cvtColor(rot, cv2.COLOR_BGR2RGB)
            d2 = model(rgb2,size=1280).pandas().xyxy[0]
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
            prev_status = statuses
        else:
            statuses = prev_status
        show_overlay(frame, statuses, all_spots)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()

# —————————————————————————————————————————————
# RANDOMIZE ALL SPOTS (show logo during rest)
# —————————————————————————————————————————————
def randomize_sheet():
    statuses=[]
    for sid_str in colA:
        if sid_str.isdigit():
            statuses.append((int(sid_str), random.choice([0,1])))
    batch_update_sheet(statuses)
    # show logo instead of blank
    cv2.imshow(WINDOW_NAME, logo)
    cv2.waitKey(IMAGE_PAUSE)

# —————————————————————————————————————————————
# MAIN LOOP
# —————————————————————————————————————————————
if __name__=='__main__':
    imgs = sorted(glob.glob(os.path.join(IMAGE_TEST_DIR,'*.png')))
    vids = sorted(glob.glob(os.path.join(VIDEO_TEST_DIR,'*.mp4')))
    print('=== DEMO RUNNER ===')
    while True:
        print('-- Offline Images --')
        for img in imgs:
            process_image(img)
        print('-- Offline Videos --')
        for vid in vids:
            process_video(vid)
        print('-- Randomize & Rest --')
        randomize_sheet()
        print(f'Sleeping {CYCLE_PAUSE}s...')
        time.sleep(CYCLE_PAUSE)
    cv2.destroyAllWindows()
