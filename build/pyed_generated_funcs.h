static PyObject* pyed_ed_ImgDetectDrawEllipses(PyObject* , PyObject* args, PyObject* kw)
{
    using namespace ed;

    PyObject* pyobj_img = NULL;
    Mat3b img;

    const char* keywords[] = { "img", NULL };
    if( PyArg_ParseTupleAndKeywords(args, kw, "O:ImgDetectDrawEllipses", (char**)keywords, &pyobj_img) &&
        pyed_to(pyobj_img, img, ArgInfo("img", 0)) )
    {
        ERRWRAP2(ed::ImgDetectDrawEllipses(img));
        Py_RETURN_NONE;
    }

    return NULL;
}

