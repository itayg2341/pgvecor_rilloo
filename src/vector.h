#ifndef VECTOR_H
#define VECTOR_H

#include <cstddef>

#define VECTOR_MAX_DIM 16000

class Vector {
public:
    int32 vl_len_; // varlena header (do not touch directly!)
    int16 dim;     // number of dimensions
    int16 unused;  // reserved for future use, always zero
    float x[1];    // flexible array member

    Vector(int16 dim);
    ~Vector();

    static size_t size(int16 dim);
    static Vector* init(int16 dim);

    void print(char* msg);
    int compare(const Vector& other) const;
};

#define DatumGetVector(x) ((Vector *) PG_DETOAST_DATUM(x))
#define PG_GETARG_VECTOR_P(x) DatumGetVector(PG_GETARG_DATUM(x))
#define PG_RETURN_VECTOR_P(x) PG_RETURN_POINTER(x)

/* TODO Move to better place */
#if PG_VERSION_NUM >= 160000
#define FUNCTION_PREFIX
#else
#define FUNCTION_PREFIX PGDLLEXPORT
#endif

#endif


