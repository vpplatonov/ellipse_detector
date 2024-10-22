#!/usr/bin/env python

from __future__ import print_function
import hdr_parser, sys, re, os
from string import Template
from pprint import pprint

if sys.version_info[0] >= 3:
    from io import StringIO
else:
    from cStringIO import StringIO

ignored_arg_types = ["RNG*"]

gen_template_check_self = Template("""    $cname* _self_ = NULL;
    if(PyObject_TypeCheck(self, &${modulePrefix}_${name}_Type))
        _self_ = ${amp}((${modulePrefix}_${name}_t*)self)->v${get};
    if (_self_ == NULL)
        return failmsgp("Incorrect type of self (must be '${name}' or its derivative)");
""")

gen_template_check_self_algo = Template("""    $cname* _self_ = NULL;
    if(PyObject_TypeCheck(self, &${modulePrefix}_${name}_Type))
        _self_ = dynamic_cast<$cname*>(${amp}((${modulePrefix}_${name}_t*)self)->v.get());
    if (_self_ == NULL)
        return failmsgp("Incorrect type of self (must be '${name}' or its derivative)");
""")

gen_template_call_constructor_prelude = Template("""new (&(self->v)) Ptr<$cname>(); // init Ptr with placement new
        if(self) """)

gen_template_call_constructor = Template("""self->v.reset(new ${cname}${args})""")

gen_template_simple_call_constructor_prelude = Template("""if(self) """)

gen_template_simple_call_constructor = Template("""new (&(self->v)) ${cname}${args}""")

gen_template_parse_args = Template("""const char* keywords[] = { $kw_list, NULL };
    if( PyArg_ParseTupleAndKeywords(args, kw, "$fmtspec", (char**)keywords, $parse_arglist)$code_cvt )""")

gen_template_func_body = Template("""$code_decl
    $code_parse
    {
        ${code_prelude}ERRWRAP2($code_fcall);
        $code_ret;
    }
""")

head_init_str = "CV_PYTHON_TYPE_HEAD_INIT()"

gen_template_simple_type_decl = Template("""
struct ${modulePrefix}_${name}_t
{
    PyObject_HEAD
    ${cname} v;
};
static PyTypeObject ${modulePrefix}_${name}_Type =
{
    %s
    MODULESTR".$wname",
    sizeof(${modulePrefix}_${name}_t),
};
static void ${modulePrefix}_${name}_dealloc(PyObject* self)
{
    ((${modulePrefix}_${name}_t*)self)->v.${cname}::~${sname}();
    PyObject_Del(self);
}
template<> PyObject* ${modulePrefix}_from(const ${cname}& r)
{
    ${modulePrefix}_${name}_t *m = PyObject_NEW(${modulePrefix}_${name}_t, &${modulePrefix}_${name}_Type);
    new (&m->v) ${cname}(r); //Copy constructor
    return (PyObject*)m;
}
template<> bool ${modulePrefix}_to(PyObject* src, ${cname}& dst, const char* name)
{
    if( src == NULL || src == Py_None )
        return true;
    if(!PyObject_TypeCheck(src, &${modulePrefix}_${name}_Type))
    {
        failmsg("Expected ${cname} for argument '%%s'", name);
        return false;
    }
    dst = ((${modulePrefix}_${name}_t*)src)->v;
    return true;
}
""" % head_init_str)


gen_template_type_decl = Template("""
struct ${modulePrefix}_${name}_t
{
    PyObject_HEAD
    Ptr<${cname1}> v;
};
static PyTypeObject ${modulePrefix}_${name}_Type =
{
    %s
    MODULESTR".$wname",
    sizeof(${modulePrefix}_${name}_t),
};
static void ${modulePrefix}_${name}_dealloc(PyObject* self)
{
    ((${modulePrefix}_${name}_t*)self)->v.release();
    PyObject_Del(self);
}
template<> PyObject* ${modulePrefix}_from(const Ptr<${cname}>& r)
{
    ${modulePrefix}_${name}_t *m = PyObject_NEW(${modulePrefix}_${name}_t, &${modulePrefix}_${name}_Type);
    new (&(m->v)) Ptr<$cname1>(); // init Ptr with placement new
    m->v = r;
    return (PyObject*)m;
}
template<> bool ${modulePrefix}_to(PyObject* src, Ptr<${cname}>& dst, const char* name)
{
    if( src == NULL || src == Py_None )
        return true;
    if(!PyObject_TypeCheck(src, &${modulePrefix}_${name}_Type))
    {
        failmsg("Expected ${cname} for argument '%%s'", name);
        return false;
    }
    dst = ((${modulePrefix}_${name}_t*)src)->v.dynamicCast<${cname}>();
    return true;
}
""" % head_init_str)

gen_template_map_type_cvt = Template("""
template<> bool ${modulePrefix}_to(PyObject* src, ${cname}& dst, const char* name);
""")

gen_template_set_prop_from_map = Template("""
    if( PyMapping_HasKeyString(src, (char*)"$propname") )
    {
        tmp = PyMapping_GetItemString(src, (char*)"$propname");
        ok = tmp && ${modulePrefix}_to(tmp, dst.$propname);
        Py_DECREF(tmp);
        if(!ok) return false;
    }""")

