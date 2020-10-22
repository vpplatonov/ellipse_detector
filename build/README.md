## convert OpenCV C++ code into a Python module
https://www.learnopencv.com/how-to-convert-your-opencv-c-code-into-a-python-module

https://github.com/spmallick/learnopencv/tree/master/pymodule

https://docs.opencv.org/3.4.11/da/d49/tutorial_py_bindings_basics.html

### install
```
sudo apt-get install python-numpy
```

### opencv CMake-gui
-DENABLE_PRECOMPILED_HEADERS=OFF

### generate bindings
Use gen2.py to generate the Python binding files. You need to specify the prefix (pybv), 
the location of the temporary files (build) and the location of the header files (headers.txt).

```bash
python3 gen2.py pyed build headers.txt
```

### compile
```
g++ -shared -rdynamic -g -O3 -Wall -fPIC \
ed.cpp src/edmodule.cpp \
-DMODULE_STR=ed -DMODULE_PREFIX=pyed \
-DNDEBUG -DPY_MAJOR_VERSION=3 \
`pkg-config --cflags --libs opencv`  \
`python3-config --includes --ldflags` \
-I . -I ~/anaconda3/envs/opencv3p3.8/lib/python3.8/site-packages/numpy/core/include -I build \
-o build/ed.so 
```

```
g++ -shared -rdynamic -g -O3 -Wall -fPIC bv.cpp src/bvmodule.cpp \
-DMODULE_STR=bv \
-DMODULE_PREFIX=pybv -DNDEBUG \
-DPY_MAJOR_VERSION=3 \
`pkg-config --cflags --libs opencv` \
`python3-config --includes --ldflags` \
-I . -I ~/anaconda3/envs/opencv3p3.8/lib/python3.8/site-packages/numpy/core/include -I build \
-o build/bv.so
```

### 