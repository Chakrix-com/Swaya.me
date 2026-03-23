import './RichTextRenderer.css'

/**
 * RichTextRenderer — zero Tiptap dependency.
 * Renders HTML stored by RichTextEditor (or plain text) for participant / presenter views.
 */
export default function RichTextRenderer({ content, isDark = false, className = '', style }) {
  if (!content) return null

  const themeClass = isDark ? 'rte-rendered--dark' : 'rte-rendered--light'

  return (
    <div
      className={`rte-rendered ${themeClass} ${className}`}
      style={style}
      // Content is sanitised by the backend XSS validator before storage
      // eslint-disable-next-line react/no-danger
      dangerouslySetInnerHTML={{ __html: content }}
    />
  )
}
