import cv2
import os
import torch
import json
import gspread
import time
from google.oauth2.service_account import Credentials


# Camera Configuration
RTSP_URL = "rtsp://admin:2025@ROOST11@169.254.109.34:681/Streaming/channels/103"  # Replace with actual details
UPDATE_INTERVAL = 5  # Detect vehicles & update Google Sheets every 10 seconds

# Set up paths
script_dir = os.path.dirname(os.path.abspath(__file__))
json_key_path = os.path.join(script_dir, 'test1roost-0c848c46550d.json')

# Load the YOLOv5 model for vehicle detection
model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)

# Google Sheets API Authentication
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(json_key_path, scopes=SCOPES)
client = gspread.authorize(creds)

# Open Google Sheet (assumes Column A has Spot IDs and Column B will store occupancy)
SPREADSHEET_ID = "1Kb-Vu3I1DIRUix-8swzzwJcqiEAkBGkW8JaDrD7r4bo"  # Replace with your spreadsheet ID
sheet = client.open_by_key(SPREADSHEET_ID).sheet1  # Select the first sheet

###############################################################################
# Define all parking spots as polygons.
# Each spot has an "id" and a "polygon": list of (x, y) points.
###############################################################################
all_spots = [
    #test spaces
    {
        "id": 70,
        "name": "Spot 70",
        "polygon": [(600, 400), (680, 400), (680, 480), (600, 480)]
    },
    {
        "id": 72,
        "name": "Spot 72",
        "polygon": [(700, 500), (780, 500), (780, 580), (700, 580)]
    },
]

# Specify which spots are active for the current test.
active_spot_ids = [70, 72]
active_spots = [spot for spot in all_spots if spot["id"] in active_spot_ids]

# Helper Function: Point-In-Polygon (Ray Casting Algorithm)
def is_point_in_polygon(px, py, polygon):
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        intersect = ((y1 > py) != (y2 > py)) and \
                    (px < (x2 - x1) * (py - y1) / (y2 - y1) + x1)
        if intersect:
            inside = not inside
    return inside

# Open RTSP Video Stream
cap = cv2.VideoCapture(RTSP_URL)
if not cap.isOpened():
    print("Error: Could not open video stream")
    exit()

frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
cv2.namedWindow("Vehicle Detection", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Vehicle Detection", frame_width, frame_height)

print(f"Stream resolution: {frame_width}x{frame_height}")
print("Processing video feed... Vehicle detection & Google Sheets updates every 10 seconds. Press 'q' to stop.")

last_update_time = time.time()


# Main Loop
while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    cv2.imshow("Vehicle Detection", frame)

    current_time = time.time()
    if current_time - last_update_time >= UPDATE_INTERVAL:
        print(f"Running YOLOv5 detection after {UPDATE_INTERVAL} seconds.")

        # Resize for YOLOv5 if needed; adjust dimensions as appropriate.
        img_resized = cv2.resize(frame, (2560, 540))
        img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)

        # Run YOLOv5 detection
        results = model(img_rgb)
        detections = results.pandas().xyxy[0]

        # Build occupancy status for active spots: [spot_id, occupancy]
        # occupancy: 0 = empty, 1 = occupied
        spot_status = []
        for spot in active_spots:
            occupied = 0  # Assume spot is empty by default.
            for idx, row in detections.iterrows():
                if row['name'] in ['car', 'truck']:
                    # Compute detection center
                    det_x1 = int(row['xmin'])
                    det_y1 = int(row['ymin'])
                    det_x2 = int(row['xmax'])
                    det_y2 = int(row['ymax'])
                    center_x = (det_x1 + det_x2) // 2
                    center_y = (det_y1 + det_y2) // 2

                    # Check if the detection center falls inside the spot's polygon
                    if is_point_in_polygon(center_x, center_y, spot["polygon"]):
                        occupied = 1
                        break
            spot_status.append([spot["id"], occupied])

        # (Optional) Save detection results to a JSON file for debugging.
        detection_results = {"spot_status": spot_status}
        json_output_path = os.path.join(script_dir, "detection_results.json")
        with open(json_output_path, "w") as json_file:
            json.dump(detection_results, json_file, indent=4)

        print("Active Spot Statuses:", spot_status)

        # Update Google Sheets for only the active spots.
        # Here we assume Column A has the spot IDs and Column B stores occupancy.
        # For each active spot, find its row (by searching Column A) and update Column B.
        for status in spot_status:
            spot_id, occupancy = status
            try:
                # Find the cell in Column A that contains the spot ID (as string)
                cell = sheet.find(str(spot_id))
                if cell:
                    row_to_update = cell.row
                    # Update Column B (occupancy)
                    sheet.update_cell(row_to_update, 2, occupancy)
                    print(f"Updated Spot {spot_id} at row {row_to_update} to occupancy {occupancy}")
            except Exception as e:
                print(f"Error updating spot {spot_id}: {e}")

        last_update_time = current_time

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
