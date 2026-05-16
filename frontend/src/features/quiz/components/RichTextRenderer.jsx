import { useEffect, useRef } from 'react'
import { createLowlight, common } from 'lowlight'
import './RichTextRenderer.css'

const lowlight = createLowlight(common)

/**
 * Convert a lowlight hast tree to HTML string (no external dep needed).
 */
function hastToHtml(node) {
  if (!node) return ''
  if (node.type === 'text') {
    return node.value
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
  }
  if (node.type === 'element') {
    const cls = (node.properties?.className || []).join(' ')
    const open = cls ? `<span class="${cls}">` : '<span>'
    return open + (node.children || []).map(hastToHtml).join('') + '</span>'
  }
  return (node.children || []).map(hastToHtml).join('')
}

/**
 * RichTextRenderer — zero Tiptap dependency.
 * Renders HTML stored by RichTextEditor (or plain text / Gemini-converted HTML)
 * for participant / presenter views. Applies syntax highlighting to any
 * <pre><code class="language-*"> blocks that haven't been highlighted yet.
 */
export default function RichTextRenderer({ content, isDark = false, className = '', style }) {
  const ref = useRef(null)

  useEffect(() => {
    if (!ref.current) return
    const blocks = ref.current.querySelectorAll('pre code')
    blocks.forEach(block => {
      // Skip blocks already processed by Tiptap/lowlight (they have hljs spans)
      if (block.querySelector('span')) return
      const langMatch = block.className.match(/language-([\w-]+)/)
      const lang = langMatch?.[1]
      const rawCode = block.textContent || ''
      try {
        const tree = lang && lowlight.registered(lang)
          ? lowlight.highlight(lang, rawCode)
          : lowlight.highlightAuto(rawCode)
        block.innerHTML = (tree.children || []).map(hastToHtml).join('')
      } catch {
        // leave unstyled if highlighting fails
      }
    })
  }, [content])

  if (!content) return null

  const themeClass = isDark ? 'rte-rendered--dark' : 'rte-rendered--light'

  return (
    <div
      ref={ref}
      className={`rte-rendered ${themeClass} ${className}`}
      style={style}
      // Content is sanitised by the backend XSS validator before storage
      // eslint-disable-next-line react/no-danger
      dangerouslySetInnerHTML={{ __html: content }}
    />
  )
}
