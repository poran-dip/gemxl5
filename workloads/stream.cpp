// STREAM triad: A = B + 3*C. work = bytes moved (24 B/element/iter).
#include "common.h"
int main(int argc, char** argv) {
    Args a = parse_args(argc, argv);
    size_t n = (a.bytes() / (3 * sizeof(double))) & ~size_t(7);
    double *A = (double*)alloc64(n * 8), *B = (double*)alloc64(n * 8), *C = (double*)alloc64(n * 8);
    Rng r(a.seed);
    for (size_t i = 0; i < n; i++) { A[i] = 0; B[i] = r.unit(); C[i] = r.unit(); }
    roi_begin();
    for (int it = 0; it < a.iters; it++)
        for (size_t i = 0; i < n; i++) A[i] = B[i] + 3.0 * C[i];
    double sec = roi_end();
    double s = 0; for (size_t i = 0; i < n; i += 97) s += A[i];
    report("stream", a, sec, 24.0 * n * a.iters, (uint64_t)(s * 1000));
}
