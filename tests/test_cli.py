from pathlib import Path

from typer.testing import CliRunner

from goldcoast.cli import app

PROJECT_ROOT = Path(__file__).parents[1]
runner = CliRunner()


def test_validate_seed_prints_counts() -> None:
    result = runner.invoke(app, ["validate-seed", "--data-dir", str(PROJECT_ROOT / "data")])
    assert result.exit_code == 0, result.output
    assert "athletes: 1" in result.output
    assert "businesses: 3" in result.output
    assert "ad_styles: 2" in result.output
    assert "venues: 2" in result.output


def test_stage_stubs_exit_nonzero() -> None:
    for command in ("run",):
        result = runner.invoke(app, [command, "input.json"])
        assert result.exit_code != 0
        assert "not implemented" in result.output
