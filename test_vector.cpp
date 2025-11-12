#include <iostream>
#include <cstring>
#include "src_cpp/vector.hpp"

int main() {
    using namespace pgvector::cpp;
    
    // Test basic Vector class functionality
    constexpr int dim = 5;
    
    // Allocate memory for vector
    void* mem = std::malloc(Vector::size(dim));
    Vector* vec = new (mem) Vector(dim);
    
    // Test getDim()
    std::cout << "Vector dimension: " << vec->getDim() << std::endl;
    
    // Test getData()
    float* data = vec->getData();
    for (int i = 0; i < vec->getDim(); ++i) {
        data[i] = static_cast<float>(i);
    }
    
    std::cout << "Vector data: ";
    for (int i = 0; i < vec->getDim(); ++i) {
        std::cout << data[i] << " ";
    }
    std::cout << std::endl;
    
    // Test move semantics by creating a new vector and moving from it
    void* mem2 = std::malloc(Vector::size(dim));
    Vector* vec2 = new (mem2) Vector(0);  // Start with 0 dimension
    *vec2 = std::move(*vec);  // Move assignment
    
    std::cout << "After move - original vector dimension: " << vec->getDim() << std::endl;
    std::cout << "After move - new vector dimension: " << vec2->getDim() << std::endl;
    
    // Test size calculation
    std::cout << "Vector size for dimension " << dim << ": " << Vector::size(dim) << std::endl;
    
    // Clean up
    std::free(mem);
    std::free(mem2);
    
    return 0;
}
