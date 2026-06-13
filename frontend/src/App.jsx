import { useState, createContext, useContext, useEffect, lazy, Suspense, useRef } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom'
import { ProLayout } from '@ant-design/pro-components'
import { App as AntApp, Button, ConfigProvider, Dropdown, Space, Divider, Typography, Tooltip, Spin, Tag } from 'antd'
import enUS from 'antd/locale/en_US'
import hiIN from 'antd/locale/hi_IN'
import {
  DashboardOutlined,
  PlusOutlined,
  LogoutOutlined,
  QuestionCircleOutlined,
  TeamOutlined,
  BarChartOutlined,
  ApartmentOutlined,
  MessageOutlined,
  AppstoreOutlined,
  SlidersOutlined,
  LoadingOutlined,
  CrownOutlined,
  UserOutlined,
  UnorderedListOutlined,
  AppstoreAddOutlined,
  TrophyOutlined,
} from '@ant-design/icons'
import { useSelector, useDispatch } from 'react-redux'
import { useTranslation } from 'react-i18next'
import { logout, refreshUser, initAuth } from './store/authSlice'
import { authAPI } from './services/api'
import { applyTheme, getTheme } from './themes/themes'
import ThemePicker from './components/ThemePicker'
import './themes/funky-studio.css'

// Essential public routes (eagerly loaded)
import Home from './features/home/Home'
import Login from './features/auth/Login'
import Register from './features/auth/Register'
import GoogleCallback from './features/auth/GoogleCallback'
import AudienceJoin from './features/audience/AudienceJoin'
import AudienceSession from './features/audience/AudienceSession'
import OfflinePollSession from './features/offline-poll/OfflinePollSession'
import ExamSession from './features/exam/ExamSession'

// Heavy or Host-only routes (lazily loaded)
const PrivacyPolicy = lazy(() => import('./features/home/PrivacyPolicy'))
const TermsOfService = lazy(() => import('./features/home/TermsOfService'))
const About = lazy(() => import('./features/home/About'))
const Help = lazy(() => import('./features/home/Help'))
const VerifyEmail = lazy(() => import('./features/auth/VerifyEmail'))
const ForgotPassword = lazy(() => import('./features/auth/ForgotPassword'))
const ResetPassword = lazy(() => import('./features/auth/ResetPassword'))
const Dashboard = lazy(() => import('./features/dashboard/Dashboard'))
const Activities = lazy(() => import('./features/activities/Activities'))
const TemplateGallery = lazy(() => import('./features/templates/TemplateGallery'))
const ExplorePage = lazy(() => import('./features/explore/ExplorePage'))
const ResultsHub = lazy(() => import('./features/results/ResultsHub'))
const UserPlans = lazy(() => import('./features/dashboard/UserPlans'))
const QuizBuilder = lazy(() => import('./features/quiz/QuizBuilder'))
const QuizControl = lazy(() => import('./features/quiz/QuizControl'))
const QuizHistory = lazy(() => import('./features/quiz/QuizHistory'))
const SessionRecap = lazy(() => import('./features/quiz/SessionRecap'))
const OfflinePollResults = lazy(() => import('./features/offline-poll/OfflinePollResults'))
const ExamResults = lazy(() => import('./features/exam/ExamResults'))
const IntegrityReport = lazy(() => import('./features/exam/IntegrityReport'))
const QuizPresent = lazy(() => import('./features/quiz/QuizPresent'))
const UserManagement = lazy(() => import('./features/admin/components/UserManagement'))
const Statistics = lazy(() => import('./features/admin/Statistics'))
const OrganizationManagement = lazy(() => import('./features/admin/OrganizationManagement'))
const FeedbackManagement = lazy(() => import('./features/admin/FeedbackManagement'))
const PlatformQuizzes = lazy(() => import('./features/admin/PlatformQuizzes'))
const TierManagement = lazy(() => import('./features/admin/TierManagement'))

import LanguageSwitcher from './components/LanguageSwitcher'
import GlobalOverlay from './components/GlobalOverlay'
import SidebarFolderTree from './components/SidebarFolderTree'
import SidebarLiveSessions from './components/SidebarLiveSessions'
import logo from './assets/logo.png'
import './App.css'

// Map i18n language codes to Ant Design locales
const localeMap = {
  en: enUS,
  hi: hiIN,
  ta: enUS, // Fallback to English for unsupported locales
  te: enUS,
  ka: enUS,
  bn: enUS,
  gu: enUS,
}

export const VisitorThemeContext = createContext({ theme: 'light', toggle: () => {} })

const TIER_COLORS = { free: 'default', basic: 'blue', pro: 'purple', enterprise: 'gold' }

