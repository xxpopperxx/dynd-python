//
// Copyright (C) 2011-13 Mark Wiebe, DyND Developers
// BSD 2-Clause License, see LICENSE.txt
//
// This header defines some wrapping functions to
// access various dtype parameters
//

#ifndef _DYND__DTYPE_FUNCTIONS_HPP_
#define _DYND__DTYPE_FUNCTIONS_HPP_

#include "Python.h"

#include <sstream>

#include <dynd/type.hpp>
#include <dynd/string_encodings.hpp>
#include "placement_wrappers.hpp"

namespace pydynd {

/**
 * This is the typeobject and struct of w_type from Cython.
 */
extern PyTypeObject *WType_Type;
inline bool WType_CheckExact(PyObject *obj) {
    return Py_TYPE(obj) == WType_Type;
}
inline bool WType_Check(PyObject *obj) {
    return PyObject_TypeCheck(obj, WType_Type);
}
struct WType {
  PyObject_HEAD;
  // This is ndt_type_placement_wrapper in Cython-land
  dynd::ndt::type v;
};
void init_w_type_typeobject(PyObject *type);

inline PyObject *wrap_ndt_type(const dynd::ndt::type& d) {
    WType *result = (WType *)WType_Type->tp_alloc(WType_Type, 0);
    if (!result) {
        throw std::runtime_error("");
    }
    // Calling tp_alloc doesn't call Cython's __cinit__, so do the placement new here
    pydynd::placement_new(reinterpret_cast<pydynd::ndt_type_placement_wrapper &>(result->v));
    result->v = d;
    return (PyObject *)result;
}
#ifdef DYND_RVALUE_REFS
inline PyObject *wrap_dtype(dynd::ndt::type&& d) {
    WType *result = (WType *)WType_Type->tp_alloc(WType_Type, 0);
    if (!result) {
        throw std::runtime_error("");
    }
    // Calling tp_alloc doesn't call Cython's __cinit__, so do the placement new here
    pydynd::placement_new(reinterpret_cast<pydynd::ndt_type_placement_wrapper &>(result->v));
    result->v = DYND_MOVE(d);
    return (PyObject *)result;
}
#endif

inline std::string dtype_str(const dynd::ndt::type& d)
{
    std::stringstream ss;
    ss << d;
    return ss.str();
}

std::string dtype_repr(const dynd::ndt::type& d);

/**
 * Returns the kind of the dtype, as a Python string.
 */
PyObject *dtype_get_kind(const dynd::ndt::type& d);

/**
 * Returns the type id of the dtype, as a Python string.
 */
PyObject *dtype_get_type_id(const dynd::ndt::type& d);

/**
 * Produces a dynd::dtype corresponding to the object's type. This
 * is to determine the dtype of an object that contains a value
 * or values.
 */
dynd::ndt::type deduce_dtype_from_pyobject(PyObject* obj);

/**
 * Converts a Python type, Numpy dtype, or string
 * into a dtype. This raises an error if given an object
 * which contains values, it is for dtype-like things only.
 */
dynd::ndt::type make_ndt_type_from_pyobject(PyObject* obj);

/**
 * Creates a convert dtype.
 */
dynd::ndt::type dynd_make_convert_type(const dynd::ndt::type& to_dtype, const dynd::ndt::type& from_dtype, PyObject *errmode);

/**
 * Creates a view dtype.
 */
dynd::ndt::type dynd_make_view_type(const dynd::ndt::type& value_type, const dynd::ndt::type& operand_type);

/**
 * Creates a fixed-sized string dtype.
 */
dynd::ndt::type dynd_make_fixedstring_type(intptr_t size, PyObject *encoding_obj);

/**
 * Creates a blockref string dtype.
 */
dynd::ndt::type dynd_make_string_type(PyObject *encoding_obj);

/**
 * Creates a blockref pointer dtype.
 */
dynd::ndt::type dynd_make_pointer_type(const dynd::ndt::type& target_dtype);

dynd::ndt::type dynd_make_struct_type(PyObject *field_types, PyObject *field_names);
dynd::ndt::type dynd_make_cstruct_type(PyObject *field_types, PyObject *field_names);
dynd::ndt::type dynd_make_fixed_dim_type(PyObject *shape, const dynd::ndt::type& element_dtype, PyObject *axis_perm);

/**
 * Implementation of __getitem__ for the wrapped dtype object.
 */
dynd::ndt::type dtype_getitem(const dynd::ndt::type& d, PyObject *subscript);

PyObject *dtype_array_property_names(const dynd::ndt::type& d);

} // namespace pydynd

#endif // _DYND__DTYPE_FUNCTIONS_HPP_
