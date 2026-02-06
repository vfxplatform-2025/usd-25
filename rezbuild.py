# -*- coding: utf-8 -*-
"""
usd 25.11 rezbuild.py - OpenUSD CMake direct build
build_usd.py 대신 CMake 직접 빌드로 rez 패키지 의존성만 사용
"""
import os
import sys
import shutil
import subprocess
import multiprocessing


def run_cmd(cmd, cwd=None, env=None):
    """명령 실행"""
    print(f"[RUN] {cmd}  (cwd={cwd})")
    subprocess.run(
        ["bash", "-lc", cmd],
        cwd=cwd,
        env=env,
        check=True,
    )


def clean_build_dir(path):
    """빌드 디렉토리 클린업 (*.rxt, variant.json 보존)"""
    if os.path.isdir(path):
        print(f"Cleaning build directory (preserving .rxt/.json): {path}")
        for item in os.listdir(path):
            if item.endswith(".rxt") or item == "variant.json":
                continue
            full = os.path.join(path, item)
            if os.path.isdir(full):
                shutil.rmtree(full)
            else:
                os.remove(full)


def clean_install_dir(path):
    """설치 디렉토리 제거"""
    if os.path.isdir(path):
        print(f"Removing install directory: {path}")
        shutil.rmtree(path)


def _patch_file(filepath, replacements):
    """파일에서 문자열 치환 (이미 패치된 경우 자동 건너뜀)"""
    if not os.path.isfile(filepath):
        print(f"  SKIP (not found): {filepath}")
        return
    with open(filepath, "r") as f:
        content = f.read()
    original = content
    for old, new in replacements:
        if old not in content:
            continue
        if new and new in content:
            continue  # 이미 패치됨
        content = content.replace(old, new, 1)
    if content != original:
        with open(filepath, "w") as f:
            f.write(content)
        print(f"  PATCHED: {filepath}")
    else:
        print(f"  OK (already patched): {filepath}")


