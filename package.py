# -*- coding: utf-8 -*-
name = "usd"
version = "25.11"
authors = ["Pixar Animation Studios"]
description = "Universal Scene Description (OpenUSD) with Arnold plugin support"

variants = [
    ["python-3.11", "arnold-7.4.2.0"],
    ["python-3.12", "arnold-7.4.2.0"],
    ["python-3.13", "arnold-7.4.2.0"],
]

requires = [
    "boost-1.85.0",
    "tbb-2022.2.0",
    "openexr-3.3.3",
    "imath-3.2.0",
    "oiio-3.0.3.0",
    "materialx-1.39.3",
    "opensubdiv-3.6.1",
    "openvdb-13.0.0",
    "alembic-1.8.7",
    "ptex-2.4.2",
    "pyside6-6.9.1",
    "jinja2-3.1.2",
    "pyopengl-3.1.9",
    "libjpeg-3.0.2",
    "qt-6.9.1",
]

build_requires = [
    "cmake-3.26.5",
    "gcc-11.5.0",
    "ninja-1.11.1",
]

tools = [
    "usdcat",
    "usdedit",
    "usdview",
    "usdrecord",
    "usdresolve",
    "usdtree",
    "usdchecker",
    "usdGenSchema",
]

build_command = "python {root}/rezbuild.py {install}"

def commands():
    env.USD_ROOT = "{root}"
    env.PXR_USD_LOCATION = "{root}"
    env.CMAKE_PREFIX_PATH.prepend("{root}")
    env.PATH.prepend("{root}/bin")
    env.LD_LIBRARY_PATH.prepend("{root}/lib")
    env.LIBRARY_PATH.prepend("{root}/lib")
    env.CPATH.prepend("{root}/include")
    env.PKG_CONFIG_PATH.prepend("{root}/lib/pkgconfig")
    env.PYTHONPATH.prepend("{root}/lib/python")
    env.PXR_PLUGINPATH_NAME.prepend("{root}/lib/usd")
