from typing import Union, Tuple, List

import numpy as np
from numba import njit, typed
from rasterio.features import shapes
from pyproj import Transformer

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


@njit
def delineate_task(
    fd: np.ndarray, stack: List[List[int]]
) -> Tuple[List[List[int]], List[List[int]]]:
    """Delineate a watershed above a point. If a point out of bounds is encountered, the
    function will return with the element being evaluated and the location of the out
    of bounds element.

    Args:
        fd (np.ndarray): 2D flow direction array derived from GRASS GIS.
        stack (List[List[int]]): Indexes of elements to try and add to the
        watershed. Stack is mutated.

    Returns:
        Tuple[List[List[int]], List[List[int]]]: Lists of both watershed
        cells, and edges encountered.
    """
    directions = [[7, 6, 5], [8, 0, 4], [1, 2, 3]]
    nbrs = [[-1, -1], [-1, 0], [-1, 1], [0, -1], [0, 1], [1, -1], [1, 0], [1, 1]]

    basin = []
    edges = []

    while len(stack) > 0:
        i, j = stack.pop()

        for row_offset, col_offset in nbrs:
            t_i, t_j = i + row_offset, j + col_offset

            # Out of bounds?
            if t_i < 0 or t_j < 0 or t_i == fd.shape[0] or t_j == fd.shape[0]:
                edges.append([directions[row_offset + 1][col_offset + 1], t_i, t_j])
                continue

            # Flow off map
            if fd[t_i, t_j] <= 0:
                continue

            # Check if the element at this offset contributes to the element being
            # tested
            if fd[t_i, t_j] == directions[row_offset + 1][col_offset + 1]:
                stack.append(typed.List([t_i, t_j]))
                basin.append([t_i, t_j])

    return basin, edges


@njit
def array_to_typed_list(a: np.ndarray) -> typed.List:
    return typed.List([typed.List(e) for e in a])


def delineate(
    stream_src: str, fd_src: str, x: float, y: float, xy_srs: Union[str, int]
) -> list:
    with Raster(fd_src) as fd, Raster(stream_src) as streams:
        if not fd.matches(streams):
            raise ValueError("Input Stream and Flow Direction rasters must match")

        # Align the point with the grids and move downslope to a stream
        x_transformed, y_transformed = fd.match_point(x, y, xy_srs)
        x_onstream, y_onstream = find_stream(streams, fd, x_transformed, y_transformed)

        # Binary grid occupying the extent of the flow direction grid
        # TODO: Allocate output tile-by-tile to avoid memory overload
        coverage = np.zeros(fd.shape, bool)
        coverage[fd.coord_to_idx(x_onstream, y_onstream)] = True

        def next_delin(stack, window):
            data = fd[window]

            cov_idx, edges = delineate_task(data, stack[window])

            # Add new indices to coverage
            coverage[
                (
                    [i[0] + window.row_off for i in cov_idx],
                    [j[1] + window.col_off for j in cov_idx],
                )
            ] = True

            if len(edges) > 0:
                edges = np.asarray(edges)

                top_slice = edges[:, 1] < 0
                bottom_slice = edges[:, 1] == data.shape[0]
                left_slice = edges[:, 2] < 0
                right_slice = edges[:, 2] == data.shape[1]

                for bool_slice in (
                    top_slice & ~left_slice & ~right_slice,
                    bottom_slice & ~left_slice & ~right_slice,
                    left_slice & ~top_slice & ~bottom_slice,
                    right_slice & ~top_slice & ~bottom_slice,
                    top_slice & left_slice,
                    top_slice & right_slice,
                    bottom_slice & left_slice,
                    bottom_slice & right_slice,
                ):
                    if bool_slice.sum() > 0:
                        edge_subset = edges[bool_slice]
                        edge_i, edge_j = edge_subset[0, 1:]
                        try:
                            next_window, i, j = fd.intersecting_window(
                                *fd.xy_from_window_index(edge_i, edge_j, window)
                            )
                        except IndexError:
                            # Out of bounds
                            continue

                        # Align the edge locations with the next window and add
                        # contributing locations to the respective window stack
                        edge_subset[:, 1] += i - edge_i
                        edge_subset[:, 2] += j - edge_j

                        edge_subset = array_to_typed_list(
                            edge_subset[
                                fd[next_window][(edge_subset[:, 1], edge_subset[:, 2])]
                                == edge_subset[:, 0]
                            ][:, 1:]
                        )
                        try:
                            stack[next_window] += edge_subset
                        except KeyError:
                            stack[next_window] = edge_subset

        window, i, j = fd.intersecting_window(x_onstream, y_onstream)
        stack = {window: typed.List([typed.List([i, j])])}

        while True:
            next_delin(stack, window)

            window = next(
                (wind for wind, wind_stack in stack.items() if len(wind_stack) > 0),
                None,
            )

            if window is None:
                break

        # Create a vector
        transformer = Transformer.from_crs(fd.proj, 4326, always_xy=True)

        def transform_geojson(coords):
            wgs_pnts = transformer.transform(
                [coord[0] for coord in coords[0]],
                [coord[1] for coord in coords[0]],
            )

            return [list(zip(*wgs_pnts))]

        # TODO: Optimize this...rasterio.shapes requires a type promotion and to iterate
        # the generator to gather polygons
        watershed_geom = {"type": "MultiPolygon", "coordinates": []}

        for geo, value in shapes(
            coverage.astype("uint8"), connectivity=8, transform=fd.transform
        ):
            if value == 1:
                watershed_geom["coordinates"].append(
                    transform_geojson(geo["coordinates"])
                )

        return x_onstream, y_onstream, watershed_geom
