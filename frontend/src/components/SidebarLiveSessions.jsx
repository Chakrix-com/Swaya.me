import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSelector, useDispatch } from 'react-redux'
import { Collapse, Badge, Button, Popconfirm, Space, message } from 'antd'
import { WifiOutlined, StopOutlined } from '@ant-design/icons'
import { setQuizzes } from '../store/quizSlice'
import { sessionAPI } from '../services/api'
import './SidebarLiveSessions.css'

function SidebarLiveSessions() {
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const { quizzes } = useSelector(s => s.quiz)

  const activeSessions = useMemo(
    () => (quizzes || []).filter(q => q.has_active_session),
    [quizzes]
  )

  const handleStop = async (sessionId) => {
    try {
      await sessionAPI.end(sessionId)
      message.success('Session stopped')
      const updated = (quizzes || []).map(q =>
        q.active_session_id === sessionId
          ? { ...q, has_active_session: false, active_session_id: null }
          : q
      )
      dispatch(setQuizzes(updated))
    } catch (e) {
      message.error(e?.response?.data?.detail || 'Failed to stop session')
    }
  }

  if (activeSessions.length === 0) return null

  const collapseItems = [{
    key: 'live',
    label: (
      <Space size={6}>
        <Badge status="processing" color="#10B981" />
        <span style={{ fontWeight: 600, fontSize: 13, color: '#374151' }}>Live Sessions</span>
        <span className="sidebar-live-count">{activeSessions.length}</span>
      </Space>
    ),
    children: (
      <div className="sidebar-live-list">
        {activeSessions.map(quiz => (
          <div key={quiz.id} className="sidebar-live-item">
            <div className="sidebar-live-title">{quiz.title}</div>
            <div className="sidebar-live-sub">
              {quiz.response_count > 0 ? `${quiz.response_count} responses` : 'Session active'}
            </div>
            <Space size={4} style={{ marginTop: 6 }}>
              <Button
                type="primary"
                size="small"
                icon={<WifiOutlined />}
                onClick={() => navigate(`/quiz/${quiz.id}/control`)}
                style={{ fontSize: 11, height: 24, background: '#6366F1', borderColor: '#6366F1' }}
              >
                Open
              </Button>
              <Popconfirm
                title="Stop this session?"
                description="This will end the session for all participants."
                onConfirm={() => handleStop(quiz.active_session_id)}
                okText="Stop"
                okButtonProps={{ danger: true }}
                cancelText="Cancel"
              >
                <Button
                  danger
                  size="small"
                  icon={<StopOutlined />}
                  style={{ fontSize: 11, height: 24 }}
                >
                  End
                </Button>
              </Popconfirm>
            </Space>
          </div>
        ))}
      </div>
    ),
  }]

  return (
    <div className="sidebar-live-accordion">
      <Collapse
        defaultActiveKey={[]}
        ghost
        items={collapseItems}
        className="sidebar-live-collapse"
      />
    </div>
  )
}

export default SidebarLiveSessions
