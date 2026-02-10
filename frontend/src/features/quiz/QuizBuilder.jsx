import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { 
  Layout,
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
  LeftOutlined
} from '@ant-design/icons'
import { quizAPI, questionAPI } from '../../services/api'

const { Title, Text } = Typography
const { Content } = Layout
const { TextArea } = Input

export default function QuizBuilder() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [quiz, setQuiz] = useState(null)
  const [questions, setQuestions] = useState([])
  const [editingQuestion, setEditingQuestion] = useState(null)

  useEffect(() => {
    if (id) {
      loadQuiz()
    }
  }, [id])

  const loadQuiz = async () => {
    try {
      const response = await quizAPI.get(id)
      setQuiz(response.data)
      
      // Transform backend format to frontend format
      const transformedQuestions = (response.data.questions || []).map(q => ({
        ...q,
        option_a: q.options[0],
        option_b: q.options[1],
        option_c: q.options[2],
        option_d: q.options[3],
        correct_answer: ['A', 'B', 'C', 'D'][q.correct_answer_index]
      }))
      setQuestions(transformedQuestions)
      
      form.setFieldsValue({
        title: response.data.title,
        description: response.data.description
      })
    } catch (error) {
      message.error('Failed to load quiz')
      console.error(error)
    }
  }

  const handleSaveQuiz = async (values) => {
    setLoading(true)
    try {
      if (id) {
        await quizAPI.update(id, values)
        message.success('Quiz updated successfully')
        loadQuiz()
      } else {
        const response = await quizAPI.create({ ...values, event_id: 1 })
        message.success('Quiz created successfully')
        navigate(`/quiz/${response.data.id}/edit`)
      }
    } catch (error) {
      message.error('Failed to save quiz')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleAddQuestion = async (values) => {
    if (!id) {
      message.warning('Please save the quiz first')
      return
    }
    
    setLoading(true)
    try {
      // Transform frontend format to backend format
      const questionData = {
        text: values.text,
        options: [values.option_a, values.option_b, values.option_c, values.option_d],
        correct_answer_index: ['A', 'B', 'C', 'D'].indexOf(values.correct_answer)
      }
      await questionAPI.add(id, questionData)
      message.success('Question added successfully')
      loadQuiz()
      setEditingQuestion(null)
    } catch (error) {
      message.error('Failed to add question')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleUpdateQuestion = async (questionId, values) => {
    setLoading(true)
    try {
      // Transform frontend format to backend format
      const questionData = {
        text: values.text,
        options: [values.option_a, values.option_b, values.option_c, values.option_d],
        correct_answer_index: ['A', 'B', 'C', 'D'].indexOf(values.correct_answer)
      }
      await questionAPI.update(questionId, questionData)
      message.success('Question updated successfully')
      loadQuiz()
      setEditingQuestion(null)
    } catch (error) {
      message.error('Failed to update question')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteQuestion = async (questionId) => {
    setLoading(true)
    try {
      await questionAPI.delete(questionId)
      message.success('Question deleted successfully')
      loadQuiz()
    } catch (error) {
      message.error('Failed to delete question')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handlePublish = async () => {
    setLoading(true)
    try {
      await quizAPI.publish(id)
      message.success('Quiz published successfully!')
      loadQuiz()
    } catch (error) {
      message.error(error.response?.data?.detail || 'Failed to publish quiz')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const QuestionForm = ({ question, onSave, onCancel }) => {
    const [questionForm] = Form.useForm()

    useEffect(() => {
      if (question) {
        questionForm.setFieldsValue(question)
      }
    }, [question])

    return (
      <Card style={{ marginBottom: 16, width: '100%' }}>
        <Form
          form={questionForm}
          layout="vertical"
          onFinish={onSave}
          initialValues={{
            type: 'multiple_choice',
            correct_answer: 'A'
          }}
        >
          <Form.Item
            name="text"
            label="Question"
            rules={[{ required: true, message: 'Please enter question text' }]}
          >
            <TextArea rows={2} placeholder="Enter your question" />
          </Form.Item>

          <Form.Item
            name="type"
            label="Question Type"
            rules={[{ required: true }]}
          >
            <Radio.Group>
              <Radio value="multiple_choice">Multiple Choice</Radio>
            </Radio.Group>
          </Form.Item>

          <Form.Item
            name="option_a"
            label="Option A"
            rules={[{ required: true, message: 'Please enter option A' }]}
          >
            <Input placeholder="Option A" />
          </Form.Item>

          <Form.Item
            name="option_b"
            label="Option B"
            rules={[{ required: true, message: 'Please enter option B' }]}
          >
            <Input placeholder="Option B" />
          </Form.Item>

          <Form.Item
            name="option_c"
            label="Option C"
            rules={[{ required: true, message: 'Please enter option C' }]}
          >
            <Input placeholder="Option C" />
          </Form.Item>

          <Form.Item
            name="option_d"
            label="Option D"
            rules={[{ required: true, message: 'Please enter option D' }]}
          >
            <Input placeholder="Option D" />
          </Form.Item>

          <Form.Item
            name="correct_answer"
            label="Correct Answer"
            rules={[{ required: true }]}
          >
            <Radio.Group>
              <Radio value="A">A</Radio>
              <Radio value="B">B</Radio>
              <Radio value="C">C</Radio>
              <Radio value="D">D</Radio>
            </Radio.Group>
          </Form.Item>

          <Space>
            <Button type="primary" htmlType="submit" loading={loading}>
              {question ? 'Update' : 'Add'} Question
            </Button>
            <Button onClick={onCancel}>Cancel</Button>
          </Space>
        </Form>
      </Card>
    )
  }

  return (
    <Layout style={{ width: '100%' }}>
      <Content style={{ padding: '24px', minHeight: 280, width: '100%' }}>
        <div style={{ width: '100%', maxWidth: 1200, margin: '0 auto' }}>
      <Space style={{ marginBottom: 24, width: '100%', justifyContent: 'space-between' }}>
        <Button 
          icon={<LeftOutlined />} 
          onClick={() => navigate('/dashboard')}
        >
          Back to Dashboard
        </Button>
        {quiz && quiz.status === 'draft' && questions.length >= 1 && (
          <Button 
            type="primary" 
            icon={<RocketOutlined />}
            onClick={handlePublish}
            loading={loading}
          >
            Publish Quiz
          </Button>
        )}
      </Space>

      <Card title={id ? "Edit Quiz" : "Create New Quiz"} style={{ marginBottom: 24, width: '100%' }}>
        {quiz && (
          <Space style={{ marginBottom: 16 }}>
            <Tag color={quiz.status === 'draft' ? 'orange' : 'green'}>
              {quiz.status.toUpperCase()}
            </Tag>
            <Text type="secondary">
              {questions.length} {questions.length === 1 ? 'question' : 'questions'}
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
            label="Quiz Title"
            rules={[{ required: true, message: 'Please enter quiz title' }]}
          >
            <Input placeholder="Enter quiz title" size="large" />
          </Form.Item>

          <Form.Item
            name="description"
            label="Description"
          >
            <TextArea rows={3} placeholder="Enter quiz description (optional)" />
          </Form.Item>

          <Button 
            type="primary" 
            htmlType="submit" 
            icon={<SaveOutlined />}
            loading={loading}
          >
            {id ? 'Update' : 'Create'} Quiz
          </Button>
        </Form>
      </Card>

      {id && (
        <>
          <Divider>Questions</Divider>

          {editingQuestion === 'new' ? (
            <QuestionForm
              onSave={handleAddQuestion}
              onCancel={() => setEditingQuestion(null)}
            />
          ) : (
            <Button
              type="dashed"
              icon={<PlusOutlined />}
              onClick={() => setEditingQuestion('new')}
              style={{ marginBottom: 16, width: '100%' }}
              size="large"
            >
              Add Question
            </Button>
          )}

          <List
            dataSource={questions}
            renderItem={(question, index) => (
              editingQuestion === question.id ? (
                <QuestionForm
                  question={question}
                  onSave={(values) => handleUpdateQuestion(question.id, values)}
                  onCancel={() => setEditingQuestion(null)}
                />
              ) : (
                <Card
                  key={question.id}
                  style={{ marginBottom: 16, width: '100%' }}
                  title={
                    <Space>
                      <Tag color="blue">Q{index + 1}</Tag>
                      <Text strong>{question.text}</Text>
                    </Space>
                  }
                  extra={
                    <Space>
                      <Button
                        size="small"
                        onClick={() => setEditingQuestion(question.id)}
                      >
                        Edit
                      </Button>
                      <Popconfirm
                        title="Delete this question?"
                        onConfirm={() => handleDeleteQuestion(question.id)}
                        okText="Yes"
                        cancelText="No"
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
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <div>
                      <Text>A: {question.option_a}</Text>
                      {question.correct_answer === 'A' && <Tag color="green" style={{ marginLeft: 8 }}>Correct</Tag>}
                    </div>
                    <div>
                      <Text>B: {question.option_b}</Text>
                      {question.correct_answer === 'B' && <Tag color="green" style={{ marginLeft: 8 }}>Correct</Tag>}
                    </div>
                    <div>
                      <Text>C: {question.option_c}</Text>
                      {question.correct_answer === 'C' && <Tag color="green" style={{ marginLeft: 8 }}>Correct</Tag>}
                    </div>
                    <div>
                      <Text>D: {question.option_d}</Text>
                      {question.correct_answer === 'D' && <Tag color="green" style={{ marginLeft: 8 }}>Correct</Tag>}
                    </div>
                  </Space>
                </Card>
              )
            )}
          />
        </>
      )}
        </div>
      </Content>
    </Layout>
  )
}
