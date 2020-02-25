r"""Function of unitary fourier transform (uft) and utilities

This module implements the unitary fourier transform, also known as
the ortho-normal transform. It is especially useful for convolution
[1], as it respects the Parseval equality. The value of the null
frequency is equal to

.. math::  \frac{1}{\sqrt{n}} \sum_i x_i

so the Fourier transform has the same energy as the original image
(see ``image_quad_norm`` function). The transform is applied from the
last axis for performance (assuming a C-order array input).

References
----------
.. [1] B. R. Hunt "A matrix theory proof of the discrete convolution
       theorem", IEEE Trans. on Audio and Electroacoustics,
       vol. au-19, no. 4, pp. 285-288, dec. 1971

"""


import math

import cupy

from .._shared.fft import fftmodule as fft

__keywords__ = "fft, Fourier Transform, orthonormal, unitary"


def ufftn(inarray, dim=None):
    """N-dimensional unitary Fourier transform.

    Parameters
    ----------
    inarray : ndarray
        The array to transform.
    dim : int, optional
        The last axis along which to compute the transform. All
        axes by default.

    Returns
    -------
    outarray : ndarray (same shape than inarray)
        The unitary N-D Fourier transform of ``inarray``.

    Examples
    --------
    >>> input = cupy.ones((3, 3, 3))
    >>> output = ufftn(input)
    >>> cupy.allclose(cupy.sum(input) / cupy.sqrt(input.size), output[0, 0, 0])
    True
    >>> output.shape
    (3, 3, 3)
    """
    if dim is None:
        dim = inarray.ndim
    outarray = fft.fftn(inarray, axes=range(-dim, 0), norm="ortho")
    return outarray


def uifftn(inarray, dim=None):
    """N-dimensional unitary inverse Fourier transform.

    Parameters
    ----------
    inarray : ndarray
        The array to transform.
    dim : int, optional
        The last axis along which to compute the transform. All
        axes by default.

    Returns
    -------
    outarray : ndarray (same shape than inarray)
        The unitary inverse N-D Fourier transform of ``inarray``.

    Examples
    --------
    >>> input = cupy.ones((3, 3, 3))
    >>> output = uifftn(input)
    >>> cupy.allclose(cupy.sum(input) / cupy.sqrt(input.size), output[0, 0, 0])
    True
    >>> output.shape
    (3, 3, 3)
    """
    if dim is None:
        dim = inarray.ndim
    outarray = fft.ifftn(inarray, axes=range(-dim, 0), norm="ortho")
    return outarray


def urfftn(inarray, dim=None):
    """N-dimensional real unitary Fourier transform.

    This transform considers the Hermitian property of the transform on
    real-valued input.

    Parameters
    ----------
    inarray : ndarray, shape (M, N, ..., P)
        The array to transform.
    dim : int, optional
        The last axis along which to compute the transform. All
        axes by default.

    Returns
    -------
    outarray : ndarray, shape (M, N, ..., P / 2 + 1)
        The unitary N-D real Fourier transform of ``inarray``.

    Notes
    -----
    The ``urfft`` functions assume an input array of real
    values. Consequently, the output has a Hermitian property and
    redundant values are not computed or returned.

    Examples
    --------
    >>> input = cupy.ones((5, 5, 5))
    >>> output = urfftn(input)
    >>> cupy.allclose(cupy.sum(input) / cupy.sqrt(input.size), output[0, 0, 0])
    True
    >>> output.shape
    (5, 5, 3)
    """
    if dim is None:
        dim = inarray.ndim
    outarray = fft.rfftn(inarray, axes=range(-dim, 0), norm="ortho")
    return outarray


def uirfftn(inarray, dim=None, shape=None):
    """N-dimensional inverse real unitary Fourier transform.

    This transform considers the Hermitian property of the transform
    from complex to real input.

    Parameters
    ----------
    inarray : ndarray
        The array to transform.
    dim : int, optional
        The last axis along which to compute the transform. All
        axes by default.
    shape : tuple of int, optional
        The shape of the output. The shape of ``rfft`` is ambiguous in
        case of odd-valued input shape. In this case, this parameter
        should be provided. See ``cupy.fft.irfftn``.

    Returns
    -------
    outarray : ndarray
        The unitary N-D inverse real Fourier transform of ``inarray``.

    Notes
    -----
    The ``uirfft`` function assumes that the output array is
    real-valued. Consequently, the input is assumed to have a Hermitian
    property and redundant values are implicit.

    Examples
    --------
    >>> input = cupy.ones((5, 5, 5))
    >>> output = uirfftn(urfftn(input), shape=input.shape)
    >>> cupy.allclose(input, output)
    True
    >>> output.shape
    (5, 5, 5)
    """
    if dim is None:
        dim = inarray.ndim
    outarray = fft.irfftn(inarray, shape, axes=range(-dim, 0), norm="ortho")
    return outarray