gen_template_type_impl = Template("""
static PyObject* ${modulePrefix}_${name}_repr(PyObject* self)
{
    char str[1000];
    sprintf(str, "<$wname %p>", self);
    return PyString_FromString(str);
}
${getset_code}
static PyGetSetDef ${modulePrefix}_${name}_getseters[] =
{${getset_inits}
    {NULL}  /* Sentinel */
};
${methods_code}
static PyMethodDef ${modulePrefix}_${name}_methods[] =
{
${methods_inits}
    {NULL,          NULL}
};
static void ${modulePrefix}_${name}_specials(void)
{
    ${modulePrefix}_${name}_Type.tp_base = ${baseptr};
    ${modulePrefix}_${name}_Type.tp_dealloc = ${modulePrefix}_${name}_dealloc;
    ${modulePrefix}_${name}_Type.tp_repr = ${modulePrefix}_${name}_repr;
    ${modulePrefix}_${name}_Type.tp_getset = ${modulePrefix}_${name}_getseters;
    ${modulePrefix}_${name}_Type.tp_init = (initproc)${constructor};
    ${modulePrefix}_${name}_Type.tp_methods = ${modulePrefix}_${name}_methods;${extra_specials}
}
""")


gen_template_get_prop = Template("""
static PyObject* ${modulePrefix}_${name}_get_${member}(${modulePrefix}_${name}_t* p, void *closure)
{
    return ${modulePrefix}_from(p->v${access}${member});
}
""")

gen_template_get_prop_algo = Template("""
static PyObject* ${modulePrefix}_${name}_get_${member}(${modulePrefix}_${name}_t* p, void *closure)
{
    $cname* _self_ = dynamic_cast<$cname*>(p->v.get());
    if (_self_ == NULL)
        return failmsgp("Incorrect type of object (must be '${name}' or its derivative)");
    return ${modulePrefix}_from(_self_${access}${member});
}
""")

gen_template_set_prop = Template("""
static int ${modulePrefix}_${name}_set_${member}(${modulePrefix}_${name}_t* p, PyObject *value, void *closure)
{
    if (value == NULL)
    {
        PyErr_SetString(PyExc_TypeError, "Cannot delete the ${member} attribute");
        return -1;
    }
    return ${modulePrefix}_to(value, p->v${access}${member}) ? 0 : -1;
}
""")

gen_template_set_prop_algo = Template("""
static int ${modulePrefix}_${name}_set_${member}(${modulePrefix}_${name}_t* p, PyObject *value, void *closure)
{
    if (value == NULL)
    {
        PyErr_SetString(PyExc_TypeError, "Cannot delete the ${member} attribute");
        return -1;
    }
    $cname* _self_ = dynamic_cast<$cname*>(p->v.get());
    if (_self_ == NULL)
    {
        failmsgp("Incorrect type of object (must be '${name}' or its derivative)");
        return -1;
    }
    return ${modulePrefix}_to(value, _self_${access}${member}) ? 0 : -1;
}
""")


gen_template_prop_init = Template("""
    {(char*)"${member}", (getter)${modulePrefix}_${name}_get_${member}, NULL, (char*)"${member}", NULL},""")

gen_template_rw_prop_init = Template("""
    {(char*)"${member}", (getter)${modulePrefix}_${name}_get_${member}, (setter)${modulePrefix}_${name}_set_${member}, (char*)"${member}", NULL},""")

simple_argtype_mapping = {
    "bool": ("bool", "b", "0"),
    "size_t": ("size_t", "I", "0"),
    "int": ("int", "i", "0"),
    "float": ("float", "f", "0.f"),
    "double": ("double", "d", "0"),
    "c_string": ("char*", "s", '(char*)""')
}

def normalize_class_name(name):
    return re.sub(r"^cv\.", "", name).replace(".", "_")

class ClassProp(object):
    def __init__(self, decl):
        self.tp = decl[0].replace("*", "_ptr")
        self.name = decl[1]
        self.readonly = True
        if "/RW" in decl[3]:
            self.readonly = False

