from lora_mesh.runner import run_command


def test_run_command_preserves_output_and_exit_code(tmp_path):
    result = run_command(
        ["python3", "-c", "print('simulation-ok')"],
        cwd=tmp_path,
        log_path=tmp_path / "run.log",
    )
    assert result.returncode == 0
    assert "simulation-ok" in (tmp_path / "run.log").read_text()
