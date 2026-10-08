"""Constants shared by the reporting code."""

# One DRAM burst moves 64 B on a x64 channel with burst length 8 (DDR3/DDR4 as configured here).
BURST_BYTES = 64

# gem5's default tick is 1 ps.
TICKS_PER_NS = 1_000
TICKS_PER_SEC = 1e12

# A gem5 memory controller whose stat path matches this is counted as the slow (remote) tier.
# Name the second tier's controller accordingly when the two-tier config is built.
SLOW_TIER_PATTERN = r"slow|cxl|pcie"

# What one unit of each workload's "work" means (see the comment at the top of each workload).
WORK_UNIT = {
    "stream": "bytes",
    "chase": "hops",
    "gemm": "flops",
    "sort": "compares",
    "kvdecode": "bytes",
}
