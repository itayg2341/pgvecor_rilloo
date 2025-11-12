#ifndef VECTOR_HPP
#define VECTOR_HPP

#include <cstdint>
#include <cstring>
#include <vector>
#include <memory>

// Forward declare PostgreSQL types if not available
extern "C" {
    typedef uintptr_t Datum;
    typedef struct varlena* (*PG_DETOAST_DATUM_FUNC)(Datum datum);
    typedef Datum (*PG_RETURN_POINTER_FUNC)(void* pointer);
    
    // These would normally come from postgres.h
    static PG_DETOAST_DATUM_FUNC PG_DETOAST_DATUM = nullptr;
    static PG_RETURN_POINTER_FUNC PG_RETURN_POINTER = nullptr;
}

namespace pgvector {
namespace cpp {

constexpr int32_t VECTOR_MAX_DIM = 16000;

class Vector {
private:
    int32_t vl_len_;  // varlena header (do not touch directly!)
    int16_t dim;      // number of dimensions
    int16_t unused;   // reserved for future use, always zero

public:
    float x[];  // flexible array member

    // Constructor
    explicit Vector(int16_t d) : vl_len_(0), dim(d), unused(0) {
        std::memset(x, 0, dim * sizeof(float));
    }

    // Destructor
    ~Vector() = default;

    // Move constructor
    Vector(Vector&& other) noexcept : vl_len_(other.vl_len_), dim(other.dim), unused(other.unused) {
        std::memcpy(x, other.x, dim * sizeof(float));
        other.vl_len_ = 0;
        other.dim = 0;
    }

    // Move assignment
    Vector& operator=(Vector&& other) noexcept {
        if (this != &other) {
            vl_len_ = other.vl_len_;
            dim = other.dim;
            unused = other.unused;
            std::memcpy(x, other.x, dim * sizeof(float));
            other.vl_len_ = 0;
            other.dim = 0;
        }
        return *this;
    }

    // Delete copy constructor and assignment
    Vector(const Vector&) = delete;
    Vector& operator=(const Vector&) = delete;

    // Accessors
    int16_t getDim() const { return dim; }
    const float* getData() const { return x; }
    float* getData() { return x; }

    // Size calculation
    static constexpr size_t size(int16_t d) {
        return sizeof(Vector) + sizeof(float) * d;
    }
};

// Inline functions instead of macros
inline Vector* datumGetVector(Datum datum) {
    if (PG_DETOAST_DATUM) {
        return reinterpret_cast<Vector*>(PG_DETOAST_DATUM(datum));
    }
    return nullptr;
}

inline Vector* pgGetArgVector(int arg) {
    // This would normally use PG_GETARG_DATUM(arg)
    return nullptr;
}

inline Datum pgReturnVector(Vector* vec) {
    if (PG_RETURN_POINTER) {
        return PG_RETURN_POINTER(vec);
    }
    return 0;
}

// External functions
Vector* InitVector(int dim);
void PrintVector(const char* msg, Vector* vector);
int vector_cmp_internal(Vector* a, Vector* b);

} // namespace cpp
} // namespace pgvector

#endif // VECTOR_HPP
