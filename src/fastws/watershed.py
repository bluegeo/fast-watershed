from typing import Union, Tuple

import numpy as np
from numba import njit
from numba.types import boolean

from fastws.raster import Raster


@njit
def find_stream_task(stream, fd, i, j):
    directions = [
        [0, 0],
        [-1, 1],
        [-1, 0],
        [-1, -1],
        [0, -1],
        [1, -1],
        [1, 0],
        [1, 1],
        [0, 1],
    ]

    found = False

    while True:
        if stream[i, j]:
            found = True
            break

        # Off map
        if fd[i, j] <= 0:
            break

        # Collect the downstream cell
        i_offset, j_offset = directions[fd[i, j]]
        i += i_offset
        j += j_offset

        if i < 0 or i >= fd.shape[0] or j < 0 or j >= fd.shape[1]:
            break

    return found, i, j


@njit
def delineate_task(fd: np.ndarray, i: int, j: int) -> Tuple[list, list]:
    """Delineate a watershed above a point.

    Args:
        fd (np.ndarray): 2D flow direction array derived from GRASS GIS.
        i (int): i (y) index.
        j (int): j (x) index.

    Returns:
        Tuple[list, list]: Lists of both watershed boundary cells, and cells that remain
        untested.
    """
    directions = [[7, 6, 5], [8, 0, 4], [1, 2, 3]]
    nbrs = [[-1, -1], [-1, 0], [-1, 1], [0, -1], [0, 1], [1, -1], [1, 0], [1, 1]]

    stack = [[i, j]]
    basin = [[i, j]]
    edges = []

    while len(stack) > 0:
        i, j = stack.pop()
        
        if i == 0 or j == 0 or i == fd.shape[0] - 1 or j == fd.shape[1] - 1:
            # Edge holds the target element, followed by those that need to be evaluated
            edge = [[i, j], []]
            for row_offset, col_offset in nbrs:
                edge[1].append(i + row_offset, j + col_offset)
            edges.append(edge)
            continue

        for row_offset, col_offset in nbrs:
            t_i, t_j = i + row_offset, j + col_offset

            # Flow off map
            if fd[t_i, t_j] <= 0:
                continue

            # Check if the element at this offset contributes to the element being tested
            if fd[t_i, t_j] == directions[row_offset + 1][col_offset + 1]:
                basin.append([i, j])
                stack.append([i, j])
    
    return basin, edges


def find_stream(streams: Raster, fd: Raster, x: float, y: float) -> Tuple[float, float]:
    """Search for the nearest stream cell and return the central coordinate.

    Args:
        streams (Raster): Raster source of stream data.
        fd (Raster): Raster source of flow direction data.
        x (float): x-coordinate.
        y (float): y-coordinate.

    Returns:
        Tuple[float, float]: (x, y) coordinates that intersect a stream.
    """
    window, i, j = fd.intersecting_window(x, y)

    stream_data = streams[window] != streams.nodata
    fd_data = fd[window]

    if fd_data[i, j] == fd.nodata or fd_data[i, j] <= 0:
        raise ValueError(f"The point ({x}, {y}) is out of bounds")

    found, i, j = find_stream_task(stream_data, fd_data, i, j)
    while not found:
        try:
            window, i, j = fd.intersecting_window(
                *fd.xy_from_window_index(i, j, window)
            )
        except IndexError:
            raise ValueError(f"No streams found near the point ({x}, {y})")

        found, i, j = find_stream_task(
            streams[window] != streams.nodata, fd[window], i, j
        )

    return fd.xy_from_window_index(i, j, window)


def delineate(
    stream_src: str, fd_src: str, x: float, y: float, xy_srs: Union[str, int]
) -> list:
    with Raster(fd_src) as fd, Raster(stream_src) as streams:
        if not fd.matches(streams):
            raise ValueError("Input Stream and Flow Direction rasters must match")

        # Align the point with the grids and move downslope to a stream
        x_transformed, y_transformed = fd.match_point(x, y, xy_srs)
        x_onstream, y_onstream = find_stream(streams, fd, x_transformed, y_transformed)

        coverage = np.zeros(fd.shape, bool)

        def next_window(x, y):
            window, i, j = fd.intersecting_window(x, y)
            coverage[fd.window_idx_to_global([[i, j]], window)] = True
            new_coverage, edges = delineate_task(fd[window], i, j)
            coverage[fd.window_idx_to_global(new_coverage, window)] = True

            return [fd.xy_from_window_index(i, j, window) for i, j in edges]

        edges = next_window(x_onstream, y_onstream)

        while len(edges) > 0:
            next_window(*edges.pop())

        # Create a vector
        # driver = gdal.GetDriverByName("MEM")
        # ds = driver.create("name", fd.shape[1], fd.shape[0], 1, gdal.GDT_Byte)
        # ds.SetGeoTransform(fd.geotransform)

        # srs = osr.SpatialReference()
        # srs.ImportFromEPSG(self.srid)
        # raster.SetProjection(srs.ExportToWkt())

        # band = ds.GetRasterBand(1)
        # band.SetNoDataValue(0)
        # band.WriteArray(coverage.astype("uint8"))
        # band.FlushCache()
        # band = None
        # ds.FlushCache()
        # gdal_polygonize(ds, in_memory_vector)
        # watershed_geojson = in_memory_vector.read()

        return x_onstream, y_onstream, watershed_geojson