def ufft2(inarray):
    """2-dimensional unitary Fourier transform.

    Compute the Fourier transform on the last 2 axes.

    Parameters
    ----------
    inarray : ndarray
        The array to transform.

    Returns
    -------
    outarray : ndarray (same shape as inarray)
        The unitary 2-D Fourier transform of ``inarray``.

    See Also
    --------
    uifft2, ufftn, urfftn

    Examples
    --------
    >>> input = cupy.ones((10, 128, 128))
    >>> output = ufft2(input)
    >>> cupy.allclose(cupy.sum(input[1, ...]) / cupy.sqrt(input[1, ...].size),
    ...               output[1, 0, 0])
    True
    >>> output.shape
    (10, 128, 128)
    """
    return ufftn(inarray, 2)


def uifft2(inarray):
    """2-dimensional inverse unitary Fourier transform.

    Compute the inverse Fourier transform on the last 2 axes.

    Parameters
    ----------
    inarray : ndarray
        The array to transform.

    Returns
    -------
    outarray : ndarray (same shape as inarray)
        The unitary 2-D inverse Fourier transform of ``inarray``.

    See Also
    --------
    uifft2, uifftn, uirfftn

    Examples
    --------
    >>> input = cupy.ones((10, 128, 128))
    >>> output = uifft2(input)
    >>> cupy.allclose(cupy.sum(input[1, ...]) / cupy.sqrt(input[1, ...].size),
    ...               output[0, 0, 0])
    True
    >>> output.shape
    (10, 128, 128)
    """
    return uifftn(inarray, 2)


def urfft2(inarray):
    """2-dimensional real unitary Fourier transform

    Compute the real Fourier transform on the last 2 axes. This
    transform considers the Hermitian property of the transform from
    complex to real-valued input.

    Parameters
    ----------
    inarray : ndarray, shape (M, N, ..., P)
        The array to transform.

    Returns
    -------
    outarray : ndarray, shape (M, N, ..., 2 * (P - 1))
        The unitary 2-D real Fourier transform of ``inarray``.

    See Also
    --------
    ufft2, ufftn, urfftn

    Examples
    --------
    >>> input = cupy.ones((10, 128, 128))
    >>> output = urfft2(input)
    >>> cupy.allclose(cupy.sum(input[1,...]) / cupy.sqrt(input[1,...].size),
    ...               output[1, 0, 0])
    True
    >>> output.shape
    (10, 128, 65)
    """
    return urfftn(inarray, 2)


def uirfft2(inarray, shape=None):
    """2-dimensional inverse real unitary Fourier transform.

    Compute the real inverse Fourier transform on the last 2 axes.
    This transform considers the Hermitian property of the transform
    from complex to real-valued input.

    Parameters
    ----------
    inarray : ndarray, shape (M, N, ..., P)
        The array to transform.
    shape : tuple of int, optional
        The shape of the output. The shape of ``rfft`` is ambiguous in
        case of odd-valued input shape. In this case, this parameter
        should be provided. See ``cupy.fft.irfftn``.

    Returns
    -------
    outarray : ndarray, shape (M, N, ..., 2 * (P - 1))
        The unitary 2-D inverse real Fourier transform of ``inarray``.

    See Also
    --------
    urfft2, uifftn, uirfftn

    Examples
    --------
    >>> input = cupy.ones((10, 128, 128))
    >>> output = uirfftn(urfftn(input), shape=input.shape)
    >>> cupy.allclose(input, output)
    True
    >>> output.shape
    (10, 128, 128)
    """
    return uirfftn(inarray, 2, shape=shape)