def patch_usd_metal_msl(src_dir):
    """Linux에서 MaterialXGenMsl (Metal Shading Language) 빌드 비활성화 패치.
    USD 25.11 버그: hdSt가 PXR_ENABLE_METAL_SUPPORT 확인 없이 MSL 코드를 빌드.
    이미 존재하는 PXR_METAL_SUPPORT_ENABLED 매크로로 #ifdef 가드 추가.
    향후 USD 버전에서 수정되면 이 함수는 자동으로 no-op."""

    import platform
    if platform.system() == "Darwin":
        print("=== macOS: MaterialXGenMsl patch not needed ===")
        return

    print("=== Patching USD source: disable MaterialXGenMsl on Linux ===")
    hdst = os.path.join(src_dir, "pxr", "imaging", "hdSt")

    # 1. CMakeLists.txt — MaterialXGenMsl 링크 제거
    _patch_file(os.path.join(hdst, "CMakeLists.txt"), [
        ("        MaterialXGenMsl\n", ""),
    ])

    # 2. materialXShaderGen.h — MSL include와 class를 #ifdef 가드
    _patch_file(os.path.join(hdst, "materialXShaderGen.h"), [
        # MSL include 가드
        ('#include <MaterialXGenMsl/MslShaderGenerator.h>\n',
         '#ifdef PXR_METAL_SUPPORT_ENABLED\n#include <MaterialXGenMsl/MslShaderGenerator.h>\n#endif\n'),
        # MSL class 시작 가드
        ('/// \\class HdStMaterialXShaderGenMsl\n',
         '#ifdef PXR_METAL_SUPPORT_ENABLED\n/// \\class HdStMaterialXShaderGenMsl\n'),
        # MSL class 끝 가드 (helper namespace 직전)
        ('// Helper functions to aid building both MaterialX 1.38.X and 1.39.X\n',
         '#endif // PXR_METAL_SUPPORT_ENABLED\n\n// Helper functions to aid building both MaterialX 1.38.X and 1.39.X\n'),
    ])

    # 3. materialXShaderGen.cpp — MSL include, TARGET 참조, MSL 섹션을 #ifdef 가드
    _patch_file(os.path.join(hdst, "materialXShaderGen.cpp"), [
        # MSL includes 가드 (3줄 묶음)
        ('#include <MaterialXGenMsl/Nodes/SurfaceNodeMsl.h>\n'
         '#include <MaterialXGenMsl/MslResourceBindingContext.h>\n'
         '#include <MaterialXGenMsl/MslShaderGenerator.h>\n',
         '#ifdef PXR_METAL_SUPPORT_ENABLED\n'
         '#include <MaterialXGenMsl/Nodes/SurfaceNodeMsl.h>\n'
         '#include <MaterialXGenMsl/MslResourceBindingContext.h>\n'
         '#include <MaterialXGenMsl/MslShaderGenerator.h>\n'
         '#endif\n'),
        # _EmitMxVertexDataDeclarations 내 MSL TARGET 참조 가드 (여는 괄호)
        ('    else if (targetShadingLanguage == mx::MslShaderGenerator::TARGET) {\n'
         '        line += "{";\n'
         '    }\n',
         '#ifdef PXR_METAL_SUPPORT_ENABLED\n'
         '    else if (targetShadingLanguage == mx::MslShaderGenerator::TARGET) {\n'
         '        line += "{";\n'
         '    }\n'
         '#endif\n'),
        # _EmitMxVertexDataDeclarations 내 MSL TARGET 참조 가드 (닫는 괄호)
        ('    else if (targetShadingLanguage == mx::MslShaderGenerator::TARGET) {\n'
         '        line += "}";\n'
         '    }\n',
         '#ifdef PXR_METAL_SUPPORT_ENABLED\n'
         '    else if (targetShadingLanguage == mx::MslShaderGenerator::TARGET) {\n'
         '        line += "}";\n'
         '    }\n'
         '#endif\n'),
        # MSL 섹션 전체 가드 시작
        ('// ----------------------------------------------------------------------------\n'
         '//                          HdSt MaterialX ShaderGen Metal\n'
         '// ----------------------------------------------------------------------------\n',
         '#ifdef PXR_METAL_SUPPORT_ENABLED\n'
         '// ----------------------------------------------------------------------------\n'
         '//                          HdSt MaterialX ShaderGen Metal\n'
         '// ----------------------------------------------------------------------------\n'),
        # MSL 섹션 전체 가드 끝 (helper functions 직전)
        ('\n\n// Helper functions to aid building both MaterialX 1.38.X and 1.39.X\n',
         '\n#endif // PXR_METAL_SUPPORT_ENABLED\n\n// Helper functions to aid building both MaterialX 1.38.X and 1.39.X\n'),
    ])

    # 4. materialXFilter.cpp — HdStMaterialXShaderGenMsl 참조 가드
    _patch_file(os.path.join(hdst, "materialXFilter.cpp"), [
        ('    if (apiName == HgiTokens->Metal) {\n'
         '        return HdStMaterialXShaderGenMsl::create(mxHdInfo);\n'
         '    }\n',
         '#ifdef PXR_METAL_SUPPORT_ENABLED\n'
         '    if (apiName == HgiTokens->Metal) {\n'
         '        return HdStMaterialXShaderGenMsl::create(mxHdInfo);\n'
         '    }\n'
         '#endif\n'),
    ])


