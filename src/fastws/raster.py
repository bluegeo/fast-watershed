from __future__ import annotations
from typing import Union, Tuple
from types import SimpleNamespace

import numpy as np
import rasterio
from rasterio import DatasetReader
from rasterio.windows import Window
from pyproj import Transformer


class Raster:
    def __init__(self, src: str):
        self.ds = rasterio.open(src)

        if not self.ds.is_tiled:
            raise ValueError("Input raster should be tiled")
        
        self.data_cache = {}

    def __enter__(self) -> DatasetReader:
        return self

    def __exit__(self, a, b, c):
        self.ds.close

    @property
    def transform(self):
        return self.ds.transform

    @property
    def shape(self):
        return (self.ds.height, self.ds.width)

    @property
    def nodata(self):
        return self.ds.nodatavals[0]

    @property
    def proj(self):
        return self.ds.crs

    @property
    def left(self):
        return self.ds.bounds.left

    @property
    def top(self):
        return self.ds.bounds.top

    @property
    def csx(self):
        return self.ds.res[0]

    @property
    def csy(self):
        return self.ds.res[1]

    def window_extent(self, window: Window) -> SimpleNamespace:
        """Collect the bounding coordinates of a given window in the raster.

        Args:
            window (Window): Window within the raster.

        Returns:
            SimpleNamespace: Object with coordinate attributes top, bottom, left, right. 
        """
        return SimpleNamespace(
            top=self.top - window.row_off * self.csy,
            bottom=self.top - (window.row_off + window.height) * self.csy,
            left=self.left + window.col_off * self.csx,
            right=self.left + (window.col_off + window.width) * self.csx,
        )

    def matches(self, other: Raster) -> bool:
        return all(
            [
                all(
                    [np.isclose(a, b) for a, b in zip(self.ds.bounds, other.ds.bounds)]
                ),
                self.proj == other.proj,
                self.ds.height == other.ds.height,
                self.ds.width == other.ds.width,
            ]
        )

    def match_point(
        self, x: float, y: float, s_srs: Union[str, int]
    ) -> Tuple[float, float]:
        """Reproject a point to match the coordinate system.

        Args:
            x (float): x-coordinate.
            x (float): y-coordinate.
            s_srs (Union[str, int]): Source spatial reference.

        Returns:
            Tuple[float, float]: x and y reprojected
        """
        transformer = Transformer.from_crs(self.proj, s_srs, always_xy=True)

        return transformer.transform(x, y)
    
    def coord_to_idx(self, x: float, y: float) -> Tuple[int, int]:
        """Convert a cartesian point to a raster grid index.

        Args:
            x (float): x-coordinate.
            y (float): y-coordinate.

        Returns:
            Tuple[int, int]: An index pair in the form (i, j).
        """
        i = int(np.floor((self.top - y) / self.csy))
        j = int(np.floor((x - self.left) / self.csx))

        if i < 0 or j < 0 or i > self.shape[0] - 1 or j > self.shape[1] - 1:
            raise IndexError(f"Location ({x}, {y}) off of raster map")

        return (i, j)

    def intersecting_window(self, x: float, y: float) -> Tuple[Window, int, int]:
        """Return the window that intersects a point.

        Args:
            x (float): x-coordinate.
            y (float): y-coordinate.

        Returns:
            Tuple[Window, int, int]: The resulting window, and the index of (x, y) on
                the window.
        """

        def intersects(x: float, y: float, window: Window) -> bool:
            window_ext = self.window_extent(window)

            return all(
                [
                    y <= window_ext.top,
                    y >= window_ext.bottom,
                    x >= window_ext.left,
                    x <= window_ext.right,
                ]
            )

        window = next(
            (
                window
                for _, window in self.ds.block_windows()
                if intersects(x, y, window)
            ),
            None,
        )

        if window is None:
            raise IndexError(f"No window intersects the point ({x}, {y})")

        window_ext = self.window_extent(window)
        i = int(np.floor((window_ext.top - y) / self.csy))
        j = int(np.floor((x - window_ext.left) / self.csx))

        return window, i, j

    def xy_from_window_index(
        self, i: int, j: int, window: Window
    ) -> Tuple[float, float]:
        """Return an x, y coordinate from an index on or relative to the provided
        window.

        Args:
            i (int): i (y-based) index.
            j (int): j (x-based) index.
            window (Window): Window associated with the provided (i, j).

        Returns:
            Tuple[float, float]: (x, y) coordinates of the index.
        """
        window_ext = self.window_extent(window)

        half_csy = self.csy / 2.0
        half_csx = self.csx / 2.0

        y = (window_ext.top - i * self.csy) - half_csy

        x = (window_ext.left + j * self.csx) + half_csx

        return x, y

    def __getitem__(self, window: Window) -> np.ndarray:
        """Collect a window of data.

        Args:
            s (Window): A window object used to read data from the source raster.

        Returns:
            np.ndarray: 2D Numpy array of data.
        """
        try:
            return self.data_cache[window]
        except KeyError:
            self.data_cache[window] = self.ds.read(1, window=window)

        return self.data_cache[window]