class ClassInfo(object):
    def __init__(self, name, decl=None):
        self.cname = name.replace(".", "::")
        self.name = self.wname = normalize_class_name(name)
        self.sname = name[name.rfind('.') + 1:]
        self.ismap = False
        self.issimple = False
        self.isalgorithm = False
        self.methods = {}
        self.props = []
        self.consts = {}
        self.base = None
        self.constructor = None
        customname = False

        if decl:
            bases = decl[1].split()[1:]
            if len(bases) > 1:
                print("Note: Class %s has more than 1 base class (not supported by Python C extensions)" % (self.name,))
                print("      Bases: ", " ".join(bases))
                print("      Only the first base class will be used")
                #return sys.exit(-1)
            elif len(bases) == 1:
                self.base = bases[0].strip(",")
                if self.base.startswith("cv::"):
                    self.base = self.base[4:]
                if self.base == "Algorithm":
                    self.isalgorithm = True
                self.base = self.base.replace("::", "_")

            for m in decl[2]:
                if m.startswith("="):
                    self.wname = m[1:]
                    customname = True
                elif m == "/Map":
                    self.ismap = True
                elif m == "/Simple":
                    self.issimple = True
            self.props = [ClassProp(p) for p in decl[3]]

        if not customname and self.wname.startswith("Cv"):
            self.wname = self.wname[2:]

    def gen_map_code(self, codegen):
        all_classes = codegen.classes
        code = ("static bool " + modulePrefix + "_to(PyObject* src, %s& dst, const char* name)\n{\n    PyObject* tmp;\n    bool ok;\n") % (self.cname)
        code += "".join([gen_template_set_prop_from_map.substitute(modulePrefix=modulePrefix,propname=p.name,proptype=p.tp) for p in self.props])
        if self.base:
            code += "\n    return " + modulePrefix + "_to(src, (%s&)dst, name);\n}\n" % all_classes[self.base].cname
        else:
            code += "\n    return true;\n}\n"
        return code

    def gen_code(self, codegen):
        all_classes = codegen.classes
        if self.ismap:
            return self.gen_map_code(codegen)

        getset_code = StringIO()
        getset_inits = StringIO()

        sorted_props = [(p.name, p) for p in self.props]
        sorted_props.sort()

        access_op = "->"
        if self.issimple:
            access_op = "."

        for pname, p in sorted_props:
            if self.isalgorithm:
                getset_code.write(gen_template_get_prop_algo.substitute(modulePrefix=modulePrefix,name=self.name, cname=self.cname, member=pname, membertype=p.tp, access=access_op))
            else:
                getset_code.write(gen_template_get_prop.substitute(modulePrefix=modulePrefix,name=self.name, member=pname, membertype=p.tp, access=access_op))
            if p.readonly:
                getset_inits.write(gen_template_prop_init.substitute(modulePrefix=modulePrefix,name=self.name, member=pname))
            else:
                if self.isalgorithm:
                    getset_code.write(gen_template_set_prop_algo.substitute(modulePrefix=modulePrefix,name=self.name, cname=self.cname, member=pname, membertype=p.tp, access=access_op))
                else:
                    getset_code.write(gen_template_set_prop.substitute(modulePrefix=modulePrefix,name=self.name, member=pname, membertype=p.tp, access=access_op))
                getset_inits.write(gen_template_rw_prop_init.substitute(modulePrefix=modulePrefix,name=self.name, member=pname))

        methods_code = StringIO()
        methods_inits = StringIO()

        sorted_methods = list(self.methods.items())
        sorted_methods.sort()

        if self.constructor is not None:
            methods_code.write(self.constructor.gen_code(codegen))

        for mname, m in sorted_methods:
            methods_code.write(m.gen_code(codegen))
            methods_inits.write(m.get_tab_entry())

        baseptr = "NULL"
        if self.base and self.base in all_classes:
            baseptr = "&" + modulePrefix + "_" + all_classes[self.base].name + "_Type"

        constructor_name = "0"
        if self.constructor is not None:
            constructor_name = self.constructor.get_wrapper_name()

        code = gen_template_type_impl.substitute(modulePrefix=modulePrefix,name=self.name, wname=self.wname, cname=self.cname,
            getset_code=getset_code.getvalue(), getset_inits=getset_inits.getvalue(),
            methods_code=methods_code.getvalue(), methods_inits=methods_inits.getvalue(),
            baseptr=baseptr, constructor=constructor_name, extra_specials="")

        return code


def handle_ptr(tp):
    if tp.startswith('Ptr_'):
        tp = 'Ptr<' + "::".join(tp.split('_')[1:]) + '>'
    return tp


class ArgInfo(object):
    def __init__(self, arg_tuple):
        self.tp = handle_ptr(arg_tuple[0])
        self.name = arg_tuple[1]
        self.defval = arg_tuple[2]
        self.isarray = False
        self.arraylen = 0
        self.arraycvt = None
        self.inputarg = True
        self.outputarg = False
        self.returnarg = False
        for m in arg_tuple[3]:
            if m == "/O":
                self.inputarg = False
                self.outputarg = True
                self.returnarg = True
            elif m == "/IO":
                self.inputarg = True
                self.outputarg = True
                self.returnarg = True
            elif m.startswith("/A"):
                self.isarray = True
                self.arraylen = m[2:].strip()
            elif m.startswith("/CA"):
                self.isarray = True
                self.arraycvt = m[2:].strip()
        self.py_inputarg = False
        self.py_outputarg = False

    def isbig(self):
        return self.tp == "Mat" or self.tp == "vector_Mat"\
               or self.tp == "UMat" or self.tp == "vector_UMat" # or self.tp.startswith("vector")

    def crepr(self):
        return "ArgInfo(\"%s\", %d)" % (self.name, self.outputarg)


