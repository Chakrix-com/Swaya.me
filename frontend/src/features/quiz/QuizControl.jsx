import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
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
  Input
} from 'antd'
import {
  PlayCircleOutlined,
  ArrowRightOutlined,
  CloseCircleOutlined,
  LeftOutlined,
  TeamOutlined,
  CheckCircleOutlined,
  CopyOutlined
} from '@ant-design/icons'
import { QRCodeCanvas } from 'qrcode.react'
import { sessionAPI, quizAPI } from '../../services/api'

const { Title, Text } = Typography

export default function QuizControl() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [quiz, setQuiz] = useState(null)
  const [session, setSession] = useState(null)
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (id) {
      loadQuiz()
    }
  }, [id])

  useEffect(() => {
    if (session) {
      const interval = setInterval(loadResults, 3000) // Refresh every 3 seconds
      return () => clearInterval(interval)
    }
  }, [session])

  const loadQuiz = async () => {
    try {
      const response = await quizAPI.get(id)
      setQuiz(response.data)
    } catch (error) {
      message.error('Failed to load quiz')
      console.error(error)
    }
  }

  const loadResults = async () => {
    if (!session) return
    try {
      const response = await sessionAPI.getResults(session.id, session.session_token)
      setResults(response.data)
    } catch (error) {
      console.error('Failed to load results', error)
    }
  }

  const handleStartSession = async () => {
    setLoading(true)
    try {
      const response = await sessionAPI.start(id)
      setSession(response.data)
      message.success('Session started! Share the join code with participants.')
    } catch (error) {
      message.error(error.response?.data?.detail || 'Failed to start session')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleAdvanceQuestion = async () => {
    setLoading(true)
    try {
      await sessionAPI.advance(session.id)
      message.success('Moved to next question')
      loadResults()
    } catch (error) {
      message.error(error.response?.data?.detail || 'Failed to advance question')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleEndSession = async () => {
    setLoading(true)
    try {
      await sessionAPI.end(session.id)
      message.success('Session ended')
      navigate('/dashboard')
    } catch (error) {
      message.error('Failed to end session')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const copyJoinLink = () => {
    const inputElement = document.getElementById('join-url-input')
    if (!inputElement || !inputElement.value) {
      message.error('No URL to copy')
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
        message.success('Link copied to clipboard!')
      } else {
        message.error('Please copy manually')
      }
    } catch (err) {
      console.error('Copy failed:', err)
      document.body.removeChild(textarea)
      message.error('Please copy manually')
    }
  }

  if (!quiz) {
    return <div style={{ padding: 24 }}>Loading...</div>
  }

  const currentQuestion = results?.current_question

  return (
    <div style={{ padding: 24 }}>
      <Space style={{ marginBottom: 24, width: '100%', justifyContent: 'space-between' }}>
        <Button
          icon={<LeftOutlined />}
          onClick={() => navigate('/dashboard')}
        >
          Back to Dashboard
        </Button>
        {session && session.status === 'active' && (
          <Button
            danger
            icon={<CloseCircleOutlined />}
            onClick={handleEndSession}
            loading={loading}
          >
            End Session
          </Button>
        )}
      </Space>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={24} md={24} lg={16} xl={16}>
          <Card>
            <Title level={2} style={{ marginBottom: 8 }}>{quiz.title}</Title>
            {quiz.description && <Text type="secondary">{quiz.description}</Text>}
          </Card>
        </Col>
        <Col xs={12} sm={12} md={12} lg={4} xl={4}>
          <Card style={{ height: '100%' }}>
            <Statistic
              title="Participants"
              value={results?.total_participants || 0}
              prefix={<TeamOutlined />}
              valueStyle={{ fontSize: 28 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={12} md={12} lg={4} xl={4}>
          <Card style={{ height: '100%', minHeight: 100 }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 14, color: '#00000073', marginBottom: 8 }}>Status</div>
              <div style={{ fontSize: 24, fontWeight: 600, color: session?.status === 'active' ? '#52c41a' : '#faad14' }}>
                {session?.status ? session.status.toUpperCase() : 'READY'}
              </div>
              {session && (
                <Tag color={session.status === 'active' ? 'green' : 'orange'} style={{ marginTop: 8 }}>
                  {session.status === 'active' ? 'LIVE' : 'ENDED'}
                </Tag>
              )}
            </div>
          </Card>
        </Col>
      </Row>

      {!session ? (
        <Card>
          <Space direction="vertical" align="center" style={{ width: '100%' }}>
            <Title level={3}>Ready to Start?</Title>
            <Text>Start the session to allow participants to join.</Text>
            <Button
              type="primary"
              size="large"
              icon={<PlayCircleOutlined />}
              onClick={handleStartSession}
              loading={loading}
            >
              Start Session
            </Button>
          </Space>
        </Card>
      ) : (
        <>
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col xs={24} lg={24}>
              <Card title="Join Information">
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
                          Join URL:
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
                          Copy Join Link
                        </Button>
                      </div>
                    </Space>
                  </Col>
                  <Col xs={24} md={8}>
                    <div style={{ textAlign: 'center' }}>
                      <Statistic
                        title="Join Code"
                        value={session.join_code}
                        valueStyle={{ color: '#3f8600', fontSize: 32, fontWeight: 'bold' }}
                      />
                      <Text type="secondary" style={{ fontSize: 12 }}>Enter this code at /join</Text>
                    </div>
                  </Col>
                </Row>
              </Card>
            </Col>
          </Row>

          {currentQuestion ? (
            <Card
              title={
                <Space>
                  <Tag color="blue">Question {results.current_question_index + 1} of {quiz.questions?.length}</Tag>
                  <Text strong>{currentQuestion.text}</Text>
                </Space>
              }
              extra={
                session.status === 'active' && (
                  <Button
                    type="primary"
                    icon={results.current_question_index < (quiz.questions?.length - 1) ? <ArrowRightOutlined /> : <CheckCircleOutlined />}
                    onClick={handleAdvanceQuestion}
                    loading={loading}
                  >
                    {results.current_question_index < (quiz.questions?.length - 1) ? 'Next Question' : 'Finish'}
                  </Button>
                )
              }
              style={{ marginBottom: 24 }}
            >
              <Alert
                message={`${currentQuestion.total_answers || 0} responses received`}
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />

              <Space direction="vertical" style={{ width: '100%' }} size="large">
                <div>
                  <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 8 }}>
                    <Text strong>A: {currentQuestion.option_a}</Text>
                    <Text>{currentQuestion.answer_distribution?.[0] || 0} responses ({((currentQuestion.answer_distribution?.[0] / currentQuestion.total_answers * 100) || 0).toFixed(1)}%)</Text>
                  </Space>
                  <Progress
                    percent={((currentQuestion.answer_distribution?.[0] / currentQuestion.total_answers * 100) || 0)}
                    strokeColor={currentQuestion.correct_answer === 'A' ? '#52c41a' : '#1890ff'}
                  />
                </div>

                <div>
                  <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 8 }}>
                    <Text strong>B: {currentQuestion.option_b}</Text>
                    <Text>{currentQuestion.answer_distribution?.[1] || 0} responses ({((currentQuestion.answer_distribution?.[1] / currentQuestion.total_answers * 100) || 0).toFixed(1)}%)</Text>
                  </Space>
                  <Progress
                    percent={((currentQuestion.answer_distribution?.[1] / currentQuestion.total_answers * 100) || 0)}
                    strokeColor={currentQuestion.correct_answer === 'B' ? '#52c41a' : '#1890ff'}
                  />
                </div>

                <div>
                  <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 8 }}>
                    <Text strong>C: {currentQuestion.option_c}</Text>
                    <Text>{currentQuestion.answer_distribution?.[2] || 0} responses ({((currentQuestion.answer_distribution?.[2] / currentQuestion.total_answers * 100) || 0).toFixed(1)}%)</Text>
                  </Space>
                  <Progress
                    percent={((currentQuestion.answer_distribution?.[2] / currentQuestion.total_answers * 100) || 0)}
                    strokeColor={currentQuestion.correct_answer === 'C' ? '#52c41a' : '#1890ff'}
                  />
                </div>

                <div>
                  <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 8 }}>
                    <Text strong>D: {currentQuestion.option_d}</Text>
                    <Text>{currentQuestion.answer_distribution?.[3] || 0} responses ({((currentQuestion.answer_distribution?.[3] / currentQuestion.total_answers * 100) || 0).toFixed(1)}%)</Text>
                  </Space>
                  <Progress
                    percent={((currentQuestion.answer_distribution?.[3] / currentQuestion.total_answers * 100) || 0)}
                    strokeColor={currentQuestion.correct_answer === 'D' ? '#52c41a' : '#1890ff'}
                  />
                </div>

                <Alert
                  message={`Correct Answer: ${currentQuestion.correct_answer}`}
                  description={`${currentQuestion[`option_${currentQuestion.correct_answer.toLowerCase()}`]}`}
                  type="success"
                  showIcon
                />
              </Space>
            </Card>
          ) : session && results && results.current_question_index === -1 ? (
            <Card>
              <Space direction="vertical" align="center" style={{ width: '100%' }}>
                <Title level={4}>Ready to Start!</Title>
                <Text>Click "Advance Question" to show the first question to participants.</Text>
                <Button
                  type="primary"
                  size="large"
                  icon={<ArrowRightOutlined />}
                  onClick={handleAdvanceQuestion}
                  loading={loading}
                >
                  Start First Question
                </Button>
              </Space>
            </Card>
          ) : (
            <Card>
              <Space direction="vertical" align="center" style={{ width: '100%' }}>
                <Title level={4}>Session Complete!</Title>
                <Text>All questions have been answered.</Text>
                <Button
                  type="primary"
                  onClick={() => navigate('/dashboard')}
                >
                  Back to Dashboard
                </Button>
              </Space>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
