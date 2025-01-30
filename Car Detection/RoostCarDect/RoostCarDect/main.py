import cv2
import os
import torch
import json

script_dir = os.path.dirname(os.path.abspath(__file__))
img_path = os.path.join(script_dir, 'CamTest7.png')

# Load the YOLOv5 model for vehicle detection
model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)

# Load the image
img = cv2.imread(img_path) 
img_resized = cv2.resize(img, (2560, 540))

# Convert the image to RGB (YOLOv5 expects images in RGB format)
img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)

# Perform inference to detect vehicles
results = model(img_rgb)
detections = results.pandas().xyxy[0]  # x_min, y_min, x_max, y_max, confidence, class, name

# Count the number of vehicles detected (cars and trucks) and convert to Python int
vehicle_count = int(detections[detections['name'].isin(['car', 'truck'])].shape[0])

# Create a dictionary to store only the vehicle count
detection_results = {
    "vehicle_count": vehicle_count
}

# Save the count to a JSON file
json_output_path = os.path.join(script_dir, "detection_results.json")
with open(json_output_path, "w") as json_file:
    json.dump(detection_results, json_file, indent=4)

print(f"Detection results saved to {json_output_path}")