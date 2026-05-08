from pathlib import Path


def test_readme_exists() -> None:
    assert Path("README.md").exists()
