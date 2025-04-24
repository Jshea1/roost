import cv2
import json
import os

# Path to your image and output JSON
IMAGE   = "Annotations/test_img/CamTest3.png"
OUTPUT  = "CamTest3.json"

polygons = []      # will hold multiple spot polygons
current = []       # current spot being clicked

def on_mouse(evt, x, y, flags, param):
    if evt == cv2.EVENT_LBUTTONDOWN:
        current.append([x, y])
        cv2.circle(img, (x, y), 3, (0, 255, 0), -1)
        cv2.imshow("Annotate", img)

# Load image
img = cv2.imread(IMAGE)
if img is None:
    print(f"Error: could not open image at {IMAGE}")
    exit(1)

# Create a resizable window and resize it to match the image dimensions
cv2.namedWindow("Annotate", cv2.WINDOW_NORMAL)
h, w = img.shape[:2]
cv2.resizeWindow("Annotate", w, h)

cv2.setMouseCallback("Annotate", on_mouse)

print("Click corners for one spot. When done with that spot, press 'n' to save it and start the next.")
print("When ALL spots are done, press 's' to save everything and quit.")

while True:
    cv2.imshow("Annotate", img)
    key = cv2.waitKey(1) & 0xFF
    if key == ord("n"):
        # finish this polygon
        if len(current) >= 3:
            polygons.append(current.copy())
            print(f"Saved polygon #{len(polygons)} with {len(current)} points.")
            current.clear()
        else:
            print("Need at least 3 points for a polygon.")
    elif key == ord("s"):
        # save all and exit
        break

cv2.destroyAllWindows()

# Ensure the output folder exists
out_dir = os.path.dirname(OUTPUT)
if out_dir and not os.path.exists(out_dir):
    os.makedirs(out_dir)

# Write out all your polygons
with open(OUTPUT, "w") as f:
    json.dump({"polygons": polygons}, f, indent=2)

print(f"Wrote {OUTPUT} with {len(polygons)} polygons.")
