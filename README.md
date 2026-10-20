# Advanced Calculator

![CI](https://github.com/Chiraagrah/Calculator_Application/actions/workflows/python-app.yml/badge.svg)

A command-line calculator built around a REPL. It supports ten arithmetic operations, undo/redo, CSV persistence with pandas, file logging, and configuration through a `.env` file. All arithmetic uses `Decimal`, so `0.1 + 0.2` is exactly `0.3`.

## Features

- Ten operations: add, subtract, multiply, divide, power, root, modulus, int_divide, percent, abs_diff
- Undo and redo of every change to history (including `clear` and `load`)
- History saved to and loaded from CSV using pandas, with automatic saving after each calculation
- Logging to a file at INFO, WARNING, and ERROR levels
- Color-coded output on terminals, with automatic fallback to plain text
- Help menu generated from the registered operations and commands

## Design patterns

| Pattern | Where | Purpose |
|---|---|---|
| Factory | `OperationFactory` in `app/operations.py` | Creates operation objects from command names |
| Memento | `CalculatorMemento`, `Calculator.undo/redo` | Snapshots history for undo and redo |
| Observer | `LoggingObserver`, `AutoSaveObserver` in `app/history.py` | React to each new calculation |
| Decorator | `@describe` and `@command` | Attach help text and register commands, so help updates automatically |
| Command | `app/commands.py` | Each REPL request is an object executed by the REPL |

## Project structure

```
app/
  calculator.py          Calculator: calculations, rounding, history, undo/redo
  calculation.py         Immutable Calculation record with dict serialization
  calculator_config.py   Validated settings loaded from .env
  calculator_memento.py  Memento snapshot
  commands.py            Command pattern, registry, and parser
  colors.py              Terminal-aware color helper
  exceptions.py          Custom exceptions
  history.py             Observers and the pandas-backed HistoryStore
  input_validators.py    Input validation
  logger.py              File logging setup
  operations.py          Operations, factory, and @describe decorator
  repl.py                REPL loop and application entry point
tests/                   pytest suite (one module per app module)
main.py                  Entry point
```

## Installation

```bash
git clone https://github.com/Chiraagrah/Calculator_Application.git
cd Calculator_Application
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

Settings are read from `.env` (loaded with python-dotenv). Every value is optional; the defaults below apply when a variable is unset or blank. A value that is set but invalid stops the program at startup with a message naming the variable.

| Variable | Default | Meaning |
|---|---|---|
| `CALCULATOR_LOG_DIR` | `logs` | Directory for the log file |
| `CALCULATOR_HISTORY_DIR` | `history` | Directory for the history CSV |
| `CALCULATOR_LOG_FILE` | `calculator.log` | Log file name |
| `CALCULATOR_HISTORY_FILE` | `calculator_history.csv` | History file name |
| `CALCULATOR_MAX_HISTORY_SIZE` | `100` | Maximum history entries; the oldest is dropped when full |
| `CALCULATOR_AUTO_SAVE` | `true` | `true` or `false`; save after every calculation |
| `CALCULATOR_PRECISION` | `10` | Decimal places (0 to 28) |
| `CALCULATOR_MAX_INPUT_VALUE` | `1000000` | Largest allowed absolute input value |
| `CALCULATOR_DEFAULT_ENCODING` | `utf-8` | Encoding for the log and CSV files |

## Usage

```bash
python main.py
```

Operations take exactly two numbers: `<operation> <a> <b>`.

| Command | Description |
|---|---|
| `add`, `subtract`, `multiply`, `divide` | Basic arithmetic |
| `power a b` | a raised to the power b |
| `root a n` | nth root of a |
| `modulus a b` | Remainder of a divided by b |
| `int_divide a b` | Integer quotient of a divided by b |
| `percent a b` | (a / b) * 100 |
| `abs_diff a b` | Absolute difference |
| `history` | Show calculation history |
| `clear` | Clear history (undoable) |
| `undo` / `redo` | Step backward or forward through history changes |
| `save` / `load` | Write history to CSV, or replace history from CSV (undoable) |
| `help` | List operations and commands |
| `exit` | Quit |

Sample session:

```
Advanced Calculator. Type 'help' for commands, 'exit' to quit.
calc> add 2 3
Result: 5
calc> divide 1 3
Result: 0.3333333333
calc> divide 1 0
Error: Division by zero is not allowed
calc> history
1. add(2, 3) = 5
2. divide(1, 3) = 0.3333333333
calc> undo
Undone. History now has 1 entries.
calc> redo
Redone. History now has 2 entries.
calc> exit
Goodbye!
```

### Behavior worth knowing

- Results are rounded half-to-even to `CALCULATOR_PRECISION` places, so `5 / 2` at precision 0 gives `2`.
- `modulus` and `int_divide` truncate toward zero, so `-7 % 3` is `-1` and `-7 // 2` is `-3`.
- Scientific notation (`1e3`), `NaN`, and `Infinity` are rejected as input.
- `undo`, `redo`, and `load` do not trigger an auto-save. Run `save` if you want the CSV to match the current state.
- Failed calculations are logged as warnings and never change history.

## Logging

The log file rotates at about 1 MB and keeps the 3 most recent backups (calculator.log.1 to .3), so it cannot grow without limit

## Testing

```bash
pytest                                   # runs the suite with coverage (see pytest.ini)
pytest --cov=app --cov-fail-under=90     # same check CI enforces
```

## Continuous integration

`.github/workflows/python-app.yml` runs on every push and pull request to `main`: it checks out the code, sets up Python, installs `requirements.txt`, runs pytest with coverage, and fails the build if coverage drops below 90%.