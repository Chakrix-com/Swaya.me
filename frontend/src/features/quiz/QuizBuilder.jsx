import { useState, useEffect, useCallback, memo, useContext, useRef, useMemo } from 'react'
import { DndContext, closestCenter, PointerSensor, KeyboardSensor, useSensor, useSensors } from '@dnd-kit/core'
import { arrayMove, SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy, useSortable } from '@dnd-kit/sortable'
import { CSS as DndCSS } from '@dnd-kit/utilities'
import { useNavigate, useParams, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ProCard } from '@ant-design/pro-components'
import {
  App,
  Card,
  Form,
  Input,
  InputNumber,
  Button,
  Space,
  List,
  Radio,
  Popconfirm,
  Typography,
  Divider,
  Tag,
  Table,
  Upload,
  Tabs,
  theme,
} from 'antd'
import {
  PlusOutlined,
  DeleteOutlined,
  SaveOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  RocketOutlined,
  LeftOutlined,
  RightOutlined,
  EditOutlined,
  CloseOutlined,
  MinusCircleOutlined,
  ThunderboltOutlined,
  BulbOutlined,
  LoadingOutlined,
  HolderOutlined,
  FolderFilled,
  FileTextOutlined,
} from '@ant-design/icons'
import {
  Modal,
  Checkbox,
  Select,
  Spin,
  Alert,
  Tooltip,
  Popover,
  DatePicker,
  Switch,
  message as antMessage,
} from 'antd'
import { CopyOutlined, ShareAltOutlined, DownloadOutlined, InboxOutlined, CheckCircleOutlined, ExclamationCircleOutlined, FontColorsOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { quizAPI, questionAPI, aiAPI, examAPI } from '../../services/api'
import ImageUpload from './components/ImageUpload'
import VideoEmbed, { getVideoEmbedUrl } from './components/VideoEmbed'
import RichTextEditor from './components/RichTextEditor'
import RichTextRenderer from './components/RichTextRenderer'
import { VisitorThemeContext } from '../../App'
import './QuizBuilder.css'
import { ProctoringSettings } from './components/ProctoringSettings'
import { skins } from '../../themes/skins'

const { Title, Text } = Typography
const { TextArea } = Input
const getQuestionTypeLabel = (type, t) => {
  const labels = {
    mcq: t('quiz.multipleChoice'),
    word_cloud: t('quiz.wordCloud'),
    single_line: t('quiz.singleLine'),
    scale: t('quizPresent.scaleOneToFive'),
    paragraph: t('quiz.paragraph'),
    one_word: t('quiz.oneWord'),
  }
  return labels[type] || t('quiz.multipleChoice')
}

const stripHtml = (h) => (h || '').replace(/<[^>]*>/g, '').trim()

// Stable sortable wrapper — must live outside questions.map so React sees a consistent
// component type across re-renders (avoids unmount/remount of children on every parent render).
const SortableItem = ({ id, disabled, children, marginBottom = 16 }) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id, disabled })
  const style = { transform: DndCSS.Transform.toString(transform), transition, opacity: isDragging ? 0.5 : 1, marginBottom }
  return (
    <div ref={setNodeRef} style={style} {...attributes}>
      {children({ dragHandleProps: listeners })}
    </div>
  )
}

