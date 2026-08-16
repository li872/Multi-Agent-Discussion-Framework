# 读写 skills：目录以 PG 的 file_path 为准（通常 {owner_id}/{skill-name}）
import asyncio
import os
import shutil
from pathlib import Path

SKILLS_ROOT = Path(
    os.getenv("SKILLS_ROOT", str(Path(__file__).parent.parent.parent.parent / "skills"))
)


class SkillFileManager:
    def _ensure_within(self, path: Path, root: Path, label: str) -> None:
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"Path traversal denied: {label}") from exc

    def skill_dir(self, file_path: str) -> Path:
        if not file_path or file_path.startswith("/") or file_path.startswith("\\"):
            raise ValueError("Path traversal denied: file_path")
        root = SKILLS_ROOT.resolve()
        full = (root / file_path).resolve()
        self._ensure_within(full, root, file_path)
        return full

    def _resolve_child(self, skill_dir: Path, rel_path: str) -> Path:
        full_path = (skill_dir / rel_path).resolve()
        self._ensure_within(full_path, skill_dir.resolve(), rel_path)
        return full_path

    def _ensure_dir(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)

    async def create_skill_dir(self, file_path: str) -> Path:
        skill_dir = self.skill_dir(file_path)
        refs_dir = skill_dir / "references" / "research"
        await asyncio.to_thread(self._ensure_dir, refs_dir)
        return skill_dir

    async def write_file(self, file_path: str, rel_path: str, content: str) -> Path:
        skill_dir = self.skill_dir(file_path)
        full_path = self._resolve_child(skill_dir, rel_path)
        await asyncio.to_thread(self._ensure_dir, full_path.parent)
        await asyncio.to_thread(full_path.write_text, content, encoding="utf-8")
        return full_path

    async def read_file(self, file_path: str, rel_path: str) -> str:
        skill_dir = self.skill_dir(file_path)
        if not skill_dir.exists():
            raise FileNotFoundError(f"Skill files missing on disk: {file_path}")
        full_path = self._resolve_child(skill_dir, rel_path)
        if not full_path.exists() or not full_path.is_file():
            raise FileNotFoundError(f"Skill files missing on disk: {file_path}")
        return await asyncio.to_thread(full_path.read_text, encoding="utf-8")

    async def list_files(self, file_path: str) -> list[str]:
        skill_dir = self.skill_dir(file_path)
        if not skill_dir.exists():
            raise FileNotFoundError(f"Skill files missing on disk: {file_path}")

        def _list() -> list[str]:
            files: list[str] = []
            for root, _dirs, filenames in os.walk(skill_dir):
                for f in filenames:
                    abs_path = os.path.join(root, f)
                    rel = os.path.relpath(abs_path, skill_dir)
                    files.append(rel.replace("\\", "/"))
            return sorted(files)

        return await asyncio.to_thread(_list)

    async def delete_skill_dir(self, file_path: str) -> None:
        skill_dir = self.skill_dir(file_path)
        if skill_dir.exists():
            await asyncio.to_thread(shutil.rmtree, str(skill_dir))

    async def copy_skill_dir(self, src_file_path: str, dst_file_path: str) -> None:
        src = self.skill_dir(src_file_path)
        dst = self.skill_dir(dst_file_path)
        if not src.exists():
            raise FileNotFoundError(f"Skill files missing on disk: {src_file_path}")
        await asyncio.to_thread(shutil.copytree, src, dst)
