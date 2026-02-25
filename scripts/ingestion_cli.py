#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json

from app.db import AsyncSessionLocal
from apps.ingestion.models import IngestionRunTrigger
from apps.ingestion.services import IngestionPipelineService, SourceRegistryService
from apps.ingestion.tasks import ingest_source_task


async def seed_sources() -> dict:
    async with AsyncSessionLocal() as db:
        service = SourceRegistryService(db)
        count = await service.seed_default_sources()
        return {"seeded": count}


async def reprocess_source(source_key: str, *, sync: bool, trace_id: str | None) -> dict:
    async with AsyncSessionLocal() as db:
        service = IngestionPipelineService(db)
        run_id, run_item_ids = await service.create_run(
            trigger_type=IngestionRunTrigger.reprocess,
            requested_by="cli",
            trace_id=trace_id,
            source_key=source_key,
            metadata_json={"requested_via": "cli"},
        )
        run_item_id = run_item_ids[0]

        if sync:
            status = await service.process_run_item(run_item_id=run_item_id, attempt_number=1)
            run = await service.finalize_run(run_id)
            return {
                "mode": "sync",
                "run_id": str(run_id),
                "run_status": run.status.value,
                "run_item_id": str(run_item_id),
                "item_status": status.value,
            }

        task = ingest_source_task.apply_async(
            kwargs={"run_id": str(run_id), "run_item_id": str(run_item_id), "trace_id": trace_id},
            queue="ingestion_queue",
        )
        return {
            "mode": "async",
            "run_id": str(run_id),
            "run_item_id": str(run_item_id),
            "task_id": task.id,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingestion pipeline operations")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("seed-sources", help="Seed source registry with default official sources")

    reprocess = subparsers.add_parser("reprocess-source", help="Reprocess a source key")
    reprocess.add_argument("--source-key", required=True, help="source registry key")
    reprocess.add_argument("--sync", action="store_true", help="execute ingestion in-process")
    reprocess.add_argument("--trace-id", default=None, help="optional trace id")

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "seed-sources":
        output = asyncio.run(seed_sources())
    elif args.command == "reprocess-source":
        output = asyncio.run(
            reprocess_source(
                args.source_key,
                sync=args.sync,
                trace_id=args.trace_id,
            )
        )
    else:
        raise ValueError(f"Unsupported command: {args.command}")
    print(json.dumps(output, ensure_ascii=True))


if __name__ == "__main__":
    main()
