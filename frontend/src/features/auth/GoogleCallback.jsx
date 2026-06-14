import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import { Spin } from 'antd'
import { loginSuccess, loginFailure } from '../../store/authSlice'
import { authAPI } from '../../services/api'

function GoogleCallback() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const dispatch = useDispatch()

  useEffect(() => {
    const code = searchParams.get('code')
    const state = searchParams.get('state')
    if (!code) {
      navigate('/login', { replace: true })
      return
    }
    authAPI.googleCallback(code, state)
      .then(r => {
        dispatch(loginSuccess(r.data))
        navigate('/dashboard', { replace: true })
      })
      .catch(() => {
        dispatch(loginFailure('Google sign-in failed'))
        navigate('/login', { replace: true })
      })
  }, [])

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
      <Spin size="large" />
    </div>
  )
}

export default GoogleCallback
