import { useState, useEffect, useCallback, memo } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ProCard } from '@ant-design/pro-components'
import { 
  Card, 
  Form, 
  Input, 
  Button, 
  Space, 
  List, 
  Radio, 
  Popconfirm, 
  message,
  Typography,
  Divider,
  Tag
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
  CloseOutlined
} from '@ant-design/icons'
import { quizAPI, questionAPI } from '../../services/api'
import ImageUpload from './components/ImageUpload'
import './QuizBuilder.css'

const { Title, Text } = Typography
const { TextArea } = Input

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
  t
}) => {
  const [questionForm] = Form.useForm()
  const [questionType, setQuestionType] = useState('mcq')
  
  // Debug: Log when component renders
  console.log('[QuestionForm] Rendering. Question ID:', question?.id || 'NEW')

  useEffect(() => {
    console.log('[QuestionForm] useEffect triggered')
    if (question) {
      questionForm.setFieldsValue(question)
      setQuestionType(question.question_type || 'mcq')
      
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
  }, [question])  // Removed setQuestionImageUrl, setOptionImages - they're stable

  const handleTypeChange = (e) => {
    setQuestionType(e.target.value)
    // Clear option fields when switching to word cloud
    if (e.target.value === 'word_cloud') {
      questionForm.setFieldsValue({
        option_a: undefined,
        option_b: undefined,
        option_c: undefined,
        option_d: undefined,
        correct_answer: undefined
      })
    }
  }

  return (
    <Card style={{ marginBottom: 16, width: '100%' }}>
      <Form
        form={questionForm}
        layout="vertical"
        onFinish={onSave}
        initialValues={{
          question_type: 'mcq',
          correct_answer: 'A'
        }}
      >
        <Form.Item
          name="question_type"
          label={t('quiz.questionType')}
          rules={[{ required: true }]}
        >
          <Radio.Group onChange={handleTypeChange}>
            <Radio value="mcq">{t('quiz.multipleChoice')}</Radio>
            <Radio value="word_cloud">{t('quiz.wordCloud')}</Radio>
          </Radio.Group>
        </Form.Item>

        <Form.Item
          name="text"
          label={t('quiz.question')}
          rules={[{ required: true, message: t('quiz.questionRequired') }]}
        >
          <TextArea rows={2} placeholder={t('quiz.enterQuestion')} />
        </Form.Item>

        {/* Question Image Upload */}
        <div style={{ marginBottom: 16 }}>
          <Text type="secondary" style={{ display: 'block', marginBottom: 4 }}>
            Question Image (optional)
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
              label={t('quiz.optionA')}
              rules={[{ required: true, message: t('quiz.optionARequired') }]}
            >
              <Input placeholder={t('quiz.optionAPlaceholder')} />
            </Form.Item>
            
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
              label={t('quiz.optionB')}
              rules={[{ required: true, message: t('quiz.optionBRequired') }]}
            >
              <Input placeholder={t('quiz.optionBPlaceholder')} />
            </Form.Item>
            
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

            <Form.Item
              name="option_c"
              label={t('quiz.optionC')}
              rules={[{ required: true, message: t('quiz.optionCRequired') }]}
            >
              <Input placeholder={t('quiz.optionCPlaceholder')} />
            </Form.Item>
            
            {/* Option C Image Upload */}
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

            <Form.Item
              name="option_d"
              label={t('quiz.optionD')}
              rules={[{ required: true, message: t('quiz.optionDRequired') }]}
            >
              <Input placeholder={t('quiz.optionDPlaceholder')} />
            </Form.Item>
            
            {/* Option D Image Upload */}
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

            <Form.Item
              name="correct_answer"
              label={t('quiz.correctAnswer')}
              rules={[{ required: true, message: t('quiz.correctAnswerRequired') }]}
            >
              <Radio.Group>
                <Radio value="A">A</Radio>
                <Radio value="B">B</Radio>
                <Radio value="C">C</Radio>
                <Radio value="D">D</Radio>
              </Radio.Group>
            </Form.Item>
          </>
        )}

        {questionType === 'word_cloud' && (
          <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
            {t('quiz.wordCloudDescription')}
          </Text>
        )}

        <Space>
          <Button
            type="primary"
            htmlType="submit"
            loading={loading || movingImages}
            icon={question ? <SaveOutlined /> : <PlusOutlined />}
          >
            {movingImages ? 'Moving images...' : (question ? t('quiz.updateQuestion') : t('quiz.addQuestion'))}
          </Button>
          <Button icon={<CloseOutlined />} onClick={onCancel}>{t('common.cancel')}</Button>
        </Space>
      </Form>
    </Card>
  )
}

