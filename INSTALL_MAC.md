# QuantDrift Mac Installation

## If you see "QuantDrift can't be opened" or "App is damaged"

The app may have lost its execute permissions during download/transfer (e.g. from Google Drive zip).

**Fix:** In Terminal, run:

```bash
chmod +x ~/Downloads/QuantDrift.app/Contents/MacOS/opt-bot
chmod +x ~/Downloads/QuantDrift.app/Contents/MacOS/trading-engine
```

*(Adjust the path if the app is in a different location, e.g. `/Applications/QuantDrift.app`.)*

Then double-click the app to open.

## Distribution tip

To avoid permission loss when sharing:
- Upload the **.dmg file directly** to Google Drive (don't zip it), or
- Use AirDrop / USB drive for transfer
