import pytest
import io
import click
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from pathlib import Path

import tectonic.cli as cli

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def mock_ctx():
    """Prepare a fake ctx.obj with mocks for Core and Description."""
    mock_config = MagicMock()
    mock_description = MagicMock()
    mock_core = MagicMock()
    return {"config": mock_config, "description": mock_description, "core": mock_core}


# ---- Test helpers ----   
@pytest.fixture()
@patch("tectonic.cli.TectonicConfig.load")
@patch("tectonic.cli.Description")
def base_cli_args(mock_desc, mock_config, tectonic_config_path, labs_path):
    mock_config.load.return_value = MagicMock()
    lab_edition_file = Path(labs_path) / "test.yml"

    return ["-c", str(tectonic_config_path), str(lab_edition_file)]

def run_cli(runner, base_cli_args, extra_args=None, obj=None, **kwargs):
    return runner.invoke(cli.tectonic, base_cli_args+extra_args, obj=obj, **kwargs)

# ---- ParamType ----

def test_number_range_param_type():
    t = cli.NUMBER_RANGE
    assert t.convert("1,3,5", None, None) == [1, 3, 5]
    assert t.convert("1-3", None, None) == [1, 2, 3]
    assert t.convert("", None, None) == []
    assert t.convert([4,2,3], None, None) == [2,3,4]
    with pytest.raises(click.BadParameter):
        t.convert("x", None, None)

def test_range_to_str():
    assert cli.range_to_str([1, 2, 3, 4]) == "from 1 to 4"
    assert cli.range_to_str([1, 3, 4, 5, 7]) == "1, from 3 to 5, and 7"
    assert cli.range_to_str([1, 3, 4]) == "1, 3, and 4"
    assert cli.range_to_str([1]) == "1"
    assert cli.range_to_str([]) == ""

test_cases = [
    { "expected": "Testing all machines, on all instances.",
     },
    { "instances": [10,11,12],
      "expected": "Testing all machines, on all instances.",
     },
    { "instances": [1,2,3,6],
      "guests": ("attacker",),
      "expected": "Testing the attacker, on instances from 1 to 3.",
     },
    { "guests": ("teacher_access", "student_access", "packetbeat"),
      "expected": "Testing the teacher access, the student access and the packetbeat.",
     },
    { "instances": [1],
      "guests": ("victim",),
      "expected": "Testing all copies of the victim, on instance 1.",
     },
    { "guests": ("attacker", "victim", "server"),
      "expected": "Testing the attacker, all copies of the victim and the server, on all instances.",
     },
    { "guests": ("attacker", "victim"),
      "copies": [2],
      "expected": "Testing copy 2 of the victim, on all instances.",
     },
    { "guests": ("attacker", "victim"),
      "copies": [2,3,4],
      "expected": "Testing copies from 2 to 4 of the victim, on all instances.",
     },
]
@pytest.mark.parametrize('test', test_cases)
def test_confirm_machines(monkeypatch, description, runner, mock_ctx, capsys, test):
    ctx = click.Context(click.Command('tectonic'),
                        obj={'description': description})

    # Use more instances and copies, so we can test more conditions
    ctx.obj["description"].instance_number = 5
    ctx.obj["description"].base_guests["victim"].copies = 4

    monkeypatch.setattr('sys.stdin', io.StringIO("y"))
    
    cli.confirm_machines(ctx,
                         test.get("instances"),
                         test.get("guests"),
                         test.get("copies"),
                         "Testing")
    captured = capsys.readouterr()
    assert test.get("expected", "") in captured.out

    # Restore description values
    ctx.obj["description"].instance_number = 2
    ctx.obj["description"].base_guests["victim"].copies = 2


# ---- Commands ----

@patch("tectonic.cli.Core")
def test_tectonic_group_initialization(mock_core, runner, base_cli_args, mock_ctx):
    result = run_cli(runner, base_cli_args, ["info"], obj=mock_ctx)

    assert result.exit_code == 0
    mock_core.assert_called()

@patch("tectonic.cli.Core")
def test_deploy(mock_core, runner, base_cli_args, mock_ctx):
    result = run_cli(runner, base_cli_args, ["deploy", "-f"], obj=mock_ctx)
    assert result.exit_code == 0
    mock_ctx["core"].deploy.assert_called_once()
    mock_ctx["core"].create_instances_images.assert_not_called()
    
    mock_ctx["core"].reset_mock()

    result = run_cli(runner, base_cli_args, ["deploy", "-f", "--images"], obj=mock_ctx)
    assert result.exit_code == 0
    mock_ctx["core"].create_instances_images.assert_called_once()
    mock_ctx["core"].deploy.assert_called_once()


