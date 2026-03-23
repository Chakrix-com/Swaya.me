import { useEffect, useRef, useState } from 'react'
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight'
import Placeholder from '@tiptap/extension-placeholder'
import { createLowlight, common } from 'lowlight'
import { Button, Select, Tooltip } from 'antd'
import {
  BoldOutlined,
  ItalicOutlined,
  UnderlineOutlined,
  UnorderedListOutlined,
  OrderedListOutlined,
  CodeOutlined,
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import './RichTextEditor.css'

const lowlight = createLowlight(common)

const CODE_LANGUAGES = [
  { value: 'python',     label: 'Python' },
  { value: 'java',       label: 'Java' },
  { value: 'c',          label: 'C' },
  { value: 'cpp',        label: 'C++' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'typescript', label: 'TypeScript' },
  { value: 'shell',      label: 'Shell/Bash' },
  { value: 'go',         label: 'Go' },
  { value: 'rust',       label: 'Rust' },
  { value: 'sql',        label: 'SQL' },
  { value: 'xml',        label: 'HTML' },
  { value: 'css',        label: 'CSS' },
]

export default function RichTextEditor({
  value,
  onChange,
  placeholder,
  isDark = false,
  disabled = false,
}) {
  const { t } = useTranslation()
  const [selectedLang, setSelectedLang] = useState('python')
  const lastEmitted = useRef(value || '')

  const editor = useEditor({
    extensions: [
      StarterKit.configure({ codeBlock: false }),
      Underline,
      CodeBlockLowlight.configure({ lowlight }),
      Placeholder.configure({ placeholder: placeholder || '' }),
    ],
    content: value || '',
    editable: !disabled,
    onUpdate: ({ editor }) => {
      const html = editor.getHTML()
      lastEmitted.current = html
      onChange?.(html)
    },
  })

  // Sync external value changes (e.g. AI rewrite) into editor
  useEffect(() => {
    if (!editor) return
    const incoming = value || ''
    if (incoming !== lastEmitted.current) {
      lastEmitted.current = incoming
      editor.commands.setContent(incoming, false)
    }
  }, [value, editor])

  // Update editable state
  useEffect(() => {
    if (editor) editor.setEditable(!disabled)
  }, [disabled, editor])

  // Track current code block language from cursor position
  useEffect(() => {
    if (!editor) return
    const update = () => {
      if (editor.isActive('codeBlock')) {
        const attrs = editor.getAttributes('codeBlock')
        if (attrs.language) setSelectedLang(attrs.language)
      }
    }
    editor.on('selectionUpdate', update)
    return () => editor.off('selectionUpdate', update)
  }, [editor])

  const handleLangChange = (lang) => {
    setSelectedLang(lang)
    if (editor && editor.isActive('codeBlock')) {
      editor.chain().focus().setCodeBlock({ language: lang }).run()
    }
  }

  const insertCodeBlock = () => {
    editor?.chain().focus().setCodeBlock({ language: selectedLang }).run()
  }

  if (!editor) return null

  const themeClass = isDark ? 'rte-wrap--dark' : 'rte-wrap--light'

  return (
    <div className={`rte-wrap ${themeClass}`}>
      <div className="rte-toolbar">
        <Tooltip title={t('quiz.boldTooltip')}>
          <Button
            type="text"
            size="small"
            className={`rte-toolbar-btn${editor.isActive('bold') ? ' rte-active' : ''}`}
            onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().toggleBold().run() }}
            aria-label={t('quiz.boldTooltip')}
          >
            <BoldOutlined />
          </Button>
        </Tooltip>

        <Tooltip title={t('quiz.italicTooltip')}>
          <Button
            type="text"
            size="small"
            className={`rte-toolbar-btn${editor.isActive('italic') ? ' rte-active' : ''}`}
            onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().toggleItalic().run() }}
            aria-label={t('quiz.italicTooltip')}
          >
            <ItalicOutlined />
          </Button>
        </Tooltip>

        <Tooltip title={t('quiz.underlineTooltip')}>
          <Button
            type="text"
            size="small"
            className={`rte-toolbar-btn${editor.isActive('underline') ? ' rte-active' : ''}`}
            onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().toggleUnderline().run() }}

            aria-label={t('quiz.underlineTooltip')}
          >
            <UnderlineOutlined />
          </Button>
        </Tooltip>

        <div className="rte-toolbar-divider" />

        <Tooltip title={t('quiz.bulletListTooltip')}>
          <Button
            type="text"
            size="small"
            className={`rte-toolbar-btn${editor.isActive('bulletList') ? ' rte-active' : ''}`}
            onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().toggleBulletList().run() }}
            aria-label={t('quiz.bulletListTooltip')}
          >
            <UnorderedListOutlined />
          </Button>
        </Tooltip>

        <Tooltip title={t('quiz.orderedListTooltip')}>
          <Button
            type="text"
            size="small"
            className={`rte-toolbar-btn${editor.isActive('orderedList') ? ' rte-active' : ''}`}
            onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().toggleOrderedList().run() }}
            aria-label={t('quiz.orderedListTooltip')}
          >
            <OrderedListOutlined />
          </Button>
        </Tooltip>

        <div className="rte-toolbar-divider" />

        <Select
          className="rte-lang-select"
          size="small"
          value={selectedLang}
          onChange={handleLangChange}
          options={CODE_LANGUAGES}
          aria-label={t('quiz.codeLanguageSelect')}
        />

        <Tooltip title={t('quiz.codeBlockTooltip')}>
          <Button
            type="text"
            size="small"
            className={`rte-toolbar-btn${editor.isActive('codeBlock') ? ' rte-active' : ''}`}
            onMouseDown={(e) => { e.preventDefault(); insertCodeBlock() }}
            aria-label={t('quiz.codeBlockTooltip')}
          >
            <CodeOutlined />
          </Button>
        </Tooltip>
      </div>

      <div className="rte-content">
        <EditorContent editor={editor} />
      </div>
    </div>
  )
}
