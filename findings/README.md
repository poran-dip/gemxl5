# Findings

One file per result, numbered in the order they were found. Each states what was run, what the
data shows, what it does **not** show, and what it changes in the plan. Raw data lives in
`results/`; a finding points at the CSV and the command that produced it.

Status of a finding: **established** (the data supports it and the measurement is sound),
**tentative** (consistent with the data, but not yet tested directly), or **hypothesis** (an
expectation the data suggests, to be tested later).

| #                                   | Finding                                                                                                                  | Source                     | Date       |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | -------------------------- | ---------- |
| [001](001-native-capacity-cliff.md) | With swap as the only overflow, workloads either degrade gradually or fall off a cliff once they no longer fit in memory | `results/native_sweep.csv` | 2026-10-08 |