// QuestionForm component - extracted to prevent recreation on parent re-renders
const QuestionForm = ({
  question,
  onSave,
  onCancel,
  onAutoSave,
  onNavigate,
  questionIndex,
  totalQuestions,
  quizId,
  questionImageUrl,
  setQuestionImageUrl,
  optionImages,
  setOptionImages,
  tempImages,
  setTempImages,
  loading,
  movingImages,
  isPoll,
  isExam,
  isOfflinePoll,
  language,
  isAdmin,
  t
}) => {
  const { message } = App.useApp()
  const [questionForm] = Form.useForm()
  const [questionType, setQuestionType] = useState('mcq')
  const [mcqBaseOptionCount, setMcqBaseOptionCount] = useState(2)
  const [aiSuggestOpen, setAiSuggestOpen] = useState(false)
  const [aiSuggestTopic, setAiSuggestTopic] = useState('')
  const [aiSuggesting, setAiSuggesting] = useState(false)
  const [rewriting, setRewriting] = useState({})
  const [useRichText, setUseRichText] = useState(false)
  const [typeChipsExpanded, setTypeChipsExpanded] = useState(true)
  const [explanationOpen, setExplanationOpen] = useState(false)
  const [mediaVideoOpen, setMediaVideoOpen] = useState(false)
  const [selectedAnswer, setSelectedAnswer] = useState('0')
  const [useRichTextOptions, setUseRichTextOptions] = useState({ option_a: false, option_b: false, option_c: false, option_d: false })
  const [extraRichOpts, setExtraRichOpts] = useState([])
  const [questionVideoUrl, setQuestionVideoUrl] = useState(null)
  const { theme } = useContext(VisitorThemeContext)

  const watchedPoints = Form.useWatch('points', questionForm)
  const watchedNegPoints = Form.useWatch('negative_points', questionForm)
  const watchedMaxTime = Form.useWatch('max_time_seconds', questionForm)

  const toggleOptRich = (key) => {
    setUseRichTextOptions((prev) => {
      const next = !prev[key]
      if (!next) {
        // Switching to plain — strip HTML from that field
        const v = questionForm.getFieldValue(key)
        if (v) questionForm.setFieldsValue({ [key]: stripHtml(v) })
      }
      return { ...prev, [key]: next }
    })
  }

  const toggleExtraOptRich = (index) => {
    setExtraRichOpts((prev) => {
      const next = [...prev]
      const wasRich = !!next[index]
      if (wasRich) {
        const extras = questionForm.getFieldValue('extra_options') || []
        const v = extras[index]
        if (v) {
          const updated = [...extras]
          updated[index] = stripHtml(v)
          questionForm.setFieldsValue({ extra_options: updated })
        }
      }
      next[index] = !wasRich
      return next
    })
  }

  // Debug: Log when component renders
  console.log('[QuestionForm] Rendering. Question ID:', question?.id || 'NEW')

  useEffect(() => {
    console.log('[QuestionForm] useEffect triggered')
    if (question) {
      const formValues = {
        ...question,
        points: question.points ?? 1,
        max_time_seconds: question.max_time_seconds ?? null,
        negative_points: question.negative_points ?? 0,
        is_required: question.is_required ?? false,
        answer_explanation: question.answer_explanation ?? '',
      }
      if (question.question_type === 'mcq') {
        const existingOptionCount = question.options?.length || 2
        setMcqBaseOptionCount(Math.min(4, Math.max(2, existingOptionCount)))
        formValues.option_a = question.options?.[0] || ''
        formValues.option_b = question.options?.[1] || ''
        formValues.option_c = question.options?.[2] || ''
        formValues.option_d = question.options?.[3] || ''
        formValues.extra_options = question.options?.slice(4) || []
        formValues.correct_answer = isPoll ? undefined : String(question.correct_answer_index ?? 0)
      }
      questionForm.setFieldsValue(formValues)
      setQuestionType(question.question_type || 'mcq')
      setTypeChipsExpanded(!question.text)
      setExplanationOpen(!!question.answer_explanation)
      setMediaVideoOpen(!!question.question_video_url)
      setSelectedAnswer(isPoll ? '-1' : String(question.correct_answer_index ?? 0))

      // Auto-detect rich text: if question text contains HTML tags open in rich text mode
      setUseRichText(/<[a-z][\s\S]*>/i.test(question.text || ''))
      // Auto-detect rich text per option
      const opts = question.options || []
      setUseRichTextOptions({
        option_a: /<[a-z][\s\S]*>/i.test(opts[0] || ''),
        option_b: /<[a-z][\s\S]*>/i.test(opts[1] || ''),
        option_c: /<[a-z][\s\S]*>/i.test(opts[2] || ''),
        option_d: /<[a-z][\s\S]*>/i.test(opts[3] || ''),
      })
      setExtraRichOpts(opts.slice(4).map((o) => /<[a-z][\s\S]*>/i.test(o || '')))

      // Set image/video URLs from question data
      setQuestionImageUrl(question.question_image_url || null)
      setQuestionVideoUrl(question.question_video_url || null)
      setOptionImages({
        A: question.option_images?.A || null,
        B: question.option_images?.B || null,
        C: question.option_images?.C || null,
        D: question.option_images?.D || null
      })
    } else {
      // Reset form for new question
      questionForm.resetFields()
      setMcqBaseOptionCount(2)
      setUseRichText(false)
      setUseRichTextOptions({ option_a: false, option_b: false, option_c: false, option_d: false })
      setExtraRichOpts([])
      questionForm.setFieldsValue({
        option_a: '',
        option_b: '',
        option_c: '',
        option_d: '',
        extra_options: [],
        correct_answer: isPoll ? undefined : '0',
      })
      setQuestionType('mcq')
      setTypeChipsExpanded(true)
      setExplanationOpen(false)
      setMediaVideoOpen(false)
      setSelectedAnswer(isPoll ? '-1' : '0')

      // Reset image/video state for new question
      setQuestionImageUrl(null)
      setQuestionVideoUrl(null)
      setOptionImages({
        A: null,
        B: null,
        C: null,
        D: null
      })
    }
  }, [question, isPoll])  // Removed setQuestionImageUrl, setOptionImages - they're stable

  const handleTypeChange = (e) => {
    const nextType = e.target.value
    setQuestionType(nextType)
    if (nextType === 'mcq') {
      setMcqBaseOptionCount(2)
      setSelectedAnswer('0')
      questionForm.setFieldsValue({
        option_c: undefined,
        option_d: undefined,
        extra_options: [],
        correct_answer: isPoll ? undefined : '0',
      })
    }
    if (nextType === 'word_cloud' || nextType === 'single_line' || nextType === 'paragraph') {
      questionForm.setFieldsValue({
        option_a: undefined,
        option_b: undefined,
        option_c: undefined,
        option_d: undefined,
        extra_options: [],
        correct_answer: undefined,
        expected_answer: undefined,
      })
    }
    if (nextType === 'scale') {
        questionForm.setFieldsValue({
          option_a: '1',
          option_b: '2',
          option_c: '3',
          option_d: '4',
          option_e: '5',
          correct_answer: isPoll ? undefined : '2'
        })
    }
  }

  const normalizeCorrectAnswerAfterOptionCountChange = (nextOptionCount) => {
    if (isPoll) return
    const current = Number(questionForm.getFieldValue('correct_answer'))
    if (!Number.isInteger(current) || current >= nextOptionCount) {
      questionForm.setFieldValue('correct_answer', String(Math.max(0, nextOptionCount - 1)))
    }
  }



  const handleRewrite = async (fieldName, context) => {
    const val = questionForm.getFieldValue(fieldName)
    const plainVal = stripHtml(val) || (typeof val === 'string' ? val.trim() : '')
    if (!plainVal) return
    setRewriting(prev => ({ ...prev, [fieldName]: true }))
    try {
      const res = await aiAPI.rewrite({ text: plainVal, context, language: language || 'en' })
      questionForm.setFieldsValue({ [fieldName]: res.data.rewritten })
    } catch {
      // silently fail — field stays unchanged
    } finally {
      setRewriting(prev => ({ ...prev, [fieldName]: false }))
    }
  }

  const rewriteIcon = (fieldName) =>
    rewriting[fieldName] ? <LoadingOutlined spin /> : <ThunderboltOutlined />

  const handleAiSuggestPrompt = async () => {
    if (!aiSuggestTopic.trim()) return
    setAiSuggesting(true)
    try {
      const res = await aiAPI.generatePollPrompt({ topic: aiSuggestTopic.trim(), language: language || 'en' })
      questionForm.setFieldsValue({ text: res.data.prompt })
      setAiSuggestOpen(false)
      setAiSuggestTopic('')
    } catch {
      // silently fail — user can still type manually
    } finally {
      setAiSuggesting(false)
    }
  }

  const handleFormBlur = useCallback((e) => {
    if (!onAutoSave || !question) return
    if (e.currentTarget.contains(e.relatedTarget)) return
    onAutoSave(question.id, questionForm.getFieldsValue(true))
  }, [onAutoSave, question, questionForm])

  return (
    <div onBlur={handleFormBlur}>
    <Card style={{ marginBottom: 16, width: '100%' }}>
      <Form
        form={questionForm}
        layout="vertical"
        onFinish={onSave}
        onFinishFailed={(errorInfo) => {
          const errors = errorInfo.errorFields.map(f => f.errors.join(', ')).join(' | ');
          message.warning(`${t('quiz.formValidationFailed')}: ${errors}`);
          console.error('Validation failed:', errorInfo);
        }}
        initialValues={{
          question_type: 'mcq',
          correct_answer: isPoll ? undefined : '0'
        }}
      >
        {/* Question position indicator */}
        {question && (
          <div className="qb-q-position">
            Q{questionIndex + 1}
            <span className="qb-q-position-total"> · {totalQuestions} {totalQuestions !== 1 ? t('quiz.questions', 'questions') : 'question'}</span>
          </div>
        )}

        {/* Question type — pill chips */}
        <Form.Item name="question_type" rules={[{ required: true }]} style={{ marginBottom: 12 }}>
          {typeChipsExpanded ? (
            <div className="qb-type-chips">
              {[
                { value: 'mcq', label: t('quiz.multipleChoice'), show: true },
                { value: 'single_line', label: t('quiz.singleLine'), show: !isPoll || isOfflinePoll === false },
                { value: 'word_cloud', label: t('quiz.wordCloud'), show: isPoll },
                { value: 'scale', label: t('quizPresent.scaleOneToFive'), show: isPoll },
                { value: 'paragraph', label: t('quiz.paragraph'), show: isOfflinePoll },
                { value: 'one_word', label: t('quiz.oneWord'), show: isPoll },
              ].filter(c => c.show).map(chip => (
                <button
                  key={chip.value}
                  type="button"
                  className={`qb-type-chip${questionType === chip.value ? ' qb-type-chip--active' : ''}`}
                  onClick={() => { questionForm.setFieldsValue({ question_type: chip.value }); handleTypeChange({ target: { value: chip.value } }) }}
                >
                  {chip.label}
                </button>
              ))}
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className="qb-type-chip qb-type-chip--active" style={{ cursor: 'default' }}>
                {getQuestionTypeLabel(questionType, t)}
              </span>
              <button type="button" className="qb-change-type-link" onClick={() => setTypeChipsExpanded(true)}>
                {t('quiz.changeType', 'Change type')}
              </button>
            </div>
          )}
        </Form.Item>

        <Form.Item
          label={
            <div className="qb-question-label-row">
              <span className="qb-question-label-text">{t('quiz.question')}</span>
              <div className="qb-scoring-chips">
                {!isPoll && (
                  <Popover
                    content={
                      <InputNumber
                        min={0}
                        precision={0}
                        size="small"
                        value={watchedPoints ?? 1}
                        onChange={val => questionForm.setFieldsValue({ points: val })}
                        style={{ width: 80 }}
                      />
                    }
                    title={t('quiz.pointsLabel')}
                    trigger="click"
                  >
                    <span className="qb-chip">★ {watchedPoints ?? 1}pt</span>
                  </Popover>
                )}
                {isExam && (
                  <Popover
                    content={
                      <InputNumber
                        min={0}
                        step={0.5}
                        size="small"
                        value={watchedNegPoints ?? 0}
                        onChange={val => questionForm.setFieldsValue({ negative_points: val })}
                        style={{ width: 80 }}
                      />
                    }
                    title={t('exam.negativePoints')}
                    trigger="click"
                  >
                    <span className="qb-chip qb-chip--neg">– {watchedNegPoints ?? 0}</span>
                  </Popover>
                )}
                {!isOfflinePoll && (
                  <Popover
                    content={
                      <InputNumber
                        min={0}
                        max={3600}
                        precision={0}
                        size="small"
                        value={watchedMaxTime ?? undefined}
                        onChange={val => questionForm.setFieldsValue({ max_time_seconds: val || null })}
                        placeholder="∞"
                        addonAfter="s"
                        style={{ width: 100 }}
                      />
                    }
                    title={t('quiz.maxTimeSecondsLabel')}
                    trigger="click"
                  >
                    <span className="qb-chip qb-chip--time">⏱ {watchedMaxTime ? `${watchedMaxTime}s` : '—'}</span>
                  </Popover>
                )}
              </div>
            </div>
          }
          style={{ marginBottom: 0 }}
        >
          <div className="qb-compose-box">
            <Form.Item
              name="text"
              noStyle
              rules={[{ required: true, message: t('quiz.questionRequired') }]}
              getValueFromEvent={useRichText ? (v) => v : undefined}
            >
              {useRichText ? (
                <RichTextEditor
                  isDark={theme === 'dark'}
                  placeholder={t('quiz.enterQuestion')}
                />
              ) : (
                <TextArea
                  rows={3}
                  placeholder={t('quiz.enterQuestion')}
                  spellCheck="true"
                  lang={t('common.langCode', { defaultValue: 'en' })}
                  onContextMenu={(e) => e.stopPropagation()}
                />
              )}
            </Form.Item>
            {/* Compose strip: format · image · video ──── rewrite */}
            <div className="qb-compose-strip">
              <Tooltip title={useRichText ? t('quiz.simpleTextToggle') : t('tooltip.richTextToggleQuestion')}>
                <button
                  type="button"
                  className={`qb-aa-btn${useRichText ? ' qb-aa-btn--active' : ''}`}
                  onClick={() => setUseRichText(v => !v)}
                >
                  <FontColorsOutlined />
                </button>
              </Tooltip>
              {questionImageUrl ? (
                <div className="qb-media-thumb">
                  <img src={questionImageUrl} alt="" style={{ height: 28, borderRadius: 4, objectFit: 'cover' }} />
                  <button type="button" className="qb-media-remove" onClick={() => { setQuestionImageUrl(null); setTempImages(prev => ({ ...prev, question: null })) }}>✕</button>
                </div>
              ) : (
                <ImageUpload
                  quizId={parseInt(quizId)}
                  questionId={question?.id}
                  imageType="question"
                  currentImageUrl={null}
                  tempData={tempImages.question}
                  onImageChange={(url, tempKey) => {
                    if (tempKey) {
                      setTempImages(prev => ({ ...prev, question: { url, tempKey } }))
                    } else {
                      setQuestionImageUrl(url)
                      setTempImages(prev => ({ ...prev, question: null }))
                    }
                  }}
                  triggerElement={
                    <button type="button" className="qb-media-btn">
                      📷 {t('quiz.addImage', 'Add image')}
                    </button>
                  }
                />
              )}
              {questionVideoUrl ? (
                <div className="qb-media-thumb">
                  <span style={{ fontSize: 11 }}>🎬 {questionVideoUrl.slice(0, 22)}{questionVideoUrl.length > 22 ? '…' : ''}</span>
                  <button type="button" className="qb-media-remove" onClick={() => { setQuestionVideoUrl(null); setMediaVideoOpen(false) }}>✕</button>
                </div>
              ) : (
                <button type="button" className={`qb-media-btn${mediaVideoOpen ? ' qb-media-btn--active' : ''}`} onClick={() => setMediaVideoOpen(v => !v)}>
                  🎬 {t('quiz.addVideo', 'Add video')}
                </button>
              )}
              <div style={{ flex: 1 }} />
              <Tooltip title={t('ai.rewriteWithAIModel')}>
                <Button
                  size="small"
                  type="text"
                  icon={rewriteIcon('text')}
                  loading={rewriting['text']}
                  style={{ fontSize: 12 }}
                  onClick={() => {
                    if (useRichText) {
                      const rawHtml = questionForm.getFieldValue('text') || ''
                      const plain = rawHtml.replace(/<[^>]*>/g, '').trim()
                      if (!plain) return
                      setRewriting(prev => ({ ...prev, text: true }))
                      aiAPI.rewrite({ text: plain, context: isPoll ? 'poll question' : 'quiz question', language: language || 'en' })
                        .then(res => questionForm.setFieldsValue({ text: res.data.rewritten }))
                        .catch(() => {})
                        .finally(() => setRewriting(prev => ({ ...prev, text: false })))
                    } else {
                      handleRewrite('text', isPoll ? 'poll question' : 'quiz question')
                    }
                  }}
                >
                  {t('ai.rewrite')}
                </Button>
              </Tooltip>
            </div>
          </div>
        </Form.Item>
        {mediaVideoOpen && !questionVideoUrl && (
          <Form.Item name="question_video_url" style={{ marginBottom: 12 }}>
            <Input
              placeholder={t('quiz.videoUrlPlaceholder')}
              allowClear
              autoFocus
              onChange={e => setQuestionVideoUrl(e.target.value || null)}
            />
          </Form.Item>
        )}
        {questionVideoUrl && (() => {
          const embedUrl = getVideoEmbedUrl(questionVideoUrl)
          return embedUrl
            ? <VideoEmbed url={questionVideoUrl} height={180} />
            : <Text type="warning" style={{ display: 'block', marginBottom: 8 }}>{t('quiz.videoUrlInvalid')}</Text>
        })()}

        {questionType === 'mcq' && (
          <>
            {/* Hidden correct_answer field — value set via letter dot clicks */}
            {!isPoll && (
              <Form.Item name="correct_answer" hidden rules={[{ required: true, message: t('quiz.correctAnswerRequired') }]}>
                <Input />
              </Form.Item>
            )}

            {/* Option rows: A / B / C / D — 2-column grid on desktop */}
            <div className="qb-options-grid">
            {[
              { key: 'option_a', imgKey: 'A', tempKey: 'optionA', richKey: 'option_a', label: 'A', index: 0, show: true, required: true, req: t('quiz.optionARequired'), ph: t('quiz.optionAPlaceholder') },
              { key: 'option_b', imgKey: 'B', tempKey: 'optionB', richKey: 'option_b', label: 'B', index: 1, show: true, required: true, req: t('quiz.optionBRequired'), ph: t('quiz.optionBPlaceholder') },
              { key: 'option_c', imgKey: 'C', tempKey: 'optionC', richKey: 'option_c', label: 'C', index: 2, show: mcqBaseOptionCount >= 3, required: false, req: null, ph: t('quiz.optionCPlaceholder') },
              { key: 'option_d', imgKey: 'D', tempKey: 'optionD', richKey: 'option_d', label: 'D', index: 3, show: mcqBaseOptionCount >= 4, required: false, req: null, ph: t('quiz.optionDPlaceholder') },
            ].filter(o => o.show).map(opt => {
              const isRich = !!useRichTextOptions[opt.richKey]
              const isCorrect = !isPoll && selectedAnswer === String(opt.index)
              const hasImg = !!optionImages[opt.imgKey]
              const rules = isRich
                ? [{ validator: (_, v) => stripHtml(v) ? Promise.resolve() : Promise.reject(opt.req || '') }]
                : opt.required ? [{ required: true, message: opt.req }] : []
              return (
                <div key={opt.key} className={`qb-option-card${isCorrect ? ' qb-option-card--correct' : ''}`}>
                  {/* Top row: correct-answer dot + input */}
                  <div className="qb-opt-row">
                    <button
                      type="button"
                      className={`qb-opt-dot${isCorrect ? ' qb-opt-dot--correct' : ''}${isPoll ? ' qb-opt-dot--poll' : ''}`}
                      onClick={() => {
                        if (isPoll) return
                        setSelectedAnswer(String(opt.index))
                        questionForm.setFieldsValue({ correct_answer: String(opt.index) })
                      }}
                      title={isPoll ? undefined : t('quiz.markCorrect', 'Mark as correct answer')}
                    >
                      {opt.label}
                    </button>
                    <div className="qb-opt-content">
                      <Form.Item
                        name={opt.key}
                        style={{ marginBottom: 0 }}
                        rules={rules}
                        getValueFromEvent={isRich ? (v) => v : undefined}
                      >
                        {isRich
                          ? <RichTextEditor isDark={theme === 'dark'} placeholder={opt.ph} />
                          : <Input
                              placeholder={opt.ph}
                              spellCheck="true"
                              lang={t('common.langCode', { defaultValue: 'en' })}
                              onContextMenu={e => e.stopPropagation()}
                            />
                        }
                      </Form.Item>
                      {hasImg && (
                        <div className="qb-opt-img-thumb">
                          <img src={optionImages[opt.imgKey]} alt="" />
                          <button type="button" className="qb-media-remove" onClick={() => { setOptionImages(prev => ({ ...prev, [opt.imgKey]: null })); setTempImages(prev => ({ ...prev, [opt.tempKey]: null })) }}>✕</button>
                        </div>
                      )}
                    </div>
                  </div>
                  {/* Compose strip: format toggle + image + rewrite — visible on focus */}
                  <div className="qb-opt-strip">
                    <Tooltip title={isRich ? t('quiz.simpleTextToggle') : t('tooltip.richTextToggleOptions')}>
                      <button type="button" className={`qb-aa-btn qb-aa-btn--sm${isRich ? ' qb-aa-btn--active' : ''}`} onClick={() => toggleOptRich(opt.richKey)}>
                        <FontColorsOutlined />
                      </button>
                    </Tooltip>
                    <Tooltip title={t('quiz.addImage', 'Add image')}>
                      <ImageUpload
                        quizId={parseInt(quizId)}
                        questionId={question?.id}
                        imageType={`option_${opt.label.toLowerCase()}`}
                        currentImageUrl={null}
                        tempData={tempImages[opt.tempKey]}
                        onImageChange={(url, tempKey) => {
                          if (tempKey) {
                            setTempImages(prev => ({ ...prev, [opt.tempKey]: { url, tempKey } }))
                          } else {
                            setOptionImages(prev => ({ ...prev, [opt.imgKey]: url }))
                            setTempImages(prev => ({ ...prev, [opt.tempKey]: null }))
                          }
                        }}
                        triggerElement={
                          <button type="button" className={`qb-opt-camera qb-opt-strip-btn${hasImg ? ' qb-opt-camera--active' : ''}`}>📷</button>
                        }
                      />
                    </Tooltip>
                    <Tooltip title={t('ai.rewriteWithAI')}>
                      <Button type="text" size="small" icon={rewriteIcon(opt.key)} onClick={() => handleRewrite(opt.key, 'quiz answer option')} />
                    </Tooltip>
                  </div>
                </div>
              )
            })}
            </div>{/* end qb-options-grid (fixed A-D) */}

            <Form.List name="extra_options">
              {(fields, { add, remove }) => (
                <>
                  <div className="qb-options-grid">
                  {fields.map((field) => {
                    const isRich = !!extraRichOpts[field.name]
                    const extraIndex = mcqBaseOptionCount + field.name
                    const isCorrect = !isPoll && selectedAnswer === String(extraIndex)
                    const extraLabel = String.fromCharCode(65 + extraIndex)
                    return (
                      <div key={field.key} className={`qb-option-card${isCorrect ? ' qb-option-card--correct' : ''}`}>
                        <div className="qb-opt-row">
                          <button
                            type="button"
                            className={`qb-opt-dot${isCorrect ? ' qb-opt-dot--correct' : ''}${isPoll ? ' qb-opt-dot--poll' : ''}`}
                            onClick={() => {
                              if (isPoll) return
                              setSelectedAnswer(String(extraIndex))
                              questionForm.setFieldsValue({ correct_answer: String(extraIndex) })
                            }}
                          >
                            {extraLabel}
                          </button>
                          <div className="qb-opt-content">
                            <Form.Item
                              {...field}
                              style={{ marginBottom: 0 }}
                              rules={isRich
                                ? [{ validator: (_, v) => stripHtml(v) ? Promise.resolve() : Promise.reject(t('quiz.optionRequired', { defaultValue: 'Option cannot be empty' })) }]
                                : [{ required: true, message: t('quiz.optionRequired', { defaultValue: 'Option cannot be empty' }) }]
                              }
                              getValueFromEvent={isRich ? (v) => v : undefined}
                            >
                              {isRich
                                ? <RichTextEditor isDark={theme === 'dark'} placeholder={t('quiz.optionPlaceholder', { defaultValue: 'Enter option text' })} />
                                : <Input placeholder={t('quiz.optionPlaceholder', { defaultValue: 'Enter option text' })} />
                              }
                            </Form.Item>
                          </div>
                        </div>
                        <div className="qb-opt-strip">
                          <Tooltip title={isRich ? t('quiz.simpleTextToggle') : t('tooltip.richTextToggleOptions')}>
                            <button type="button" className={`qb-aa-btn qb-aa-btn--sm${isRich ? ' qb-aa-btn--active' : ''}`} onClick={() => toggleExtraOptRich(field.name)}>
                              <FontColorsOutlined />
                            </button>
                          </Tooltip>
                          <button type="button" className="qb-opt-camera qb-opt-strip-btn" onClick={() => remove(field.name)} title="Remove option">✕</button>
                        </div>
                      </div>
                    )
                  })}
                  </div>{/* end qb-options-grid (extras) */}
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 4, marginBottom: 16 }}>
                    <Button
                      type="dashed"
                      size="small"
                      onClick={() => {
                        const totalOptions = mcqBaseOptionCount + fields.length
                        if (totalOptions >= 10) return
                        if (mcqBaseOptionCount < 4) {
                          const nextCount = mcqBaseOptionCount + 1
                          setMcqBaseOptionCount(nextCount)
                          normalizeCorrectAnswerAfterOptionCountChange(nextCount + fields.length)
                          return
                        }
                        add()
                      }}
                      icon={<PlusOutlined />}
                      disabled={mcqBaseOptionCount + fields.length >= 10}
                    >
                      {t('quiz.addOption', { defaultValue: 'Add option' })}
                    </Button>
                    <Button
                      size="small"
                      onClick={() => {
                        if (fields.length > 0) {
                          remove(fields.length - 1)
                          normalizeCorrectAnswerAfterOptionCountChange(mcqBaseOptionCount + fields.length - 1)
                          return
                        }
                        if (mcqBaseOptionCount === 4) {
                          questionForm.setFieldsValue({ option_d: undefined })
                          setOptionImages(prev => ({ ...prev, D: null }))
                          setTempImages(prev => ({ ...prev, optionD: null }))
                          setMcqBaseOptionCount(3)
                          normalizeCorrectAnswerAfterOptionCountChange(3)
                          return
                        }
                        if (mcqBaseOptionCount === 3) {
                          questionForm.setFieldsValue({ option_c: undefined })
                          setOptionImages(prev => ({ ...prev, C: null }))
                          setTempImages(prev => ({ ...prev, optionC: null }))
                          setMcqBaseOptionCount(2)
                          normalizeCorrectAnswerAfterOptionCountChange(2)
                        }
                      }}
                      icon={<MinusCircleOutlined />}
                      disabled={mcqBaseOptionCount + fields.length <= 2}
                    >
                      {t('quiz.removeOption', { defaultValue: 'Remove option' })}
                    </Button>
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      {t('quiz.optionCountHint', { defaultValue: 'Options: {{count}} (min 2, max 10)', count: mcqBaseOptionCount + fields.length })}
                    </Text>
                  </div>
                </>
              )}
            </Form.List>
          </>
        )}

        {questionType === 'one_word' && (
          <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
            {t('quiz.oneWordDescription')}
          </Text>
        )}

        {questionType === 'word_cloud' && (
          <>
            <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
              {t('quiz.wordCloudDescription')}
            </Text>
            {!aiSuggestOpen && isAdmin ? (
              <Button
                size="small"
                icon={<BulbOutlined />}
                style={{ marginBottom: 12 }}
                onClick={() => setAiSuggestOpen(true)}
              >
                {t('ai.aiSuggestPrompt')}
              </Button>
            ) : (
              <Space style={{ marginBottom: 12, width: '100%' }} wrap>
                <Input
                  placeholder={t('ai.topicForAIPlaceholder')}
                  value={aiSuggestTopic}
                  onChange={e => setAiSuggestTopic(e.target.value)}
                  onPressEnter={handleAiSuggestPrompt}
                  style={{ width: 240 }}
                  autoFocus
                />
                <Button
                  type="primary"
                  size="small"
                  icon={<BulbOutlined />}
                  loading={aiSuggesting}
                  onClick={handleAiSuggestPrompt}
                  disabled={!aiSuggestTopic.trim()}
                >
                  {t('ai.suggest')}
                </Button>
                <Button size="small" onClick={() => { setAiSuggestOpen(false); setAiSuggestTopic('') }}>{t('common.cancel')}</Button>
              </Space>
            )}
          </>
        )}

        {questionType === 'single_line' && (
          <>
            <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
              {t('quiz.singleLineDescription')}
            </Text>
            {!isPoll && (
              <Form.Item
                name="expected_answer"
                label={t('quiz.correctAnswer')}
                rules={[{ required: !isPoll, message: t('quiz.correctAnswerRequired') }]}
                help={t('tooltip.expectedAnswer')}
              >
                <Input
                  placeholder={t('quiz.expectedAnswerPlaceholder')}
                  spellCheck="true"
                  lang={t('common.langCode', { defaultValue: 'en' })}
                  onContextMenu={(e) => e.stopPropagation()}
                />
              </Form.Item>
            )}
          </>
        )}

        {questionType === 'paragraph' && (
          <>
            <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
              {t('quiz.paragraphDescription')}
            </Text>
            {!isPoll && (
              <Form.Item
                name="expected_answer"
                label={t('quiz.correctAnswer')}
                rules={[{ required: !isPoll, message: t('quiz.correctAnswerRequired') }]}
                help={t('tooltip.expectedAnswer')}
              >
                <TextArea
                  rows={3}
                  placeholder={t('quiz.expectedAnswerGuidancePlaceholder')}
                  spellCheck="true"
                  lang={t('common.langCode', { defaultValue: 'en' })}
                  onContextMenu={(e) => e.stopPropagation()}
                />
              </Form.Item>
            )}
          </>
        )}

        {questionType === 'scale' && (
          <>
            <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
              {t('quiz.scaleDescription')}
            </Text>
            {!isPoll && (
              <Form.Item
                name="correct_answer"
                label={t('quiz.correctAnswer')}
                rules={[{ required: true, message: t('quiz.correctAnswerRequired') }]}
                help={t('tooltip.scaleCorrectAnswer')}
              >
                <Radio.Group>
                  <Radio value="0">1</Radio>
                  <Radio value="1">2</Radio>
                  <Radio value="2">3</Radio>
                  <Radio value="3">4</Radio>
                  <Radio value="4">5</Radio>
                </Radio.Group>
              </Form.Item>
            )}
          </>
        )}

        {/* Explanation — collapsed by default */}
        <div style={{ marginBottom: 16 }}>
          <button
            type="button"
            className="qb-explanation-toggle"
            onClick={() => setExplanationOpen(v => !v)}
          >
            {explanationOpen ? '▾' : '▸'} {explanationOpen
              ? t('quiz.editExplanation', 'Edit explanation')
              : t('quiz.addExplanation', 'Add explanation (optional)')}
          </button>
          {explanationOpen && (
            <Form.Item name="answer_explanation" style={{ marginTop: 8, marginBottom: 0 }}>
              <Input.TextArea
                placeholder={t('quiz.answerExplanationPlaceholder', 'Explain why the correct answer is correct…')}
                maxLength={1000}
                showCount
                autoSize={{ minRows: 2, maxRows: 5 }}
                autoFocus
              />
            </Form.Item>
          )}
        </div>

        {/* Hidden form bindings for scoring — values managed via label chips */}
        {!isPoll && (
          <Form.Item name="points" initialValue={1} rules={[{ required: true, message: t('quiz.pointsRequired') }]} style={{ display: 'none', margin: 0 }}>
            <InputNumber />
          </Form.Item>
        )}
        {isExam && (
          <Form.Item name="negative_points" initialValue={0} style={{ display: 'none', margin: 0 }}>
            <InputNumber />
          </Form.Item>
        )}
        {!isOfflinePoll && (
          <Form.Item name="max_time_seconds" style={{ display: 'none', margin: 0 }}>
            <InputNumber />
          </Form.Item>
        )}

        {/* Footer row: Required toggle (offline poll only) + Prev / Next */}
        <div className="qb-footer-row">
          {isOfflinePoll && (
            <div className="qb-footer-field">
              <label className="qb-footer-label">{t('offlinePoll.required', 'Required')}</label>
              <Form.Item name="is_required" valuePropName="checked" style={{ margin: 0 }}>
                <Switch size="small" />
              </Form.Item>
            </div>
          )}
          <div style={{ flex: 1 }} />
          {question ? (
            /* Existing question: Prev / Next navigation (autosave handles saving) */
            <>
              <Button
                size="small"
                icon={<LeftOutlined />}
                disabled={questionIndex <= 0}
                onClick={() => {
                  if (onAutoSave) onAutoSave(question.id, questionForm.getFieldsValue(true))
                  onNavigate && onNavigate(-1)
                }}
              >
                {t('common.prev', 'Prev')}
              </Button>
              <Button
                size="small"
                icon={<RightOutlined />}
                iconPosition="end"
                disabled={questionIndex >= totalQuestions - 1}
                onClick={() => {
                  if (onAutoSave) onAutoSave(question.id, questionForm.getFieldsValue(true))
                  onNavigate && onNavigate(1)
                }}
              >
                {t('common.next', 'Next')}
              </Button>
            </>
          ) : (
            /* New question: explicit Add / Cancel */
            <>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading || movingImages}
                icon={<PlusOutlined />}
                size="small"
              >
                {movingImages ? t('quiz.movingImages') : t('quiz.addQuestion')}
              </Button>
              <Button size="small" icon={<CloseOutlined />} onClick={onCancel}>{t('common.cancel')}</Button>
            </>
          )}
        </div>
      </Form>
    </Card>
    </div>
  )
}

