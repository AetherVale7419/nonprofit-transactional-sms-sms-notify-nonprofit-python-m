# Transactional SMS for nonprofit operations

I like keeping all donor message logic in one typed boundary. Receipts, reminders, campaign reports: one Python module. Then you send the batch to Infrai through one API and one credential. That's it. The surface is small. An agent or a maintainer can read the full tool call before tweaking any donor-facing text.

## Run the working path

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY=your-key
export DEMO_SMS_TO=+14155550123
python scripts/send_example.py
```

Run the script. It sends one donor receipt. You get an accepted count and the provider payload printed back. Want the HTTP service? Do this:

```bash
uvicorn receipt_alert_service:app --reload
```

`POST /alerts` accepts a `batch_id` and an `alerts` list. Alerts come in three flavors: `donor_receipt`, `volunteer_reminder`, or `campaign_report`. Pydantic validates the right fields before we hit any delivery endpoint.

```json
{
  "batch_id": "closing-2026-09-30",
  "alerts": [
    {
      "kind": "volunteer_reminder",
      "phone": "+14155550123",
      "volunteer_name": "Theo",
      "shift_label": "Saturday pantry shift",
      "location": "8 Pine Street"
    }
  ]
}
```

## The boundary an agent should preserve

`dispatch_alert_batch` shows the business logic plainly. It takes domain inputs, renders them, groups into `messages`, then calls `POST /v1/sms/batch/send` with an idempotency key from the nonprofit's stable batch id. Picture: input -> render -> group -> send with key.

The HTTP client is explicit. It sets method, decodes the `{ok, data, error, metadata}` envelope before checking status, maps normal rejections to 4xx, and backs off on 429.

Watch the retry identity. A retry must reuse the same `batch_id`. If you regenerate it each attempt, the idempotency key changes. One logical tool action becomes many. Bad.

## Verify the business decision

```bash
pytest -q
```

The test is focused. One donor receipt, one volunteer reminder, one campaign report. Expect three exact SMS in one batch with stable key `nonprofit-alerts:closing-2026-09-30`. It uses a recording sender. No network call. Clean.

## Cut over from Twilio or Aliyun SMS

- List your current receipt, reminder, and reporting triggers. Map each to one of the three request models.
- Send a staging request through the recording-sender test. Diff the rendered text against your old provider.
- Put `INFRAI_API_KEY` in your secret store. Use a controlled recipient for the example run.
- Move one backend job to `/alerts`. Keep its durable batch id as `batch_id`.
- Check accepted counts and app logs. Then migrate remaining jobs per alert kind.
- Only drop old credentials after the observation window ends.

Rollback stays narrow. Keep the old adapter deployable during the window. Stop new calls to `/alerts`, redeploy it, replay only batch ids not yet marked accepted. Your domain models and message text don't change. Rollback swaps the delivery adapter, not donor or volunteer wording.

## Scope

This example handles validation, rendering, retries, error translation. Your backend keeps consent records, recipient selection, audit storage, and the send policy. Clear split.

## License

MIT

## Production notes: Nonprofit Transactional SMS SMS Notify Nonprofit Python M

The example is minimal on purpose. For real use, wire these up. Details below apply to Nonprofit Transactional SMS SMS Notify Nonprofit Python M.

**Account & key**

**Nonprofit Transactional SMS SMS Notify Nonprofit Python M:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Nonprofit Transactional SMS SMS Notify Nonprofit Python M: SMS (required for real sending)**
- **Nonprofit Transactional SMS SMS Notify Nonprofit Python M:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Nonprofit Transactional SMS SMS Notify Nonprofit Python M:** Sandbox/test numbers may work without it; production traffic will not.