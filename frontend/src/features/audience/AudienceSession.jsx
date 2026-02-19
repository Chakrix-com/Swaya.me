import { useState, useEffect, useRef } from 'react'
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
  Progress,
  Input,
  message
} from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  LoginOutlined,
  SendOutlined
} from '@ant-design/icons'
import ReactWordcloud from 'react-wordcloud'
import { sessionAPI, questionAPI } from '../../services/api'

const { Title, Text } = Typography
const { TextArea } = Input

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
  const [wordCloudAnswer, setWordCloudAnswer] = useState('')
  const [wordCloudData, setWordCloudData] = useState([])
  const [submitted, setSubmitted] = useState(false)
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [sessionStatus, setSessionStatus] = useState(null) // 'created', 'active', 'ended'
  const [sessionInvalidated, setSessionInvalidated] = useState(false)
  const lastQuestionIdRef = useRef(null)
  const pollingIntervalRef = useRef(null)

  useEffect(() => {
    if (sessionToken && sessionId) {
      pollingIntervalRef.current = setInterval(loadResults, 2000) // Poll every 2 seconds
      loadResults()
      return () => {
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current)
        }
      }
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
      
      const newQuestionId = response.data.current_question?.question_id
      const newStatus = response.data.status
      
      // Track session status changes and show notifications
      if (sessionStatus && sessionStatus !== newStatus) {
        if (newStatus === 'ended') {
          message.success('Quiz has ended! Thank you for participating!')
          // Stop polling when quiz ends
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current)
            pollingIntervalRef.current = null
          }
        } else if (newStatus === 'active' && sessionStatus === 'created') {
          message.info('Quiz is starting!')
        }
      }
      setSessionStatus(newStatus)
      
      // If question ID changed, reset answer state
      if (lastQuestionIdRef.current && newQuestionId && newQuestionId !== lastQuestionIdRef.current) {
        console.log('Question changed from', lastQuestionIdRef.current, 'to', newQuestionId, '- resetting answer state')
        setSubmitted(false)
        setSelectedAnswer(null)
        setWordCloudAnswer('')
        setWordCloudData([])
      }
      
      // Always update tracking
      lastQuestionIdRef.current = newQuestionId
      setResults(response.data)
      setCurrentQuestion(response.data.current_question)
      
      // If current question is word cloud, load word cloud data
      if (response.data.current_question?.question_type === 'word_cloud') {
        loadWordCloudData(response.data.current_question.question_id)
      }
    } catch (error) {
      console.error('Failed to load results', error)
      
      // Check if session was invalidated (403)
      if (error.response?.status === 403) {
        setSessionInvalidated(true)
        // Stop polling
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current)
          pollingIntervalRef.current = null
        }
        message.warning('Session has been restarted. Please rejoin with the new code.')
      }
    }
  }

  const loadWordCloudData = async (questionId) => {
    if (!sessionId) return
    try {
      const response = await questionAPI.getWordCloudResults(questionId, sessionId)
      const words = Object.entries(response.data.word_frequencies).map(([word, count]) => ({
        text: word,
        value: count
      }))
      setWordCloudData(words)
    } catch (error) {
      console.error('Failed to load word cloud data:', error)
    }
  }

  const handleSubmitAnswer = async () => {
    console.log('handleSubmitAnswer called, selectedAnswer:', selectedAnswer, 'wordCloudAnswer:', wordCloudAnswer)
    
    const isWordCloud = currentQuestion?.question_type === 'word_cloud'
    
    if (isWordCloud) {
      if (!wordCloudAnswer || !wordCloudAnswer.trim()) {
        console.log('No word cloud answer entered, returning')
        return
      }
    } else {
      if (!selectedAnswer) {
        console.log('No answer selected, returning')
        return
      }
    }

    setLoading(true)
    try {
      if (isWordCloud) {
        console.log('Submitting word cloud answer:', { text_answer: wordCloudAnswer.trim(), question_id: currentQuestion.question_id })
        
        await sessionAPI.submitWordCloudAnswer(sessionToken, {
          question_id: currentQuestion.question_id,
          text_answer: wordCloudAnswer.trim()
        })
        console.log('Word cloud answer submitted successfully')
        
        // Clear input for next submission but don't set submitted=true
        setWordCloudAnswer('')
        
        // Reload word cloud immediately to show new word
        setTimeout(() => loadWordCloudData(currentQuestion.question_id), 500)
      } else {
        // Convert answer letter (A,B,C,D) to index (0,1,2,3)
        const answerIndex = selectedAnswer.charCodeAt(0) - 65 // A=0, B=1, C=2, D=3
        console.log('Submitting answer:', { selectedAnswer, answerIndex, question_id: currentQuestion.question_id })
        
        await sessionAPI.submitAnswer(sessionToken, {
          question_id: currentQuestion.question_id,
          selected_option_index: answerIndex
        })
        console.log('Answer submitted successfully')
        setSubmitted(true)
      }
    } catch (error) {
      console.error('Failed to submit answer', error)
      // For MCQ, continue anyway as the error might be "already submitted"
      if (!isWordCloud) {
        setSubmitted(true)
      }
    } finally {
      setLoading(false)
    }
  }

  if (!sessionToken) {
    return (
      <div style={{ padding: 16, maxWidth: 600, margin: '0 auto' }}>
        <Result
          status="error"
          title="No Session Found"
          subTitle="Please join a session first"
          extra={
            <Button type="primary" icon={<LoginOutlined />} onClick={() => navigate('/join')}>
              Go to Join Page
            </Button>
          }
        />
      </div>
    )
  }

  // Session Invalidated - Host restarted quiz
  if (sessionInvalidated) {
    return (
      <div style={{ padding: 16, maxWidth: 600, margin: '0 auto' }}>
        <Card>
          <Result
            status="warning"
            icon={<CloseCircleOutlined style={{ color: '#faad14' }} />}
            title="Session Restarted"
            subTitle="The host has started a new quiz session"
            extra={
              <Button
                type="primary"
                icon={<LoginOutlined />}
                onClick={() => navigate('/join')}
                size="large"
              >
                Rejoin Quiz
              </Button>
            }
          />
        </Card>
      </div>
    )
  }

  // Quiz Completed - Show final score
  if (sessionStatus === 'ended' && !currentQuestion) {
    return (
      <div style={{ padding: 16, maxWidth: 600, margin: '0 auto' }}>
        <Card>
          <Result
            status="success"
            icon={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
            title="Quiz Completed!"
            subTitle={
              <Space direction="vertical" align="center" style={{ marginTop: 16 }}>
                <Title level={4} style={{ margin: 0 }}>
                  Your Score: {results?.participant_correct || 0}/{results?.total_questions || 0}
                </Title>
                <Text type="secondary">
                  You got {results?.participant_correct || 0} correct answer{(results?.participant_correct || 0) !== 1 ? 's' : ''}!
                </Text>
                <Tag color="blue" style={{ marginTop: 8 }}>Joined as: {displayName}</Tag>
              </Space>
            }
            extra={
              <Text type="secondary">Thank you for participating!</Text>
            }
          />
        </Card>
      </div>
    )
  }

  // Waiting for host/question
  if (!currentQuestion && sessionStatus !== 'ended') {
    return (
      <div style={{ padding: 16, maxWidth: 600, margin: '0 auto' }}>
        <Card>
          <Space direction="vertical" align="center" style={{ width: '100%' }}>
            <LoadingOutlined style={{ fontSize: 48 }} />
            <Title level={3}>
              {sessionStatus === 'created' ? 'Waiting for quiz to start...' : 'Waiting for next question...'}
            </Title>
            <Text type="secondary">
              {sessionStatus === 'created' ? 'The quiz will start soon' : 'Host is preparing the next question'}
            </Text>
            <Tag color="blue">Joined as: {displayName}</Tag>
          </Space>
        </Card>
      </div>
    )
  }

  const isWordCloud = currentQuestion?.question_type === 'word_cloud'
  const isCorrect = submitted && !isWordCloud && selectedAnswer === currentQuestion.correct_answer

  return (
    <div style={{ 
      padding: 16,  // Reduced from 24 for better mobile fit
      maxWidth: 800, 
      margin: '0 auto' 
    }}>
      <Card style={{ marginBottom: 16 }}>
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Tag color="blue">
            Question {results.current_question_index + 1}
          </Tag>
          {isWordCloud && <Tag color="purple">Word Cloud</Tag>}
          <Text strong>{displayName}</Text>
        </Space>
      </Card>

      <Card
        title={
          <Title 
            level={3} 
            style={{ 
              margin: 0,
              wordBreak: 'break-word',
              overflowWrap: 'break-word',
              whiteSpace: 'normal'
            }}
          >
            {currentQuestion.text}
          </Title>
        }
      >
        {isWordCloud ? (
          // Word Cloud: Always show input + visualization
          <>
            <TextArea
              rows={3}
              placeholder="Enter your answer (max 100 characters)"
              maxLength={100}
              value={wordCloudAnswer}
              onChange={(e) => setWordCloudAnswer(e.target.value)}
              showCount
              style={{ marginBottom: 16 }}
            />
            <Button
              type="primary"
              size="large"
              block
              icon={<SendOutlined />}
              disabled={!wordCloudAnswer.trim()}
              onClick={handleSubmitAnswer}
              loading={loading}
              style={{ marginBottom: 24 }}
            >
              Submit Answer
            </Button>
            
            {/* Word Cloud Visualization */}
            {wordCloudData.length > 0 ? (
              <>
                <Alert
                  message="Live Word Cloud"
                  description={`${wordCloudData.reduce((sum, w) => sum + w.value, 0)} responses submitted`}
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
                <div style={{
                  width: '100%',
                  height: '350px',
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
                      fontSizes: [16, 60],
                      padding: 4,
                      enableTooltip: true,
                      deterministic: true,
                      fontFamily: 'Arial',
                      colors: ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#eb2f96']
                    }}
                  />
                </div>
              </>
            ) : (
              <Alert
                message="Be the first to respond!"
                description="Submit your answer and watch the word cloud grow."
                type="info"
                showIcon
              />
            )}
          </>
        ) : !submitted ? (
          // MCQ Question UI
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
                        backgroundColor: selectedAnswer === 'A' ? '#e6f7ff' : 'white',
                        wordBreak: 'break-word',
                        overflowWrap: 'break-word',
                        whiteSpace: 'normal'
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
                        backgroundColor: selectedAnswer === 'B' ? '#e6f7ff' : 'white',
                        wordBreak: 'break-word',
                        overflowWrap: 'break-word',
                        whiteSpace: 'normal'
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
                        backgroundColor: selectedAnswer === 'C' ? '#e6f7ff' : 'white',
                        wordBreak: 'break-word',
                        overflowWrap: 'break-word',
                        whiteSpace: 'normal'
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
                        backgroundColor: selectedAnswer === 'D' ? '#e6f7ff' : 'white',
                        wordBreak: 'break-word',
                        overflowWrap: 'break-word',
                        whiteSpace: 'normal'
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
                  icon={<SendOutlined />}
                  disabled={!selectedAnswer}
                  onClick={handleSubmitAnswer}
                  loading={loading}
                  style={{ marginTop: 24 }}
                >
                  Submit Answer
                </Button>
              </>
        ) : (
          // MCQ Results (after submission)
          <>
            <Alert
              message={isCorrect ? "Correct!" : "Incorrect"}
              description={
                <>
                      <Text style={{ wordBreak: 'break-word', overflowWrap: 'break-word' }}>
                        Your answer: <Text strong>{selectedAnswer}</Text>
                      </Text>
                      <br />
                      <Text style={{ wordBreak: 'break-word', overflowWrap: 'break-word' }}>
                        Correct answer: <Text strong>{currentQuestion.correct_answer}</Text>
                      </Text>
                      <br />
                      <Text style={{ wordBreak: 'break-word', overflowWrap: 'break-word' }}>
                        {currentQuestion[`option_${currentQuestion.correct_answer.toLowerCase()}`]}
                      </Text>
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
                      <Text style={{ wordBreak: 'break-word', overflowWrap: 'break-word', flex: 1 }}>
                        A: {currentQuestion.option_a}
                      </Text>
                      <Text style={{ whiteSpace: 'nowrap', marginLeft: 8 }}>
                        {results.answer_distribution?.A || 0} ({results.answer_distribution_percentage?.A?.toFixed(1) || 0}%)
                      </Text>
                    </Space>
                    <Progress
                      percent={results.answer_distribution_percentage?.A || 0}
                      strokeColor={currentQuestion.correct_answer === 'A' ? '#52c41a' : '#1890ff'}
                    />
                  </div>

                  <div>
                    <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 8 }}>
                      <Text style={{ wordBreak: 'break-word', overflowWrap: 'break-word', flex: 1 }}>
                        B: {currentQuestion.option_b}
                      </Text>
                      <Text style={{ whiteSpace: 'nowrap', marginLeft: 8 }}>
                        {results.answer_distribution?.B || 0} ({results.answer_distribution_percentage?.B?.toFixed(1) || 0}%)
                      </Text>
                    </Space>
                    <Progress
                      percent={results.answer_distribution_percentage?.B || 0}
                      strokeColor={currentQuestion.correct_answer === 'B' ? '#52c41a' : '#1890ff'}
                    />
                  </div>

                  <div>
                    <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 8 }}>
                      <Text style={{ wordBreak: 'break-word', overflowWrap: 'break-word', flex: 1 }}>
                        C: {currentQuestion.option_c}
                      </Text>
                      <Text style={{ whiteSpace: 'nowrap', marginLeft: 8 }}>
                        {results.answer_distribution?.C || 0} ({results.answer_distribution_percentage?.C?.toFixed(1) || 0}%)
                      </Text>
                    </Space>
                    <Progress
                      percent={results.answer_distribution_percentage?.C || 0}
                      strokeColor={currentQuestion.correct_answer === 'C' ? '#52c41a' : '#1890ff'}
                    />
                  </div>

                  <div>
                    <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 8 }}>
                      <Text style={{ wordBreak: 'break-word', overflowWrap: 'break-word', flex: 1 }}>
                        D: {currentQuestion.option_d}
                      </Text>
                      <Text style={{ whiteSpace: 'nowrap', marginLeft: 8 }}>
                        {results.answer_distribution?.D || 0} ({results.answer_distribution_percentage?.D?.toFixed(1) || 0}%)
                      </Text>
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
