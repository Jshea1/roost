import cv2
import os
import torch
import json
import gspread
import time
from google.oauth2.service_account import Credentials

# Camera Configuration
RTSP_URL = "rtsp://admin:2025@ROOST11@169.254.109.34:681/Streaming/channels/103"  # Replace with actual details
UPDATE_INTERVAL = 10  # Detect vehicles & update Google Sheets every 10 seconds

# Set up paths
script_dir = os.path.dirname(os.path.abspath(__file__))
json_key_path = os.path.join(script_dir, 'test1roost-0c848c46550d.json')

# Load the YOLOv5 model for vehicle detection
model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)

# Google Sheets API Authentication
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(json_key_path, scopes=SCOPES)
client = gspread.authorize(creds)

# Open Google Sheet
SPREADSHEET_ID = "1Kb-Vu3I1DIRUix-8swzzwJcqiEAkBGkW8JaDrD7r4bo"  # Replace with your actual spreadsheet ID
sheet = client.open_by_key(SPREADSHEET_ID).sheet1  # Select the first sheet

# Open RTSP Video Stream
cap = cv2.VideoCapture(RTSP_URL)

if not cap.isOpened():
    print("Error: Could not open video stream")
    exit()

# Get actual video frame width and height
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

print(f"Stream resolution: {frame_width}x{frame_height}")

# Set window properties to allow resizing
cv2.namedWindow("Vehicle Detection", cv2.WINDOW_NORMAL)  # Make window resizable
cv2.resizeWindow("Vehicle Detection", frame_width, frame_height) 

print("Processing video feed at 12 FPS... Vehicle detection & Google Sheets updates every 10 seconds. Press 'q' to stop.")

last_update_time = time.time()
latest_vehicle_count = 0  # Store last detected vehicle count

while True:
    ret, frame = cap.read()
    
    if not ret:
        print("Failed to grab frame")
        break

    cv2.imshow("Vehicle Detection", frame)

    # Check if 10 seconds have passed before running detection
    current_time = time.time()
    if current_time - last_update_time >= UPDATE_INTERVAL:  
        print(f"Running YOLOv5 detection after {UPDATE_INTERVAL} seconds.")

        # Resize for consistent YOLOv5 processing
        img_resized = cv2.resize(frame, (2560, 540))  # Keep this for YOLO

        # Convert to RGB (YOLOv5 expects RGB format)
        img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)

        # Perform inference to detect vehicles
        results = model(img_rgb)
        detections = results.pandas().xyxy[0]  # x_min, y_min, x_max, y_max, confidence, class, name

        # Count the number of vehicles detected (cars and trucks)
        latest_vehicle_count = int(detections[detections['name'].isin(['car', 'truck'])].shape[0])

        # Save Detection Results to JSON
        detection_results = {"vehicle_count": latest_vehicle_count}
        json_output_path = os.path.join(script_dir, "detection_results.json")
        with open(json_output_path, "w") as json_file:
            json.dump(detection_results, json_file, indent=4)

        print(f"Detected {latest_vehicle_count} vehicles.")

        # Draw Bounding Boxes
        for index, row in detections.iterrows():
            x_min, y_min, x_max, y_max = int(row['xmin']), int(row['ymin']), int(row['xmax']), int(row['ymax'])
            cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)  # Green bounding box

        cv2.imshow("Vehicle Detection", frame)

        # Update Google Sheets only every 10 seconds
        sheet.update(range_name="A1", values=[["Vehicle Count"], [latest_vehicle_count]])
        print(f"Updated Google Sheets at {time.strftime('%H:%M:%S')}.")
        
        last_update_time = current_time  # Reset update timer

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
