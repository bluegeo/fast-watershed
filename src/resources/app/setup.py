from setuptools import setup, find_namespace_packages

from aot import cc


if __name__ == "__main__":
    cc.compile()
    
    setup(
        name="fastws",
        version="1.0",
        description="Quickly and efficiently delineate watersheds",
        author="bluegeo",
        author_email="devin.cairns@bluegeo.ca",
        url="https://github.com/bluegeo/fast-watershed",
        packages=find_namespace_packages(),
        ext_modules=[cc.distutils_extension()],
        install_requires=["numpy", "rasterio", "shapely", "pyproj"]
    )
