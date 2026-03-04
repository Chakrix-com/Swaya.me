import React from 'react'
import ReactDOM from 'react-dom/client'
import { Provider } from 'react-redux'
import { ConfigProvider } from 'antd'
import enUS from 'antd/locale/en_US'
import App from './App.jsx'
import { store } from './store/store'
import './locales/i18n'
import 'bootstrap/dist/css/bootstrap-grid.min.css'
import 'bootstrap/dist/css/bootstrap-utilities.min.css'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Provider store={store}>
      <ConfigProvider
        locale={enUS}
        theme={{
          token: {
            colorPrimary: '#1890ff',
          },
        }}
      >
        <App />
      </ConfigProvider>
    </Provider>
  </React.StrictMode>,
)
