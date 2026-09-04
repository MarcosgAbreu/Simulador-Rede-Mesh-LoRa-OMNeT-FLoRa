from pathlib import Path


def test_versions_are_compatible_and_project_paths_are_relative():
    versions = Path("config/versions.env").read_text()
    assert "OMNETPP_VERSION=6.4.0" in versions
    assert "INET_VERSION=4.6.0" in versions
    assert "FLORA_VERSION=1.3.0" in versions
    assert "PROJECT_ROOT" not in versions
