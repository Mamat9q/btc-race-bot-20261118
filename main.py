#!/usr/bin/env python3
"""BTC race bot: 90-bar Donchian breakout, long only, full size.

Strategy (tuned on this competition's published dev window, 1440
one-minute CBBTC bars, 2026-11-18):
  - Entry: the close breaks above the highest high of the previous 90 bars
    -> buy with all available cash (one position, max 100% of equity).
  - Exit: the whole position is sold when the close falls 80 bps below the
    highest close since entry (trailing stop), or after 240 bars held,
    whichever comes first.
  - Every order caps slippage at 100 bps past the close it was decided on.
  - Drawdown halt: if equity has fallen 5% (500 bps) below its peak, the bot
    stops opening new positions until equity recovers above the halt line;
    an open position is still managed to its normal exit. This guards the
    race rule that ranks any entry with a >25% max drawdown below every
    entry that stays under it. On the dev window max drawdown is 1.2%, so
    the halt never triggers there and the dev result is unchanged.

Why this shape: this dev window is quieter than the previous race's
(-2.8% drift, 3.35% range, ~6.7 bps per-minute stdev vs 8.6% range
before), so the shorter 60-bar breakout that won last time overtrades
here (-$25.66 on 16 trades). A full-size round trip costs ~40 bps
(4 bps fee + 2 bps slippage + ~15 bps impact each way on ~$1.4M pool
depth), so the bot only trades genuine 90-minute breakouts and sits in
cash the rest of the time. On the dev window it makes +$7.92 net on
4 trades (2 round trips) with 1.2% max drawdown, passing the dev gate
(net PnL > $0 after all fees). The same 2 round trips appear across a
plateau of nearby settings (lookback 90-105, trail 80-100 bps,
hold 240), so the result is not a knife-edge fit to one parameter.

Deterministic: integer comparisons on closes/highs only, no clock, no
environment, no randomness. The wire protocol is the vendored SDK shim
(vendor/makefun_bars.py, a byte copy of the kit's sdk/makefun_bars.py).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
LOOKBACK = 90          # bars of prior highs defining the breakout
TRAIL_BPS = 80         # trailing stop below the peak close since entry
MAX_HOLD = 240         # bars, then exit even without a stop trigger
MAX_SLIPPAGE_BPS = 100
HALT_DD_BPS = 500      # stop opening new positions after a 5% equity drawdown

_highs = []   # high of every bar seen, in order
_closes = []  # close of every bar seen, in order
_peak = 0     # highest close since entry (0 when flat)
_since = 0    # batches since the entry decision
_peak_equity = 0  # highest equity seen so far (quote units)


def on_batch(state, batch):
    global _peak, _since, _peak_equity
    for bar in batch["bars"]:
        if bar["symbol"] != SYMBOL:
            continue
        _highs.append(int(bar["h"]))
        _closes.append(int(bar["c"]))
    _since += 1
    if state.warming_up:
        return []
    if state.equity > _peak_equity:
        _peak_equity = state.equity
    held = state.positions.get(SYMBOL)
    close = state.close(SYMBOL)
    if close is None:
        return []
    if held is not None:
        if close > _peak:
            _peak = close
        trailing_hit = close * 10000 <= _peak * (10000 - TRAIL_BPS)
        held_too_long = _since >= MAX_HOLD
        if trailing_hit or held_too_long:
            _peak = 0
            return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        return []
    if _peak_equity > 0 and state.equity * 10000 <= _peak_equity * (10000 - HALT_DD_BPS):
        return []  # in drawdown halt: no new entries until equity recovers
    if len(_closes) < LOOKBACK + 1:
        return []
    hi = max(_highs[-LOOKBACK - 1:-1])
    if close > hi:
        _peak = close
        _since = 0
        return [{"side": "buy", "symbol": SYMBOL,
                 "notional_quote_units": state.cash,
                 "max_slippage_bps": MAX_SLIPPAGE_BPS}]
    return []


makefun_bars.run(on_batch)
