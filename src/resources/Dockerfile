ARG PYTHON_RUNTIME=3.12

FROM --platform=linux/amd64 public.ecr.aws/lambda/python:${PYTHON_RUNTIME} AS build

ENV PREFIX=$LAMBDA_TASK_ROOT

ENV \
    PYTHON_VERSION=3.12.5 \
    CMAKE_VESRION=3.30.3 \
    SQLITE3_VERSION=3460100 \
    OPENSSL_VERSION=1.1.1 \
    LIBTIFF_VERSION=4.6.0 \
    PROJ_VERSION=9.4.1 \
    LIBGEOTIFF_VERSION=1.7.3 \
    GEOS_VERSION=3.12.2 \
    GDAL_VERSION=3.9.2 \
    LD_LIBRARY_PATH=$PREFIX/lib:$LD_LIBRARY_PATH \
    PATH=$PREFIX/bin:$PATH

# Install build dependencies
RUN dnf install -y \
    perl \
    wget \
    libcurl-devel \
    tar \
    openssl-devel \
    bzip2-devel \
    libffi-devel \
    sqlite-devel \
    zlib-devel

# cmake
RUN cd /tmp \
    && wget https://cmake.org/files/v${CMAKE_VESRION%.*}/cmake-${CMAKE_VESRION}.tar.gz \
    && tar -xvzf cmake-$CMAKE_VESRION.tar.gz \
    && cd cmake-$CMAKE_VESRION \
    && ./bootstrap \
    && make -j$(nproc) --silent && make install

RUN mkdir $PREFIX/py \
    && pip install --upgrade pip && pip install numpy -t $PREFIX/py

# libtiff-4
RUN cd /tmp \
    && wget https://download.osgeo.org/libtiff/tiff-${LIBTIFF_VERSION}.tar.gz \
    && tar -xvf tiff-$LIBTIFF_VERSION.tar.gz \
    && cd tiff-$LIBTIFF_VERSION \
    && ./configure --prefix=$PREFIX \
    && make -j$(nproc) --silent \
    && make install

# PROJ
RUN cd /tmp \
    && wget https://download.osgeo.org/proj/proj-${PROJ_VERSION}.tar.gz \
    && tar -xvf proj-$PROJ_VERSION.tar.gz \
    && cd proj-$PROJ_VERSION \
    && mkdir build \
    && cd build \
    && cmake \
    -DCMAKE_INSTALL_PREFIX:PATH=$PREFIX \
    -DCMAKE_INSTALL_LIBDIR:PATH=lib \
    .. \
    && cmake --build . -- -j $(nproc)\
    && cmake --build . --target install

# libgeotiff
RUN cd /tmp \
    && wget https://github.com/OSGeo/libgeotiff/releases/download/${LIBGEOTIFF_VERSION}/libgeotiff-${LIBGEOTIFF_VERSION}.tar.gz \
    && tar -xvf libgeotiff-$LIBGEOTIFF_VERSION.tar.gz \
    && cd libgeotiff-$LIBGEOTIFF_VERSION \
    && ./configure \
    --prefix=$PREFIX \
    --with-proj=$PREFIX \
    --with-zip=yes \
    --with-zlib \
    --with-libtiff=$PREFIX \
    && make -j$(nproc) --silent && make install

# GEOS
RUN cd /tmp \
    && wget https://github.com/libgeos/geos/archive/refs/tags/${GEOS_VERSION}.tar.gz \
    && tar -xvf $GEOS_VERSION.tar.gz \
    && cd geos-$GEOS_VERSION \
    && mkdir build \
    && cd build \
    && cmake \
    -DCMAKE_INSTALL_PREFIX:PATH=$PREFIX \
    -DCMAKE_INSTALL_LIBDIR:PATH=lib \
    .. \
    && cmake --build . -- -j $(nproc) \
    && cmake --build . --target install

# GDAL
RUN cd /tmp \
    && wget https://github.com/OSGeo/gdal/releases/download/v${GDAL_VERSION}/gdal-${GDAL_VERSION}.tar.gz \
    && tar -xvf gdal-$GDAL_VERSION.tar.gz \
    && cd gdal-$GDAL_VERSION \
    && mkdir build \
    && cd build \
    && cmake \
    -DCMAKE_INSTALL_PREFIX:PATH=$PREFIX \
    -DCMAKE_INSTALL_LIBDIR:PATH=lib \
    -DPROJ_LIBRARY=$PREFIX/lib64/libproj.so \
    -DPROJ_INCLUDE_DIR=$PREFIX/include \
    -DGDAL_USE_TIFF_INTERNAL=OFF \
    -DGDAL_USE_GEOTIFF_INTERNAL=OFF \
    .. \
    && cmake --build . -- -j $(nproc) && cmake --build . --target install

# Copy python library and install
COPY fastws packages/fastws
COPY setup.py packages/
RUN cd packages \
    && pip install --upgrade -t $LAMBDA_TASK_ROOT/py

FROM --platform=linux/amd64 public.ecr.aws/lambda/python:${PYTHON_RUNTIME}

ENV PREFIX=$LAMBDA_TASK_ROOT

# Libs
# For rasterio
COPY --from=build /usr/lib64/libexpat.so.1 $PREFIX/lib/
COPY --from=build /usr/lib64/libexpat.so.1.8.10 $PREFIX/lib/

COPY --from=build $PREFIX/lib/ $PREFIX/lib/
COPY --from=build $PREFIX/include/ $PREFIX/include/
COPY --from=build $PREFIX/share/ $PREFIX/share/
COPY --from=build $PREFIX/bin/ $PREFIX/bin/
COPY --from=build $PREFIX/py $PREFIX/py

ENV \
    LD_LIBRARY_PATH=$PREFIX/lib:$LD_LIBRARY_PATH \
    PATH=$PREFIX/bin:$PREFIX:$PATH \
    PYTHONPATH=$PREFIX:$PREFIX/py \
    GDAL_DATA=$PREFIX/share/gdal \
    PROJ_DATA=$PREFIX/share/proj \
    GDAL_CONFIG=$PREFIX/bin/gdal-config \
    GEOS_CONFIG=$PREFIX/bin/geos-config

COPY handler.py ${LAMBDA_TASK_ROOT}/
CMD [ "handler.handler" ]
