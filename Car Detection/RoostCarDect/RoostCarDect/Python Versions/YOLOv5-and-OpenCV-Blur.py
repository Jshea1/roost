import cv2
import os
import torch

script_dir = os.path.dirname(os.path.abspath(__file__))
img_path = os.path.join(script_dir, 'CamTest.png')

# Load the YOLOv5 model for vehicle detection
model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)

# Load your image
#img_path = './CamTest1.png'
img = cv2.imread(img_path) 
img_resized = cv2.resize(img, (2550, 540))

# Convert the image to RGB (YOLOv5 expects images in RGB format)
img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)

# Perform inference to detect vehicles
results = model(img_rgb)
detections = results.pandas().xyxy[0]  # x_min, y_min, x_max, y_max, confidence, class, name

# Count the number of vehicles detected (YOLOv5 labels cars as 'car' or 'truck')
vehicle_count = detections[detections['name'].isin(['car', 'truck'])].shape[0]

# Load additional models for face and license plate detection
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
plate_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_russian_plate_number.xml')

# Convert image to grayscale for face and license plate detection
gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)

# Detect faces and apply blur
faces = face_cascade.detectMultiScale(gray, 1.1, 4)
face_count = len(faces)

for (x, y, w, h) in faces:
    # Apply Gaussian blur to the face region
    face_region = img_resized[y:y+h, x:x+w]
    blurred_face = cv2.GaussianBlur(face_region, (23, 23), 30)
    img_resized[y:y+h, x:x+w] = blurred_face

# Detect license plates and apply blur
plates = plate_cascade.detectMultiScale(gray, 1.01, 3)
plate_count = len(plates)

for (x, y, w, h) in plates:
    # Apply Gaussian blur to the license plate region
    plate_region = img_resized[y:y+h, x:x+w]
    blurred_plate = cv2.GaussianBlur(plate_region, (23, 23), 30)
    img_resized[y:y+h, x:x+w] = blurred_plate

# Draw bounding boxes around detected vehicles (from YOLOv5)
for index, row in detections.iterrows():
    x_min, y_min, x_max, y_max = int(row['xmin']), int(row['ymin']), int(row['xmax']), int(row['ymax'])
    # Draw the bounding box for vehicles
    cv2.rectangle(img_resized, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)

# Print the counts of each detection type
print(f"Total vehicles detected: {vehicle_count}")
print(f"Total license plates detected: {plate_count}")
print(f"Total faces detected: {face_count}")

# Display the result
cv2.imshow('Detection with Blurred Faces and Plates', img_resized)
cv2.waitKey(0)  # Press any key to close the window
cv2.destroyAllWindows()
