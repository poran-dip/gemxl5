"""gem5 SE-mode baseline: one workload, all-local DRAM of configurable size.
Run:  gem5.opt -d <outdir> configs/run.py --binary build/m5/stream --mem-size 64MiB -- -s 8 -i 2
Everything after '--' is passed to the workload.
"""

import argparse

from gem5.components.boards.simple_board import SimpleBoard
from gem5.components.cachehierarchies.classic.private_l1_private_l2_cache_hierarchy import (
    PrivateL1PrivateL2CacheHierarchy,
)
from gem5.components.memory.single_channel import SingleChannelDDR4_2400
from gem5.components.processors.cpu_types import CPUTypes
from gem5.components.processors.simple_processor import SimpleProcessor
from gem5.isas import ISA
from gem5.resources.resource import BinaryResource
from gem5.simulate.simulator import Simulator
from gem5.utils.requires import requires

requires(isa_required=ISA.X86)

p = argparse.ArgumentParser()
p.add_argument("--binary", required=True)
p.add_argument("--mem-size", default="64MiB", help="simulated local DRAM size")
p.add_argument("--cpu", choices=["atomic", "timing", "o3"], default="timing")
p.add_argument("--clk", default="3GHz")
p.add_argument("--l1d", default="32KiB")
p.add_argument("--l1i", default="32KiB")
p.add_argument("--l2", default="256KiB", help="keep small so MB-scale working sets reach DRAM")
p.add_argument("wl_args", nargs=argparse.REMAINDER)
a = p.parse_args()
wl_args = [x for x in a.wl_args if x != "--"]

cpu = {"atomic": CPUTypes.ATOMIC, "timing": CPUTypes.TIMING, "o3": CPUTypes.O3}[a.cpu]
board = SimpleBoard(
    clk_freq=a.clk,
    processor=SimpleProcessor(cpu_type=cpu, isa=ISA.X86, num_cores=1),
    memory=SingleChannelDDR4_2400(size=a.mem_size),
    cache_hierarchy=PrivateL1PrivateL2CacheHierarchy(l1d_size=a.l1d, l1i_size=a.l1i, l2_size=a.l2),
)
board.set_se_binary_workload(binary=BinaryResource(local_path=a.binary), arguments=wl_args)

sim = Simulator(board=board)
sim.run()
print(f"EXIT cause={sim.get_last_exit_event_cause()} tick={sim.get_current_tick()}")
