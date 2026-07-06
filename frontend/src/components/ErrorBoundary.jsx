import { Component } from 'react'
import { withTranslation } from 'react-i18next'
import { Button } from 'antd'
import { WarningOutlined } from '@ant-design/icons'

class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error, info) {
    // No error-reporting service wired up yet — the console is where anyone
    // reproducing this on a VDI/remote session can find the actual stack.
    console.error('Unhandled render error:', error, info?.componentStack)
  }

  render() {
    if (!this.state.hasError) {
      return this.props.children
    }

    const { t } = this.props
    return (
      <div style={{
        minHeight: '100vh', display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', gap: 16,
        padding: 24, textAlign: 'center',
      }}>
        <WarningOutlined style={{ fontSize: 40, color: '#faad14' }} />
        <h2 style={{ margin: 0 }}>{t('errorBoundary.title', 'Something went wrong')}</h2>
        <p style={{ margin: 0, color: '#666', maxWidth: 360 }}>
          {t('errorBoundary.description', 'This page hit an unexpected error. Reloading usually fixes it.')}
        </p>
        <Button type="primary" onClick={() => window.location.reload()}>
          {t('errorBoundary.reload', 'Reload page')}
        </Button>
        <p style={{ margin: 0, fontSize: 12, color: '#999' }}>
          {t('errorBoundary.contactSupport', 'If this keeps happening, contact support.')}
        </p>
      </div>
    )
  }
}

export default withTranslation()(ErrorBoundary)
