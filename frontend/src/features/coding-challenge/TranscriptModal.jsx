import { useMemo, useState } from 'react'
import { Button, Tag } from 'antd'
import SafeModal from '../../components/SafeModal'

// Claude Code's own session transcript format (~/.claude/projects/*/*.jsonl) —
// one JSON object per line. Explicitly not a documented/stable API (per the
// backend comment where this is captured), so parsing here is defensive:
// anything we don't recognize renders as a labeled, expandable raw-JSON block
// rather than being silently dropped or crashing the view.
function parseTranscript(raw) {
  const entries = []
  let skipped = 0
  for (const line of (raw || '').split('\n')) {
    const trimmed = line.trim()
    if (!trimmed) continue
    try {
      entries.push(JSON.parse(trimmed))
    } catch {
      skipped++
    }
  }
  return { entries, skipped }
}

function ExpandableJson({ label, data, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div style={{ marginTop: 4 }}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        style={{
          fontSize: 11, fontWeight: 600, color: 'var(--sw-text3, #888)', background: 'none',
          border: 'none', cursor: 'pointer', padding: '2px 0', display: 'inline-flex', alignItems: 'center', gap: 4,
        }}
      >
        {open ? '▾' : '▸'} {label}
      </button>
      {open && (
        <pre style={{
          fontSize: 11, fontFamily: 'monospace', background: 'var(--sw-surface, #f5f5f5)',
          border: '1px solid var(--sw-border, #e5e7eb)', borderRadius: 6, padding: 8,
          whiteSpace: 'pre-wrap', wordBreak: 'break-all', maxHeight: 300, overflowY: 'auto', margin: 0,
        }}>
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  )
}

function Bubble({ roleLabel, accent, children }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-start' }}>
      <span style={{ fontSize: 11, fontWeight: 700, color: accent }}>{roleLabel}</span>
      <div style={{
        maxWidth: '85%', padding: '8px 12px', borderRadius: 10, fontSize: 13, lineHeight: 1.5,
        background: `color-mix(in srgb, ${accent} 8%, transparent)`,
        border: `1px solid color-mix(in srgb, ${accent} 25%, transparent)`,
      }}>
        {children}
      </div>
    </div>
  )
}

function ContentBlocks({ blocks, accent, t }) {
  if (typeof blocks === 'string') return <span style={{ whiteSpace: 'pre-wrap' }}>{blocks}</span>
  if (!Array.isArray(blocks)) return <ExpandableJson label={t('codingChallenge.rawEntry', 'Raw entry')} data={blocks} />

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {blocks.map((block, i) => {
        if (!block || typeof block !== 'object') return <span key={i}>{String(block)}</span>
        if (block.type === 'text') {
          return <span key={i} style={{ whiteSpace: 'pre-wrap' }}>{block.text}</span>
        }
        if (block.type === 'thinking') {
          return (
            <div key={i} style={{ fontStyle: 'italic', color: 'var(--sw-text3, #888)' }}>
              <ExpandableJson label={`🤔 ${t('codingChallenge.thinking', 'Thinking')}`} data={block.thinking} />
            </div>
          )
        }
        if (block.type === 'tool_use') {
          return (
            <div key={i}>
              <Tag color="blue">🔧 {t('codingChallenge.calledTool', 'Used tool')}: {block.name}</Tag>
              <ExpandableJson label={t('codingChallenge.toolInput', 'Tool input')} data={block.input} />
            </div>
          )
        }
        if (block.type === 'tool_result') {
          return (
            <div key={i}>
              <Tag color={block.is_error ? 'error' : 'default'}>
                {block.is_error ? '⚠' : '✓'} {t('codingChallenge.toolResult', 'Tool result')}
              </Tag>
              <ExpandableJson label={t('codingChallenge.viewResult', 'View result')} data={block.content ?? block} />
            </div>
          )
        }
        return <ExpandableJson key={i} label={t('codingChallenge.unrecognizedBlock', 'Unrecognized entry ({{type}})', { type: block.type || 'unknown' })} data={block} />
      })}
    </div>
  )
}

export default function TranscriptModal({ open, onClose, rawTranscript, tokenUsage, t }) {
  const [view, setView] = useState('conversation')
  const { entries, skipped } = useMemo(() => parseTranscript(rawTranscript), [rawTranscript])

  return (
    <SafeModal
      title={t('codingChallenge.aiTranscript', 'AI Chat Transcript')}
      open={open}
      onCancel={onClose}
      width={800}
      footer={null}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
        <div style={{ display: 'flex', gap: 6 }}>
          {tokenUsage && (
            <>
              <Tag>{t('codingChallenge.inputTokens', 'input')}: {tokenUsage.input_tokens || 0}</Tag>
              <Tag>{t('codingChallenge.outputTokens', 'output')}: {tokenUsage.output_tokens || 0}</Tag>
              <Tag>{t('codingChallenge.turns', 'turns')}: {tokenUsage.turns || 0}</Tag>
            </>
          )}
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          <Button size="small" type={view === 'conversation' ? 'primary' : 'default'} onClick={() => setView('conversation')}>
            {t('codingChallenge.conversationView', 'Conversation')}
          </Button>
          <Button size="small" type={view === 'raw' ? 'primary' : 'default'} onClick={() => setView('raw')}>
            {t('codingChallenge.rawJsonView', 'Raw JSON')}
          </Button>
        </div>
      </div>

      <div style={{ maxHeight: '65vh', overflowY: 'auto' }}>
        {entries.length === 0 ? (
          <span style={{ color: 'var(--sw-text3, #888)' }}>{t('codingChallenge.noTranscript', 'No transcript available.')}</span>
        ) : view === 'raw' ? (
          <>
            {skipped > 0 && (
              <div style={{ fontSize: 12, color: 'var(--sw-warning, #d97706)', marginBottom: 8 }}>
                {t('codingChallenge.linesSkipped', '{{count}} line(s) could not be parsed and are omitted below.', { count: skipped })}
              </div>
            )}
            <pre style={{
              fontSize: 12, fontFamily: 'monospace', whiteSpace: 'pre-wrap', wordBreak: 'break-all',
              background: 'var(--sw-surface, #fafafa)', border: '1px solid var(--sw-border, #e5e7eb)',
              borderRadius: 8, padding: 12, margin: 0,
            }}>
              {JSON.stringify(entries, null, 2)}
            </pre>
          </>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {entries.map((entry, i) => {
              const role = entry?.message?.role || entry?.role
              const content = entry?.message?.content ?? entry?.content
              if (!role || content == null) {
                return (
                  <ExpandableJson
                    key={i}
                    label={t('codingChallenge.unrecognizedEntry', 'Unrecognized entry ({{type}})', { type: entry?.type || 'unknown' })}
                    data={entry}
                  />
                )
              }
              const isCandidate = role === 'user'
              return (
                <Bubble
                  key={i}
                  roleLabel={isCandidate ? t('codingChallenge.candidateRole', 'Candidate') : t('codingChallenge.aiRole', 'AI Assistant')}
                  accent={isCandidate ? 'var(--sw-primary, #6366f1)' : 'var(--sw-info, #3b82f6)'}
                >
                  <ContentBlocks blocks={content} accent={isCandidate ? 'var(--sw-primary, #6366f1)' : 'var(--sw-info, #3b82f6)'} t={t} />
                </Bubble>
              )
            })}
          </div>
        )}
      </div>
    </SafeModal>
  )
}
