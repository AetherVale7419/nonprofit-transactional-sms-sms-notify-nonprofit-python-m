from __future__ import annotations

import os

from nonprofit_alerts import AlertBatch, InfraiSmsClient, dispatch_alert_batch


def main() -> None:
    phone = os.environ.get("DEMO_SMS_TO")
    if not phone:
        raise SystemExit("DEMO_SMS_TO is required")

    batch = AlertBatch.model_validate(
        {
            "batch_id": "demo-receipt-1042",
            "alerts": [
                {
                    "kind": "donor_receipt",
                    "phone": phone,
                    "donor_name": "Avery",
                    "amount": "35.00",
                    "receipt_number": "R-1042",
                }
            ],
        }
    )
    client = InfraiSmsClient()
    try:
        result = dispatch_alert_batch(batch, client)
        print(f"accepted {result.accepted} alert for batch {result.batch_id}")
        print(result.provider_data)
    finally:
        client.close()


if __name__ == "__main__":
    main()
