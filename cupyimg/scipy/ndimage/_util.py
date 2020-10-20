import cupy


def _is_integer_output(output, input):
    if output is None:
        return input.dtype.kind in "iu"
    elif isinstance(output, cupy.ndarray):
        return output.dtype.kind in "iu"
    return cupy.dtype(output).kind in "iu"


def _check_cval(mode, cval, integer_output):
    if mode == "constant" and integer_output and not cupy.isfinite(cval):
        raise NotImplementedError(
            "Non-finite cval is not supported for "
            "outputs with integer dtype."
        )


def _check_axis(axis, rank):
    if axis < 0:
        axis += rank
    if axis < 0 or axis >= rank:
        raise ValueError("invalid axis")
    return axis


def _get_output(
    output, input, shape=None, weights_dtype=None, allow_inplace=True
):
    if shape is None:
        shape = input.shape
    if isinstance(output, cupy.ndarray):
        if output.shape != tuple(shape):
            raise ValueError("output shape is not correct")
        if weights_dtype is None:
            complex_out = input.dtype.kind == "c"
        else:
            complex_out = input.dtype.kind == "c" or weights_dtype.kind == "c"
        if complex_out and output.dtype.kind != "c":
            raise RuntimeError(
                "output must have complex dtype if either the input or "
                "weights are complex-valued."
            )
        if not allow_inplace and output is input:
            raise RuntimeError("in-place filtering is not supported")
    else:
        if weights_dtype is not None:
            dtype = output
            if dtype is None:
                if weights_dtype.kind == "c":
                    dtype = cupy.promote_types(input.dtype, cupy.complex64)
                else:
                    dtype = input.dtype
            elif (
                input.dtype.kind == "c" or weights_dtype.kind == "c"
            ) and output.dtype.kind != "c":
                raise RuntimeError(
                    "output must have complex dtype if either the input or "
                    "weights are complex-valued."
                )
        else:
            dtype = input.dtype if output is None else output
        output = cupy.zeros(shape, dtype)
    return output


def _fix_sequence_arg(arg, ndim, name, conv=lambda x: x):
    if isinstance(arg, str):
        return [conv(arg)] * ndim
    try:
        arg = iter(arg)
    except TypeError:
        return [conv(arg)] * ndim
    lst = [conv(x) for x in arg]
    if len(lst) != ndim:
        msg = "{} must have length equal to input rank".format(name)
        raise RuntimeError(msg)
    return lst


def _check_origin(origin, width):
    origin = int(origin)
    if (width // 2 + origin < 0) or (width // 2 + origin >= width):
        raise ValueError("invalid origin")
    return origin


def _check_mode(mode):
    if mode not in ("reflect", "constant", "nearest", "mirror", "wrap"):
        msg = "boundary mode not supported (actual: {})".format(mode)
        raise RuntimeError(msg)
    return mode


def _get_inttype(input):
    # The integer type to use for indices in the input array
    # The indices actually use byte positions and we can't just use
    # input.nbytes since that won't tell us the number of bytes between the
    # first and last elements when the array is non-contiguous
    nbytes = (
        sum(
            (x - 1) * abs(stride)
            for x, stride in zip(input.shape, input.strides)
        )
        + input.dtype.itemsize
    )
    return "int" if nbytes < (1 << 31) else "ptrdiff_t"


def _normalize_sequence(arr, rank):
    """If arr is a scalar, create a sequence of length equal to the
    rank by duplicating the arr. If arr is a sequence,
    check if its length is equal to the length of array.
    """
    if hasattr(arr, "__iter__") and not isinstance(arr, str):
        if isinstance(arr, cupy.ndarray):
            arr = cupy.asnumpy(arr)
        normalized = list(arr)
        if len(normalized) != rank:
            err = "sequence argument must have length equal to arr rank"
            raise RuntimeError(err)
    else:
        normalized = [arr] * rank
    return normalized


def _get_ndimage_mode_kwargs(mode, cval=0):
    if mode == "reflect":
        mode_kwargs = dict(mode="symmetric")
    elif mode == "mirror":
        mode_kwargs = dict(mode="reflect")
    elif mode == "nearest":
        mode_kwargs = dict(mode="edge")
    elif mode == "constant":
        mode_kwargs = dict(mode="constant", cval=cval)
    elif mode == "wrap":
        mode_kwargs = dict(mode="periodic")
    else:
        raise ValueError("unsupported mode: {}".format(mode))
    return mode_kwargs


def _generate_boundary_condition_ops(mode, ix, xsize):
    if mode == "reflect":
        ops = """
        if ({ix} < 0) {{
            {ix} = - 1 -{ix};
        }}
        {ix} %= {xsize} * 2;
        {ix} = min({ix}, 2 * {xsize} - 1 - {ix});""".format(
            ix=ix, xsize=xsize
        )
    elif mode == "mirror":
        ops = """
        if ({xsize} == 1) {{
            {ix} = 0;
        }} else {{
            if ({ix} < 0) {{
                {ix} = -{ix};
            }}
            {ix} = 1 + ({ix} - 1) % (({xsize} - 1) * 2);
            {ix} = min({ix}, 2 * {xsize} - 2 - {ix});
        }}""".format(
            ix=ix, xsize=xsize
        )
    elif mode == "nearest":
        ops = """
        {ix} = min(max({ix}, 0), {xsize} - 1);""".format(
            ix=ix, xsize=xsize
        )
    elif mode == "wrap":
        ops = """
        {ix} %= {xsize};
        if ({ix} < 0) {{
            {ix} += {xsize};
        }}""".format(
            ix=ix, xsize=xsize
        )
    elif mode == "constant":
        ops = """
        if ({ix} >= {xsize}) {{
            {ix} = -1;
        }}""".format(
            ix=ix, xsize=xsize
        )
    return ops


def _generate_indices_ops(ndim, int_type, offsets):
    code = "{type} ind_{j} = _i % ysize_{j} - {offset}; _i /= ysize_{j};"
    body = [
        code.format(type=int_type, j=j, offset=offsets[j])
        for j in range(ndim - 1, 0, -1)
    ]
    return "{type} _i = i;\n{body}\n{type} ind_0 = _i - {offset};".format(
        type=int_type, body="\n".join(body), offset=offsets[0]
    )
