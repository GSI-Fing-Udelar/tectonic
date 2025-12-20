import pytest
import json

from unittest.mock import patch, call

from tectonic.packer import PackerException
import packerpy

def test_create_instance_image(mocker, packer):
    m = mocker.patch.object(packer, "_invoke_packer")
    packer.create_instance_image(["attacker"])

    m.assert_called_once()
    assert 'image_generation/create_image.pkr.hcl' in str(m.call_args[0][0])
    assert "machines_json" in m.call_args[0][1]
    assert "tectonic_json" in m.call_args[0][1]
    assert "guests_json" in m.call_args[0][1]
    assert "networks_json" in m.call_args[0][1]
    mj = m.call_args[0][1]['machines_json']
    assert "attacker" in mj

def test_create_instance_image_proxy(mocker, packer):
    old_proxy = packer.config.proxy
    proxy = 'http://proxy.example.com:3128'
    packer.config.proxy = proxy

    m = mocker.patch.object(packer, "_invoke_packer")
    packer.create_instance_image(["attacker"])

    m.assert_called_once()
    arguments = json.loads(m.call_args[0][1]['tectonic_json'])
    assert "proxy" in arguments['config']
    proxy_var = arguments['config']['proxy']
    assert proxy in proxy_var

    packer.config.proxy = old_proxy


def test_create_service_image(mocker, packer):
    m = mocker.patch.object(packer, "_invoke_packer")
    packer.create_service_image(["caldera"])

    m.assert_called_once()
    assert 'services/image_generation/create_image.pkr.hcl' in str(m.call_args[0][0])
    assert "machines_json" in m.call_args[0][1]
    assert "tectonic_json" in m.call_args[0][1]
    mj = m.call_args[0][1]['machines_json']
    assert "caldera" in mj

def test_create_service_image_empty(mocker, packer):
    m = mocker.patch.object(packer, "_invoke_packer")
    packer.create_service_image([])
    m.assert_not_called()
    
def test_create_service_image_proxy(mocker, packer):
    old_proxy = packer.config.proxy
    proxy = 'http://proxy.example.com:3128'
    packer.config.proxy = proxy

    m = mocker.patch.object(packer, "_invoke_packer")
    packer.create_service_image(["caldera"])

    m.assert_called_once()
    arguments = json.loads(m.call_args[0][1]['tectonic_json'])
    assert "proxy" in arguments['config']
    proxy_var = arguments['config']['proxy']
    assert proxy in proxy_var

    packer.config.proxy = old_proxy


def test_destroy_instance_image(mocker, packer):
    m = mocker.patch.object(packer.client, "delete_image")

    # Try to delete an image that is in use
    with pytest.raises(PackerException, match="Unable to delete image"):
        packer.destroy_instance_image(["attacker"])

    # Mark it as unused
    mocker.patch.object(packer.client, "is_image_in_use", return_value=False)
    packer.destroy_instance_image(["attacker"])
    m.assert_called_once_with("udelar-lab01-attacker")


def test_destroy_service_image(mocker, packer):
    m = mocker.patch.object(packer.client, "delete_image")

    mocker.patch.object(packer.client, "is_image_in_use", return_value=True)
    with pytest.raises(PackerException, match="Unable to delete image"):
        packer.destroy_service_image(["caldera"])

    mocker.patch.object(packer.client, "is_image_in_use", return_value=False)
    packer.destroy_service_image(["caldera"])
    m.assert_called_once_with("caldera")

def test_invoke_packer_fail(mocker, packer):
    with pytest.raises(PackerException, match="Packer init returned an error"):
        packer._invoke_packer("x", {})

    mocker.patch.object(packerpy.PackerExecutable, 'build', return_value=(2, ''.encode(), None))
    with pytest.raises(PackerException, match="Packer build returned an error"):
        packer._invoke_packer(packer.INSTANCES_PACKER_MODULE, {})

    mocker.patch.object(packerpy.PackerExecutable, 'build', return_value=(0, ''.encode(), None))
    packer._invoke_packer(packer.INSTANCES_PACKER_MODULE, {}) # Success


# def test_create_instance_image_calls_invoke(monkeypatch):
#     config, description, client, _ = make_common_objects()
#     p = ConcretePacker(config, description, client)

#     called = {}
#     def fake_invoke(module, variables):
#         called['module'] = module
#         called['vars'] = variables

#     monkeypatch.setattr(p, "_invoke_packer", fake_invoke)
#     p.create_instance_image(["g1"])
#     assert 'module' in called
#     assert "machines_json" in called['vars']
#     mj = json.loads(called['vars']['machines_json'])
#     assert "g1" in mj


# def test_create_service_image_enabled_and_disabled(monkeypatch):
#     config, description, client, _ = make_common_objects()
#     p = ConcretePacker(config, description, client)

#     # When services list intersects with enabled_services -> should call _invoke_packer
#     called = {"count": 0}
#     def fake_invoke(module, variables):
#         called["count"] += 1
#         called["module"] = module
#     monkeypatch.setattr(p, "_invoke_packer", fake_invoke)

#     # description.services_guests has svc1 as base_name (from helper)
#     enabled_services = [service.base_name for _, service in description.services_guests.items()]
#     # call with intersecting services
#     p.create_service_image(enabled_services)
#     assert called["count"] == 1

#     # call with non intersecting services -> should not call again
#     called["count"] = 0
#     p.create_service_image(["not_present"])
#     assert called["count"] == 0


# def test_destroy_instance_image_in_use_and_delete(monkeypatch):
#     config, description, client, deleted = make_common_objects()
#     p = ConcretePacker(config, description, client)

