#include <opencv2/opencv.hpp>
//#include "CNEllipseDetector.h"
//#include "common.h"

//using namespace std;
using namespace cv;

namespace ed
{
    CV_EXPORTS_W void ImgDetectDrawEllipses(Mat3b &img);

//    struct CV_EXPORTS_W_MAP EllipseCV
//    {
//    public:
//        CV_PROP_RW float _xc, _yc, _a, _b, _rad, _score;
//        EllipseCV();
//        EllipseCV(Ellipse);
//    };
//
//	class CV_EXPORTS_W CNEllipseDetectorCV: public CNEllipseDetector
//	{
//	public:
//		CV_WRAP CNEllipseDetectorCV();
//		CV_WRAP void SetParameters(
//                CV_IN_OUT Size	szPreProcessingGaussKernelSize,
//                double	dPreProcessingGaussSigma,
//                float 	fThPosition,
//                float	fMaxCenterDistance,
//                int		iMinEdgeLength,
//                float	fMinOrientedRectSide,
//                float	fDistanceToEllipseContour,
//                float	fMinScore,
//                float	fMinReliability,
//                int     iNs
//        );
//        CV_WRAP void Detect
//                (Mat1b &gray,
//                 CV_OUT EllipseCV& ellipse
//                 );
//        CV_WRAP void DrawDetectedEllipses(
//                InputOutputArray image,
//                CV_OUT EllipseCV& ellipse,
//                int iTopN,
//                int thickness
//                );
//	};


}