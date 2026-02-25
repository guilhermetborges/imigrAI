from uuid import uuid4

import pytest
from billiard.exceptions import SoftTimeLimitExceeded

import apps.assessments.tasks as assessment_tasks
import apps.roadmaps.tasks as roadmap_tasks


class RetryCalled(Exception):
    pass


def test_score_task_success(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"completed": False}

    async def fake_run_assessment_job(**kwargs) -> None:
        assert kwargs["trace_id"] == "trace-1"

    async def fake_mark_job_completed(job_id, *, duration_ms: int) -> None:
        called["completed"] = True
        assert duration_ms >= 0

    monkeypatch.setattr(assessment_tasks, "_run_assessment_job", fake_run_assessment_job)
    monkeypatch.setattr(assessment_tasks, "_mark_job_completed", fake_mark_job_completed)

    result = assessment_tasks.process_assessment_task.run(
        assessment_id=str(uuid4()),
        job_id=str(uuid4()),
        trace_id="trace-1",
    )

    assert result["status"] == "completed"
    assert called["completed"] is True


def test_score_task_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: dict[str, object] = {}

    async def fake_run_assessment_job(**kwargs) -> None:
        raise RuntimeError("temporary db error")

    async def fake_mark_job_pending_retry(*, job_id, error_message: str) -> None:
        recorded["error"] = error_message

    async def fake_mark_job_failed(**kwargs) -> None:
        raise AssertionError("must not mark dead-letter in first retry")

    def fake_retry(*, exc: Exception, countdown: int):
        recorded["retry_countdown"] = countdown
        raise RetryCalled(str(exc))

    monkeypatch.setattr(assessment_tasks, "_run_assessment_job", fake_run_assessment_job)
    monkeypatch.setattr(assessment_tasks, "_mark_job_pending_retry", fake_mark_job_pending_retry)
    monkeypatch.setattr(assessment_tasks, "_mark_job_failed", fake_mark_job_failed)
    monkeypatch.setattr(assessment_tasks.process_assessment_task, "retry", fake_retry)
    assessment_tasks.process_assessment_task.request.retries = 0

    with pytest.raises(RetryCalled):
        assessment_tasks.process_assessment_task.run(
            assessment_id=str(uuid4()),
            job_id=str(uuid4()),
            trace_id="trace-2",
        )

    assert recorded["retry_countdown"] == 1
    assert "temporary db error" in str(recorded["error"])


def test_roadmap_task_timeout_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: dict[str, object] = {}

    async def fake_run_roadmap_job(**kwargs) -> None:
        raise SoftTimeLimitExceeded()

    async def fake_mark_failure_state(
        *,
        roadmap_id,
        job_id,
        error_message: str,
        duration_ms: int,
        dead_letter: bool,
    ) -> None:
        recorded["dead_letter"] = dead_letter
        recorded["error_message"] = error_message
        assert duration_ms >= 0

    def fake_retry(*, exc: Exception, countdown: int):
        recorded["retry_countdown"] = countdown
        raise RetryCalled(str(exc))

    monkeypatch.setattr(roadmap_tasks, "_run_roadmap_job", fake_run_roadmap_job)
    monkeypatch.setattr(roadmap_tasks, "_mark_failure_state", fake_mark_failure_state)
    monkeypatch.setattr(roadmap_tasks.generate_roadmap_task, "retry", fake_retry)
    roadmap_tasks.generate_roadmap_task.request.retries = 0

    with pytest.raises(RetryCalled):
        roadmap_tasks.generate_roadmap_task.run(
            roadmap_id=str(uuid4()),
            job_id=str(uuid4()),
            trace_id="trace-3",
        )

    assert recorded["dead_letter"] is False
    assert recorded["retry_countdown"] == 1


def test_roadmap_task_provider_error_dead_letter(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: dict[str, object] = {}

    async def fake_run_roadmap_job(**kwargs) -> None:
        raise RuntimeError("provider failed")

    async def fake_mark_failure_state(
        *,
        roadmap_id,
        job_id,
        error_message: str,
        duration_ms: int,
        dead_letter: bool,
    ) -> None:
        recorded["dead_letter"] = dead_letter
        recorded["error_message"] = error_message
        assert duration_ms >= 0

    monkeypatch.setattr(roadmap_tasks, "_run_roadmap_job", fake_run_roadmap_job)
    monkeypatch.setattr(roadmap_tasks, "_mark_failure_state", fake_mark_failure_state)
    roadmap_tasks.generate_roadmap_task.request.retries = int(
        roadmap_tasks.generate_roadmap_task.max_retries
    )

    with pytest.raises(RuntimeError, match="provider failed"):
        roadmap_tasks.generate_roadmap_task.run(
            roadmap_id=str(uuid4()),
            job_id=str(uuid4()),
            trace_id="trace-4",
        )

    assert recorded["dead_letter"] is True
    assert "provider failed" in str(recorded["error_message"])
