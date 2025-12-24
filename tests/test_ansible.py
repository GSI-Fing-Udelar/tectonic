import pytest
import types
from unittest.mock import MagicMock, patch
from tectonic.ansible import Ansible, AnsibleException

@pytest.fixture(scope="session")
def fake_client():
    client = MagicMock()
    client.get_ssh_hostname.return_value = "host1"
    client.get_ssh_proxy_command.return_value = None
    return client


@pytest.fixture()
def ansible_client(tectonic_config, description, fake_client):
    return Ansible(tectonic_config, description, fake_client)


def test_ansible_callback_basic(ansible_client):
    event = {"stdout": "hello"}
    assert ansible_client._ansible_callback(event) is True
    assert "hello" in ansible_client.output


def test_ansible_callback_with_debug(ansible_client):
    event = {
        "stdout": "out",
        "event_data": {
            "resolved_action": "ansible.builtin.debug",
            "res": {
                "_ansible_verbose_always": 1,
                "_ansible_no_log": True,
                "changed": True,
                "foo": "bar",
            },
        },
    }
    ansible_client._ansible_callback(event)
    assert {"foo": "bar"} in ansible_client.debug_outputs


def test_build_inventory_linux(ansible_client):
    inv = ansible_client.build_inventory(["udelar-lab01-1-attacker"])
    assert "attacker" in inv
    assert "udelar-lab01-1-attacker" in inv["attacker"]["hosts"]


def test_build_inventory_windows(ansible_client):
    ansible_client.description.base_guests["attacker"].os = "windows_srv_2022"
    inv = ansible_client.build_inventory(["udelar-lab01-1-attacker"])
    host = inv["attacker"]["hosts"]["udelar-lab01-1-attacker"]
    assert host["ansible_shell_type"] == "powershell"


def test_build_inventory_localhost(ansible_client):
    inv = ansible_client.build_inventory_localhost(username="u")
    key = list(inv.keys())[0]
    assert "localhost" in inv[key]["hosts"]


@patch("tectonic.ansible.ansible_runner.interface.run")
def test_run_with_missing_playbook(mock_run, ansible_client):
    # no playbook file exists
    with pytest.raises(AnsibleException):
        ansible_client.run(playbook="not_found.yml")
    mock_run.assert_not_called()


@patch("tectonic.ansible.ansible_runner.interface.run")
def test_run_with_existing_playbook_success(mock_run, ansible_client):
    mock_run.return_value = types.SimpleNamespace(rc=0, status="successful")
    ansible_client.run()
    mock_run.assert_called_once()


@patch("tectonic.ansible.ansible_runner.interface.run")
def test_run_with_failure_quiet(mock_run, ansible_client):
    mock_run.return_value = types.SimpleNamespace(rc=1, status="failed")
    with pytest.raises(AnsibleException):
        ansible_client.run(quiet=True)


@patch("tectonic.ansible.Ansible.run")
def test_wait_for_connections(mock_run, ansible_client):
    ansible_client.wait_for_connections()
    mock_run.assert_called_once()


@patch("tectonic.ansible.Ansible.run")
@patch("tectonic.ansible.Ansible.wait_for_connections")
def test_configure_services(mock_wait, mock_run, ansible_client):
    ansible_client.configure_services()
    mock_wait.assert_called_once()
    mock_run.assert_called_once()


def test_configure_services_empty(ansible_client):
    # no services => nothing happens
    ansible_client.description.elastic.enable = False
    ansible_client.description.caldera.enable = False
    ansible_client.description.guacamole.enable = False
    ansible_client.description.moodle.enable = False
    ansible_client.description.bastion_host.enable = False
    ansible_client.description.teacher_access_host.enable = False
    # should not raise
    ansible_client.configure_services()
