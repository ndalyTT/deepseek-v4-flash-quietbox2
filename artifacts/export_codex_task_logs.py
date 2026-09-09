"""Export one Codex thread tree from the local paginated history databases."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root-thread", required=True)
    parser.add_argument("--state-db", type=Path, required=True)
    parser.add_argument("--history-db", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def _readonly(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)


def _thread_tree(state: sqlite3.Connection, root_thread: str) -> list[dict[str, Any]]:
    rows = state.execute(
        """
        WITH RECURSIVE tree(id, depth) AS (
            SELECT ?, 0
            UNION ALL
            SELECT edge.child_thread_id, tree.depth + 1
            FROM thread_spawn_edges AS edge
            JOIN tree ON edge.parent_thread_id = tree.id
        )
        SELECT tree.depth, threads.id, threads.agent_nickname,
               threads.agent_role, threads.agent_path, threads.title,
               threads.created_at_ms, threads.updated_at_ms,
               threads.model, threads.reasoning_effort
        FROM tree JOIN threads ON threads.id = tree.id
        ORDER BY tree.depth, threads.created_at_ms
        """,
        (root_thread,),
    ).fetchall()
    if not rows:
        raise RuntimeError(f"root thread is not present in state DB: {root_thread}")
    names = (
        "depth",
        "thread_id",
        "agent_nickname",
        "agent_role",
        "agent_path",
        "title",
        "created_at_ms",
        "updated_at_ms",
        "model",
        "reasoning_effort",
    )
    return [dict(zip(names, row, strict=True)) for row in rows]


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    state = _readonly(args.state_db)
    history = _readonly(args.history_db)
    threads = _thread_tree(state, args.root_thread)
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "root_thread": args.root_thread,
        "scope": "root thread plus recursive thread_spawn_edges children",
        "threads": [],
    }
    for thread in threads:
        thread_id = thread["thread_id"]
        rows = history.execute(
            """
            SELECT thread_id, turn_id, item_id, rollout_ordinal,
                   created_at_ms, item_type, updated_at_ordinal, item_json
            FROM thread_items
            WHERE thread_id = ?
            ORDER BY rollout_ordinal, updated_at_ordinal, item_id
            """,
            (thread_id,),
        )
        output_path = args.output_dir / f"{thread_id}.jsonl"
        item_count = 0
        with output_path.open("w") as output:
            for row in rows:
                record = {
                    "thread_id": row[0],
                    "turn_id": row[1],
                    "item_id": row[2],
                    "rollout_ordinal": row[3],
                    "created_at_ms": row[4],
                    "item_type": row[5],
                    "updated_at_ordinal": row[6],
                    "item": json.loads(row[7]),
                }
                output.write(json.dumps(record, separators=(",", ":")) + "\n")
                item_count += 1
        manifest["threads"].append(
            {
                **thread,
                "item_count": item_count,
                "file": output_path.name,
                "bytes": output_path.stat().st_size,
            }
        )
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
