import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

@pytest.fixture
def fake_ansible():
    ansible = MagicMock()
    ansible.debug_outputs = [{"password.stdout": "user1 pass1\nuser2 pass2", "token": "tok", "agent_status": "running"}]
    ansible.build_inventory.return_value = "inventory"
    ansible.build_inventory_localhost.return_value = "localhost_inventory"
    return ansible


# --- Tests start here ---
def test_get_service_credentials(service, fake_ansible):
    result = service.get_service_credentials(service.description.elastic, fake_ansible)
    assert result == {"user1": "pass1", "user2": "pass2"}
    fake_ansible.run.assert_called_once()


def test_get_service_info(service, fake_ansible):
    result = service.get_service_info(service.description.elastic, fake_ansible, Path("play.yml"), {"k": "v"})
    assert result == fake_ansible.debug_outputs
    fake_ansible.run.assert_called_once()


def test_install_elastic_agent(service, fake_ansible):
    with patch.object(service.client, "get_machine_status", return_value = "RUNNING"):
        fake_ansible.debug_outputs = [{"token": "endpoint_tok"}]
        service.install_elastic_agent(fake_ansible, instances=[1])
        assert fake_ansible.run.called
        assert fake_ansible.build_inventory.called


def test_install_elastic_agent_not_running(service, fake_ansible):
    with patch.object(service.client, "get_machine_status", return_value = "STOPPED"):
        service.install_elastic_agent(fake_ansible, instances=[1])
        assert not fake_ansible.run.called


def test_install_caldera_agent(service, fake_ansible):
    with patch.object(service.client, "get_machine_status", return_value = "RUNNING"):
        service.install_caldera_agent(fake_ansible, [1])
        assert fake_ansible.run.call_count == 2


def test_install_caldera_agent_none(service, fake_ansible):
    with patch.object(service.client, "get_machine_status", return_value = "STOPPED"):
        service.install_caldera_agent(fake_ansible, [1])
        assert not fake_ansible.run.called


def test_manage_packetbeat_status(service, fake_ansible):
    result = service.manage_packetbeat(fake_ansible, "status")
    assert result == "RUNNING"
    fake_ansible.run.assert_called_once()


def test_manage_packetbeat_other(service, fake_ansible):
    result = service.manage_packetbeat(fake_ansible, "restart")
    assert result is None
    fake_ansible.run.assert_called_once()


def test_deploy_packetbeat(service, fake_ansible):
    with patch.object(service.client, "get_machine_status", return_value = "RUNNING"):
        fake_ansible.debug_outputs = [{"token": "tok"}]
        service.deploy_packetbeat(fake_ansible)
        fake_ansible.wait_for_connections.assert_called_once()
        assert fake_ansible.run.call_count == 2


def test_deploy_packetbeat_not_running(service, fake_ansible):
    with patch.object(service.client, "get_machine_status", return_value = "STOPPED"):
        service.deploy_packetbeat(fake_ansible)
        assert not fake_ansible.run.called


def test_destroy_packetbeat(service, fake_ansible):
    service.destroy_packetbeat(fake_ansible)
    if service.config.platform == "aws":
        fake_ansible.run.assert_not_called()
    else:
        fake_ansible.run.assert_called_once()



def test_deploy_destroy_recreate(service):
    # patch internal _apply and _destroy
    with patch.object(service, "_apply") as mock_apply:
        with patch.object(service, "_destroy") as mock_destroy:

            # deploy
            service.deploy(None)
            mock_apply.assert_called_once()
            mock_apply.reset_mock()

            service.deploy([1])
            mock_apply.assert_called_once()
            mock_apply.reset_mock()

            service.config.configure_dns = True
            service.description.elastic.monitor_type = "traffic"
            service.deploy([1])
            mock_apply.assert_called_once()
            mock_apply.reset_mock()


            # destroy
            service.destroy(None)
            mock_destroy.assert_called_once()
            mock_destroy.reset_mock()

            # destroy with resources
            service.destroy([1])
            mock_destroy.assert_not_called()
            mock_destroy.reset_mock()

            service.description.elastic.monitor_type = "endpoint"
            service.destroy([1])
            mock_destroy.assert_not_called()
            mock_destroy.reset_mock()


            # destroy with []
            with patch.object(service, "_get_resources_to_target_destroy", return_value=[]):
                service.destroy([1])
                mock_destroy.assert_not_called()

                # recreate
                service.recreate([1], ["g"], [2])
                mock_apply.assert_called_once()


# def test_get_service_machine_variables(service):
#     service_obj = types.SimpleNamespace(
#         name="svc",
#         base_name="bname",
#         os="linux",
#         interfaces={"eth0": types.SimpleNamespace(name="eth0", network=types.SimpleNamespace(name="net"), private_ip="10.0.0.1")},
#         vcpu=2,
#         memory=1024,
#         disk=20,
#     )
#     result = service._get_service_machine_variables(service_obj)
#     assert result["guest_name"] == "svc"
#     assert "interfaces" in result


def test_get_terraform_variables(service):
    result = service._get_terraform_variables()
    assert "guest_data_json" in result
