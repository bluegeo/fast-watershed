FROM ghcr.io/lambgeo/lambda-gdal:3.5-python3.9

ENV PACKAGE_PREFIX=/var/task

# Copy any local files to the package
COPY handler.py ${PACKAGE_PREFIX}/handler.py

# Install some requirements to `/var/task` (using `-t` otpion)
RUN pip install numpy rasterio mercantile --no-binary :all: -t ${PACKAGE_PREFIX}/

# Reduce size of the C libs
RUN cd $PREFIX && find lib -name \*.so\* -exec strip {} \;

# Create package.zip
# Archive python code (installed in $PACKAGE_PREFIX/)
RUN cd $PACKAGE_PREFIX && zip -r9q /tmp/package.zip *

# Archive GDAL libs (in $PREFIX/lib $PREFIX/bin $PREFIX/share)
RUN cd $PREFIX && zip -r9q --symlinks /tmp/package.zip lib/*.so* share
RUN cd $PREFIX && zip -r9q --symlinks /tmp/package.zip bin/gdal* bin/ogr* bin/geos* bin/nearblack