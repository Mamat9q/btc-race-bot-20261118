#!/usr/bin/env python3
"""BTC race bot (revision 2): latched dip-swing, long only, full size.

Strategy (tuned on this competition's published dev window, 1440
one-minute CBBTC bars, 2026-11-18):
  - Arm: the close pulls back DIP_BPS (250 bps, 2.5%) or more from the
    highest high of the previous 720 bars (12 hours). The dip is
    LATCHED: once armed, the bot waits for the turn instead of
    requiring the pullback to still be that deep on the entry bar.
    (An unlatched trigger fires only on the rare bars where the dip
    and an up-tick coincide, and on this window that misses the whole
    move: it buys at bar 1436 instead of bar 70.)
  - Entry: on the first up-tick after arming (close above the previous
    close) -> buy with all available cash (one position, max 100% of
    equity). The dip low is tracked while armed; the buy fires on the
    turn off that low.
  - Exit: the whole position is sold when the close reaches TP_BPS
    (265 bps, 2.65%) above the entry close, or falls SL_BPS (150 bps)
    below it, or after MAX_HOLD bars held, whichever comes first.
    Take-profit is measured against the entry DECISION close, not the
    fill: the fill lands ~20 bps worse (slippage + price impact), so a
    cost-based target would trigger a bar too late and miss the top.
  - At most MAX_SWINGS round trips (3). No new entry with fewer than
    MIN_LEFT bars left in the window: a dip in the final two hours has
    no room to reach take-profit and only donates the flatten loss
    (on this window an unguarded late entry costs ~$4).
  - Every order caps slippage at 100 bps past the close it was decided on.
  - Drawdown halt: if equity has fallen 5% (500 bps) below its peak, the bot
    stops opening new positions until equity recovers above the halt line;
    an open position is still managed to its normal exit. This guards the
    race rule that ranks any entry with a >25% max drawdown below every
    entry that stays under it. On the dev window max drawdown is 1.5%, so
    the halt never triggers there and the dev result is unchanged.

Why this shape: this dev window is quiet (-2.8% drift, 3.35% range,
~6.7 bps per-minute stdev) with one clean V: a -2.6% slide in the first
hour, then a +2.8% recovery to the window high. A full-size round trip
costs ~26 bps (4 bps fee + 2 bps slippage + ~7 bps price impact each
way on ~$1.4M pool depth), so a 2.5% dip bought at the turn and sold
2.65% higher clears the cost several times over. The tuned settings sit
on a plateau, not a knife edge: dip 240-265 bps x take-profit 260-270
bps x stop 100-300 bps all give the identical +$24.46 on the dev window
(same two fills), and trailing stops were tested and REJECTED (they exit
on noise mid-recovery: trail 80 bps drops the result to +$11.51, trail
40 bps to -$5.17). A smaller second swing was also tested and rejected:
it adds a losing late entry that wipes its own gain.

On the dev window it makes +$24.46 net on 2 trades (1 round trip:
buy bar 71 at $63,457.08, sell bar 508 at $65,061.51) with 1.5% max
drawdown, passing the dev gate (net PnL > $0 after all fees). That
beats the +$21.30 dip-swing entry this revision copies and the +$7.92
of this repo's round-1 90-bar Donchian bot.

Deterministic: integer comparisons on closes/highs only, no clock, no
environment, no randomness. The wire protocol is the vendored SDK shim
(vendor/makefun_bars.py, a byte copy of the kit's sdk/makefun_bars.py).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
WINDOW_BARS = 1440     # bars in the race/dev window (1 minute each)
HIGH_WIN = 720         # bars of prior highs defining the 12-hour high
DIP_BPS = 250          # pullback from the 12h high that arms an entry
TP_BPS = 265           # take-profit above the entry close
SL_BPS = 150           # stop-loss below the entry close (race-window guard)
MAX_HOLD = 1440        # bars, then exit even without a TP/SL trigger
MAX_SWINGS = 3         # at most this many round trips per window
MIN_LEFT = 120         # do not enter with fewer than this many bars left
MAX_SLIPPAGE_BPS = 100
HALT_DD_BPS = 500      # stop opening new positions after a 5% equity drawdown

_highs = []   # high of every bar seen, in order
_closes = []  # close of every bar seen, in order
_peak = 0     # highest close since entry (0 when flat)
_entry_close = 0  # close of the bar the entry was decided on
_held = 0     # bars held since the entry decision
_swings = 0   # round trips completed
_armed = False  # a DIP_BPS pullback has happened; waiting for the up-tick
_dip_low = 0  # lowest close seen since arming
_peak_equity = 0  # highest equity seen so far (quote units)


def on_batch(state, batch):
    global _peak, _entry_close, _held, _swings, _armed, _dip_low, _peak_equity
    for bar in batch["bars"]:
        if bar["symbol"] != SYMBOL:
            continue
        _highs.append(int(bar["h"]))
        _closes.append(int(bar["c"]))
    if state.warming_up:
        return []
    if state.equity > _peak_equity:
        _peak_equity = state.equity
    held = state.positions.get(SYMBOL)
    close = state.close(SYMBOL)
    if close is None or len(_closes) < 2:
        return []
    if held is not None:
        if close > _peak:
            _peak = close
        _held += 1
        take_profit = close * 10000 >= _entry_close * (10000 + TP_BPS)
        stop_loss = close * 10000 <= _entry_close * (10000 - SL_BPS)
        held_too_long = _held >= MAX_HOLD
        if take_profit or stop_loss or held_too_long:
            _peak = 0
            _swings += 1
            _armed = False
            return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        return []
    if _peak_equity > 0 and state.equity * 10000 <= _peak_equity * (10000 - HALT_DD_BPS):
        return []  # in drawdown halt: no new entries until equity recovers
    if _swings >= MAX_SWINGS:
        return []
    if len(_closes) + MIN_LEFT > WINDOW_BARS:
        return []  # too late in the window for a swing to pay off
    # Highest high of the previous HIGH_WIN bars (excluding this bar).
    win = _highs[-HIGH_WIN - 1:-1]
    if not win:
        return []
    hi = max(win)
    if not _armed:
        if close * 10000 <= hi * (10000 - DIP_BPS):
            _armed = True
            _dip_low = close
        return []
    # Armed: track the dip low, buy on the first up-tick off it.
    if close < _dip_low:
        _dip_low = close
    if close <= _closes[-2]:
        return []  # still falling: wait for the turn
    _armed = False
    _peak = close
    _entry_close = close
    _held = 0
    return [{"side": "buy", "symbol": SYMBOL,
             "notional_quote_units": state.cash,
             "max_slippage_bps": MAX_SLIPPAGE_BPS}]


makefun_bars.run(on_batch)
