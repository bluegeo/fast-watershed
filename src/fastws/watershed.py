from typing import Union, Tuple, Optional

import numpy as np
from rasterio.features import shapes
from pyproj import Transformer
from shapely.geometry import shape

from fastws.raster import Raster, WindowAccumulator, transform_point
from delineate import find_stream_task, delineate_task


def find_stream(
    stream_src: str,
    fd_src: str,
    fa_src: str,
    x: float,
    y: float,
    xy_srs: Optional[Union[str, int]] = None,
) -> Tuple[float, float, float]:
    """Search for the nearest stream cell and return the central coordinate.

    Args:
        stream_src (str): Raster source of stream data.
        fd_src (str): Raster source of flow direction data.
        fa_src (str): Raster source of flow accumulation data. This dataset only
        requires values where streams occur.
        x (float): x-coordinate.
        y (float): y-coordinate.
        xy_srs (Union[str, int], optional): Spatial reference of the (x, y) point.
        If not provided, it is assumed that the point is in the same crs as the input
        rasters. Defaults to None.

    Returns:
        Tuple[float, float]: (x, y) coordinates that intersect a stream.
    """
    with Raster(stream_src) as streams, Raster(fd_src) as fd, Raster(fa_src) as fa:
        if xy_srs is not None:
            # Align the point with the grids and move downslope to a stream
            x_prepared, y_prepared = transform_point(x, y, xy_srs, fd.proj)
        else:
            x_prepared, y_prepared = x, y

        window, i, j = fd.intersecting_window(x_prepared, y_prepared)

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

        if xy_srs is not None:
            # Return the x and y coordinates to their original coordinate system
            x, y = transform_point(x, y, fd.proj, xy_srs)

        return x, y, area


def delineate(
    x: float,
    y: float,
    stream_src: str,
    fd_src: str,
    xy_srs: Optional[Union[str, int]] = None,
    snap: bool = False,
    fa_src: Optional[str] = None,
    out_crs: Optional[Union[str, int]] = None,
    simplify: float = 0,
    smooth: float = 0,
) -> Tuple[float, float, float, dict]:
    """Delineate the watershed on a stream above the point (x, y)

    Args:
        stream_src (str): Stream raster.
        x (float): X-coordinate for delineation.
        y (float): Y-coordinate for delineation.
        fd_src (str): Flow Direction raster.
        xy_srs (Union[str, int], optional): Spatial reference of the (x, y) point.
        If not provided, it is assumed that the point is in the same crs as the input
        rasters. Defaults to None.
        snap (bool, optional): Snap the point downslope until a stream is encountered.
        Defaults to False.
        fa_src (str): Flow Accumulation raster.
        out_crs (Union[str, int], optional): Spatial reference of the output watershed
        polygon. Defaults to the spatial reference of the input raster.
        Defaults to None.
        simplify (float, optional): Simplify the resulting geometry with a tolerance.
        Defaults to 0 (do not simplify).
        smooth (float, optional): Smooth the resulting geometry with a distance.
        Defaults to 0 (do not smooth).

    Returns:
        Tuple[float, float, float, dict]: Snapped x coordinate, snapped y coordinate,
        area of the watershed in the source srs, and the watershed geojson.
    """
    if snap:
        if fa_src is None:
            raise ValueError("Flow accumulation raster is required for snapping")
        x, y, _ = find_stream(stream_src, fd_src, fa_src, x, y, xy_srs)

    with Raster(fd_src) as fd:
        # Match the point to the raster spatial reference
        if xy_srs is not None:
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
            coverage.astype(np.dtype("uint8")),
            connectivity=8,
            transform=coverage.transform,
        ):
            if value == 1:
                watershed_geom["coordinates"].append(geo["coordinates"])

        # Calculate area
        watershed_shape = shape(watershed_geom)
        if simplify > 0:
            watershed_shape = watershed_shape.simplify(tolerance=simplify)

        if smooth > 0:
            watershed_shape = watershed_shape.buffer(smooth, join_style="round").buffer(
                -smooth, join_style="round"
            )

        area = watershed_shape.area

        if out_crs is not None:
            transformer = Transformer.from_crs(fd.proj, out_crs, always_xy=True)

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
        if xy_srs is not None:
            x, y = transform_point(x, y, fd.proj, xy_srs)

        return x, y, area, watershed_geom
