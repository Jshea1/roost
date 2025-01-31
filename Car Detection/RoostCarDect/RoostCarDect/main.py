import cv2
import os
import torch
import json
import gspread
from google.oauth2.service_account import Credentials

#  Camera Configuration 
RTSP_URL = "rtsp://admin:2025@ROOST11@169.254.109.34:681/Streaming/channels/101"  # Replace with actual details

#  Set up paths 
script_dir = os.path.dirname(os.path.abspath(__file__))
json_key_path = os.path.join(script_dir, 'test1roost-0c848c46550d.json')

#  Load the YOLOv5 model for vehicle detection 
model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)

#  Google Sheets API Authentication 
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(json_key_path, scopes=SCOPES)
client = gspread.authorize(creds)

#  Open Google Sheet 
SPREADSHEET_ID = "1Kb-Vu3I1DIRUix-8swzzwJcqiEAkBGkW8JaDrD7r4bo"  # Replace with your actual spreadsheet ID
sheet = client.open_by_key(SPREADSHEET_ID).sheet1  # Select the first sheet

#  Open RTSP Video Stream 
cap = cv2.VideoCapture(RTSP_URL)

if not cap.isOpened():
    print("Error: Could not open video stream")
    exit()

print("Processing video feed... Press 'q' to stop.")

while True:
    ret, frame = cap.read()
    
    if not ret:
        print("Failed to grab frame")
        break

    # Resize for consistent YOLOv5 processing
    img_resized = cv2.resize(frame, (2560, 540))

    # Convert to RGB (YOLOv5 expects RGB format)
    img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)

    # Perform inference to detect vehicles
    results = model(img_rgb)
    detections = results.pandas().xyxy[0]  # x_min, y_min, x_max, y_max, confidence, class, name

    # Count the number of vehicles detected (cars and trucks)
    vehicle_count = int(detections[detections['name'].isin(['car', 'truck'])].shape[0])

    #  Save Detection Results to JSON 
    detection_results = {"vehicle_count": vehicle_count}
    json_output_path = os.path.join(script_dir, "detection_results.json")
    with open(json_output_path, "w") as json_file:
        json.dump(detection_results, json_file, indent=4)

    print(f"Detected {vehicle_count} vehicles.")

    #  Update Google Sheets 
    sheet.update(range_name="A1", values=[["Vehicle Count"], [vehicle_count]]) # Write data to A1
    print("Vehicle count successfully updated in Google Sheets.")

    for index, row in detections.iterrows():
        x_min, y_min, x_max, y_max = int(row['xmin']), int(row['ymin']), int(row['xmax']), int(row['ymax'])
        # Draw the bounding box
        cv2.rectangle(img_resized, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)  # Green bounding box

    # Display frame with detections
    cv2.imshow("Vehicle Detection", img_resized)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