#     # Mark the base image as in use and expect exception
#     client._in_use.add("g1.img")
#     with pytest.raises(PackerException) as excinfo:
#         p.destroy_instance_image(["g1"])
#     assert "Unable to delete image g1" in str(excinfo.value)

#     # Clear in-use and expect delete called
#     client._in_use.clear()
#     deleted.clear()
#     p.destroy_instance_image(["g1"])
#     assert "g1.img" in deleted


# def test_destroy_service_image_in_use_and_delete(monkeypatch):
#     config, description, client, deleted = make_common_objects()
#     p = ConcretePacker(config, description, client)

#     client._in_use.add("svc1.img")
#     with pytest.raises(PackerException):
#         p.destroy_service_image(["svc1"])

#     client._in_use.clear()
#     deleted.clear()
#     p.destroy_service_image(["svc1"])
#     assert "svc1.img" in deleted


# def test_get_instance_variables_proxy_and_ansible_scp_extra_args(monkeypatch):
#     # Test branches for proxy and ansible scp extra args depending on ssh_version and platform
#     config, description, client, _ = make_common_objects()
#     # set platform to non-docker to get '-O' when ssh_version >= 9
#     config.platform = "kvm"
#     config.proxy = "http://proxy:3128"
#     # ensure ssh_version returns 9
#     monkeypatch.setattr(create_image_mod, "ssh_version", lambda: 9)
#     # also patch OS_DATA
#     monkeypatch.setattr(create_image_mod, "OS_DATA", {"dummy": "data"})
#     # ensure tectonic_resources.files returns FakeFiles so json dumps of machines work (not strictly needed here)
#     monkeypatch.setattr(create_image_mod, "tectonic_resources", SimpleNamespace(files=lambda name: FakeFiles(name)))

#     p = ConcretePacker(config, description, client)
#     vars = p._get_instance_variables(["g1"])

#     assert vars["proxy"] == "http://proxy:3128"
#     assert vars["ansible_scp_extra_args"] == "'-O'"
#     # remove_ansible_logs should be string of not keep_logs -> keep_logs False -> True -> str(True)=="True"
#     assert vars["remove_ansible_logs"] in ("True", "False")
#     # verify machines_json contains the guest
#     machines = json.loads(vars["machines_json"])
#     assert "g1" in machines
#     # OS_DATA present as json
#     assert json.loads(vars["os_data_json"]) == {"dummy": "data"}


# def test_get_instance_variables_ssh_old_or_docker(monkeypatch):
#     config, description, client, _ = make_common_objects()
#     config.platform = "docker"
#     config.proxy = None
#     monkeypatch.setattr(create_image_mod, "ssh_version", lambda: 8)  # <9
#     monkeypatch.setattr(create_image_mod, "OS_DATA", {"x": 1})
#     monkeypatch.setattr(create_image_mod, "tectonic_resources", SimpleNamespace(files=lambda name: FakeFiles(name)))

#     p = ConcretePacker(config, description, client)
#     vars = p._get_instance_variables([])  # empty means include all base guests
#     # docker platform should disable the '-O' extra arg even if ssh_version >= 9 (we have 8 so also off)
#     assert vars["ansible_scp_extra_args"] == ""
#     # proxy absent
#     assert "proxy" not in vars


# def test_get_service_variables_elastic_memory_and_proxy(monkeypatch):
#     # elastic enable True => computes floor(memory / 1000 / 2)
#     config, description, client, _ = make_common_objects()
#     config.platform = "kvm"
#     config.proxy = "http://p"
#     monkeypatch.setattr(create_image_mod, "ssh_version", lambda: 9)
#     monkeypatch.setattr(create_image_mod, "OS_DATA", {"abc": 123})
#     monkeypatch.setattr(create_image_mod, "tectonic_resources", SimpleNamespace(files=lambda name: FakeFiles(name)))

#     p = ConcretePacker(config, description, client)
#     vars = p._get_service_variables(["svc1"])
#     # memory = 4000 => 4000/1000/2 = 2.0 => floor=2
#     assert vars["elasticsearch_memory"] == math.floor(description.elastic.memory / 1000 / 2)
#     assert vars["proxy"] == "http://p"
#     assert vars["elastic_latest_version"] in ("True", "False")
#     # machines_json should include svc1 and its base_os
#     machines = json.loads(vars["machines_json"])
#     assert "svc1" in machines
#     assert "base_os" in machines["svc1"] or "ansible_playbook" in machines["svc1"]


# def test_get_service_variables_elastic_disabled(monkeypatch):
#     # elastic enable False => elastic memory should be None
#     config, description, client, _ = make_common_objects()
#     description.elastic.enable = False
#     monkeypatch.setattr(create_image_mod, "ssh_version", lambda: 9)
#     monkeypatch.setattr(create_image_mod, "OS_DATA", {"abc": 123})
#     monkeypatch.setattr(create_image_mod, "tectonic_resources", SimpleNamespace(files=lambda name: FakeFiles(name)))

#     p = ConcretePacker(config, description, client)
#     vars = p._get_service_variables([])
#     assert vars["elasticsearch_memory"] is None or vars["elasticsearch_memory"] == None


# def test_get_service_machine_variables_returns_paths(monkeypatch):
#     config, description, client, _ = make_common_objects()
#     monkeypatch.setattr(create_image_mod, "tectonic_resources", SimpleNamespace(files=lambda name: FakeFiles(name)))
#     p = ConcretePacker(config, description, client)
#     svc = Guest(base_name="svc1", os="debian")
#     res = p._get_service_machine_variables(svc)
#     # check keys exist and ansible_playbook is string path
#     assert res["base_os"] == "debian"
#     assert isinstance(res["ansible_playbook"], str)
#     assert "services" in res["ansible_playbook"]
#     assert "svc1" in res["ansible_playbook"]
