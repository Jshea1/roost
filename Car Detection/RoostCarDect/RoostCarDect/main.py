import cv2
import torch

# Load the YOLOv5 model
model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)

# Load your image
img_path = './carpark6.png'
img = cv2.imread(img_path)
img_resized = cv2.resize(img, (450, 250))


# Convert the image to RGB (YOLOv5 expects images in RGB format)
img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)

# Perform inference
results = model(img_rgb)

# Print the results (coordinates, labels, confidence scores)
print(results.pandas().xyxy[0])  # Pandas DataFrame with results

# Draw bounding boxes and labels on the image
results.render()

# Save or display the result
cv2.imshow('YOLOv5 Detection', results.ims[0])
cv2.waitKey(0)  # Press any key to close the window
cv2.destroyAllWindows()
