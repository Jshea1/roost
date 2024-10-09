# source - https://youtu.be/m5ituNiReEw

# Import libraries
from PIL import Image
import cv2
import numpy as np
# import requests 

# Reading image form url
img = Image.open('./carpark.png')
img = img.resize((450,250))
#img.show() - test loading the image (load successful)

img_array = np.array(img)
#print(img_array) - printed successfully

img_gray = cv2.cvtColor(img_array,cv2.COLOR_BGR2GRAY) # convert to gray scale
#pil_image = Image.fromarray(img_gray)
#pil_image.show() - Successful gray code image produced

img_blur = cv2.GaussianBlur(img_gray,(5,5),0) # de noise
#pil_image = Image.fromarray(img_blur)
#pil_image.show() - Successful de noise

img_dilated = cv2.dilate(img_blur,np.ones((3,3)))
#pil_image = Image.fromarray(img_dilated)
#pil_image.show() - checked

kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
final_img = cv2.morphologyEx(img_dilated, cv2.MORPH_CLOSE, kernel) 
#pil_image = Image.fromarray(final_img)
#pil_image.show() - checked

cascade_source = './cars.xml'
car_cascade = cv2.CascadeClassifier(cascade_source)
cars = car_cascade.detectMultiScale(final_img, 1.09, 1) # detects any size of car
print(len(cars))





