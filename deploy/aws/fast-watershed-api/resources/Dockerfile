FROM lambci/lambda:build-python3.8

WORKDIR /var/task
ENV WORKDIR /var/task

RUN mkdir -p packages \
    && pip install -t packages/ \
    rasterio \
    pyproj \
    numpy \
    numba

# Copy python library and install
COPY fastws packages/fastws
COPY setup.py packages/
RUN cd packages \
    && pip install --upgrade -t ${WORKDIR}/packages/ .

# Clean up
RUN cd packages \
    && rm -f setup.py \
    && rm -rf numba* \
    && rm -rf llvmlite*

COPY deploy/aws/fast-watershed-api/resources/delineate.py "$WORKDIR/"

RUN cd ${WORKDIR}/packages && zip -r9 -D ${WORKDIR}/package.zip ./* ../delineate.py
