from __future__ import annotations

from fastapi import FastAPI, HTTPException

from nonprofit_alerts import AlertBatch, InfraiError, InfraiSmsClient, dispatch_alert_batch

app = FastAPI(title="Nonprofit transactional SMS")


@app.post("/alerts", status_code=202)
def send_alerts(batch: AlertBatch) -> dict[str, object]:
    client = InfraiSmsClient()
    try:
        result = dispatch_alert_batch(batch, client)
        return {
            "batch_id": result.batch_id,
            "accepted": result.accepted,
            "provider_data": result.provider_data,
        }
    except InfraiError as exc:
        caller_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=caller_status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    finally:
        client.close()