// Memoize QuestionForm with default shallow prop comparison to avoid stale form values.
const MemoizedQuestionForm = memo(QuestionForm)

export default function QuizBuilder() {
  const { token } = theme.useToken()
  const { message } = App.useApp()
  const { id } = useParams()
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [quiz, setQuiz] = useState(null)
  const [questions, setQuestions] = useState([])
  const [editingQuestion, setEditingQuestion] = useState(null)
  const [railTitleEditing, setRailTitleEditing] = useState(false)
  const [railTitleValue, setRailTitleValue] = useState('')
  const [mobileView, setMobileView] = useState('list') // 'list' | 'form'
  const [stageView, setStageView] = useState(null) // null | 'setup' | 'proctoring'
  const [railFilter, setRailFilter] = useState('all') // 'all' | 'incomplete'
  const [proctoringPolicy, setProctoringPolicy] = useState(null)
  const [saveStatus, setSaveStatus] = useState('idle') // 'idle' | 'saving' | 'saved' | 'error'
  const saveStatusTimerRef = useRef(null)
  const lastFailedSaveRef = useRef(null) // { questionId, values } — for retry
  const questionsRef = useRef(null)
  
  // Image state for question being edited/created
  const [questionImageUrl, setQuestionImageUrl] = useState(null)
  const [optionImages, setOptionImages] = useState({
    A: null,
    B: null,
    C: null,
    D: null
  })
  
  const location = useLocation()
  
  // Extract query params for initial creation (e.g. ?type=poll or ?type=offline_poll)
  const searchParams = new URLSearchParams(location.search)
  const rawType = searchParams.get('type')?.toLowerCase()
  const initialQuizType = rawType === 'poll' ? 'poll' : rawType === 'offline_poll' ? 'offline_poll' : (rawType === 'exam' || rawType === 'test') ? 'exam' : 'quiz'
  const aiPromptParam = searchParams.get('ai_prompt') || ''
  const aiCountParam = parseInt(searchParams.get('ai_count') || '5', 10) || 5
  const aiContentTypeParam = searchParams.get('ai_content_type') || 'general'
  const aiDifficultyParam = searchParams.get('ai_difficulty') || 'medium'
  const aiAutoOpen = searchParams.get('ai_auto_open') === '1'
  const isNewActivity = searchParams.get('new') === '1'

  const [tempImages, setTempImages] = useState({
    question: null,  // {url, tempKey}
    optionA: null,
    optionB: null,
    optionC: null,
    optionD: null
  })
  
  // Loading state for moving temp images
  const [movingImages, setMovingImages] = useState(false)
  const [savingForAI, setSavingForAI] = useState(false)
  const [pollLinkModal, setPollLinkModal] = useState({ open: false, url: '' })
  const [examLinkModal, setExamLinkModal] = useState({ open: false, url: '' })
  const [batchConfirmModal, setBatchConfirmModal] = useState({ open: false })
  const isPoll = quiz?.quiz_type === 'poll' || quiz?.quiz_type === 'offline_poll' || (!quiz && initialQuizType === 'poll') || (!quiz && initialQuizType === 'offline_poll')
  const isOfflinePoll = quiz?.quiz_type === 'offline_poll' || (!quiz && initialQuizType === 'offline_poll')
  const isExam = quiz?.quiz_type === 'exam' || (!quiz && initialQuizType === 'exam')
  const isLiveMode = quiz?.status === 'ready'
  const currentUser = JSON.parse(localStorage.getItem('user') || 'null')
  const isAdmin = currentUser?.role === 'admin' || currentUser?.role === 'super_admin'

  // Rewrite state for main form fields
  const [mainRewriting, setMainRewriting] = useState({})

  const handleMainRewrite = async (fieldName, context) => {
    const val = form.getFieldValue(fieldName)
    if (!val?.trim()) return
    setMainRewriting(prev => ({ ...prev, [fieldName]: true }))
    try {
      const res = await aiAPI.rewrite({ text: val.trim(), context, language: i18n.language })
      form.setFieldsValue({ [fieldName]: res.data.rewritten })
    } catch {
      // silently fail
    } finally {
      setMainRewriting(prev => ({ ...prev, [fieldName]: false }))
    }
  }

  // AI generation modal state
  const [aiModalOpen, setAiModalOpen] = useState(false)
  const [aiStep, setAiStep] = useState('input') // 'input' | 'preview'
  const [aiGenerating, setAiGenerating] = useState(false)
  const [aiAdding, setAiAdding] = useState(false)
  const [aiTopic, setAiTopic] = useState(aiPromptParam)
  const [aiCount, setAiCount] = useState(aiCountParam)
  const [aiError, setAiError] = useState(null)
  const [aiPreview, setAiPreview] = useState([]) // [{text, options, correct_answer_index, selected, question_type}]
  const [aiTitle, setAiTitle] = useState(null)
  const [aiDescription, setAiDescription] = useState(null)
  const [aiTitleDismissed, setAiTitleDismissed] = useState(false)
  const [aiContentType, setAiContentType] = useState(aiContentTypeParam)
  const [aiDifficulty, setAiDifficulty] = useState(aiDifficultyParam)
  const [editingPreviewIndex, setEditingPreviewIndex] = useState(null)
  const [editingData, setEditingData] = useState(null) // {text, options, correct_answer_index}
  const [regeneratingIndex, setRegeneratingIndex] = useState(null)
  const [aiStreaming, setAiStreaming] = useState(false)
  const [aiStreamCount, setAiStreamCount] = useState(0)
  const aiAbortRef = useRef(null)
  const [aiStyle, setAiStyle] = useState('general')
  const [aiExamSuggDuration, setAiExamSuggDuration] = useState(null)
  const [aiExamSuggProctoring, setAiExamSuggProctoring] = useState(null)
  const [aiExamSuggDismissed, setAiExamSuggDismissed] = useState(false)
  const [voiceListening, setVoiceListening] = useState(false)
  const recognizerRef = useRef(null)
  const [aiImageHintCount, setAiImageHintCount] = useState(0)
  const [aiOptionImageHintCount, setAiOptionImageHintCount] = useState(0)
  
  // Excel Import/Export State
  const [importData, setImportData] = useState(null)
  const [isValidating, setIsValidating] = useState(false)
  const [isImporting, setIsImporting] = useState(false)
  const [activeTab, setActiveTab] = useState('1')

  const handleDownloadTemplate = async () => {
    try {
      const response = await quizAPI.getImportTemplate()
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', 'Swaya_me_Test_Template.xlsx')
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (error) {
      message.error(t('quiz.exportFailed'))
    }
  }

  const handleDownloadDraft = async () => {
    try {
      // Collect current form data and questions
      const currentDraft = {
        lang: i18n.language,
        title: form.getFieldValue('title') || 'Untitled Quiz',
        description: form.getFieldValue('description'),
        quiz_type: form.getFieldValue('quiz_type') || 'quiz',
        duration_minutes: form.getFieldValue('exam_time_limit_minutes'),
        questions: (questions || []).map(q => ({
          type: q.question_type,
          text: q.text,
          points: q.points,
          negative_points: q.negative_points,
          max_time_seconds: q.max_time_seconds,
          correct_answer_index: q.correct_answer_index,
          expected_answer: q.expected_answer,
          options: (q.question_type === 'mcq' || q.question_type === 'scale') 
            ? [q.option_a, q.option_b, q.option_c, q.option_d, ...(q.extra_options || [])]
            : [q.expected_answer]
        }))
      }
      
      const response = await quizAPI.exportDraftToExcel(currentDraft)
      const blob = new Blob([response.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      const fileName = `${currentDraft.title.replace(/\s+/g, '_')}_Swaya.xlsx`
      link.download = fileName
      
      // Standard robust download trigger for Chrome/Safari compatibility
      document.body.appendChild(link)
      const clickEvent = new MouseEvent('click', {
        view: window,
        bubbles: true,
        cancelable: true
      })
      link.dispatchEvent(clickEvent)
      
      // Minor delay before cleanup to ensure browser has handled the trigger
      setTimeout(() => {
        document.body.removeChild(link)
        window.URL.revokeObjectURL(url)
      }, 100)
    } catch (error) {
      console.error('Export draft error:', error)
      message.error(t('quiz.exportFailed'))
    }
  }

  const handleExcelUpload = async (info) => {
    const { status } = info.file
    if (status === 'uploading') {
      setIsValidating(true)
      return
    }
    if (status === 'done' || (status === undefined && info.file)) {
      // Ant Design's Dragger sometimes needs manual handling if not using 'action' prop
      try {
        setIsValidating(true)
        const response = await quizAPI.validateImport(info.file.originFileObj || info.file)
        setImportData(response.data)
        message.success(t('quiz.importValidated', { filename: info.file.name }))
      } catch (error) {
        console.error('Validation error:', error)
        message.error(t('quiz.importValidateFailed', { filename: info.file.name, error: error.response?.data?.detail || error.message }))
      } finally {
        setIsValidating(false)
      }
    }
  }

  const handleFinalizeImport = async () => {
    if (!importData || !importData.canImport) return
    
    setIsImporting(true)
    try {
      const response = await quizAPI.finalizeImport(importData)
      message.success(t('quiz.importSuccess'))
      // Redirect to the new quiz or just refresh
      navigate(`/quiz/${response.data.id}/edit`)
    } catch (error) {
      console.error('Import error:', error)
      message.error(t('quiz.importError'))
    } finally {
      setIsImporting(false)
    }
  }

  useEffect(() => {
    if (id) {
      loadQuiz()
    } else {
      // For new quizzes, set initial form values based on URL param
      const isExamLocal = initialQuizType === 'exam'
      const isOfflineLocal = initialQuizType === 'offline_poll'
      
      const values = {
        quiz_type: initialQuizType
      }
      
      if (isExamLocal) {
        values.exam_start_at = dayjs()
        values.exam_end_at = dayjs().add(1, 'day')
        values.exam_time_limit_minutes = 30
      } else if (isOfflineLocal) {
        values.offline_start_at = dayjs()
        values.offline_end_at = dayjs().add(1, 'day')
      }
      
      form.setFieldsValue(values)
    }
  }, [id, initialQuizType, form])

  // Auto-open AI modal when arriving from CreateChooser "Generate" flow or after new-quiz AI save
  const aiAutoTriggeredRef = useRef(false)
  useEffect(() => {
    if (id && quiz && (aiPromptParam || aiAutoOpen) && !aiAutoTriggeredRef.current) {
      aiAutoTriggeredRef.current = true
      setAiModalOpen(true)
      setAiStep('input')
      setAiError(null)
    }
  }, [id, quiz, aiPromptParam, aiAutoOpen])

  // On mobile, the quiz settings card can push the questions section off-screen.
  // Scroll to it once after the initial load so users can see the Add Question button.
  const hasScrolledRef = useRef(false)
  useEffect(() => {
    if (id && quiz && !hasScrolledRef.current && questionsRef.current) {
      hasScrolledRef.current = true
      setTimeout(() => {
        questionsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }, 300)
    }
  }, [id, quiz])

  // Reset autosave status when switching questions (clears any error state)
  useEffect(() => {
    setSaveStatus('idle')
    clearTimeout(saveStatusTimerRef.current)
    lastFailedSaveRef.current = null
  }, [editingQuestion])

  const loadQuiz = useCallback(async () => {
    try {
      const response = await quizAPI.get(id)
      setQuiz(response.data)
      setProctoringPolicy(response.data.proctoring_policy || { enabled: false, rules: {}, escalation: { lock_on_violation_count: 3, auto_submit_on_lock: false } })
      console.log('Quiz loaded from API:', response.data)
      console.log('Raw questions from API:', JSON.stringify(response.data.questions, null, 2))
      
      // Transform backend format to frontend format
      const transformedQuestions = (response.data.questions || []).map(q => {
        console.log('Transforming question:', q.id, 'Type:', q.question_type)
        const baseQuestion = {
          ...q,
          question_type: q.question_type || 'mcq',
          points: q.points || 1,
          max_time_seconds: q.max_time_seconds ?? null,
        }
        
        // Only transform options for MCQ questions
        if ((q.question_type === 'mcq' || q.question_type === 'scale') && q.options) {
          return {
            ...baseQuestion,
            option_a: q.options[0],
            option_b: q.options[1],
            option_c: q.options[2],
            option_d: q.options[3],
            extra_options: q.question_type === 'mcq' ? (q.options.slice(4) || []) : [],
            option_e: q.options[4],
            correct_answer: q.question_type === 'mcq'
              ? String(q.correct_answer_index ?? 0)
              : String(q.correct_answer_index ?? 0)
          }
        }
        if ((q.question_type === 'single_line' || q.question_type === 'paragraph') && q.options) {
          return {
            ...baseQuestion,
            expected_answer: q.options[0] || ''
          }
        }
        
        return baseQuestion
      })
      console.log('Transformed questions:', transformedQuestions)
      console.log('Total questions after transform:', transformedQuestions.length)
      setQuestions(transformedQuestions)
      
      form.setFieldsValue({
        title: response.data.title,
        description: response.data.description,
        quiz_type: response.data.quiz_type || 'quiz',
        offline_start_at: response.data.offline_start_at ? dayjs(response.data.offline_start_at) : undefined,
        offline_end_at: response.data.offline_end_at ? dayjs(response.data.offline_end_at) : undefined,
        offline_results_email: response.data.offline_results_email || undefined,
        exam_start_at: response.data.exam_start_at ? dayjs(response.data.exam_start_at) : undefined,
        exam_end_at: response.data.exam_end_at ? dayjs(response.data.exam_end_at) : undefined,
        exam_time_limit_minutes: response.data.exam_time_limit_seconds ? Math.floor(response.data.exam_time_limit_seconds / 60) : undefined,
        exam_results_email: response.data.exam_results_email || undefined,
        exam_require_email: response.data.exam_require_email || false,
        exam_allowed_domains: response.data.exam_allowed_domains || undefined,
        skin: response.data.skin || null,
      })
      // Auto-focus title for freshly created activities (skip-setup flow)
      if (isNewActivity) {
        setTimeout(() => {
          setRailTitleValue(response.data.title || '')
          setRailTitleEditing(true)
        }, 300)
      }
    } catch (error) {
      const errorMsg = error.response?.data?.detail || t('quiz.loadError')
      message.error(errorMsg)
      console.error('Load quiz error:', error.response?.data || error)
    }
  }, [id])

  const renderQuizSettings = () => (
    <>
      <Form.Item name="quiz_type" hidden>
        <Input />
      </Form.Item>
      <Form.Item
        name="title"
        label={isExam ? t('exam.examTitle') : isOfflinePoll ? t('offlinePoll.pollTitle', 'Offline Poll Title') : isPoll ? t('quiz.pollTitle') : t('quiz.quizTitle')}
        rules={[{ required: true, message: isExam ? t('exam.examTitleRequired') : isOfflinePoll ? t('offlinePoll.pollTitleRequired', 'Please enter a title') : isPoll ? t('quiz.pollTitleRequired') : t('quiz.quizTitleRequired') }]}
      >
        <Input
          placeholder={isExam ? t('exam.enterExamTitle') : isOfflinePoll ? t('offlinePoll.enterPollTitle', 'Enter offline poll title') : isPoll ? t('quiz.enterPollTitle') : t('quiz.enterQuizTitle')}
          size="large"
          spellCheck="true"
          lang={i18n.language}
          suffix={(
            <Tooltip title={t('ai.rewriteWithAI')}>
              <Button
                type="text"
                size="small"
                icon={mainRewriting['title'] ? <LoadingOutlined spin /> : <ThunderboltOutlined />}
                loading={mainRewriting['title']}
                onClick={() => handleMainRewrite('title', isExam ? 'exam title' : isPoll ? 'poll title' : 'quiz title')}
              />
            </Tooltip>
          )}
        />
      </Form.Item>

      <Form.Item
        name="description"
        label={isExam ? t('exam.examDescription') : isOfflinePoll ? t('offlinePoll.pollDescription', 'Description') : isPoll ? t('quiz.pollDescription') : t('quiz.quizDescription')}
      >
        <TextArea
          rows={3}
          placeholder={isExam ? t('exam.enterExamDescription') : isOfflinePoll ? t('offlinePoll.enterPollDescription', 'Enter offline poll description (optional)') : isPoll ? t('quiz.enterPollDescription') : t('quiz.enterQuizDescription')}
          spellCheck="true"
          lang={i18n.language}
        />
      </Form.Item>
      {(
        <div style={{ marginTop: -8, marginBottom: 12, textAlign: 'right' }}>
          <Tooltip title={t('ai.rewriteDescWithAI')}>
            <Button
              size="small"
              type="text"
              icon={mainRewriting['description'] ? <LoadingOutlined spin /> : <ThunderboltOutlined />}
              loading={mainRewriting['description']}
              onClick={() => handleMainRewrite('description', isPoll ? 'poll description' : 'quiz description')}
            >
              {t('ai.rewrite')}
            </Button>
          </Tooltip>
        </div>
      )}

      {/* Participant skin picker */}
      <Form.Item name="skin" label={t('quiz.skinLabel', 'Participant skin')}>
        <Radio.Group buttonStyle="solid">
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 4 }}>
            {Object.values(skins).map(skin => (
              <Radio.Button
                key={skin.id}
                value={skin.id === 'default' ? null : skin.id}
                style={{ height: 'auto', padding: '8px 14px', textAlign: 'center', lineHeight: 1.4 }}
              >
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
                  <div style={{ display: 'flex', gap: 3 }}>
                    {skin.preview.map((c, i) => (
                      <div key={i} style={{ width: 14, height: 14, borderRadius: '50%', background: c, border: '1px solid rgba(0,0,0,0.15)' }} />
                    ))}
                  </div>
                  <span style={{ fontSize: 12, fontWeight: 500 }}>{skin.emoji} {skin.name}</span>
                </div>
              </Radio.Button>
            ))}
          </div>
        </Radio.Group>
      </Form.Item>

      {/* Offline poll configuration fields */}
      {isOfflinePoll && (
        <Space direction="vertical" style={{ width: '100%', marginBottom: 16 }}>
          <Form.Item
            name="offline_start_at"
            label={t('offlinePoll.startDate', 'Start Date & Time')}
            rules={[{ required: isOfflinePoll, message: t('quiz.startDateRequired') }]}
          >
            <DatePicker
              showTime
              style={{ width: '100%' }}
              disabledDate={(d) => d && d.isBefore(dayjs().startOf('day'))}
              disabledTime={(d) => {
                if (!d || !d.isSame(dayjs(), 'day')) return {}
                const now = dayjs()
                return {
                  disabledHours: () => Array.from({ length: now.hour() }, (_, i) => i),
                  disabledMinutes: (h) => h === now.hour() ? Array.from({ length: now.minute() }, (_, i) => i) : [],
                }
              }}
            />
          </Form.Item>
          <Form.Item
            name="offline_end_at"
            label={t('offlinePoll.endDate', 'End Date & Time')}
            rules={[{ required: isOfflinePoll, message: t('quiz.endDateRequired') }]}
          >
            <DatePicker
              showTime
              style={{ width: '100%' }}
              disabledDate={(d) => {
                if (!d) return false
                const start = form.getFieldValue('offline_start_at')
                const floor = start ? start.startOf('day') : dayjs().startOf('day')
                return d.isBefore(floor)
              }}
              disabledTime={(d) => {
                if (!d) return {}
                const start = form.getFieldValue('offline_start_at')
                const ref = start && d.isSame(start, 'day') ? start : (d.isSame(dayjs(), 'day') ? dayjs() : null)
                if (!ref) return {}
                return {
                  disabledHours: () => Array.from({ length: ref.hour() }, (_, i) => i),
                  disabledMinutes: (h) => h === ref.hour() ? Array.from({ length: ref.minute() + 1 }, (_, i) => i) : [],
                }
              }}
            />
          </Form.Item>
          <Form.Item
            name="offline_results_email"
            label={t('offlinePoll.resultsEmail', 'Email Results To (optional)')}
          >
            <Input type="email" placeholder={t('offlinePoll.resultsEmailPlaceholder')} />
          </Form.Item>
        </Space>
      )}

      {/* Exam configuration fields */}
      {isExam && (
        <Space direction="vertical" style={{ width: '100%', marginBottom: 16 }}>
          <Form.Item
            name="exam_start_at"
            label={t('exam.startAt')}
            rules={[{ required: isExam, message: t('exam.startAtRequired') }]}
          >
            <DatePicker
              showTime
              style={{ width: '100%' }}
              disabledDate={(d) => d && d.isBefore(dayjs().startOf('day'))}
              disabledTime={(d) => {
                if (!d || !d.isSame(dayjs(), 'day')) return {}
                const now = dayjs()
                return {
                  disabledHours: () => Array.from({ length: now.hour() }, (_, i) => i),
                  disabledMinutes: (h) => h === now.hour() ? Array.from({ length: now.minute() }, (_, i) => i) : [],
                }
              }}
            />
          </Form.Item>
          <Form.Item
            name="exam_end_at"
            label={t('exam.endAt')}
            rules={[{ required: isExam, message: t('exam.endAtRequired') }]}
          >
            <DatePicker
              showTime
              style={{ width: '100%' }}
              disabledDate={(d) => {
                if (!d) return false
                const start = form.getFieldValue('exam_start_at')
                const floor = start ? start.startOf('day') : dayjs().startOf('day')
                return d.isBefore(floor)
              }}
              disabledTime={(d) => {
                if (!d) return {}
                const start = form.getFieldValue('exam_start_at')
                const ref = start && d.isSame(start, 'day') ? start : (d.isSame(dayjs(), 'day') ? dayjs() : null)
                if (!ref) return {}
                return {
                  disabledHours: () => Array.from({ length: ref.hour() }, (_, i) => i),
                  disabledMinutes: (h) => h === ref.hour() ? Array.from({ length: ref.minute() + 1 }, (_, i) => i) : [],
                }
              }}
            />
          </Form.Item>
          <Form.Item
            name="exam_time_limit_minutes"
            label={t('exam.timeLimitMinutes')}
          >
            <InputNumber min={1} max={600} placeholder={t('exam.timeLimitPlaceholder')} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="exam_require_email" valuePropName="checked">
            <Switch checkedChildren={t('exam.requireEmailOn')} unCheckedChildren={t('exam.requireEmailOff')} />
          </Form.Item>
          <Form.Item noStyle shouldUpdate={(prev, cur) => prev.exam_require_email !== cur.exam_require_email}>
            {({ getFieldValue }) => getFieldValue('exam_require_email') && (
              <Space direction="vertical" style={{ width: '100%' }}>
                <Alert
                  type="info"
                  showIcon
                  message={t('exam.requireEmailHint')}
                  style={{ marginTop: -8 }}
                />
                <Form.Item
                  name="exam_allowed_domains"
                  label={t('exam.allowedDomains', 'Allowed email domains (optional)')}
                  extra={t('exam.allowedDomainsHint', 'Comma-separated domains, e.g. natwest.com, rbs.com — leave blank to allow any email')}
                  style={{ marginBottom: 0 }}
                >
                  <Input placeholder={t('exam.allowedDomainsPlaceholder')} />
                </Form.Item>
              </Space>
            )}
          </Form.Item>
        </Space>
      )}
    </>
  )

  const dndSensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  )

  const renderQuestionsList = () => {
    const isLive = quiz?.status === 'ready' && isExam
    return (
    <>
      <Divider>{t('quiz.questions')}</Divider>

      {isLive && (
        <Alert
          type="info"
          showIcon
          message={t('exam.questionsLockedNotice')}
          style={{ marginBottom: 16 }}
        />
      )}

      {!isLive && editingQuestion !== 'new' && (
        <Button
          icon={<ThunderboltOutlined />}
          onClick={() => { setAiModalOpen(true); setAiStep('input'); setAiError(null) }}
          style={{ marginTop: 12, marginBottom: 8, width: '100%' }}
          size="large"
          disabled={!!editingQuestion}
        >
          {t('ai.generateWithAI')}
        </Button>
      )}

      {!isLive && (editingQuestion === 'new' ? (
        <MemoizedQuestionForm
          key="new-question"
          onSave={handleAddQuestion}
          onCancel={handleCancelQuestion}
          quizId={id}
          isPoll={isPoll}
          isExam={isExam}
          isOfflinePoll={isOfflinePoll}
          language={i18n.language}
          isAdmin={isAdmin}
          questionImageUrl={questionImageUrl}
          setQuestionImageUrl={setQuestionImageUrl}
          optionImages={optionImages}
          setOptionImages={setOptionImages}
          tempImages={tempImages}
          setTempImages={setTempImages}
          loading={loading}
          movingImages={movingImages}
          t={t}
        />
      ) : (
        <Button
          type="dashed"
          icon={<PlusOutlined />}
          onClick={() => setEditingQuestion('new')}
          style={{ marginTop: 12, marginBottom: 16, width: '100%' }}
          size="large"
          disabled={!!editingQuestion}
        >
          {t('quiz.addQuestion')}
        </Button>
      ))}

      <DndContext sensors={dndSensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={questions.map(q => q.id)} strategy={verticalListSortingStrategy}>
          {questions.map((question, index) => {
            return (
              <SortableItem key={question.id} id={question.id} disabled={!!editingQuestion || isLive || quiz?.status !== 'draft'}>
                {({ dragHandleProps }) => editingQuestion === question.id ? (
                  <MemoizedQuestionForm
                    key={`edit-question-${question.id}`}
                    question={question}
                    onSave={(values) => handleUpdateQuestion(question.id, values)}
                    onCancel={handleCancelQuestion}
                    quizId={id}
                    isPoll={isPoll}
                    isExam={isExam}
                    isOfflinePoll={isOfflinePoll}
                    language={i18n.language}
                    isAdmin={isAdmin}
                    questionImageUrl={questionImageUrl}
                    setQuestionImageUrl={setQuestionImageUrl}
                    optionImages={optionImages}
                    setOptionImages={setOptionImages}
                    tempImages={tempImages}
                    setTempImages={setTempImages}
                    loading={loading}
                    movingImages={movingImages}
                    t={t}
                  />
                ) : (
                  <Card
                    style={{ width: '100%' }}
                    title={
                      <Space>
                        {quiz?.status === 'draft' && !isLive && (
                          <Tooltip title={t('quiz.dragToReorder', 'Drag to reorder')}>
                            <span {...dragHandleProps} style={{ cursor: 'grab', color: '#999', display: 'inline-flex', alignItems: 'center' }}>
                              <HolderOutlined />
                            </span>
                          </Tooltip>
                        )}
                        <Tag color="blue">Q{index + 1}</Tag>
                        <Tag color={question.question_type === 'word_cloud' ? 'purple' : (question.question_type === 'mcq' ? 'cyan' : 'geekblue')}>
                          {getQuestionTypeLabel(question.question_type, t)}
                        </Tag>
                        {!isPoll && <Tag color="green">{t('quiz.pointsTag', { points: question.points || 1 })}</Tag>}
                        {question.max_time_seconds ? (
                          <Tag color="orange">{t('quiz.timerTag', { seconds: question.max_time_seconds })}</Tag>
                        ) : null}
                        {isOfflinePoll && question.is_required && (
                          <Tag color="red">{t('offlinePoll.required', 'Required')}</Tag>
                        )}
                        <Text strong>{stripHtml(question.text).slice(0, 80) || t('quiz.untitled', 'Untitled')}</Text>
                      </Space>
                    }
                    extra={
                      !isLive ? (
                      <Space>
                        <Button
                          size="small"
                          icon={<EditOutlined />}
                          onClick={() => setEditingQuestion(question.id)}
                          disabled={!!editingQuestion}
                        >
                          {t('common.edit')}
                        </Button>
                        {quiz?.status === 'draft' && (
                          <Tooltip title={t('quiz.duplicateQuestion', 'Duplicate question')}>
                            <Button
                              size="small"
                              icon={<CopyOutlined />}
                              onClick={() => handleDuplicateQuestion(question.id)}
                              disabled={!!editingQuestion || loading}
                            />
                          </Tooltip>
                        )}
                        <Popconfirm
                          title={t('quiz.deleteQuestionConfirm')}
                          onConfirm={() => handleDeleteQuestion(question.id)}
                          okText={t('common.submit')}
                          cancelText={t('common.cancel')}
                          disabled={!!editingQuestion}
                        >
                          <Button
                            size="small"
                            danger
                            icon={<DeleteOutlined />}
                            disabled={!!editingQuestion}
                          />
                        </Popconfirm>
                      </Space>
                      ) : null
                    }
                  >
              {question.question_type === 'word_cloud' ? (
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Text type="secondary" italic>
                    {t('quiz.wordCloudQuestionDescription')}
                  </Text>
                </Space>
              ) : question.question_type === 'one_word' ? (
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Text type="secondary" italic>
                    {t('quiz.oneWordDescription')}
                  </Text>
                </Space>
              ) : question.question_type === 'single_line' || question.question_type === 'paragraph' ? (
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Text type="secondary" italic>
                    {t('quiz.textResponseDescription')}
                  </Text>
                  <Text><strong>{t('quiz.expectedAnswerLabel')}:</strong> {question.expected_answer || question.options?.[0] || t('quiz.emptyValue')}</Text>
                </Space>
              ) : question.question_type === 'scale' ? (
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Text>{t('quiz.scaleOptionsLabel')}: {(question.options || ['1', '2', '3', '4', '5']).join(', ')}</Text>
                  {!isPoll && (
                    <Text><strong>{t('quiz.expectedAnswerLabel')}:</strong> {(question.options || [])[question.correct_answer_index ?? -1] || t('quiz.emptyValue')}</Text>
                  )}
                </Space>
              ) : (
                <Space direction="vertical" style={{ width: '100%' }}>
                  <RichTextRenderer content={question.text} />
                  {(() => {
                    const fallbackOptions = [
                      question.option_a,
                      question.option_b,
                      question.option_c,
                      question.option_d,
                      ...(question.extra_options || []),
                    ]
                    const mcqOptions = (Array.isArray(question.options) && question.options.length > 0
                      ? question.options
                      : fallbackOptions
                    )
                      .map((opt) => (typeof opt === 'string' ? opt.trim() : opt))
                      .filter(Boolean)

                    const answerToken = question.correct_answer
                    let correctIndex = Number.isInteger(question.correct_answer_index)
                      ? question.correct_answer_index
                      : (Number.isInteger(Number(answerToken)) ? Number(answerToken) : -1)

                    if (!Number.isInteger(question.correct_answer_index) && typeof answerToken === 'string') {
                      const letterIndex = answerToken.toUpperCase().charCodeAt(0) - 65
                      if (letterIndex >= 0) correctIndex = letterIndex
                    }

                    return mcqOptions.map((opt, idx) => {
                      const letter = String.fromCharCode(65 + idx)
                      return (
                        <div key={`${question.id}-opt-${idx}`} style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                          <Text style={{ whiteSpace: 'nowrap', paddingTop: 2 }}>{letter}:</Text>
                          <RichTextRenderer content={opt} style={{ flex: 1 }} />
                          {!isPoll && idx === correctIndex && <Tag color="green" style={{ flexShrink: 0 }}>{t('quiz.correct')}</Tag>}
                        </div>
                      )
                    })
                  })()}
                  {question.answer_explanation && (
                    <div style={{ marginTop: 4, padding: '6px 10px', background: '#fffbe6', borderLeft: '3px solid #faad14', borderRadius: 4 }}>
                      <Text style={{ fontSize: 12 }}>
                        <strong>💡 {t('quiz.answerExplanation', 'Explanation')}:</strong> {question.answer_explanation}
                      </Text>
                    </div>
                  )}
                </Space>
              )}
                  </Card>
                )}
              </SortableItem>
            )
          })}
        </SortableContext>
      </DndContext>
    </>
    )
  }

  const handleSkipSetup = async () => {
    setLoading(true)
    try {
      const response = await quizAPI.create({
        title: t('quiz.untitled', 'Untitled Quiz'),
        quiz_type: initialQuizType,
        skin: 'default',
        description: '',
      })
      navigate(`/quiz/${response.data.id}/edit?new=1`)
    } catch {
      message.error(t('quiz.saveError'))
    } finally {
      setLoading(false)
    }
  }

  const handleRailTitleSave = async () => {
    const trimmed = railTitleValue.trim()
    if (!trimmed || trimmed === quiz?.title) { setRailTitleEditing(false); return }
    try {
      await quizAPI.update(id, { title: trimmed })
      setQuiz(q => ({ ...q, title: trimmed }))
    } catch {
      message.error(t('quiz.saveError'))
    }
    setRailTitleEditing(false)
  }

  const handleAutoSave = useCallback(async (questionId, values) => {
    setSaveStatus('saving')
    try {
      const questionData = {
        question_type: values.question_type || 'mcq',
        text: values.text,
        points: values.points || 1,
        max_time_seconds: values.max_time_seconds ?? null,
        negative_points: values.negative_points ?? 0,
        is_required: values.is_required ?? false,
        answer_explanation: values.answer_explanation || null,
        question_video_url: values.question_video_url || null,
      }
      if (values.question_type === 'mcq') {
        const mcqOptions = [values.option_a, values.option_b, values.option_c, values.option_d, ...(values.extra_options || [])].filter(opt => stripHtml(opt).length > 0)
        if (mcqOptions.length < 2) { setSaveStatus('idle'); return }
        questionData.options = mcqOptions
        const selected = Number(values.correct_answer)
        questionData.correct_answer_index = isPoll ? null : selected
      } else if (values.question_type === 'scale') {
        questionData.options = ['1', '2', '3', '4', '5']
        questionData.correct_answer_index = isPoll ? null : Number(values.correct_answer)
      } else if (values.question_type === 'single_line' || values.question_type === 'paragraph') {
        questionData.options = isPoll || !values.expected_answer ? [] : [values.expected_answer]
        questionData.correct_answer_index = null
      } else {
        questionData.options = null
        questionData.correct_answer_index = null
      }
      await questionAPI.update(questionId, questionData)
      // Update local question state so rail status dots refresh without a full reload
      setQuestions(qs => qs.map(q => q.id === questionId ? { ...q, ...questionData } : q))
      setSaveStatus('saved')
      clearTimeout(saveStatusTimerRef.current)
      saveStatusTimerRef.current = setTimeout(() => setSaveStatus('idle'), 2000)
    } catch {
      lastFailedSaveRef.current = { questionId, values }
      setSaveStatus('error')
    }
  }, [isPoll])

  const handleRetryAutoSave = useCallback(() => {
    const failed = lastFailedSaveRef.current
    if (!failed) return
    handleAutoSave(failed.questionId, failed.values)
  }, [handleAutoSave])

  const handleNavigate = useCallback((direction) => {
    if (saveStatus === 'saving') return
    const currentIndex = questions.findIndex(q => q.id === editingQuestion)
    const nextIndex = currentIndex + direction
    if (nextIndex < 0 || nextIndex >= questions.length) return
    setEditingQuestion(questions[nextIndex].id)
    setStageView(null)
  }, [questions, editingQuestion])

  const handleSaveQuiz = async (rawValues) => {
    setLoading(true)
    // Serialize dayjs objects to ISO strings for the API
    const timeLimitMins = rawValues.exam_time_limit_minutes
    const values = {
      ...rawValues,
      quiz_type: !id ? initialQuizType : (rawValues.quiz_type || quiz?.quiz_type || initialQuizType || 'quiz'),
      offline_start_at: rawValues.offline_start_at?.toISOString() ?? null,
      offline_end_at: rawValues.offline_end_at?.toISOString() ?? null,
      exam_start_at: rawValues.exam_start_at?.toISOString() ?? null,
      exam_end_at: rawValues.exam_end_at?.toISOString() ?? null,
      exam_time_limit_seconds: timeLimitMins ? Number(timeLimitMins) * 60 : null,
      exam_allowed_domains: rawValues.exam_allowed_domains?.trim() || null,
    }
    delete values.exam_time_limit_minutes
    // Include proctoring policy in the same save (single unified request)
    if (id && proctoringPolicy !== null && (isExam || quiz?.quiz_type === 'offline_poll')) {
      // Normalise: write explicit { enabled: false } for every known rule that wasn't toggled on,
      // so the backend context_resolver never falls back to the permissive platform default.
      const ALL_RULE_IDS = [
        'fullscreen_enforce', 'tab_switch_detect', 'copy_paste_block', 'multi_tab_detect',
        'right_click_block', 'bot_signal_detect', 'honeypot_traps', 'question_randomization',
        'option_randomization', 'answer_timing_enforce', 'behavioral_biometrics',
        'browser_fingerprint_bind', 'ip_bind', 'steg_watermark', 'devtools_detect',
        'webcam_monitoring', 'canvas_rendering',
      ]
      const normalised = { ...proctoringPolicy, rules: { ...proctoringPolicy.rules } }
      for (const rid of ALL_RULE_IDS) {
        if (!normalised.rules[rid]) normalised.rules[rid] = { enabled: false }
      }
      values.proctoring_policy = normalised
    }
    try {
      if (id) {
        await quizAPI.update(id, values)
        message.success(isExam ? t('exam.saveSuccess') : isOfflinePoll ? t('quiz.saveOfflinePollSuccess') : isPoll ? t('quiz.savePollSuccess') : t('quiz.saveSuccess'))
        loadQuiz()
      } else {
        const response = await quizAPI.create(values)
        message.success(isExam ? t('exam.createSuccess') : isOfflinePoll ? t('quiz.createOfflinePollSuccess') : isPoll ? t('quiz.createPollSuccess') : t('quiz.createSuccess'))
        const editPath = aiPromptParam
          ? `/quiz/${response.data.id}/edit?ai_prompt=${encodeURIComponent(aiPromptParam)}&ai_count=${aiCountParam}`
          : savingForAI
            ? `/quiz/${response.data.id}/edit?ai_auto_open=1`
            : `/quiz/${response.data.id}/edit`
        setSavingForAI(false)
        navigate(editPath)
      }
    } catch (error) {
      let detail = error.response?.data?.detail;
      if (Array.isArray(detail)) {
        detail = detail.map(e => `${e.loc?.join('.')}: ${e.msg}`).join(', ');
      } else if (typeof detail === 'object') {
        detail = JSON.stringify(detail);
      }
      const errorMsg = detail || t('quiz.saveError');
      message.error(errorMsg)
      console.error('Save quiz error:', error.response?.data || error)
    } finally {
      setLoading(false)
    }
  }

  const handleAddQuestion = useCallback(async (values) => {
    if (!id) {
      message.warning(t('quiz.saveQuizFirst'))
      return
    }

    setLoading(true)
    try {
      // Transform frontend format to backend format
      const questionData = {
        question_type: values.question_type || 'mcq',
        text: values.text,
        points: values.points || 1,
        max_time_seconds: values.max_time_seconds ?? null,
        negative_points: values.negative_points ?? 0,
        is_required: values.is_required ?? false,
        answer_explanation: values.answer_explanation || null,
        question_video_url: values.question_video_url || null,
      }

      // Add options for choice-based question types
      if (values.question_type === 'mcq') {
        const mcqOptions = [
          values.option_a,
          values.option_b,
          values.option_c,
          values.option_d,
          ...(values.extra_options || []),
        ]
          .filter((opt) => stripHtml(opt).length > 0)
        if (mcqOptions.length < 2) {
          message.error(t('quiz.mcqMinOptions'))
          return
        }
        const lowerOpts = mcqOptions.map((o) => stripHtml(o).toLowerCase())
        if (lowerOpts.some((o, i) => lowerOpts.indexOf(o) !== i)) {
          message.error(t('quiz.mcqDuplicateOptions'))
          return
        }
        questionData.options = mcqOptions
        const selected = Number(values.correct_answer)
        questionData.correct_answer_index = isPoll ? null : selected
        if (!isPoll && (!Number.isInteger(selected) || selected < 0 || selected >= mcqOptions.length)) {
          message.error(t('quiz.correctAnswerRequired'))
          return
        }
      } else if (values.question_type === 'scale') {
        questionData.options = ['1', '2', '3', '4', '5']
        questionData.correct_answer_index = isPoll ? null : Number(values.correct_answer)
      } else if (values.question_type === 'single_line' || values.question_type === 'paragraph') {
        questionData.options = isPoll || !values.expected_answer ? [] : [values.expected_answer]
        questionData.correct_answer_index = null
      } else {
        questionData.options = null
        questionData.correct_answer_index = null
      }

      console.log('Adding question with data:', questionData)
      const response = await questionAPI.add(id, questionData)
      const newQuestion = response.data
      console.log('Question added, response:', newQuestion)
      
      // Check if we have temp images to move
      const hasTempImages = Object.values(tempImages).some(img => img !== null)
      
      if (hasTempImages) {
        console.log('Moving temp images to permanent location...')
        setMovingImages(true)
        
        try {
          // Build temp images array
          const tempImageList = []
          
          if (tempImages.question) {
            tempImageList.push({
              temp_key: tempImages.question.tempKey,
              image_type: 'question'
            })
          }
          
          if (tempImages.optionA) {
            tempImageList.push({
              temp_key: tempImages.optionA.tempKey,
              image_type: 'option_a'
            })
          }
          
          if (tempImages.optionB) {
            tempImageList.push({
              temp_key: tempImages.optionB.tempKey,
              image_type: 'option_b'
            })
          }
          
          if (tempImages.optionC) {
            tempImageList.push({
              temp_key: tempImages.optionC.tempKey,
              image_type: 'option_c'
            })
          }
          
          if (tempImages.optionD) {
            tempImageList.push({
              temp_key: tempImages.optionD.tempKey,
              image_type: 'option_d'
            })
          }
          
          // Move temp images
          await questionAPI.moveTempImages(id, newQuestion.id, tempImageList)
          console.log('Temp images moved successfully')
          
          // Clear temp state
          setTempImages({
            question: null,
            optionA: null,
            optionB: null,
            optionC: null,
            optionD: null
          })
          
        } catch (moveError) {
          console.error('Failed to move temp images:', moveError)
          message.error(t('quiz.moveImagesFailed'))
        } finally {
          setMovingImages(false)
        }
      }
      
      message.success(t('quiz.addQuestionSuccess'))
      console.log('Reloading quiz...')
      await loadQuiz()
      console.log('Quiz reloaded successfully')
      setEditingQuestion(null)
    } catch (error) {
      let detail = error.response?.data?.detail;
      if (Array.isArray(detail)) {
        detail = detail.map(e => `${e.loc?.join('.')}: ${e.msg}`).join(', ');
      } else if (typeof detail === 'object') {
        detail = JSON.stringify(detail);
      }
      const errorMsg = detail || t('quiz.addQuestionError');
      message.error(errorMsg)
      console.error('Add question error:', error.response?.data || error)
    } finally {
      setLoading(false)
    }
  }, [id, t, tempImages, loadQuiz, isPoll])
  
  const handleCancelQuestion = useCallback(async () => {
    // Clean up temp images if any
    const hasTempImages = Object.values(tempImages).some(img => img !== null)
    
    if (hasTempImages) {
      try {
        // Delete each temp image
        for (const [key, imgData] of Object.entries(tempImages)) {
          if (imgData) {
            const imageType = key === 'question' ? 'question' : 
                            key === 'optionA' ? 'option_a' :
                            key === 'optionB' ? 'option_b' :
                            key === 'optionC' ? 'option_c' : 'option_d'
            
            await questionAPI.deleteImage(id, null, imageType, imgData.tempKey)
          }
        }
        
        // Clear temp state
        setTempImages({
          question: null,
          optionA: null,
          optionB: null,
          optionC: null,
          optionD: null
        })
      } catch (error) {
        console.error('Failed to cleanup temp images:', error)
        // Continue anyway
      }
    }
    
    // Close editing
    setEditingQuestion(null)
  }, [tempImages, id])

  const handleUpdateQuestion = useCallback(async (questionId, values) => {
    setLoading(true)
    try {
      // Transform frontend format to backend format
      const questionData = {
        question_type: values.question_type || 'mcq',
        text: values.text,
        points: values.points || 1,
        max_time_seconds: values.max_time_seconds ?? null,
        negative_points: values.negative_points ?? 0,
        is_required: values.is_required ?? false,
        answer_explanation: values.answer_explanation || null,
        question_video_url: values.question_video_url || null,
      }

      // Add options for choice-based question types
      if (values.question_type === 'mcq') {
        const mcqOptions = [
          values.option_a,
          values.option_b,
          values.option_c,
          values.option_d,
          ...(values.extra_options || []),
        ]
          .filter((opt) => stripHtml(opt).length > 0)
        if (mcqOptions.length < 2) {
          message.error(t('quiz.mcqMinOptions'))
          return
        }
        const lowerOpts = mcqOptions.map((o) => stripHtml(o).toLowerCase())
        if (lowerOpts.some((o, i) => lowerOpts.indexOf(o) !== i)) {
          message.error(t('quiz.mcqDuplicateOptions'))
          return
        }
        questionData.options = mcqOptions
        const selected = Number(values.correct_answer)
        questionData.correct_answer_index = isPoll ? null : selected
        if (!isPoll && (!Number.isInteger(selected) || selected < 0 || selected >= mcqOptions.length)) {
          message.error(t('quiz.correctAnswerRequired'))
          return
        }
      } else if (values.question_type === 'scale') {
        questionData.options = ['1', '2', '3', '4', '5']
        questionData.correct_answer_index = isPoll ? null : Number(values.correct_answer)
      } else if (values.question_type === 'single_line' || values.question_type === 'paragraph') {
        questionData.options = isPoll || !values.expected_answer ? [] : [values.expected_answer]
        questionData.correct_answer_index = null
      } else {
        questionData.options = null
        questionData.correct_answer_index = null
      }

      await questionAPI.update(questionId, questionData)
      message.success(t('quiz.updateQuestionSuccess'))
      loadQuiz()
      setEditingQuestion(null)
    } catch (error) {
      let detail = error.response?.data?.detail;
      if (Array.isArray(detail)) {
        detail = detail.map(e => `${e.loc?.join('.')}: ${e.msg}`).join(', ');
      } else if (typeof detail === 'object') {
        detail = JSON.stringify(detail);
      }
      const errorMsg = detail || t('quiz.updateQuestionError');
      message.error(errorMsg)
      console.error('Update question error:', error.response?.data || error)
    } finally {
      setLoading(false)
    }
  }, [t, loadQuiz, isPoll])

  const handleDeleteQuestion = async (questionId) => {
    setLoading(true)
    try {
      await questionAPI.delete(questionId)
      message.success(t('quiz.deleteQuestionSuccess'))
      loadQuiz()
    } catch (error) {
      const errorMsg = error.response?.data?.detail || t('quiz.deleteQuestionError')
      message.error(errorMsg)
      console.error('Delete question error:', error.response?.data || error)
    } finally {
      setLoading(false)
    }
  }

  const handleMoveQuestion = async (index, direction) => {
    const newQuestions = [...questions]
    const swapIndex = index + direction
    if (swapIndex < 0 || swapIndex >= newQuestions.length) return
    ;[newQuestions[index], newQuestions[swapIndex]] = [newQuestions[swapIndex], newQuestions[index]]
    setQuestions(newQuestions)
    try {
      const questionOrders = newQuestions.map((q, i) => [q.id, i])
      await questionAPI.reorder(id, questionOrders)
    } catch (error) {
      message.error(t('quiz.saveError'))
      loadQuiz()
    }
  }

  const handleDragEnd = useCallback(async (event) => {
    const { active, over } = event
    if (!over || active.id === over.id) return
    const oldIndex = questions.findIndex(q => q.id === active.id)
    const newIndex = questions.findIndex(q => q.id === over.id)
    if (oldIndex === -1 || newIndex === -1) return
    const newQuestions = arrayMove(questions, oldIndex, newIndex)
    setQuestions(newQuestions)
    try {
      await questionAPI.reorder(id, newQuestions.map((q, i) => [q.id, i]))
    } catch {
      message.error(t('quiz.saveError'))
      loadQuiz()
    }
  }, [questions, id])

  const handleDuplicateQuestion = useCallback(async (questionId) => {
    setLoading(true)
    try {
      await questionAPI.duplicate(id, questionId)
      message.success(t('quiz.duplicateQuestionSuccess', 'Question duplicated'))
      await loadQuiz()
    } catch (e) {
      message.error(e.response?.data?.detail || t('quiz.duplicateQuestionFailed', 'Failed to duplicate question'))
    } finally {
      setLoading(false)
    }
  }, [id])

  const _doPublishExam = async (freshStart) => {
    setBatchConfirmModal({ open: false })
    setLoading(true)
    try {
      const res = await examAPI.publish(id, freshStart)
      setExamLinkModal({ open: true, url: res.data.exam_url })
      await loadQuiz()
    } catch (error) {
      message.error(error.response?.data?.detail || t('exam.publishError'))
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handlePublish = async () => {
    setLoading(true)
    try {
      // Automatically save current form values before publishing to ensure dates/settings are in the DB
      const currentValues = await form.validateFields()

      // Serialize dayjs objects to ISO strings for the API (copied from handleSaveQuiz)
      const timeLimitMins = currentValues.exam_time_limit_minutes
      const saveValues = {
        ...currentValues,
        offline_start_at: currentValues.offline_start_at?.toISOString() ?? null,
        offline_end_at: currentValues.offline_end_at?.toISOString() ?? null,
        exam_start_at: currentValues.exam_start_at?.toISOString() ?? null,
        exam_end_at: currentValues.exam_end_at?.toISOString() ?? null,
        exam_time_limit_seconds: timeLimitMins ? Number(timeLimitMins) * 60 : null,
      }
      delete saveValues.exam_time_limit_minutes

      // Perform the save
      if (id) {
        await quizAPI.update(id, saveValues)
      } else {
        const response = await quizAPI.create(saveValues)
        // If it was a new quiz, we need the ID to publish, but this branch
        // is unlikely as handlePublish is only shown when id exists and questions >= 1
        navigate(`/quiz/${response.data.id}/edit`)
        return // Stop here to let the navigation and state reload happen
      }

      if (isExam) {
        if (quiz?.has_previous_session) {
          // A previous batch exists — ask the host whether to continue or start fresh
          setLoading(false)
          setBatchConfirmModal({ open: true })
          return
        }
        const res = await examAPI.publish(id)
        setExamLinkModal({ open: true, url: res.data.exam_url })
        await loadQuiz()
      } else if (isOfflinePoll) {
        const res = await quizAPI.publishOffline(id)
        setPollLinkModal({ open: true, url: res.data.poll_url })
        await loadQuiz()
      } else {
        await quizAPI.publish(id)
        message.success(t('quiz.publishSuccess'))
        navigate(`/quiz/${id}/control`)
      }
    } catch (error) {
      if (error?.name === 'ValidationError') {
        message.warning(t('quiz.validationError', 'Please check all required fields before publishing'))
      } else {
        message.error(error.response?.data?.detail || (isExam ? t('exam.publishError') : t('quiz.publishError')))
        console.error(error)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleUnpublish = async () => {
    setLoading(true)
    try {
      if (isExam) {
        await examAPI.unpublish(id)
        message.success(t('exam.unpublishSuccess'))
      } else {
        await quizAPI.unpublish(id)
        message.success(t('quiz.unpublishSuccess'))
      }
      loadQuiz()
    } catch (error) {
      message.error(error.response?.data?.detail || (isExam ? t('exam.unpublishError') : t('quiz.unpublishError')))
      console.error(error)
    } finally {
      setLoading(false)
    }
  }
  
  const CONTENT_TYPE_HINTS = {
    code: "Format all code samples using appropriate HTML code blocks with the correct language class (e.g. language-python, language-sql, language-java). Every question with code must use <pre><code class='language-X'>.",
    sql: "All SQL queries and schemas must be in SQL code blocks. Show table structure as CREATE TABLE or SELECT examples.",
    math: "Use plain Unicode for mathematical expressions (e.g. ≥, ², √, π). Keep formulas readable as text without LaTeX.",
    visual: "For questions that refer to a diagram, chart, or map: describe the visual clearly in the question text and ask students to interpret or identify elements from it.",
  }

  const STYLE_HINTS = {
    upsc: "Style: UPSC Civil Services MCQ format. Test factual knowledge with 4 options, one clearly correct. Language: formal administrative/academic. Include statement-based questions ('Consider the following statements...').",
    jee: "Style: JEE (Joint Entrance Examination) format. Application-based, numerically focused where appropriate. Include numerical values in questions. Tricky distractors based on common calculation errors.",
    ielts: "Style: IELTS Academic MCQ format. Test reading comprehension, vocabulary, and inference. Academic English only. Answer options should be complete phrases.",
    cat: "Style: CAT (Common Admission Test) MBA entrance format. Focus on verbal ability, logical reasoning, or quantitative aptitude. Questions should have tricky distractors based on plausible misreadings.",
    gate: "Style: GATE (Graduate Aptitude Test in Engineering) format. Technically rigorous, precise wording, single correct answer. Questions may reference engineering principles, formulas, or diagrams.",
  }

  const DIFFICULTY_MAP = {
    easy: { points: 1, negative_points: 0, max_time_seconds: 45 },
    medium: { points: 2, negative_points: 0.5, max_time_seconds: 60 },
    hard: { points: 4, negative_points: 1, max_time_seconds: 90 },
  }

  const handleAiGenerate = async () => {
    if (!aiTopic.trim()) return
    setAiGenerating(true)
    setAiStreaming(false)
    setAiStreamCount(0)
    setAiError(null)
    setAiPreview([])
    setAiExamSuggDuration(null)
    setAiExamSuggProctoring(null)
    setAiExamSuggDismissed(false)

    const hint = CONTENT_TYPE_HINTS[aiContentType]
    const styleHint = STYLE_HINTS[aiStyle]
    const parts = [hint, styleHint, aiTopic.trim()].filter(Boolean)
    const effectivePrompt = parts.join('\n\n')
    const quizType = quiz?.quiz_type || initialQuizType || 'quiz'

    // Collect existing question texts for context-aware generation (P3-A)
    const existingQTexts = questions.length > 0
      ? questions.map(q => stripHtml(q.text || '').trim()).filter(Boolean)
      : null

    const abort = new AbortController()
    aiAbortRef.current = abort

    // Switch to preview step immediately so questions stream in
    setAiStep('preview')
    setAiStreaming(true)

    try {
      await aiAPI.streamGenerateQuestions(
        {
          prompt: effectivePrompt,
          count: aiCount,
          language: i18n.language,
          quiz_type: quizType,
          existing_questions: existingQTexts,
        },
        (q) => {
          setAiPreview(prev => [...prev, { ...q, selected: true }])
          setAiStreamCount(prev => prev + 1)
        },
        (doneEvent) => {
          setAiTitle(doneEvent.title || null)
          setAiDescription(doneEvent.description || null)
          setAiTitleDismissed(false)
          if (doneEvent.suggested_exam_duration_minutes != null) {
            setAiExamSuggDuration(doneEvent.suggested_exam_duration_minutes)
          }
          if (doneEvent.suggested_proctoring != null) {
            setAiExamSuggProctoring(doneEvent.suggested_proctoring)
          }
        },
        abort.signal,
      )
    } catch (err) {
      if (err.name === 'AbortError') {
        // User stopped — keep questions received so far
      } else {
        const msg = err.message || t('ai.generationFailed')
        if (msg === '__PROMPT_NOT_FOR_QUIZ__') {
          setAiError(t('ai.promptNotForQuiz'))
          setAiStep('input')
        } else {
          setAiError(msg)
          if (aiPreview.length === 0) setAiStep('input')
        }
      }
    } finally {
      setAiGenerating(false)
      setAiStreaming(false)
      aiAbortRef.current = null
    }
  }

  const handleAiStopStream = () => {
    aiAbortRef.current?.abort()
  }

  const handleAiAddSelected = async () => {
    const selected = aiPreview.filter(q => q.selected)
    if (selected.length === 0) return
    setAiAdding(true)
    try {
      // Apply title/description from AI if not dismissed
      if (!aiTitleDismissed && aiTitle && id) {
        const updatePayload = {}
        const currentTitle = form.getFieldValue('title')
        if (aiTitle && (!currentTitle || currentTitle === t('quiz.enterQuizTitle') || currentTitle === t('exam.enterExamTitle'))) {
          updatePayload.title = aiTitle
        }
        if (aiDescription) updatePayload.description = aiDescription
        if (Object.keys(updatePayload).length > 0) {
          try {
            await quizAPI.update(id, updatePayload)
          } catch {
            // Non-fatal: proceed even if title update fails
          }
        }
      }

      const difficultyValues = isExam ? (DIFFICULTY_MAP[aiDifficulty] || DIFFICULTY_MAP.medium) : null

      for (const q of selected) {
        const qType = q.question_type || 'mcq'

        if (qType === 'word_cloud') {
          await questionAPI.add(id, {
            question_type: 'word_cloud',
            text: q.text,
            options: null,
            correct_answer_index: null,
            answer_explanation: null,
            points: 1,
            max_time_seconds: null,
            from_ai: true,
          })
        } else if (qType === 'scale') {
          await questionAPI.add(id, {
            question_type: 'scale',
            text: q.text,
            options: ['1', '2', '3', '4', '5'],
            correct_answer_index: null,
            answer_explanation: null,
            points: 1,
            max_time_seconds: null,
            from_ai: true,
          })
        } else if (qType === 'paragraph') {
          await questionAPI.add(id, {
            question_type: 'paragraph',
            text: q.text,
            options: [],
            correct_answer_index: null,
            answer_explanation: null,
            points: 1,
            max_time_seconds: null,
            from_ai: true,
          })
        } else {
          // mcq (default)
          await questionAPI.add(id, {
            question_type: 'mcq',
            text: q.text,
            options: q.options,
            correct_answer_index: isPoll ? null : q.correct_answer_index,
            answer_explanation: q.explanation || null,
            points: difficultyValues ? difficultyValues.points : 1,
            negative_points: difficultyValues ? difficultyValues.negative_points : 0,
            max_time_seconds: difficultyValues ? difficultyValues.max_time_seconds : null,
            from_ai: true,
          })
        }
      }
      const imgHints = selected.filter(q => q.image_suggestion).length
      const optImgHints = selected.filter(q => q.option_image_suggestions?.some(Boolean)).length
      if (imgHints > 0) setAiImageHintCount(imgHints)
      if (optImgHints > 0) setAiOptionImageHintCount(optImgHints)
      message.success(t('ai.addedSuccess', { count: selected.length }))
      setAiModalOpen(false)
      setAiStep('input')
      setAiTopic('')
      setAiPreview([])
      setAiTitle(null)
      setAiDescription(null)
      await loadQuiz()
    } catch (err) {
      message.error(err.response?.data?.detail || t('quiz.aiAddFailed'))
    } finally {
      setAiAdding(false)
    }
  }

  const handleRegenerateOne = async (index) => {
    setRegeneratingIndex(index)
    try {
      const hint = CONTENT_TYPE_HINTS[aiContentType]
      const effectivePrompt = hint ? `${hint}\n\n${aiTopic.trim()}` : aiTopic.trim()
      const quizType = quiz?.quiz_type || initialQuizType || 'quiz'
      const existing = aiPreview[index]
      const contextNote = existing?.text
        ? `Replace the following question with a completely different one on the same topic. Do NOT repeat: "${existing.text.replace(/<[^>]*>/g, '').slice(0, 100)}".`
        : ''
      const res = await aiAPI.generateQuestions({
        prompt: contextNote ? `${contextNote}\n\n${effectivePrompt}` : effectivePrompt,
        count: 1,
        language: i18n.language,
        quiz_type: quizType,
      })
      const newQ = res.data.questions[0]
      if (newQ) {
        setAiPreview(prev => prev.map((item, idx) =>
          idx === index ? { ...newQ, selected: item.selected } : item
        ))
      }
    } catch {
      message.error(t('ai.generationFailed'))
    } finally {
      setRegeneratingIndex(null)
    }
  }

  const getQuizStatusTranslation = (status) => {
    const statusMap = {
      draft: 'statusDraft',
      ready: 'statusReady',
      archived: 'statusArchived'
    }
    return t(`quiz.${statusMap[status] || 'statusDraft'}`)
  }
  return (
    <div className={id ? 'qb-studio' : 'quiz-builder-page'} style={!id ? { padding: 24 } : undefined}>
      {id ? (
        /* ── Edit mode: sticky top bar ───────────────────────────── */
        <div className="qb-topbar">
          <div className="qb-topbar-breadcrumb">
            <Button type="text" size="small" icon={<LeftOutlined />} onClick={() => navigate('/dashboard')}>
              {t('quiz.backDashboard')}
            </Button>
          </div>
          {quiz && (
            <span className="qb-topbar-type-badge">
              {isExam ? t('exam.typeLabel') : isOfflinePoll ? t('offlinePoll.typeLabel', 'Poll') : isPoll ? t('quiz.poll', 'Online Poll') : t('quiz.quizTypeLabel', 'Online Quiz')}
            </span>
          )}
          <span className={`qb-save-status${saveStatus !== 'idle' ? ` qb-save-status--${saveStatus}` : ''}`}>
            {saveStatus === 'saving' ? 'Saving…'
              : saveStatus === 'saved' ? 'Saved ✓'
              : saveStatus === 'error' ? (
                <>⚠ Save failed — <button type="button" className="qb-retry-link" onClick={handleRetryAutoSave}>retry?</button></>
              ) : ''}
          </span>
          {quiz && quiz.status === 'draft' && questions.length >= 1 && (
            <Tooltip title={t('tooltip.publishQuiz')}>
              <Button type="primary" icon={<RocketOutlined />} onClick={handlePublish} loading={loading}>
                {isExam ? t('exam.publishActivate') : isOfflinePoll ? t('offlinePoll.publishActivate', 'Publish & Activate') : isPoll ? t('quiz.publishPoll') : t('quiz.publishQuiz')}
              </Button>
            </Tooltip>
          )}
          {quiz && quiz.status === 'ready' && !isOfflinePoll && !isExam && (
            <>
              <Button type="primary" icon={<RocketOutlined />} onClick={() => navigate(`/quiz/${id}/control`)}>
                {isPoll ? t('quiz.startPoll') : t('quiz.startSession')}
              </Button>
              <Tooltip title={t('tooltip.unpublishQuiz')}>
                <Button type="default" onClick={handleUnpublish} loading={loading}>
                  {isPoll ? t('quiz.unpublishPoll') : t('quiz.unpublishQuiz')}
                </Button>
              </Tooltip>
            </>
          )}
          {quiz && quiz.status === 'ready' && isOfflinePoll && quiz.poll_slug && (
            <Tooltip title={t('tooltip.copyShareLink')}>
              <Button icon={<ShareAltOutlined />} onClick={() => setPollLinkModal({ open: true, url: `${window.location.origin}/poll/${quiz.poll_slug}` })}>
                {t('offlinePoll.copyLink', 'Copy Link')}
              </Button>
            </Tooltip>
          )}
          {quiz && quiz.status === 'ready' && isOfflinePoll && (
            <>
              <Button onClick={() => navigate(`/quiz/${id}/offline-results`)}>
                {t('offlinePoll.viewResults', 'View Results')}
              </Button>
              <Tooltip title={t('tooltip.unpublishQuiz')}>
                <Button type="default" onClick={handleUnpublish} loading={loading}>
                  {t('quiz.unpublishPoll')}
                </Button>
              </Tooltip>
            </>
          )}
          {quiz && quiz.status === 'ready' && isExam && quiz.exam_slug && (
            <Tooltip title={t('tooltip.copyShareLink')}>
              <Button icon={<ShareAltOutlined />} onClick={() => setExamLinkModal({ open: true, url: `${window.location.origin}/e/${quiz.exam_slug}` })}>
                {t('exam.copyLink')}
              </Button>
            </Tooltip>
          )}
          {quiz && quiz.status === 'ready' && isExam && (
            <>
              <Button onClick={() => navigate(`/quiz/${id}/exam-results`)}>
                {t('exam.resultsTitle')}
              </Button>
              <Tooltip title={t('tooltip.unpublishQuiz')}>
                <Button type="default" onClick={handleUnpublish} loading={loading}>
                  {t('exam.unpublishExam')}
                </Button>
              </Tooltip>
            </>
          )}
        </div>
      ) : (
        /* ── Create mode: original topbar ───────────────────────── */
        <Space wrap className="quiz-builder-topbar">
          <Button icon={<LeftOutlined />} onClick={() => navigate('/dashboard')}>
            {t('quiz.backDashboard')}
          </Button>
          {isExam && (
            <Button disabled={isValidating} icon={<DownloadOutlined />} onClick={handleDownloadTemplate}>
              {t('quiz.downloadTemplate')}
            </Button>
          )}
        </Space>
      )}

      {aiImageHintCount > 0 && (
        <Alert type="info" showIcon closable onClose={() => setAiImageHintCount(0)}
          message={t('ai.imageHintBanner', { count: aiImageHintCount, defaultValue: `${aiImageHintCount} question(s) were suggested with images. Open each question to upload the image.` })}
          style={id ? { margin: '0 20px 12px' } : { marginTop: 12 }}
        />
      )}
      {aiOptionImageHintCount > 0 && (
        <Alert type="info" showIcon closable onClose={() => setAiOptionImageHintCount(0)}
          message={t('ai.optionImageHintBanner', { count: aiOptionImageHintCount, defaultValue: `${aiOptionImageHintCount} question(s) were suggested with image options. Open each question to upload a photo per option.` })}
          style={id ? { margin: '0 20px 8px' } : { marginTop: 8 }}
        />
      )}

      {!id ? (
        <Card bordered={false} className="premium-builder-card shadow-sm" style={{ marginTop: 24 }}>
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            type="card"
            items={[
              {
                key: '1',
                label: t('quiz.fillOnline'),
                children: (
                  <div style={{ padding: '16px 0' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                      <Text type="secondary">
                         {isExam ? t('exam.typeInfo') : isOfflinePoll ? t('offlinePoll.typeInfo') : isPoll ? t('quiz.pollTypeInfo') : t('quiz.quizTypeInfo')}
                      </Text>
                      {isExam && (
                        <Button
                          icon={<DownloadOutlined />}
                          onClick={handleDownloadDraft}
                          disabled={!questions.length && !form.getFieldValue('title')}
                        >
                          {t('quiz.downloadDraftExcel')}
                        </Button>
                      )}
                    </div>
                    
                    <Form
                      form={form}
                      layout="vertical"
                      onFinish={handleSaveQuiz}
                      initialValues={{
                        quiz_type: initialQuizType,
                        exam_time_limit_minutes: 30
                      }}
                    >
                      {renderQuizSettings()}
                      
                      <div style={{ marginTop: 24, display: 'flex', justifyContent: 'center', gap: 12, flexWrap: 'wrap' }}>
                        <Button
                          type="primary"
                          size="large"
                          htmlType="submit"
                          icon={<SaveOutlined />}
                          loading={loading && !savingForAI}
                          style={{ minWidth: 180 }}
                        >
                          {isExam ? t('exam.createExam') : isOfflinePoll ? t('offlinePoll.createOfflinePoll', 'Create Offline Poll') : isPoll ? t('quiz.createPoll') : t('quiz.createQuiz')}
                        </Button>
                        <Button
                          size="large"
                          icon={<ThunderboltOutlined />}
                          loading={loading && savingForAI}
                          onClick={() => {
                            if (!form.getFieldValue('title')?.trim()) {
                              form.setFieldsValue({ title: t('quiz.untitled', 'Untitled') })
                            }
                            setSavingForAI(true)
                            form.submit()
                          }}
                          style={{ minWidth: 180 }}
                        >
                          {t('ai.generateWithAI')}
                        </Button>
                      </div>
                      <div style={{ marginTop: 16, textAlign: 'center' }}>
                        <button type="button" className="qb-skip-link" onClick={handleSkipSetup} disabled={loading}>
                          {t('quiz.skipSetup', 'or skip setup and start adding questions →')}
                        </button>
                      </div>
                    </Form>
                  </div>
                )
              },
              ...(isExam ? [{
                key: '2',
                label: t('quiz.uploadExcelTab'),
                children: (
                  <div style={{ padding: '24px 0' }}>
                    {!importData ? (
                      <div style={{ textAlign: 'center', padding: '40px 0' }}>
                        <Upload.Dragger
                          name="file"
                          multiple={false}
                          accept=".xlsx,.xls"
                          showUploadList={false}
                          customRequest={({ file, onSuccess }) => {
                            setTimeout(() => onSuccess("ok"), 0);
                          }}
                          onChange={handleExcelUpload}
                          disabled={isValidating}
                        >
                          <p className="ant-upload-drag-icon">
                            {isValidating ? <LoadingOutlined spin /> : <InboxOutlined />}
                          </p>
                          <p className="ant-upload-text">{t('quiz.uploadExcelFile')}</p>
                          <p className="ant-upload-hint">
                            {t('quiz.excelHint')}
                          </p>
                        </Upload.Dragger>
                        
                        <div style={{ marginTop: 32 }}>
                          <Button size="large" onClick={handleDownloadDraft} icon={<DownloadOutlined />} style={{ marginRight: 16 }}>
                            {t('quiz.downloadDraftExcel')}
                          </Button>
                          <Button size="large" onClick={handleDownloadTemplate} icon={<DownloadOutlined />}>
                            {t('quiz.downloadTemplate')}
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div className="import-preview-section">
                        <Alert
                          message={importData.canImport ? t('quiz.canImport') : t('quiz.hasErrors')}
                          type={importData.canImport ? "success" : "error"}
                          showIcon
                          icon={importData.canImport ? <CheckCircleOutlined /> : <ExclamationCircleOutlined />}
                          action={
                            <Space>
                              <Button size="small" onClick={() => setImportData(null)}>
                                {t('common.cancel')}
                              </Button>
                              <Button 
                                size="small" 
                                type="primary" 
                                disabled={!importData.canImport}
                                loading={isImporting}
                                onClick={handleFinalizeImport}
                              >
                                {t('quiz.finalizeImport')}
                              </Button>
                            </Space>
                          }
                          style={{ marginBottom: 24 }}
                        />
                        
                        <ProCard title={t('quiz.importPreview')} bordered headerBordered ghost>
                           <div style={{ marginBottom: 24 }}>
                             <Space direction="vertical" style={{ width: '100%' }}>
                               <div><Text strong>{t('quiz.quizTitle')}: </Text><Text>{importData.title}</Text></div>
                               {importData.description && (
                                 <div><Text strong>{t('quiz.quizDescription')}: </Text><Text>{importData.description}</Text></div>
                               )}
                               <Space size="middle">
                                 {(() => { const c = importData.quiz_type === 'exam' ? '#059669' : importData.quiz_type === 'offline_poll' ? '#DB2777' : importData.quiz_type === 'poll' ? '#EA580C' : '#4F46E5'; return (
                                   <Tag style={{ background: `${c}15`, borderColor: `${c}50`, color: c }}>
                                     {importData.quiz_type === 'exam' ? t('exam.typeLabel') : importData.quiz_type === 'offline_poll' ? t('offlinePoll.typeLabel', 'Poll') : importData.quiz_type === 'poll' ? t('quiz.poll', 'Online Poll') : t('quiz.quizTypeLabel', 'Online Quiz')}
                                   </Tag>
                                 )})()}
                                 <Tag color="blue">{importData.questions?.length} {t('quiz.questions')}</Tag>
                                 {importData.quiz_type === 'exam' && importData.duration_minutes && (
                                   <Tag color="orange">{importData.duration_minutes} {t('exam.timeLimitMinutes')}</Tag>
                                 )}
                               </Space>
                             </Space>
                           </div>

                           <Table
                             dataSource={importData.questions}
                             rowKey="index"
                             pagination={false}
                             scroll={{ y: 500 }}
                             columns={[
                               { 
                                 title: '#', 
                                 dataIndex: 'index', 
                                 width: 60 
                               },
                               { 
                                 title: t('quiz.question'), 
                                 dataIndex: 'text',
                                 render: (text, record) => (
                                   <div>
                                     <div style={{ marginBottom: 4 }}>{text}</div>
                                     {record.errors?.map((err, i) => (
                                       <Tag key={i} color="error" style={{ fontSize: '11px', whiteSpace: 'normal' }}>{err}</Tag>
                                     ))}
                                   </div>
                                 )
                               },
                               { 
                                 title: t('quiz.questionType'), 
                                 dataIndex: 'type',
                                 width: 130,
                                 render: (type) => <Tag color={type === 'MCQ' ? 'cyan' : 'green'}>{type}</Tag>
                               },
                               { 
                                 title: t('quiz.answer'), 
                                 dataIndex: 'answer',
                                 width: 120,
                                 render: (ans) => <Tag color="gold">{ans}</Tag>
                               },
                               {
                                 title: t('common.status'),
                                 dataIndex: 'isValid',
                                 width: 100,
                                 render: (isValid) => (
                                   isValid ? <Tag color="success">{t('quiz.importValidTag')}</Tag> : <Tag color="error">{t('quiz.importErrorTag')}</Tag>
                                 )
                               }
                             ]}
                           />
                        </ProCard>
                      </div>
                    )}
                  </div>
                )
              }] : [])
            ]}
          />
        </Card>
      ) : (
        /* Edit Mode: Two-Pane Studio */
        <div className="qb-body">
          <div className={`qb-rail${mobileView === 'form' ? ' qb-rail--mobile-hidden' : ''}`}>
            <div className="qb-rail-header">
              <div className="qb-rail-tree-root">
                <FolderFilled className="qb-rail-folder-icon" />
                {railTitleEditing ? (
                  <input
                    className="qb-rail-title-input"
                    value={railTitleValue}
                    autoFocus
                    onChange={e => setRailTitleValue(e.target.value)}
                    onBlur={handleRailTitleSave}
                    onKeyDown={e => { if (e.key === 'Enter') e.target.blur(); if (e.key === 'Escape') setRailTitleEditing(false) }}
                  />
                ) : (
                  <span
                    className="qb-rail-title"
                    title={t('quiz.clickToRename', 'Click to rename')}
                    onClick={() => { setRailTitleValue(quiz?.title || ''); setRailTitleEditing(true) }}
                  >
                    {quiz?.title || '…'}
                  </span>
                )}
              </div>
            </div>
            <div className="qb-rail-list">
              {/* Setup entry */}
              <div
                className={`qb-rail-entry${stageView === 'setup' ? ' qb-rail-entry--active' : ''}`}
                onClick={() => { setStageView('setup'); setEditingQuestion(null); setMobileView('form') }}
              >
                ⚙ {t('quiz.setupLabel', 'Setup')}
              </div>
              {/* Proctoring entry — exam only */}
              {isExam && (
                <div
                  className={`qb-rail-entry${stageView === 'proctoring' ? ' qb-rail-entry--active' : ''}`}
                  onClick={() => { setStageView('proctoring'); setEditingQuestion(null); setMobileView('form') }}
                >
                  🔒 {t('quiz.securityLabel', 'Security & Proctoring')}
                </div>
              )}
              {quiz?.status === 'ready' && isExam && (
                <div style={{ padding: '8px 10px', fontSize: 11, color: '#fa8c16', background: '#fff7e6', borderRadius: 6, margin: '4px 0 8px' }}>
                  {t('exam.questionsLockedNotice')}
                </div>
              )}
              {/* Filter toggle — shown when there are incomplete questions */}
              {(() => {
                const incompleteCount = questions.filter(q => {
                  const hasText = !!stripHtml(q.text).trim()
                  const hasCa = Number.isInteger(q.correct_answer_index) && q.correct_answer_index >= 0
                  const needsCa = q.question_type === 'mcq' && !isPoll
                  return !hasText || (needsCa && !hasCa)
                }).length
                if (incompleteCount === 0) return null
                return (
                  <div className="qb-rail-filter">
                    <button type="button" className={`qb-rail-filter-btn${railFilter === 'all' ? ' qb-rail-filter-btn--active' : ''}`} onClick={() => setRailFilter('all')}>
                      {t('quiz.filterAll', 'All')}
                    </button>
                    <button type="button" className={`qb-rail-filter-btn${railFilter === 'incomplete' ? ' qb-rail-filter-btn--active' : ''}`} onClick={() => setRailFilter('incomplete')}>
                      {t('quiz.filterIncomplete', 'Incomplete')} ({incompleteCount})
                    </button>
                  </div>
                )
              })()}
              <DndContext sensors={dndSensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                <SortableContext items={questions.map(q => q.id)} strategy={verticalListSortingStrategy}>
                  {questions.map((question, index) => {
                    const hasText = !!stripHtml(question.text).trim()
                    const hasCa = !Number.isInteger(question.correct_answer_index) ? false : question.correct_answer_index >= 0
                    const needsCa = question.question_type === 'mcq' && !isPoll
                    const statusCls = !hasText ? 'qb-q-status-dot--empty' : (needsCa && !hasCa) ? 'qb-q-status-dot--warn' : 'qb-q-status-dot--ok'
                    const isIncomplete = !hasText || (needsCa && !hasCa)
                    if (railFilter === 'incomplete' && !isIncomplete) return null
                    const isActive = editingQuestion === question.id
                    const isDraftQuiz = quiz?.status === 'draft'
                    return (
                      <SortableItem
                        key={question.id}
                        id={question.id}
                        disabled={!isDraftQuiz || !!(editingQuestion && editingQuestion !== question.id)}
                        marginBottom={0}
                      >
                        {({ dragHandleProps }) => (
                          <div
                            className={`qb-q-card${isActive ? ' qb-q-card--active' : ''}`}
                            onClick={() => { setEditingQuestion(question.id); setStageView(null); setMobileView('form') }}
                          >
                            {isDraftQuiz && (
                              <span className="qb-q-drag-handle" {...dragHandleProps}>⠿</span>
                            )}
                            <div className="qb-q-card-body">
                              <div className="qb-q-card-meta">
                                <FileTextOutlined className="qb-q-file-icon" />
                                <span className="qb-q-num">Q{index + 1}</span>
                                <span className="qb-q-type-tag">{getQuestionTypeLabel(question.question_type, t)}</span>
                                <span className={`qb-q-status-dot ${statusCls}`} />
                                {question.points !== undefined && question.points !== 1 && (
                                  <span className="qb-q-chip">★{question.points}</span>
                                )}
                                {question.max_time_seconds && (
                                  <span className="qb-q-chip">⏱{question.max_time_seconds}s</span>
                                )}
                              </div>
                              <div className="qb-q-preview">
                                {stripHtml(question.text).slice(0, 40) || t('quiz.untitled', 'Untitled')}
                              </div>
                            </div>
                          </div>
                        )}
                      </SortableItem>
                    )
                  })}
                </SortableContext>
              </DndContext>
              {questions.length === 0 && (
                <div style={{ padding: '24px 12px', textAlign: 'center', fontSize: 12, color: '#aaa' }}>
                  {t('quiz.addFirstQuestion', 'No questions yet — add one below')}
                </div>
              )}
            </div>
            <div className="qb-rail-footer">
              {!(quiz?.status === 'ready' && isExam) && (
                <>
                  <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    block
                    onClick={() => { setEditingQuestion('new'); setStageView(null); setMobileView('form') }}
                  >
                    {t('quiz.addQuestion')}
                  </Button>
                  <Button
                    icon={<ThunderboltOutlined />}
                    block
                    onClick={() => { setAiModalOpen(true); setAiStep('input'); setAiError(null) }}
                  >
                    {t('ai.generateWithAI')}
                  </Button>
                </>
              )}
            </div>
          </div>

          {/* Right stage — all existing edit content */}
          <div className={`qb-stage${mobileView === 'list' ? ' qb-stage--mobile-hidden' : ''}`}>
            {/* Mobile-only back button */}
            <Button
              className="qb-mobile-back"
              type="text"
              icon={<LeftOutlined />}
              onClick={() => { setMobileView('list'); setEditingQuestion(null) }}
              style={{ display: 'none', marginBottom: 12 }}
            >
              {t('quiz.allQuestions', 'All questions')}
            </Button>
            {/* Stage content driven by stageView or editingQuestion */}
            {stageView === 'setup' ? (
              /* ── Setup panel ── */
              <>
                {quiz && (
                  <Space style={{ marginBottom: 12 }}>
                    <Tag color={quiz.status === 'draft' ? 'orange' : 'green'}>{getQuizStatusTranslation(quiz.status)}</Tag>
                    {(() => {
                      const modeColor = quiz.quiz_type === 'exam' ? '#059669' : quiz.quiz_type === 'offline_poll' ? '#DB2777' : quiz.quiz_type === 'poll' ? '#EA580C' : '#4F46E5'
                      return (
                        <Tag style={{ background: `${modeColor}15`, borderColor: `${modeColor}50`, color: modeColor }}>
                          {quiz.quiz_type === 'exam' ? t('exam.typeLabel') : quiz.quiz_type === 'offline_poll' ? t('offlinePoll.typeLabel', 'Poll') : quiz.quiz_type === 'poll' ? t('quiz.poll', 'Online Poll') : t('quiz.quizTypeLabel', 'Online Quiz')}
                        </Tag>
                      )
                    })()}
                  </Space>
                )}
                <Card
                  title={t('quiz.settingsCardTitle')}
                  style={{ marginBottom: 24 }}
                  extra={
                    !isLiveMode && (
                      <Button type="primary" onClick={() => form.submit()} icon={<SaveOutlined />} loading={loading}>
                        {isExam ? t('exam.saveSettings') : isOfflinePoll ? t('offlinePoll.updateOfflinePoll', 'Update Offline Poll') : isPoll ? t('quiz.updatePoll') : t('quiz.editQuiz')}
                      </Button>
                    )
                  }
                >
                  {isLiveMode && (
                    <Alert
                      type="info"
                      showIcon
                      style={{ marginBottom: 16 }}
                      message={t('quiz.unpublishToEditBannerTitle', isExam ? '✏️ Unpublish to edit settings' : '✏️ Unpublish → Edit → Republish')}
                      description={t('quiz.unpublishToEditBannerDesc', isExam ? 'This test is live. Unpublish it to make changes, then republish when ready.' : 'This activity is published and live. Unpublish it to edit settings, then republish when ready.')}
                      action={
                        <Button type="primary" size="small" loading={loading} onClick={handleUnpublish}>
                          {isExam ? t('exam.unpublishExam') : isPoll ? t('quiz.unpublishPoll') : t('quiz.unpublishQuiz')}
                        </Button>
                      }
                    />
                  )}
                  <Form form={form} layout="vertical" onFinish={handleSaveQuiz} disabled={isLiveMode}>
                    {renderQuizSettings()}
                  </Form>
                </Card>
              </>
            ) : stageView === 'proctoring' ? (
              /* ── Security & Proctoring panel ── */
              <div style={{ marginBottom: 24 }}>
                {id && proctoringPolicy !== null ? (
                  <ProctoringSettings
                    quizId={parseInt(id)}
                    quizType={quiz?.quiz_type}
                    tenantTier={currentUser?.tier || 'free'}
                    currentPolicy={proctoringPolicy}
                    onChange={(p) => setProctoringPolicy(p)}
                  />
                ) : (
                  <Card style={{ marginTop: 16 }}>
                    <Text type="secondary">{t('quiz.proctoringLoadingNote', 'Proctoring settings will appear here once the activity is saved.')}</Text>
                  </Card>
                )}
              </div>
            ) : editingQuestion === 'new' ? (
              /* ── New question form ── */
              <MemoizedQuestionForm
                key="new-question"
                onSave={handleAddQuestion}
                onCancel={handleCancelQuestion}
                quizId={id}
                isPoll={isPoll}
                isExam={isExam}
                isOfflinePoll={isOfflinePoll}
                language={i18n.language}
                isAdmin={isAdmin}
                questionImageUrl={questionImageUrl}
                setQuestionImageUrl={setQuestionImageUrl}
                optionImages={optionImages}
                setOptionImages={setOptionImages}
                tempImages={tempImages}
                setTempImages={setTempImages}
                loading={loading}
                movingImages={movingImages}
                t={t}
              />
            ) : editingQuestion ? (
              /* ── Edit question form ── */
              (() => {
                const q = questions.find(q => q.id === editingQuestion)
                const qIndex = questions.findIndex(q => q.id === editingQuestion)
                if (!q) return null
                return (
                  <MemoizedQuestionForm
                    key={`edit-${q.id}`}
                    question={q}
                    questionIndex={qIndex}
                    totalQuestions={questions.length}
                    onSave={(values) => handleUpdateQuestion(q.id, values)}
                    onAutoSave={handleAutoSave}
                    onNavigate={handleNavigate}
                    onCancel={handleCancelQuestion}
                    quizId={id}
                    isPoll={isPoll}
                    isExam={isExam}
                    isOfflinePoll={isOfflinePoll}
                    language={i18n.language}
                    isAdmin={isAdmin}
                    questionImageUrl={questionImageUrl}
                    setQuestionImageUrl={setQuestionImageUrl}
                    optionImages={optionImages}
                    setOptionImages={setOptionImages}
                    tempImages={tempImages}
                    setTempImages={setTempImages}
                    loading={loading}
                    movingImages={movingImages}
                    t={t}
                  />
                )
              })()
            ) : (
              /* ── Empty state ── */
              <div className="qb-stage-empty">
                <div className="qb-stage-empty-icon">✏️</div>
                <div>
                  {questions.length === 0
                    ? t('quiz.addFirstQuestion', 'Add your first question using the button below')
                    : t('quiz.selectQuestion', 'Select a question on the left to edit it')}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Poll link modal for offline polls */}
      <Modal
        title={t('offlinePoll.publishActivate', 'Poll Published!')}
        open={pollLinkModal.open}
        onCancel={() => setPollLinkModal({ open: false, url: '' })}
        footer={[
          <Button key="close" onClick={() => setPollLinkModal({ open: false, url: '' })}>
            {t('common.cancel')}
          </Button>
        ]}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Text>{t('quiz.pollActiveBanner')}</Text>
          <Text
            strong
            copyable={{ text: pollLinkModal.url, icon: <CopyOutlined />, tooltips: [t('offlinePoll.copyLink', 'Copy Link'), t('offlinePoll.linkCopied', 'Link copied!')] }}
            style={{ wordBreak: 'break-all' }}
          >
            {pollLinkModal.url}
          </Text>
        </Space>
      </Modal>

      {/* Batch continuity confirm modal */}
      <Modal
        title={t('exam.batchConfirmTitle')}
        open={batchConfirmModal.open}
        onCancel={() => setBatchConfirmModal({ open: false })}
        footer={[
          <Button key="fresh" danger onClick={() => _doPublishExam(true)} loading={loading}>
            {t('exam.startFresh')}
          </Button>,
          <Button key="continue" type="primary" onClick={() => _doPublishExam(false)} loading={loading}>
            {t('exam.continueLeaderboard')}
          </Button>,
        ]}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Alert
            type="info"
            showIcon
            message={t('exam.batchConfirmDesc')}
          />
          <Text type="secondary">{t('exam.batchConfirmHint')}</Text>
        </Space>
      </Modal>

      {/* Exam link modal */}
      <Modal
        title={t('exam.publishSuccess')}
        open={examLinkModal.open}
        onCancel={() => setExamLinkModal({ open: false, url: '' })}
        footer={[
          <Button key="results" type="primary" onClick={() => { setExamLinkModal({ open: false, url: '' }); navigate(`/quiz/${id}/exam-results`) }}>
            {t('exam.resultsTitle')}
          </Button>,
          <Button key="close" onClick={() => setExamLinkModal({ open: false, url: '' })}>
            {t('common.cancel')}
          </Button>
        ]}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Text>{t('quiz.examActiveBanner')}</Text>
          <Text
            strong
            copyable={{ text: examLinkModal.url, icon: <CopyOutlined />, tooltips: [t('exam.copyLink'), t('exam.linkCopied')] }}
            style={{ wordBreak: 'break-all' }}
          >
            {examLinkModal.url}
          </Text>
        </Space>
      </Modal>

      {/* AI Generate Questions Modal */}
      <Modal
        title={<Space><ThunderboltOutlined />{t('ai.generateQuestionsTitle')}</Space>}
        open={aiModalOpen}
        onCancel={() => { setAiModalOpen(false); setAiStep('input'); setAiPreview([]); setAiError(null) }}
        footer={null}
        width={680}
      >
        {aiStep === 'input' && (
          <Space direction="vertical" style={{ width: '100%' }} size={16}>
            {questions.length > 0 && (
              <Alert
                type="info"
                showIcon
                message={t('ai.existingContextNotice', { count: questions.length })}
                style={{ marginBottom: 0 }}
              />
            )}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <Text strong>{t('ai.promptLabel')}</Text>
                {('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) && (
                  <Tooltip title={voiceListening ? t('ai.voiceStop') : t('ai.voiceStart')}>
                    <Button
                      size="small"
                      type={voiceListening ? 'primary' : 'default'}
                      danger={voiceListening}
                      icon={<span role="img" aria-label="mic">{voiceListening ? '🔴' : '🎤'}</span>}
                      onClick={() => {
                        if (voiceListening) {
                          recognizerRef.current?.stop()
                          recognizerRef.current = null
                          setVoiceListening(false)
                          return
                        }
                        const SR = window.SpeechRecognition || window.webkitSpeechRecognition
                        if (!SR) return
                        const recognizer = new SR()
                        recognizerRef.current = recognizer
                        recognizer.lang = i18n.language || 'en-US'
                        recognizer.continuous = false
                        recognizer.interimResults = false
                        recognizer.onresult = (e) => {
                          const transcript = e.results[0]?.[0]?.transcript || ''
                          if (transcript) setAiTopic(prev => prev ? `${prev} ${transcript}` : transcript)
                        }
                        recognizer.onend = () => { recognizerRef.current = null; setVoiceListening(false) }
                        recognizer.onerror = (ev) => {
                          recognizerRef.current = null
                          setVoiceListening(false)
                          if (ev.error === 'not-allowed') {
                            antMessage.error(t('quiz.voiceMicBlocked'))
                          } else if (ev.error === 'no-speech') {
                            antMessage.warning(t('quiz.voiceNoSpeech'))
                          } else if (ev.error === 'network') {
                            antMessage.error(t('quiz.voiceNetworkError'))
                          } else {
                            antMessage.error(t('quiz.voiceError', { error: ev.error || 'unknown' }))
                          }
                        }
                        try {
                          recognizer.start()
                          setVoiceListening(true)
                        } catch (err) {
                          recognizerRef.current = null
                          antMessage.error(t('quiz.voiceStartError', { error: err?.message || err }))
                        }
                      }}
                    />
                  </Tooltip>
                )}
              </div>
              <Text type="secondary" style={{ display: 'block', fontSize: 12, marginBottom: 6 }}>
                {t('ai.promptHint')}
              </Text>
              <Input.TextArea
                placeholder={t('ai.promptPlaceholder')}
                value={aiTopic}
                onChange={e => setAiTopic(e.target.value)}
                rows={9}
                autoSize={{ minRows: 9, maxRows: 16 }}
                style={{ marginTop: 2, fontFamily: 'inherit', fontSize: 14, borderColor: voiceListening ? '#ff4d4f' : undefined }}
                autoFocus
                showCount
                maxLength={5000}
              />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
              <Text strong style={{ whiteSpace: 'nowrap' }}>{t('ai.numberOfQuestions')}</Text>
              <InputNumber
                min={1}
                max={50}
                value={aiCount}
                onChange={v => setAiCount(v || 5)}
                style={{ width: 100 }}
              />
              <Text type="secondary" style={{ fontSize: 12 }}>{t('ai.questionCountHint')}</Text>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
              <Text strong style={{ whiteSpace: 'nowrap' }}>{t('ai.contentTypeLabel')}</Text>
              <Select
                value={aiContentType}
                onChange={v => setAiContentType(v)}
                style={{ width: 180 }}
                options={[
                  { value: 'general', label: t('ai.contentTypeGeneral') },
                  { value: 'code', label: t('ai.contentTypeCode') },
                  { value: 'sql', label: t('ai.contentTypeSQL') },
                  { value: 'math', label: t('ai.contentTypeMath') },
                  { value: 'visual', label: t('ai.contentTypeVisual') },
                ]}
              />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
              <Text strong style={{ whiteSpace: 'nowrap' }}>{t('ai.styleLabel')}</Text>
              <Select
                value={aiStyle}
                onChange={v => setAiStyle(v)}
                style={{ width: 180 }}
                options={[
                  { value: 'general', label: t('ai.styleGeneral') },
                  { value: 'upsc', label: t('ai.styleUPSC') },
                  { value: 'jee', label: t('ai.styleJEE') },
                  { value: 'ielts', label: t('ai.styleIELTS') },
                  { value: 'cat', label: t('ai.styleCAT') },
                  { value: 'gate', label: t('ai.styleGATE') },
                ]}
              />
            </div>
            {isExam && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                <Text strong style={{ whiteSpace: 'nowrap' }}>{t('ai.difficultyLabel')}</Text>
                <Radio.Group value={aiDifficulty} onChange={e => setAiDifficulty(e.target.value)}>
                  <Radio.Button value="easy">{t('ai.difficultyEasy')}</Radio.Button>
                  <Radio.Button value="medium">{t('ai.difficultyMedium')}</Radio.Button>
                  <Radio.Button value="hard">{t('ai.difficultyHard')}</Radio.Button>
                </Radio.Group>
              </div>
            )}
            {aiError && <Alert type="error" message={aiError} showIcon />}
            <Button
              type="primary"
              icon={<ThunderboltOutlined />}
              block
              loading={aiGenerating}
              disabled={!aiTopic.trim() || aiGenerating}
              onClick={handleAiGenerate}
              size="large"
            >
              {aiGenerating ? t('ai.generating') : t('ai.generate')}
            </Button>
          </Space>
        )}

        {aiStep === 'preview' && (
          <Space direction="vertical" style={{ width: '100%' }} size={12}>
            <Space wrap>
              <Button size="small" onClick={() => { setAiStep('input'); setAiPreview([]); setAiStreaming(false); aiAbortRef.current?.abort() }} disabled={aiStreaming}>{t('ai.back')}</Button>
              {aiStreaming ? (
                <>
                  <Text type="secondary">
                    <LoadingOutlined spin style={{ marginRight: 6 }} />
                    {t('ai.streamProgress', { count: aiStreamCount, total: aiCount })}
                  </Text>
                  <Button size="small" danger onClick={handleAiStopStream}>
                    {t('ai.stopGenerating')}
                  </Button>
                </>
              ) : (
                <Text type="secondary">{t('ai.selectedCount', { selected: aiPreview.filter(q => q.selected).length, total: aiPreview.length })}</Text>
              )}
            </Space>
            {aiTitle && !aiTitleDismissed && (
              <Alert
                type="info"
                showIcon
                message={t('ai.titleGeneratedBanner', { title: aiTitle })}
                action={
                  <Space>
                    <Button size="small" type="link" onClick={() => setAiTitleDismissed(true)}>
                      {t('ai.titleGeneratedDismiss')}
                    </Button>
                  </Space>
                }
              />
            )}
            {isExam && !aiStreaming && !aiExamSuggDismissed && (aiExamSuggDuration != null || aiExamSuggProctoring != null) && (
              <Alert
                type="success"
                showIcon
                message={
                  <Space size={4} wrap>
                    {aiExamSuggDuration != null && <span>{t('ai.examSuggDuration', { minutes: aiExamSuggDuration })}</span>}
                    {aiExamSuggProctoring != null && <span>{t('ai.examSuggProctoring', { value: aiExamSuggProctoring ? t('common.yes', 'Yes') : t('common.no', 'No') })}</span>}
                  </Space>
                }
                action={
                  <Space>
                    <Button
                      size="small"
                      type="primary"
                      onClick={() => {
                        if (aiExamSuggDuration != null) {
                          form.setFieldsValue({ exam_time_limit_minutes: aiExamSuggDuration })
                        }
                        setAiExamSuggDismissed(true)
                      }}
                    >
                      {t('ai.examSuggApply')}
                    </Button>
                    <Button size="small" type="link" onClick={() => setAiExamSuggDismissed(true)}>
                      {t('ai.examSuggDismiss')}
                    </Button>
                  </Space>
                }
              />
            )}
            {aiPreview.map((q, i) => {
              const qType = q.question_type || 'mcq'
              const typeColors = { mcq: 'cyan', word_cloud: 'purple', scale: 'geekblue', paragraph: 'orange' }
              const typeLabels = { mcq: 'MCQ', word_cloud: t('quiz.wordCloud'), scale: t('quizPresent.scaleOneToFive'), paragraph: t('quiz.paragraph') }
              const isEditing = editingPreviewIndex === i
              const isRegenerating = regeneratingIndex === i

              return (
                <Card
                  key={i}
                  size="small"
                  style={{ borderColor: isEditing ? '#fa8c16' : q.selected ? '#1677ff' : '#d9d9d9', opacity: isRegenerating ? 0.5 : 1 }}
                  extra={
                    <Space>
                      <Tag color={typeColors[qType] || 'default'}>{typeLabels[qType] || qType}</Tag>
                      {!isEditing && (
                        <>
                          <Button
                            size="small"
                            icon={isRegenerating ? <LoadingOutlined spin /> : <ThunderboltOutlined />}
                            onClick={() => handleRegenerateOne(i)}
                            disabled={isRegenerating || regeneratingIndex !== null || editingPreviewIndex !== null}
                            title={t('ai.regenerate', 'Regenerate')}
                          />
                          <Button
                            size="small"
                            icon={<EditOutlined />}
                            onClick={() => {
                              setEditingPreviewIndex(i)
                              setEditingData({
                                text: stripHtml(q.text) || q.text,
                                options: (q.options || []).map(o => stripHtml(o) || o),
                                correct_answer_index: q.correct_answer_index ?? 0,
                              })
                            }}
                            disabled={regeneratingIndex !== null || editingPreviewIndex !== null}
                          />
                          <Checkbox
                            checked={q.selected}
                            onChange={e => setAiPreview(prev => prev.map((item, idx) => idx === i ? { ...item, selected: e.target.checked } : item))}
                          />
                        </>
                      )}
                    </Space>
                  }
                >
                  {isEditing && editingData ? (
                    <Space direction="vertical" style={{ width: '100%' }} size={8}>
                      <Input.TextArea
                        value={editingData.text}
                        onChange={e => setEditingData(d => ({ ...d, text: e.target.value }))}
                        rows={2}
                        autoSize={{ minRows: 2 }}
                        placeholder={t('quiz.enterQuestion')}
                        style={{ fontWeight: 600 }}
                      />
                      {qType === 'mcq' && editingData.options.map((opt, oi) => (
                        <div key={oi} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span
                            style={{
                              flexShrink: 0, width: 22, height: 22, borderRadius: '50%',
                              display: 'flex', alignItems: 'center', justifyContent: 'center',
                              background: oi === editingData.correct_answer_index ? '#52c41a' : '#f0f0f0',
                              color: oi === editingData.correct_answer_index ? '#fff' : '#666',
                              cursor: 'pointer', fontSize: 11, fontWeight: 700,
                            }}
                            title={t('ai.setCorrect', 'Mark as correct')}
                            onClick={() => setEditingData(d => ({ ...d, correct_answer_index: oi }))}
                          >
                            {String.fromCharCode(65 + oi)}
                          </span>
                          <Input
                            value={opt}
                            onChange={e => setEditingData(d => {
                              const opts = [...d.options]
                              opts[oi] = e.target.value
                              return { ...d, options: opts }
                            })}
                            size="small"
                            style={{ flex: 1 }}
                          />
                        </div>
                      ))}
                      <Space>
                        <Button
                          size="small"
                          type="primary"
                          onClick={() => {
                            setAiPreview(prev => prev.map((item, idx) =>
                              idx === i ? { ...item, text: editingData.text, options: editingData.options, correct_answer_index: editingData.correct_answer_index } : item
                            ))
                            setEditingPreviewIndex(null)
                            setEditingData(null)
                          }}
                        >
                          {t('common.save')}
                        </Button>
                        <Button
                          size="small"
                          onClick={() => { setEditingPreviewIndex(null); setEditingData(null) }}
                        >
                          {t('common.cancel')}
                        </Button>
                      </Space>
                    </Space>
                  ) : (
                    <>
                      <div style={{ fontWeight: 600, marginBottom: 8 }}>
                        <RichTextRenderer content={q.text} />
                      </div>
                      {qType === 'mcq' && q.options && (
                        <div>
                          {q.options.map((opt, oi) => (
                            <div key={oi} style={{
                              display: 'flex', alignItems: 'baseline', gap: 4,
                              color: oi === q.correct_answer_index ? '#52c41a' : 'rgba(0,0,0,0.45)',
                              marginBottom: 2,
                            }}>
                              <span style={{ flexShrink: 0, fontWeight: 500 }}>
                                {String.fromCharCode(65 + oi)}:
                              </span>
                              <RichTextRenderer content={opt} style={{ flex: 1 }} />
                              {q.option_image_suggestions?.[oi] && (
                                <Tooltip title={q.option_image_suggestions[oi]}>
                                  <Button
                                    size="small"
                                    type="text"
                                    style={{ padding: '0 2px', flexShrink: 0 }}
                                    onClick={() => window.open(`https://www.google.com/search?tbm=isch&q=${encodeURIComponent(q.option_image_suggestions[oi])}`, '_blank')}
                                  >🔍</Button>
                                </Tooltip>
                              )}
                              {oi === q.correct_answer_index && !isPoll && (
                                <Tag color="green" style={{ marginLeft: 4, flexShrink: 0 }}>{t('ai.correct')}</Tag>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                      {qType === 'scale' && (
                        <Text type="secondary" style={{ fontSize: 12 }}>{t('quiz.scaleRange')}</Text>
                      )}
                      {(qType === 'word_cloud' || qType === 'paragraph') && (
                        <Text type="secondary" style={{ fontSize: 12, fontStyle: 'italic' }}>
                          {qType === 'word_cloud' ? t('quiz.wordCloudDescription') : t('quiz.paragraphDescription')}
                        </Text>
                      )}
                      {q.image_suggestion && (
                        <div style={{ marginTop: 6 }}>
                          <Tooltip title={q.image_suggestion}>
                            <Button
                              size="small"
                              type="dashed"
                              icon={<span>🔍</span>}
                              onClick={() => window.open(`https://www.google.com/search?tbm=isch&q=${encodeURIComponent(q.image_suggestion)}`, '_blank')}
                            >
                              {t('ai.findImage', 'Find image')}
                            </Button>
                          </Tooltip>
                        </div>
                      )}
                    </>
                  )}
                </Card>
              )
            })}
            <Button
              type="primary"
              block
              loading={aiAdding}
              disabled={aiPreview.filter(q => q.selected).length === 0 || aiStreaming}
              onClick={handleAiAddSelected}
            >
              {aiStreaming
                ? t('ai.waitForStream', 'Generating…')
                : t('ai.addToQuiz', { count: aiPreview.filter(q => q.selected).length })
              }
            </Button>
          </Space>
        )}
      </Modal>
    </div>
  )
}
