import { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useSelector } from 'react-redux'
import {
  Card,
  Radio,
  Button,
  Space,
  Typography,
  Tag,
  Alert,
  Result,
  Progress
} from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined
} from '@ant-design/icons'
import { sessionAPI } from '../../services/api'

const { Title, Text } = Typography

export default function AudienceSession() {
  const location = useLocation()
  const navigate = useNavigate()
  const reduxSession = useSelector((state) => state.session.session)
  
  // Try to get session from location.state first, then fall back to Redux
  const locationState = location.state || {}
  const sessionToken = locationState.sessionToken || reduxSession?.session_token
  const sessionId = locationState.sessionId || reduxSession?.session_id
  const displayName = locationState.displayName || reduxSession?.display_name || 'Guest'

  const [session, setSession] = useState(null)
  const [currentQuestion, setCurrentQuestion] = useState(null)
  const [selectedAnswer, setSelectedAnswer] = useState(null)
  const [submitted, setSubmitted] = useState(false)
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (sessionToken && sessionId) {
      const interval = setInterval(loadResults, 2000) // Poll every 2 seconds
      loadResults()
      return () => clearInterval(interval)
    }
  }, [sessionToken, sessionId])

  const loadResults = async () => {
    if (!sessionToken || !sessionId) {
      console.log('Missing sessionToken or sessionId:', { sessionToken, sessionId })
      return
    }
    console.log('Loading results for session:', sessionId, 'with token:', sessionToken)
    try {
      const response = await sessionAPI.getResults(sessionId, sessionToken)
      console.log('Results received:', response.data)
      
      // Get question IDs for comparison BEFORE updating state
      const newQuestionId = response.data.current_question?.id
      const oldQuestionId = currentQuestion?.id
      
      console.log('Question IDs:', { newQuestionId, oldQuestionId, selectedAnswer, submitted })
      
      // Only reset if:
      // 1. We have a new question ID
      // 2. We had an old question ID (not first load)
      // 3. They are different
      if (oldQuestionId && newQuestionId && newQuestionId !== oldQuestionId) {
        console.log('Question changed from', oldQuestionId, 'to', newQuestionId, '- resetting state')
        setSubmitted(false)
        setSelectedAnswer(null)
      } else {
        console.log('Question unchanged or first load - keeping state')
      }
      
      setResults(response.data)
      setCurrentQuestion(response.data.current_question)
    } catch (error) {
      console.error('Failed to load results', error)
    }
  }

  const handleSubmitAnswer = async () => {
    console.log('handleSubmitAnswer called, selectedAnswer:', selectedAnswer)
    if (!selectedAnswer) {
      console.log('No answer selected, returning')
      return
    }

    setLoading(true)
    try {
      // Convert answer letter (A,B,C,D) to index (0,1,2,3)
      const answerIndex = selectedAnswer.charCodeAt(0) - 65 // A=0, B=1, C=2, D=3
      console.log('Submitting answer:', { selectedAnswer, answerIndex, question_id: currentQuestion.id })
      
      await sessionAPI.submitAnswer(sessionToken, {
        question_id: currentQuestion.id,
        selected_option_index: answerIndex
      })
      console.log('Answer submitted successfully')
      setSubmitted(true)
    } catch (error) {
      console.error('Failed to submit answer', error)
      // Continue anyway as the error might be "already submitted"
      setSubmitted(true)
    } finally {
      setLoading(false)
    }
  }

  if (!sessionToken) {
    return (
      <div style={{ padding: 24, maxWidth: 600, margin: '0 auto' }}>
        <Result
          status="error"
          title="No Session Found"
          subTitle="Please join a session first"
          extra={
            <Button type="primary" onClick={() => navigate('/join')}>
              Go to Join Page
            </Button>
          }
        />
      </div>
    )
  }

  if (!currentQuestion) {
    return (
      <div style={{ padding: 24, maxWidth: 600, margin: '0 auto' }}>
        <Card>
          <Space direction="vertical" align="center" style={{ width: '100%' }}>
            <LoadingOutlined style={{ fontSize: 48 }} />
            <Title level={3}>Waiting for host...</Title>
            <Text type="secondary">The quiz will start soon</Text>
            <Tag color="blue">Joined as: {displayName}</Tag>
          </Space>
        </Card>
      </div>
    )
  }

  const isCorrect = submitted && selectedAnswer === currentQuestion.correct_answer

  return (
    <div style={{ padding: 24, maxWidth: 800, margin: '0 auto' }}>
      <Card style={{ marginBottom: 16 }}>
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Tag color="blue">
            Question {results.current_question_index + 1}
          </Tag>
          <Text strong>{displayName}</Text>
        </Space>
      </Card>

      <Card
        title={
          <Title level={3} style={{ margin: 0 }}>
            {currentQuestion.text}
          </Title>
        }
      >
        {!submitted ? (
          <>
            <Radio.Group
              onChange={(e) => {
                console.log('Radio changed:', e.target.value)
                setSelectedAnswer(e.target.value)
              }}
              value={selectedAnswer}
              style={{ width: '100%' }}
            >
              <Space direction="vertical" style={{ width: '100%' }} size="large">
                <Radio
                  value="A"
                  style={{
                    width: '100%',
                    padding: '16px',
                    border: '2px solid #d9d9d9',
                    borderRadius: '8px',
                    backgroundColor: selectedAnswer === 'A' ? '#e6f7ff' : 'white'
                  }}
                >
                  <Text strong>A:</Text> {currentQuestion.option_a}
                </Radio>

                <Radio
                  value="B"
                  style={{
                    width: '100%',
                    padding: '16px',
                    border: '2px solid #d9d9d9',
                    borderRadius: '8px',
                    backgroundColor: selectedAnswer === 'B' ? '#e6f7ff' : 'white'
                  }}
                >
                  <Text strong>B:</Text> {currentQuestion.option_b}
                </Radio>

                <Radio
                  value="C"
                  style={{
                    width: '100%',
                    padding: '16px',
                    border: '2px solid #d9d9d9',
                    borderRadius: '8px',
                    backgroundColor: selectedAnswer === 'C' ? '#e6f7ff' : 'white'
                  }}
                >
                  <Text strong>C:</Text> {currentQuestion.option_c}
                </Radio>

                <Radio
                  value="D"
                  style={{
                    width: '100%',
                    padding: '16px',
                    border: '2px solid #d9d9d9',
                    borderRadius: '8px',
                    backgroundColor: selectedAnswer === 'D' ? '#e6f7ff' : 'white'
                  }}
                >
                  <Text strong>D:</Text> {currentQuestion.option_d}
                </Radio>
              </Space>
            </Radio.Group>

            <Button
              type="primary"
              size="large"
              block
              disabled={!selectedAnswer}
              onClick={handleSubmitAnswer}
              loading={loading}
              style={{ marginTop: 24 }}
            >
              Submit Answer
            </Button>
          </>
        ) : (
          <>
            <Alert
              message={isCorrect ? "Correct!" : "Incorrect"}
              description={
                <>
                  <Text>Your answer: <Text strong>{selectedAnswer}</Text></Text>
                  <br />
                  <Text>Correct answer: <Text strong>{currentQuestion.correct_answer}</Text></Text>
                  <br />
                  <Text>{currentQuestion[`option_${currentQuestion.correct_answer.toLowerCase()}`]}</Text>
                </>
              }
              type={isCorrect ? "success" : "error"}
              icon={isCorrect ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
              showIcon
              style={{ marginBottom: 24 }}
            />

            <Space direction="vertical" style={{ width: '100%' }} size="large">
              <div>
                <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 8 }}>
                  <Text>A: {currentQuestion.option_a}</Text>
                  <Text>{results.answer_distribution?.A || 0} ({results.answer_distribution_percentage?.A?.toFixed(1) || 0}%)</Text>
                </Space>
                <Progress
                  percent={results.answer_distribution_percentage?.A || 0}
                  strokeColor={currentQuestion.correct_answer === 'A' ? '#52c41a' : '#1890ff'}
                />
              </div>

              <div>
                <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 8 }}>
                  <Text>B: {currentQuestion.option_b}</Text>
                  <Text>{results.answer_distribution?.B || 0} ({results.answer_distribution_percentage?.B?.toFixed(1) || 0}%)</Text>
                </Space>
                <Progress
                  percent={results.answer_distribution_percentage?.B || 0}
                  strokeColor={currentQuestion.correct_answer === 'B' ? '#52c41a' : '#1890ff'}
                />
              </div>

              <div>
                <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 8 }}>
                  <Text>C: {currentQuestion.option_c}</Text>
                  <Text>{results.answer_distribution?.C || 0} ({results.answer_distribution_percentage?.C?.toFixed(1) || 0}%)</Text>
                </Space>
                <Progress
                  percent={results.answer_distribution_percentage?.C || 0}
                  strokeColor={currentQuestion.correct_answer === 'C' ? '#52c41a' : '#1890ff'}
                />
              </div>

              <div>
                <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 8 }}>
                  <Text>D: {currentQuestion.option_d}</Text>
                  <Text>{results.answer_distribution?.D || 0} ({results.answer_distribution_percentage?.D?.toFixed(1) || 0}%)</Text>
                </Space>
                <Progress
                  percent={results.answer_distribution_percentage?.D || 0}
                  strokeColor={currentQuestion.correct_answer === 'D' ? '#52c41a' : '#1890ff'}
                />
              </div>
            </Space>

            <Alert
              message="Waiting for next question..."
              type="info"
              showIcon
              style={{ marginTop: 24 }}
            />
          </>
        )}
      </Card>
    </div>
  )
}
