# C to C++ Migration Plan: pgvector

## 1. Executive Summary

This document outlines a comprehensive, phased plan to migrate the `pgvector` C codebase to modern C++ (C++20). The project, a PostgreSQL extension for vector similarity search, is currently written in C. The migration will focus on improving code maintainability, safety, and robustness by introducing modern C++ features like RAII, object-oriented programming, and a modern build system.

The goal is to produce a clean, modular, and well-tested C++ library while maintaining a stable C API for compatibility with the PostgreSQL ecosystem. The final codebase will be easier to extend and maintain, with improved safety and performance.

### Assumptions & Open Questions
*   **Assumption**: The primary goal is to improve the internal implementation, while the public C API exposed to PostgreSQL remains stable.
*   **Assumption**: The migration will target C++20.
*   **Assumption**: The project will use GoogleTest for unit testing.
*   **Open Question**: What is the current test coverage? This plan assumes a baseline needs to be established.

## 2. Inventory & Architecture Map

### Source Code Inventory
The `src` directory contains the core logic, which can be grouped into the following modules:

*   **Vector (`vector.c`, `vector.h`)**: Core vector data type and functions.
*   **HNSW (`hnsw.c`, `hnsw.h`, `hnswbuild.c`, `hnswinsert.c`, `hnswscan.c`, `hnswutils.c`, `hnswvacuum.c`)**: Implementation of the HNSW index for approximate nearest neighbor search.
*   **IVF (`ivfflat.c`, `ivfflat.h`, `ivfbuild.c`, `ivfinsert.c`, `ivfscan.c`, `ivfutils.c`, `ivfvacuum.c`, `ivfkmeans.c`)**: Implementation of the IVF index.
*   **Half Precision (`halfvec.c`, `halfvec.h`, `halfutils.c`, `halfutils.h`)**: Support for half-precision floating-point vectors.
*   **Bit Vector (`bitvec.c`, `bitvec.h`, `bitutils.c`, `bitutils.h`)**: Support for binary vectors.
*   **Sparse Vector (`sparsevec.c`, `sparsevec.h`)**: Support for sparse vectors.

### Architecture
*   **Entrypoints**: The library is a PostgreSQL extension, so its entrypoints are the functions defined in `vector.c` and other files that are exposed to PostgreSQL using the `PG_FUNCTION_INFO_V1` macro.
*   **Global State**: The code uses PostgreSQL's memory management (`palloc`) and error handling (`ereport`, `elog`), which rely on PostgreSQL's global state.
*   **Memory Management**: Memory is managed manually using `palloc` and `pfree`. This is a critical area for migration to RAII.
*   **Error Handling**: Error handling is done via PostgreSQL's `ereport` and `elog` functions, which typically throw longjmp exceptions.
*   **Build System**: The project currently uses Makefiles (`Makefile`, `Makefile.win`). This will be migrated to CMake.

## 3. Design Principles for the Migration

*   **Ownership & Lifetime**: RAII will be the cornerstone of the migration. `palloc`/`pfree` will be wrapped in C++ containers and smart pointers. `std::vector` will be used for dynamic arrays.
*   **Strings & Collections**: `std::string` and `std::string_view` will be used for string manipulation where appropriate, although most of the library deals with raw binary data. `std::vector` will be the default container.
*   **Namespaces**: A top-level namespace, `pgvector`, will be introduced. Sub-namespaces will be created for different modules (e.g., `pgvector::hnsw`, `pgvector::ivf`).
*   **Error Handling**: Internal C++ code will use exceptions for error handling. A catch-all boundary will be established at the C API layer to translate exceptions into PostgreSQL errors using `ereport`.
*   **APIs**: The existing C API for PostgreSQL will be preserved using `extern "C"`. All internal implementation will be idiomatic C++.
*   **Build**: A modern CMake build system will be created with clear targets and dependency management.
*   **Static Analysis**: `clang-tidy` and `clang-format` will be used to enforce code quality and style.

## 4. C→C++ Mapping Guide

| C Pattern | C++ Equivalent | Notes |
|---|---|---|
| `struct + function_*` | `class` with private data + public methods | Encapsulate data and behavior. |
| `palloc`/`pfree` | `std::vector`, `std::unique_ptr` with custom deleter | Use RAII to manage memory. |
| C-style arrays | `std::vector`, `std::array`, `gsl::span` | Prefer C++ containers for safety and convenience. |
| `enum` | `enum class` | For type-safe enumerations. |
| Macros | `constexpr`, `inline` functions, templates | Reduce macro usage to improve debuggability. |
| `(void *)` pointers | Templates, `std::variant`, `std::any` | Improve type safety. |
| Global state | Dependency injection, singletons | Limit and manage global state. |

