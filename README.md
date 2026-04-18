## hfx-tools


# hfx-tools

Tools for working with HFX submissions (Haplotype Frequency Exchange).

This repo provides composable command line tools and a Streamlit app for building, packing, 
inspecting, and validating HFX documents, implementing the [HFX specification](https://github.com/nmdp-bioinformatics/hfx). Key features include:

- **`build`** - Build HFX bundles from a folder structure with automatic validation
- **`pack`** - Pack HFX archives from metadata.json with optional manifests and checksums
- **`qc`** - Compute quality control statistics
- **`inspect`** - Inspect metadata or bundled HFX files
- **Validation framework** - Extensible validation with built-in validators
- **Streamlit UI** - Web-based interface for building HFX files

## Key schema facts

- `metadata.frequencyLocation` controls where frequencies are stored: either `"inline"`
  or a URI (e.g., `file://data/frequencies.csv`) (see [HFX specification](https://github.com/nmdp-bioinformatics/hfx)).
  
- If inline, the JSON may include `frequencyData` (array of `{haplotype, frequency}`).

## Install

### Basic installation
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### With optional dependencies
```bash
# For Parquet support
pip install -e ".[parquet]"

# For Streamlit web UI
pip install -e ".[streamlit]"

# For development
pip install -e ".[dev,lint]"
```

## Quick Start

**5-minute walkthrough** for the most common workflow:

```bash
# 1. Create input folder with metadata and data
mkdir -p my_submission/{metadata,data}
cp my_metadata.json my_submission/metadata/metadata.json
cp my_frequencies.csv my_submission/data/frequencies.csv

# 2. Build and validate
hfx-build my_submission -n my_hfx_file

# 3. Done! Check output
ls -la my_submission/my_hfx_file.hfx
cat my_submission/my_hfx_file.build.log
```

For a guided interactive experience, launch the Streamlit web UI:
```bash
streamlit run hfx_tools/streamlit_app.py
```

## Architecture

**hfx-tools** follows a layered architecture:

```
CLI / Streamlit UI (user-facing)
    ↓
build.py (orchestration)
    ↓
validators.py (validation rules) ← pack.py (packing logic)
    ↓
io.py (file I/O, JSON parsing)
```

- **CLI layer** (`cli.py`) - Parses command-line arguments and delegates to build/pack/inspect/qc
- **Build orchestration** (`build.py`) - High-level workflow: reads metadata → detects files → validates → packs
- **Validation framework** (`validators.py`) - Pluggable validators for extensibility
- **Packing logic** (`pack.py`) - Low-level archive creation (ZIP with metadata, data, optional manifest)
- **I/O utilities** (`io.py`) - JSON parsing, file reading, consistent error handling

This design allows hackathon participants to:
1. Use the CLI for quick workflows
2. Call `build()` directly from Python for programmatic use
3. Register custom validators without modifying core code
4. Extend with custom QC statistics

## Usage

### Frequency Location Types

The HFX standard supports four types of frequency data locations:

1. **Inline** - `"frequencyLocation": "inline"` with `frequencyData` array in same JSON
2. **Remote** - `"frequencyLocation": "https://zenodo.org/.../data.csv"` or S3 URL
3. **File (relative)** - `"frequencyLocation": "file://data/frequencies.csv"` pointing to file within HFX bundle
4. **File (parquet)** - Same as above but with `.parquet` extension

### CLI: Build from folder

The most common workflow for hackathons and batch processing:

```bash
hfx-build /path/to/input_folder -n output_name
```

This will:
1. Read metadata from `input_folder/metadata/`
2. **Auto-detect** frequency data files in `input_folder/data/`
3. **Auto-update** `metadata.frequencyLocation` to `file://data/<filename>` (unless already set to remote or inline)
4. **Validate** all data with built-in validators
5. **Pack** into a single `output_name.hfx` file (self-contained bundle with all data)
6. **Log** all validation results to `output_name.build.log`

Expected folder structure:
```
input_folder/
├── metadata/
│   └── metadata.json      # Required: HFX metadata + inline data (optional)
└── data/
    └── frequencies.csv    # Optional: if frequencyLocation = "file://frequencies.csv"
```

Example:
```bash
mkdir -p example/{metadata,data}
cp metadata.json example/metadata/
cp frequencies.csv example/data/
hfx-build example -n my_submission
# Output: example/my_submission.hfx
```

Options:
- `-n, --name NAME` - Output filename (required, without .hfx)
- `-o, --out DIR` - Output directory (defaults to input folder)
- `--no-manifest` - Skip MANIFEST.json in archive
- `--hash {md5,sha256,none}` - Hash algorithm (default: sha256)
- `--no-auto-update-location` - Don't auto-update `metadata.frequencyLocation` (advanced)

### CLI: Pack (low-level)

For direct packing when you already have a metadata.json:

```bash
hfx-pack metadata.json -o dist/example.hfx --manifest --hash sha256
```

### CLI: Inspect

```bash
hfx-inspect metadata.json       # Inspect a metadata.json file
hfx-inspect example.hfx         # Inspect a bundled .hfx archive
```

### CLI: QC

```bash
hfx-qc metadata.json --write-metadata --topk 10 100 1000
```

### Streamlit: Web UI

Launch the interactive web interface:

```bash
streamlit run hfx_tools/streamlit_app.py
```

The Streamlit app provides:
- **Folder browser** - Select local folders with metadata/ and data/ subdirectories
- **File upload** - Upload metadata.json and data files directly
- **Auto-update mode** - Automatically sets `metadata.frequencyLocation` to point to uploaded data
- **Metadata preview** - View JSON structure and what will be auto-updated before building
- **Validation preview** - Run validators and see results
- **HFX download** - Download the built .hfx file
- **Build logs** - View detailed validation and packing logs

## Validation Framework

The build process includes an extensible validation framework with built-in validators:

1. **Metadata required fields** - Ensures `metadata.frequencyLocation` is present
2. **Frequency location** - Validates frequency location format (inline, file://, http://)
3. **Frequency data format** - Checks inline frequency data structure, types, and duplicates
4. **File references** - Verifies that referenced data files exist

Validation results are logged and returned with error/warning levels. The build fails if any 
error-level validations fail.

### Custom validators (for hackathon extensibility)

Hackathon participants can register custom validators:

```python
from hfx_tools.validators import ValidationFramework, ValidationResult

def my_custom_validator(metadata_json, hfx_obj, data_folder):
    # Your validation logic here
    return ValidationResult(
        validator_name="my_validator",
        passed=True,
        message="My validation passed",
        level="info"  # or "warning", "error"
    )

validator_framework = ValidationFramework()
validator_framework.register_validator("my_validator", my_custom_validator)
```

## Common Use Cases

### Scenario 1: Batch submission from local folder

Build and submit multiple HFX files from organized folders:

```bash
for dir in submissions/*/; do
  hfx-build "$dir" -n "$(basename $dir)" -o dist/
done
```

### Scenario 2: Remote frequency data

Point to frequencies hosted on Zenodo or S3 without bundling:

```json
{
  "frequencyLocation": "https://zenodo.org/record/12345/files/data.csv",
  ...
}
```

Build skips file detection and includes only the metadata:
```bash
hfx-build my_submission -n my_file --no-auto-update-location
```

### Scenario 3: Inline small frequencies

For small datasets, embed frequencies directly in JSON:

```json
{
  "frequencyLocation": "inline",
  "frequencyData": [
    {"haplotype": "A*01:01", "frequency": 0.123},
    {"haplotype": "A*01:02", "frequency": 0.456}
  ]
}
```

### Scenario 4: Programmatic use in Python

```python
from hfx_tools.build import build

result = build(
    input_folder="my_data/",
    output_name="my_submission",
    output_dir="dist/",
    hash_algorithm="sha256",
    include_manifest=True
)
print(f"Build {'succeeded' if result.success else 'failed'}")
for validation in result.validations:
    print(f"  {validation.level}: {validation.message}")
```

## Developer API

### Using the Validation Framework

```python
from hfx_tools.validators import ValidationFramework, ValidationResult

# Create framework
validator = ValidationFramework()

# Add custom validation
def check_population_size(metadata_json, hfx_obj, data_folder):
    pop_size = metadata_json.get("populationSize", 0)
    if pop_size < 100:
        return ValidationResult(
            validator_name="population_size",
            passed=False,
            message=f"Population too small: {pop_size} < 100",
            level="warning"
        )
    return ValidationResult(
        validator_name="population_size",
        passed=True,
        message=f"Population size OK: {pop_size}",
        level="info"
    )

validator.register_validator("population_size", check_population_size)

# Run validations
results = validator.validate(metadata, hfx, data_folder)
```

### Building programmatically

```python
from hfx_tools.build import build
from hfx_tools.io import read_metadata_json

# Load and modify metadata before building
metadata = read_metadata_json("metadata.json")
metadata["submissionNotes"] = "Added via script"

# Build with custom settings
result = build(
    input_folder=".",
    output_name="my_hfx",
    hash_algorithm="sha256",
    include_manifest=True
)

if not result.success:
    print("Validation errors:")
    for v in result.validations:
        if v.level == "error":
            print(f"  - {v.message}")
```

## Package contents

```
.
├── __init__.py
├── build.py           # Build orchestration (NEW - hackathon MVP)
├── cli.py             # Command-line interface
├── inspect.py         # HFX inspection tools
├── io.py              # JSON and file I/O
├── pack.py            # Low-level packing
├── qc.py              # Quality control
├── streamlit_app.py   # Web UI (NEW - hackathon MVP)
├── util.py            # Utilities
├── validators.py      # Validation framework (NEW - hackathon MVP)
├── Makefile
└── pyproject.toml
```

## Development & Contributing

### Development setup

```bash
# Clone and install with dev dependencies
git clone https://github.com/nmdp-bioinformatics/hfx-tools
cd hfx-tools
make sync EXTRAS="dev,lint"
```

### Running tests and linting

```bash
make fmt       # Format code
make lint      # Check code style
make test      # Run test suite
make build     # Build distribution
```

### Project structure for contributors

- **validators.py** - Add new validators here (see `ValidationResult` class)
- **build.py** - Core build logic, add workflow features here
- **cli.py** - Command-line entry points, add new commands here
- **streamlit_app.py** - Web UI, add interactive features here

### Submitting changes

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Add tests for new functionality
4. Run `make lint test` to verify
5. Submit a pull request

## Troubleshooting

### Issue: "frequencyLocation not found"

**Cause**: Metadata doesn't include the `frequencyLocation` field.

**Solution**: Add to `metadata.json`:
```json
{
  "frequencyLocation": "file://data/frequencies.csv"
}
```

Or use inline frequencies if no external file:
```json
{
  "frequencyLocation": "inline",
  "frequencyData": [...]
}
```

### Issue: Validation errors but can't see why

**Solution**: Check the build log:
```bash
hfx-build my_data -n output
cat my_data/output.build.log    # Detailed validation results
```

### Issue: File not found in bundle

**Cause**: Data file exists but `metadata.frequencyLocation` points to wrong path.

**Solution**: Ensure relative paths match structure:
```
my_data/
├── metadata/
│   └── metadata.json    # with frequencyLocation: "file://data/my_file.csv"
└── data/
    └── my_file.csv      # ← matches the path
```

### Issue: Permission denied when creating .venv

**Solution**: Ensure write permission to directory:
```bash
mkdir -p ~/.hfx-tools
make sync VENV=~/.hfx-tools/.venv
```

## Resources

- [HFX Specification](https://github.com/nmdp-bioinformatics/hfx) - Authoritative format specification and schema
- [phycus](https://github.com/nmdp-bioinformatics/phycus) - Related NMDP bioinformatics tools
- [Issues & Discussions](https://github.com/nmdp-bioinformatics/hfx-tools/issues) - Report bugs or suggest features
- [HFX Spec Issues](https://github.com/nmdp-bioinformatics/hfx/issues) - Discuss spec-related questions



