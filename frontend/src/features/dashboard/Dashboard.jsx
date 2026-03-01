import { useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useSelector, useDispatch } from 'react-redux'
import { ProCard } from '@ant-design/pro-components'
import { Button, Tag, Space, Popconfirm, message, Row, Col, Card, Statistic } from 'antd'
import {
  PlusOutlined,
  PlayCircleOutlined,
  EditOutlined,
  DeleteOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  EditFilled,
  RocketOutlined,
  HistoryOutlined
} from '@ant-design/icons'
import { setQuizzes } from '../../store/quizSlice'
import { logout } from '../../store/authSlice'
import { quizAPI } from '../../services/api'
import './Dashboard.css'

function Dashboard() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const { quizzes } = useSelector((state) => state.quiz)

  useEffect(() => {
    loadQuizzes()
  }, [])

  useEffect(() => {
    document.body.classList.add('dashboard-scroll-active')
    return () => {
      document.body.classList.remove('dashboard-scroll-active')
    }
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

  const getStatusTranslation = (status) => {
    const statusMap = {
      draft: 'statusDraft',
      ready: 'statusReady',
      archived: 'statusArchived'
    }
    return t(`quiz.${statusMap[status] || 'statusDraft'}`)
  }

  // Calculate quiz statistics
  const statistics = useMemo(() => {
    const stats = {
      total: quizzes.length,
      byStatus: {
        draft: 0,
        ready: 0,
        archived: 0
      },
      totalQuestions: 0
    }

    quizzes.forEach(quiz => {
      // Count by status
      if (quiz.status in stats.byStatus) {
        stats.byStatus[quiz.status]++
      }
      // Count total questions
      if (quiz.question_count) {
        stats.totalQuestions += quiz.question_count
      }
    })

    return stats
  }, [quizzes])

  return (
    <div className="dashboard-scroll">
      <div className="dashboard-page" style={{ padding: 24, overflowX: 'hidden' }}>
      {/* Statistics Cards */}
      <Row gutter={[8, 8]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Total Quizzes"
              value={statistics.total}
              prefix={<FileTextOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Ready to Launch"
              value={statistics.byStatus.ready}
              prefix={<RocketOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Drafts"
              value={statistics.byStatus.draft}
              prefix={<EditFilled />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Total Questions"
              value={statistics.totalQuestions}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Quiz List */}
      <ProCard
        title={t('quiz.myQuizzes')}
        style={{ overflowX: 'hidden' }}
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
      <div style={{ width: '100%', overflow: 'hidden' }}>
        {quizzes.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '24px', color: '#999' }}>
            {t('quiz.noQuizzes') || 'No quizzes yet. Create your first quiz!'}
          </div>
        ) : quizzes.map((quiz, index) => (
          <div
            key={quiz.id}
            className="quiz-item"
          >
            <div className="quiz-item-meta">
              <div style={{ marginBottom: 4 }}>
                <strong>{quiz.title}</strong>
              </div>
              <Space>
                <Tag color={getStatusColor(quiz.status)}>{getStatusTranslation(quiz.status)}</Tag>
                <span>{quiz.question_count || 0} {t('quiz.questions')}</span>
              </Space>
            </div>
            <div className="quiz-item-actions">
              <Button
                icon={<EditOutlined />}
                onClick={() => navigate(`/quiz/${quiz.id}/edit`)}
              >
                {t('common.edit')}
              </Button>
              <Button
                icon={<HistoryOutlined />}
                onClick={() => navigate(`/quiz/${quiz.id}/history`)}
              >
                {t('quiz.history')}
              </Button>
              {quiz.status === 'ready' && (
                <Button
                  type="primary"
                  icon={<PlayCircleOutlined />}
                  onClick={() => navigate(`/quiz/${quiz.id}/control`)}
                >
                  {t('quiz.startQuiz')}
                </Button>
              )}
              <Popconfirm
                title={t('quiz.deleteConfirm')}
                description={t('quiz.deleteWarning')}
                onConfirm={() => handleDeleteQuiz(quiz.id)}
                okText={t('common.submit')}
                cancelText={t('common.cancel')}
              >
                <Button danger icon={<DeleteOutlined />}>
                  {t('common.delete')}
                </Button>
              </Popconfirm>
            </div>
          </div>
        ))}
      </div>
    </ProCard>
      </div>
    </div>
  )
}

export default Dashboard
