## hfx-tools


# hfx-tools

Tools for working with HFX submissions (Haplotype Frequency Exchange).

This repo provides small, composable command line tools that operate on an HFX
submission JSON (the object that contains `metadata`, and optionally inline `frequencyData`).

Key schema facts:

- `metadata.frequencyLocation` controls where frequencies are stored: either `"inline"`
  or a URI (e.g., `file://data/frequencies.csv`) (see HFX schema).
  
- If inline, the JSON may include `frequencyData` (array of `{haplotype, frequency}`).

## Install (dev)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[parquet]"
```


## Run

`hfx-pack metadata.json -o dist/example.hfx --manifest --hash sha256`


Assuming your metatdata.json contains

```
{
  "metadata": {
    "frequencyLocation": "file://data/frequencies.csv",
    ...
  }
}
```


## package contents

.
├── __init__.py
├── cli.py
├── inspect.py
├── io.py
├── Makefile
├── pack.py
├── qc.py
└── util.py