function TierBadge({ user }) {
  const [limits, setLimits] = useState(null)
  const fetchedRef = useRef(false)
  const { t } = useTranslation()

  useEffect(() => {
    if (!user || fetchedRef.current) return
    fetchedRef.current = true
    authAPI.getMyLimits()
      .then(r => setLimits(r.data))
      .catch(() => {})
  }, [user])

  if (!user) return null
  const tier = user.tier || 'free'
  const color = TIER_COLORS[tier] || 'default'
  const tooltipContent = limits ? (
    <div style={{ fontSize: 12, lineHeight: '20px' }}>
      <div>{t('dashboard.tierTooltipParticipants')}: <b>{limits.max_participants}</b></div>
      <div>{t('dashboard.tierTooltipQuestions')}: <b>{limits.max_questions}</b></div>
      <div>{t('dashboard.tierTooltipSessions')}: <b>{limits.max_concurrent_events}</b></div>
    </div>
  ) : null

  return (
    <Tooltip title={tooltipContent} placement="bottomRight">
      <Tag color={color} style={{ cursor: 'default', textTransform: 'uppercase', fontWeight: 600, fontSize: 11, letterSpacing: '0.5px' }}>
        {tier}
      </Tag>
    </Tooltip>
  )
}

// Layout wrapper for authenticated routes
function AuthenticatedLayout({ children }) {
  const navigate = useNavigate()
  const location = useLocation()
  const dispatch = useDispatch()
  const { user } = useSelector((state) => state.auth)
  const { t } = useTranslation()
  const [collapsed, setCollapsed] = useState(false)
  const themeId = useSelector((state) => state.theme.themeId)
  const currentTheme = getTheme(themeId)

  const handleLogout = async () => {
    try { await authAPI.logout() } catch (_) {}
    dispatch(logout())
    navigate('/login')
  }

  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin'
  const isSuperAdmin = user?.role === 'super_admin'

  return (
    <ProLayout
      title="Swaya.me"
      headerTitleRender={(logo, title) => (
        <span
          style={{ display: 'inline-flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}
          onClick={(e) => { e.preventDefault(); e.stopPropagation(); navigate('/dashboard') }}
        >
          {logo}{title}
        </span>
      )}
      onMenuHeaderClick={(e) => { e.preventDefault(); navigate('/dashboard') }}
      logo={<img src={logo} alt="Swaya.me" style={{ height: 26, width: 'auto', borderRadius: 4 }} />}
      layout="mix"
      splitMenus={false}
      contentWidth="Fluid"
      fixedHeader
      fixSiderbar
      collapsed={collapsed}
      onCollapse={setCollapsed}
      contentStyle={{ overflowX: 'hidden', padding: 0 }}
      token={currentTheme.proLayout}
      location={{
        pathname: location.pathname,
      }}
      route={{
        path: '/',
        routes: [
          {
            path: '/dashboard',
            name: t('common.dashboard'),
            icon: <DashboardOutlined />,
          },
          {
            path: '/activities',
            name: t('activities.title'),
            icon: <UnorderedListOutlined />,
          },
          {
            path: '/templates',
            name: t('templates.title'),
            icon: <AppstoreAddOutlined />,
          },
          {
            path: '/results',
            name: t('results.title', 'Results'),
            icon: <TrophyOutlined />,
          },
          // Hidden routes — still routable but not shown in sidebar
          { path: '/plans',                    hideInMenu: true },
          { path: '/quiz/new',                 hideInMenu: true },
          { path: '/quiz',                     hideInMenu: true },
          { path: '/admin/statistics',         hideInMenu: true },
          { path: '/admin/users',              hideInMenu: true },
          { path: '/admin/organizations',      hideInMenu: true },
          { path: '/admin/platform-quizzes',   hideInMenu: true },
          { path: '/admin/tier-management',    hideInMenu: true },
          { path: '/admin/feedback',           hideInMenu: true },
        ],
      }}
      menuItemRender={(item, dom) => (
        <div onClick={() => navigate(item.path || '/')}>
          {dom}
        </div>
      )}
      menuFooterRender={() => !collapsed ? (
        <>
          <SidebarLiveSessions />
          <SidebarFolderTree />
        </>
      ) : null}
      avatarProps={{
        src: null,
        icon: <UserOutlined style={{ fontSize: 13 }} />,
        style: { background: currentTheme.antd.token.colorPrimary, color: currentTheme.onPrimary, cursor: 'pointer', flexShrink: 0 },
        title: <span className="hide-on-mobile">{user?.full_name || user?.email || t('common.user')}</span>,
        size: 'small',
        render: (_props, dom) => (
          <Dropdown
            trigger={['click']}
            placement="bottomRight"
            menu={{
              items: [
                {
                  key: 'profile-label',
                  type: 'group',
                  label: (
                    <div style={{ padding: '2px 0 6px' }}>
                      <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--sw-text1)' }}>
                        {user?.full_name || user?.email}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--sw-text3)', marginTop: 2 }}>
                        {user?.email}
                      </div>
                      <div style={{ marginTop: 6 }}>
                        <TierBadge user={user} />
                      </div>
                    </div>
                  ),
                },
                { type: 'divider' },
                {
                  key: 'plans',
                  icon: <CrownOutlined />,
                  label: t('dashboard.plansTab', 'User Plans'),
                  onClick: () => navigate('/plans'),
                },
                ...(isAdmin ? [
                  { type: 'divider' },
                  {
                    key: 'statistics',
                    icon: <BarChartOutlined />,
                    label: t('admin.statistics', 'Statistics'),
                    onClick: () => navigate('/admin/statistics'),
                  },
                  {
                    key: 'users',
                    icon: <TeamOutlined />,
                    label: t('admin.userManagement', 'User Management'),
                    onClick: () => navigate('/admin/users'),
                  },
                  ...(isSuperAdmin ? [
                    {
                      key: 'organizations',
                      icon: <ApartmentOutlined />,
                      label: t('admin.organizations', 'Organizations'),
                      onClick: () => navigate('/admin/organizations'),
                    },
                    {
                      key: 'platform-quizzes',
                      icon: <AppstoreOutlined />,
                      label: t('admin.platformQuizzes', 'Platform Quizzes'),
                      onClick: () => navigate('/admin/platform-quizzes'),
                    },
                    {
                      key: 'tier-management',
                      icon: <SlidersOutlined />,
                      label: t('admin.tierManagement', 'Tier Management'),
                      onClick: () => navigate('/admin/tier-management'),
                    },
                    {
                      key: 'feedback',
                      icon: <MessageOutlined />,
                      label: t('admin.feedback', 'Feedback'),
                      onClick: () => navigate('/admin/feedback'),
                    },
                  ] : []),
                ] : []),
                { type: 'divider' },
                {
                  key: 'logout',
                  icon: <LogoutOutlined />,
                  label: t('tooltip.logout', 'Sign Out'),
                  danger: true,
                  onClick: handleLogout,
                },
              ],
            }}
          >
            <span style={{ cursor: 'pointer' }}>{dom}</span>
          </Dropdown>
        ),
      }}
      actionsRender={() => [
        <Tooltip key="theme" title={t('tooltip.themePicker', 'Choose a UI theme')}><span><ThemePicker /></span></Tooltip>,
        <Tooltip key="language" title={t('tooltip.languageSwitcher')}><span><LanguageSwitcher /></span></Tooltip>,
      ]}
      footerRender={() => location.pathname.includes('/control') ? null : (
        <div style={{ textAlign: 'center', padding: '12px 24px', borderTop: '1px solid var(--sw-border)' }}>
          <Space split={<Divider type="vertical" />} wrap style={{ justifyContent: 'center' }}>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>© 2026 Swaya.me. {t('home.footer.rights')}</Typography.Text>
            <Button type="link" size="small" onClick={() => navigate('/about')} style={{ padding: 0, fontSize: 12 }}>{t('pages.legal.aboutLink')}</Button>
            <Button type="link" size="small" onClick={() => navigate('/privacy-policy')} style={{ padding: 0, fontSize: 12 }}>{t('pages.legal.privacyLink')}</Button>
            <Button type="link" size="small" onClick={() => navigate('/terms-of-service')} style={{ padding: 0, fontSize: 12 }}>{t('pages.legal.termsLink')}</Button>
            {/* Help link hidden — page still exists at /help */}
            {/* <Button type="link" size="small" onClick={() => navigate('/help')} style={{ padding: 0, fontSize: 12 }}>{t('pages.help.footerHelp')}</Button> */}
            <a href="mailto:info@chakrix.net" style={{ fontSize: 12 }}>{t('pages.legal.contactLink')}</a>
          </Space>
        </div>
      )}
    >
      {children}
    </ProLayout>
  )
}

