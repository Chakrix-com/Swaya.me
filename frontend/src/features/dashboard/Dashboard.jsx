import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useSelector, useDispatch } from 'react-redux'
import { ProCard } from '@ant-design/pro-components'
import { Button, List, Tag, Space, Popconfirm, message } from 'antd'
import { PlusOutlined, PlayCircleOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { setQuizzes } from '../../store/quizSlice'
import { logout } from '../../store/authSlice'
import { quizAPI } from '../../services/api'

function Dashboard() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const dispatch = useDispatch()
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

  const handleDeleteQuiz = async (quizId) => {
    try {
      await quizAPI.delete(quizId)
      loadQuizzes()
    } catch (error) {
      console.error('Failed to delete quiz:', error)
    }
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
    <ProCard
      title={t('quiz.myQuizzes')}
      extra={
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => navigate('/quiz/new')}
        >
          {t('quiz.createQuiz')}
        </Button>
      }
    >
      <List
        dataSource={quizzes}
        renderItem={(quiz) => (
          <List.Item
            actions={[
              <Button
                icon={<EditOutlined />}
                onClick={() => navigate(`/quiz/${quiz.id}/edit`)}
              >
                {t('common.edit')}
              </Button>,
              quiz.status === 'ready' && (
                <Button
                  type="primary"
                  icon={<PlayCircleOutlined />}
                  onClick={() => navigate(`/quiz/${quiz.id}/control`)}
                >
                  {t('quiz.startQuiz')}
                </Button>
              ),
              <Popconfirm
                title={t('quiz.deleteConfirm')}
                description={t('quiz.deleteWarning')}
                onConfirm={() => handleDeleteQuiz(quiz.id)}
                okText={t('common.submit')}
                cancelText={t('common.cancel')}
              >
                <Button
                  danger
                  icon={<DeleteOutlined />}
                >
                  {t('common.delete')}
                </Button>
              </Popconfirm>
            ].filter(Boolean)}
          >
            <List.Item.Meta
              title={quiz.title}
              description={
                <Space>
                  <Tag color={getStatusColor(quiz.status)}>{quiz.status}</Tag>
                  <span>{quiz.question_count || 0} {t('quiz.questions')}</span>
                </Space>
              }
            />
          </List.Item>
        )}
      />
    </ProCard>
  )
}

export default Dashboard
