import cv2
import sys
sys.path.append('build')
import ed

im = cv2.imread('images/soccer_frame_1.jpg')  #, cv2.IMREAD_GRAYSCALE)
im_detected = im.copy()

ed.ImgDetectDrawEllipses(im_detected)

cv2.imshow("Original image", im)
cv2.imshow("Python Module Function Example", im_detected)
cv2.waitKey(0)
