import numpy as np
from numba.pycc import CC


cc = CC("delineate")


@cc.export("find_stream_task", "Tuple((b1, i8, i8))(b1[:, :], i2[:, :], i8, i8)")
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


@cc.export(
    "delineate_task",
    "Tuple((i8[:, :], i8[:, :], i2[:]))(i2[:, :], i8[:, :])",
)
def delineate_task(fd, stack):
    """Delineate a watershed above a point. If a point out of bounds is encountered, the
    function will return with the element being evaluated and the location of the out
    of bounds element.

    Args:
        fd (np.ndarray): 2D flow direction array derived from GRASS GIS.
        stack (np.ndarray): Indexes of elements to try and add to the
        watershed.

    Returns:
        Lists of both watershed
        cells, and edges encountered.
    """
    directions = [[7, 6, 5], [8, 0, 4], [1, 2, 3]]
    nbrs = [[-1, -1], [-1, 0], [-1, 1], [0, -1], [0, 1], [1, -1], [1, 0], [1, 1]]

    basin = [[np.int64(0), np.int64(0)]]
    edges = [[np.int64(0), np.int64(0)]]
    edge_directions = []

    list_stack = [[val for val in e] for e in stack]

    while len(list_stack) > 0:
        i, j = list_stack.pop()

        for row_offset, col_offset in nbrs:
            t_i, t_j = i + row_offset, j + col_offset

            # Out of bounds?
            if t_i < 0 or t_j < 0 or t_i == fd.shape[0] or t_j == fd.shape[0]:
                edge_directions.append(
                    np.int16(directions[row_offset + 1][col_offset + 1])
                )
                edges.append([t_i, t_j])
                continue

            # Flow off map
            if fd[t_i, t_j] <= 0:
                continue

            # Check if the element at this offset contributes to the element being
            # tested
            if fd[t_i, t_j] == directions[row_offset + 1][col_offset + 1]:
                list_stack.append([t_i, t_j])
                basin.append([t_i, t_j])

    return np.asarray(basin)[1:], np.asarray(edges)[1:], np.asarray(edge_directions)