def build(source_path, build_path, install_path_env, targets):
    name = os.environ.get("REZ_BUILD_PROJECT_NAME", "usd")
    version = os.environ.get("REZ_BUILD_PROJECT_VERSION")
    if not version:
        sys.exit("REZ_BUILD_PROJECT_VERSION not set")

    # Python 버전 (rez variant가 제공)
    py_major = os.environ.get("REZ_PYTHON_MAJOR_VERSION", "3")
    py_minor = os.environ.get("REZ_PYTHON_MINOR_VERSION", "11")
    py_version = f"{py_major}.{py_minor}"
    print(f"Building USD {version} for Python {py_version}")

    # Python executable
    python_root = os.environ.get("REZ_PYTHON_ROOT", "")
    python_exe = os.path.join(python_root, "bin", f"python{py_version}") if python_root else ""
    if not python_exe or not os.path.exists(python_exe):
        python_exe = os.path.join(python_root, "bin", "python3") if python_root else ""
    if not python_exe or not os.path.exists(python_exe):
        python_exe = shutil.which("python3") or sys.executable
        print(f"Warning: Rez Python not found, using: {python_exe}")
    else:
        print(f"Using Python: {python_exe}")

    # Python library / include 탐색
    python_lib = ""
    python_include = ""
    if python_root:
        for libname in (f"libpython{py_version}.so", f"libpython{py_version}m.so"):
            candidate = os.path.join(python_root, "lib", libname)
            if os.path.exists(candidate):
                python_lib = candidate
                break
        for incdir in (f"python{py_version}", f"python{py_version}m"):
            candidate = os.path.join(python_root, "include", incdir)
            if os.path.isdir(candidate):
                python_include = candidate
                break

    # variant subpath
    variant_subpath = os.environ.get("REZ_BUILD_VARIANT_SUBPATH", "")

    # 소스 디렉토리
    src_dir = os.path.join(source_path, "source", f"OpenUSD-{version}")
    if not os.path.isdir(src_dir):
        raise FileNotFoundError(f"Source not found: {src_dir}")

    # 빌드/설치 디렉토리 준비
    clean_build_dir(build_path)
    os.makedirs(build_path, exist_ok=True)

    install_root = install_path_env
    if "install" in targets:
        install_root = f"/core/Linux/APPZ/packages/{name}/{version}/{variant_subpath}"
        clean_install_dir(install_root)
        os.makedirs(install_root, exist_ok=True)

    # === REZ 의존 패키지 경로 수집 ===
    boost_root = os.environ.get("REZ_BOOST_ROOT", "")
    tbb_root = os.environ.get("REZ_TBB_ROOT", "")
    openexr_root = os.environ.get("REZ_OPENEXR_ROOT", "")
    imath_root = os.environ.get("REZ_IMATH_ROOT", "")
    oiio_root = os.environ.get("REZ_OIIO_ROOT", "")
    ocio_root = os.environ.get("REZ_OCIO_ROOT", "")
    materialx_root = os.environ.get("REZ_MATERIALX_ROOT", "")
    opensubdiv_root = os.environ.get("REZ_OPENSUBDIV_ROOT", "")
    openvdb_root = os.environ.get("REZ_OPENVDB_ROOT", "")
    alembic_root = os.environ.get("REZ_ALEMBIC_ROOT", "")
    ptex_root = os.environ.get("REZ_PTEX_ROOT", "")
    pyside6_root = os.environ.get("REZ_PYSIDE6_ROOT", "")
    qt_root = os.environ.get("REZ_QT_ROOT", "")
    jinja2_root = os.environ.get("REZ_JINJA2_ROOT", "")
    pyopengl_root = os.environ.get("REZ_PYOPENGL_ROOT", "")
    libjpeg_root = os.environ.get("REZ_LIBJPEG_ROOT", "")
    arnold_root = os.environ.get("REZ_ARNOLD_ROOT", "")
    gcc_root = os.environ.get("REZ_GCC_ROOT", "")
    cmake_root = os.environ.get("REZ_CMAKE_ROOT", "")
    ninja_root = os.environ.get("REZ_NINJA_ROOT", "")

    print("=== Dependency roots ===")
    for var_name in ["BOOST", "TBB", "OPENEXR", "IMATH", "OIIO", "OCIO",
                     "MATERIALX", "OPENSUBDIV", "OPENVDB", "ALEMBIC", "PTEX",
                     "PYSIDE6", "QT", "ARNOLD", "PYTHON"]:
        val = os.environ.get(f"REZ_{var_name}_ROOT", "(not set)")
        print(f"  REZ_{var_name}_ROOT = {val}")

    # === 소스 패치 (Linux Metal/MSL 비활성화) ===
    patch_usd_metal_msl(src_dir)

    # === CMAKE_PREFIX_PATH 구성 ===
    dep_env_vars = [
        "REZ_BOOST_ROOT",
        "REZ_TBB_ROOT",
        "REZ_OPENEXR_ROOT",
        "REZ_IMATH_ROOT",
        "REZ_OIIO_ROOT",
        "REZ_OCIO_ROOT",
        "REZ_MATERIALX_ROOT",
        "REZ_OPENSUBDIV_ROOT",
        "REZ_OPENVDB_ROOT",
        "REZ_ALEMBIC_ROOT",
        "REZ_PTEX_ROOT",
        "REZ_PYSIDE6_ROOT",
        "REZ_QT_ROOT",
        "REZ_LIBJPEG_ROOT",
        "REZ_PYTHON_ROOT",
    ]
    prefix_paths = [os.environ.get(v, "") for v in dep_env_vars if os.environ.get(v)]
    cmake_prefix = ";".join(prefix_paths)

    # === 개별 CMake 의존성 경로 변수 ===

    # TBB: Find + CONFIG 모드
    tbb_cmake_dir = ""
    if tbb_root:
        for libdir in ("lib/cmake/tbb", "lib64/cmake/tbb", "lib/cmake/TBB"):
            candidate = os.path.join(tbb_root, libdir)
            if os.path.isdir(candidate):
                tbb_cmake_dir = candidate
                break

    # Imath: CONFIG 모드
    imath_cmake_dir = ""
    if imath_root:
        for libdir in ("lib/cmake/Imath", "lib64/cmake/Imath"):
            candidate = os.path.join(imath_root, libdir)
            if os.path.isdir(candidate):
                imath_cmake_dir = candidate
                break

    # MaterialX: CONFIG 모드
    materialx_cmake_dir = ""
    if materialx_root:
        for libdir in ("lib/cmake/MaterialX", "lib64/cmake/MaterialX"):
            candidate = os.path.join(materialx_root, libdir)
            if os.path.isdir(candidate):
                materialx_cmake_dir = candidate
                break

    # Qt6: CONFIG 모드
    qt6_cmake_dir = ""
    if qt_root:
        for libdir in ("lib/cmake/Qt6", "lib64/cmake/Qt6"):
            candidate = os.path.join(qt_root, libdir)
            if os.path.isdir(candidate):
                qt6_cmake_dir = candidate
                break

    # === CMake 구성 인자 ===
    cmake_args = [
        f"cmake {src_dir}",
        f"-DCMAKE_INSTALL_PREFIX={install_root}",
        "-DCMAKE_BUILD_TYPE=Release",
        "-G Ninja",
        "-DBUILD_SHARED_LIBS=ON",
        f'-DCMAKE_PREFIX_PATH="{cmake_prefix}"',
        # PXR 빌드 플래그
        "-DPXR_BUILD_IMAGING=ON",
        "-DPXR_BUILD_USD_IMAGING=ON",
        "-DPXR_BUILD_USDVIEW=ON",
        "-DPXR_BUILD_OPENIMAGEIO_PLUGIN=ON",
        "-DPXR_BUILD_OPENCOLORIO_PLUGIN=ON",
        "-DPXR_ENABLE_MATERIALX_SUPPORT=ON",
        "-DPXR_ENABLE_OPENVDB_SUPPORT=ON",
        "-DPXR_ENABLE_PTEX_SUPPORT=ON",
        "-DPXR_BUILD_ALEMBIC_PLUGIN=ON",
        "-DPXR_BUILD_DRACO_PLUGIN=OFF",
        "-DPXR_BUILD_TESTS=OFF",
        "-DPXR_BUILD_EXAMPLES=OFF",
        "-DPXR_BUILD_TUTORIALS=OFF",
        "-DPXR_BUILD_USD_TOOLS=ON",
        "-DPXR_ENABLE_PYTHON_SUPPORT=ON",
    ]

    # Python 경로
    cmake_args.append(f"-DPython3_EXECUTABLE={python_exe}")
    if python_lib:
        cmake_args.append(f"-DPython3_LIBRARY={python_lib}")
    if python_include:
        cmake_args.append(f"-DPython3_INCLUDE_DIR={python_include}")

    # 의존성 개별 경로 변수
    if boost_root:
        cmake_args.append(f"-DBoost_ROOT={boost_root}")
    if tbb_root:
        cmake_args.append(f"-DTBB_ROOT_DIR={tbb_root}")
    if tbb_cmake_dir:
        cmake_args.append(f"-DTbb_DIR={tbb_cmake_dir}")
    if imath_cmake_dir:
        cmake_args.append(f"-DImath_DIR={imath_cmake_dir}")
    if opensubdiv_root:
        cmake_args.append(f"-DOPENSUBDIV_ROOT_DIR={opensubdiv_root}")
    if oiio_root:
        cmake_args.append(f"-DOIIO_LOCATION={oiio_root}")
    if ocio_root:
        cmake_args.append(f"-DOCIO_LOCATION={ocio_root}")
    if materialx_cmake_dir:
        cmake_args.append(f"-DMaterialX_DIR={materialx_cmake_dir}")
    if openvdb_root:
        cmake_args.append(f"-DOPENVDB_LOCATION={openvdb_root}")
    if alembic_root:
        cmake_args.append(f"-DALEMBIC_DIR={alembic_root}")
    if ptex_root:
        cmake_args.append(f"-DPTEX_LOCATION={ptex_root}")
    if libjpeg_root:
        cmake_args.append(f"-DJPEG_ROOT={libjpeg_root}")
    if qt6_cmake_dir:
        cmake_args.append(f"-DQt6_DIR={qt6_cmake_dir}")

    # === 환경 설정 ===
    env = os.environ.copy()

    # GCC
    gcc_bin = ""
    if gcc_root:
        gcc_bin = os.path.join(gcc_root, "bin")
        if not os.path.isdir(gcc_bin):
            gcc_bin = os.path.join(gcc_root, "platform_linux", "bin")
        env["CC"] = os.path.join(gcc_bin, "gcc")
        env["CXX"] = os.path.join(gcc_bin, "g++")

    # PATH: cmake, gcc, ninja, python, pyside6 순서
    path_prepend = []
    if cmake_root:
        path_prepend.append(os.path.join(cmake_root, "bin"))
    if gcc_bin:
        path_prepend.append(gcc_bin)
    if ninja_root:
        path_prepend.append(os.path.join(ninja_root, "bin"))
    if python_root:
        path_prepend.append(os.path.join(python_root, "bin"))
    if pyside6_root:
        path_prepend.append(os.path.join(pyside6_root, "bin"))
    if path_prepend:
        env["PATH"] = ":".join(path_prepend) + ":" + env.get("PATH", "")

    # PYTHONPATH: pyside6, pyopengl, jinja2 site-packages
    py_paths = []
    if pyside6_root:
        py_paths.append(os.path.join(pyside6_root, "lib", f"python{py_version}", "site-packages"))
    if pyopengl_root:
        py_paths.append(pyopengl_root)
    if jinja2_root:
        py_paths.append(os.path.join(jinja2_root, "lib", f"python{py_version}", "site-packages"))
    if py_paths:
        env["PYTHONPATH"] = ":".join(py_paths)

    # LD_LIBRARY_PATH
    ld_paths = []
    if qt_root:
        ld_paths.append(os.path.join(qt_root, "lib"))
    if tbb_root:
        tbb_lib = os.path.join(tbb_root, "lib64")
        if not os.path.isdir(tbb_lib):
            tbb_lib = os.path.join(tbb_root, "lib")
        ld_paths.append(tbb_lib)
    if opensubdiv_root:
        ld_paths.append(os.path.join(opensubdiv_root, "lib"))
    if ld_paths:
        env["LD_LIBRARY_PATH"] = ":".join(ld_paths) + ":" + env.get("LD_LIBRARY_PATH", "")

    # TBB 환경변수
    if tbb_root:
        env["TBB_ROOT"] = tbb_root

    # === CMake Configure → Build → Install ===
    print("=== USD CMake configure ===")
    cmd_str = " ".join(cmake_args)
    print(f"CMake args ({len(cmake_args)}):")
    for i, arg in enumerate(cmake_args):
        print(f"  [{i}] {arg}")

    run_cmd(cmd_str, cwd=build_path, env=env)

    print("=== USD CMake build ===")
    run_cmd(f"cmake --build . --parallel {multiprocessing.cpu_count()}", cwd=build_path, env=env)

    if "install" in targets:
        print("=== USD CMake install ===")
        run_cmd("cmake --install .", cwd=build_path, env=env)

    print(f"USD {version} build completed successfully")

    # === Arnold USD 플러그인 빌드 (선택) ===
    arnold_usd_src = os.path.join(source_path, "source", "arnold-usd")
    if arnold_root and os.path.isdir(arnold_usd_src):
        print("=== Arnold USD plugin build ===")
        build_arnold_usd(arnold_usd_src, build_path, install_root, env, arnold_root)
    else:
        print("Arnold USD source not found, skipping Arnold plugin build")

    # === 설치 후처리 ===
    if "install" in targets:
        # package.py 복사 (버전 루트에 1개)
        server_base = f"/core/Linux/APPZ/packages/{name}/{version}"
        os.makedirs(server_base, exist_ok=True)
        dst_pkg = os.path.join(server_base, "package.py")
        print(f"Copying package.py -> {dst_pkg}")
        shutil.copy(os.path.join(source_path, "package.py"), dst_pkg)

        # 빌드 마커
        marker = os.path.join(build_path, "build.rxt")
        open(marker, "a").close()

    print(f"usd-{version} (Python {py_version}) build/install complete: {install_root}")


