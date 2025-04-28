import cv2

RTSP_URL = "rtsp://admin:2025@ROOST11@169.254.109.34:681/Streaming/channels/103"
cap = cv2.VideoCapture(RTSP_URL)
ret, frame = cap.read()
if not ret:
    raise RuntimeError("Couldn't grab frame")
cv2.imwrite("RTSP_snapshot.png", frame)
cap.release()
