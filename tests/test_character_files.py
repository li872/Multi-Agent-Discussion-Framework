import pytest

import backend.services.character.file_manager as fm_mod
from backend.services.character.file_manager import SkillFileManager
from backend.services.character.schemas import CharacterCreateRequest
from pydantic import ValidationError


def test_should_reject_empty_character_name():
    with pytest.raises(ValidationError):
        CharacterCreateRequest(name="")


@pytest.mark.asyncio
async def test_should_write_and_read_skill_file(tmp_path, monkeypatch):
    monkeypatch.setattr(fm_mod, "SKILLS_ROOT", tmp_path)
    mgr = SkillFileManager()
    await mgr.create_skill_dir("owner-1", "jobs-perspective")
    await mgr.write_file("owner-1", "jobs-perspective", "SKILL.md", "> stay hungry\n")
    text = await mgr.read_file("owner-1", "jobs-perspective", "SKILL.md")
    assert "stay hungry" in text
    files = await mgr.list_files("owner-1", "jobs-perspective")
    assert "SKILL.md" in files


@pytest.mark.asyncio
async def test_should_deny_path_traversal_on_write(tmp_path, monkeypatch):
    monkeypatch.setattr(fm_mod, "SKILLS_ROOT", tmp_path)
    mgr = SkillFileManager()
    await mgr.create_skill_dir("owner-1", "jobs-perspective")
    with pytest.raises(ValueError, match="Path traversal denied"):
        await mgr.write_file(
            "owner-1",
            "jobs-perspective",
            "../escape.md",
            "nope",
        )
    assert not (tmp_path / "escape.md").exists()
    assert list(tmp_path.rglob("escape.md")) == []


def test_should_extract_blockquote_quotes_from_skill_md():
    from backend.services.character.service import CharacterService

    quotes = CharacterService._extract_quotes(
        "# Title\n> first\nplain\n> second\n> \n> third\n",
        limit=2,
    )
    assert quotes == ["first", "second"]
