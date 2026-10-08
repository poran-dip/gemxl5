// LLM-decode proxy. 70% of working set = weight matrix (streamed by matvec each token),
// 30% = KV cache (scanned by attention each token). iters = tokens. work = bytes read.
#include "common.h"
#include <cmath>
int main(int argc, char** argv) {
    Args a = parse_args(argc, argv);
    const size_t C = 2048, D = 128;
    size_t total = a.bytes();
    size_t R = (size_t)(total * 0.7) / (C * 4);
    size_t T = (size_t)(total * 0.3) / (2 * D * 4);
    float* W = (float*)alloc64(R * C * 4);
    float* K = (float*)alloc64(T * D * 4);
    float* V = (float*)alloc64(T * D * 4);
    float* x = (float*)alloc64(C * 4);
    float* y = (float*)alloc64(R * 4);
    float* sc = (float*)alloc64(T * 4);
    Rng r(a.seed);
    for (size_t i = 0; i < R * C; i++)
        W[i] = (r.unit() - 0.5f) * 0.02f;
    for (size_t i = 0; i < T * D; i++) {
        K[i] = r.unit() - 0.5f;
        V[i] = r.unit() - 0.5f;
    }
    for (size_t i = 0; i < C; i++)
        x[i] = r.unit();
    float out[D];
    roi_begin();
    for (int tok = 0; tok < a.iters; tok++) {
        for (size_t i = 0; i < R; i++) { // matvec: stream all weights
            float acc = 0;
            const float* w = W + i * C;
            for (size_t c = 0; c < C; c++)
                acc += w[c] * x[c];
            y[i] = acc;
        }
        const float* q = y;              // first D outputs act as the query
        for (size_t t = 0; t < T; t++) { // attention scores: scan K
            float d = 0;
            const float* k = K + t * D;
            for (size_t j = 0; j < D; j++)
                d += k[j] * q[j];
            sc[t] = d * (1.0f / D);
        }
        for (float& o : out)
            o = 0;
        for (size_t t = 0; t < T; t++) { // weighted sum: scan V
            const float* v = V + t * D;
            float s = sc[t];
            for (size_t j = 0; j < D; j++)
                out[j] += s * v[j];
        }
        for (size_t c = 0; c < C; c++)
            x[c] = 0.5f * x[c] + 1e-3f * y[c % R] + 1e-3f * out[c % D];
    }
    double sec = roi_end();
    float s = 0;
    for (size_t c = 0; c < C; c++)
        s += x[c];
    uint32_t bits;
    memcpy(&bits, &s, 4);
    double bytes = ((double)R * C + 2.0 * T * D) * 4 * a.iters;
    report("kvdecode", a, sec, bytes, bits);
}