// Custom comparison function for React.memo
const arePropsEqual = (prevProps, nextProps) => {
  const changed = []
  
  // Check each prop
  if (prevProps.question?.id !== nextProps.question?.id) changed.push('question.id')
  if (prevProps.quizId !== nextProps.quizId) changed.push('quizId')
  if (prevProps.questionImageUrl !== nextProps.questionImageUrl) changed.push('questionImageUrl')
  if (prevProps.loading !== nextProps.loading) changed.push('loading')
  if (prevProps.movingImages !== nextProps.movingImages) changed.push('movingImages')
  if (prevProps.onSave !== nextProps.onSave) changed.push('onSave')
  if (prevProps.onCancel !== nextProps.onCancel) changed.push('onCancel')
  
  // Check optionImages
  if (JSON.stringify(prevProps.optionImages) !== JSON.stringify(nextProps.optionImages)) {
    changed.push('optionImages')
  }
  
  // Check tempImages
  if (JSON.stringify(prevProps.tempImages) !== JSON.stringify(nextProps.tempImages)) {
    changed.push('tempImages')
  }
  
  if (changed.length > 0) {
    console.log('[QuestionForm] Props changed:', changed.join(', '))
    return false // Re-render
  }
  
  console.log('[QuestionForm] Props unchanged, skipping render')
  return true // Skip render
}

// Memoize QuestionForm to prevent unnecessary re-renders
const MemoizedQuestionForm = memo(QuestionForm, arePropsEqual)

