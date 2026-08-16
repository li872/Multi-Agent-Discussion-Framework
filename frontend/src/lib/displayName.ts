// Skill 目录名常带 -perspective；界面只展示人物名
export function displayName(name: string | null | undefined): string {
  if (!name) return ''
  return name.replace(/-perspective$/i, '')
}
