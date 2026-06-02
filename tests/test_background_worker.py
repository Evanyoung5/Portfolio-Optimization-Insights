from app.api.routes import portfolio_repository
from app.background.portfolio_tasks import create_position_lot
from app.background.queue import QueuedBackgroundJob, dequeue_background_job_message, parse_background_job_message
from app.background.worker import process_background_job
from app.db.models import Portfolio


def test_queue_rebuild_positions_route_enqueues_redis_message(client, auth_headers, monkeypatch):
    queued_jobs = []

    def fake_enqueue(job, **kwargs):
        queued_jobs.append((job, kwargs))

    monkeypatch.setattr("app.api.routes.enqueue_background_job_message", fake_enqueue)
    create_response = client.post(
        "/portfolios",
        headers=auth_headers,
        json={"name": "Queued Rebuild"},
    )
    portfolio = create_response.json()

    response = client.post(
        f"/portfolios/{portfolio['id']}/jobs/rebuild-positions",
        headers=auth_headers,
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["job_type"] == "rebuild_positions"
    assert payload["status"] == "pending"
    assert queued_jobs[0][0].id == payload["id"]
    assert queued_jobs[0][0].portfolio_id == portfolio["id"]


def test_worker_processes_position_rebuild_job():
    portfolio = portfolio_repository.create(
        name="Worker Portfolio",
        base_currency="USD",
        cash=0,
        positions=[],
        lots=[],
        user_id="user-1",
    )
    portfolio_repository.add_lots(
        portfolio.id,
        [
            create_position_lot(
                {
                    "ticker": "AAPL",
                    "quantity": 2,
                    "purchase_price": 100,
                    "current_price": 125,
                }
            )
        ],
    )
    job = portfolio_repository.enqueue_background_job(
        portfolio.id,
        "rebuild_positions",
        message="Queued position rebuild for background worker.",
    )

    result = process_background_job(
        portfolio_repository,
        QueuedBackgroundJob(
            job_id=job.id,
            portfolio_id=portfolio.id,
            job_type=job.job_type,
            payload={},
        ),
    )

    updated = portfolio_repository.get(portfolio.id)
    assert isinstance(updated, Portfolio)
    assert result.status == "completed"
    assert result.message == "Rebuilt positions from 1 lot(s)."
    assert updated.positions[0].symbol == "AAPL"
    assert updated.positions[0].quantity == 2
    assert updated.positions[0].market_value == 250
    assert updated.background_jobs[-1].status == "completed"


def test_parse_background_job_message_validates_payload():
    message = '{"job_id":"job-1","portfolio_id":"portfolio-1","job_type":"rebuild_positions","payload":{}}'

    queued_job = parse_background_job_message(message)

    assert queued_job.job_id == "job-1"
    assert queued_job.portfolio_id == "portfolio-1"
    assert queued_job.job_type == "rebuild_positions"

def test_dequeue_timeout_is_treated_as_empty_queue():
    class TimeoutClient:
        def blpop(self, keys, timeout):
            raise TimeoutError("Timeout reading from socket")

    assert dequeue_background_job_message(client=TimeoutClient()) is None

def test_worker_drops_stale_queued_job_without_raising():
    result = process_background_job(
        portfolio_repository,
        QueuedBackgroundJob(
            job_id="missing-job",
            portfolio_id="missing-portfolio",
            job_type="rebuild_positions",
            payload={},
        ),
    )

    assert result.status == "dropped"
    assert result.id == "missing-job"
    assert "Dropped stale background job" in (result.message or "")

def test_worker_drops_already_finished_queued_job_without_reprocessing():
    portfolio = portfolio_repository.create(
        name="Finished Job Portfolio",
        base_currency="USD",
        cash=0,
        positions=[],
        lots=[],
        user_id="user-finished",
    )
    job = portfolio_repository.enqueue_background_job(portfolio.id, "refresh_market_data")
    portfolio_repository.complete_background_job(portfolio.id, job.id, status="completed", message="Already done.")

    result = process_background_job(
        portfolio_repository,
        QueuedBackgroundJob(
            job_id=job.id,
            portfolio_id=portfolio.id,
            job_type="refresh_market_data",
            payload={},
        ),
    )

    assert result.status == "dropped"
    assert "already-finished" in (result.message or "")
    updated = portfolio_repository.get(portfolio.id)
    assert updated.background_jobs[-1].status == "completed"
