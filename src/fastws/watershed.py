from typing import Union, Tuple

from numba import njit

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
def delineate_task():
    pass


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
        window, i, j = fd.intersecting_window(*fd.xy_from_window_index(i, j, window))
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

        x_transformed, y_transformed = fd.match_point(x, y, xy_srs)
        x_onstream, y_onstream = find_stream(streams, fd, x_transformed, y_transformed)

        return x_onstream, y_onstream