class FuncVariant(object):
    def __init__(self, classname, name, decl, isconstructor):
        self.classname = classname
        self.name = self.wname = name
        self.isconstructor = isconstructor

        self.docstring = decl[5]

        self.rettype = decl[4] or handle_ptr(decl[1])
        if self.rettype == "void":
            self.rettype = ""
        self.args = []
        self.array_counters = {}
        for a in decl[3]:
            ainfo = ArgInfo(a)
            if ainfo.isarray and not ainfo.arraycvt:
                c = ainfo.arraylen
                c_arrlist = self.array_counters.get(c, [])
                if c_arrlist:
                    c_arrlist.append(ainfo.name)
                else:
                    self.array_counters[c] = [ainfo.name]
            self.args.append(ainfo)
        self.init_pyproto()

    def init_pyproto(self):
        # string representation of argument list, with '[', ']' symbols denoting optional arguments, e.g.
        # "src1, src2[, dst[, mask]]" for cv.add
        argstr = ""

        # list of all input arguments of the Python function, with the argument numbers:
        #    [("src1", 0), ("src2", 1), ("dst", 2), ("mask", 3)]
        # we keep an argument number to find the respective argument quickly, because
        # some of the arguments of C function may not present in the Python function (such as array counters)
        # or even go in a different order ("heavy" output parameters of the C function
        # become the first optional input parameters of the Python function, and thus they are placed right after
        # non-optional input parameters)
        arglist = []

        # the list of "heavy" output parameters. Heavy parameters are the parameters
        # that can be expensive to allocate each time, such as vectors and matrices (see isbig).
        outarr_list = []

        # the list of output parameters. Also includes input/output parameters.
        outlist = []

        firstoptarg = 1000000
        argno = -1
        for a in self.args:
            argno += 1
            if a.name in self.array_counters:
                continue
            if a.tp in ignored_arg_types:
                continue
            if a.returnarg:
                outlist.append((a.name, argno))
            if (not a.inputarg) and a.isbig():
                outarr_list.append((a.name, argno))
                continue
            if not a.inputarg:
                continue
            if not a.defval:
                arglist.append((a.name, argno))
            else:
                firstoptarg = min(firstoptarg, len(arglist))
                # if there are some array output parameters before the first default parameter, they
                # are added as optional parameters before the first optional parameter
                if outarr_list:
                    arglist += outarr_list
                    outarr_list = []
                arglist.append((a.name, argno))

        if outarr_list:
            firstoptarg = min(firstoptarg, len(arglist))
            arglist += outarr_list
        firstoptarg = min(firstoptarg, len(arglist))

        noptargs = len(arglist) - firstoptarg
        argnamelist = [aname for aname, argno in arglist]
        argstr = ", ".join(argnamelist[:firstoptarg])
        argstr = "[, ".join([argstr] + argnamelist[firstoptarg:])
        argstr += "]" * noptargs
        if self.rettype:
            outlist = [("retval", -1)] + outlist
        elif self.isconstructor:
            assert outlist == []
            outlist = [("self", -1)]
        if self.isconstructor:
            classname = self.classname
            if classname.startswith("Cv"):
                classname=classname[2:]
            outstr = "<%s object>" % (classname,)
        elif outlist:
            outstr = ", ".join([o[0] for o in outlist])
        else:
            outstr = "None"

        self.py_arg_str = argstr
        self.py_return_str = outstr
        self.py_prototype = "%s(%s) -> %s" % (self.wname, argstr, outstr)
        self.py_noptargs = noptargs
        self.py_arglist = arglist
        for aname, argno in arglist:
            self.args[argno].py_inputarg = True
        for aname, argno in outlist:
            if argno >= 0:
                self.args[argno].py_outputarg = True
        self.py_outlist = outlist


