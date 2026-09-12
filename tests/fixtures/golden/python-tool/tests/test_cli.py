from rn_forge.cli import ExitCode, run

from golden_tool.main import app


def test_the_declared_app_exposes_the_declared_command(capsys):
    assert run(app, ["hello", "kiln"]) == ExitCode.OK
    assert "Hello, kiln!" in capsys.readouterr().out


def test_an_unknown_command_is_a_usage_error():
    assert run(app, ["nope"]) == ExitCode.USAGE


def test_a_missing_argument_is_a_usage_error():
    assert run(app, ["hello"]) == ExitCode.USAGE