## 5. Phased Plan (Milestones & Steps)

### Phase 0: Safety Net

#### Step 1: Introduce CMake
```json
{
  "id": "PHASE_0_STEP_1",
  "title": "Introduce CMake build system",
  "rationale": "Create a modern, cross-platform build system to replace the existing Makefiles. This is a prerequisite for integrating tools like GoogleTest and for a more structured build process.",
  "preconditions": [
    "Repository contains existing Makefiles."
  ],
  "changes": {
    "files_glob": ["*"],
    "actions": [
      {"type": "create_file", "path": "CMakeLists.txt", "content": "cmake_minimum_required(VERSION 3.16)\nproject(pgvector CXX C)\n\n# Add source files\nfile(GLOB_RECURSE SOURCES src/*.c src/*.h)\n\n# This is a placeholder. A proper CMake setup for PG extensions is more complex.\nadd_library(pgvector MODULE ${SOURCES})\n"}
    ]
  },
  "build_and_test": {
    "configure": ["# CMake configuration will be refined in later steps"],
    "build": ["# Build will be enabled once CMake is fully configured"],
    "tests": [],
    "sanitizers": []
  },
  "acceptance_criteria": [
    "A root CMakeLists.txt file is created.",
    "The project can be configured with CMake, even if it doesn't build successfully yet."
  ],
  "rollback": "git checkout -- CMakeLists.txt",
  "estimated_runtime_minutes": 30
}
```
This step introduces a basic CMake build system. The initial `CMakeLists.txt` will be simple and will be expanded in later steps to handle PostgreSQL extensions correctly.

#### Step 2: Add GoogleTest
```json
{
  "id": "PHASE_0_STEP_2",
  "title": "Add GoogleTest for unit testing",
  "rationale": "Integrate GoogleTest to create a safety net of unit tests. This allows us to verify that refactoring does not break existing functionality.",
  "preconditions": [
    "CMakeLists.txt exists."
  ],
  "changes": {
    "files_glob": ["CMakeLists.txt", "test/*"],
    "actions": [
      {"type": "execute_command", "command": "git submodule add https://github.com/google/googletest.git test/googletest"},
      {"type": "modify_file", "path": "CMakeLists.txt", "description": "Add GoogleTest to the CMake build."},
      {"type": "create_file", "path": "test/main.cpp", "content": "#include <gtest/gtest.h>\n\nint main(int argc, char **argv) {\n  ::testing::InitGoogleTest(&argc, argv);\n  return RUN_ALL_TESTS();\n}"}
    ]
  },
  "build_and_test": {
    "configure": ["cmake -S . -B build"],
    "build": ["cmake --build build"],
    "tests": ["ctest --test-dir build"],
    "sanitizers": []
  },
  "acceptance_criteria": [
    "GoogleTest is added as a submodule.",
    "A basic test runner is created.",
    "The test suite can be built and run, even if there are no tests yet."
  ],
  "rollback": "git submodule deinit -f test/googletest && git rm -f test/googletest && git checkout -- CMakeLists.txt test/main.cpp",
  "estimated_runtime_minutes": 20
}
```
This step integrates GoogleTest, providing the foundation for unit testing during the migration.

### Phase 1: Mechanical Preparation

#### Step 1: Rename C sources to C++
```json
{
  "id": "PHASE_1_STEP_1",
  "title": "Rename .c/.h files to .cpp/.hpp",
  "rationale": "Rename all C source and header files to C++ extensions to allow the compiler to treat them as C++ files. This is a necessary first step before introducing C++ features.",
  "preconditions": [
    "All source files have .c and .h extensions."
  ],
  "changes": {
    "files_glob": ["src/*"],
    "actions": [
      {"type": "rename_ext", "from_ext": ".c", "to_ext": ".cpp", "filter": "src/*.c"},
      {"type": "rename_ext", "from_ext": ".h", "to_ext": ".hpp", "filter": "src/*.h"}
    ]
  },
  "build_and_test": {
    "configure": ["cmake -S . -B build"],
    "build": ["cmake --build build"],
    "tests": ["ctest --test-dir build"],
    "sanitizers": []
  },
  "acceptance_criteria": [
    "All .c files in src/ are renamed to .cpp.",
    "All .h files in src/ are renamed to .hpp.",
    "The project still compiles successfully as C++."
  ],
  "rollback": "git checkout -- src/",
  "estimated_runtime_minutes": 15
}
```
This step is a bulk rename of files to signal the transition to C++. The code should still compile as C-in-C++.

