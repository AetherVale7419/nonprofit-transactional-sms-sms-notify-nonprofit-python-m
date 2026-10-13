from __future__ import annotations

from typing import Any

from nonprofit_alerts import AlertBatch, dispatch_alert_batch


class RecordingSender:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []
        self.idempotency_key = ""

    def batch_send(
        self, *, messages: list[dict[str, str]], idempotency_key: str
    ) -> dict[str, Any]:
        self.messages = messages
        self.idempotency_key = idempotency_key
        return {"batch_id": "sms_batch_42"}


def test_dispatch_renders_three_nonprofit_decisions_in_one_batch() -> None:
    batch = AlertBatch.model_validate(
        {
            "batch_id": "closing-2026-09-30",
            "alerts": [
                {
                    "kind": "donor_receipt",
                    "phone": "+14155550101",
                    "donor_name": "Mina",
                    "amount": "25.50",
                    "receipt_number": "R-91",
                },
                {
                    "kind": "volunteer_reminder",
                    "phone": "+14155550102",
                    "volunteer_name": "Theo",
                    "shift_label": "Saturday pantry shift",
                    "location": "8 Pine Street",
                },
                {
                    "kind": "campaign_report",
                    "phone": "+14155550103",
                    "campaign_name": "School supplies",
                    "donor_count": 18,
                    "total_raised": "740.00",
                },
            ],
        }
    )
    sender = RecordingSender()

    result = dispatch_alert_batch(batch, sender)

    assert result.accepted == 3
    assert sender.idempotency_key == "nonprofit-alerts:closing-2026-09-30"
    assert sender.messages == [
        {
            "to": "+14155550101",
            "message": "Thank you, Mina. We received $25.50. Receipt: R-91.",
        },
        {
            "to": "+14155550102",
            "message": (
                "Hi Theo, reminder: Saturday pantry shift at 8 Pine Street. "
                "Thank you for volunteering."
            ),
        },
        {
            "to": "+14155550103",
            "message": "School supplies report: 18 donors, $740.00 raised.",
        },
    ]
