#include "edmodule.hpp"
#include "CNEllipseDetector.h"
#include "common.h"

using namespace std;
//using namespace cv;

namespace ed
{
//  EllipseCV::EllipseCV(Ellipse ell) {
//    _xc = ell._xc;
//    _yc = ell._yc;
//    _a = ell._a;
//    _b = ell._b;
//    _rad = ell._rad;
//    _score = ell._score;
//  };

  void CV_EXPORTS_W ImgDetectDrawEllipses(Mat3b &image)
  {
      Mat1b gray;
      CNEllipseDetector cned;
      Size sz = image.size();

      // Parameters Settings (Sect. 4.2)
      int	iThLength = 16;
      float	fThObb = 3.0f;
      float	fThPos = 1.0f;
      float	fTaoCenters = 0.05f;
      int 	iNs = 16;//ÏÒÊý
      float	fMaxCenterDistance = sqrt(float(sz.width*sz.width + sz.height*sz.height)) * fTaoCenters;

      // Other constant parameters settings.
      // Gaussian filter parameters, in pre-processing
      Size	szPreProcessingGaussKernelSize	= Size(5,5);
      double	dPreProcessingGaussSigma	= 1.0;
      float	fDistanceToEllipseContour		= 0.1f;	// (Sect. 3.3.1 - Validation)

      cned.SetParameters	(
              szPreProcessingGaussKernelSize,
              dPreProcessingGaussSigma,
              fThPos,
              fMaxCenterDistance,
              iThLength,
              fThObb,
              fDistanceToEllipseContour,
              0.9f,
              0.9f,
              iNs
      );

      cvtColor(image, gray, COLOR_BGR2GRAY);
      vector<Ellipse> ellipses;

      //Find Ellipses
      cned.Detect(gray, ellipses);
      cned.DrawDetectedEllipses(image, ellipses, 0, 3);

  }

//  void CNEllipseDetectorCV::Detect(
//            Mat1b &gray,
//            EllipseCV &ellipse
//  ) {
//        vector<Ellipse> ellipses;
//        CNEllipseDetector::Detect(
//                gray,
//                ellipses
//        );
//        Ellipse& e = ellipses[0];
//        ellipse = EllipseCV(e);
//  }

}