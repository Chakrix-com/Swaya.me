import { useEffect, useState } from 'react'
import { Card, Statistic, Spin, Alert, Typography } from 'antd'
import {
  UserOutlined,
  FileTextOutlined,
  ThunderboltOutlined,
  TeamOutlined,
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { statsAPI } from '../services/api'

const { Text } = Typography

function StatsPanel({ userRole }) {
  const { t } = useTranslation()
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)

  const fetchStats = async () => {
    try {
      setError(null)
      const response = await statsAPI.get()
      setStats(response.data)
      setLastUpdate(new Date())
    } catch (err) {
      setError(err.response?.data?.detail || t('admin.stats.failedToLoadStats'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStats()
    
    const interval = setInterval(fetchStats, 30000)
    
    return () => clearInterval(interval)
  }, [])

  if (loading && !stats) {
    return (
      <div style={{ padding: 16, textAlign: 'center' }}>
        <Spin size="small" />
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ padding: 16 }}>
        <Alert message={t('admin.panel.statsUnavailable')} type="warning" showIcon size="small" />
      </div>
    )
  }

  if (!stats) return null

  const isSuperAdmin = userRole === 'super_admin'
  const title = stats.scope === 'platform' ? `📊 ${t('admin.panel.platformStats')}` : `📊 ${t('admin.panel.organizationStats')}`

  return (
    <Card
      size="small"
      title={<Text strong style={{ fontSize: 12 }}>{title}</Text>}
      style={{ margin: '16px 8px', fontSize: 12 }}
      bodyStyle={{ padding: 8 }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div>
          <Statistic
            title={<Text style={{ fontSize: 11 }}>👤 {t('admin.panel.users')}</Text>}
            value={stats.stats.users.total}
            valueStyle={{ fontSize: 16 }}
          />
          <Text type="secondary" style={{ fontSize: 10 }}>
            ✓ {stats.stats.users.active} {t('admin.panel.active')} · ✗ {stats.stats.users.inactive} {t('admin.panel.inactive')}
          </Text>
        </div>

        <div>
          <Statistic
            title={<Text style={{ fontSize: 11 }}>📝 {t('admin.panel.quizzes')}</Text>}
            value={stats.stats.quizzes.total}
            valueStyle={{ fontSize: 16 }}
          />
          <Text type="secondary" style={{ fontSize: 10 }}>
            ✓ {stats.stats.quizzes.ready} {t('admin.panel.ready')} · 📝 {stats.stats.quizzes.draft} {t('admin.panel.draft')}
          </Text>
        </div>

        <div>
          <Statistic
            title={<Text style={{ fontSize: 11 }}>⚡ {t('admin.panel.activeSessions')}</Text>}
            value={stats.stats.sessions.active}
            valueStyle={{ fontSize: 16, color: stats.stats.sessions.active > 0 ? '#52c41a' : undefined }}
          />
          <Text type="secondary" style={{ fontSize: 10 }}>
            {t('admin.panel.today')}: {stats.stats.sessions.total_today} · {t('admin.panel.total')}: {formatNumber(stats.stats.sessions.total_all_time)}
          </Text>
        </div>

        <div>
          <Statistic
            title={<Text style={{ fontSize: 11 }}>👥 {t('admin.panel.participants')}</Text>}
            value={formatNumber(stats.stats.participants.total_all_time)}
            valueStyle={{ fontSize: 16 }}
          />
          <Text type="secondary" style={{ fontSize: 10 }}>
            {t('admin.panel.activeNow')}: {stats.stats.participants.active_now}
          </Text>
        </div>

        {isSuperAdmin && stats.stats.load && (
          <div>
            <Text style={{ fontSize: 11 }}>💻 {t('admin.panel.systemLoad')}</Text>
            <br />
            <Text type="secondary" style={{ fontSize: 10 }}>
              {t('admin.panel.cpu')}: <Text style={{ color: getLoadColor(stats.stats.load.cpu_percent) }}>
                {stats.stats.load.cpu_percent}%
              </Text>
              {' · '}
              {t('admin.panel.memory')}: <Text style={{ color: getLoadColor(stats.stats.load.memory_percent) }}>
                {stats.stats.load.memory_percent}%
              </Text>
            </Text>
          </div>
        )}
      </div>

      {lastUpdate && (
        <Text type="secondary" style={{ fontSize: 9, display: 'block', marginTop: 8, textAlign: 'center' }}>
          ↻ {t('admin.panel.updated')} {getTimeAgo(lastUpdate, t)}
        </Text>
      )}
    </Card>
  )
}

function formatNumber(num) {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
  return num
}

function getLoadColor(percent) {
  if (percent > 85) return '#ff4d4f'
  if (percent > 70) return '#faad14'
  return '#52c41a'
}

function getTimeAgo(date, t) {
  const seconds = Math.floor((new Date() - date) / 1000)
  if (seconds < 10) return t('admin.panel.justNow')
  if (seconds < 60) return t('admin.panel.secondsAgo', { seconds })
  if (seconds < 3600) return t('admin.panel.minutesAgo', { minutes: Math.floor(seconds / 60) })
  return t('admin.panel.hoursAgo', { hours: Math.floor(seconds / 3600) })
}

export default StatsPanel
