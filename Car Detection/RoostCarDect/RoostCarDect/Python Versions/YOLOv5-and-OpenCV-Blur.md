This variant of the code successfully uses Yolov5 (with just the boxes; no confidence levels)

OpenCVs haarcascades for license plates and faces was used. I have not tried images with faces, but it has worked on license plates. Results vary; the closer the vehicle is, the more likely it is to get the plate detced and blurred. I have seen that for some vehicles, the entire vehicle is blurred. 

I'm thinking instead of trying to blur the license plates specifically, detect the vehicles, then blur out the entire vehicle since it's easier to detect. Then the info of the cars deteched can be the only data tracked and shared. 