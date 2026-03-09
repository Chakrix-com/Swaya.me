import { useEffect, useState } from 'react'
import { Card, Row, Col, Statistic, Spin, Alert, Button, Typography, Divider, DatePicker, Select, Space, message } from 'antd'
import {
  UserOutlined,
  FileTextOutlined,
  ThunderboltOutlined,
  TeamOutlined,
  ReloadOutlined,
  DesktopOutlined,
  LineChartOutlined,
  GlobalOutlined,
  DownloadOutlined,
} from '@ant-design/icons'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell, BarChart, Bar } from 'recharts'
import dayjs from 'dayjs'
import { useTranslation } from 'react-i18next'
import { statsAPI, languageTrackingAPI } from '../../services/api'
import './Admin.css'

const { Title, Text } = Typography
const { RangePicker } = DatePicker

// Colors for language charts
const LANGUAGE_COLORS = {
  en: '#1890ff',
  hi: '#52c41a',
  ta: '#722ed1',
  te: '#fa8c16',
  ka: '#eb2f96',
  bn: '#13c2c2',
  gu: '#faad14',
}

const CHART_COLORS = ['#1890ff', '#52c41a', '#722ed1', '#fa8c16', '#eb2f96', '#13c2c2', '#faad14']

function Statistics() {
  const { t } = useTranslation()
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)
  
  // History state
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyData, setHistoryData] = useState([])
  const [historyError, setHistoryError] = useState(null)
  const [dateRange, setDateRange] = useState([dayjs().subtract(7, 'day'), dayjs()])
  const [granularity, setGranularity] = useState('hourly')

  // Language tracking state
  const [languageStats, setLanguageStats] = useState(null)
  const [languageLoading, setLanguageLoading] = useState(false)
  const [languageError, setLanguageError] = useState(null)

  const fetchStats = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await statsAPI.get()
      setStats(response.data)
      setLastUpdate(new Date())
    } catch (err) {
      setError(err.response?.data?.detail || t('admin.stats.failedToLoadStats', { defaultValue: 'Failed to load statistics' }))
    } finally {
      setLoading(false)
    }
  }

  const fetchHistory = async () => {
    if (!dateRange || dateRange.length !== 2) {
      message.warning(t('admin.stats.selectDateRange'))
      return
    }

    try {
      setHistoryLoading(true)
      setHistoryError(null)
      
      const params = {
        start_date: dateRange[0].toISOString(),
        end_date: dateRange[1].toISOString(),
        granularity: granularity.toUpperCase()
      }
      
      const response = await statsAPI.getHistory(params)
      
      // Transform data for charts
      const transformed = response.data.map(snapshot => ({
        time: dayjs(snapshot.captured_at).format(granularity === 'hourly' ? 'MMM D, HH:mm' : 'MMM D'),
        users: snapshot.stats.stats.users.total,
        activeUsers: snapshot.stats.stats.users.active,
        quizzes: snapshot.stats.stats.quizzes.total,
        sessions: snapshot.stats.stats.sessions.active,
        participants: snapshot.stats.stats.participants.active_now,
        cpuPercent: snapshot.stats.stats.load?.cpu_percent || 0,
        memoryPercent: snapshot.stats.stats.load?.memory_percent || 0,
      }))
      
      setHistoryData(transformed)
      
      if (transformed.length === 0) {
        message.info(t('admin.stats.noHistoricalData'))
      } else {
        message.success(t('admin.stats.loadedDataPoints', { count: transformed.length }))
      }
    } catch (err) {
      let errorMsg = t('admin.stats.failedToLoadHistory')
      
      // Handle Pydantic validation errors (array of error objects)
      if (err.response?.data?.detail && Array.isArray(err.response.data.detail)) {
        errorMsg = err.response.data.detail.map(e => e.msg).join(', ')
      } else if (err.response?.data?.detail) {
        errorMsg = err.response.data.detail
      }
      
      setHistoryError(errorMsg)
      message.error(errorMsg)
    } finally {
      setHistoryLoading(false)
    }
  }

  const fetchLanguageStats = async () => {
    try {
      setLanguageLoading(true)
      setLanguageError(null)
      const response = await languageTrackingAPI.getStats()
      setLanguageStats(response.data)
    } catch (err) {
      const errorMsg = err.response?.data?.detail || t('admin.languageStats.error')
      setLanguageError(errorMsg)
      console.error('Language stats error:', err)
    } finally {
      setLanguageLoading(false)
    }
  }

  const handleExportLanguageStats = async () => {
    try {
      const response = await languageTrackingAPI.exportStats({ days: 30 })
      const blob = new Blob([response.data], { type: 'text/csv' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `language_stats_${dayjs().format('YYYY-MM-DD')}.csv`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
      message.success(t('admin.languageStats.exportSuccess'))
    } catch (err) {
      message.error(t('admin.languageStats.exportError'))
      console.error('Export error:', err)
    }
  }

  useEffect(() => {
    fetchStats()
    fetchLanguageStats()
  }, [])

  if (loading && !stats) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0' }}>
        <Spin size="large" tip={t('admin.stats.loadingStats')} />
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ padding: 24 }}>
        <Alert
          message={t('admin.stats.error')}
          description={error}
          type="error"
          showIcon
          action={
            <Button onClick={fetchStats} type="primary">
              {t('admin.stats.retry')}
            </Button>
          }
        />
      </div>
    )
  }

  if (!stats) return null

  const getLoadColor = (percent) => {
    if (percent < 70) return '#52c41a'
    if (percent < 85) return '#faad14'
    return '#ff4d4f'
  }

  const formatNumber = (num) => {
    return new Intl.NumberFormat().format(num)
  }

  return (
    <div className="admin-page" style={{ padding: 24 }}>
      <div className="admin-header" style={{ marginBottom: 16 }}>
        <div>
          <Title level={2} style={{ margin: 0 }}>{t('admin.stats.dashboard')}</Title>
          <Text type="secondary">
            {stats.scope === 'platform' ? t('admin.stats.platformWide') : t('admin.stats.forTenant', { tenantName: stats.tenant_name })}
          </Text>
        </div>
        <Space className="admin-header-actions" wrap>
          <Text type="secondary">
            {t('admin.stats.lastUpdated', { time: lastUpdate ? dayjs(lastUpdate).format('HH:mm:ss') : '-' })}
          </Text>
          <Button 
            icon={<ReloadOutlined />} 
            onClick={fetchStats}
            loading={loading}
          >
            {t('admin.stats.refresh')}
          </Button>
        </Space>
      </div>

      <Divider />

      {/* Current Stats Summary */}
      <Title level={4}>{t('admin.stats.currentStats')}</Title>
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={t('admin.stats.totalUsers')}
              value={stats.stats.users.total}
              prefix={<UserOutlined />}
              formatter={(value) => formatNumber(value)}
            />
            <div style={{ marginTop: 8 }}>
              <Text type="secondary">{t('admin.stats.active')} {formatNumber(stats.stats.users.active)}</Text>
              <br />
              <Text type="secondary">{t('admin.stats.inactive')} {formatNumber(stats.stats.users.inactive)}</Text>
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={t('admin.stats.totalQuizzes')}
              value={stats.stats.quizzes.total}
              prefix={<FileTextOutlined />}
              formatter={(value) => formatNumber(value)}
            />
            <div style={{ marginTop: 8 }}>
              <Text type="secondary">{t('admin.stats.ready')} {formatNumber(stats.stats.quizzes.ready)}</Text>
              <br />
              <Text type="secondary">{t('admin.stats.draft')} {formatNumber(stats.stats.quizzes.draft)}</Text>
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={t('admin.stats.activeSessions')}
              value={stats.stats.sessions.active}
              prefix={<ThunderboltOutlined />}
              valueStyle={{ color: stats.stats.sessions.active > 0 ? '#3f8600' : undefined }}
              formatter={(value) => formatNumber(value)}
            />
            <div style={{ marginTop: 8 }}>
              <Text type="secondary">{t('admin.stats.today')} {formatNumber(stats.stats.sessions.total_today)}</Text>
              <br />
              <Text type="secondary">{t('admin.stats.allTime')} {formatNumber(stats.stats.sessions.total_all_time)}</Text>
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={t('admin.stats.activeParticipants')}
              value={stats.stats.participants.active_now}
              prefix={<TeamOutlined />}
              valueStyle={{ color: stats.stats.participants.active_now > 0 ? '#3f8600' : undefined }}
              formatter={(value) => formatNumber(value)}
            />
            <div style={{ marginTop: 8 }}>
              <Text type="secondary">{t('admin.stats.allTime')} {formatNumber(stats.stats.participants.total_all_time)}</Text>
            </div>
          </Card>
        </Col>
      </Row>

      {/* System Health (Super Admin Only) */}
      {stats.scope === 'platform' && stats.stats.load && (
        <>
          <Title level={4}>{t('admin.stats.systemHealth')}</Title>
          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            <Col xs={24} sm={8}>
              <Card>
                <Statistic
                  title={t('admin.stats.cpuUsage')}
                  value={stats.stats.load.cpu_percent}
                  suffix="%"
                  valueStyle={{ color: getLoadColor(stats.stats.load.cpu_percent) }}
                  prefix={<DesktopOutlined />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card>
                <Statistic
                  title={t('admin.stats.memoryUsage')}
                  value={stats.stats.load.memory_percent}
                  suffix="%"
                  valueStyle={{ color: getLoadColor(stats.stats.load.memory_percent) }}
                  prefix={<DesktopOutlined />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card>
                <Statistic
                  title={t('admin.stats.dbConnections')}
                  value={stats.stats.load.db_connections}
                  prefix={<DesktopOutlined />}
                />
              </Card>
            </Col>
          </Row>
        </>
      )}

      <Divider />

      {/* Historical Trends */}
      <div style={{ marginBottom: 16 }}>
        <Title level={4} style={{ marginBottom: 16 }}>
          <LineChartOutlined /> {t('admin.stats.historicalTrends')}
        </Title>
        
        <Card>
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <Row gutter={[16, 16]} align="middle" className="admin-action-row">
              <Col xs={24} sm="auto">
                <Text strong>{t('admin.stats.dateRange')}</Text>
              </Col>
              <Col xs={24} sm="auto">
                <RangePicker
                  className="admin-control"
                  value={dateRange}
                  onChange={setDateRange}
                  format="YYYY-MM-DD"
                  maxDate={dayjs()}
                />
              </Col>
              <Col xs={24} sm="auto">
                <Text strong>{t('admin.stats.granularity')}</Text>
              </Col>
              <Col xs={24} sm="auto">
                <Select
                  value={granularity}
                  onChange={setGranularity}
                  className="admin-control"
                  options={[
                    { label: t('admin.stats.hourly'), value: 'hourly' },
                    { label: t('admin.stats.daily'), value: 'daily' },
                  ]}
                />
              </Col>
              <Col xs={24} sm="auto">
                <Button
                  type="primary"
                  icon={<ReloadOutlined />}
                  onClick={fetchHistory}
                  loading={historyLoading}
                  className="admin-control"
                >
                  {t('admin.stats.loadHistory')}
                </Button>
              </Col>
            </Row>

            {historyError && (
              <Alert
                message={t('admin.stats.errorLoadingHistory')}
                description={historyError}
                type="error"
                showIcon
                closable
                onClose={() => setHistoryError(null)}
              />
            )}

            {historyData.length > 0 && (
              <>
                <Divider />
                
                {/* Users Chart */}
                <div>
                  <Title level={5}>{t('admin.stats.usersOverTime')}</Title>
                  <ResponsiveContainer width="100%" height={250}>
                    <LineChart data={historyData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="time" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Line type="monotone" dataKey="users" stroke="#1890ff" name={t('admin.stats.chartLegendTotalUsers')} />
                      <Line type="monotone" dataKey="activeUsers" stroke="#52c41a" name={t('admin.stats.chartLegendActiveUsers')} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                <Divider />

                {/* Quizzes & Sessions Chart */}
                <div>
                  <Title level={5}>{t('admin.stats.quizzesAndSessions')}</Title>
                  <ResponsiveContainer width="100%" height={250}>
                    <LineChart data={historyData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="time" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Line type="monotone" dataKey="quizzes" stroke="#722ed1" name={t('admin.stats.chartLegendTotalQuizzes')} />
                      <Line type="monotone" dataKey="sessions" stroke="#fa8c16" name={t('admin.stats.chartLegendActiveSessions')} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                <Divider />

                {/* Participants Chart */}
                <div>
                  <Title level={5}>{t('admin.stats.activeParticipants')}</Title>
                  <ResponsiveContainer width="100%" height={250}>
                    <LineChart data={historyData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="time" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Line type="monotone" dataKey="participants" stroke="#eb2f96" name={t('admin.stats.activeParticipants')} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                {/* System Load (Super Admin Only) */}
                {stats.scope === 'platform' && (
                  <>
                    <Divider />
                    <div>
                      <Title level={5}>{t('admin.stats.systemLoad')}</Title>
                      <ResponsiveContainer width="100%" height={250}>
                        <LineChart data={historyData}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="time" />
                          <YAxis />
                          <Tooltip />
                          <Legend />
                          <Line type="monotone" dataKey="cpuPercent" stroke="#faad14" name={`${t('admin.stats.cpuUsage')} %`} />
                          <Line type="monotone" dataKey="memoryPercent" stroke="#ff4d4f" name={`${t('admin.stats.memoryUsage')} %`} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </>
                )}
              </>
            )}

            {historyData.length === 0 && !historyLoading && !historyError && (
              <Alert
                message={t('admin.stats.noData')}
                description={t('admin.stats.selectDateRangeToView')}
                type="info"
                showIcon
              />
            )}
          </Space>
        </Card>
      </div>

      <Divider />

      {/* Language Usage Analytics */}
      <div style={{ marginBottom: 16 }}>
        <Title level={4}>
          <GlobalOutlined /> {t('admin.languageStats.title')}
        </Title>
        
        {languageLoading && (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Spin size="large" tip={t('admin.languageStats.loading')} />
          </div>
        )}
        
        {languageError && (
          <Alert
            message={t('admin.languageStats.error')}
            description={languageError}
            type="error"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}
        
        {languageStats && !languageLoading && (
          <Card>
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              {/* Summary Cards */}
              <Row gutter={[16, 16]}>
                <Col xs={24} sm={12} lg={6}>
                  <Card>
                    <Statistic
                      title={t('admin.languageStats.totalEvents')}
                      value={languageStats.summary?.total_events || 0}
                      prefix={<LineChartOutlined />}
                      valueStyle={{ color: '#1890ff' }}
                    />
                  </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                  <Card>
                    <Statistic
                      title={t('admin.languageStats.mostPopular')}
                      value={languageStats.summary?.most_popular_language || t('common.noData')}
                      prefix={<GlobalOutlined />}
                      valueStyle={{ color: '#52c41a' }}
                    />
                    <div style={{ marginTop: 8 }}>
                      <Text type="secondary">
                        {languageStats.summary?.most_popular_count || 0} {t('admin.languageStats.events')}
                      </Text>
                    </div>
                  </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                  <Card>
                    <Statistic
                      title={t('admin.languageStats.uniqueUsers')}
                      value={languageStats.summary?.unique_users || 0}
                      prefix={<UserOutlined />}
                      valueStyle={{ color: '#722ed1' }}
                    />
                  </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                  <Card>
                    <Statistic
                      title={t('admin.languageStats.uniqueSessions')}
                      value={languageStats.summary?.unique_sessions || 0}
                      prefix={<TeamOutlined />}
                      valueStyle={{ color: '#fa8c16' }}
                    />
                  </Card>
                </Col>
              </Row>

              <Divider />

              {/* Charts Row */}
              <Row gutter={[16, 16]}>
                {/* Pie Chart - Language Distribution */}
                <Col xs={24} lg={12}>
                  <Card title={t('admin.languageStats.distributionChart')}>
                    {languageStats.event_stats && languageStats.event_stats.length > 0 ? (
                      <ResponsiveContainer width="100%" height={300}>
                        <PieChart>
                          <Pie
                            data={languageStats.event_stats}
                            dataKey="total_events"
                            nameKey="language"
                            cx="50%"
                            cy="50%"
                            outerRadius={100}
                            label={(entry) => `${t(`languages.${entry.language}`)}: ${entry.total_events}`}
                          >
                            {languageStats.event_stats.map((entry, index) => (
                              <Cell 
                                key={`cell-${index}`} 
                                fill={LANGUAGE_COLORS[entry.language] || CHART_COLORS[index % CHART_COLORS.length]} 
                              />
                            ))}
                          </Pie>
                          <Tooltip formatter={(value, name, props) => [value, t(`languages.${props.payload.language}`)]} />
                          <Legend formatter={(value) => t(`languages.${value}`)} />
                        </PieChart>
                      </ResponsiveContainer>
                    ) : (
                      <Alert message={t('admin.languageStats.noData')} type="info" showIcon />
                    )}
                  </Card>
                </Col>

                {/* Bar Chart - Events by Language */}
                <Col xs={24} lg={12}>
                  <Card title={t('admin.languageStats.eventsChart')}>
                    {languageStats.event_stats && languageStats.event_stats.length > 0 ? (
                      <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={languageStats.event_stats}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis 
                            dataKey="language" 
                            tickFormatter={(value) => t(`languages.${value}`)}
                          />
                          <YAxis />
                          <Tooltip 
                            labelFormatter={(value) => t(`languages.${value}`)}
                          />
                          <Legend />
                          <Bar dataKey="total_events" fill="#1890ff" name={t('admin.languageStats.events')} />
                          <Bar dataKey="unique_users" fill="#52c41a" name={t('admin.languageStats.users')} />
                          <Bar dataKey="unique_sessions" fill="#722ed1" name={t('admin.languageStats.sessions')} />
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <Alert message={t('admin.languageStats.noData')} type="info" showIcon />
                    )}
                  </Card>
                </Col>
              </Row>

              <Divider />

              {/* Line Chart - Trends Over Time */}
              <Card title={t('admin.languageStats.trendsChart')}>
                {languageStats.trends && languageStats.trends.length > 0 ? (
                  (() => {
                    // Transform trends data for multi-line chart
                    const transformedTrends = {}
                    languageStats.trends.forEach(item => {
                      const date = dayjs(item.date).format('MMM D')
                      if (!transformedTrends[date]) {
                        transformedTrends[date] = { date }
                      }
                      transformedTrends[date][item.language] = item.count
                    })
                    const trendData = Object.values(transformedTrends)
                    
                    // Get unique languages for lines
                    const languages = [...new Set(languageStats.trends.map(t => t.language))]
                    
                    return (
                      <ResponsiveContainer width="100%" height={300}>
                        <LineChart data={trendData}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="date" />
                          <YAxis />
                          <Tooltip />
                          <Legend />
                          {languages.map((lang, index) => (
                            <Line
                              key={lang}
                              type="monotone"
                              dataKey={lang}
                              stroke={LANGUAGE_COLORS[lang] || CHART_COLORS[index % CHART_COLORS.length]}
                              name={t(`languages.${lang}`)}
                            />
                          ))}
                        </LineChart>
                      </ResponsiveContainer>
                    )
                  })()
                ) : (
                  <Alert message={t('admin.languageStats.noData')} type="info" showIcon />
                )}
              </Card>

              <Divider />

              {/* Action Buttons */}
              <Row gutter={16}>
                <Col>
                  <Button 
                    type="primary" 
                    icon={<DownloadOutlined />}
                    onClick={handleExportLanguageStats}
                  >
                    {t('admin.languageStats.export')}
                  </Button>
                </Col>
                <Col>
                  <Button 
                    icon={<ReloadOutlined />}
                    onClick={fetchLanguageStats}
                    loading={languageLoading}
                  >
                    {t('admin.languageStats.refresh')}
                  </Button>
                </Col>
              </Row>
            </Space>
          </Card>
        )}

        {!languageStats && !languageLoading && !languageError && (
          <Alert
            message={t('admin.languageStats.noData')}
            type="info"
            showIcon
          />
        )}
      </div>

    </div>
  )
}

export default Statistics
