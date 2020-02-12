import cupy as cp
import pytest
from cupy.testing import assert_array_equal

from cupyimg.skimage.segmentation import (
    morphological_chan_vese,
    morphological_geodesic_active_contour,
    inverse_gaussian_gradient,
    disk_level_set,
)


def gaussian_blob():
    coords = cp.mgrid[-5:6, -5:6]
    sqrdistances = (coords ** 2).sum(0)
    return cp.exp(-sqrdistances / 10)


def test_morphsnakes_incorrect_image_shape():
    img = cp.zeros((10, 10, 3))
    ls = cp.zeros((10, 9))

    with pytest.raises(ValueError):
        morphological_chan_vese(img, iterations=1, init_level_set=ls)
    with pytest.raises(ValueError):
        morphological_geodesic_active_contour(
            img, iterations=1, init_level_set=ls
        )


def test_morphsnakes_incorrect_ndim():
    img = cp.zeros((4, 4, 4, 4))
    ls = cp.zeros((4, 4, 4, 4))

    with pytest.raises(ValueError):
        morphological_chan_vese(img, iterations=1, init_level_set=ls)
    with pytest.raises(ValueError):
        morphological_geodesic_active_contour(
            img, iterations=1, init_level_set=ls
        )


def test_morphsnakes_black():
    img = cp.zeros((11, 11))
    ls = disk_level_set(img.shape, (5, 5), 3)

    ref_zeros = cp.zeros(img.shape, dtype=cp.int8)
    ref_ones = cp.ones(img.shape, dtype=cp.int8)

    acwe_ls = morphological_chan_vese(img, iterations=6, init_level_set=ls)
    assert_array_equal(acwe_ls, ref_zeros)

    gac_ls = morphological_geodesic_active_contour(
        img, iterations=6, init_level_set=ls
    )
    assert_array_equal(gac_ls, ref_zeros)

    gac_ls2 = morphological_geodesic_active_contour(
        img,
        iterations=6,
        init_level_set=ls,
        balloon=1,
        threshold=-1,
        smoothing=0,
    )
    assert_array_equal(gac_ls2, ref_ones)

    assert acwe_ls.dtype == gac_ls.dtype == gac_ls2.dtype == cp.int8


def test_morphsnakes_simple_shape_chan_vese():
    img = gaussian_blob()
    ls1 = disk_level_set(img.shape, (5, 5), 3)
    ls2 = disk_level_set(img.shape, (5, 5), 6)

    acwe_ls1 = morphological_chan_vese(img, iterations=10, init_level_set=ls1)
    acwe_ls2 = morphological_chan_vese(img, iterations=10, init_level_set=ls2)

    assert_array_equal(acwe_ls1, acwe_ls2)

    assert acwe_ls1.dtype == acwe_ls2.dtype == cp.int8


def test_morphsnakes_simple_shape_geodesic_active_contour():
    img = disk_level_set((11, 11), (5, 5), 3.5).astype(float)
    gimg = inverse_gaussian_gradient(img, alpha=10.0, sigma=1.0)
    ls = disk_level_set(img.shape, (5, 5), 6)

    ref = cp.asarray(
        [
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
            [0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0],
            [0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0],
            [0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0],
            [0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0],
            [0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0],
            [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ],
        dtype=cp.int8,
    )

    gac_ls = morphological_geodesic_active_contour(
        gimg, iterations=10, init_level_set=ls, balloon=-1
    )
    assert_array_equal(gac_ls, ref)
    assert gac_ls.dtype == cp.int8


def test_init_level_sets():
    image = cp.zeros((6, 6))
    checkerboard_ls = morphological_chan_vese(image, 0, "checkerboard")
    checkerboard_ref = cp.asarray(
        [
            [0, 0, 0, 0, 0, 1],
            [0, 0, 0, 0, 0, 1],
            [0, 0, 0, 0, 0, 1],
            [0, 0, 0, 0, 0, 1],
            [0, 0, 0, 0, 0, 1],
            [1, 1, 1, 1, 1, 0],
        ],
        dtype=cp.int8,
    )

    circle_ls = morphological_geodesic_active_contour(image, 0, "circle")
    circle_ref = cp.asarray(
        [
            [0, 0, 0, 0, 0, 0],
            [0, 0, 1, 1, 1, 0],
            [0, 1, 1, 1, 1, 1],
            [0, 1, 1, 1, 1, 1],
            [0, 1, 1, 1, 1, 1],
            [0, 0, 1, 1, 1, 0],
        ],
        dtype=cp.int8,
    )

    assert_array_equal(checkerboard_ls, checkerboard_ref)
    assert_array_equal(circle_ls, circle_ref)


def test_morphsnakes_3d():
    image = cp.zeros((7, 7, 7))

    evolution = []

    def callback(x):
        evolution.append(x.sum())

    ls = morphological_chan_vese(image, 5, "circle", iter_callback=callback)

    # Check that the initial circle level set is correct
    assert evolution[0] == 81

    # Check that the final level set is correct
    assert ls.sum() == 0

    # Check that the contour is shrinking at every iteration
    for v1, v2 in zip(evolution[:-1], evolution[1:]):
        assert v1 >= v2
