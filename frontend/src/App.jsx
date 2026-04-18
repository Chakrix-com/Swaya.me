import { useState, createContext, useContext, useEffect, lazy, Suspense, useRef } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom'
import { ProLayout } from '@ant-design/pro-components'
import { App as AntApp, Button, ConfigProvider, Space, Divider, Typography, theme as antTheme, Tooltip, Spin, Tag } from 'antd'
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
  SunOutlined,
  MoonOutlined,
  LoadingOutlined,
} from '@ant-design/icons'
import { useSelector, useDispatch } from 'react-redux'
import { useTranslation } from 'react-i18next'
import { logout, refreshUser } from './store/authSlice'
import { authAPI } from './services/api'

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
const QuizBuilder = lazy(() => import('./features/quiz/QuizBuilder'))
const QuizControl = lazy(() => import('./features/quiz/QuizControl'))
const QuizHistory = lazy(() => import('./features/quiz/QuizHistory'))
const OfflinePollResults = lazy(() => import('./features/offline-poll/OfflinePollResults'))
const ExamResults = lazy(() => import('./features/exam/ExamResults'))
const QuizPresent = lazy(() => import('./features/quiz/QuizPresent'))
const UserManagement = lazy(() => import('./features/admin/components/UserManagement'))
const Statistics = lazy(() => import('./features/admin/Statistics'))
const OrganizationManagement = lazy(() => import('./features/admin/OrganizationManagement'))
const FeedbackManagement = lazy(() => import('./features/admin/FeedbackManagement'))
const PlatformQuizzes = lazy(() => import('./features/admin/PlatformQuizzes'))
const TierManagement = lazy(() => import('./features/admin/TierManagement'))

import LanguageSwitcher from './components/LanguageSwitcher'
import GlobalOverlay from './components/GlobalOverlay'
import StatsPanel from './components/StatsPanel'
import BetaBadge from './components/BetaBadge'
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

const THEME_STORAGE_KEY = 'visitor-theme-preference'

export const VisitorThemeContext = createContext({ theme: 'dark', toggle: () => {} })

const getInitialVisitorTheme = () => {
  const storedTheme = localStorage.getItem(THEME_STORAGE_KEY)
  if (storedTheme === 'dark' || storedTheme === 'light') {
    return storedTheme
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

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
function AuthenticatedLayout({ children, visitorTheme, onToggleVisitorTheme }) {
  const navigate = useNavigate()
  const location = useLocation()
  const dispatch = useDispatch()
  const { user } = useSelector((state) => state.auth)
  const { t } = useTranslation()
  const [collapsed, setCollapsed] = useState(false)

  const handleLogout = () => {
    dispatch(logout())
    navigate('/login')
  }

  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin'
  const isSuperAdmin = user?.role === 'super_admin'

  return (
    <VisitorThemeContext.Provider value={{ theme: visitorTheme, toggle: onToggleVisitorTheme }}>
    <ProLayout
      title="Swaya.me"
      logo={null}
      headerTitleRender={() => (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 12 }}>
          <img src={logo} alt="Swaya.me Logo" style={{ height: 'auto', maxHeight: '32px', maxWidth: '100%', objectFit: 'contain', borderRadius: '4px' }} />
          <span>Swaya.me</span>
          <BetaBadge />
        </span>
      )}
      layout="mix"
      splitMenus={false}
      contentWidth="Fluid"
      fixedHeader
      fixSiderbar
      collapsed={collapsed}
      onCollapse={setCollapsed}
      contentStyle={{ overflowX: 'hidden' }}
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
            path: '/quiz/new',
            name: t('quiz.createQuiz'),
            icon: <PlusOutlined />,
            hideInMenu: true,
          },
          {
            path: '/quiz',
            name: t('quiz.questions'),
            icon: <QuestionCircleOutlined />,
            hideInMenu: true,
          },
          ...(isAdmin ? [
            {
              path: '/admin/statistics',
              name: t('admin.statistics'),
              icon: <BarChartOutlined />,
            },
            {
              path: '/admin/users',
              name: t('admin.userManagement'),
              icon: <TeamOutlined />,
            },
            ...(isSuperAdmin ? [{
              path: '/admin/organizations',
              name: t('admin.organizations'),
              icon: <ApartmentOutlined />,
            },
            {
              path: '/admin/platform-quizzes',
              name: t('admin.platformQuizzes'),
              icon: <AppstoreOutlined />,
            },
            {
              path: '/admin/tier-management',
              name: t('admin.tierManagement'),
              icon: <SlidersOutlined />,
            },
            {
              path: '/admin/feedback',
              name: t('admin.feedback'),
              icon: <MessageOutlined />,
            }] : [])
          ] : []),
        ],
      }}
      menuItemRender={(item, dom) => (
        <div onClick={() => navigate(item.path || '/')}>
          {dom}
        </div>
      )}
      menuFooterRender={() => {
        if (isAdmin && !collapsed) {
          return <StatsPanel userRole={user?.role} />
        }
        return null
      }}
      avatarProps={{
        src: null,
        title: <span className="hide-on-mobile">{user?.full_name || user?.email || t('common.user')}</span>,
        size: 'small',
        render: (props, dom) => {
          return dom
        },
      }}
      actionsRender={() => [
        <TierBadge key="tier" user={user} />,
        <Tooltip key="language" title={t('tooltip.languageSwitcher')}><span><LanguageSwitcher /></span></Tooltip>,
        <Tooltip key="theme" title={t('tooltip.themeToggle')}>
          <Button
            type="text"
            icon={visitorTheme === 'dark' ? <SunOutlined /> : <MoonOutlined />}
            onClick={onToggleVisitorTheme}
            style={{ fontSize: 16 }}
          />
        </Tooltip>,
        <Tooltip key="logout" title={t('tooltip.logout')}>
          <LogoutOutlined
            onClick={handleLogout}
            style={{ fontSize: 16, cursor: 'pointer' }}
          />
        </Tooltip>,
      ]}
      footerRender={() => (
        <div style={{ textAlign: 'center', padding: '12px 24px', borderTop: '1px solid rgba(0,0,0,0.06)' }}>
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
    </VisitorThemeContext.Provider>
  )
}

