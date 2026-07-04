import React, { useMemo } from 'react';
import CodeMirror from '@uiw/react-codemirror';
import { githubDark } from '@uiw/codemirror-theme-github';
import { python } from '@codemirror/lang-python';
import { java } from '@codemirror/lang-java';
import { cpp } from '@codemirror/lang-cpp';
import { javascript } from '@codemirror/lang-javascript';
import { go } from '@codemirror/lang-go';
import { rust } from '@codemirror/lang-rust';
import { useTranslation } from 'react-i18next';

const LANGUAGE_EXTENSIONS = {
  python: python(),
  java: java(),
  cpp: cpp(),
  javascript: javascript(),
  typescript: javascript({ typescript: true }),
  go: go(),
  rust: rust(),
  csharp: cpp(),
};

const LANGUAGE_LABELS = {
  python: 'Python',
  java: 'Java',
  cpp: 'C++',
  javascript: 'JavaScript',
  typescript: 'TypeScript',
  go: 'Go',
  rust: 'Rust',
  csharp: 'C#',
};

const VERDICT_STYLES = {
  AC:  { background: '#52c41a', color: '#fff', label: 'AC' },
  WA:  { background: '#ff4d4f', color: '#fff', label: 'WA' },
  PE:  { background: '#fa8c16', color: '#fff', label: 'PE' },
  RE:  { background: '#722ed1', color: '#fff', label: 'RE' },
  CE:  { background: '#8c8c8c', color: '#fff', label: 'CE' },
  TLE: { background: '#1677ff', color: '#fff', label: 'TLE' },
};

export default function CodeEditor({
  code = '',
  language = 'python',
  allowedLanguages = ['python'],
  onChange,
  onLanguageChange,
  readOnly = false,
  isDark = false,
  verdict = null,
  aiFeedback = null,
}) {
  const { t } = useTranslation();

  const extensions = useMemo(
    () => [LANGUAGE_EXTENSIONS[language] || python()],
    [language]
  );

  // Always use a dark theme for the code editor — better contrast and IDE feel
  const editorTheme = githubDark;

  const verdictStyle = verdict ? VERDICT_STYLES[verdict] : null;
  const toolbarBg = '#21262d';
  const borderColor = '#30363d';

  return (
    <div style={{
      border: `2px solid ${borderColor}`,
      borderRadius: 8,
      overflow: 'hidden',
      boxShadow: '0 1px 6px rgba(0,0,0,0.10)',
    }}>
      {/* Toolbar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '6px 12px',
        background: toolbarBg,
        borderBottom: `1px solid ${borderColor}`,
      }}>
        <span style={{ fontSize: 12, color: '#8b949e', flexShrink: 0, fontWeight: 500 }}>
          {t('codeEditor.language', 'Language')}:
        </span>

        {readOnly ? (
          <span style={{
            fontSize: 12,
            fontWeight: 600,
            color: '#e6edf3',
            background: '#30363d',
            padding: '2px 10px',
            borderRadius: 4,
          }}>
            {LANGUAGE_LABELS[language] || language}
          </span>
        ) : (
          <select
            value={language}
            onChange={(e) => onLanguageChange && onLanguageChange(e.target.value)}
            style={{
              fontSize: 13,
              padding: '3px 8px',
              borderRadius: 4,
              border: '1px solid #444d56',
              background: '#161b22',
              color: '#e6edf3',
              cursor: 'pointer',
              fontWeight: 500,
            }}
          >
            {allowedLanguages.map((lang) => (
              <option key={lang} value={lang}>
                {LANGUAGE_LABELS[lang] || lang}
              </option>
            ))}
          </select>
        )}

        <div style={{ flex: 1 }} />

        {verdictStyle && (
          <span style={{
            fontSize: 12,
            fontWeight: 700,
            background: verdictStyle.background,
            color: verdictStyle.color,
            padding: '2px 10px',
            borderRadius: 4,
            letterSpacing: 1,
          }}>
            {verdictStyle.label}
          </span>
        )}
      </div>

      {/* Editor */}
      <CodeMirror
        value={code}
        height="300px"
        theme={editorTheme}
        extensions={extensions}
        readOnly={readOnly}
        onChange={(val) => onChange && onChange(val)}
        basicSetup={{
          lineNumbers: true,
          foldGutter: false,
          dropCursor: false,
          allowMultipleSelections: false,
          indentOnInput: true,
          bracketMatching: true,
          closeBrackets: true,
          autocompletion: false,
          highlightSelectionMatches: false,
        }}
      />

      {/* AI Feedback panel */}
      {aiFeedback && (
        <div style={{
          padding: '8px 12px',
          background: '#161b22',
          borderTop: `1px solid ${borderColor}`,
          fontFamily: 'monospace',
          fontSize: 12,
          color: '#8b949e',
          whiteSpace: 'pre-wrap',
          maxHeight: 120,
          overflowY: 'auto',
        }}>
          {aiFeedback}
        </div>
      )}
    </div>
  );
}