def build_arnold_usd(arnold_usd_src, build_path, install_root, env, arnold_root):
    """Arnold USD 플러그인 빌드"""
    arnold_usd_build = os.path.join(build_path, "arnold-usd")
    os.makedirs(arnold_usd_build, exist_ok=True)

    cmake_root = os.environ.get("REZ_CMAKE_ROOT", "")
    cmake_bin = os.path.join(cmake_root, "bin", "cmake") if cmake_root else "cmake"

    cmake_args = [
        cmake_bin,
        arnold_usd_src,
        f"-DCMAKE_INSTALL_PREFIX={install_root}",
        f"-DUSD_ROOT={install_root}",
        f"-DARNOLD_ROOT={arnold_root}",
        f"-DARNOLD_BINARY_DIR={arnold_root}/bin",
        f"-DARNOLD_LIBRARY={arnold_root}/bin/libai.so",
        f"-DARNOLD_INCLUDE_DIR={arnold_root}/include",
        "-DCMAKE_BUILD_TYPE=Release",
        "-Wno-dev",
    ]

    print(f"Configuring Arnold USD: {' '.join(cmake_args)}")
    result = subprocess.run(cmake_args, cwd=arnold_usd_build, env=env)
    if result.returncode != 0:
        print("WARNING: Arnold USD cmake configure failed, skipping")
        return

    print("Building Arnold USD...")
    build_cmd = [cmake_bin, "--build", ".", "--parallel"]
    result = subprocess.run(build_cmd, cwd=arnold_usd_build, env=env)
    if result.returncode != 0:
        print("WARNING: Arnold USD build failed, skipping")
        return

    # 플러그인 설치
    install_cmd = [cmake_bin, "--install", "."]
    result = subprocess.run(install_cmd, cwd=arnold_usd_build, env=env)
    if result.returncode == 0:
        print("Arnold USD plugin installed successfully")
    else:
        print("WARNING: Arnold USD install failed")


if __name__ == "__main__":
    build(
        source_path=os.environ["REZ_BUILD_SOURCE_PATH"],
        build_path=os.environ["REZ_BUILD_PATH"],
        install_path_env=os.environ["REZ_BUILD_INSTALL_PATH"],
        targets=sys.argv[1:],
    )