class FuncInfo(object):
    def __init__(self, classname, name, cname, isconstructor, namespace, isclassmethod):
        self.classname = classname
        self.name = name
        self.cname = cname
        self.isconstructor = isconstructor
        self.namespace = namespace
        self.isclassmethod = isclassmethod
        self.variants = []

    def add_variant(self, decl):
        self.variants.append(FuncVariant(self.classname, self.name, decl, self.isconstructor))

    def get_wrapper_name(self):
        name = self.name
        if self.classname:
            classname = self.classname + "_"
            if "[" in name:
                name = "getelem"
        else:
            classname = ""

        if self.isclassmethod:
            name += "_cls"

        return modulePrefix + "_" + self.namespace.replace('.','_') + '_' + classname + name

    def get_wrapper_prototype(self, codegen):
        full_fname = self.get_wrapper_name()
        if self.isconstructor:
            return "static int {fn_name}({modulePrefix}_{type_name}_t* self, PyObject* args, PyObject* kw)".format(modulePrefix=modulePrefix,
                    fn_name=full_fname, type_name=codegen.classes[self.classname].name)

        if self.classname:
            self_arg = "self"
        else:
            self_arg = ""
        return "static PyObject* %s(PyObject* %s, PyObject* args, PyObject* kw)" % (full_fname, self_arg)

    def get_tab_entry(self):
        prototype_list = []
        docstring_list = []

        have_empty_constructor = False
        for v in self.variants:
            s = v.py_prototype
            if (not v.py_arglist) and self.isconstructor:
                have_empty_constructor = True
            if s not in prototype_list:
                prototype_list.append(s)
                docstring_list.append(v.docstring)

        # if there are just 2 constructors: default one and some other,
        # we simplify the notation.
        # Instead of ClassName(args ...) -> object or ClassName() -> object
        # we write ClassName([args ...]) -> object
        if have_empty_constructor and len(self.variants) == 2:
            idx = self.variants[1].py_arglist != []
            s = self.variants[idx].py_prototype
            p1 = s.find("(")
            p2 = s.rfind(")")
            prototype_list = [s[:p1+1] + "[" + s[p1+1:p2] + "]" + s[p2:]]

        # The final docstring will be: Each prototype, followed by
        # their relevant doxygen comment
        full_docstring = ""
        for prototype, body in zip(prototype_list, docstring_list):
            full_docstring += Template("$prototype\n$docstring\n\n\n\n").substitute(
                modulePrefix=modulePrefix,prototype=prototype,
                docstring='\n'.join(
                    ['.   ' + line
                     for line in body.split('\n')]
                )
            )

        # Escape backslashes, newlines, and double quotes
        full_docstring = full_docstring.strip().replace("\\", "\\\\").replace('\n', '\\n').replace("\"", "\\\"")
        # Convert unicode chars to xml representation, but keep as string instead of bytes
        full_docstring = full_docstring.encode('ascii', errors='xmlcharrefreplace').decode()

        flags = ["METH_VARARGS", "METH_KEYWORDS"]
        if self.isclassmethod:
            flags.append("METH_CLASS")

        return Template('    {"$py_funcname", (PyCFunction)$wrap_funcname, $flags, "$py_docstring"},\n'
                        ).substitute(modulePrefix=modulePrefix,py_funcname = self.variants[0].wname, wrap_funcname=self.get_wrapper_name(),
                                     flags = " | ".join(flags), py_docstring = full_docstring)

    def gen_code(self, codegen):
        all_classes = codegen.classes
        proto = self.get_wrapper_prototype(codegen)
        code = "%s\n{\n" % (proto,)
        code += "    using namespace %s;\n\n" % self.namespace.replace('.', '::')

        selfinfo = ClassInfo("")
        ismethod = self.classname != "" and not self.isconstructor
        # full name is needed for error diagnostic in PyArg_ParseTupleAndKeywords
        fullname = self.name

        if self.classname:
            selfinfo = all_classes[self.classname]
            if not self.isconstructor:
                amp = "&" if selfinfo.issimple else ""
                if self.isclassmethod:
                    pass
                elif selfinfo.isalgorithm:
                    code += gen_template_check_self_algo.substitute(modulePrefix=modulePrefix,name=selfinfo.name, cname=selfinfo.cname, amp=amp)
                else:
                    get = "" if selfinfo.issimple else ".get()"
                    code += gen_template_check_self.substitute(modulePrefix=modulePrefix,name=selfinfo.name, cname=selfinfo.cname, amp=amp, get=get)
                fullname = selfinfo.wname + "." + fullname

        all_code_variants = []
        declno = -1
        for v in self.variants:
            code_decl = ""
            code_ret = ""
            code_cvt_list = []

            code_args = "("
            all_cargs = []
            parse_arglist = []

            # declare all the C function arguments,
            # add necessary conversions from Python objects to code_cvt_list,
            # form the function/method call,
            # for the list of type mappings
            for a in v.args:
                if a.tp in ignored_arg_types:
                    defval = a.defval
                    if not defval and a.tp.endswith("*"):
                        defval = 0
                    assert defval
                    if not code_args.endswith("("):
                        code_args += ", "
                    code_args += defval
                    all_cargs.append([[None, ""], ""])
                    continue
                tp1 = tp = a.tp
                amp = ""
                defval0 = ""
                if tp.endswith("*"):
                    tp = tp1 = tp[:-1]
                    amp = "&"
                    if tp.endswith("*"):
                        defval0 = "0"
                        tp1 = tp.replace("*", "_ptr")
                if tp1.endswith("*"):
                    print("Error: type with star: a.tp=%s, tp=%s, tp1=%s" % (a.tp, tp, tp1))
                    sys.exit(-1)

                amapping = simple_argtype_mapping.get(tp, (tp, "O", defval0))
                parse_name = a.name
                if a.py_inputarg:
                    if amapping[1] == "O":
                        code_decl += "    PyObject* pyobj_%s = NULL;\n" % (a.name,)
                        parse_name = "pyobj_" + a.name
                        if a.tp == 'char':
                            code_cvt_list.append("convert_to_char(pyobj_%s, &%s, %s)"% (a.name, a.name, a.crepr()))
                        else:
                            code_cvt_list.append((modulePrefix + "_to(pyobj_%s, %s, %s)") % (a.name, a.name, a.crepr()))

                all_cargs.append([amapping, parse_name])

                defval = a.defval
                if not defval:
                    defval = amapping[2]
                else:
                    if "UMat" in tp:
                        if "Mat" in defval and "UMat" not in defval:
                            defval = defval.replace("Mat", "UMat")
                # "tp arg = tp();" is equivalent to "tp arg;" in the case of complex types
                if defval == tp + "()" and amapping[1] == "O":
                    defval = ""
                if a.outputarg and not a.inputarg:
                    defval = ""
                if defval:
                    code_decl += "    %s %s=%s;\n" % (amapping[0], a.name, defval)
                else:
                    code_decl += "    %s %s;\n" % (amapping[0], a.name)

                if not code_args.endswith("("):
                    code_args += ", "
                code_args += amp + a.name

            code_args += ")"

            if self.isconstructor:
                if selfinfo.issimple:
                    templ_prelude = gen_template_simple_call_constructor_prelude
                    templ = gen_template_simple_call_constructor
                else:
                    templ_prelude = gen_template_call_constructor_prelude
                    templ = gen_template_call_constructor

                code_prelude = templ_prelude.substitute(modulePrefix=modulePrefix,name=selfinfo.name, cname=selfinfo.cname)
                code_fcall = templ.substitute(modulePrefix=modulePrefix,name=selfinfo.name, cname=selfinfo.cname, args=code_args)
            else:
                code_prelude = ""
                code_fcall = ""
                if v.rettype:
                    code_decl += "    " + v.rettype + " retval;\n"
                    code_fcall += "retval = "
                if ismethod and not self.isclassmethod:
                    code_fcall += "_self_->" + self.cname
                else:
                    code_fcall += self.cname
                code_fcall += code_args

            if code_cvt_list:
                code_cvt_list = [""] + code_cvt_list

            # add info about return value, if any, to all_cargs. if there non-void return value,
            # it is encoded in v.py_outlist as ("retval", -1) pair.
            # As [-1] in Python accesses the last element of a list, we automatically handle the return value by
            # adding the necessary info to the end of all_cargs list.
            if v.rettype:
                tp = v.rettype
                tp1 = tp.replace("*", "_ptr")
                amapping = simple_argtype_mapping.get(tp, (tp, "O", "0"))
                all_cargs.append(amapping)

            if v.args and v.py_arglist:
                # form the format spec for PyArg_ParseTupleAndKeywords
                fmtspec = "".join([all_cargs[argno][0][1] for aname, argno in v.py_arglist])
                if v.py_noptargs > 0:
                    fmtspec = fmtspec[:-v.py_noptargs] + "|" + fmtspec[-v.py_noptargs:]
                fmtspec += ":" + fullname

                # form the argument parse code that:
                #   - declares the list of keyword parameters
                #   - calls PyArg_ParseTupleAndKeywords
                #   - converts complex arguments from PyObject's to native OpenCV types
                code_parse = gen_template_parse_args.substitute(
                    modulePrefix=modulePrefix,kw_list = ", ".join(['"' + aname + '"' for aname, argno in v.py_arglist]),
                    fmtspec = fmtspec,
                    parse_arglist = ", ".join(["&" + all_cargs[argno][1] for aname, argno in v.py_arglist]),
                    code_cvt = " &&\n        ".join(code_cvt_list))
            else:
                code_parse = "if(PyObject_Size(args) == 0 && (kw == NULL || PyObject_Size(kw) == 0))"

            if len(v.py_outlist) == 0:
                code_ret = "Py_RETURN_NONE"
            elif len(v.py_outlist) == 1:
                if self.isconstructor:
                    code_ret = "return 0"
                else:
                    aname, argno = v.py_outlist[0]
                    code_ret = ("return " + modulePrefix + "_from(%s)") % (aname,)
            else:
                # ther is more than 1 return parameter; form the tuple out of them
                fmtspec = "N"*len(v.py_outlist)
                backcvt_arg_list = []
                for aname, argno in v.py_outlist:
                    amapping = all_cargs[argno][0]
                    backcvt_arg_list.append("%s(%s)" % (amapping[2], aname))
                code_ret = "return Py_BuildValue(\"(%s)\", %s)" % \
                    (fmtspec, ", ".join([modulePrefix + "_from(" + aname + ")" for aname, argno in v.py_outlist]))

            all_code_variants.append(gen_template_func_body.substitute(modulePrefix=modulePrefix,code_decl=code_decl,
                code_parse=code_parse, code_prelude=code_prelude, code_fcall=code_fcall, code_ret=code_ret))

        if len(all_code_variants)==1:
            # if the function/method has only 1 signature, then just put it
            code += all_code_variants[0]
        else:
            # try to execute each signature
            code += "    PyErr_Clear();\n\n".join(["    {\n" + v + "    }\n" for v in all_code_variants])

        def_ret = "NULL"
        if self.isconstructor:
            def_ret = "-1"
        code += "\n    return %s;\n}\n\n" % def_ret

        cname = self.cname
        classinfo = None
        #dump = False
        #if dump: pprint(vars(self))
        #if dump: pprint(vars(self.variants[0]))
        if self.classname:
            classinfo = all_classes[self.classname]
            #if dump: pprint(vars(classinfo))
            if self.isconstructor:
                py_name = 'cv.' + classinfo.wname
            elif self.isclassmethod:
                py_name = '.'.join([self.namespace, classinfo.sname + '_' + self.variants[0].wname])
            else:
                cname = classinfo.cname + '::' + cname
                py_name = 'cv.' + classinfo.wname + '.' + self.variants[0].wname
        else:
            py_name = '.'.join([self.namespace, self.variants[0].wname])
        #if dump: print(cname + " => " + py_name)
        py_signatures = codegen.py_signatures.setdefault(cname, [])
        for v in self.variants:
            s = dict(name=py_name, arg=v.py_arg_str, ret=v.py_return_str)
            for old in py_signatures:
                if s == old:
                    break
            else:
                py_signatures.append(s)

        return code


