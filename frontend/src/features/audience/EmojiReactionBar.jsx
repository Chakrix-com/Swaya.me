import { useState } from 'react'
import { App, Rate } from 'antd'
import { useTranslation } from 'react-i18next'
import { feedbackAPI } from '../../services/api'
import './EmojiReactionBar.css'

const REACTION_SETS = {
  thumbs: [
    { key: 'thumbs_down', emoji: '👎', labelKey: 'reactions.notGreat', defaultLabel: 'Not great' },
    { key: 'thumbs_up', emoji: '👍', labelKey: 'reactions.likedIt', defaultLabel: 'Liked it' },
    { key: 'thumbs_love', emoji: '👍👍', labelKey: 'reactions.lovedIt', defaultLabel: 'Loved it!' },
  ],
  hearts: [
    { key: 'hearts_broken', emoji: '💔', labelKey: 'reactions.meh', defaultLabel: 'Meh' },
    { key: 'hearts_red', emoji: '❤️', labelKey: 'reactions.likedIt', defaultLabel: 'Liked it' },
    { key: 'hearts_fire', emoji: '❤️‍🔥', labelKey: 'reactions.lovedIt', defaultLabel: 'Loved it!' },
  ],
  vibes: [
    { key: 'vibes_boring', emoji: '😴', labelKey: 'reactions.boring', defaultLabel: 'Boring' },
    { key: 'vibes_ok', emoji: '😐', labelKey: 'reactions.ok', defaultLabel: 'OK' },
    { key: 'vibes_good', emoji: '😊', labelKey: 'reactions.good', defaultLabel: 'Good' },
    { key: 'vibes_amazing', emoji: '🤩', labelKey: 'reactions.amazing', defaultLabel: 'Amazing!' },
  ],
}

export default function EmojiReactionBar({ reactionStyle, sessionToken }) {
  const { t } = useTranslation()
  const { message } = App.useApp()
  const [submitted, setSubmitted] = useState(false)
  const [selectedKey, setSelectedKey] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleReact = async (reactionKey) => {
    if (submitted || loading) return
    setSelectedKey(reactionKey)
    setLoading(true)
    try {
      await feedbackAPI.submitParticipant(sessionToken, { reaction: reactionKey })
      setSubmitted(true)
      navigator.vibrate?.(50)
    } catch (err) {
      if (err.response?.status === 409) {
        setSubmitted(true)
      } else {
        message.error(err.response?.data?.detail || t('reactions.submitFailed', { defaultValue: 'Could not submit reaction' }))
        setSelectedKey(null)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleStarReact = async (val) => {
    if (submitted || loading || val === 0) return
    const key = `stars_${val}`
    setSelectedKey(key)
    setLoading(true)
    try {
      await feedbackAPI.submitParticipant(sessionToken, { reaction: key, rating: val })
      setSubmitted(true)
      navigator.vibrate?.(50)
    } catch (err) {
      if (err.response?.status === 409) {
        setSubmitted(true)
      } else {
        message.error(err.response?.data?.detail || t('reactions.submitFailed', { defaultValue: 'Could not submit reaction' }))
        setSelectedKey(null)
      }
    } finally {
      setLoading(false)
    }
  }

  if (reactionStyle === 'stars') {
    const starVal = selectedKey ? Number(selectedKey.replace('stars_', '')) : 0
    return (
      <div className={`aud2-reaction-bar${submitted ? ' aud2-reaction-bar--done' : ''}`}>
        <p className="aud2-reaction-prompt">
          {submitted
            ? t('reactions.thanks', { defaultValue: 'Thanks for your feedback!' })
            : t('reactions.howWasIt', { defaultValue: 'How was it?' })}
        </p>
        <Rate
          style={{ fontSize: 40, color: '#faad14' }}
          value={starVal}
          onChange={handleStarReact}
          disabled={submitted}
        />
      </div>
    )
  }

  const options = REACTION_SETS[reactionStyle]
  if (!options) return null

  return (
    <div className={`aud2-reaction-bar${submitted ? ' aud2-reaction-bar--done' : ''}`}>
      <p className="aud2-reaction-prompt">
        {submitted
          ? t('reactions.thanks', { defaultValue: 'Thanks for your feedback!' })
          : t('reactions.howWasIt', { defaultValue: 'How was it?' })}
      </p>
      <div className="aud2-reaction-options">
        {options.map((opt) => {
          const isSelected = selectedKey === opt.key
          return (
            <button
              key={opt.key}
              className={`aud2-reaction-btn${isSelected ? ' aud2-reaction-btn--selected' : ''}${submitted && !isSelected ? ' aud2-reaction-btn--faded' : ''}`}
              onClick={() => handleReact(opt.key)}
              disabled={submitted || loading}
            >
              <span className="aud2-reaction-emoji">{opt.emoji}</span>
              <span className="aud2-reaction-label">{t(opt.labelKey, { defaultValue: opt.defaultLabel })}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
