# Billing Service: Local Xendit Webhook Testing

This guide explains how to receive Xendit Test Mode callbacks on a locally running MaaS stack using an ngrok HTTPS tunnel. The flow exercises the app's real public route:

```text
Xendit Test Mode
  -> ngrok HTTPS URL
  -> local Nginx on port 80
  -> API Gateway
  -> Billing webhook handler
```

The callback URL is `POST /api/v1/billing/webhook/xendit`. The Gateway allows this exact route without a user JWT, forwards the `x-callback-token` header, and Billing validates that header against `XENDIT_CALLBACK_TOKEN`.

## Prerequisites

- Docker Desktop with Docker Compose
- An ngrok account and the ngrok CLI installed and authenticated
- A Xendit account with **Test Mode** enabled
- A local root `.env` file based on `.env.example`

## 1. Configure Test Mode credentials

In the root `.env`, set:

```dotenv
XENDIT_SECRET_KEY=<your Xendit Test Mode secret API key>
XENDIT_CALLBACK_TOKEN=<your Xendit webhook verification token>
```

Get the webhook verification token from the Xendit Dashboard's Webhook settings. It is sent in the `x-callback-token` request header. It is not the Xendit API key, a user JWT, or the ngrok authentication token. Keep both values private and do not use Live Mode credentials for local testing.

If the Billing container is already running when `.env` changes, recreate it so Compose passes the updated environment:

```powershell
docker compose up -d --force-recreate billing
```

## 2. Start the MaaS stack

From the repository root:

```powershell
docker compose up -d --build
```

Compose publishes Nginx on host port `80`; the API Gateway and Billing service are not published directly. Keep the webhook tunnel pointed at Nginx so the callback traverses the same Gateway route used by the app.

## 3. Start the ngrok tunnel

In a separate terminal:

```powershell
ngrok http 80
```

Copy the HTTPS forwarding address shown by ngrok, for example `https://example.ngrok-free.app`. Do not include a trailing slash when adding the app path.

## 4. Configure Xendit webhook notifications

In the Xendit Dashboard, switch to **Test Mode**, open **Settings → Webhooks**, and set the callback URL for the Payment Session completed notification and the Subscriptions lifecycle notifications to:

```text
https://<your-ngrok-host>/api/v1/billing/webhook/xendit
```

Enable the subscription lifecycle events used by the integration, including plan activation/deactivation and recurring cycle success/retry/failure. Save the settings and use Xendit's **Save and Test** action. A successful 2xx response confirms that the tunnel, route, and callback token are working.

The Save and Test callback is only a delivery check; it does not create or activate a MaaS subscription.

## 5. Verify a real sandbox subscription

1. Open the local MaaS app and sign in.
2. Go to Billing and start the Pro checkout.
3. Complete the checkout using Xendit's Test Mode payment flow.
4. Check the Xendit Dashboard's webhook delivery history for a successful delivery to the ngrok URL.
5. Refresh the MaaS Billing page and confirm the plan is Pro with an active period.

The initial activation requires a payment-confirming event such as `payment_session.completed` or `payment.capture`. The handler matches the callback to a pending checkout and validates its reference ID, payment-session ID, amount, and currency. A plan activation event by itself does not grant Pro access. Xendit can send payment-session and recurring-plan events as separate notifications.

To watch application logs while testing:

```powershell
docker compose logs -f api-gateway billing
```

Billing currently logs webhook payloads. Treat these logs as sensitive; do not paste full payloads into public issues, chats, or support requests.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Xendit cannot connect or times out | Keep ngrok running, confirm `docker compose ps` shows Nginx and the app services running, and confirm ngrok forwards to local port `80`. |
| `401 Invalid or missing webhook callback token` | Ensure `XENDIT_CALLBACK_TOKEN` exactly matches the token shown in Xendit Webhook settings, then recreate the Billing container. |
| `404 Not Found` | Check the exact path `/api/v1/billing/webhook/xendit`; the webhook must use `POST`. |
| Xendit gets 2xx but the account remains Hobby | Save and Test does not activate a subscription. Complete a real Test Mode checkout and check for a payment-confirming event that matches the pending checkout. |
| Billing returns a server error | Check that PostgreSQL and Billing started successfully, then inspect the private Billing and Gateway logs. |

Do not expose the Billing container or PostgreSQL port to the internet. Only the temporary ngrok HTTPS URL should be public, and only while performing local testing.

## References

- [Xendit webhook setup guide](https://help.xendit.co/hc/en-us/articles/360038048871-How-Do-I-Set-and-Update-The-Webhook-URL)
- [Xendit payment integration and webhook checklist](https://docs.xendit.co/docs/payments-integration-setup)
- [Xendit subscription overview](https://docs.xendit.co/docs/subscriptions-overview)
