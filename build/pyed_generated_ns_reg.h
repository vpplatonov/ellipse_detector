static PyMethodDef methods_ed[] = {
    {"ImgDetectDrawEllipses", (PyCFunction)pyed_ed_ImgDetectDrawEllipses, METH_VARARGS | METH_KEYWORDS, "ImgDetectDrawEllipses(img) -> None\n."},
    {NULL, NULL}
};

static ConstDef consts_ed[] = {
    {NULL, 0}
};

static void init_submodules(PyObject * root) 
{
  init_submodule(root, MODULESTR"", methods_ed, consts_ed);
};
