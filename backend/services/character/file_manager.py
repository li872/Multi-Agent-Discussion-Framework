# 读写 skills
# 在项目根目录 skills/{用户id}/{角色名}/ 下建目录、读写文件，并防止 ../ 路径穿越。
import asyncio
import os
import shutil
from pathlib import Path

SKILLS_ROOT = Path(
    os.getenv("SKILLS_ROOT", str(Path(__file__).parent.parent.parent.parent / "skills"))
)


class SkillFileManager:
    def _skill_dir(self, owner_id: str, skill_name: str) -> Path:
        return SKILLS_ROOT / owner_id / skill_name

    def _ensure_within(self, path: Path, root: Path, label: str) -> None:
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"Path traversal denied: {label}") from exc

    def _resolve_child(self, root: Path, rel_path: str) -> Path:
        full_path = (root / rel_path).resolve()
        self._ensure_within(full_path, root.resolve(), rel_path)
        return full_path

    def _ensure_dir(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)

    async def create_skill_dir(self, owner_id: str, skill_name: str) -> Path:
        skill_dir = self._skill_dir(owner_id, skill_name)
        refs_dir = skill_dir / "references" / "research"
        await asyncio.to_thread(self._ensure_dir, refs_dir)
        return skill_dir

    async def write_file(
        self, owner_id: str, skill_name: str, rel_path: str, content: str
    ) -> Path:
        skill_dir = self._skill_dir(owner_id, skill_name)
        full_path = self._resolve_child(skill_dir, rel_path)
        await asyncio.to_thread(self._ensure_dir, full_path.parent)
        await asyncio.to_thread(full_path.write_text, content, encoding="utf-8")
        return full_path

    async def read_file(self, owner_id: str, skill_name: str, rel_path: str) -> str:
        skill_dir = self._skill_dir(owner_id, skill_name)
        full_path = self._resolve_child(skill_dir, rel_path)
        return await asyncio.to_thread(full_path.read_text, encoding="utf-8")

    async def list_files(self, owner_id: str, skill_name: str) -> list[str]:
        skill_dir = self._skill_dir(owner_id, skill_name)
        if not skill_dir.exists():
            return []

        def _list() -> list[str]:
            files: list[str] = []
            for root, _dirs, filenames in os.walk(skill_dir):
                for f in filenames:
                    abs_path = os.path.join(root, f)
                    rel = os.path.relpath(abs_path, skill_dir)
                    files.append(rel.replace("\\", "/"))
            return sorted(files)

        return await asyncio.to_thread(_list)

    async def delete_skill_dir(self, owner_id: str, skill_name: str) -> None:
        skill_dir = self._skill_dir(owner_id, skill_name)
        if skill_dir.exists():
            await asyncio.to_thread(shutil.rmtree, str(skill_dir))