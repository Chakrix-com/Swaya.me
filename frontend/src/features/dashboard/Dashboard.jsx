import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useSelector, useDispatch } from 'react-redux'
import { ProCard } from '@ant-design/pro-components'
import { Button, Tag, Space, Popconfirm, message, Row, Col, Card, Statistic, Modal, Table } from 'antd'
import {
  PlusOutlined,
  PlayCircleOutlined,
  CloseCircleOutlined,
  EditOutlined,
  DeleteOutlined,
  CopyOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  EditFilled,
  RocketOutlined,
  HistoryOutlined,
  StarOutlined,
  BarChartOutlined,
} from '@ant-design/icons'
import { setQuizzes } from '../../store/quizSlice'
import { logout } from '../../store/authSlice'
import { quizAPI, sessionAPI } from '../../services/api'
import './Dashboard.css'

function Dashboard() {
  const TEMPLATE_CACHE_KEY = 'templateQuizIds'
  const { t } = useTranslation()
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const { quizzes } = useSelector((state) => state.quiz)
  const [templateModalOpen, setTemplateModalOpen] = useState(false)
  const [templates, setTemplates] = useState([])
  const [templatesLoading, setTemplatesLoading] = useState(false)
  const [usingTemplateId, setUsingTemplateId] = useState(null)

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

  const handleDuplicateQuiz = async (quizId) => {
    const extractErrorDetail = (err) => {
      const detail = err?.response?.data?.detail
      if (typeof detail === 'string') return detail
      if (Array.isArray(detail) && detail.length > 0) {
        return detail[0]?.msg || null
      }
      return null
    }

    try {
      const response = await quizAPI.duplicate(quizId)
      message.success(t('quiz.duplicateSuccess', { defaultValue: 'Quiz duplicated successfully' }))
      loadQuizzes()
      navigate(`/quiz/${response.data.id}/edit`)
    } catch (error) {
      console.error('Failed to duplicate quiz:', error)
      const detail = extractErrorDetail(error)
      message.error(
        detail ||
        t('quiz.duplicateFailed', { defaultValue: 'Failed to duplicate quiz' })
      )
    }
  }

  const handleStopActiveSession = async (sessionId) => {
    try {
      await sessionAPI.end(sessionId)
      message.success(t('quiz.activeSessionStopped', { defaultValue: 'Active session stopped' }))
      loadQuizzes()
    } catch (error) {
      console.error('Failed to stop active session:', error)
      message.error(
        error?.response?.data?.detail ||
        t('quiz.failedToStopActiveSession', { defaultValue: 'Failed to stop active session' })
      )
    }
  }

  const handleToggleTemplate = async (quiz) => {
    const nextTemplateState = !quiz.is_template
    try {
      const response = await quizAPI.setTemplate(quiz.id, { is_template: nextTemplateState })
      const updatedQuiz = response.data
      const normalizedQuiz = {
        ...quiz,
        ...updatedQuiz,
        is_template: typeof updatedQuiz?.is_template === 'boolean' ? updatedQuiz.is_template : nextTemplateState,
      }
      const nextQuizzes = (quizzes || []).map((q) => (q.id === normalizedQuiz.id ? { ...q, ...normalizedQuiz } : q))
      dispatch(setQuizzes(nextQuizzes))
      const cachedIds = new Set(
        JSON.parse(localStorage.getItem(TEMPLATE_CACHE_KEY) || '[]').filter((id) => Number.isInteger(id))
      )
      if (normalizedQuiz.is_template) cachedIds.add(normalizedQuiz.id)
      else cachedIds.delete(normalizedQuiz.id)
      localStorage.setItem(TEMPLATE_CACHE_KEY, JSON.stringify(Array.from(cachedIds)))
      setTemplates((prev) => {
        const withoutCurrent = (prev || []).filter((tq) => tq.id !== normalizedQuiz.id)
        if (!normalizedQuiz.is_template) return withoutCurrent
        return [
          {
            id: normalizedQuiz.id,
            title: normalizedQuiz.title,
            quiz_type: normalizedQuiz.quiz_type || 'quiz',
            template_scope: normalizedQuiz.template_scope || 'tenant',
            question_count: normalizedQuiz.question_count || 0,
            tenant_id: normalizedQuiz.tenant_id,
          },
          ...withoutCurrent,
        ]
      })
      message.success(
        quiz.is_template
          ? t('quiz.templateUnsetSuccess', { defaultValue: 'Template removed' })
          : t('quiz.templateSetSuccess', { defaultValue: 'Template set successfully' })
      )
      loadQuizzes()
    } catch (error) {
      message.error(error.response?.data?.detail || t('quiz.templateSetFailed', { defaultValue: 'Failed to update template status' }))
    }
  }

  const openTemplateModal = async () => {
    setTemplateModalOpen(true)
    setTemplatesLoading(true)
    const cachedTemplateIds = JSON.parse(localStorage.getItem(TEMPLATE_CACHE_KEY) || '[]').filter((id) => Number.isInteger(id))
    let myTemplates = (quizzes || []).filter((q) => q.is_template || cachedTemplateIds.includes(q.id))
    setTemplates(
      myTemplates.map((q) => ({
        id: q.id,
        title: q.title,
        quiz_type: q.quiz_type || 'quiz',
        template_scope: q.template_scope || 'tenant',
        question_count: q.question_count || 0,
        tenant_id: q.tenant_id,
      }))
    )
    try {
      try {
        const quizListResponse = await quizAPI.list()
        const latestQuizzes = quizListResponse.data || []
        dispatch(setQuizzes(latestQuizzes))
        myTemplates = latestQuizzes.filter((q) => q.is_template || cachedTemplateIds.includes(q.id))
      } catch (refreshError) {
        // Keep existing local state as fallback.
      }

      let templateItems = []
      try {
        const response = await quizAPI.listTemplates()
        templateItems = response.data || []
      } catch (primaryError) {
        const legacyResponse = await quizAPI.listTemplatesLegacy()
        templateItems = legacyResponse.data || []
      }

      if (templateItems.length > 0) {
        setTemplates(templateItems)
      } else {
        setTemplates(myTemplates)
      }
    } catch (error) {
      if (myTemplates.length > 0) {
        setTemplates(myTemplates)
      } else {
        message.error(error.response?.data?.detail || t('quiz.templateLoadFailed', { defaultValue: 'Failed to load templates' }))
        setTemplates([])
      }
    } finally {
      setTemplatesLoading(false)
    }
  }

  const handleUseTemplate = async (templateId) => {
    setUsingTemplateId(templateId)
    try {
      let response
      try {
        response = await quizAPI.useTemplate(templateId)
      } catch (primaryError) {
        response = await quizAPI.useTemplateLegacy(templateId)
      }
      message.success(t('quiz.templateUseSuccess', { defaultValue: 'Template quiz created' }))
      setTemplateModalOpen(false)
      loadQuizzes()
      navigate(`/quiz/${response.data.id}/edit`)
    } catch (error) {
      message.error(error.response?.data?.detail || t('quiz.templateUseFailed', { defaultValue: 'Failed to use template' }))
    } finally {
      setUsingTemplateId(null)
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

  const getQuizTypeColor = (quizType) => (quizType === 'poll' ? 'purple' : 'blue')
  const getQuizTypeLabel = (quizType) => (quizType === 'poll' ? t('quiz.poll', { defaultValue: 'Poll' }) : t('quiz.quizTypeLabel', { defaultValue: 'Quiz' }))

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

  const visibleTemplateData = (templates && templates.length > 0
    ? templates
    : (quizzes || [])
        .filter((q) => {
          const cachedTemplateIds = JSON.parse(localStorage.getItem(TEMPLATE_CACHE_KEY) || '[]').filter((id) => Number.isInteger(id))
          return q.is_template || cachedTemplateIds.includes(q.id)
        })
        .map((q) => ({
          id: q.id,
          title: q.title,
          quiz_type: q.quiz_type || 'quiz',
          template_scope: q.template_scope || 'tenant',
          question_count: q.question_count || 0,
          tenant_id: q.tenant_id,
        })))

  return (
    <div className="dashboard-scroll">
      <div className="dashboard-page" style={{ padding: 24, overflowX: 'hidden' }}>
      {/* Statistics Cards */}
      <Row gutter={[8, 8]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title={t('admin.stats.totalQuizzes')}
              value={statistics.total}
              prefix={<FileTextOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title={t('dashboard.readyToLaunch', { defaultValue: 'Ready to Launch' })}
              value={statistics.byStatus.ready}
              prefix={<RocketOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title={t('dashboard.drafts', { defaultValue: 'Drafts' })}
              value={statistics.byStatus.draft}
              prefix={<EditFilled />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title={t('dashboard.totalQuestions', { defaultValue: 'Total Questions' })}
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
          <div className="dashboard-action-buttons">
            <Button icon={<StarOutlined />} onClick={openTemplateModal}>
              {t('quiz.useTemplate', { defaultValue: 'Use Template' })}
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => navigate('/quiz/new?type=quiz')}
            >
              {t('quiz.createQuiz')}
            </Button>
            <Button
              type="primary"
              icon={<BarChartOutlined />}
              onClick={() => navigate('/quiz/new?type=poll')}
              style={{ backgroundColor: '#722ed1', borderColor: '#722ed1' }}
            >
              {t('quiz.createPoll', { defaultValue: 'Create Poll' })}
            </Button>
          </div>
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
                <Tag color={getQuizTypeColor(quiz.quiz_type)}>
                  {getQuizTypeLabel(quiz.quiz_type)}
                </Tag>
                <Tag color={getStatusColor(quiz.status)}>{getStatusTranslation(quiz.status)}</Tag>
                {quiz.is_template && (
                  <Tag color={quiz.template_scope === 'global' ? 'purple' : 'blue'}>
                    {quiz.template_scope === 'global'
                      ? t('quiz.globalTemplate', { defaultValue: 'Global Template' })
                      : t('quiz.tenantTemplate', { defaultValue: 'Tenant Template' })}
                  </Tag>
                )}
                <span>
                  {t('quiz.questionCount', {
                    count: quiz.question_count || 0,
                    defaultValue: `${quiz.question_count || 0} ${t('quiz.questions')}`,
                  })}
                </span>
              </Space>
            </div>
            <div className="quiz-item-actions">
              <Button
                icon={<StarOutlined />}
                onClick={() => handleToggleTemplate(quiz)}
              >
                {quiz.is_template
                  ? t('quiz.removeTemplate', { defaultValue: 'Remove Template' })
                  : t('quiz.makeTemplate', { defaultValue: 'Make Template' })}
              </Button>
              <Button
                icon={<CopyOutlined />}
                onClick={() => handleDuplicateQuiz(quiz.id)}
              >
                {t('quiz.duplicate', { defaultValue: 'Duplicate' })}
              </Button>
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
              {quiz.has_active_session && quiz.active_session_id ? (
                <Popconfirm
                  title={t('quiz.stopActiveSessionConfirm', { defaultValue: 'Stop active session?' })}
                  description={t('quiz.stopQuizConfirm', { defaultValue: 'This will end the session for all participants. You cannot restart it.' })}
                  onConfirm={() => handleStopActiveSession(quiz.active_session_id)}
                  okText={t('quiz.stopQuizOk', { defaultValue: 'Yes, stop it' })}
                  cancelText={t('common.cancel')}
                >
                  <Button danger icon={<CloseCircleOutlined />}>
                    {t('quiz.stopActiveSession', { defaultValue: 'Stop Active Session' })}
                  </Button>
                </Popconfirm>
              ) : null}
              {quiz.status === 'ready' && !quiz.has_active_session && (
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
      <Modal
        title={t('quiz.templateLibrary', { defaultValue: 'Template Library' })}
        open={templateModalOpen}
        onCancel={() => setTemplateModalOpen(false)}
        footer={null}
        width={900}
      >
        <Table
          rowKey="id"
          loading={templatesLoading}
          dataSource={visibleTemplateData}
          pagination={{ pageSize: 8 }}
          columns={[
            {
              title: t('quiz.title', { defaultValue: 'Title' }),
              dataIndex: 'title',
            },
            {
              title: t('dashboard.type', { defaultValue: 'Type' }),
              dataIndex: 'quiz_type',
              width: 110,
              render: (value) => (
                <Tag color={getQuizTypeColor(value)}>
                  {getQuizTypeLabel(value)}
                </Tag>
              ),
            },
            {
              title: t('quiz.scope', { defaultValue: 'Scope' }),
              dataIndex: 'template_scope',
              width: 160,
              render: (value) => (
                <Tag color={value === 'global' ? 'purple' : 'blue'}>
                  {value === 'global'
                    ? t('quiz.globalTemplate', { defaultValue: 'Global Template' })
                    : t('quiz.tenantTemplate', { defaultValue: 'Tenant Template' })}
                </Tag>
              ),
            },
            {
              title: t('quiz.questions', { defaultValue: 'Questions' }),
              dataIndex: 'question_count',
              width: 120,
            },
            {
              title: t('common.actions', { defaultValue: 'Actions' }),
              width: 180,
              render: (_, record) => (
                <Button
                  type="primary"
                  loading={usingTemplateId === record.id}
                  onClick={() => handleUseTemplate(record.id)}
                >
                  {t('quiz.useTemplate', { defaultValue: 'Use Template' })}
                </Button>
              ),
            },
          ]}
        />
      </Modal>
      </div>
    </div>
  )
}

export default Dashboard
