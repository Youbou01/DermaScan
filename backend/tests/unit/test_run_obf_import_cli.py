import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "run_obf_import.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_obf_import", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_defaults() -> None:
    cli = _load_script()
    args = cli.parse_args([])
    assert args.limit is None
    assert args.dump_path == cli.DEFAULT_DUMP_PATH


def test_limit_and_dump_path() -> None:
    cli = _load_script()
    args = cli.parse_args(["--limit", "50", "--dump-path", "dump.jsonl.gz"])
    assert args.limit == 50
    assert args.dump_path == Path("dump.jsonl.gz")


@pytest.mark.parametrize("bad", ["0", "-3", "abc"])
def test_invalid_limit_rejected(bad: str) -> None:
    cli = _load_script()
    with pytest.raises(SystemExit):
        cli.parse_args(["--limit", bad])
