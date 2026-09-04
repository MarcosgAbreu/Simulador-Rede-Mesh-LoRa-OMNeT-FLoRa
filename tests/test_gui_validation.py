from lora_mesh.gui import fields_to_config, open_in_file_manager


def test_gui_fields_use_seconds_and_defaults():
    config = fields_to_config(
        {
            "nodes": "10",
            "area_m": "1000",
            "activation_min_s": "0",
            "activation_max_s": "3600",
            "simulation_time_s": "14400",
            "seed": "1",
        }
    )
    assert config.node_count == 10
    assert config.simulation_time_s == 14400.0


def test_open_in_file_manager_uses_explorer_on_wsl(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "lora_mesh.gui.shutil.which",
        lambda name: {"wslpath": "/usr/bin/wslpath", "explorer.exe": "/mnt/c/Windows/explorer.exe"}.get(name),
    )
    monkeypatch.setattr(
        "lora_mesh.gui.subprocess.check_output",
        lambda command, text: "C:\\runs\\latest\n",
    )

    def fake_popen(command):
        calls.append(command)
        return None

    monkeypatch.setattr("lora_mesh.gui.subprocess.Popen", fake_popen)
    open_in_file_manager(tmp_path)
    assert calls == [["explorer.exe", "C:\\runs\\latest"]]
