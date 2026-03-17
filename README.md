# FOA Fetcher

This script fetches recent funding opportunity announcements (FOAs) from the grants.gov API and exports them to JSON and CSV files with basic rule-based tagging.

At a high level, the pipeline in [main.py](main.py) does the following:
- Calls the grants.gov search API (via `fetch_recent_opportunities`) to pull FOAs posted in the last 24 hours.
- Normalizes and cleans text fields (HTML → plain text, whitespace cleanup, date parsing).
- Runs simple rule-based keyword matching (`rule_based_tagging`) to assign tags to each FOA.
- Attaches the `Source URL` you pass on the command line to every record.
- Serializes the results to `foa.json` and `foa.csv` in the chosen output directory.

## Requirements

- Python 3.8+
- Dependencies listed in `requirements.txt`

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

From the project directory:

```bash
python main.py --url "https://www.grants.gov" --out_dir ./out
```

Arguments:
- `--url` (required): A source URL string that will be recorded in each record under the `Source URL` field in both JSON and CSV.
- `--out_dir` (optional, default `./out`): Directory where the outputs will be written.

## Output

- JSON: `<out_dir>/foa.json`
- CSV: `<out_dir>/foa.csv`

Each record includes fields such as FOA ID, title, agency, open/close dates, eligibility text, program description, award information, and a `Source URL` field populated from `--url`, along with basic rule-based tags inferred from the text.

## Implementation Details

Key pieces in [main.py](main.py):
- **Ontology and keywords**: A small controlled ontology and `RULE_KEYWORDS` map define which concepts can be tagged (e.g., `food safety`, `training`, `trade development`).
- **Tagging logic**: `rule_based_tagging(text)` lowercases the combined FOA text and checks for keyword occurrences with simple regex word-boundary matching, returning a list of tags.
- **Extraction**: `extract_foa(record, source_url)` pulls fields from the raw API record, normalizes them, computes tags, and injects the `Source URL` into each record.
- **Processing**: `process_records(records, source_url)` applies `extract_foa` to every API record and returns a list of FOA dictionaries ready for export.
- **Persistence**: `save_json` and `save_csv` write that list to disk; the CSV headers are derived from the FOA dictionary keys so JSON and CSV stay aligned.
- **CLI entrypoint**: `main()` parses `--url` and `--out_dir`, ensures the output directory exists, and then calls `run_pipeline` which orchestrates fetch → process → save.
