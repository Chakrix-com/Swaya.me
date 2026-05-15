import { useEffect, useRef, useState } from 'react'
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight'
import TextAlign from '@tiptap/extension-text-align'
import Link from '@tiptap/extension-link'
import { TextStyle } from '@tiptap/extension-text-style'
import { Color } from '@tiptap/extension-color'
import { Highlight } from '@tiptap/extension-highlight'
import { Subscript } from '@tiptap/extension-subscript'
import { Superscript } from '@tiptap/extension-superscript'
import { Table, TableRow, TableHeader, TableCell } from '@tiptap/extension-table'
import TaskList from '@tiptap/extension-task-list'
import TaskItem from '@tiptap/extension-task-item'
import { createLowlight, common } from 'lowlight'
import { Button, Select, Tooltip, Popover } from 'antd'
import {
  BoldOutlined,
  ItalicOutlined,
  UnderlineOutlined,
  StrikethroughOutlined,
  UnorderedListOutlined,
  OrderedListOutlined,
  CodeOutlined,
  AlignLeftOutlined,
  AlignCenterOutlined,
  AlignRightOutlined,
  MenuOutlined,
  LinkOutlined,
  MinusOutlined,
  TableOutlined,
  CheckSquareOutlined,
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

const COLORS = [
  '#000000', '#434343', '#666666', '#999999', '#b7b7b7', '#cccccc', '#d9d9d9', '#ffffff',
  '#ff0000', '#ff4500', '#ff8c00', '#ffd700', '#008000', '#0000ff', '#4b0082', '#800080',
  '#e74c3c', '#e67e22', '#f1c40f', '#2ecc71', '#3498db', '#9b59b6', '#1abc9c', '#34495e',
]

const HIGHLIGHTS = [
  '#ffd700', '#ff8c00', '#ffb3ba', '#baffc9', '#bae1ff', '#f9c6ff', '#ffe4ba', '#e8e8e8',
]

function ToolbarBtn({ active, onClick, tooltip, children, disabled }) {
  return (
    <Tooltip title={tooltip}>
      <Button
        type="text"
        size="small"
        disabled={disabled}
        className={`rte-toolbar-btn${active ? ' rte-active' : ''}`}
        onMouseDown={(e) => { e.preventDefault(); onClick() }}
      >
        {children}
      </Button>
    </Tooltip>
  )
}

function Divider() {
  return <div className="rte-toolbar-divider" />
}

export default function RichTextEditor({
  value,
  onChange,
  placeholder,
  isDark = false,
  disabled = false,
  showCode = true,
}) {
  const { t } = useTranslation()
  const headingOptions = [
    { value: 0, label: t('richText.normal') },
    { value: 1, label: t('richText.heading1') },
    { value: 2, label: t('richText.heading2') },
    { value: 3, label: t('richText.heading3') },
    { value: 4, label: t('richText.heading4') },
  ]
  const [selectedLang, setSelectedLang] = useState('python')
  const [isEmpty, setIsEmpty] = useState(true)
  const lastEmitted = useRef(value || '')

  const extensions = [
    StarterKit.configure({ codeBlock: false }),
    Underline,
  ]

  if (showCode) {
    extensions.push(
      CodeBlockLowlight.configure({ lowlight }),
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      Link.configure({ openOnClick: false, HTMLAttributes: { rel: 'noopener noreferrer', target: '_blank' } }),
      TextStyle,
      Color,
      Highlight.configure({ multicolor: true }),
      Subscript,
      Superscript,
      Table.configure({ resizable: true }),
      TableRow,
      TableHeader,
      TableCell,
      TaskList,
      TaskItem.configure({ nested: true }),
    )
  }

  const editor = useEditor({
    extensions,
    content: value || '',
    editable: !disabled,
    onUpdate: ({ editor }) => {
      const html = editor.getHTML()
      lastEmitted.current = html
      onChange?.(html)
      setIsEmpty(editor.isEmpty)
    },
    onCreate: ({ editor }) => {
      setIsEmpty(editor.isEmpty)
    },
  })

  useEffect(() => {
    if (!editor) return
    const incoming = value || ''
    if (incoming !== lastEmitted.current) {
      lastEmitted.current = incoming
      editor.commands.setContent(incoming, false)
      setIsEmpty(editor.isEmpty)
    }
  }, [value, editor])

  useEffect(() => {
    if (editor) editor.setEditable(!disabled)
  }, [disabled, editor])

  useEffect(() => {
    if (!editor || !showCode) return
    const update = () => {
      if (editor.isActive('codeBlock')) {
        const attrs = editor.getAttributes('codeBlock')
        if (attrs.language) setSelectedLang(attrs.language)
      }
    }
    editor.on('selectionUpdate', update)
    return () => editor.off('selectionUpdate', update)
  }, [editor, showCode])

  const handleLangChange = (lang) => {
    setSelectedLang(lang)
    if (editor && editor.isActive('codeBlock')) {
      editor.chain().focus().setCodeBlock({ language: lang }).run()
    }
  }

  const setLink = () => {
    const prev = editor.getAttributes('link').href
    const url = window.prompt('URL', prev || 'https://')
    if (url === null) return
    if (url === '') { editor.chain().focus().extendMarkRange('link').unsetLink().run(); return }
    editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run()
  }

  const getHeadingValue = () => {
    for (let i = 1; i <= 4; i++) {
      if (editor.isActive('heading', { level: i })) return i
    }
    return 0
  }

  const setHeading = (val) => {
    if (val === 0) editor.chain().focus().setParagraph().run()
    else editor.chain().focus().setHeading({ level: val }).run()
  }

  if (!editor) return null

  const themeClass = isDark ? 'rte-wrap--dark' : 'rte-wrap--light'

  return (
    <div className={`rte-wrap ${themeClass}`}>
      <div className="rte-toolbar">

        {/* --- Minimal toolbar (feedback) --- */}
        {!showCode && (
          <>
            <ToolbarBtn active={editor.isActive('bold')} tooltip={t('quiz.boldTooltip')} onClick={() => editor.chain().focus().toggleBold().run()}><BoldOutlined /></ToolbarBtn>
            <ToolbarBtn active={editor.isActive('italic')} tooltip={t('quiz.italicTooltip')} onClick={() => editor.chain().focus().toggleItalic().run()}><ItalicOutlined /></ToolbarBtn>
            <ToolbarBtn active={editor.isActive('underline')} tooltip={t('quiz.underlineTooltip')} onClick={() => editor.chain().focus().toggleUnderline().run()}><UnderlineOutlined /></ToolbarBtn>
            <Divider />
            <ToolbarBtn active={editor.isActive('bulletList')} tooltip={t('quiz.bulletListTooltip')} onClick={() => editor.chain().focus().toggleBulletList().run()}><UnorderedListOutlined /></ToolbarBtn>
            <ToolbarBtn active={editor.isActive('orderedList')} tooltip={t('quiz.orderedListTooltip')} onClick={() => editor.chain().focus().toggleOrderedList().run()}><OrderedListOutlined /></ToolbarBtn>
          </>
        )}

        {/* --- Full toolbar (questions) --- */}
        {showCode && (
          <>
            {/* Block type */}
            <Select
              className="rte-heading-select"
              size="small"
              value={getHeadingValue()}
              onChange={setHeading}
              options={headingOptions}
            />

            <Divider />

            {/* Text formatting */}
            <ToolbarBtn active={editor.isActive('bold')} tooltip={t('quiz.boldTooltip')} onClick={() => editor.chain().focus().toggleBold().run()}><BoldOutlined /></ToolbarBtn>
            <ToolbarBtn active={editor.isActive('italic')} tooltip={t('richText.italic')} onClick={() => editor.chain().focus().toggleItalic().run()}><ItalicOutlined /></ToolbarBtn>
            <ToolbarBtn active={editor.isActive('underline')} tooltip={t('richText.underline')} onClick={() => editor.chain().focus().toggleUnderline().run()}><UnderlineOutlined /></ToolbarBtn>
            <ToolbarBtn active={editor.isActive('strike')} tooltip={t('richText.strikethrough')} onClick={() => editor.chain().focus().toggleStrike().run()}><StrikethroughOutlined /></ToolbarBtn>
            <ToolbarBtn active={editor.isActive('code')} tooltip={t('richText.inlineCode')} onClick={() => editor.chain().focus().toggleCode().run()}><CodeOutlined /></ToolbarBtn>

            <Divider />

            {/* Superscript / Subscript */}
            <ToolbarBtn active={editor.isActive('superscript')} tooltip={t('richText.superscript')} onClick={() => editor.chain().focus().toggleSuperscript().run()}><span style={{ fontWeight: 700, fontSize: 11 }}>x²</span></ToolbarBtn>
            <ToolbarBtn active={editor.isActive('subscript')} tooltip={t('richText.subscript')} onClick={() => editor.chain().focus().toggleSubscript().run()}><span style={{ fontWeight: 700, fontSize: 11 }}>x₂</span></ToolbarBtn>

            <Divider />

            {/* Text colour */}
            <Popover
              trigger="click"
              content={
                <div style={{ display: 'flex', flexWrap: 'wrap', width: 160, gap: 4 }}>
                  {COLORS.map((c) => (
                    <div key={c} onClick={() => editor.chain().focus().setColor(c).run()}
                      style={{ width: 18, height: 18, background: c, borderRadius: 3, cursor: 'pointer', border: '1px solid #ccc' }} />
                  ))}
                  <Button size="small" style={{ marginTop: 4, width: '100%' }} onClick={() => editor.chain().focus().unsetColor().run()}>{t('common.clear')}</Button>
                </div>
              }
            >
              <Tooltip title={t('richText.textColour')}>
                <Button type="text" size="small" className="rte-toolbar-btn">
                  <span style={{ fontWeight: 700, borderBottom: `3px solid ${editor.getAttributes('textStyle').color || '#000'}` }}>A</span>
                </Button>
              </Tooltip>
            </Popover>

            {/* Highlight */}
            <Popover
              trigger="click"
              content={
                <div style={{ display: 'flex', flexWrap: 'wrap', width: 160, gap: 4 }}>
                  {HIGHLIGHTS.map((c) => (
                    <div key={c} onClick={() => editor.chain().focus().toggleHighlight({ color: c }).run()}
                      style={{ width: 18, height: 18, background: c, borderRadius: 3, cursor: 'pointer', border: '1px solid #ccc' }} />
                  ))}
                  <Button size="small" style={{ marginTop: 4, width: '100%' }} onClick={() => editor.chain().focus().unsetHighlight().run()}>{t('common.clear')}</Button>
                </div>
              }
            >
              <Tooltip title={t('richText.highlight')}>
                <Button type="text" size="small" className="rte-toolbar-btn">
                  <span style={{ background: '#ffd700', padding: '0 2px', fontWeight: 700 }}>H</span>
                </Button>
              </Tooltip>
            </Popover>

            <Divider />

            {/* Alignment */}
            <ToolbarBtn active={editor.isActive({ textAlign: 'left' })} tooltip={t('richText.alignLeft')} onClick={() => editor.chain().focus().setTextAlign('left').run()}><AlignLeftOutlined /></ToolbarBtn>
            <ToolbarBtn active={editor.isActive({ textAlign: 'center' })} tooltip={t('richText.alignCenter')} onClick={() => editor.chain().focus().setTextAlign('center').run()}><AlignCenterOutlined /></ToolbarBtn>
            <ToolbarBtn active={editor.isActive({ textAlign: 'right' })} tooltip={t('richText.alignRight')} onClick={() => editor.chain().focus().setTextAlign('right').run()}><AlignRightOutlined /></ToolbarBtn>
            <ToolbarBtn active={editor.isActive({ textAlign: 'justify' })} tooltip={t('richText.justify')} onClick={() => editor.chain().focus().setTextAlign('justify').run()}><MenuOutlined /></ToolbarBtn>

            <Divider />

            {/* Lists */}
            <ToolbarBtn active={editor.isActive('bulletList')} tooltip={t('richText.bulletList')} onClick={() => editor.chain().focus().toggleBulletList().run()}><UnorderedListOutlined /></ToolbarBtn>
            <ToolbarBtn active={editor.isActive('orderedList')} tooltip={t('richText.orderedList')} onClick={() => editor.chain().focus().toggleOrderedList().run()}><OrderedListOutlined /></ToolbarBtn>
            <ToolbarBtn active={editor.isActive('taskList')} tooltip={t('richText.taskList')} onClick={() => editor.chain().focus().toggleTaskList().run()}><CheckSquareOutlined /></ToolbarBtn>

            <Divider />

            {/* Blocks */}
            <ToolbarBtn active={editor.isActive('blockquote')} tooltip={t('richText.blockquote')} onClick={() => editor.chain().focus().toggleBlockquote().run()}>
              <span style={{ fontSize: 14, fontWeight: 900, lineHeight: 1 }}>"</span>
            </ToolbarBtn>
            <ToolbarBtn active={false} tooltip={t('richText.horizontalRule')} onClick={() => editor.chain().focus().setHorizontalRule().run()}><MinusOutlined /></ToolbarBtn>

            <Divider />

            {/* Link */}
            <ToolbarBtn active={editor.isActive('link')} tooltip="Link" onClick={setLink}><LinkOutlined /></ToolbarBtn>

            {/* Table */}
            <ToolbarBtn active={editor.isActive('table')} tooltip={t('richText.insertTable')} onClick={() => editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()}><TableOutlined /></ToolbarBtn>

            <Divider />

            {/* Code block */}
            <Select
              className="rte-lang-select"
              size="small"
              value={selectedLang}
              onChange={handleLangChange}
              options={CODE_LANGUAGES}
            />
            <ToolbarBtn active={editor.isActive('codeBlock')} tooltip={t('richText.codeBlock')} onClick={() => editor.chain().focus().setCodeBlock({ language: selectedLang }).run()}><CodeOutlined /></ToolbarBtn>
          </>
        )}
      </div>

      <div className="rte-content" style={{ position: 'relative' }}>
        {isEmpty && placeholder && (
          <div className="rte-placeholder" aria-hidden="true">{placeholder}</div>
        )}
        <EditorContent editor={editor} />
      </div>
    </div>
  )
}