@patch("tectonic.cli.Core")
def test_destroy(mock_core, runner, base_cli_args,  mock_ctx):
    run_cli(runner, base_cli_args, ["destroy", "-f"], obj=mock_ctx)
    mock_ctx["core"].destroy.assert_called_once()

    # Invalid invokations
    result = run_cli(runner, base_cli_args, ["destroy", "-f", "-i", "1", "--no-machines"], obj=mock_ctx)
    assert result.exit_code != 0

    result = run_cli(runner, base_cli_args, ["destroy", "-f", "-i", "1", "--caldera"], obj=mock_ctx)
    assert result.exit_code != 0

@patch("tectonic.cli.Core")
def test_create_images(mock_core, runner, base_cli_args, mock_ctx):
    result = run_cli(runner, base_cli_args, ["create-images"], obj=mock_ctx)
    assert result.exit_code == 0
    mock_ctx["core"].create_instances_images.assert_called_once()

@patch("tectonic.cli.Core")
def test_list_instance(mock_core, runner, base_cli_args, mock_ctx):
    with patch("tectonic.cli.utils.create_table", return_value="TABLE"):
        result = run_cli(runner, base_cli_args, ["list"], obj=mock_ctx)
        assert result.exit_code == 0
        assert "TABLE" in result.output

@patch("tectonic.cli.Core")
def test_start_stop_reboot(mock_core, base_cli_args, runner, mock_ctx):
    result = run_cli(runner, base_cli_args, ["start", "-f"], obj=mock_ctx)
    assert result.exit_code == 0
    mock_ctx["core"].start.assert_called_once()
    result = run_cli(runner, base_cli_args, ["shutdown", "-f"], obj=mock_ctx)
    assert result.exit_code == 0
    mock_ctx["core"].stop.assert_called_once()
    result = run_cli(runner, base_cli_args, ["reboot", "-f"], obj=mock_ctx)
    assert result.exit_code == 0
    mock_ctx["core"].restart.assert_called_once()

@patch("tectonic.cli.Core")
def test_console(mock_core, base_cli_args, runner, mock_ctx):
    result = run_cli(runner, base_cli_args, ["console"], obj=mock_ctx)
    assert result.exit_code == 0
    mock_ctx["core"].console.assert_called_once()

@patch("tectonic.cli.Core")
def test_run_ansible(mock_core, base_cli_args, runner, mock_ctx):
    result = run_cli(runner, base_cli_args, ["run-ansible", "-f"], obj=mock_ctx)
    assert result.exit_code == 0
    mock_ctx["core"].run_automation.assert_called_once()


@patch("tectonic.cli.Core")
def test_student_access(mock_core, base_cli_args, runner, mock_ctx):
    with patch("tectonic.cli.utils.create_table", return_value="TABLE"):
        result = run_cli(runner, base_cli_args, ["student-access", "-f"], obj=mock_ctx)
        assert result.exit_code == 0
        assert "TABLE" in result.output
    mock_ctx["core"].configure_students_access.assert_called_once()

@patch("tectonic.cli.Core")
def test_recreate(mock_core, base_cli_args, runner, mock_ctx):
    result = run_cli(runner, base_cli_args, ["recreate", "-f"], obj=mock_ctx)
    assert result.exit_code == 0
    mock_ctx["core"].recreate.assert_called_once()

@patch("tectonic.cli.Core")
def test_show_parameters(mock_core, base_cli_args, runner, mock_ctx):
    with patch("tectonic.cli.utils.create_table", return_value="TABLE"):
        result = run_cli(runner, base_cli_args, ["show-parameters"], obj=mock_ctx)
        assert result.exit_code == 0
        assert "TABLE" in result.output
    mock_ctx["core"].get_parameters.assert_called_once()

@patch("tectonic.cli.Core")
def test_info(mock_core, base_cli_args, runner, mock_ctx):
    with patch("tectonic.cli.utils.create_table", return_value="TABLE"):
        result = run_cli(runner, base_cli_args, ["info"], obj=mock_ctx)
        assert result.exit_code == 0
        assert "TABLE" in result.output
    mock_ctx["core"].info.assert_called_once()

# def test_info_and__info(runner, mock_ctx):
#     with patch("tectonic.cli.utils.create_table", return_value="TABLE"):
#         result = run_cli(runner, ["info"], obj=mock_ctx)
#         assert "TABLE" in result.output


