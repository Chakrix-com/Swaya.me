import React, { useMemo } from 'react';
import CodeMirror from '@uiw/react-codemirror';
import { githubDark } from '@uiw/codemirror-theme-github';
import { python } from '@codemirror/lang-python';
import { java, javaLanguage } from '@codemirror/lang-java';
import { completeFromList } from '@codemirror/autocomplete';
import { cpp, cppLanguage } from '@codemirror/lang-cpp';
import { javascript } from '@codemirror/lang-javascript';
import { go, goLanguage } from '@codemirror/lang-go';
import { rust, rustLanguage } from '@codemirror/lang-rust';
import { useTranslation } from 'react-i18next';

const kwCompletion = (language, words) =>
  language.data.of({
    autocomplete: completeFromList(
      words.map(w => ({ label: w, type: /^[A-Z]/.test(w) || w.includes('.') ? 'class' : 'keyword' }))
    ),
  });

const JAVA_WORDS = [
  'abstract','assert','boolean','break','byte','case','catch','char','class',
  'continue','default','do','double','else','enum','extends','final','finally',
  'float','for','if','implements','import','instanceof','int','interface','long',
  'native','new','package','private','protected','public','return','short',
  'static','strictfp','super','switch','synchronized','this','throw','throws',
  'transient','try','var','void','volatile','while','null','true','false',
  'String','System','Object','Integer','Long','Double','Float','Boolean',
  'Character','Byte','Short','Math','StringBuilder','StringBuffer',
  'ArrayList','LinkedList','HashMap','HashSet','TreeMap','TreeSet',
  'LinkedHashMap','LinkedHashSet','Arrays','Collections','Optional',
  'Stream','List','Map','Set','Queue','Deque','Iterator','Iterable',
  'Comparable','Comparator','Runnable','Thread','Exception',
  'RuntimeException','IOException','NullPointerException',
  'IllegalArgumentException','IllegalStateException',
  'IndexOutOfBoundsException','NumberFormatException',
  'System.out.println','System.err.println',
];

const GO_WORDS = [
  'break','case','chan','const','continue','default','defer','else','fallthrough',
  'for','func','go','goto','if','import','interface','map','package','range',
  'return','select','struct','switch','type','var',
  'bool','byte','complex64','complex128','error','float32','float64',
  'int','int8','int16','int32','int64','rune','string',
  'uint','uint8','uint16','uint32','uint64','uintptr',
  'nil','true','false','iota',
  'append','cap','close','complex','copy','delete','imag','len','make',
  'new','panic','print','println','real','recover',
  'fmt','os','io','http','json','sync','time','errors','math',
  'strings','strconv','bufio','bytes','context','log','sort',
];

const RUST_WORDS = [
  'as','break','const','continue','crate','dyn','else','enum','extern',
  'false','fn','for','if','impl','in','let','loop','match','mod','move',
  'mut','pub','ref','return','self','Self','static','struct','super',
  'trait','true','type','unsafe','use','where','while','async','await',
  'i8','i16','i32','i64','i128','isize','u8','u16','u32','u64','u128',
  'usize','f32','f64','bool','char','str',
  'String','Vec','Option','Result','Box','Rc','Arc','HashMap','HashSet',
  'BTreeMap','BTreeSet','VecDeque','LinkedList',
  'None','Some','Ok','Err',
  'Clone','Copy','Debug','Display','Default','Iterator','IntoIterator',
  'From','Into','AsRef','AsMut','PartialEq','Eq','PartialOrd','Ord',
  'Hash','Send','Sync','Drop','Fn','FnMut','FnOnce',
  'println!','print!','vec!','panic!','assert!','assert_eq!',
  'todo!','unimplemented!','unreachable!','format!','eprintln!',
];

// C++ and C# share cppLanguage — combined keyword set works for both
const CPP_CSHARP_WORDS = [
  // Shared
  'auto','bool','break','case','catch','char','class','const','continue',
  'default','delete','do','double','else','enum','explicit','extern',
  'false','float','for','friend','goto','if','inline','int','long',
  'namespace','new','nullptr','operator','private','protected','public',
  'return','short','signed','sizeof','static','struct','switch','template',
  'this','throw','true','try','typedef','typename','union','unsigned',
  'using','virtual','void','volatile','while',
  // C++ specific
  'alignas','alignof','constexpr','consteval','constinit','decltype',
  'noexcept','reinterpret_cast','static_assert','static_cast','dynamic_cast',
  'const_cast','thread_local','co_await','co_return','co_yield','requires',
  'concept','export','mutable','typeid','wchar_t',
  'std','cout','cin','endl','string','vector','map','set','pair','tuple',
  'unordered_map','unordered_set','list','deque','queue','stack','array',
  'shared_ptr','unique_ptr','weak_ptr','make_shared','make_unique',
  // C# specific
  'abstract','as','base','byte','checked','decimal','delegate','event',
  'fixed','foreach','implicit','in','interface','internal','is','lock',
  'object','out','override','params','readonly','ref','sbyte','sealed',
  'stackalloc','string','typeof','uint','ulong','unchecked','unsafe',
  'ushort','var','async','await','yield','partial','record','init',
  'required','with','when','nameof','dynamic','global',
  'Console','String','Math','List','Dictionary','Array','Exception','Task',
  'Thread','DateTime','StringBuilder','IEnumerable','IList','IDictionary',
  'Action','Func','EventHandler','Nullable','Tuple','ValueTuple',
];

const LANGUAGE_EXTENSIONS = {
  python: python(),
  java: [java(), kwCompletion(javaLanguage, JAVA_WORDS)],
  cpp: [cpp(), kwCompletion(cppLanguage, CPP_CSHARP_WORDS)],
  javascript: javascript(),
  typescript: javascript({ typescript: true }),
  go: [go(), kwCompletion(goLanguage, GO_WORDS)],
  rust: [rust(), kwCompletion(rustLanguage, RUST_WORDS)],
  csharp: [cpp(), kwCompletion(cppLanguage, CPP_CSHARP_WORDS)],
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

  const extensions = useMemo(() => {
    const ext = LANGUAGE_EXTENSIONS[language] || python();
    return Array.isArray(ext) ? ext : [ext];
  }, [language]);

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
          autocompletion: true,
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