// Simple layout for public routes
function PublicLayout({ children }) {
  return (
    <div className="visitor-theme visitor-theme--light">
      {children}
    </div>
  )
}

function AppRoutes() {
  const { isAuthenticated } = useSelector((state) => state.auth)
  const location = useLocation()

  // Legal/info routes are always public — accessible whether logged in or not
  if (
    location.pathname === '/privacy-policy' ||
    location.pathname === '/terms-of-service' ||
    location.pathname === '/about' ||
    location.pathname === '/help'
  ) {
    return (
      <PublicLayout>
        <Routes>
          <Route path="/privacy-policy" element={<PrivacyPolicy />} />
          <Route path="/terms-of-service" element={<TermsOfService />} />
          <Route path="/about" element={<About />} />
          <Route path="/help" element={<Help />} />
        </Routes>
      </PublicLayout>
    )
  }

  // Explore page — public template gallery, no auth
  if (location.pathname.startsWith('/explore')) {
    return (
      <Suspense fallback={<div style={{ padding: 40, textAlign: 'center' }}><Spin size="large" /></div>}>
        <Routes>
          <Route path="/explore" element={<ExplorePage />} />
          <Route path="*" element={<Navigate to="/explore" />} />
        </Routes>
      </Suspense>
    )
  }

  // Join, session, present, offline poll, and exam routes are always public
  if (
    location.pathname.startsWith('/join') ||
    location.pathname.startsWith('/session') ||
    location.pathname.startsWith('/present') ||
    location.pathname.startsWith('/poll') ||
    location.pathname.startsWith('/e/')
  ) {
    return (
      <PublicLayout>
        <Routes>
          <Route path="/join" element={<AudienceJoin />} />
          <Route path="/join/:joinCode" element={<AudienceJoin />} />
          <Route path="/session/:sessionId" element={<AudienceSession />} />
          <Route path="/present/:sessionId" element={<QuizPresent />} />
          <Route path="/poll/:slug" element={<OfflinePollSession />} />
          <Route path="/e/:slug" element={<ExamSession />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </PublicLayout>
    )
  }

  // Other public routes — only when not authenticated
  if (!isAuthenticated) {
    return (
      <PublicLayout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/verify-email" element={<VerifyEmail />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/auth/google/callback" element={<GoogleCallback />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </PublicLayout>
    )
  }

  // Authenticated routes (with ProLayout)
  return (
    <AuthenticatedLayout>
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/activities" element={<Activities />} />
        <Route path="/templates" element={<TemplateGallery />} />
        <Route path="/explore" element={<ExplorePage />} />
        <Route path="/results" element={<ResultsHub />} />
        <Route path="/plans" element={<UserPlans />} />
        <Route path="/quiz/new" element={<QuizBuilder />} />
        <Route path="/quiz/:id/edit" element={<QuizBuilder />} />
        <Route path="/quiz/:id/control" element={<QuizControl />} />
        <Route path="/quiz/:id/history" element={<QuizHistory />} />
        <Route path="/quiz/:id/recap/:sessionId" element={<SessionRecap />} />
        <Route path="/quiz/:id/offline-results" element={<OfflinePollResults />} />
        <Route path="/quiz/:id/exam-results" element={<ExamResults />} />
        <Route path="/quiz/:id/exam-results/integrity/:participantId" element={<IntegrityReport />} />
        <Route path="/admin/statistics" element={<Statistics />} />
        <Route path="/admin/users" element={<UserManagement />} />
        <Route path="/admin/organizations" element={<OrganizationManagement />} />
        <Route path="/admin/platform-quizzes" element={<PlatformQuizzes />} />
        <Route path="/admin/tier-management" element={<TierManagement />} />
        <Route path="/admin/feedback" element={<FeedbackManagement />} />
        <Route path="/" element={<Navigate to="/dashboard" />} />
        <Route path="*" element={<Navigate to="/dashboard" />} />
      </Routes>
    </AuthenticatedLayout>
  )
}

function App() {
  const { i18n } = useTranslation()
  const locale = localeMap[i18n.language] || enUS
  const dispatch = useDispatch()
  const { isAuthenticated, loading: authLoading } = useSelector((state) => state.auth)
  const themeId = useSelector((state) => state.theme.themeId)
  const currentTheme = getTheme(themeId)

  useEffect(() => {
    applyTheme(currentTheme)
  }, [themeId])

  // On mount, check if the HttpOnly cookie session is still valid and populate user state
  useEffect(() => {
    authAPI.getMe()
      .then(r => dispatch(initAuth(r.data)))
      .catch(() => dispatch(initAuth(null)))
  }, [])

  if (authLoading) {
    return (
      <ConfigProvider locale={locale} theme={currentTheme.antd}>
        <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Spin indicator={<LoadingOutlined style={{ fontSize: 24 }} spin />} />
        </div>
      </ConfigProvider>
    )
  }

  return (
    <ConfigProvider locale={locale} theme={currentTheme.antd}>
      <AntApp>
        <Router>
          <Suspense fallback={
            <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Spin indicator={<LoadingOutlined style={{ fontSize: 24 }} spin />} />
            </div>
          }>
            <AppRoutes />
          </Suspense>
          <GlobalOverlay />
        </Router>
      </AntApp>
    </ConfigProvider>
  )
}

export default App
