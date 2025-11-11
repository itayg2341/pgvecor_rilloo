#ifndef SPARSEVEC_H
#define SPARSEVEC_H

#include <cstddef>

#define SPARSEVEC_MAX_DIM 1000000000
#define SPARSEVEC_MAX_NNZ 16000

class SparseVector {
public:
    int32 vl_len_; // varlena header (do not touch directly!)
    int32 dim;     // number of dimensions
    int32 nnz;     // number of non-zero elements
    int32 unused;  // reserved for future use, always zero
    int32 indices[1]; // flexible array member

    SparseVector(int32 dim, int32 nnz);

    static size_t size(int32 nnz);
    static SparseVector* init(int32 dim, int32 nnz);

    float* values() const;
};

#define DatumGetSparseVector(x) ((SparseVector *) PG_DETOAST_DATUM(x))
#define PG_GETARG_SPARSEVEC_P(x) DatumGetSparseVector(PG_GETARG_DATUM(x))
#define PG_RETURN_SPARSEVEC_P(x) PG_RETURN_POINTER(x)

#endif

