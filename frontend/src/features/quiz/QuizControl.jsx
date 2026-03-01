import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  Card,
  Button,
  Space,
  Typography,
  Tag,
  Statistic,
  Row,
  Col,
  Progress,
  message,
  Alert,
  Input,
  Rate,
  Table
} from 'antd'
import {
  PlayCircleOutlined,
  ArrowRightOutlined,
  CloseCircleOutlined,
  LeftOutlined,
  TeamOutlined,
  CheckCircleOutlined,
  CopyOutlined,
  TrophyOutlined
} from '@ant-design/icons'
import { QRCodeCanvas } from 'qrcode.react'
import ReactWordcloud from 'react-wordcloud'
import { sessionAPI, quizAPI, questionAPI, feedbackAPI } from '../../services/api'
import './QuizControl.css'

const { Title, Text } = Typography
const { TextArea } = Input

export default function QuizControl() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [quiz, setQuiz] = useState(null)
  const [session, setSession] = useState(null)
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [wordCloudData, setWordCloudData] = useState([])
  const [leaderboard, setLeaderboard] = useState(null)
  const [feedbackText, setFeedbackText] = useState('')
  const [feedbackRating, setFeedbackRating] = useState(0)
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false)
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false)

  useEffect(() => {
    if (id) {
      loadQuiz()
    }
  }, [id])

  useEffect(() => {
    if (session) {
      loadResults() // Immediate first load
      const interval = setInterval(loadResults, 3000) // Refresh every 3 seconds
      return () => clearInterval(interval)
    }
  }, [session])

  const loadQuiz = async () => {
    try {
      const response = await quizAPI.get(id)
      setQuiz(response.data)
    } catch (error) {
      message.error(t('quiz.failedToLoadQuiz'))
      console.error(error)
    }
  }

  const loadResults = async () => {
    if (!session) return
    try {
      const response = await sessionAPI.getResults(session.id, session.session_token)
      setResults(response.data)

      // If current question is word cloud, fetch word cloud data
      if (response.data.current_question?.question_type === 'word_cloud') {
        loadWordCloudData(response.data.current_question.id)
      }
    } catch (error) {
      console.error(t('quiz.failedToLoadResults'), error)
    }
    // Leaderboard is non-critical — fetch independently so it never blocks results
    sessionAPI.getLeaderboard(session.id, null)
      .then(res => setLeaderboard(res.data))
      .catch(() => {})
  }

  const loadWordCloudData = async (questionId) => {
    if (!session) return
    try {
      const response = await questionAPI.getWordCloudResults(questionId, session.id)
      // Transform dict {word: count} to array [{text, value}] for react-wordcloud
      const words = Object.entries(response.data.word_frequencies).map(([word, count]) => ({
        text: word,
        value: count
      }))
      setWordCloudData(words)
    } catch (error) {
      console.error('Failed to load word cloud data:', error)
    }
  }

  const handleStartSession = async () => {
    setLoading(true)
    try {
      const response = await sessionAPI.start(id)
      setSession(response.data)
      message.success(t('quiz.sessionStarted'))
    } catch (error) {
      message.error(error.response?.data?.detail || t('quiz.failedToStart'))
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleAdvanceQuestion = async () => {
    setLoading(true)
    try {
      await sessionAPI.advance(session.id)
      message.success(t('quiz.movedToNextQuestion'))
      await loadResults()
    } catch (error) {
      message.error(error.response?.data?.detail || t('quiz.failedToAdvance'))
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleBackQuestion = async () => {
    setLoading(true)
    try {
      await sessionAPI.back(session.id)
      message.success(t('quiz.movedToPreviousQuestion'))
      await loadResults()
    } catch (error) {
      message.error(error.response?.data?.detail || t('quiz.failedToGoBack'))
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleEndSession = async () => {
    setLoading(true)
    try {
      await sessionAPI.end(session.id)
      message.success(t('quiz.sessionEnded'))
      navigate('/dashboard')
    } catch (error) {
      message.error(t('quiz.failedToEnd'))
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const getStatusTranslation = (status) => {
    if (!status) return t('quiz.ready')
    const statusKey = status.toLowerCase()
    return t(`quiz.${statusKey}`)
  }

  const copyJoinLink = () => {
    const inputElement = document.getElementById('join-url-input')
    if (!inputElement || !inputElement.value) {
      message.error(t('quiz.noUrlToCopy'))
      return
    }

    const joinUrl = inputElement.value
    
    // Safari workaround: Create temporary textarea (not readonly)
    const textarea = document.createElement('textarea')
    textarea.value = joinUrl
    textarea.style.position = 'fixed'
    textarea.style.top = '0'
    textarea.style.left = '0'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    
    try {
      // Focus and select the textarea
      textarea.focus()
      textarea.select()
      textarea.setSelectionRange(0, textarea.value.length)
      
      // Execute copy command
      const successful = document.execCommand('copy')
      
      // Clean up
      document.body.removeChild(textarea)
      
      if (successful) {
        message.success(t('quiz.linkCopied'))
      } else {
        message.error(t('quiz.copyManually'))
      }
    } catch (err) {
      console.error('Copy failed:', err)
      document.body.removeChild(textarea)
      message.error(t('quiz.copyManually'))
    }
  }

  const handleSubmitFeedback = async () => {
    if (!feedbackText.trim()) return
    setFeedbackSubmitting(true)
    try {
      await feedbackAPI.submitUser({
        quiz_id: Number(id),
        session_id: session?.id,
        rating: feedbackRating || undefined,
        feedback_text: feedbackText.trim(),
      })
      setFeedbackSubmitted(true)
      message.success('Feedback submitted')
    } catch (error) {
      message.error(error.response?.data?.detail || 'Failed to submit feedback')
    } finally {
      setFeedbackSubmitting(false)
    }
  }

  if (!quiz) {
    return <div style={{ padding: 24 }}>{t('common.loading')}</div>
  }

  const currentQuestion = results?.current_question

  return (
    <div className="quiz-control-page" style={{ padding: 24 }}>
      <Space wrap className="quiz-control-topbar">
        <Button
          icon={<LeftOutlined />}
          onClick={() => navigate('/dashboard')}
        >
          {t('quiz.backDashboard')}
        </Button>
        {session && session.status === 'active' && (
          <Button
            danger
            icon={<CloseCircleOutlined />}
            onClick={handleEndSession}
            loading={loading}
          >
            {t('quiz.endSession')}
          </Button>
        )}
      </Space>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={24} md={24} lg={14} xl={14}>
          <Card>
            <Title level={2} style={{ marginBottom: 8 }}>{quiz.title}</Title>
            {quiz.description && <Text type="secondary">{quiz.description}</Text>}
          </Card>
        </Col>
        <Col xs={12} sm={12} md={12} lg={4} xl={4}>
          <Card style={{ height: '100%' }}>
            <div style={{ textAlign: 'center' }}>
              <Statistic
                title={t('quiz.participants')}
                value={results?.total_participants || 0}
                prefix={<TeamOutlined />}
                valueStyle={{ fontSize: 28 }}
              />
            </div>
          </Card>
        </Col>
        <Col xs={12} sm={12} md={12} lg={6} xl={6}>
          <Card style={{ height: '100%', minHeight: 100 }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 14, color: '#00000073', marginBottom: 8 }}>{t('quiz.status')}</div>
              <div style={{ fontSize: 24, fontWeight: 600, color: session?.status === 'active' ? '#52c41a' : '#faad14' }}>
                {getStatusTranslation(session?.status)}
              </div>
              {session && (
                <Tag color={session.status === 'active' ? 'green' : 'orange'} style={{ marginTop: 8 }}>
                  {session.status === 'active' ? t('quiz.live') : t('quiz.ended')}
                </Tag>
              )}
            </div>
          </Card>
        </Col>
      </Row>

      {!session ? (
        <Card>
          <Space direction="vertical" align="center" style={{ width: '100%' }}>
            <Title level={3}>{t('quiz.readyToStart')}</Title>
            <Text>{t('quiz.startSessionDesc')}</Text>
            <Button
              type="primary"
              size="large"
              icon={<PlayCircleOutlined />}
              onClick={handleStartSession}
              loading={loading}
            >
              {t('quiz.startSession')}
            </Button>
          </Space>
        </Card>
      ) : (
        <>
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col xs={24} lg={24}>
              <Card title={t('quiz.joinInformation')}>
                <Row gutter={16}>
                  <Col xs={24} md={8} style={{ textAlign: 'center' }}>
                    <QRCodeCanvas
                      value={`${window.location.origin}/join/${session.join_code}`}
                      size={160}
                      level="H"
                      includeMargin={true}
                    />
                  </Col>
                  <Col xs={24} md={8}>
                    <Space direction="vertical" style={{ width: '100%' }} size="middle">
                      <div>
                        <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
                          {t('quiz.joinUrl')}
                        </Text>
                        <Input
                          id="join-url-input"
                          value={`${window.location.origin}/join/${session.join_code}`}
                          readOnly
                          size="large"
                          style={{ marginBottom: 8 }}
                        />
                        <Button
                          type="primary"
                          icon={<CopyOutlined />}
                          onClick={copyJoinLink}
                          block
                        >
                          {t('quiz.copyJoinLink')}
                        </Button>
                      </div>
                    </Space>
                  </Col>
                  <Col xs={24} md={8}>
                    <div style={{ textAlign: 'center' }}>
                      <Statistic
                        title={t('quiz.joinCode')}
                        value={session.join_code}
                        valueStyle={{ color: '#3f8600', fontSize: 32, fontWeight: 'bold' }}
                      />
                      <Text type="secondary" style={{ fontSize: 12 }}>{t('quiz.enterCodeAt')}</Text>
                    </div>
                  </Col>
                </Row>
              </Card>
            </Col>
          </Row>

          {leaderboard && (
            <Card
              title={
                <Space>
                  <TrophyOutlined style={{ color: '#faad14' }} />
                  <span>{t('leaderboard.title')}</span>
                  {leaderboard.total_participants > 0 && (
                    <Tag color="blue">{leaderboard.total_participants} {t('quiz.participants')}</Tag>
                  )}
                  {leaderboard.mcq_question_count > 0 && (
                    <Tag color="default">{t('leaderboard.mcqOnly')}</Tag>
                  )}
                </Space>
              }
              style={{ marginBottom: 24 }}
            >
              {leaderboard.entries.length === 0 ? (
                <Text type="secondary">{t('leaderboard.noData')}</Text>
              ) : (
                <>
                  <Table
                    dataSource={leaderboard.entries.slice(0, 10)}
                    rowKey="participant_id"
                    pagination={false}
                    size="small"
                    columns={[
                      {
                        title: t('leaderboard.rank'),
                        dataIndex: 'rank',
                        width: 60,
                        render: (rank) => {
                          const colors = { 1: '#FFD700', 2: '#C0C0C0', 3: '#CD7F32' }
                          return (
                            <Tag color={colors[rank] ? undefined : 'default'} style={colors[rank] ? { backgroundColor: colors[rank], color: '#000', borderColor: colors[rank] } : {}}>
                              {rank}
                            </Tag>
                          )
                        }
                      },
                      {
                        title: t('leaderboard.participant'),
                        dataIndex: 'display_name',
                        ellipsis: true,
                      },
                      {
                        title: `${t('leaderboard.score')} / ${leaderboard.mcq_question_count}`,
                        dataIndex: 'score',
                        width: 100,
                        render: (score) => <Tag color="green">{score}</Tag>
                      }
                    ]}
                  />
                  {leaderboard.entries.length > 10 && (
                    <div style={{ textAlign: 'center', marginTop: 8, color: '#888', fontSize: 12 }}>
                      +{leaderboard.entries.length - 10} more participants
                    </div>
                  )}
                </>
              )}
            </Card>
          )}

          {currentQuestion ? (
            <Card
              title={
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Space>
                    <Tag color="blue">{t('quiz.questionOf')} {results.current_question_index + 1} {t('quiz.of')} {quiz.questions?.length}</Tag>
                    {currentQuestion.question_type === 'word_cloud' && <Tag color="purple">Word Cloud</Tag>}
                  </Space>
                  {currentQuestion.question_image_url && (
                    <img 
                      src={currentQuestion.question_image_url} 
                      alt="Question" 
                      style={{ 
                        maxWidth: '100%', 
                        maxHeight: '300px', 
                        borderRadius: '8px',
                        marginTop: '8px',
                        display: 'block'
                      }} 
                    />
                  )}
                  <Text strong style={{ display: 'block', marginTop: currentQuestion.question_image_url ? '8px' : '0' }}>
                    {currentQuestion.text}
                  </Text>
                </Space>
              }
              style={{ marginBottom: 24 }}
            >
              <Alert
                message={`${currentQuestion.total_answers || 0} ${t('quiz.responsesReceived')}`}
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />

              {currentQuestion.question_type === 'word_cloud' ? (
                // Word Cloud Question View
                <Space direction="vertical" style={{ width: '100%' }} size="large">
                  <Alert
                    message="Word Cloud Question"
                    description={`${currentQuestion.total_answers || 0} ${t('quiz.responsesReceived')}`}
                    type="info"
                    showIcon
                  />
                  
                  {wordCloudData.length > 0 ? (
                    <div style={{ 
                      width: '100%', 
                      height: '400px', 
                      border: '1px solid #d9d9d9',
                      borderRadius: '8px',
                      padding: '16px',
                      backgroundColor: '#fafafa'
                    }}>
                      <ReactWordcloud
                        words={wordCloudData}
                        options={{
                          rotations: 2,
                          rotationAngles: [0, 90],
                          fontSizes: [20, 80],
                          padding: 5,
                          enableTooltip: true,
                          deterministic: true,
                          fontFamily: 'Arial',
                          colors: ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#eb2f96']
                        }}
                      />
                    </div>
                  ) : (
                    <Alert
                      message="No responses yet"
                      description="Word cloud will appear once participants start submitting answers."
                      type="warning"
                    />
                  )}
                </Space>
              ) : (
                // MCQ Question View
                <Space direction="vertical" style={{ width: '100%' }} size="large">
                  <div>
                    <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 8, alignItems: 'flex-start' }}>
                      <Space direction="vertical">
                        <Text strong>A: {currentQuestion.option_a}</Text>
                        {currentQuestion.option_images?.A && (
                          <img 
                            src={currentQuestion.option_images.A} 
                            alt="Option A" 
                            style={{ maxWidth: '200px', maxHeight: '150px', borderRadius: '4px', marginTop: '4px' }} 
                          />
                        )}
                      </Space>
                      <Text>{currentQuestion.answer_distribution?.[0] || 0} {t('quiz.responses')} ({((currentQuestion.answer_distribution?.[0] / currentQuestion.total_answers * 100) || 0).toFixed(1)}%)</Text>
                    </Space>
                    <Progress
                      percent={((currentQuestion.answer_distribution?.[0] / currentQuestion.total_answers * 100) || 0)}
                      strokeColor={currentQuestion.correct_answer === 'A' ? '#52c41a' : '#1890ff'}
                    />
                  </div>

                  <div>
                    <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 8, alignItems: 'flex-start' }}>
                      <Space direction="vertical">
                        <Text strong>B: {currentQuestion.option_b}</Text>
                        {currentQuestion.option_images?.B && (
                          <img 
                            src={currentQuestion.option_images.B} 
                            alt="Option B" 
                            style={{ maxWidth: '200px', maxHeight: '150px', borderRadius: '4px', marginTop: '4px' }} 
                          />
                        )}
                      </Space>
                      <Text>{currentQuestion.answer_distribution?.[1] || 0} {t('quiz.responses')} ({((currentQuestion.answer_distribution?.[1] / currentQuestion.total_answers * 100) || 0).toFixed(1)}%)</Text>
                    </Space>
                    <Progress
                      percent={((currentQuestion.answer_distribution?.[1] / currentQuestion.total_answers * 100) || 0)}
                      strokeColor={currentQuestion.correct_answer === 'B' ? '#52c41a' : '#1890ff'}
                    />
                  </div>

                  <div>
                    <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 8, alignItems: 'flex-start' }}>
                      <Space direction="vertical">
                        <Text strong>C: {currentQuestion.option_c}</Text>
                        {currentQuestion.option_images?.C && (
                          <img 
                            src={currentQuestion.option_images.C} 
                            alt="Option C" 
                            style={{ maxWidth: '200px', maxHeight: '150px', borderRadius: '4px', marginTop: '4px' }} 
                          />
                        )}
                      </Space>
                      <Text>{currentQuestion.answer_distribution?.[2] || 0} {t('quiz.responses')} ({((currentQuestion.answer_distribution?.[2] / currentQuestion.total_answers * 100) || 0).toFixed(1)}%)</Text>
                    </Space>
                    <Progress
                      percent={((currentQuestion.answer_distribution?.[2] / currentQuestion.total_answers * 100) || 0)}
                      strokeColor={currentQuestion.correct_answer === 'C' ? '#52c41a' : '#1890ff'}
                    />
                  </div>

                  <div>
                    <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 8, alignItems: 'flex-start' }}>
                      <Space direction="vertical">
                        <Text strong>D: {currentQuestion.option_d}</Text>
                        {currentQuestion.option_images?.D && (
                          <img 
                            src={currentQuestion.option_images.D} 
                            alt="Option D" 
                            style={{ maxWidth: '200px', maxHeight: '150px', borderRadius: '4px', marginTop: '4px' }} 
                          />
                        )}
                      </Space>
                      <Text>{currentQuestion.answer_distribution?.[3] || 0} {t('quiz.responses')} ({((currentQuestion.answer_distribution?.[3] / currentQuestion.total_answers * 100) || 0).toFixed(1)}%)</Text>
                    </Space>
                    <Progress
                      percent={((currentQuestion.answer_distribution?.[3] / currentQuestion.total_answers * 100) || 0)}
                      strokeColor={currentQuestion.correct_answer === 'D' ? '#52c41a' : '#1890ff'}
                    />
                  </div>

                  <Alert
                    message={`${t('quiz.correctAnswer')}: ${currentQuestion.correct_answer}`}
                    description={`${currentQuestion[`option_${currentQuestion.correct_answer.toLowerCase()}`]}`}
                    type="success"
                    showIcon
                  />
                </Space>
              )}

              <div style={{ marginTop: 24, display: 'flex', justifyContent: 'center', gap: 16 }}>
                <Button
                  type="default"
                  size="large"
                  icon={<LeftOutlined />}
                  onClick={handleBackQuestion}
                  loading={loading}
                  disabled={results.current_question_index === 0}
                >
                  {t('quiz.previousQuestion')}
                </Button>
                <Button
                  type="primary"
                  size="large"
                  icon={results.current_question_index < (quiz.questions?.length - 1) ? <ArrowRightOutlined /> : <CheckCircleOutlined />}
                  onClick={handleAdvanceQuestion}
                  loading={loading}
                >
                  {results.current_question_index < (quiz.questions?.length - 1) ? t('quiz.nextQuestion') : t('quiz.finish')}
                </Button>
              </div>
            </Card>
          ) : !results || results.current_question_index === -1 ? (
            <Card>
              <Space direction="vertical" align="center" style={{ width: '100%' }}>
                <Title level={4}>{t('quiz.readyToStartFirst')}</Title>
                <Text>{t('quiz.clickAdvanceToStart')}</Text>
                <Button
                  type="primary"
                  size="large"
                  icon={<ArrowRightOutlined />}
                  onClick={handleAdvanceQuestion}
                  loading={loading}
                >
                  {t('quiz.startFirstQuestion')}
                </Button>
              </Space>
            </Card>
          ) : (
            <Card>
              <Space direction="vertical" align="center" style={{ width: '100%' }} size="large">
                <Title level={4}>{t('quiz.sessionComplete')}</Title>
                <Text>{t('quiz.allQuestionsAnswered')}</Text>
                <Card size="small" style={{ width: '100%', maxWidth: 620 }}>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Text strong>Share Feedback</Text>
                    <Rate value={feedbackRating} onChange={setFeedbackRating} disabled={feedbackSubmitted} />
                    <TextArea
                      rows={4}
                      value={feedbackText}
                      onChange={(e) => setFeedbackText(e.target.value)}
                      maxLength={500}
                      showCount
                      disabled={feedbackSubmitted}
                      placeholder="Share your experience running this quiz"
                    />
                    <Button
                      type="primary"
                      onClick={handleSubmitFeedback}
                      loading={feedbackSubmitting}
                      disabled={feedbackSubmitted || !feedbackText.trim()}
                    >
                      {feedbackSubmitted ? 'Feedback Submitted' : 'Submit Feedback'}
                    </Button>
                  </Space>
                </Card>
                <Button
                  type="primary"
                  icon={<LeftOutlined />}
                  onClick={() => navigate('/dashboard')}
                >
                  {t('quiz.backDashboard')}
                </Button>
              </Space>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
