from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_metadata_matches_custom_license_and_canonical_remote():
    metadata = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert 'license = "LicenseRef-Ethernium-Sym"' in metadata
    assert 'license-files = ["LICENSE.txt"]' in metadata
    assert "https://github.com/NullaLabs/FONTS-FORGE-by-Ethernium" in metadata
    assert (ROOT / "LICENSE.txt").is_file()


def test_public_readme_contains_no_machine_local_links():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "file:///" not in readme


def test_assembler_cannot_publish_or_rewrite_git_history():
    assembler = (ROOT / "tools" / "assemble_clean_repo.py").read_text(
        encoding="utf-8"
    )

    assert "git push" not in assembler
    assert "push --force" not in assembler
    assert "subprocess" not in assembler
