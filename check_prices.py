name: Check Flight Prices

on:
  schedule:
    - cron: '0 13 * * *'
  workflow_dispatch:

permissions:
  contents: write

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install requests

      - name: Run price checker
        env:
          TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
          TELEGRAM_CHAT_ID_OLEKSANDR: ${{ secrets.TELEGRAM_CHAT_ID_OLEKSANDR }}
          TELEGRAM_CHAT_ID_VICTORIA: ${{ secrets.TELEGRAM_CHAT_ID_VICTORIA }}
          SERPAPI_KEY: ${{ secrets.SERPAPI_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: python check_prices.py
