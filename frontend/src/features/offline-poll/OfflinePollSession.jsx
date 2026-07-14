import { useState, useEffect, useCallback, useContext } from 'react'
import { useParams } from 'react-router-dom'
import {
  Card, Button, Typography, Space, Progress, Radio, Input, Spin,
  Alert, Tag, Divider, Row, Col, message, Checkbox
} from 'antd'
import { CheckCircleOutlined, ClockCircleOutlined, SafetyCertificateOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { offlinePollAPI } from '../../services/api'
import { ProctoringProvider, ProctoringGate } from '../proctoring'
import PublicBrandHeader from '../../components/PublicBrandHeader'
import RichTextRenderer from '../quiz/components/RichTextRenderer'
import VideoEmbed from '../quiz/components/VideoEmbed'
import PromoCard from '../../components/PromoCard'
import { VisitorThemeContext } from '../../App'

const { Title, Text, Paragraph } = Typography
const { TextArea } = Input

const STORAGE_TOKEN_KEY = (slug) => `offline_poll_${slug}_token`
const STORAGE_COMPLETED_KEY = (slug) => `offline_poll_${slug}_completed`

const cardStyle = {
  width: '100%',
  maxWidth: 600,
  borderRadius: 12,
  marginTop: 24,
}

function formatDate(dt) {
  if (!dt) return ''
  return new Date(dt).toLocaleString()
}

export default function OfflinePollSession() {
  const { slug } = useParams()
  const { t } = useTranslation()
  const { theme } = useContext(VisitorThemeContext)

  // State machine: loading | not_started | active | closed | joining | answering | completed | already_completed
  const [phase, setPhase] = useState('loading')
  const [pollInfo, setPollInfo] = useState(null)
  const [error, setError] = useState(null)

  // Participation state
  const [displayName, setDisplayName] = useState('')
  const [sessionToken, setSessionToken] = useState(null)
  const [questions, setQuestions] = useState([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [answers, setAnswers] = useState({}) // { questionId: { selected_option_index?, text_answer? } }
  const [saving, setSaving] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  // Load poll info
  useEffect(() => {
    const completedKey = STORAGE_COMPLETED_KEY(slug)
    if (localStorage.getItem(completedKey) === 'true') {
      setPhase('already_completed')
      return
    }
    offlinePollAPI.getInfo(slug)
      .then(res => {
        setPollInfo(res.data)
        const status = res.data.status
        if (status === 'not_started') setPhase('not_started')
        else if (status === 'closed') setPhase('closed')
        else setPhase('active') // active → show join UI
      })
      .catch(err => {
        if (err.response?.status === 404) setError(t('offlinePoll.pollNotFound', 'Poll not found'))
        else setError(t('common.error', 'An error occurred'))
        setPhase('error')
      })
  }, [slug, t])

  const handleJoin = useCallback(async () => {
    setPhase('joining')
    try {
      const storedToken = sessionStorage.getItem(STORAGE_TOKEN_KEY(slug))
      const res = await offlinePollAPI.join(slug, {
        display_name: displayName || undefined,
        session_token: storedToken || undefined,
      })
      const { session_token, questions: qs, saved_answers } = res.data
      sessionStorage.setItem(STORAGE_TOKEN_KEY(slug), session_token)
      setSessionToken(session_token)
      setQuestions(qs)

      // Restore saved answers
      const savedMap = {}
      for (const sa of (saved_answers || [])) {
        savedMap[sa.question_id] = {
          selected_option_index: sa.selected_option_index,
          selected_option_indices: sa.selected_option_indices,
          text_answer: sa.text_answer,
        }
      }
      setAnswers(savedMap)

      // Resume at first unanswered question
      let resumeIndex = 0
      for (let i = 0; i < qs.length; i++) {
        if (savedMap[qs[i].id] !== undefined) {
          resumeIndex = i
        }
      }
      // If all answered, start at last
      if (Object.keys(savedMap).length > 0) {
        resumeIndex = Math.min(resumeIndex, qs.length - 1)
      }
      setCurrentIndex(resumeIndex)
      setPhase('answering')
    } catch (err) {
      const detail = err.response?.data?.detail || t('common.error', 'Failed to join poll')
      setError(detail)
      setPhase('active')
    }
  }, [slug, displayName, t])

  const saveCurrentAnswer = useCallback(async (qId, answerData) => {
    if (!sessionToken) return
    setSaving(true)
    try {
      await offlinePollAPI.saveAnswer(slug, {
        session_token: sessionToken,
        question_id: qId,
        ...answerData,
      })
    } catch (err) {
      // Non-blocking — user can still navigate
      console.warn('Save answer failed:', err)
    } finally {
      setSaving(false)
    }
  }, [slug, sessionToken])

  const handleAnswerChange = (questionId, field, value) => {
    setAnswers(prev => ({
      ...prev,
      [questionId]: { ...(prev[questionId] || {}), [field]: value },
    }))
  }

  const handleNext = async () => {
    const q = questions[currentIndex]
    const ans = answers[q.id]
    if (ans) await saveCurrentAnswer(q.id, ans)
    setCurrentIndex(i => i + 1)
  }

  const handleBack = async () => {
    const q = questions[currentIndex]
    const ans = answers[q.id]
    if (ans) await saveCurrentAnswer(q.id, ans)
    setCurrentIndex(i => i - 1)
  }

  const handleSubmit = async () => {
    // Save last answer first
    const q = questions[currentIndex]
    const ans = answers[q.id]
    if (ans) await saveCurrentAnswer(q.id, ans)

    setSubmitting(true)
    try {
      await offlinePollAPI.complete(slug, { session_token: sessionToken })
      localStorage.setItem(STORAGE_COMPLETED_KEY(slug), 'true')
      setPhase('completed')
    } catch (err) {
      const detail = err.response?.data?.detail || t('common.error', 'Submission failed')
      message.error(detail)
    } finally {
      setSubmitting(false)
    }
  }

  // ---- Render phases ----

  if (phase === 'loading') {
    return (
      <div className="offline-poll-session">
        <PublicBrandHeader />
        <div className="offline-poll-session__content">
          <Spin size="large" style={{ marginTop: 60 }} />
        </div>
      </div>
    )
  }

  if (phase === 'error') {
    return (
      <div className="offline-poll-session">
        <PublicBrandHeader />
        <div className="offline-poll-session__content">
          <Card style={cardStyle}>
            <Alert type="error" message={error} showIcon />
          </Card>
        </div>
      </div>
    )
  }

  if (phase === 'not_started') {
    return (
      <div className="offline-poll-session">
        <PublicBrandHeader />
        <div className="offline-poll-session__content">
        <Card style={cardStyle}>
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Title level={3} style={{ margin: 0 }}>{pollInfo?.title}</Title>
            <Tag color="blue" icon={<ClockCircleOutlined />}>
              {t('offlinePoll.statusNotStarted', 'Poll hasn\'t started yet')}
            </Tag>
            <Text type="secondary">
              {t('offlinePoll.startsOn', 'Opens on {{date}}', { date: formatDate(pollInfo?.starts_at) })}
            </Text>
            {pollInfo?.description && <Paragraph>{pollInfo.description}</Paragraph>}
          </Space>
        </Card>
        </div>
      </div>
    )
  }

  if (phase === 'closed') {
    return (
      <div className="offline-poll-session">
        <PublicBrandHeader />
        <div className="offline-poll-session__content">
        <Card style={cardStyle}>
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Title level={3} style={{ margin: 0 }}>{pollInfo?.title}</Title>
            <Tag color="default">
              {t('offlinePoll.statusClosed', 'This poll has closed')}
            </Tag>
            <Text type="secondary">
              {t('offlinePoll.closedOn', 'Closed on {{date}}', { date: formatDate(pollInfo?.ends_at) })}
            </Text>
          </Space>
        </Card>
        </div>
      </div>
    )
  }

  if (phase === 'already_completed') {
    return (
      <div className="offline-poll-session">
        <PublicBrandHeader />
        <div className="offline-poll-session__content">
        <Card style={cardStyle}>
          <Space direction="vertical" align="center" style={{ width: '100%' }} size="middle">
            <CheckCircleOutlined style={{ fontSize: 48, color: '#52c41a' }} />
            <Title level={3} style={{ margin: 0 }}>
              {t('offlinePoll.alreadyCompleted', "You've already submitted this poll.")}
            </Title>
            <PromoCard />
          </Space>
        </Card>
        </div>
      </div>
    )
  }

  if (phase === 'completed') {
    return (
      <div className="offline-poll-session">
        <PublicBrandHeader />
        <div className="offline-poll-session__content">
        <Card style={cardStyle}>
          <Space direction="vertical" align="center" style={{ width: '100%' }} size="middle">
            <CheckCircleOutlined style={{ fontSize: 56, color: '#52c41a' }} />
            <Title level={2} style={{ margin: 0 }}>
              {t('offlinePoll.thankYouTitle', 'Thank you!')}
            </Title>
            <Paragraph style={{ textAlign: 'center' }}>
              {t('offlinePoll.thankYouDesc', 'Your responses have been recorded.')}
            </Paragraph>
            {pollInfo?.ends_at && (
              <Text type="secondary">
                {t('offlinePoll.closesOn', 'Closes on {{date}}', { date: formatDate(pollInfo.ends_at) })}
              </Text>
            )}
            <PromoCard />
          </Space>
        </Card>
        </div>
      </div>
    )
  }

  // active (join form)
  if (phase === 'active') {
    return (
      <div className="offline-poll-session">
        <PublicBrandHeader />
        <div className="offline-poll-session__content">
        <Card style={cardStyle}>
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Title level={3} style={{ margin: 0 }}>{pollInfo?.title}</Title>
            {pollInfo?.description && <Paragraph>{pollInfo.description}</Paragraph>}
            <Tag color="green" icon={<ClockCircleOutlined />}>
              {t('offlinePoll.statusActive', 'Poll is open')}
            </Tag>
            {pollInfo?.ends_at && (
              <Text type="secondary">
                {t('offlinePoll.closesOn', 'Closes on {{date}}', { date: formatDate(pollInfo.ends_at) })}
              </Text>
            )}
            <Divider />
            <Text>{t('offlinePoll.yourName', 'Your name (optional)')}</Text>
            <Input
              placeholder={t('offlinePoll.yourName', 'Your name (optional)')}
              value={displayName}
              onChange={e => setDisplayName(e.target.value)}
              onPressEnter={handleJoin}
              maxLength={100}
            />
            {error && <Alert type="error" message={error} showIcon />}
            <Button
              type="primary"
              size="large"
              block
              onClick={handleJoin}
              disabled={phase === 'joining'}
            >
              {sessionStorage.getItem(STORAGE_TOKEN_KEY(slug))
                ? t('offlinePoll.resumePoll', 'Resume Poll')
                : t('offlinePoll.startPoll', 'Start Poll')}
            </Button>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {t('offlinePoll.questionCount', '{{total}} questions', { total: pollInfo?.question_count || '?' })}
            </Text>
          </Space>
        </Card>
        </div>
      </div>
    )
  }

  if (phase === 'joining') {
    return (
      <div className="offline-poll-session">
        <PublicBrandHeader />
        <div className="offline-poll-session__content">
          <Spin size="large" style={{ marginTop: 60 }} />
        </div>
      </div>
    )
  }

  // answering phase
  if (phase === 'answering' && questions.length > 0) {
    const question = questions[currentIndex]
    const answer = answers[question.id] || {}
    const isLast = currentIndex === questions.length - 1
    const hasAnswer = answer.selected_option_index !== undefined
      || (Array.isArray(answer.selected_option_indices) && answer.selected_option_indices.length > 0)
      || (answer.text_answer && answer.text_answer.trim())
    const isBlocked = question.is_required && !hasAnswer

    return (
      <ProctoringProvider quizId={pollInfo?.quiz_id} sessionToken={sessionToken}>
        <ProctoringGate>
          <div className="offline-poll-session">
            <PublicBrandHeader />
            <div className="offline-poll-session__content">
            <Card style={cardStyle}>
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            {/* Progress */}
            <Text type="secondary">
              {t('offlinePoll.questionOf', 'Question {{current}} of {{total}}', {
                current: currentIndex + 1,
                total: questions.length,
              })}
            </Text>
            <Progress
              percent={Math.round(((currentIndex + 1) / questions.length) * 100)}
              showInfo={false}
              strokeColor="#1890ff"
            />

            {/* Question text */}
            <VideoEmbed url={question.question_video_url} />
            {question.question_image_url && (
              <img
                src={question.question_image_url}
                alt=""
                style={{ maxWidth: '100%', borderRadius: 8 }}
              />
            )}
            <Space size={4} align="baseline">
              <RichTextRenderer content={question.text} isDark={theme === 'dark'} />
              {question.is_required && (
                <Text type="danger" style={{ fontWeight: 600 }}>*</Text>
              )}
            </Space>
            {isBlocked && (
              <Alert
                type="warning"
                message={t('offlinePoll.requiredWarning', 'This question is required. Please answer it to continue.')}
                showIcon
                style={{ marginTop: 4 }}
              />
            )}

            {/* MCQ options */}
            {question.question_type === 'mcq' && (
              <Radio.Group
                value={answer.selected_option_index}
                onChange={e => handleAnswerChange(question.id, 'selected_option_index', e.target.value)}
                style={{ width: '100%' }}
              >
                <Space direction="vertical" style={{ width: '100%' }}>
                  {(question.options || []).map((opt, idx) => (
                    <Radio
                      key={idx}
                      value={idx}
                      style={{
                        display: 'block',
                        padding: '8px 12px',
                        borderRadius: 8,
                        border: '1px solid var(--poll-border)',
                        marginBottom: 4,
                        background: answer.selected_option_index === idx ? 'var(--poll-radio-selected)' : 'var(--poll-surface)',
                      }}
                    >
                      <Space>
                        {question.option_images?.[['A', 'B', 'C', 'D', 'E'][idx]] && (
                          <img
                            src={question.option_images[['A', 'B', 'C', 'D', 'E'][idx]]}
                            alt=""
                            style={{ maxWidth: 60, borderRadius: 4 }}
                          />
                        )}
                        {opt}
                      </Space>
                    </Radio>
                  ))}
                </Space>
              </Radio.Group>
            )}

            {/* Multi-select MCQ options */}
            {question.question_type === 'mcq_multi' && (
              <>
                <Text type="secondary" style={{ display: 'block' }}>
                  {question.required_answer_count
                    ? t('quiz.chooseCorrectCount', { count: question.required_answer_count, defaultValue: 'Choose the correct {{count}} answers' })
                    : t('quiz.selectAllThatApply', 'Select all that apply')}
                </Text>
                <Checkbox.Group
                  value={answer.selected_option_indices || []}
                  onChange={vals => handleAnswerChange(question.id, 'selected_option_indices', vals)}
                  style={{ width: '100%' }}
                >
                  <Space direction="vertical" style={{ width: '100%' }}>
                    {(question.options || []).map((opt, idx) => (
                      <Checkbox
                        key={idx}
                        value={idx}
                        style={{
                          display: 'block',
                          padding: '8px 12px',
                          borderRadius: 8,
                          border: '1px solid var(--poll-border)',
                          marginBottom: 4,
                          background: (answer.selected_option_indices || []).includes(idx) ? 'var(--poll-radio-selected)' : 'var(--poll-surface)',
                        }}
                      >
                        <Space>
                          {question.option_images?.[['A', 'B', 'C', 'D', 'E'][idx]] && (
                            <img
                              src={question.option_images[['A', 'B', 'C', 'D', 'E'][idx]]}
                              alt=""
                              style={{ maxWidth: 60, borderRadius: 4 }}
                            />
                          )}
                          {opt}
                        </Space>
                      </Checkbox>
                    ))}
                  </Space>
                </Checkbox.Group>
              </>
            )}

            {/* Text-based question types */}
            {(question.question_type === 'word_cloud' ||
              question.question_type === 'single_line' ||
              question.question_type === 'paragraph') && (
              question.question_type === 'paragraph' ? (
                <TextArea
                  rows={4}
                  placeholder={t('common.typeHere', 'Type your answer here...')}
                  value={answer.text_answer || ''}
                  onChange={e => handleAnswerChange(question.id, 'text_answer', e.target.value)}
                  maxLength={2000}
                  showCount
                />
              ) : (
                <Input
                  placeholder={t('common.typeHere', 'Type your answer here...')}
                  value={answer.text_answer || ''}
                  onChange={e => handleAnswerChange(question.id, 'text_answer', e.target.value)}
                  maxLength={question.question_type === 'word_cloud' ? 200 : 500}
                />
              )
            )}

            {/* Scale question */}
            {question.question_type === 'scale' && (
              <Radio.Group
                value={answer.selected_option_index}
                onChange={e => handleAnswerChange(question.id, 'selected_option_index', e.target.value)}
              >
                <Row gutter={8} justify="center">
                  {(question.options || ['1', '2', '3', '4', '5']).map((opt, idx) => (
                    <Col key={idx}>
                      <Radio.Button value={idx}>{opt}</Radio.Button>
                    </Col>
                  ))}
                </Row>
              </Radio.Group>
            )}

            <Divider />

            {/* Navigation */}
            <Row gutter={12}>
              <Col span={12}>
                <Button
                  block
                  disabled={currentIndex === 0 || saving}
                  onClick={handleBack}
                >
                  {t('offlinePoll.back', 'Back')}
                </Button>
              </Col>
              <Col span={12}>
                {isLast ? (
                  <Button
                    type="primary"
                    block
                    loading={submitting}
                    disabled={isBlocked}
                    onClick={handleSubmit}
                  >
                    {t('offlinePoll.submitPoll', 'Submit Poll')}
                  </Button>
                ) : (
                  <Button
                    type="primary"
                    block
                    loading={saving}
                    disabled={isBlocked}
                    onClick={handleNext}
                  >
                    {t('offlinePoll.next', 'Next')}
                  </Button>
                )}
              </Col>
            </Row>

            {saving && (
              <Text type="secondary" style={{ fontSize: 12, textAlign: 'center', display: 'block' }}>
                {t('offlinePoll.submitting', 'Saving...')}
              </Text>
            )}
          </Space>
        </Card>
        </div>
      </div>
        </ProctoringGate>
      </ProctoringProvider>
    )
  }

  return null
}