export default function QuizBuilder() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [quiz, setQuiz] = useState(null)
  const [questions, setQuestions] = useState([])
  const [editingQuestion, setEditingQuestion] = useState(null)
  
  // Image state for question being edited/created
  const [questionImageUrl, setQuestionImageUrl] = useState(null)
  const [optionImages, setOptionImages] = useState({
    A: null,
    B: null,
    C: null,
    D: null
  })
  
  // Temp image state (for new questions without ID)
  const [tempImages, setTempImages] = useState({
    question: null,  // {url, tempKey}
    optionA: null,
    optionB: null,
    optionC: null,
    optionD: null
  })
  
  // Loading state for moving temp images
  const [movingImages, setMovingImages] = useState(false)

  useEffect(() => {
    if (id) {
      loadQuiz()
    }
  }, [id])

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
          question_type: q.question_type || 'mcq'
        }
        
        // Only transform options for MCQ questions
        if (q.question_type === 'mcq' && q.options) {
          return {
            ...baseQuestion,
            option_a: q.options[0],
            option_b: q.options[1],
            option_c: q.options[2],
            option_d: q.options[3],
            correct_answer: ['A', 'B', 'C', 'D'][q.correct_answer_index]
          }
        }
        
        return baseQuestion
      })
      console.log('Transformed questions:', transformedQuestions)
      console.log('Total questions after transform:', transformedQuestions.length)
      setQuestions(transformedQuestions)
      
      form.setFieldsValue({
        title: response.data.title,
        description: response.data.description
      })
    } catch (error) {
      const errorMsg = error.response?.data?.detail || t('quiz.loadError')
      message.error(errorMsg)
      console.error('Load quiz error:', error.response?.data || error)
    }
  }, [id])

  const handleSaveQuiz = async (values) => {
    setLoading(true)
    try {
      if (id) {
        await quizAPI.update(id, values)
        message.success(t('quiz.saveSuccess'))
        loadQuiz()
      } else {
        const response = await quizAPI.create(values)
        message.success(t('quiz.createSuccess'))
        navigate(`/quiz/${response.data.id}/edit`)
      }
    } catch (error) {
      const errorMsg = error.response?.data?.detail || t('quiz.saveError')
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
        text: values.text
      }
      
      // Only add options and correct_answer for MCQ
      if (values.question_type === 'mcq') {
        questionData.options = [values.option_a, values.option_b, values.option_c, values.option_d]
        questionData.correct_answer_index = ['A', 'B', 'C', 'D'].indexOf(values.correct_answer)
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
          message.error('Question saved but failed to move images. Please re-upload.')
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
      const errorMsg = error.response?.data?.detail || t('quiz.addQuestionError')
      message.error(errorMsg)
      console.error('Add question error:', error.response?.data || error)
    } finally {
      setLoading(false)
    }
  }, [id, t, tempImages, loadQuiz])
  
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
        text: values.text
      }
      
      // Only add options and correct_answer for MCQ
      if (values.question_type === 'mcq') {
        questionData.options = [values.option_a, values.option_b, values.option_c, values.option_d]
        questionData.correct_answer_index = ['A', 'B', 'C', 'D'].indexOf(values.correct_answer)
      }
      
      await questionAPI.update(questionId, questionData)
      message.success(t('quiz.updateQuestionSuccess'))
      loadQuiz()
      setEditingQuestion(null)
    } catch (error) {
      const errorMsg = error.response?.data?.detail || t('quiz.updateQuestionError')
      message.error(errorMsg)
      console.error('Update question error:', error.response?.data || error)
    } finally {
      setLoading(false)
    }
  }, [t, loadQuiz])

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
      await quizAPI.publish(id)
      message.success(t('quiz.publishSuccess'))
      loadQuiz()
    } catch (error) {
      message.error(error.response?.data?.detail || t('quiz.publishError'))
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleUnpublish = async () => {
    setLoading(true)
    try {
      await quizAPI.unpublish(id)
      message.success(t('quiz.unpublishSuccess'))
      loadQuiz()
    } catch (error) {
      message.error(error.response?.data?.detail || t('quiz.unpublishError'))
      console.error(error)
    } finally {
      setLoading(false)
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
          <Button 
            type="primary" 
            icon={<RocketOutlined />}
            onClick={handlePublish}
            loading={loading}
          >
            {t('quiz.publishQuiz')}
          </Button>
        )}
        {quiz && quiz.status === 'ready' && (
          <Button 
            type="default" 
            onClick={handleUnpublish}
            loading={loading}
          >
            {t('quiz.unpublishQuiz')}
          </Button>
        )}
      </Space>

      <Card title={id ? t('quiz.editQuiz') : t('quiz.createNewQuiz')} style={{ marginBottom: 24, width: '100%' }}>
        {quiz && (
          <Space style={{ marginBottom: 16 }}>
            <Tag color={quiz.status === 'draft' ? 'orange' : 'green'}>
              {getQuizStatusTranslation(quiz.status)}
            </Tag>
            {quiz.status === 'ready' && (
              <Tag color="red">
                {t('quiz.unpublishMessage') || 'Click "Unpublish Quiz" above to edit'}
              </Tag>
            )}
            <Text type="secondary">
              {questions.length} {questions.length === 1 ? t('quiz.question') : t('quiz.questions')}
            </Text>
          </Space>
        )}

        <Form
          form={form}
          layout="vertical"
          onFinish={handleSaveQuiz}
        >
          <Form.Item
            name="title"
            label={t('quiz.quizTitle')}
            rules={[{ required: true, message: t('quiz.quizTitleRequired') }]}
          >
            <Input placeholder={t('quiz.enterQuizTitle')} size="large" />
          </Form.Item>

          <Form.Item
            name="description"
            label={t('quiz.quizDescription')}
          >
            <TextArea rows={3} placeholder={t('quiz.enterQuizDescription')} />
          </Form.Item>

          <Button 
            type="primary" 
            htmlType="submit" 
            icon={<SaveOutlined />}
            loading={loading}
          >
            {id ? t('quiz.editQuiz') : t('quiz.createQuiz')}
          </Button>
        </Form>
      </Card>

      {id && (
        <>
          <Divider>{t('quiz.questions')}</Divider>

          {editingQuestion === 'new' ? (
            <MemoizedQuestionForm
              key="new-question"
              onSave={handleAddQuestion}
              onCancel={handleCancelQuestion}
              quizId={id}
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
              style={{ marginBottom: 16, width: '100%' }}
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
                      <Tag color={question.question_type === 'word_cloud' ? 'purple' : 'cyan'}>
                        {question.question_type === 'word_cloud' ? t('quiz.wordCloud') : 'MCQ'}
                      </Tag>
                      <Text strong>{question.text}</Text>
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
                  ) : (
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <div>
                        <Text>A: {question.option_a}</Text>
                        {question.correct_answer === 'A' && <Tag color="green" style={{ marginLeft: 8 }}>{t('quiz.correct')}</Tag>}
                      </div>
                      <div>
                        <Text>B: {question.option_b}</Text>
                        {question.correct_answer === 'B' && <Tag color="green" style={{ marginLeft: 8 }}>{t('quiz.correct')}</Tag>}
                      </div>
                      <div>
                        <Text>C: {question.option_c}</Text>
                        {question.correct_answer === 'C' && <Tag color="green" style={{ marginLeft: 8 }}>{t('quiz.correct')}</Tag>}
                      </div>
                      <div>
                        <Text>D: {question.option_d}</Text>
                        {question.correct_answer === 'D' && <Tag color="green" style={{ marginLeft: 8 }}>{t('quiz.correct')}</Tag>}
                      </div>
                    </Space>
                  )}
                </Card>
              )
            )}
          />
        </>
      )}
    </div>
  )
}
