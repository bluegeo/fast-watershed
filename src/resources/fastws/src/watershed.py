from typing import Union, Tuple

import numpy as np
from rasterio.features import shapes
from pyproj import Transformer
from shapely.geometry import shape

from fastws.raster import Raster, WindowAccumulator, transform_point
from .delineate import find_stream_task, delineate_task


def find_stream(
    stream_src: str, fd_src: str, fa_src: str, x: float, y: float, xy_srs
) -> Tuple[float, float]:
    """Search for the nearest stream cell and return the central coordinate.

    Args:
        stream_src (str): Raster source of stream data.
        fd_src (str): Raster source of flow direction data.
        fa_src (str): Raster source of flow accumulation data. This dataset only
        requires values where streams occur.
        x (float): x-coordinate.
        y (float): y-coordinate.

    Returns:
        Tuple[float, float]: (x, y) coordinates that intersect a stream.
    """
    with Raster(stream_src) as streams, Raster(fd_src) as fd, Raster(fa_src) as fa:
        # Align the point with the grids and move downslope to a stream
        x_transformed, y_transformed = transform_point(x, y, xy_srs, fd.proj)

        window, i, j = fd.intersecting_window(x_transformed, y_transformed)

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

        area = abs(fa[window][i, j] * fa.csx * fa.csy)

        x, y = fd.xy_from_window_index(i, j, window)

        # Return the x and y coordinates to the original coordinate system
        x, y = transform_point(x, y, fd.proj, xy_srs)

        return x, y, area


def delineate(
    stream_src: str,
    fd_src: str,
    fa_src: str,
    x: float,
    y: float,
    xy_srs: Union[str, int],
    snap: bool = True,
    wgs_84: bool = True,
    simplify: float = 0,
    smooth: float = 0
) -> Tuple[float, float, float, dict]:
    """Delineate the watershed on a stream above the point (x, y)

    Args:
        stream_src (str): Stream raster.
        fd_src (str): Flow Direction raster.
        fa_src (str): Flow Accumulation raster.
        x (float): X-coordinate for delineation.
        y (float): Y-coordinate for delineation.
        xy_srs (Union[str, int]): Spatial reference of the (x, y) point.
        snap (bool, optional): Snap the point downslope until a stream is encountered.
        Defaults to True.
        wgs_84 (bool, optional): Transform the output watershed polygon to WGS 84 (4326)
        Defaults to True.
        simplify (float, optional): Simplify the resulting geometry with a tolerance.
        Defaults to 0 (do not simplify).
        smooth (float, optional): Smooth the resulting geometry with a distance.
        Defaults to 0 (do not smooth).

    Returns:
        Tuple[float, float, float, dict]: Snapped x coordinate, snapped y coordinate,
        area of the watershed in the source srs, and the watershed geojson.
    """
    if snap:
        x, y, _ = find_stream(stream_src, fd_src, fa_src, x, y, xy_srs)

    with Raster(fd_src) as fd, Raster(stream_src) as streams:
        if not fd.matches(streams):
            raise ValueError("Input Stream and Flow Direction rasters must match")

        # Match the point to the raster spatial reference
        x, y = transform_point(x, y, xy_srs, fd.proj)

        def next_delin(stack, window):
            # Flow direction data over the extent of the current window
            data = fd[window]

            # Add contributing cells to the window mask from the stack, and reset
            cov_idx, edges, edge_dirs = delineate_task(data, np.asarray(stack[window]))
            stack[window] = []

            # Add new indices to coverage
            coverage[window][tuple(cov_idx.T)] = True

            # Edge cells are tracked to determine if adjacent windows are needed
            if len(edges) > 0:
                edges = np.hstack(
                    [
                        np.asarray(edge_dirs).reshape((len(edge_dirs), 1)),
                        np.asarray(edges),
                    ]
                )

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

                        edge_subset = edge_subset[
                            fd[next_window][(edge_subset[:, 1], edge_subset[:, 2])]
                            == edge_subset[:, 0]
                        ][:, 1:]

                        coverage.add_window(next_window)

                        # Add to basin
                        coverage[next_window][tuple(edge_subset.T)] = True

                        try:
                            stack[next_window] += edge_subset.tolist()
                        except KeyError:
                            stack[next_window] = edge_subset.tolist()

        window, i, j = fd.intersecting_window(x, y)
        stack = {window: [[i, j]]}

        coverage = WindowAccumulator.from_raster(fd, window)
        coverage[window][i, j] = True

        while True:
            next_delin(stack, window)

            window = next(
                (wind for wind, wind_stack in stack.items() if len(wind_stack) > 0),
                None,
            )

            if window is None:
                break

        # Create a GeoJSON
        watershed_geom = {"type": "MultiPolygon", "coordinates": []}

        for geo, value in shapes(
            coverage.astype(np.uint8), connectivity=8, transform=coverage.transform
        ):
            if value == 1:
                watershed_geom["coordinates"].append(geo["coordinates"])

        # Calculate area
        watershed_shape = shape(watershed_geom)
        if simplify > 0:
            watershed_shape = watershed_shape.simplify(tolerance=simplify)

        if smooth > 0:
            watershed_shape = watershed_shape.buffer(smooth, join_style=1).buffer(
                -smooth, join_style=1
            )

        area = watershed_shape.area

        if wgs_84:
            transformer = Transformer.from_crs(fd.proj, 4326, always_xy=True)

            def transform_coords(coords):
                wgs_pnts = transformer.transform(
                    [coord[0] for coord in coords[0]],
                    [coord[1] for coord in coords[0]],
                )

                return [list(zip(*wgs_pnts))]

            watershed_geom["coordinates"] = [
                transform_coords(coords) for coords in watershed_geom["coordinates"]
            ]

        # Return the x and y coordinates to the original coordinate system
        x, y = transform_point(x, y, fd.proj, xy_srs)

        return x, y, area, watershed_geom
