from ..type cimport type

cdef extern from 'types/pyobject_type.hpp':
    int pyobject_type_id

    cdef cppclass pyobject_type:
        pass
