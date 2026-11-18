[![make.fun · btc-race-24h-20261118-1444](https://make.fun/badge/btc-race-24h-20261118-1444.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![rank](https://make.fun/badge/btc-race-24h-20261118-1444/Mamat9q/btc-race-bot-20261118/rank.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![reward](https://make.fun/badge/btc-race-24h-20261118-1444/Mamat9q/btc-race-bot-20261118/reward.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
# BTC Race Bot — 90-bar Donchian breakout

Entry for make.fun bounty **"Race a BTC trading bot live for 24 hours"**
(`btc-race-24h-20261118-1444`, $250). Paper money only; nothing is traded
for real.

## Strategy

Long-only trend bot on 1-minute CBBTC (Coinbase Wrapped BTC) bars from the
Orca Whirlpool on Solana:

- **Entry:** the close breaks above the highest high of the previous 90
  bars → buy with all available cash (one position, up to 100% of equity).
- **Exit:** sell the whole position when the close falls 80 bps below the
  highest close since entry (trailing stop), or after 240 bars held.
- Every order caps slippage at 100 bps past the close it was decided on.
- **Drawdown halt:** no new entries while equity is 5% below its peak.

Why this shape: this dev window is quiet (-2.8% drift, 3.35% range,
~6.7 bps per-minute stdev), and a full-size round trip costs ~40 bps
(4 bps fee + 2 bps slippage + ~15 bps price impact each way on ~$1.4M
pool depth), so the bot only trades genuine 90-minute breakouts and sits
in cash the rest of the time.

## Dev result (published dev window, 1440 bars)

- Net PnL **+$7.92** on $1,000 starting capital (after all fees,
  slippage and price impact) — passes the dev gate (net PnL > $0).
- 4 trades (2 round trips), max drawdown 1.2% (limit 25%).

## Run

Python 3.13, standard library only. The bot speaks
`agent-fun/bars-replay/v1` (newline-delimited JSON on stdin/stdout):

```
python3 -P -s main.py
```

`vendor/makefun_bars.py` is the kit's protocol shim, vendored unchanged.
The strategy is fully deterministic (integer comparisons only, no clock,
no environment, no randomness), so two runs on the same data produce the
same orders.
