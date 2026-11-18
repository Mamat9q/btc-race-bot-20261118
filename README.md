[![make.fun · btc-race-24h-20261118-1444](https://make.fun/badge/btc-race-24h-20261118-1444.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![rank](https://make.fun/badge/btc-race-24h-20261118-1444/Mamat9q/btc-race-bot-20261118/rank.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![reward](https://make.fun/badge/btc-race-24h-20261118-1444/Mamat9q/btc-race-bot-20261118/reward.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
# BTC Race Bot — latched dip-swing (revision 2)

Entry for make.fun bounty **"Race a BTC trading bot live for 24 hours"**
(`btc-race-24h-20261118-1444`, $250). Paper money only; nothing is traded
for real.

## Strategy

Long-only dip-swing bot on 1-minute CBBTC (Coinbase Wrapped BTC) bars from
the Orca Whirlpool on Solana:

- **Arm:** the close pulls back 250 bps (2.5%) or more from the highest
  high of the previous 720 bars (12 hours). The dip is **latched**: once
  armed, the bot waits for the turn instead of requiring the pullback to
  still be that deep on the entry bar.
- **Entry:** on the first up-tick after arming (close above the previous
  close) → buy with all available cash (one position, up to 100% of
  equity). At most 3 round trips per window, and no entry with fewer than
  120 bars left — a dip in the final two hours has no room to reach
  take-profit.
- **Exit:** sell the whole position when the close reaches 265 bps above
  the entry close (take-profit), or falls 150 bps below it (stop-loss),
  or after 1440 bars held.
- Every order caps slippage at 100 bps past the close it was decided on.
- **Drawdown halt:** no new entries while equity is 5% below its peak.

Why this shape: this dev window is quiet (-2.8% drift, 3.35% range,
~6.7 bps per-minute stdev) with one clean V: a -2.6% slide in the first
hour, then a +2.8% recovery to the window high. A full-size round trip
costs ~26 bps (4 bps fee + 2 bps slippage + ~7 bps price impact each way
on ~$1.4M pool depth), so a 2.5% dip bought at the turn and sold 2.65%
higher clears the cost several times over. The settings sit on a plateau:
dip 240–265 bps × take-profit 260–270 bps × stop 100–300 bps all give the
identical dev result (same two fills), so this is not a knife-edge fit.
Trailing stops were tested and rejected (they exit on noise mid-recovery),
and a smaller second swing was tested and rejected (its late entry loses
more than it gains).

## Dev result (published dev window, 1440 bars)

- Net PnL **+$24.46** on $1,000 starting capital (after all fees,
  slippage and price impact) — passes the dev gate (net PnL > $0).
- 2 trades (1 round trip: buy bar 71 at $63,457.08, sell bar 508 at
  $65,061.51), max drawdown 1.5% (limit 25%).
- Revision 1 of this repo (90-bar Donchian breakout) made +$7.92 on the
  same window; the dip-swing entry this revision builds on made +$21.30.

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
