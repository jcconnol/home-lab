# Artificial-life terrarium

Run from this folder with Python 3.11+ (standard library only):

```sh
python run.py --ticks 10 --food 10 --seed 7
python run.py --ticks 0
```

Persists plants, creatures, energy, lineage, and the last 100 birth/death events. Explicit ticks only: it pauses between invocations. Food adds plant energy. Ages are measured in ticks. No visual renderer, inheritance, predators, or continuous service yet.

Use `python run.py --help` for options. See [the garage run guide](../../README.md) for deployment boundaries.
