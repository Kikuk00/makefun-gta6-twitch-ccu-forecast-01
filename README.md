# GTA VI Twitch CCU forecast — `gta6-twitch-ccu-forecast-01`

Forecasts how many people watch Grand Theft Auto VI live on Twitch in each
hour of its release day (2026-11-19 UTC, hours 2–24), as five quantiles per
hour, from the first hour's print plus the case's comparable past launches.

## How it works

One file, `main.py` (Python 3.13, standard library only, no network, no
randomness). For every past big launch in the case's `comparables`, its
release-day hourly curve is expressed as log-ratios to its own hour-1 print,
`ln(viewers_h / viewers_1)`. Hour 1's scale encodes the launch's shape: a
category still dead at 00:00 UTC (unlock hours away) has a tiny hour-1 print
and explodes 50–2000x by the US evening, while a game already live everywhere
at hour 1 stays near flat. So each comparable is weighted by a Gaussian
kernel in log hour-1 viewers (σ = 1.0) around the target's hour-1 print, and
each hour's five quantiles are read straight off that weighted empirical
distribution of log-ratios, multiplied back by the target's hour-1 print. No
normality assumption — where launches disagree the band is honestly wide,
where they agree it is narrow.

The GTA VI category's own pre-release history is excluded as a comparable
(it is not a launch). Pre-launch-history features and platform/unlock-text
similarity weights were tried and made the backtest worse, so they are not
used; the hour-1 print alone carries the signal.

## How to run

```sh
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Reads every `*.in` in the input dir (in name order) and writes one
`<id>.out` per case: `{"hours": [{"hour": h, "q": [q05, q25, q50, q75, q95]}]}`
for hours 2–24. Falls back safely (persistence shape) if no comparable can be
scored, and always writes 23 valid rows.

## Local evidence

`backtest.py` runs a leave-one-out backtest on the kit's 37 comparable
launches using the real entry code (each launch forecast from the other 36,
scored against its actual hours 2–24); `results.txt` holds the full output.

| Slice | This entry | House baseline |
|---|---|---|
| All 37 launches (mean pinball loss) | **0.4048** | 0.9297 |
| Hour-1 print > 20,000 (practice scale) | **0.2579** | 0.3214 |
| Hour-1 print > 100,000 | **0.2163** | 0.2611 |
| Hour-1 print < 5,000 (unlock still to come) | **0.8913** | 2.9966 |

90% coverage 0.86 overall (0.88–0.89 on large hour-1 launches). Beats the
baseline on 32 of 37 launches. Practice-case answers are not shipped in the
kit (the server grades them), so no direct practice loss can be computed
locally — the backtest above is the local evidence.

Practice validation: all 4 practice cases pass strict schema checks, two
runs are byte-identical, and runtime is ~0.1 s per case (limit 8 s).

## Files

- `main.py` — the entry (repository root file)
- `LICENSE` — MIT (kit starter license text)
- `backtest.py` — leave-one-out backtest against the entry code
- `results.txt` — backtest output + practice validation summary
