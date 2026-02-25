import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom'
import { ProLayout } from '@ant-design/pro-components'
import { ConfigProvider } from 'antd'
import enUS from 'antd/locale/en_US'
import hiIN from 'antd/locale/hi_IN'
import { 
  DashboardOutlined, 
  PlusOutlined, 
  LogoutOutlined,
  QuestionCircleOutlined,
  TeamOutlined,
  BarChartOutlined,
  ApartmentOutlined
} from '@ant-design/icons'
import { useSelector, useDispatch } from 'react-redux'
import { useTranslation } from 'react-i18next'
import { logout } from './store/authSlice'
import Home from './features/home/Home'
import Login from './features/auth/Login'
import Register from './features/auth/Register'
import Dashboard from './features/dashboard/Dashboard'
import QuizBuilder from './features/quiz/QuizBuilder'
import QuizControl from './features/quiz/QuizControl'
import AudienceJoin from './features/audience/AudienceJoin'
import AudienceSession from './features/audience/AudienceSession'
import UserManagement from './features/admin/components/UserManagement'
import Statistics from './features/admin/Statistics'
import OrganizationManagement from './features/admin/OrganizationManagement'
import LanguageSwitcher from './components/LanguageSwitcher'
import StatsPanel from './components/StatsPanel'
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
      layout="mix"
      splitMenus={false}
      contentWidth="Fluid"
      fixedHeader
      fixSiderbar
      collapsed={collapsed}
      onCollapse={setCollapsed}
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
        title: user?.full_name || user?.email || t('common.user'),
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
    >
      {children}
    </ProLayout>
  )
}

// Simple layout for public routes
function PublicLayout({ children }) {
  return (
    <div style={{ minHeight: '100vh' }}>
      {children}
    </div>
  )
}

function AppRoutes() {
  const { isAuthenticated } = useSelector((state) => state.auth)
  const location = useLocation()

  // Public routes (no ProLayout)
  const publicRoutes = ['/', '/login', '/register', '/join', '/session']
  const isPublicRoute = publicRoutes.some(route => location.pathname === '/' || location.pathname.startsWith(route))

  if (isPublicRoute && !isAuthenticated) {
    return (
      <PublicLayout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/join" element={<AudienceJoin />} />
          <Route path="/join/:joinCode" element={<AudienceJoin />} />
          <Route path="/session/:sessionId" element={<AudienceSession />} />
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
        <Route path="/admin/statistics" element={<Statistics />} />
        <Route path="/admin/users" element={<UserManagement />} />
        <Route path="/admin/organizations" element={<OrganizationManagement />} />
        <Route path="/" element={<Navigate to="/dashboard" />} />
        <Route path="*" element={<Navigate to="/dashboard" />} />
      </Routes>
    </AuthenticatedLayout>
  )
}

function App() {
  const { i18n } = useTranslation()
  const locale = localeMap[i18n.language] || enUS

  return (
    <ConfigProvider locale={locale}>
      <Router>
        <AppRoutes />
      </Router>
    </ConfigProvider>
  )
}

export default App
