import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom'
import { ProLayout } from '@ant-design/pro-components'
import { Button, ConfigProvider, Space, Divider, Typography } from 'antd'
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
  MoonOutlined,
  SunOutlined,
} from '@ant-design/icons'
import { useSelector, useDispatch } from 'react-redux'
import { useTranslation } from 'react-i18next'
import { logout } from './store/authSlice'
import Home from './features/home/Home'
import PrivacyPolicy from './features/home/PrivacyPolicy'
import TermsOfService from './features/home/TermsOfService'
import About from './features/home/About'
import Login from './features/auth/Login'
import Register from './features/auth/Register'
import VerifyEmail from './features/auth/VerifyEmail'
import ForgotPassword from './features/auth/ForgotPassword'
import ResetPassword from './features/auth/ResetPassword'
import Dashboard from './features/dashboard/Dashboard'
import QuizBuilder from './features/quiz/QuizBuilder'
import QuizControl from './features/quiz/QuizControl'
import QuizHistory from './features/quiz/QuizHistory'
import AudienceJoin from './features/audience/AudienceJoin'
import AudienceSession from './features/audience/AudienceSession'
import QuizPresent from './features/quiz/QuizPresent'
import UserManagement from './features/admin/components/UserManagement'
import Statistics from './features/admin/Statistics'
import OrganizationManagement from './features/admin/OrganizationManagement'
import FeedbackManagement from './features/admin/FeedbackManagement'
import PlatformQuizzes from './features/admin/PlatformQuizzes'
import TierManagement from './features/admin/TierManagement'
import LanguageSwitcher from './components/LanguageSwitcher'
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

const getInitialVisitorTheme = () => {
  const storedTheme = localStorage.getItem(THEME_STORAGE_KEY)
  if (storedTheme === 'dark' || storedTheme === 'light') {
    return storedTheme
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

// Layout wrapper for authenticated routes
function AuthenticatedLayout({ children }) {
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
      token={{
        layout: {
          header: {
            colorBgHeader: '#ffffff',
            colorBgScrollHeader: '#ffffff',
          },
          bgLayout: '#f5f5f5',
        },
      }}
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
        <LanguageSwitcher key="language" />,
        <LogoutOutlined 
          key="logout" 
          onClick={handleLogout}
          style={{ fontSize: 16, cursor: 'pointer' }}
        />,
      ]}
      footerRender={() => (
        <div style={{ textAlign: 'center', padding: '12px 24px', borderTop: '1px solid #f0f0f0', background: '#fff' }}>
          <Space split={<Divider type="vertical" />} wrap style={{ justifyContent: 'center' }}>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>© 2026 Swaya.me. {t('home.footer.rights')}</Typography.Text>
            <Button type="link" size="small" onClick={() => navigate('/about')} style={{ padding: 0, fontSize: 12 }}>{t('pages.legal.aboutLink')}</Button>
            <Button type="link" size="small" onClick={() => navigate('/privacy-policy')} style={{ padding: 0, fontSize: 12 }}>{t('pages.legal.privacyLink')}</Button>
            <Button type="link" size="small" onClick={() => navigate('/terms-of-service')} style={{ padding: 0, fontSize: 12 }}>{t('pages.legal.termsLink')}</Button>
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
function PublicLayout({ children, visitorTheme, onToggleVisitorTheme, hideVisitorThemeToggle = false }) {
  return (
    <div className={`visitor-theme visitor-theme--${visitorTheme}`}>
      {!hideVisitorThemeToggle && (
        <div className="visitor-theme-toggle">
          <Button
            type="text"
            icon={visitorTheme === 'dark' ? <SunOutlined /> : <MoonOutlined />}
            onClick={onToggleVisitorTheme}
            aria-label={`Switch to ${visitorTheme === 'dark' ? 'light' : 'dark'} mode`}
          />
        </div>
      )}
      {children}
    </div>
  )
}

function AppRoutes({ visitorTheme, onToggleVisitorTheme }) {
  const { isAuthenticated } = useSelector((state) => state.auth)
  const location = useLocation()

  // Legal/info routes are always public — accessible whether logged in or not
  if (
    location.pathname === '/privacy-policy' ||
    location.pathname === '/terms-of-service' ||
    location.pathname === '/about'
  ) {
    return (
      <Routes>
        <Route path="/privacy-policy" element={<PrivacyPolicy />} />
        <Route path="/terms-of-service" element={<TermsOfService />} />
        <Route path="/about" element={<About />} />
      </Routes>
    )
  }

  // Join, session, and present routes are always public — accessible whether logged in or not
  if (
    location.pathname.startsWith('/join') ||
    location.pathname.startsWith('/session') ||
    location.pathname.startsWith('/present')
  ) {
    return (
      <PublicLayout
        visitorTheme={visitorTheme}
        onToggleVisitorTheme={onToggleVisitorTheme}
        hideVisitorThemeToggle={location.pathname.startsWith('/present')}
      >
        <Routes>
          <Route path="/join" element={<AudienceJoin />} />
          <Route path="/join/:joinCode" element={<AudienceJoin />} />
          <Route path="/session/:sessionId" element={<AudienceSession />} />
          <Route path="/present/:sessionId" element={<QuizPresent />} />
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
        <Route path="/quiz/new" element={<QuizBuilder />} />
        <Route path="/quiz/:id/edit" element={<QuizBuilder />} />
        <Route path="/quiz/:id/control" element={<QuizControl />} />
        <Route path="/quiz/:id/history" element={<QuizHistory />} />
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

  const handleToggleVisitorTheme = () => {
    setVisitorTheme((currentTheme) => {
      const nextTheme = currentTheme === 'dark' ? 'light' : 'dark'
      localStorage.setItem(THEME_STORAGE_KEY, nextTheme)
      return nextTheme
    })
  }

  return (
    <ConfigProvider locale={locale}>
      <Router>
        <AppRoutes visitorTheme={visitorTheme} onToggleVisitorTheme={handleToggleVisitorTheme} />
      </Router>
    </ConfigProvider>
  )
}

export default App
