# Data preparation module
# To use - requires the installation of hydro-tools, which requires a
# local GRASS GIS installation

import os

try:
    from hydrotools.utils import TempRasterFiles
    from hydrotools.raster import warp
    from hydrotools.watershed import flow_direction_accumulation, extract_streams
except:
    raise ImportError(
        "This module requires GRASS GIS and the hydro-tools package, which can be"
        "installed by running: `pip install git+https://github.com/bluegeo/hydro-tools.git`"
    )


def out_path(rpath: str, suffix: str, res: int) -> str:
    return os.path.join(
        os.path.dirname(rpath),
        ".".join(os.path.basename(rpath).split(".")[:-1]) + f"_{suffix}_{res}.tif",
    )


def prepare_data(dem_path: str, resolutions=[15, 25, 50, 100, 200]):
    """Generate the necessary files to be used in the Fast Watershed algorithm

    Args:
        dem_path (str): Path to a DEM raster grid
        resolutions (list, optional): Resolutions to output necessary files.
        Defaults to [15, 25, 50, 100, 200].
    """
    for res in resolutions:
        with TempRasterFiles(2) as (dem_reproj, flow_dir_tmp):
            # Resample the DEM
            warp(
                dem_path,
                dem_reproj,
                csx=res,
                csy=res,
                resample_method="bilinear",
                as_cog=False,
            )

            flow_acc = out_path(dem_path, "flow_acc", res)
            streams = out_path(dem_path, "streams", res)
            flow_dir = out_path(dem_path, "flow_dir", res)

            flow_direction_accumulation(dem_reproj, flow_dir_tmp, flow_acc)

            extract_streams(dem_reproj, flow_acc, streams, flow_dir)
