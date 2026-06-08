from pathlib import Path

from setuptools import setup

from aot import cc


def read_version() -> str:
    namespace = {}
    init_path = Path(__file__).parent / "src" / "fastws" / "__init__.py"
    exec(init_path.read_text(), namespace)
    return namespace["__version__"]


if __name__ == "__main__":
    cc.compile()

    setup(
        name="fastws",
        version=read_version(),
        description="Quickly and efficiently delineate watersheds",
        author="bluegeo",
        author_email="devin.cairns@bluegeo.ca",
        url="https://github.com/bluegeo/fast-watershed",
        packages=["fastws"],
        package_dir={"": "src"},
        ext_modules=[cc.distutils_extension()],
        install_requires=["numpy", "fiona", "rasterio", "shapely", "pyproj"],
    )
