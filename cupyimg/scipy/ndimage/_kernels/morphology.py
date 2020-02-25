import functools
import operator

import cupy

from .support import (
    _nested_loops_init,
    _masked_loop_init,
    _pixelregion_to_buffer,
    _pixelmask_to_buffer,
)


erode_preamble = """
static __device__ X erode_point(
    X pi, bool mv, X *buffer, bool center_is_true, bool true_val,
    bool false_val, bool *changed)
{
    X out;
    bool _in = pi ? true : false;

    if (mv) {
        if (center_is_true && _in == false)
        {
            *changed = 0
            out = (X)_in;
        } else {
            out = (X)true_val;
            for (size_t ii = 0; ii < filter_size; ii++) {
                if (!buffer[ii])
                {
                    out = (X)false_val;
                }
            }
            *changed = out != in;
        }
    } else {
        out = (X)_in;
    }

    return out;
}

"""


def _generate_erode_kernel(
    xshape,
    fshape,
    origin,
    center_is_true,
    border_value,
    true_val,
    false_val,
    masked=False,
):
    if masked:
        in_params = (
            "raw X x, raw W w, raw M mask"
        )  # TODO: can I set bool explicitly here?
    else:
        in_params = "raw X x, raw W w"
    out_params = "Y y"

    ndim = len(fshape)

    ops = []
    if masked:
        ops.append("bool mv = (bool)mask[i];")
    else:
        ops.append("bool mv = true;")
    ops.append(
        """
    int _in = x[i] ? 1 : 0;
    if (!mv) {{
        y = (Y)_in;
        return;
    }} else if ({center_is_true} && _in == {false_val}) {{
        y = (Y)_in;
        return;
    }}
    """.format(
            center_is_true=int(center_is_true), false_val=false_val
        )
    )

    ndim = len(fshape)

    ops.append("y = (Y){true_val};".format(true_val=true_val))

    # declare the loop and intialize image indices, ix_0, etc.
    ops += _nested_loops_init("constant", xshape, fshape, origin)

    # GRL: end of different middle section here

    _cond = " || ".join(["(ix_{0} < 0)".format(j) for j in range(ndim)])
    _expr = " + ".join(["ix_{0}".format(j) for j in range(ndim)])

    ops.append(
        """
        if (w[iw]) {{
            int ix = {expr};
            if ({cond}) {{
                if (!{border_value}) {{
                    y = (Y){false_val};
                    return;
                }}
            }} else {{
                bool nn = x[ix] ? {true_val} : {false_val};
                if (!nn) {{
                    y = (Y){false_val};
                    return;
                }}
            }}
        }}
        iw += 1;
        """.format(
            cond=_cond,
            expr=_expr,
            true_val=int(true_val),
            false_val=int(false_val),
            border_value=int(border_value),
        )
    )

    ops.append("}" * ndim)
    operation = "\n".join(ops)

    invert = true_val == 0
    name = "cupy_ndimage_erode_{}d_inv{}_x{}_w{}".format(
        ndim,
        invert,
        "_".join(["{}".format(j) for j in xshape]),
        "_".join(["{}".format(j) for j in fshape]),
    )
    return in_params, out_params, operation, name


def _generate_erode_kernel_masked(
    xshape,
    fshape,
    origin,
    center_is_true,
    border_value,
    true_val,
    false_val,
    masked=False,
):
    if masked:
        in_params = (
            "raw X x, raw I wlocs, raw W wvals, raw M mask"
        )  # TODO: can I set bool explicitly here?
    else:
        in_params = "raw X x, raw I wlocs, raw W wvals"
    out_params = "Y y"

    ndim = len(fshape)

    ops = []
    if masked:
        ops.append("bool mv = (bool)mask[i];")
    else:
        ops.append("bool mv = true;")
    ops.append(
        """
    int _in = x[i] ? 1 : 0;
    if (!mv) {{
        y = (Y)_in;
        return;
    }} else if ({center_is_true} && _in == {false_val}) {{
        y = (Y)_in;
        return;
    }}
    """.format(
            center_is_true=int(center_is_true), false_val=int(false_val)
        )
    )

    nnz = functools.reduce(operator.mul, fshape)
    ndim = len(fshape)
    ops.append("y = (Y){true_val};".format(true_val=true_val))

    # declare the loop and intialize image indices, ix_0, etc.
    ops += _masked_loop_init("constant", xshape, fshape, origin, nnz)

    _cond = " || ".join(["(ix_{0} < 0)".format(j) for j in range(ndim)])
    _expr = " + ".join(["ix_{0}".format(j) for j in range(ndim)])

    ops.append(
        """
        if (wvals[iw]) {{
            int ix = {expr};
            if ({cond}) {{
                if (!{border_value}) {{
                    y = (Y){false_val};
                    return;
                }}
            }} else {{
                bool nn = x[ix] ? {true_val} : {false_val};
                if (!nn) {{
                    y = (Y){false_val};
                    return;
                }}
            }}
        }}
        """.format(
            cond=_cond,
            expr=_expr,
            true_val=int(true_val),
            false_val=int(false_val),
            border_value=int(border_value),
        )
    )

    ops.append("}" * ndim)
    operation = "\n".join(ops)

    invert = true_val == 0
    name = "cupy_ndimage_erode_{}d_inv{}_x{}_w{}".format(
        ndim,
        invert,
        "_".join(["{}".format(j) for j in xshape]),
        "_".join(["{}".format(j) for j in fshape]),
    )
    return in_params, out_params, operation, name


# @cupy.util.memoize()
def _get_erode_kernel(
    xshape, fshape, origin, center_is_true, border_value, invert, masked
):
    if invert:
        border_value = int(not border_value)
        true_val = 0
        false_val = 1
    else:
        true_val = 1
        false_val = 0

    in_params, out_params, operation, name = _generate_erode_kernel(
        xshape,
        fshape,
        origin,
        center_is_true,
        border_value,
        true_val,
        false_val,
        masked,
    )
    return cupy.ElementwiseKernel(in_params, out_params, operation, name)