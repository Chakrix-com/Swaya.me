import { useState, useEffect, useCallback, memo, useContext, useRef } from 'react'
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
} from 'antd'
import {
  PlusOutlined,
  DeleteOutlined,
  SaveOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  RocketOutlined,
  LeftOutlined,
  EditOutlined,
  CloseOutlined,
  MinusCircleOutlined,
  ThunderboltOutlined,
  BulbOutlined,
  LoadingOutlined,
} from '@ant-design/icons'
import {
  Modal,
  Checkbox,
  Select,
  Spin,
  Alert,
  Tooltip,
  DatePicker,
  message as antMessage,
} from 'antd'
import { CopyOutlined, ShareAltOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { quizAPI, questionAPI, aiAPI, examAPI } from '../../services/api'
import ImageUpload from './components/ImageUpload'
import RichTextEditor from './components/RichTextEditor'
import { VisitorThemeContext } from '../../App'
import './QuizBuilder.css'

const { Title, Text } = Typography
const { TextArea } = Input
const getQuestionTypeLabel = (type, t) => {
  const labels = {
    mcq: t('quiz.multipleChoice'),
    word_cloud: t('quiz.wordCloud'),
    single_line: t('quiz.singleLine'),
    scale: t('quizPresent.scaleOneToFive'),
    paragraph: t('quiz.paragraph'),
  }
  return labels[type] || t('quiz.multipleChoice')
}

// QuestionForm component - extracted to prevent recreation on parent re-renders
const QuestionForm = ({
  question,
  onSave,
  onCancel,
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
  language,
  isAdmin,
  t
}) => {
  const [questionForm] = Form.useForm()
  const [questionType, setQuestionType] = useState('mcq')
  const [mcqBaseOptionCount, setMcqBaseOptionCount] = useState(2)
  const [aiSuggestOpen, setAiSuggestOpen] = useState(false)
  const [aiSuggestTopic, setAiSuggestTopic] = useState('')
  const [aiSuggesting, setAiSuggesting] = useState(false)
  const [rewriting, setRewriting] = useState({})
  const [useRichText, setUseRichText] = useState(false)
  const [useRichTextOptions, setUseRichTextOptions] = useState({ option_a: false, option_b: false, option_c: false, option_d: false })
  const [extraRichOpts, setExtraRichOpts] = useState([])
  const { theme } = useContext(VisitorThemeContext)

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

      // Set image URLs from question data
      setQuestionImageUrl(question.question_image_url || null)
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
      
      // Reset image state for new question
      setQuestionImageUrl(null)
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

  const stripHtml = (h) => (h || '').replace(/<[^>]*>/g, '').trim()

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

  return (
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
        <Form.Item
          name="question_type"
          label={t('quiz.questionType')}
          rules={[{ required: true }]}
        >
            <Radio.Group onChange={handleTypeChange}>
              <Radio value="mcq">{t('quiz.multipleChoice')}</Radio>
              {isPoll && <Radio value="word_cloud">{t('quiz.wordCloud')}</Radio>}
              {!isExam && <Radio value="single_line">{t('quiz.singleLine')}</Radio>}
              {isPoll && <Radio value="scale">{t('quizPresent.scaleOneToFive')}</Radio>}
              {isPoll && <Radio value="paragraph">{t('quiz.paragraph')}</Radio>}
          </Radio.Group>
        </Form.Item>

        <Form.Item
          name="text"
          label={
            <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {t('quiz.question')}
              <Tooltip title={useRichText ? t('quiz.simpleTextToggle') : t('tooltip.richTextToggleQuestion')}>
                <Button
                  size="small"
                  type={useRichText ? 'primary' : 'default'}
                  onClick={() => setUseRichText(v => !v)}
                  style={{ fontSize: 11, height: 20, padding: '0 7px', lineHeight: '18px' }}
                >
                  {useRichText ? t('quiz.simpleTextToggle') : t('quiz.richTextToggle')}
                </Button>
              </Tooltip>
            </span>
          }
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
              rows={2}
              placeholder={t('quiz.enterQuestion')}
              spellCheck="true"
              lang={t('common.langCode', { defaultValue: 'en' })}
              onContextMenu={(e) => e.stopPropagation()}
            />
          )}
        </Form.Item>
        {(
          <div style={{ marginTop: -8, marginBottom: 12, textAlign: 'right' }}>
            <Tooltip title={t('ai.rewriteWithAIModel')}>
              <Button
                size="small"
                type="text"
                icon={rewriteIcon('text')}
                loading={rewriting['text']}
                onClick={() => {
                  if (useRichText) {
                    // Strip HTML before sending to AI, then put response back as plain text
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
        )}

        {!isPoll && (
          <Space size={16} style={{ width: '100%' }} wrap>
            <Form.Item
              name="points"
              label={t('quiz.pointsLabel')}
              initialValue={1}
              rules={[{ required: true, message: t('quiz.pointsRequired') }]}
              help={t('tooltip.questionPoints')}
            >
              <InputNumber min={1} precision={0} />
            </Form.Item>
            <Form.Item
              name="max_time_seconds"
              label={t('quiz.maxTimeSecondsLabel')}
              tooltip={t('quiz.maxTimeSecondsTooltip')}
              help={t('tooltip.maxTime')}
            >
              <InputNumber min={1} max={3600} precision={0} />
            </Form.Item>
            {isExam && (
              <Form.Item
                name="negative_points"
                label={t('exam.negativePoints')}
                initialValue={0}
                tooltip={t('tooltip.negativePoints')}
                help={t('tooltip.negativePoints')}
              >
                <InputNumber min={0} precision={0} />
              </Form.Item>
            )}
          </Space>
        )}

        {/* Question Image Upload */}
        <div style={{ marginBottom: 16 }}>
          <Text type="secondary" style={{ display: 'block', marginBottom: 4 }}>
            {t('quiz.questionImageOptional')}
          </Text>
          <ImageUpload
            quizId={parseInt(quizId)}
            questionId={question?.id}
            imageType="question"
            currentImageUrl={questionImageUrl}
            tempData={tempImages.question}
            onImageChange={(url, tempKey) => {
              if (tempKey) {
                // Temp upload
                setTempImages(prev => ({ ...prev, question: { url, tempKey } }))
              } else {
                // Permanent upload or deletion
                setQuestionImageUrl(url)
                setTempImages(prev => ({ ...prev, question: null }))
              }
            }}
          />
        </div>

        {questionType === 'mcq' && (
          <>
            <Form.Item
              name="option_a"
              label={
                <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  {t('quiz.optionA')}
                  <Tooltip title={useRichTextOptions.option_a ? t('quiz.simpleTextToggle') : t('tooltip.richTextToggleOptions')}>
                    <Button size="small" type={useRichTextOptions.option_a ? 'primary' : 'default'} onClick={() => toggleOptRich('option_a')} style={{ fontSize: 11, height: 20, padding: '0 7px', lineHeight: '18px' }}>
                      {useRichTextOptions.option_a ? t('quiz.simpleTextToggle') : t('quiz.richTextToggle')}
                    </Button>
                  </Tooltip>
                </span>
              }
              rules={useRichTextOptions.option_a
                ? [{ validator: (_, v) => stripHtml(v) ? Promise.resolve() : Promise.reject(t('quiz.optionARequired')) }]
                : [{ required: true, message: t('quiz.optionARequired') }]
              }
              getValueFromEvent={useRichTextOptions.option_a ? (v) => v : undefined}
            >
              {useRichTextOptions.option_a
                ? <RichTextEditor isDark={theme === 'dark'} placeholder={t('quiz.optionAPlaceholder')} />
                : <Input
                    placeholder={t('quiz.optionAPlaceholder')}
                    spellCheck="true"
                    lang={t('common.langCode', { defaultValue: 'en' })}
                    onContextMenu={(e) => e.stopPropagation()}
                    suffix={(
                      <Tooltip title={t('ai.rewriteWithAI')}>
                        <Button type="text" size="small" icon={rewriteIcon('option_a')} onClick={() => handleRewrite('option_a', 'quiz answer option')} />
                      </Tooltip>
                    )}
                  />
              }
            </Form.Item>
            {useRichTextOptions.option_a && (
              <div style={{ marginTop: -8, marginBottom: 12, textAlign: 'right' }}>
                <Tooltip title={t('ai.rewriteWithAI')}>
                  <Button type="text" size="small" icon={rewriteIcon('option_a')} onClick={() => handleRewrite('option_a', 'quiz answer option')} />
                </Tooltip>
              </div>
            )}

            {/* Option A Image Upload */}
            <ImageUpload
              quizId={parseInt(quizId)}
              questionId={question?.id}
              imageType="option_a"
              currentImageUrl={optionImages.A}
              tempData={tempImages.optionA}
              onImageChange={(url, tempKey) => {
                if (tempKey) {
                  setTempImages(prev => ({ ...prev, optionA: { url, tempKey } }))
                } else {
                  setOptionImages(prev => ({ ...prev, A: url }))
                  setTempImages(prev => ({ ...prev, optionA: null }))
                }
              }}
            />

            <Form.Item
              name="option_b"
              label={
                <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  {t('quiz.optionB')}
                  <Tooltip title={useRichTextOptions.option_b ? t('quiz.simpleTextToggle') : t('tooltip.richTextToggleOptions')}>
                    <Button size="small" type={useRichTextOptions.option_b ? 'primary' : 'default'} onClick={() => toggleOptRich('option_b')} style={{ fontSize: 11, height: 20, padding: '0 7px', lineHeight: '18px' }}>
                      {useRichTextOptions.option_b ? t('quiz.simpleTextToggle') : t('quiz.richTextToggle')}
                    </Button>
                  </Tooltip>
                </span>
              }
              rules={useRichTextOptions.option_b
                ? [{ validator: (_, v) => stripHtml(v) ? Promise.resolve() : Promise.reject(t('quiz.optionBRequired')) }]
                : [{ required: true, message: t('quiz.optionBRequired') }]
              }
              getValueFromEvent={useRichTextOptions.option_b ? (v) => v : undefined}
            >
              {useRichTextOptions.option_b
                ? <RichTextEditor isDark={theme === 'dark'} placeholder={t('quiz.optionBPlaceholder')} />
                : <Input
                    placeholder={t('quiz.optionBPlaceholder')}
                    spellCheck="true"
                    lang={t('common.langCode', { defaultValue: 'en' })}
                    onContextMenu={(e) => e.stopPropagation()}
                    suffix={(
                      <Tooltip title={t('ai.rewriteWithAI')}>
                        <Button type="text" size="small" icon={rewriteIcon('option_b')} onClick={() => handleRewrite('option_b', 'quiz answer option')} />
                      </Tooltip>
                    )}
                  />
              }
            </Form.Item>
            {useRichTextOptions.option_b && (
              <div style={{ marginTop: -8, marginBottom: 12, textAlign: 'right' }}>
                <Tooltip title={t('ai.rewriteWithAI')}>
                  <Button type="text" size="small" icon={rewriteIcon('option_b')} onClick={() => handleRewrite('option_b', 'quiz answer option')} />
                </Tooltip>
              </div>
            )}

            {/* Option B Image Upload */}
            <ImageUpload
              quizId={parseInt(quizId)}
              questionId={question?.id}
              imageType="option_b"
              currentImageUrl={optionImages.B}
              tempData={tempImages.optionB}
              onImageChange={(url, tempKey) => {
                if (tempKey) {
                  setTempImages(prev => ({ ...prev, optionB: { url, tempKey } }))
                } else {
                  setOptionImages(prev => ({ ...prev, B: url }))
                  setTempImages(prev => ({ ...prev, optionB: null }))
                }
              }}
            />

            {mcqBaseOptionCount >= 3 && (
              <>
                <Form.Item
                  name="option_c"
                  label={
                    <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      {t('quiz.optionC')}
                      <Tooltip title={useRichTextOptions.option_c ? t('quiz.simpleTextToggle') : t('tooltip.richTextToggleOptions')}>
                        <Button size="small" type={useRichTextOptions.option_c ? 'primary' : 'default'} onClick={() => toggleOptRich('option_c')} style={{ fontSize: 11, height: 20, padding: '0 7px', lineHeight: '18px' }}>
                          {useRichTextOptions.option_c ? t('quiz.simpleTextToggle') : t('quiz.richTextToggle')}
                        </Button>
                      </Tooltip>
                    </span>
                  }
                  getValueFromEvent={useRichTextOptions.option_c ? (v) => v : undefined}
                >
                  {useRichTextOptions.option_c
                    ? <RichTextEditor isDark={theme === 'dark'} placeholder={t('quiz.optionCPlaceholder')} />
                    : <Input
                        placeholder={t('quiz.optionCPlaceholder')}
                        spellCheck="true"
                        lang={t('common.langCode', { defaultValue: 'en' })}
                        onContextMenu={(e) => e.stopPropagation()}
                        suffix={(
                          <Tooltip title={t('ai.rewriteWithAI')}>
                            <Button type="text" size="small" icon={rewriteIcon('option_c')} onClick={() => handleRewrite('option_c', 'quiz answer option')} />
                          </Tooltip>
                        )}
                      />
                  }
                </Form.Item>
                {useRichTextOptions.option_c && (
                  <div style={{ marginTop: -8, marginBottom: 12, textAlign: 'right' }}>
                    <Tooltip title={t('ai.rewriteWithAI')}>
                      <Button type="text" size="small" icon={rewriteIcon('option_c')} onClick={() => handleRewrite('option_c', 'quiz answer option')} />
                    </Tooltip>
                  </div>
                )}

                <ImageUpload
                  quizId={parseInt(quizId)}
                  questionId={question?.id}
                  imageType="option_c"
                  currentImageUrl={optionImages.C}
                  tempData={tempImages.optionC}
                  onImageChange={(url, tempKey) => {
                    if (tempKey) {
                      setTempImages(prev => ({ ...prev, optionC: { url, tempKey } }))
                    } else {
                      setOptionImages(prev => ({ ...prev, C: url }))
                      setTempImages(prev => ({ ...prev, optionC: null }))
                    }
                  }}
                />
              </>
            )}

            {mcqBaseOptionCount >= 4 && (
              <>
                <Form.Item
                  name="option_d"
                  label={
                    <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      {t('quiz.optionD')}
                      <Tooltip title={useRichTextOptions.option_d ? t('quiz.simpleTextToggle') : t('tooltip.richTextToggleOptions')}>
                        <Button size="small" type={useRichTextOptions.option_d ? 'primary' : 'default'} onClick={() => toggleOptRich('option_d')} style={{ fontSize: 11, height: 20, padding: '0 7px', lineHeight: '18px' }}>
                          {useRichTextOptions.option_d ? t('quiz.simpleTextToggle') : t('quiz.richTextToggle')}
                        </Button>
                      </Tooltip>
                    </span>
                  }
                  getValueFromEvent={useRichTextOptions.option_d ? (v) => v : undefined}
                >
                  {useRichTextOptions.option_d
                    ? <RichTextEditor isDark={theme === 'dark'} placeholder={t('quiz.optionDPlaceholder')} />
                    : <Input
                        placeholder={t('quiz.optionDPlaceholder')}
                        spellCheck="true"
                        lang={t('common.langCode', { defaultValue: 'en' })}
                        onContextMenu={(e) => e.stopPropagation()}
                        suffix={(
                          <Tooltip title={t('ai.rewriteWithAI')}>
                            <Button type="text" size="small" icon={rewriteIcon('option_d')} onClick={() => handleRewrite('option_d', 'quiz answer option')} />
                          </Tooltip>
                        )}
                      />
                  }
                </Form.Item>
                {useRichTextOptions.option_d && (
                  <div style={{ marginTop: -8, marginBottom: 12, textAlign: 'right' }}>
                    <Tooltip title={t('ai.rewriteWithAI')}>
                      <Button type="text" size="small" icon={rewriteIcon('option_d')} onClick={() => handleRewrite('option_d', 'quiz answer option')} />
                    </Tooltip>
                  </div>
                )}

                <ImageUpload
                  quizId={parseInt(quizId)}
                  questionId={question?.id}
                  imageType="option_d"
                  currentImageUrl={optionImages.D}
                  tempData={tempImages.optionD}
                  onImageChange={(url, tempKey) => {
                    if (tempKey) {
                      setTempImages(prev => ({ ...prev, optionD: { url, tempKey } }))
                    } else {
                      setOptionImages(prev => ({ ...prev, D: url }))
                      setTempImages(prev => ({ ...prev, optionD: null }))
                    }
                  }}
                />
              </>
            )}

            <Form.List name="extra_options">
              {(fields, { add, remove }) => (
                <>
                  {fields.map((field) => {
                    const isRich = !!extraRichOpts[field.name]
                    return (
                      <div key={field.key} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginBottom: 8 }}>
                        <div style={{ flex: 1 }}>
                          <Form.Item
                            {...field}
                            label={
                              <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                {t('quiz.optionLabel', { defaultValue: `Option ${field.name + 5}` })}
                                <Tooltip title={isRich ? t('quiz.simpleTextToggle') : t('tooltip.richTextToggleOptions')}>
                                  <Button size="small" type={isRich ? 'primary' : 'default'} onClick={() => toggleExtraOptRich(field.name)} style={{ fontSize: 11, height: 20, padding: '0 7px', lineHeight: '18px' }}>
                                    {isRich ? t('quiz.simpleTextToggle') : t('quiz.richTextToggle')}
                                  </Button>
                                </Tooltip>
                              </span>
                            }
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
                        <Button style={{ marginTop: 30 }} icon={<MinusCircleOutlined />} onClick={() => remove(field.name)} />
                      </div>
                    )
                  })}
                  <Form.Item>
                    <Space>
                      <Button
                        type="dashed"
                        onClick={() => {
                          const totalOptions = mcqBaseOptionCount + fields.length
                          if (totalOptions >= 10) {
                            return
                          }
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
                    </Space>
                  </Form.Item>
                  <Form.Item style={{ marginTop: -8 }}>
                    <Text type="secondary">
                      {t('quiz.optionCountHint', { defaultValue: 'Options: {{count}} (min 2, max 10)', count: mcqBaseOptionCount + fields.length })}
                    </Text>
                  </Form.Item>
                </>
              )}
            </Form.List>

            {!isPoll && (
              <>
                <Form.Item shouldUpdate>
                  {() => {
                    const optionValues = [
                      questionForm.getFieldValue('option_a'),
                      questionForm.getFieldValue('option_b'),
                      questionForm.getFieldValue('option_c'),
                      questionForm.getFieldValue('option_d'),
                      ...(questionForm.getFieldValue('extra_options') || []),
                    ].filter((v) => stripHtml(v).length > 0)

                    return (
                      <Form.Item
                        name="correct_answer"
                        label={t('quiz.correctAnswer')}
                        rules={[{ required: true, message: t('quiz.correctAnswerRequired') }]}
                      >
                        <Radio.Group>
                          {optionValues.map((_, index) => (
                            <Radio key={index} value={String(index)}>
                              {t('quiz.optionLabel', { defaultValue: `Option ${index + 1}` })}
                            </Radio>
                          ))}
                        </Radio.Group>
                      </Form.Item>
                    )
                  }}
                </Form.Item>
              </>
            )}
          </>
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
                <Button size="small" onClick={() => { setAiSuggestOpen(false); setAiSuggestTopic('') }}>Cancel</Button>
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

        <Space style={{ marginTop: 28 }}>
          <Button
            type="primary"
            htmlType="submit"
            loading={loading || movingImages}
            icon={question ? <SaveOutlined /> : <PlusOutlined />}
          >
            {movingImages ? t('quiz.movingImages') : (question ? t('quiz.updateQuestion') : t('quiz.addQuestion'))}
          </Button>
          <Button icon={<CloseOutlined />} onClick={onCancel}>{t('common.cancel')}</Button>
        </Space>
      </Form>
    </Card>
  )
}

// Memoize QuestionForm with default shallow prop comparison to avoid stale form values.
const MemoizedQuestionForm = memo(QuestionForm)

export default function QuizBuilder() {
  const { message } = App.useApp()
  const { id } = useParams()
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [quiz, setQuiz] = useState(null)
  const [questions, setQuestions] = useState([])
  const [editingQuestion, setEditingQuestion] = useState(null)
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
  const rawType = searchParams.get('type')
  const initialQuizType = rawType === 'poll' ? 'poll' : rawType === 'offline_poll' ? 'offline_poll' : rawType === 'exam' ? 'exam' : 'quiz'

  const [tempImages, setTempImages] = useState({
    question: null,  // {url, tempKey}
    optionA: null,
    optionB: null,
    optionC: null,
    optionD: null
  })
  
  // Loading state for moving temp images
  const [movingImages, setMovingImages] = useState(false)
  const [pollLinkModal, setPollLinkModal] = useState({ open: false, url: '' })
  const [examLinkModal, setExamLinkModal] = useState({ open: false, url: '' })
  const isPoll = quiz?.quiz_type === 'poll' || quiz?.quiz_type === 'offline_poll' || (!quiz && initialQuizType === 'poll') || (!quiz && initialQuizType === 'offline_poll')
  const isOfflinePoll = quiz?.quiz_type === 'offline_poll' || (!quiz && initialQuizType === 'offline_poll')
  const isExam = quiz?.quiz_type === 'exam' || (!quiz && initialQuizType === 'exam')
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
  const [aiTopic, setAiTopic] = useState('')
  const [aiCount, setAiCount] = useState(5)
  const [aiError, setAiError] = useState(null)
  const [aiPreview, setAiPreview] = useState([]) // [{text, options, correct_answer_index, selected}]

  useEffect(() => {
    if (id) {
      loadQuiz()
    } else {
      // For new quizzes, set initial form values based on URL param
      form.setFieldsValue({
        quiz_type: initialQuizType
      })
    }
  }, [id, initialQuizType, form])

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

  const loadQuiz = useCallback(async () => {
    try {
      const response = await quizAPI.get(id)
      setQuiz(response.data)
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
      })
    } catch (error) {
      const errorMsg = error.response?.data?.detail || t('quiz.loadError')
      message.error(errorMsg)
      console.error('Load quiz error:', error.response?.data || error)
    }
  }, [id])

  const handleSaveQuiz = async (rawValues) => {
    setLoading(true)
    // Serialize dayjs objects to ISO strings for the API
    const timeLimitMins = rawValues.exam_time_limit_minutes
    const values = {
      ...rawValues,
      offline_start_at: rawValues.offline_start_at?.toISOString() ?? null,
      offline_end_at: rawValues.offline_end_at?.toISOString() ?? null,
      exam_start_at: rawValues.exam_start_at?.toISOString() ?? null,
      exam_end_at: rawValues.exam_end_at?.toISOString() ?? null,
      exam_time_limit_seconds: timeLimitMins ? Number(timeLimitMins) * 60 : null,
    }
    delete values.exam_time_limit_minutes
    try {
      if (id) {
        await quizAPI.update(id, values)
        message.success(isExam ? t('exam.saveSuccess') : isOfflinePoll ? t('quiz.saveOfflinePollSuccess') : isPoll ? t('quiz.savePollSuccess') : t('quiz.saveSuccess'))
        loadQuiz()
      } else {
        const response = await quizAPI.create(values)
        message.success(isExam ? t('exam.createSuccess') : isOfflinePoll ? t('quiz.createOfflinePollSuccess') : isPoll ? t('quiz.createPollSuccess') : t('quiz.createSuccess'))
        navigate(`/quiz/${response.data.id}/edit`)
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

  const handlePublish = async () => {
    setLoading(true)
    try {
      if (isExam) {
        const res = await examAPI.publish(id)
        setExamLinkModal({ open: true, url: res.data.exam_url })
        loadQuiz()
      } else if (isOfflinePoll) {
        const res = await quizAPI.publishOffline(id)
        setPollLinkModal({ open: true, url: res.data.poll_url })
        loadQuiz()
      } else {
        await quizAPI.publish(id)
        message.success(t('quiz.publishSuccess'))
        navigate(`/quiz/${id}/control`)
      }
    } catch (error) {
      message.error(error.response?.data?.detail || (isExam ? t('exam.publishError') : t('quiz.publishError')))
      console.error(error)
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
  
  const handleAiGenerate = async () => {
    if (!aiTopic.trim()) return
    setAiGenerating(true)
    setAiError(null)
    try {
      const res = await aiAPI.generateQuestions({
        topic: aiTopic.trim(),
        count: aiCount,
        language: i18n.language,
      })
      const questions = res.data.questions.map(q => ({ ...q, selected: true }))
      if (questions.length === 0) {
        setAiError(t('ai.noQuestionsGenerated'))
        return
      }
      setAiPreview(questions)
      setAiStep('preview')
    } catch (err) {
      setAiError(err.response?.data?.detail || t('ai.generationFailed'))
    } finally {
      setAiGenerating(false)
    }
  }

  const handleAiAddSelected = async () => {
    const selected = aiPreview.filter(q => q.selected)
    if (selected.length === 0) return
    setAiAdding(true)
    try {
      for (const q of selected) {
        await questionAPI.add(id, {
          question_type: 'mcq',
          text: q.text,
          options: q.options,
          correct_answer_index: isPoll ? null : q.correct_answer_index,
          points: 1,
          max_time_seconds: null,
        })
      }
      message.success(t('ai.addedSuccess', { count: selected.length }))
      setAiModalOpen(false)
      setAiStep('input')
      setAiTopic('')
      setAiPreview([])
      await loadQuiz()
    } catch (err) {
      message.error(err.response?.data?.detail || 'Failed to add questions')
    } finally {
      setAiAdding(false)
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
    <div className="quiz-builder-page" style={{ padding: 24 }}>
      <Space wrap className="quiz-builder-topbar">
        <Button 
          icon={<LeftOutlined />} 
          onClick={() => navigate('/dashboard')}
        >
          {t('quiz.backDashboard')}
        </Button>
        {quiz && quiz.status === 'draft' && questions.length >= 1 && (
          <Tooltip title={t('tooltip.publishQuiz')}>
            <Button
              type="primary"
              icon={<RocketOutlined />}
              onClick={handlePublish}
              loading={loading}
            >
              {isExam ? t('exam.publishActivate') : isOfflinePoll ? t('offlinePoll.publishActivate', 'Publish & Activate') : isPoll ? t('quiz.publishPoll') : t('quiz.publishQuiz')}
            </Button>
          </Tooltip>
        )}
        {quiz && quiz.status === 'ready' && !isOfflinePoll && !isExam && (
          <>
            <Button
              type="primary"
              icon={<RocketOutlined />}
              onClick={() => navigate(`/quiz/${id}/control`)}
            >
              {isPoll ? t('quiz.startPoll') : t('quiz.startSession')}
            </Button>
            <Tooltip title={t('tooltip.unpublishQuiz')}>
              <Button
                type="default"
                onClick={handleUnpublish}
                loading={loading}
              >
                {isPoll ? t('quiz.unpublishPoll') : t('quiz.unpublishQuiz')}
              </Button>
            </Tooltip>
          </>
        )}
        {quiz && quiz.status === 'ready' && isOfflinePoll && quiz.poll_slug && (
          <Tooltip title={t('tooltip.copyShareLink')}>
            <Button
              icon={<ShareAltOutlined />}
              onClick={() => setPollLinkModal({ open: true, url: `${window.location.origin}/poll/${quiz.poll_slug}` })}
            >
              {t('offlinePoll.copyLink', 'Copy Link')}
            </Button>
          </Tooltip>
        )}
        {quiz && quiz.status === 'ready' && isOfflinePoll && (
          <Button
            onClick={() => navigate(`/quiz/${id}/offline-results`)}
          >
            {t('offlinePoll.viewResults', 'View Results')}
          </Button>
        )}
        {quiz && quiz.status === 'ready' && isExam && quiz.exam_slug && (
          <Tooltip title={t('tooltip.copyShareLink')}>
            <Button
              icon={<ShareAltOutlined />}
              onClick={() => setExamLinkModal({ open: true, url: `${window.location.origin}/e/${quiz.exam_slug}` })}
            >
              {t('exam.copyLink')}
            </Button>
          </Tooltip>
        )}
        {quiz && quiz.status === 'ready' && isExam && (
          <>
            <Button
              onClick={() => navigate(`/quiz/${id}/exam-results`)}
            >
              {t('exam.results.title', 'View Results')}
            </Button>
            <Tooltip title={t('tooltip.unpublishQuiz')}>
              <Button
                type="default"
                onClick={handleUnpublish}
                loading={loading}
              >
                {t('exam.unpublishExam')}
              </Button>
            </Tooltip>
          </>
        )}
      </Space>

      <Card
        title={
          id
            ? (isExam ? t('exam.editExam') : isOfflinePoll ? t('offlinePoll.editOfflinePoll', 'Edit Offline Poll') : isPoll ? t('quiz.editPoll', 'Edit Poll') : t('quiz.editQuiz'))
            : (isExam ? t('exam.createExam') : isOfflinePoll ? t('offlinePoll.createOfflinePoll', 'Create Poll') : isPoll ? t('quiz.createPoll') : t('quiz.createQuiz'))
        }
        style={{ marginBottom: 24, width: '100%' }}
      >
        {quiz && (
          <Space style={{ marginBottom: 16 }}>
            <Tag color={quiz.status === 'draft' ? 'orange' : 'green'}>
              {getQuizStatusTranslation(quiz.status)}
            </Tag>
            <Tag color={quiz.quiz_type === 'exam' ? 'volcano' : quiz.quiz_type === 'offline_poll' ? 'magenta' : quiz.quiz_type === 'poll' ? 'purple' : 'blue'}>
              {quiz.quiz_type === 'exam' ? t('exam.typeLabel') : quiz.quiz_type === 'offline_poll' ? t('offlinePoll.typeLabel', 'Poll') : quiz.quiz_type === 'poll' ? t('quiz.poll', 'Online Poll') : t('quiz.quizTypeLabel', 'Online Quiz')}
            </Tag>
            {quiz.quiz_type === 'offline_poll' && quiz.poll_slug && (
              <Text
                copyable={{ text: `${window.location.origin}/poll/${quiz.poll_slug}`, tooltips: ['Copy link', 'Copied!'] }}
                type="secondary"
                style={{ fontSize: 12 }}
              >
                {t('offlinePoll.copyLink', 'Copy Link')}
              </Text>
            )}
            {quiz.status === 'ready' && !isOfflinePoll && (
              <Tag color="red">
                {isExam ? t('exam.unpublishMessage', 'Click "Deactivate Exam" above to edit') : isPoll ? t('quiz.unpublishPollMessage', 'Click "Unpublish Poll" above to edit') : (t('quiz.unpublishMessage') || 'Click "Unpublish Quiz" above to edit')}
              </Tag>
            )}
            <Text type="secondary">
              {questions.length} {questions.length === 1 ? t('quiz.question') : t('quiz.questions')}
            </Text>
          </Space>
        )}

        {!id && (
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
            message={
              isExam ? t('exam.typeInfo')
              : isOfflinePoll ? t('offlinePoll.typeInfo')
              : isPoll ? t('quiz.pollTypeInfo')
              : t('quiz.quizTypeInfo')
            }
          />
        )}

        <Form
          form={form}
          layout="vertical"
          onFinish={handleSaveQuiz}
        >
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

          <Form.Item
            name="quiz_type"
            label={t('quiz.mode')}
            initialValue="quiz"
            hidden
          >
            <Radio.Group>
              <Radio value="quiz">{t('quiz.modeQuiz')}</Radio>
              <Radio value="poll">{t('quiz.modePoll')}</Radio>
              <Radio value="offline_poll">{t('offlinePoll.typeLabel', 'Offline Poll')}</Radio>
            </Radio.Group>
          </Form.Item>

          {/* Offline poll configuration fields */}
          {isOfflinePoll && (
            <Space direction="vertical" style={{ width: '100%', marginBottom: 16 }}>
              <Form.Item
                name="offline_start_at"
                label={t('offlinePoll.startDate', 'Start Date & Time')}
                rules={[{ required: isOfflinePoll, message: 'Start date is required for offline polls' }]}
              >
                <DatePicker showTime style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item
                name="offline_end_at"
                label={t('offlinePoll.endDate', 'End Date & Time')}
                rules={[{ required: isOfflinePoll, message: 'End date is required for offline polls' }]}
              >
                <DatePicker showTime style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item
                name="offline_results_email"
                label={t('offlinePoll.resultsEmail', 'Email Results To (optional)')}
              >
                <Input type="email" placeholder="your@email.com" />
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
                <DatePicker showTime style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item
                name="exam_end_at"
                label={t('exam.endAt')}
                rules={[{ required: isExam, message: t('exam.endAtRequired') }]}
              >
                <DatePicker showTime style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item
                name="exam_time_limit_minutes"
                label={t('exam.timeLimitMinutes')}
              >
                <InputNumber min={1} max={600} placeholder={t('exam.timeLimitPlaceholder')} style={{ width: '100%' }} />
              </Form.Item>
            </Space>
          )}

          <Button
            type="primary"
            htmlType="submit"
            icon={<SaveOutlined />}
            loading={loading}
          >
            {id
              ? (isExam ? t('exam.editExam') : isOfflinePoll ? t('offlinePoll.updateOfflinePoll', 'Update Offline Poll') : isPoll ? t('quiz.updatePoll') : t('quiz.editQuiz'))
              : (isExam ? t('exam.createExam') : isOfflinePoll ? t('offlinePoll.createOfflinePoll', 'Create Offline Poll') : isPoll ? t('quiz.createPoll') : t('quiz.createQuiz'))
            }
          </Button>
        </Form>
      </Card>

      {/* Poll link modal for offline polls */}
      <Modal
        title={t('offlinePoll.publishActivate', 'Poll Published!')}
        open={pollLinkModal.open}
        onCancel={() => setPollLinkModal({ open: false, url: '' })}
        footer={[
          <Button key="close" onClick={() => setPollLinkModal({ open: false, url: '' })}>
            Close
          </Button>
        ]}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Text>Your offline poll is now active. Share this link with participants:</Text>
          <Text
            strong
            copyable={{ text: pollLinkModal.url, icon: <CopyOutlined />, tooltips: [t('offlinePoll.copyLink', 'Copy Link'), t('offlinePoll.linkCopied', 'Link copied!')] }}
            style={{ wordBreak: 'break-all' }}
          >
            {pollLinkModal.url}
          </Text>
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
            Close
          </Button>
        ]}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Text>Your exam is now live. Share this link with participants:</Text>
          <Text
            strong
            copyable={{ text: examLinkModal.url, icon: <CopyOutlined />, tooltips: [t('exam.copyLink'), t('exam.linkCopied')] }}
            style={{ wordBreak: 'break-all' }}
          >
            {examLinkModal.url}
          </Text>
        </Space>
      </Modal>

      {id && (
        <>
          <div ref={questionsRef} />
          <Divider>{t('quiz.questions')}</Divider>

          {editingQuestion !== 'new' && isAdmin && (
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

          {editingQuestion === 'new' ? (
            <MemoizedQuestionForm
              key="new-question"
              onSave={handleAddQuestion}
              onCancel={handleCancelQuestion}
              quizId={id}
              isPoll={isPoll}
              isExam={isExam}
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
            >
              {t('quiz.addQuestion')}
            </Button>
          )}

          <List
            dataSource={questions}
            renderItem={(question, index) => (
              editingQuestion === question.id ? (
                <MemoizedQuestionForm
                  key={`edit-question-${question.id}`}
                  question={question}
                  onSave={(values) => handleUpdateQuestion(question.id, values)}
                  onCancel={handleCancelQuestion}
                  quizId={id}
                  isPoll={isPoll}
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
                  key={question.id}
                  style={{ marginBottom: 16, width: '100%' }}
                  title={
                    <Space>
                      <Tag color="blue">Q{index + 1}</Tag>
                      <Tag color={question.question_type === 'word_cloud' ? 'purple' : (question.question_type === 'mcq' ? 'cyan' : 'geekblue')}>
                        {getQuestionTypeLabel(question.question_type, t)}
                      </Tag>
                      {!isPoll && <Tag color="green">{t('quiz.pointsTag', { points: question.points || 1 })}</Tag>}
                      {!isPoll && question.max_time_seconds ? (
                        <Tag color="orange">{t('quiz.timerTag', { seconds: question.max_time_seconds })}</Tag>
                      ) : null}
                      <Text strong>{question.text.replace(/<[^>]*>/g, '')}</Text>
                    </Space>
                  }
                  extra={
                    <Space>
                      <Button
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => setEditingQuestion(question.id)}
                      >
                        {t('common.edit')}
                      </Button>
                      <Popconfirm
                        title={t('quiz.deleteQuestionConfirm')}
                        onConfirm={() => handleDeleteQuestion(question.id)}
                        okText={t('common.submit')}
                        cancelText={t('common.cancel')}
                      >
                        <Button
                          size="small"
                          danger
                          icon={<DeleteOutlined />}
                        />
                      </Popconfirm>
                    </Space>
                  }
                >
                  {question.question_type === 'word_cloud' ? (
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Text type="secondary" italic>
                        {t('quiz.wordCloudQuestionDescription')}
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
                            <div key={`${question.id}-opt-${idx}`}>
                              <Text>{letter}: {opt}</Text>
                              {!isPoll && idx === correctIndex && <Tag color="green" style={{ marginLeft: 8 }}>{t('quiz.correct')}</Tag>}
                            </div>
                          )
                        })
                      })()}
                    </Space>
                  )}
                </Card>
              )
            )}
          />
        </>
      )}

      {/* AI Generate Questions Modal */}
      <Modal
        title={<Space><ThunderboltOutlined />{t('ai.generateQuestionsTitle')}</Space>}
        open={aiModalOpen}
        onCancel={() => { setAiModalOpen(false); setAiStep('input'); setAiPreview([]); setAiError(null) }}
        footer={null}
        width={600}
      >
        {aiStep === 'input' && (
          <Space direction="vertical" style={{ width: '100%' }} size={16}>
            <div>
              <Text strong>{t('ai.topicLabel')}</Text>
              <Input
                placeholder={t('ai.topicPlaceholder')}
                value={aiTopic}
                onChange={e => setAiTopic(e.target.value)}
                onPressEnter={handleAiGenerate}
                style={{ marginTop: 4 }}
                autoFocus
              />
            </div>
            <div>
              <Text strong>{t('ai.numberOfQuestions')}</Text>
              <Select
                value={aiCount}
                onChange={setAiCount}
                style={{ display: 'block', marginTop: 4 }}
                options={[1,2,3,4,5].map(n => ({ value: n, label: t('ai.questionCount', { count: n }) }))}
              />
            </div>
            {aiError && <Alert type="error" message={aiError} showIcon />}
            <Button
              type="primary"
              icon={<ThunderboltOutlined />}
              block
              loading={aiGenerating}
              disabled={!aiTopic.trim()}
              onClick={handleAiGenerate}
            >
              {aiGenerating ? t('ai.generating') : t('ai.generate')}
            </Button>
          </Space>
        )}

        {aiStep === 'preview' && (
          <Space direction="vertical" style={{ width: '100%' }} size={12}>
            <Space>
              <Button size="small" onClick={() => setAiStep('input')}>{t('ai.back')}</Button>
              <Text type="secondary">{t('ai.selectedCount', { selected: aiPreview.filter(q => q.selected).length, total: aiPreview.length })}</Text>
            </Space>
            {aiPreview.map((q, i) => (
              <Card
                key={i}
                size="small"
                style={{ borderColor: q.selected ? '#1677ff' : '#d9d9d9' }}
                extra={
                  <Checkbox
                    checked={q.selected}
                    onChange={e => setAiPreview(prev => prev.map((item, idx) => idx === i ? { ...item, selected: e.target.checked } : item))}
                  />
                }
              >
                <Text strong>{q.text}</Text>
                <div style={{ marginTop: 8 }}>
                  {q.options.map((opt, oi) => (
                    <div key={oi}>
                      <Text type={oi === q.correct_answer_index ? 'success' : 'secondary'}>
                        {String.fromCharCode(65 + oi)}: {opt}
                        {oi === q.correct_answer_index && !isPoll && <Tag color="green" style={{ marginLeft: 6 }}>{t('ai.correct')}</Tag>}
                      </Text>
                    </div>
                  ))}
                </div>
              </Card>
            ))}
            <Button
              type="primary"
              block
              loading={aiAdding}
              disabled={aiPreview.filter(q => q.selected).length === 0}
              onClick={handleAiAddSelected}
            >
              {t('ai.addToQuiz', { count: aiPreview.filter(q => q.selected).length })}
            </Button>
          </Space>
        )}
      </Modal>
    </div>
  )
}