#### Step 2: Wrap headers with `extern "C"`
```json
{
  "id": "PHASE_1_STEP_2",
  "title": "Wrap headers with extern \"C\"",
  "rationale": "Wrap all public headers with `extern \"C\"` to prevent C++ name mangling, ensuring that the C API remains compatible with PostgreSQL.",
  "preconditions": [
    "Header files have .hpp extensions."
  ],
  "changes": {
    "files_glob": ["src/*.hpp"],
    "actions": [
      {"type": "codemod", "tool": "custom", "description": "Wrap all header content in `extern \"C\" { ... }` if it's a C API header."}
    ]
  },
  "build_and_test": {
    "configure": ["cmake -S . -B build"],
    "build": ["cmake --build build"],
    "tests": ["ctest --test-dir build"],
    "sanitizers": []
  },
  "acceptance_criteria": [
    "All public C API headers are wrapped in `extern \"C\"`.",
    "The project compiles and links correctly."
  ],
  "rollback": "git checkout -- src/",
  "estimated_runtime_minutes": 20
}
```
This step ensures that the C interface to PostgreSQL is maintained during the migration.

### Phase 2: Data Ownership and Encapsulation

#### Step 1: Convert `Vector` to a C++ class
```json
{
  "id": "PHASE_2_STEP_1",
  "title": "Convert `Vector` struct and functions to a C++ class",
  "rationale": "Convert the core `Vector` data structure and its associated C functions into a C++ class. This will encapsulate the data and logic, and is the first step towards an object-oriented design.",
  "preconditions": [
    "src/vector.cpp and src/vector.hpp exist."
  ],
  "changes": {
    "files_glob": ["src/vector.cpp", "src/vector.hpp"],
    "actions": [
      {"type": "refactor", "description": "Create a `pgvector::Vector` class from the `Vector` struct. Move related functions like `vector_add` into the class as methods. Use `std::vector<float>` for the data.", "targets": ["src/vector.cpp", "src/vector.hpp"]}
    ]
  },
  "build_and_test": {
    "configure": ["cmake -S . -B build"],
    "build": ["cmake --build build"],
    "tests": ["ctest --test-dir build"],
    "sanitizers": ["ASAN", "UBSAN"]
  },
  "acceptance_criteria": [
    "A `pgvector::Vector` class is created.",
    "The new class is used in the rest of the codebase.",
    "All existing tests pass."
  ],
  "rollback": "git checkout -- src/vector.cpp src/vector.hpp",
  "estimated_runtime_minutes": 60
}
```
This is a major step that starts the process of converting C-style code to C++. The `Vector` data structure is a good candidate for the first conversion.

## 6. Testing & CI Strategy

*   **Unit Tests**: GoogleTest will be used to write unit tests for each class as it is migrated. Tests will be added to the `test/` directory.
*   **CI**: A GitHub Actions workflow will be created to:
    *   Build the project on Linux, macOS, and Windows.
    *   Run all unit tests.
    *   Run with AddressSanitizer (ASAN) and UndefinedBehaviorSanitizer (UBSAN) to detect memory errors and undefined behavior.
    *   Run `clang-format` to check for code style.
    *   Run `clang-tidy` to check for common C++ pitfalls.
*   **Coverage**: Code coverage will be measured using `gcov` or `lcov` and uploaded to a service like Codecov. The target coverage for migrated code will be 80%.

## 7. Risk & Rollback

*   **Risks**:
    *   **Performance Regression**: The introduction of C++ abstractions could lead to performance regressions. This will be mitigated by benchmarking critical code paths before and after migration.
    *   **ABI Incompatibility**: Changes to the C API could break compatibility with PostgreSQL. This will be mitigated by carefully managing the `extern "C"` interface and running integration tests.
    *   **Increased Complexity**: Overuse of complex C++ features could make the code harder to understand. The migration will focus on using a clean, modern, but not overly complex subset of C++.
*   **Rollback**: Each step in the phased plan is designed to be a small, atomic change. If a step introduces a problem, it can be reverted using `git checkout` or `git revert`. The CI system will help to catch issues early.

## 8. Acceptance Criteria

*   The entire codebase is migrated to modern C++ (C++20).
*   The project builds cleanly with CMake on Linux, macOS, and Windows.
*   The public C API for PostgreSQL is preserved and remains stable.
*   All unit tests pass.
*   Code coverage is at least 80% for all migrated code.
*   The project passes checks with ASAN, UBSAN, `clang-format`, and `clang-tidy`.
*   The `README.md` is updated with new build and installation instructions.
