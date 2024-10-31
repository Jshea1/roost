import cv2
import torch

# Load the YOLOv5 model
model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)

# Load your image
img_path = './CamTest1.png'
img = cv2.imread(img_path) 
img_resized = cv2.resize(img, (1200, 400))


# Convert# the image to RGB (YOLOv5 expects images in RGB format)
img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)

# Perform inference
results = model(img_rgb)
 
# The code below prints out the cars detected, as well as the confidence level
"""
# Print the results (coordinates, labels, confidence scores)
print(results.pandas().xyxy[0])  # Pandas DataFrame with results

# Draw bounding boxes and labels on the image
results.render()

# Save or display the result
cv2.imshow('YOLOv5 Detection', results.ims[0])
cv2.waitKey(0)  # Press any key to close the window
cv2.destroyAllWindows()
"""

# Get the detection results as a Pandas DataFrame
detections = results.pandas().xyxy[0]  # x_min, y_min, x_max, y_max, confidence, class, name
print(results.pandas().xyxy[0])  # Pandas DataFrame with results

# Draw bounding boxes without labels or confidence scores
for index, row in detections.iterrows():
    x_min, y_min, x_max, y_max = int(row['xmin']), int(row['ymin']), int(row['xmax']), int(row['ymax'])
    # Draw the bounding box
    cv2.rectangle(img_resized, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)  # Green bounding box

# Display the result
cv2.imshow('YOLOv5 Detection', img_resized)
cv2.waitKey(0)  # Press any key to close the window
cv2.destroyAllWindows()



