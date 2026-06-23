from pathlib import Path
from config import load_config

ROOT = Path(__file__).parent.parent / "skills" / "news-impact"

def test_skill_md_exists_with_frontmatter():
    text = (ROOT / "SKILL.md").read_text()
    assert text.startswith("---")
    assert "name:" in text and "description:" in text

def test_config_example_is_valid():
    cfg = load_config(str(ROOT / "config.example.yaml"))
    assert cfg.model == "ollama:llama3.1:8b"
    assert cfg.sources["yahoo"].enabled is True

def test_reference_docs_exist():
    assert (ROOT / "references" / "symbol-aliases.md").exists()
    assert (ROOT / "references" / "sources.md").exists()
