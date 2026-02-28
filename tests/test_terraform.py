import pytest
from unittest.mock import MagicMock, patch
from tectonic.terraform import TerraformException

def test_run_terraform_cmd_success(terraform):
    mock_t = MagicMock()
    mock_t.cmd = MagicMock(return_value = (0, "stdout", "stderr"))
    result = terraform._run_terraform_cmd(mock_t, "apply", {"x": "y"})
    assert result == "stdout"
    mock_t.cmd.assert_called_once()


def test_run_terraform_cmd_failure(terraform):
    mock_t = MagicMock()
    mock_t.cmd = MagicMock(return_value = (1, "stdout", "terrible error"))
    with pytest.raises(TerraformException):
        terraform._run_terraform_cmd(mock_t, "apply", {})


def test_generate_backend_config_file(terraform):
    terraform.BACKEND_TYPE = "FILE"
    result = terraform._generate_backend_config("/tmp/mydir")
    assert terraform.description.lab_name in result[0]


def test_generate_backend_config_gitlab(terraform):
    terraform.BACKEND_TYPE = "GITLAB"
    terraform.config.gitlab_backend_username = "sometestuser"
    result = terraform._generate_backend_config("/tmp/mydir")
    in_r = (terraform.config.gitlab_backend_username in r for r in result)
    assert any(terraform.config.gitlab_backend_username in r for r in result)

def test_generate_backend_config_invalid(terraform):
    terraform.BACKEND_TYPE = "x"
    result = terraform._generate_backend_config("/tmp/mydir")
    assert result is None

def test_apply(terraform):
    with patch.object(terraform, '_run_terraform_cmd', return_value="ok") as mock_run:
        terraform._apply("dir", {"var": "val"})
        assert mock_run.call_count == 3
        assert mock_run.call_args_list[0][0][1] == "init"
        assert mock_run.call_args_list[1][0][1] == "plan"
        assert "target" in mock_run.call_args_list[1][1]
        assert mock_run.call_args_list[2][0][1] == "apply"
        assert "target" in mock_run.call_args_list[2][1]

        mock_run.reset_mock()

        terraform._apply("dir", {"var": "val"}, resources=["res"], recreate=True)
        assert mock_run.call_count == 3
        assert mock_run.call_args_list[0][0][1] == "init"
        assert mock_run.call_args_list[1][0][1] == "plan"
        assert "replace" in mock_run.call_args_list[1][1]
        assert mock_run.call_args_list[2][0][1] == "apply"
        assert "replace" in mock_run.call_args_list[2][1]


def test_deploy(terraform):
    with patch.object(terraform, '_apply') as mock_apply:
        terraform.deploy(None)
        mock_apply.assert_called_once()

        mock_apply.reset_mock()
        terraform.deploy([1])
        mock_apply.assert_called_once()

        mock_apply.reset_mock()
        terraform.config.aws.teacher_access = "endpoint"
        terraform.config.configure_dns = True
        terraform.description._base_guests["attacker"].internet_access = True
        terraform.deploy([1])
        mock_apply.assert_called_once()

def test_destroy(terraform):
    with patch.object(terraform, '_run_terraform_cmd', return_value="ok") as mock_run:
        terraform.destroy(None)
        assert mock_run.call_count == 2
        assert mock_run.call_args_list[0][0][1] == "init"
        assert mock_run.call_args_list[1][0][1] == "destroy"

        mock_run.reset_mock()
        terraform.destroy([1])
        assert mock_run.call_count == 2
        assert mock_run.call_args_list[0][0][1] == "init"
        assert mock_run.call_args_list[1][0][1] == "destroy"

        mock_run.reset_mock()
        terraform.config.configure_dns = True
        terraform.destroy([1])
        assert mock_run.call_count == 2
        assert mock_run.call_args_list[0][0][1] == "init"
        assert mock_run.call_args_list[1][0][1] == "destroy"
        
def test_recreate(terraform):
    with patch.object(terraform, '_apply', return_value="ok") as mock_apply:
        terraform.recreate([1], [], [])
        mock_apply.assert_called_once()

# def test_deploy_and_destroy_and_recreate(terraform, monkeypatch):
#     monkeypatch.setattr(terraform, "_apply", lambda *a, **kw: "applied")
#     monkeypatch.setattr(terraform, "_destroy", lambda *a, **kw: "destroyed")

#     terraform.deploy([1])
#     terraform.deploy(None)
#     terraform.destroy([1])
#     terraform.destroy(None)
#     terraform.recreate([1], ["guest"], [2])


# def test_get_guest_and_interface_variables(terraform):
#     class DummyInterface:
#         def __init__(self):
#             self.name = "eth0"
#             self.private_ip = "10.0.0.1"
#             self.network = type("N", (), {"name": "net"})()

#     class DummyGuest:
#         def __init__(self):
#             self.base_name = "base"
#             self.name = "g1"
#             self.vcpu = 2
#             self.memory = 2048
#             self.disk = 10
#             self.hostname = "h"
#             self.os = "linux"
#             self.interfaces = {"i": DummyInterface()}
#             self.is_in_services_network = True

#     guest = DummyGuest()
#     iface_vars = terraform._get_network_interface_variables(list(guest.interfaces.values())[0])
#     assert iface_vars["name"] == "eth0"

#     guest_vars = terraform._get_guest_variables(guest)
#     assert guest_vars["vcpu"] == 2
#     assert "interfaces" in guest_vars


# def test_get_terraform_variables(terraform, config, description, monkeypatch):
#     monkeypatch.setattr("yourmodule.OS_DATA", {"os": "data"})
#     monkeypatch.setattr("yourmodule.json.dumps", lambda x: f"json:{len(x)}")

#     result = terraform._get_terraform_variables()
#     assert "institution" in result
#     assert result["os_data_json"].startswith("json:")
