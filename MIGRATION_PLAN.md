# C to C++ Migration Plan for pgvector

## 1. Introduction

This document outlines a staged plan for migrating the `pgvector` C codebase to modern C++ (C++20). The plan is based on a file-level dependency analysis of the source code.

The primary goal is to modernize the codebase, improving type safety, maintainability, and enabling the use of modern C++ features, while ensuring correctness and performance are preserved.

## 2. Methodology

The migration plan was generated using the following methodology:

1.  **File Discovery:** All `.c` and `.h` files in the `src/` directory were identified as migration candidates.
2.  **Dependency Analysis:** Project-local `#include` directives were parsed to build a directed dependency graph. This shows which files depend on others.
3.  **Cycle Detection:** The graph was analyzed for strongly connected components (SCCs), also known as dependency cycles. No cycles were detected, which simplifies the migration process significantly.
4.  **Staging:** A topological sort of the dependency graph was performed to create a migration plan that starts with files that have no dependencies (leaf nodes) and progressively moves to more central, highly-connected files.

The machine-readable dependency data is available in `migration_plan.json`.

## 3. Staged Migration Plan

The migration is broken down into three sequential stages. Each stage must be completed and verified before the next one begins. For all stages, the C++ code must be wrapped in `extern "C"` blocks where necessary to maintain ABI compatibility with the PostgreSQL C interface.

---

### Stage 0: Foundational Headers

These files are the "leaf" nodes of the dependency graph. They define core data structures and function signatures but do not depend on any other local headers.

**Files to Migrate:**
- `src/bitutils.h`
- `src/bitvec.h`
- `src/halfvec.h`
- `src/sparsevec.h`
- `src/vector.h`

**Rationale:**
Migrating these headers first ensures that the foundational data types and interfaces are defined in C++ before any implementation code that uses them is touched.

**Risks & Challenges:**
- C-style structs and macros are prevalent. Care must be taken to convert them to C++ classes/structs and `constexpr` functions or constants where appropriate.
- PostgreSQL-specific C types (e.g., `PG_FUNCTION_ARGS`) must be handled correctly.

**Proposed Refactors:**
- Convert C-style structs to C++ `struct` or `class`, potentially adding member functions for behavior.
- Replace macros with `inline` or `constexpr` functions for improved type safety.
- Introduce C++ standard library types like `std::size_t` where appropriate.

**Verification Steps:**
- Ensure the project still compiles successfully as a C++ project (using a C++ compiler like `g++`).
- No functional changes are expected, so existing tests should continue to pass.

---

### Stage 1: Core Headers and First-Level Implementations

These files depend only on the foundational headers migrated in Stage 0. This stage involves migrating the next level of headers and the first set of simple implementation files.

**Files to Migrate:**
- `src/bitutils.c`
- `src/bitvec.c`
- `src/halfutils.h`
- `src/hnsw.h`
- `src/ivfflat.h`

**Rationale:**
This stage builds upon the foundation of Stage 0. Migrating these files tests the new C++ headers with actual implementation code. It introduces C++ compilation to `.c` files (which will be renamed to `.cpp`).

**Risks & Challenges:**
- C-style idioms like manual memory management (`palloc`, `pfree`) and pointer arithmetic will be encountered.
- Mixing C and C++ code requires careful management of `extern "C"` declarations to prevent linkage errors.

**Proposed Refactors:**
- Rename `.c` files to `.cpp`.
- Introduce RAII principles where possible, though direct use of `palloc`/`pfree` may still be necessary due to the PostgreSQL memory management context.
- Use C++ casts (`static_cast`, `reinterpret_cast`) instead of C-style casts.
- Begin introducing standard library containers like `std::vector` for temporary, function-local storage.

**Verification Steps:**
- The project must compile cleanly with a C++ compiler.
- Run the full test suite (`make installcheck`) to ensure no regressions have been introduced.

---

### Stage 2: Main Implementation Files

This final, large stage includes all the remaining implementation files. These files contain the bulk of the logic and depend on the headers migrated in the previous stages.

**Files to Migrate:**
- `src/halfutils.c`
- `src/halfvec.c`
- `src/hnsw.c`
- `src/hnswbuild.c`
- `src/hnswinsert.c`
- `src/hnswscan.c`
- `src/hnswutils.c`
- `src/hnswvacuum.c`
- `src/ivfbuild.c`
- `src/ivfflat.c`
- `src/ivfinsert.c`
- `src/ivfkmeans.c`
- `src/ivfscan.c`
- `src/ivfutils.c`
- `src/ivfvacuum.c`
- `src/sparsevec.c`
- `src/vector.c`

**Rationale:**
With all headers and interfaces migrated, the core logic can now be converted to C++. This is the most labor-intensive part of the migration.

**Risks & Challenges:**
- The complexity of the algorithms in these files (HNSW, IVF) may be tightly coupled to C-style memory layouts and performance optimizations.
- Performance is critical. C++ abstractions must be chosen carefully to avoid introducing overhead (zero-cost abstractions).

**Proposed Refactors:**
- Rename all remaining `.c` files to `.cpp`.
- Systematically replace raw pointer loops with iterator-based loops or range-based for loops where applicable.
- Encapsulate related functions and data into classes. For example, the HNSW and IVF functionalities could be organized into `HnswIndex` or `IvfIndex` classes.
- Use `std::unique_ptr` or similar smart pointers for memory that is not managed by PostgreSQL's memory contexts.

**Verification Steps:**
- The entire project must compile as C++.
- The full test suite must pass.
- Perform targeted performance benchmarks to ensure that key operations (indexing, querying) have not regressed.
