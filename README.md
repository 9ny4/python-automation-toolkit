# 🐍 Python Automation Toolkit

A practical collection of Python automation scripts for everyday business tasks.
Clean, well-documented, and ready to drop into any workflow.

## Scripts

| Script | Description | Quick Usage |
|--------|-------------|-------------|
| [`organize.py`](scripts/organize.py) | Sort files into folders by type | `python organize.py --source ~/Downloads --dry-run` |
| [`csv_toolkit.py`](scripts/csv_toolkit.py) | Merge, dedupe, filter & inspect CSVs | `python csv_toolkit.py stats -i data.csv` |

---

## Installation

```bash
git clone https://github.com/9ny4/python-automation-toolkit.git
cd python-automation-toolkit
pip install -r requirements.txt
```

---

## Script Reference

### 📁 organize.py — File Organizer

Scans a directory and moves files into categorized subdirectories:

| Extension(s) | Destination |
|---|---|
| jpg, jpeg, png, gif, webp, bmp, svg | `Images/` |
| pdf, doc, docx, txt, xlsx, csv, pptx | `Documents/` |
| mp4, mov, avi, mkv, wmv | `Videos/` |
| mp3, wav, flac, aac, ogg | `Audio/` |
| zip, tar, gz, rar, 7z | `Archives/` |
| everything else | `Other/` |

**Usage**

```
python scripts/organize.py [OPTIONS]

Options:
  -s, --source PATH   Directory to scan  [required]
  -d, --dest PATH     Destination root (default: same as source)
  -n, --dry-run       Preview changes without moving files
  -v, --verbose       Enable debug logging
  --log-file PATH     Write log to file
  --help              Show this message and exit.
```

**Examples**

```bash
# Preview what would happen (safe to run first)
python scripts/organize.py --source ~/Downloads --dry-run

# Organize into a separate destination folder
python scripts/organize.py --source ~/Downloads --dest ~/Sorted

# Verbose mode + save log
python scripts/organize.py --source ~/Desktop --verbose --log-file organize.log
```

**Sample output**

```
09:14:22 | INFO     | Source      : /home/user/Downloads
09:14:22 | INFO     | Destination : /home/user/Downloads

 Organizer Summary
┌─────────────┬───────┬───────────────────────────────────┐
│ Category    │ Files │ Sample                            │
├─────────────┼───────┼───────────────────────────────────┤
│ Archives    │     2 │ project_backup.zip, assets.tar.gz │
│ Audio       │     2 │ podcast.mp3, ambient.flac         │
│ Documents   │     4 │ report_q1.pdf, notes.txt, …       │
│ Images      │     4 │ photo_vacation.jpg, …             │
│ Other       │     2 │ readme_random.md, unknown_file…   │
│ Videos      │     2 │ intro.mp4, tutorial.mov           │
├─────────────┼───────┼───────────────────────────────────┤
│ Total       │    16 │                                   │
└─────────────┴───────┴───────────────────────────────────┘

Done. 16 file(s) organized into /home/user/Downloads
```

---

### 📊 csv_toolkit.py — CSV Toolkit

Four subcommands for common CSV operations.

**Usage**

```
python scripts/csv_toolkit.py [COMMAND] [OPTIONS]

Commands:
  merge    Combine multiple CSV files
  dedupe   Remove duplicate rows
  filter   Keep/exclude rows by column value
  stats    Print summary statistics
```

---

#### `merge` — Combine CSVs

Merges multiple CSV files into one, handling different column sets gracefully.
Adds a `_source_file` column so you know where each row came from.

```bash
python scripts/csv_toolkit.py merge \
  -i samples/jan.csv \
  -i samples/feb.csv \
  -i samples/mar.csv \
  -o output/q1_combined.csv
```

Output:
```
Merged 3 files → 62 rows, 9 columns
✓ Saved 62 rows → output/q1_combined.csv
```

---

#### `dedupe` — Remove Duplicates

```bash
# Dedupe on all columns
python scripts/csv_toolkit.py dedupe -i data.csv -o clean.csv

# Dedupe on specific columns (keep first occurrence)
python scripts/csv_toolkit.py dedupe -i contacts.csv -o clean.csv --cols email

# Dedupe on multiple columns, keep last
python scripts/csv_toolkit.py dedupe -i orders.csv -o clean.csv --cols customer_id,product --keep last
```

Options:
- `--cols` — comma-separated column names (default: all columns)
- `--keep` — `first` (default), `last`, or `none` (drop all duplicates)

---

#### `filter` — Filter Rows

```bash
# Keep only active customers
python scripts/csv_toolkit.py filter \
  -i samples/sample.csv -o active.csv \
  --col status --value active

# Exclude cancelled rows
python scripts/csv_toolkit.py filter \
  -i samples/sample.csv -o no_cancelled.csv \
  --col status --value cancelled --exclude
```

---

#### `stats` — Summary Statistics

```bash
python scripts/csv_toolkit.py stats -i samples/sample.csv
python scripts/csv_toolkit.py stats -i samples/sample.csv --full   # includes percentiles
```

Sample output:
```
         Overview: sample.csv
┌──────────────┬──────────────────┐
│ Metric       │            Value │
├──────────────┼──────────────────┤
│ Rows         │               20 │
│ Columns      │               12 │
│ Memory usage │             14.2 KB │
└──────────────┴──────────────────┘

                      Column Details
┌────────────────┬─────────┬──────────┬──────┬────────┬───────────┐
│ Column         │ Type    │ Non-null │ Null │ Unique │ Sample    │
├────────────────┼─────────┼──────────┼──────┼────────┼───────────┤
│ id             │ int64   │ 20       │ 0    │ 20     │ 1, 2, 3   │
│ name           │ object  │ 20       │ 0    │ 20     │ Alice...  │
│ status         │ object  │ 20       │ 0    │ 3      │ active... │
│ monthly_revenue│ float64 │ 20       │ 0    │ 4      │ 299.0...  │
│ ...            │ ...     │ ...      │ ...  │ ...    │ ...       │
└────────────────┴─────────┴──────────┴──────┴────────┴───────────┘
```

---

## Sample Data

The `samples/` directory contains:

- `sample_files/` — 16 dummy files of different types for testing `organize.py`
- `sample.csv` — 20 realistic CRM customer records for testing `csv_toolkit.py`

---

## Requirements

- Python 3.10+
- [click](https://click.palletsprojects.com/) — CLI framework
- [rich](https://rich.readthedocs.io/) — terminal output / tables
- [loguru](https://loguru.readthedocs.io/) — structured logging
- [pandas](https://pandas.pydata.org/) — CSV processing

---

## License

MIT — use freely, attribution appreciated.
