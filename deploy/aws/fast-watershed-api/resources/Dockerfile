FROM lambci/lambda:build-python3.8

WORKDIR /var/task
ENV WORKDIR /var/task

# Necessary packages here
RUN mkdir -p packages/ && \
    pip3 install \
    rasterio \
    pyproj \
    numpy \
    numba \
    git+https://github.com/bluegeo/fast-watershed.git \
    -t packages/

COPY delineate.py "$WORKDIR/"

RUN zip -r9 -D $WORKDIR/package.zip packages/ delineate.py
