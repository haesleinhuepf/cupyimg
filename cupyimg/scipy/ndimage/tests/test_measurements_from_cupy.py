import unittest

import numpy

from cupy import testing
import cupyimg.scipy.ndimage  # NOQA
from cupyimg.testing import numpy_cupyimg_array_equal

try:
    import scipy.ndimage  # NOQA
except ImportError:
    pass


def _generate_binary_structure(rank, connectivity):
    if connectivity < 1:
        connectivity = 1
    if rank < 1:
        return numpy.array(True, dtype=bool)
    output = numpy.fabs(numpy.indices([3] * rank) - 1)
    output = numpy.add.reduce(output, 0)
    return output <= connectivity


@testing.parameterize(
    *testing.product(
        {
            "ndim": [1, 2, 3, 4],
            "size": [50, 100],
            "density": [0.2, 0.3, 0.4],
            "connectivity": [None, 2, 3],
            "x_dtype": [
                bool,
                numpy.int8,
                numpy.int32,
                numpy.int64,
                numpy.float32,
                numpy.float64,
            ],
            "output": [None, numpy.int32, numpy.int64],
            "o_type": [None, "ndarray"],
        }
    )
)
@testing.gpu
@testing.with_requires("scipy")
class TestLabel(unittest.TestCase):
    @numpy_cupyimg_array_equal(scipy_name="scp")
    def test_label(self, xp, scp):
        size = int(pow(self.size, 1 / self.ndim))
        x_shape = range(size, size + self.ndim)
        x = xp.zeros(x_shape, dtype=self.x_dtype)
        x[testing.shaped_random(x_shape, xp) < self.density] = 1
        if self.connectivity is None:
            structure = None
        else:
            structure = scipy.ndimage.generate_binary_structure(
                self.ndim, self.connectivity
            )
        if self.o_type == "ndarray" and self.output is not None:
            output = xp.empty(x_shape, dtype=self.output)
            num_features = scp.ndimage.label(
                x, structure=structure, output=output
            )
            return output
        labels, num_features = scp.ndimage.label(
            x, structure=structure, output=self.output
        )
        return labels
