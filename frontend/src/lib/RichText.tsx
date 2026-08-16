import type { ReactNode } from 'react'

// 轻量 Markdown：只处理 **加粗** 和 > 引用，不引入额外依赖、也不用 innerHTML
function renderBold(text: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((part, i) => {
    const m = part.match(/^\*\*([^*]+)\*\*$/)
    if (m) return <strong key={i}>{m[1]}</strong>
    return <span key={i}>{part}</span>
  })
}

export function RichText({ text }: { text: string }) {
  const lines = text.split('\n')
  return (
    <div className="rich-text">
      {lines.map((line, i) => {
        if (line.startsWith('> ')) {
          return (
            <blockquote key={i} className="quote">
              {renderBold(line.slice(2))}
            </blockquote>
          )
        }
        return <p key={i}>{renderBold(line)}</p>
      })}
    </div>
  )
}