// Simple layout for public routes
function PublicLayout({ children, visitorTheme, onToggleVisitorTheme }) {
  return (
    <VisitorThemeContext.Provider value={{ theme: visitorTheme, toggle: onToggleVisitorTheme }}>
      <div className={`visitor-theme visitor-theme--${visitorTheme}`}>
        {children}
      </div>
    </VisitorThemeContext.Provider>
  )
}

function AppRoutes({ visitorTheme, onToggleVisitorTheme }) {
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
      <PublicLayout
        visitorTheme={visitorTheme}
        onToggleVisitorTheme={onToggleVisitorTheme}
      >
        <Routes>
          <Route path="/privacy-policy" element={<PrivacyPolicy />} />
          <Route path="/terms-of-service" element={<TermsOfService />} />
          <Route path="/about" element={<About />} />
            <Route path="/help" element={<Help visitorTheme={visitorTheme} />} />
        </Routes>
      </PublicLayout>
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
      <PublicLayout
        visitorTheme={visitorTheme}
        onToggleVisitorTheme={onToggleVisitorTheme}
      >
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
      <PublicLayout visitorTheme={visitorTheme} onToggleVisitorTheme={onToggleVisitorTheme}>
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
    <AuthenticatedLayout visitorTheme={visitorTheme} onToggleVisitorTheme={onToggleVisitorTheme}>
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/quiz/new" element={<QuizBuilder />} />
        <Route path="/quiz/:id/edit" element={<QuizBuilder />} />
        <Route path="/quiz/:id/control" element={<QuizControl />} />
        <Route path="/quiz/:id/history" element={<QuizHistory />} />
        <Route path="/quiz/:id/offline-results" element={<OfflinePollResults />} />
        <Route path="/quiz/:id/exam-results" element={<ExamResults />} />
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
  const [visitorTheme, setVisitorTheme] = useState(getInitialVisitorTheme)
  const dispatch = useDispatch()
  const { isAuthenticated } = useSelector((state) => state.auth)

  useEffect(() => {
    document.documentElement.dataset.theme = visitorTheme
  }, [visitorTheme])

  useEffect(() => {
    if (!isAuthenticated) return
    authAPI.getMe()
      .then(r => dispatch(refreshUser(r.data)))
      .catch(() => {})
  }, [isAuthenticated])

  const handleToggleVisitorTheme = () => {
    setVisitorTheme((currentTheme) => {
      const nextTheme = currentTheme === 'dark' ? 'light' : 'dark'
      localStorage.setItem(THEME_STORAGE_KEY, nextTheme)
      return nextTheme
    })
  }

  return (
    <ConfigProvider
      locale={locale}
      theme={{ algorithm: visitorTheme === 'dark' ? antTheme.darkAlgorithm : antTheme.defaultAlgorithm }}
    >
      <AntApp>
        <Router>
          <Suspense fallback={
            <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Spin indicator={<LoadingOutlined style={{ fontSize: 24 }} spin />} />
            </div>
          }>
            <AppRoutes visitorTheme={visitorTheme} onToggleVisitorTheme={handleToggleVisitorTheme} />
          </Suspense>
          <VisitorThemeContext.Provider value={{ theme: visitorTheme, toggle: handleToggleVisitorTheme }}>
            <GlobalOverlay />
          </VisitorThemeContext.Provider>
        </Router>
      </AntApp>
    </ConfigProvider>
  )
}

export default App
