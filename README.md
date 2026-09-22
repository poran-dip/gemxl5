# Tiered Memory Architecture

Evaluating CXL-style multi-tier memory systems — from local DRAM to CXL-attached memory and computational storage — using the gem5 architectural simulator, with a focus on AI inference/matrix workloads, evaluating latency, IPC, and cost-normalized performance.

## Motivation

DDR5 memory prices have spiked with AI datacenter demand, while older memory modules and alternative storage tiers remain comparatively cheap. Attaching lower-cost memory over a CXL/PCIe bus is one answer, but the tradeoffs — latency, bandwidth, and how workloads actually behave across a tiered hierarchy — aren't well characterized yet, especially for AI inference and matrix-heavy workloads at the gem5 microarchitecture level. This project uses gem5 to model that hierarchy directly and measure what it actually costs and gains.

## Scope

The project started from a 2-tier spec (fast local DRAM vs. high-latency PCIe memory) and has since grown into a 3–4 tier model, closer to a real datacenter stack:

- **GPU-local memory** (HBM/GDDR) at the top
- **Local DDR5**
- **DDR4**, either as a second local tier or CXL-attached, depending on the topology being tested
- **Computational storage** (in-/near-storage compute) as the slowest, largest tier

Both topology variants — DDR4 as a local tier vs. DDR4 as the CXL-attached tier with storage a rung below — are being explored as configurations of the same parameterized simulation setup, rather than committing to one upfront.

Alongside the usual IPC, bandwidth, and latency measurements, this project also aims to report a **cost-normalized performance metric** ($/GB-effective or similar), since that's the gap the existing literature leaves most open.

## Repo structure

```bash
tiered-memory
└── docs
    └── literature-review.md    # papers reviewed, grouped by topic
```

More will land here as the project moves past the literature-review stage: gem5 configuration scripts (Python), any custom C++ device models, benchmark/workload harnesses, result data, and eventually the LaTeX source for the final report.

## Tech stack

- **gem5** — architectural simulator, core of the project
- **Python** — gem5 stdlib config scripts, workload harnesses, data analysis (Matplotlib/Pandas)
- **C++** — only if/when custom gem5 device models are needed
- **LaTeX** — final report
- Formatting/linting: Biome + Prettier for this repo's JS/TS/Markdown tooling; clang-format, black/ruff, and LaTeX tooling (latexindent, chktex) to be added once gem5 and report work start

## Status

Literature review in progress — see [`docs/literature-review.md`](docs/literature-review.md). No simulation results yet.
