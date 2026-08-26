BIG.BULL LIVE APP — PARALLEL CONNECTION

IMPORTANT:
This package does NOT modify your current Pine Script, Telegram alert, Render MT5 bridge, or MT5 EA.

How it works:
1) Your current Telegram TradingView alert stays exactly as it is.
2) Deploy this package as a NEW Render web service.
3) Create ONE EXTRA TradingView alert from the same BIG.BULL indicator:
   Condition: BIG.BULL -> Any alert() function call
   Webhook URL: https://YOUR-NEW-APP.onrender.com/tv/YOUR_APP_WEBHOOK_KEY
4) Leave the alert Message field as TradingView/Pine alert() uses it automatically.
5) The app receives the same Telegram-shaped JSON, parses the "text" field, and updates the live card.
6) Open https://YOUR-NEW-APP.onrender.com on mobile.
7) When prompted, enter APP_VIEW_KEY from Render Environment.

Render environment variables:
- APP_WEBHOOK_KEY : secret string used in the TradingView webhook URL
- APP_VIEW_KEY    : password/key used to view the app
- APP_DB_PATH     : optional, defaults to bigbull_app.db

Health test:
https://YOUR-NEW-APP.onrender.com/health

Notes:
- Render free instances/filesystems may reset local SQLite data after restart/redeploy.
- This V1 keeps up to 500 received events.
- Telegram stays independent. Existing MT5 bridge stays independent.
- This V1 is read-only: it does NOT place or modify MT5 trades.

Files:
main.py
requirements.txt
Dockerfile
render.yaml
static/index.html
static/manifest.webmanifest
static/sw.js
