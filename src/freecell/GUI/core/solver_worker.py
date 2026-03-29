from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from multiprocessing import Process, Queue
from queue import Empty
from time import perf_counter

from freecell.core import Move, PackedState
from freecell.solvers.Astar import AstarSolver
from freecell.solvers.BFS import BFSSolver
from freecell.solvers.UCS import UCSSolver


def _solve_target(
    initial_state: PackedState,
    solver_name: str,
    max_expansions: int,
    queue: Queue,
) -> None:
    started = perf_counter()
    name = solver_name.upper()
    if name == "BFS":
        solver = BFSSolver()
    elif name in ("ASTAR", "A*"):
        solver = AstarSolver(max_expansions=max_expansions)
    else:
        solver = UCSSolver(max_expansions=max_expansions)

    result = solver.solve(initial_state)
    reason = "solved" if result.solved else "no_solution_within_limit"
    queue.put(
        {
            "status": "done",
            "solved": result.solved,
            "reason": reason,
            "elapsed_seconds": perf_counter() - started,
            "expanded_nodes": result.expanded_nodes,
            "moves": [dataclasses.astuple(move) for move in result.moves],
        }
    )


@dataclass(slots=True)
class SolverUpdate:
    status: str
    solved: bool = False
    reason: str = ""
    elapsed_seconds: float = 0.0
    expanded_nodes: int = 0
    moves: tuple[Move, ...] = ()


class SolverWorker:
    def __init__(self) -> None:
        self._queue: Queue | None = None
        self._process: Process | None = None
        self._started_at = 0.0

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.is_alive()

    def start(self, initial_state: PackedState, solver_name: str, max_expansions: int) -> None:
        self.stop()
        self._queue = Queue()
        self._process = Process(
            target=_solve_target,
            args=(initial_state, solver_name, max_expansions, self._queue),
            daemon=True,
        )
        self._process.start()
        self._started_at = perf_counter()

    def stop(self) -> None:
        if self._process is not None and self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=1.0)
        self._process = None
        self._queue = None

    def poll(self) -> SolverUpdate:
        if self._queue is None:
            return SolverUpdate(status="idle")

        try:
            payload = self._queue.get_nowait()
        except Empty:
            if self.is_running:
                return SolverUpdate(
                    status="running",
                    elapsed_seconds=perf_counter() - self._started_at,
                )
            return SolverUpdate(status="idle")

        return SolverUpdate(
            status=payload["status"],
            solved=bool(payload.get("solved", False)),
            reason=str(payload.get("reason", "")),
            elapsed_seconds=float(payload.get("elapsed_seconds", 0.0)),
            expanded_nodes=int(payload.get("expanded_nodes", 0)),
            moves=tuple(Move(*entry) for entry in payload.get("moves", [])),
        )