def image_quad_norm(inarray):
    """Return the quadratic norm of images in Fourier space.

    This function detects whether the input image satisfies the
    Hermitian property.

    Parameters
    ----------
    inarray : ndarray
        Input image. The image data should reside in the final two
        axes.

    Returns
    -------
    norm : float
        The quadratic norm of ``inarray``.

    Examples
    --------
    >>> input = cupy.ones((5, 5))
    >>> image_quad_norm(ufft2(input)) == cupy.sum(cupy.abs(input)**2)
    True
    >>> image_quad_norm(ufft2(input)) == image_quad_norm(urfft2(input))
    True
    """
    # If there is a Hermitian symmetry
    abs_sq = cupy.abs(inarray)
    abs_sq *= abs_sq
    if inarray.shape[-1] != inarray.shape[-2]:
        return 2 * cupy.sum(cupy.sum(abs_sq, axis=-1), axis=-1) - cupy.sum(
            cupy.abs(inarray[..., 0]) ** 2, axis=-1
        )
    else:
        return cupy.sum(cupy.sum(abs_sq, axis=-1), axis=-1)


def ir2tf(imp_resp, shape, dim=None, is_real=True):
    """Compute the transfer function of an impulse response (IR).

    This function makes the necessary correct zero-padding, zero
    convention, correct fft2, etc... to compute the transfer function
    of IR. To use with unitary Fourier transform for the signal (ufftn
    or equivalent).

    Parameters
    ----------
    imp_resp : ndarray
        The impulse responses.
    shape : tuple of int
        A tuple of integer corresponding to the target shape of the
        transfer function.
    dim : int, optional
        The last axis along which to compute the transform. All
        axes by default.
    is_real : boolean, optional
       If True (default), imp_resp is supposed real and the Hermitian property
       is used with rfftn Fourier transform.

    Returns
    -------
    y : complex ndarray
       The transfer function of shape ``shape``.

    See Also
    --------
    ufftn, uifftn, urfftn, uirfftn

    Examples
    --------
    >>> cupy.all(cupy.array([[4, 0], [0, 0]]) == ir2tf(cupy.ones((2, 2)), (2, 2)))
    True
    >>> ir2tf(cupy.ones((2, 2)), (512, 512)).shape == (512, 257)
    True
    >>> ir2tf(cupy.ones((2, 2)), (512, 512), is_real=False).shape == (512, 512)
    True

    Notes
    -----
    The input array can be composed of multiple-dimensional IR with
    an arbitrary number of IR. The individual IR must be accessed
    through the first axes. The last ``dim`` axes contain the space
    definition.
    """
    if not dim:
        dim = imp_resp.ndim
    # Zero padding and fill
    irpadded = cupy.zeros(shape)
    irpadded[tuple([slice(0, s) for s in imp_resp.shape])] = imp_resp
    # Roll for zero convention of the fft to avoid the phase
    # problem. Work with odd and even size.
    for axis, axis_size in enumerate(imp_resp.shape):
        if axis >= imp_resp.ndim - dim:
            irpadded = cupy.roll(
                irpadded, shift=-math.floor(axis_size / 2), axis=axis
            )
    if is_real:
        return fft.rfftn(irpadded, axes=range(-dim, 0))
    else:
        return fft.fftn(irpadded, axes=range(-dim, 0))


def laplacian(ndim, shape, is_real=True):
    """Return the transfer function of the Laplacian.

    Laplacian is the second order difference, on row and column.

    Parameters
    ----------
    ndim : int
        The dimension of the Laplacian.
    shape : tuple
        The support on which to compute the transfer function.
    is_real : boolean, optional
       If True (default), imp_resp is assumed to be real-valued and
       the Hermitian property is used with rfftn Fourier transform
       to return the transfer function.

    Returns
    -------
    tf : array_like, complex
        The transfer function.
    impr : array_like, real
        The Laplacian.

    Examples
    --------
    >>> tf, ir = laplacian(2, (32, 32))
    >>> cupy.all(ir == cupy.array([[0, -1, 0], [-1, 4, -1], [0, -1, 0]]))
    True
    >>> cupy.all(tf == ir2tf(ir, (32, 32)))
    True
    """
    impr = cupy.zeros([3] * ndim)
    for dim in range(ndim):
        idx = tuple(
            [slice(1, 2)] * dim
            + [slice(None)]
            + [slice(1, 2)] * (ndim - dim - 1)
        )
        impr[idx] = cupy.array([-1.0, 0.0, -1.0]).reshape(
            [-1 if i == dim else 1 for i in range(ndim)]
        )
    impr[(slice(1, 2),) * ndim] = 2.0 * ndim
    return ir2tf(impr, shape, is_real=is_real), impr