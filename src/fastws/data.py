# Data preparation module
# To use - requires the installation of hydro-tools, which requires a
# local GRASS GIS installation

from typing import List, Optional, Union
import os

try:
    import dask.array as da
    from hydrotools.utils import TempRasterFiles
    from hydrotools.raster import warp, from_raster, to_raster
    from hydrotools.watershed import flow_direction_accumulation, extract_streams
except ImportError:
    raise ImportError(
        "This module requires GRASS GIS and the hydro-tools package, which can be"
        "installed by running: `pip install git+https://github.com/bluegeo/hydro-tools.git`"
    )


def out_path(rpath: str, suffix: str, res: Union[str, float, int]) -> str:
    return os.path.join(
        os.path.dirname(rpath),
        ".".join(os.path.basename(rpath).split(".")[:-1]) + f"_{suffix}_{res}.tif",
    )


def prepare_data(dem_path: str, resolutions: Optional[List[int]] = None):
    """Generate the necessary files to be used in the Fast Watershed algorithm

    Args:
        dem_path (str): Path to a DEM raster grid
        resolutions (list, optional): Resolutions to output necessary files:
        ex: `[15, 25, 50, 100, 200]`.
        Defaults to None.
    """
    for res in resolutions if resolutions is not None else [None]:
        with TempRasterFiles(3) as (dem_postprep, flow_dir_tmp, flow_acc_tmp):
            if res is not None:
                # Resample the DEM
                warp(
                    dem_path,
                    dem_postprep,
                    csx=res,
                    csy=res,
                    resample_method="bilinear",
                    as_cog=False,
                )
            else:
                dem_postprep = dem_path
                res = "native"

            flow_acc = out_path(dem_path, "flow_acc", res)
            streams = out_path(dem_path, "streams", res)
            flow_dir = out_path(dem_path, "flow_dir", res)

            flow_direction_accumulation(dem_postprep, flow_dir_tmp, flow_acc_tmp)

            extract_streams(dem_postprep, flow_acc, streams, flow_dir)

            # Only include flow accumulation over the extent of streams
            to_raster(
                da.ma.masked_where(
                    da.ma.getmaskarray(from_raster(streams)),
                    from_raster(flow_acc_tmp),
                ),
                flow_acc_tmp,
                flow_acc,
            )
