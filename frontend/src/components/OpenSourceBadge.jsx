import React from 'react'
import { GithubOutlined } from '@ant-design/icons'
import './OpenSourceBadge.css'

function OpenSourceBadge({ className = '' }) {
  return (
    <a
      href="https://github.com/Chakrix-com/Swaya.me"
      target="_blank"
      rel="noopener noreferrer"
      className={`open-source-badge ${className}`.trim()}
      aria-label="View source on GitHub"
    >
      <GithubOutlined />
    </a>
  )
}

export default OpenSourceBadge
