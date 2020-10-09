# CNC-Ellipse-Detector
[A Fast Ellipse Detector Using Projective Invariant Pruning] (https://arxiv.org/pdf/1608.07470.pdf)
- This is the source code of A Fast Ellipse Detector Using Projective Invariant Pruning.
- We proposed a fast and accurate method to get arcs belongs to an ellipse.
- The average detect-time of Dataset #1 is about 8.55ms.(CPU: i7 6700)

## Demo for Windows
### CNCE.exe

### How to use
- -N image Name 
- -D DataSet Name
- -P The Path of DataSet`s father name
- -S The threshold of ellipse score
- -R The threshold of Reliability
- -C The threshold of CenterDis
- -M The Method Id
	Method Id:
	* 1	Detect one image. (default value)
	* 2	Detect one DB

### Result
- 027_0003.jpg detect-time 18.94ms Image size [720*435].

<img src="./resultImage/resultImage.jpg" width="60%" height="60%">
- bike_0068.jpg detect-time 12.77ms Image size [640*480].

<img src="./resultImage/resultImage (6).jpg" width="60%" height="60%">
- Other results are shown in paper.

## Future
- Parameter self-adjust
- More complex images

## Thanks
- [Michele Fornaciari] (https://sourceforge.net/projects/yaed/)
- [OpenCV 3.4.11] (http://opencv.org/)

### install
- [Install openCV] (https://docs.opencv.org/3.4.11/d7/d9f/tutorial_linux_install.html)
better way use cmake-gui 

## Contact
- Email: lianbosong@foxmail.com