class Namespace(object):
    def __init__(self):
        self.funcs = {}
        self.consts = {}


class PythonWrapperGenerator(object):
    def __init__(self):
        self.clear()

    def clear(self):
        self.classes = {}
        self.namespaces = {}
        self.consts = {}
        self.code_include = StringIO()
        self.code_types = StringIO()
        self.code_funcs = StringIO()
        self.code_type_reg = StringIO()
        self.code_ns_reg = StringIO()
        self.code_type_publish = StringIO()
        self.py_signatures = dict()
        self.class_idx = 0

    def add_class(self, stype, name, decl):
        classinfo = ClassInfo(name, decl)
        classinfo.decl_idx = self.class_idx
        self.class_idx += 1

        if classinfo.name in self.classes:
            print("Generator error: class %s (cname=%s) already exists" \
                % (classinfo.name, classinfo.cname))
            sys.exit(-1)
        self.classes[classinfo.name] = classinfo

        # Add Class to json file.
        namespace, classes, name = self.split_decl_name(name)
        namespace = '.'.join(namespace)
        name = '_'.join(classes+[name])

        py_name = 'cv.' + classinfo.wname  # use wrapper name
        py_signatures = self.py_signatures.setdefault(classinfo.cname, [])
        py_signatures.append(dict(name=py_name))
        #print('class: ' + classinfo.cname + " => " + py_name)

    def split_decl_name(self, name):
        chunks = name.split('.')
        namespace = chunks[:-1]
        classes = []
        while namespace and '.'.join(namespace) not in self.parser.namespaces:
            classes.insert(0, namespace.pop())
        return namespace, classes, chunks[-1]


    def add_const(self, name, decl):
        cname = name.replace('.','::')
        namespace, classes, name = self.split_decl_name(name)
        namespace = '.'.join(namespace)
        name = '_'.join(classes+[name])
        ns = self.namespaces.setdefault(namespace, Namespace())
        if name in ns.consts:
            print("Generator error: constant %s (cname=%s) already exists" \
                % (name, cname))
            sys.exit(-1)
        ns.consts[name] = cname

        value = decl[1]
        py_name = '.'.join([namespace, name])
        py_signatures = self.py_signatures.setdefault(cname, [])
        py_signatures.append(dict(name=py_name, value=value))
        #print(cname + ' => ' + str(py_name) + ' (value=' + value + ')')

    def add_func(self, decl):
        namespace, classes, barename = self.split_decl_name(decl[0])
        cname = "::".join(namespace+classes+[barename])
        name = barename
        classname = ''
        bareclassname = ''
        if classes:
            classname = normalize_class_name('.'.join(namespace+classes))
            bareclassname = classes[-1]
        namespace = '.'.join(namespace)

        isconstructor = name == bareclassname
        isclassmethod = False
        for m in decl[2]:
            if m == "/S":
                isclassmethod = True
            elif m.startswith("="):
                name = m[1:]
        if isconstructor:
            name = "_".join(classes[:-1]+[name])

        if isclassmethod:
            # Add it as a method to the class
            func_map = self.classes[classname].methods
            func = func_map.setdefault(name, FuncInfo(classname, name, cname, isconstructor, namespace, isclassmethod))
            func.add_variant(decl)

            # Add it as global function
            g_name = "_".join(classes+[name])
            func_map = self.namespaces.setdefault(namespace, Namespace()).funcs
            func = func_map.setdefault(g_name, FuncInfo("", g_name, cname, isconstructor, namespace, False))
            func.add_variant(decl)
        else:
            if classname and not isconstructor:
                cname = barename
                func_map = self.classes[classname].methods
            else:
                func_map = self.namespaces.setdefault(namespace, Namespace()).funcs

            func = func_map.setdefault(name, FuncInfo(classname, name, cname, isconstructor, namespace, isclassmethod))
            func.add_variant(decl)

        if classname and isconstructor:
            self.classes[classname].constructor = func


    def gen_namespace(self, ns_name):
        ns = self.namespaces[ns_name]
        wname = normalize_class_name(ns_name)

        self.code_ns_reg.write('static PyMethodDef methods_%s[] = {\n'%wname)
        for name, func in sorted(ns.funcs.items()):
            if func.isconstructor:
                continue
            self.code_ns_reg.write(func.get_tab_entry())
        self.code_ns_reg.write('    {NULL, NULL}\n};\n\n')

        self.code_ns_reg.write('static ConstDef consts_%s[] = {\n'%wname)
        for name, cname in sorted(ns.consts.items()):
            self.code_ns_reg.write('    {"%s", %s},\n'%(name, cname))
            compat_name = re.sub(r"([a-z])([A-Z])", r"\1_\2", name).upper()
            if name != compat_name:
                self.code_ns_reg.write('    {"%s", %s},\n'%(compat_name, cname))
        self.code_ns_reg.write('    {NULL, 0}\n};\n\n')

    def gen_namespaces_reg(self):
        self.code_ns_reg.write('static void init_submodules(PyObject * root) \n{\n')
        for ns_name in sorted(self.namespaces):
            wname = normalize_class_name(ns_name)
            self.code_ns_reg.write('  init_submodule(root, MODULESTR"%s", methods_%s, consts_%s);\n' % (ns_name[2:], wname, wname))
        self.code_ns_reg.write('};\n')


    def save(self, path, name, buf):
        with open(path + "/" + name, "wt") as f:
            f.write(buf.getvalue())

    def save_json(self, path, name, value):
        import json
        with open(path + "/" + name, "wt") as f:
            json.dump(value, f)

    def gen(self, srcfiles, output_path):
        self.clear()
        self.parser = hdr_parser.CppHeaderParser(generate_umat_decls=True)

        # step 1: scan the headers and build more descriptive maps of classes, consts, functions
        for hdr in srcfiles:
            decls = self.parser.parse(hdr)
            if len(decls) == 0:
                continue
            self.code_include.write( '#include "{0}"\n'.format(hdr[hdr.rindex('src/'):]) )
            for decl in decls:
                name = decl[0]
                if name.startswith("struct") or name.startswith("class"):
                    # class/struct
                    p = name.find(" ")
                    stype = name[:p]
                    name = name[p+1:].strip()
                    self.add_class(stype, name, decl)
                elif name.startswith("const"):
                    # constant
                    self.add_const(name.replace("const ", "").strip(), decl)
                else:
                    # function
                    self.add_func(decl)

        # step 1.5 check if all base classes exist
        for name, classinfo in self.classes.items():
            if classinfo.base:
                chunks = classinfo.base.split('_')
                base = '_'.join(chunks)
                while base not in self.classes and len(chunks)>1:
                    del chunks[-2]
                    base = '_'.join(chunks)
                if base not in self.classes:
                    print("Generator error: unable to resolve base %s for %s"
                        % (classinfo.base, classinfo.name))
                    sys.exit(-1)
                base_instance = self.classes[base]
                classinfo.base = base
                classinfo.isalgorithm |= base_instance.isalgorithm  # wrong processing of 'isalgorithm' flag:
                                                                    # doesn't work for trees(graphs) with depth > 2
                self.classes[name] = classinfo

        # tree-based propagation of 'isalgorithm'
        processed = dict()
        def process_isalgorithm(classinfo):
            if classinfo.isalgorithm or classinfo in processed:
                return classinfo.isalgorithm
            res = False
            if classinfo.base:
                res = process_isalgorithm(self.classes[classinfo.base])
                #assert not (res == True or classinfo.isalgorithm is False), "Internal error: " + classinfo.name + " => " + classinfo.base
                classinfo.isalgorithm |= res
                res = classinfo.isalgorithm
            processed[classinfo] = True
            return res
        for name, classinfo in self.classes.items():
            process_isalgorithm(classinfo)

        # step 2: generate code for the classes and their methods
        classlist = list(self.classes.items())
        classlist.sort()
        for name, classinfo in classlist:
            if classinfo.ismap:
                self.code_types.write(gen_template_map_type_cvt.substitute(modulePrefix=modulePrefix,name=name, cname=classinfo.cname))
            else:
                if classinfo.issimple:
                    templ = gen_template_simple_type_decl
                else:
                    templ = gen_template_type_decl
                self.code_types.write(templ.substitute(modulePrefix=modulePrefix,name=name, wname=classinfo.wname, cname=classinfo.cname, sname=classinfo.sname,
                                      cname1=("cv::Algorithm" if classinfo.isalgorithm else classinfo.cname)))

        # register classes in the same order as they have been declared.
        # this way, base classes will be registered in Python before their derivatives.
        classlist1 = [(classinfo.decl_idx, name, classinfo) for name, classinfo in classlist]
        classlist1.sort()

        for decl_idx, name, classinfo in classlist1:
            code = classinfo.gen_code(self)
            self.code_types.write(code)
            if not classinfo.ismap:
                self.code_type_reg.write("MKTYPE2(%s);\n" % (classinfo.name,) )
                self.code_type_publish.write("PUBLISH_OBJECT(\"{name}\", {modulePrefix}_{name}_Type);\n".format(name=classinfo.name,modulePrefix=modulePrefix))

        # step 3: generate the code for all the global functions
        for ns_name, ns in sorted(self.namespaces.items()):
            #Chandra disabled
            #if ns_name.split('.')[0] != 'cv':
            #    continue
            for name, func in sorted(ns.funcs.items()):
                if func.isconstructor:
                    continue
                code = func.gen_code(self)
                self.code_funcs.write(code)
            self.gen_namespace(ns_name)
        self.gen_namespaces_reg()

        # step 4: generate the code for constants
        constlist = list(self.consts.items())
        constlist.sort()
        for name, constinfo in constlist:
            self.gen_const_reg(constinfo)

        # That's it. Now save all the files
        self.save(output_path, modulePrefix + "_generated_include.h", self.code_include)
        self.save(output_path, modulePrefix + "_generated_funcs.h", self.code_funcs)
        self.save(output_path, modulePrefix + "_generated_types.h", self.code_types)
        self.save(output_path, modulePrefix + "_generated_type_reg.h", self.code_type_reg)
        self.save(output_path, modulePrefix + "_generated_ns_reg.h", self.code_ns_reg)
        self.save(output_path, modulePrefix + "_generated_type_publish.h", self.code_type_publish)
        self.save_json(output_path, modulePrefix + "_signatures.json", self.py_signatures)


if __name__ == "__main__":
    srcfiles = hdr_parser.opencv_hdr_list
    dstdir = "/tmp/"
    modulePrefix="pyopencv"
    if len(sys.argv) > 1:
        modulePrefix = sys.argv[1]
    if len(sys.argv) > 2:
        dstdir = sys.argv[2]
    if len(sys.argv) > 3:
        srcfiles = [f.strip() for f in open(sys.argv[3], 'r').readlines()]
    generator = PythonWrapperGenerator()
    generator.gen(srcfiles, dstdir)
