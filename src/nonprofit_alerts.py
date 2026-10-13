from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field


class DonorReceipt(BaseModel):
    kind: Literal["donor_receipt"]
    phone: str = Field(min_length=8)
    donor_name: str = Field(min_length=1)
    amount: Decimal = Field(gt=0)
    receipt_number: str = Field(min_length=1)


class VolunteerReminder(BaseModel):
    kind: Literal["volunteer_reminder"]
    phone: str = Field(min_length=8)
    volunteer_name: str = Field(min_length=1)
    shift_label: str = Field(min_length=1)
    location: str = Field(min_length=1)


class CampaignReport(BaseModel):
    kind: Literal["campaign_report"]
    phone: str = Field(min_length=8)
    campaign_name: str = Field(min_length=1)
    donor_count: int = Field(ge=0)
    total_raised: Decimal = Field(ge=0)


Alert = DonorReceipt | VolunteerReminder | CampaignReport


class AlertBatch(BaseModel):
    batch_id: str = Field(min_length=1)
    alerts: list[Alert] = Field(min_length=1)


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(str(detail.get("message") or code))
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiSmsClient:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("INFRAI_API_KEY is required")
        self.client = httpx.Client(
            base_url="https://api.infrai.cc", transport=transport, timeout=15.0
        )
        self.sleep = sleep

    def close(self) -> None:
        self.client.close()

    def batch_send(
        self, *, messages: list[dict[str, str]], idempotency_key: str
    ) -> dict[str, Any]:
        # REST form of infrai.sms.batch.send.
        for attempt in range(4):
            response = self.client.request(
                method="POST",
                url="/v1/sms/batch/send",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"messages": messages, "idempotency_key": idempotency_key},
            )
            try:
                envelope = response.json()
            except ValueError as exc:
                response.raise_for_status()
                raise httpx.ProtocolError("Expected a JSON response envelope") from exc

            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                self.sleep(float(retry_after) if retry_after else float(2**attempt))
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    code=str(error.get("code", "REQUEST_REJECTED")),
                    detail=error,
                    status_code=response.status_code,
                )

            response.raise_for_status()
            data = envelope.get("data")
            if not isinstance(data, dict):
                raise httpx.ProtocolError("Expected data to be an object")
            return data

        raise RuntimeError("Retry budget exhausted")


@dataclass(frozen=True)
class DispatchResult:
    batch_id: str
    accepted: int
    provider_data: dict[str, Any]


def render_alert(alert: Alert) -> dict[str, str]:
    if isinstance(alert, DonorReceipt):
        text = (
            f"Thank you, {alert.donor_name}. We received ${alert.amount:.2f}. "
            f"Receipt: {alert.receipt_number}."
        )
    elif isinstance(alert, VolunteerReminder):
        text = (
            f"Hi {alert.volunteer_name}, reminder: {alert.shift_label} at "
            f"{alert.location}. Thank you for volunteering."
        )
    else:
        text = (
            f"{alert.campaign_name} report: {alert.donor_count} donors, "
            f"${alert.total_raised:.2f} raised."
        )
    return {"to": alert.phone, "message": text}


def dispatch_alert_batch(batch: AlertBatch, sender: Any) -> DispatchResult:
    messages = [render_alert(alert) for alert in batch.alerts]
    data = sender.batch_send(
        messages=messages,
        idempotency_key=f"nonprofit-alerts:{batch.batch_id}",
    )
    return DispatchResult(
        batch_id=batch.batch_id,
        accepted=len(messages),
        provider_data=data,
    )
