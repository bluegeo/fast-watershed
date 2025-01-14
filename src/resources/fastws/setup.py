from setuptools import setup

from fastws.aot import cc

if __name__ == "__main__":
    cc.compile()
    setup(
        name="fast-watershed",
        version="1.0",
        description="Quickly and efficiently delineate watersheds",
        author="bluegeo",
        author_email="devin.cairns@bluegeo.ca",
        url="https://github.com/bluegeo/fast-watershed",
        packages=["fastws"],
        ext_modules=[cc.distutils_extension()],
    )
