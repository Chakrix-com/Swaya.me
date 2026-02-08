import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSelector, useDispatch } from 'react-redux'
import { Layout, Card, Button, List, Tag, Space, Typography } from 'antd'
import { PlusOutlined, PlayCircleOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { setQuizzes } from '../../store/quizSlice'
import { logout } from '../../store/authSlice'
import { quizAPI } from '../../services/api'

const { Header, Content } = Layout
const { Title } = Typography

function Dashboard() {
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const { user } = useSelector((state) => state.auth)
  const { quizzes } = useSelector((state) => state.quiz)

  useEffect(() => {
    loadQuizzes()
  }, [])

  const loadQuizzes = async () => {
    try {
      const response = await quizAPI.list()
      dispatch(setQuizzes(response.data))
    } catch (error) {
      console.error('Failed to load quizzes:', error)
    }
  }

  const handleLogout = () => {
    dispatch(logout())
    navigate('/login')
  }

  const getStatusColor = (status) => {
    const colors = {
      draft: 'default',
      ready: 'success',
      archived: 'error',
    }
    return colors[status] || 'default'
  }

  return (
    <Layout>
      <Header style={{ background: '#fff', padding: '0 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={3} style={{ margin: 0 }}>Swaya.me Dashboard</Title>
        <Space>
          <span>Welcome, {user?.full_name || user?.email}</span>
          <Button onClick={handleLogout}>Logout</Button>
        </Space>
      </Header>
      <Content style={{ padding: '24px', minHeight: 280 }}>
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
          <Card
            title="My Quizzes"
            extra={
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => navigate('/quiz/builder')}
              >
                Create Quiz
              </Button>
            }
          >
            <List
              dataSource={quizzes}
              renderItem={(quiz) => (
                <List.Item
                  actions={[
                    quiz.status === 'draft' && (
                      <Button
                        icon={<EditOutlined />}
                        onClick={() => navigate(`/quiz/builder/${quiz.id}`)}
                      >
                        Edit
                      </Button>
                    ),
                    quiz.status === 'ready' && (
                      <Button
                        type="primary"
                        icon={<PlayCircleOutlined />}
                        onClick={() => {/* Start session */}}
                      >
                        Start
                      </Button>
                    ),
                  ].filter(Boolean)}
                >
                  <List.Item.Meta
                    title={quiz.title}
                    description={
                      <Space>
                        <Tag color={getStatusColor(quiz.status)}>{quiz.status}</Tag>
                        <span>{quiz.question_count} questions</span>
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
        </div>
      </Content>
    </Layout>
  )
}

export default Dashboard
