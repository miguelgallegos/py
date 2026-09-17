# Trading API

A Flask-based multi-exchange trading API for Robinhood, Webull, Kraken, and Alpaca.

## Endpoints

- `GET /health` - health check
- `POST /trade` - execute buy/sell orders
- `GET /portfolio` - retrieve portfolio values for all exchanges or a specific exchange

## Request examples

### Trade

POST `/trade`

JSON body:

{
  "exchange": "alpaca",
  "operation": "buy",
  "symbol": "AAPL",
  "order_type": "market",
  "quantity": 1,
  "auto_trade": false
}

For auto trade:

{
  "exchange": "kraken",
  "operation": "buy",
  "symbol": "BTCUSD",
  "order_type": "market",
  "auto_trade": true,
  "amount_percent": 10
}

### Portfolio

GET `/portfolio`
GET `/portfolio?exchange=alpaca`

## Getting started

1. Copy `.env.example` to `.env` and fill in credentials.
2. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

3. Run locally:

```bash
python app.py
```

### Run locally with Docker

```bash
docker build -t trading-api .
docker run --rm -p 8080:8080 --env-file .env trading-api
```

The service will be available at `http://localhost:8080`.

4. Run tests:

```bash
pytest tests
```

## Deployment

This repo includes:
- `Dockerfile` for container packaging
- `app.yaml` for App Engine / Cloud Run settings
- `cloudbuild.yaml` for Google Cloud Build deployment to Cloud Run

### Prerequisites

1. Install the Google Cloud SDK: https://cloud.google.com/sdk/docs/install
2. Authenticate:

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

3. Enable required APIs:

```bash
gcloud services enable cloudbuild.googleapis.com run.googleapis.com
```

### Deploy to Cloud Run via Cloud Build

1. Push the code to a Git repository (GitHub, Cloud Source Repositories, etc).
2. Set up Cloud Build trigger in the GCP Console, or submit manually:

```bash
gcloud builds submit --config cloudbuild.yaml .
```

The build will:
- Build the Docker image
- Push to `gcr.io/$PROJECT_ID/trading-api:$SHORT_SHA`
- Deploy to Cloud Run

3. After deployment, retrieve the service URL:

```bash
gcloud run services list
```

### Deploy to Cloud Run directly

Alternatively, build and deploy in one step:

```bash
gcloud run deploy trading-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

### Set environment variables on Cloud Run

Update `.env` values in the Cloud Run service:

```bash
gcloud run services update trading-api \
  --region us-central1 \
  --set-env-vars TEST_MODE=false,ALPACA_API_KEY=your_key,ALPACA_API_SECRET=your_secret
```

### View logs

```bash
gcloud run services logs read trading-api --region us-central1 --limit 50
```

## Live exchange configuration

- Set `TEST_MODE=false` in `.env` for live trading.
- Robinhood requires login credentials and may require two-factor authentication support.
- Webull requires `WEBULL_APP_KEY`, `WEBULL_APP_SECRET`, `WEBULL_ACCOUNT_ID`, and optionally `WEBULL_REGION`, `WEBULL_API_ENDPOINT`, and `WEBULL_TOKEN_DIR`.
- Alpaca and Kraken require API key/secret credentials for live mode.

## Notes

- Supports `market` and `limit` orders.
- Portfolio results are returned raw per exchange.
- `TEST_MODE=true` enables simulated order and portfolio responses.
