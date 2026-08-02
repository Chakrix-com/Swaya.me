import { useEffect, useState } from 'react'
import { App, Button, Typography, Tag, Tooltip, theme } from 'antd'
import { CopyOutlined, ReloadOutlined, CheckCircleOutlined, ClockCircleOutlined, HistoryOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import SafeModal from '../../../components/SafeModal'
import EmailChipInput, { isValidEmail } from '../../../components/EmailChipInput'
import { codingChallengeAPI } from '../../../services/api'

const { Text } = Typography
const MAX_BATCH = 50

function StatusTag({ status, t }) {
  if (status === 'started') {
    return <Tag color="success" icon={<CheckCircleOutlined />}>{t('codingChallenge.inviteStatusStarted', 'Started')}</Tag>
  }
  if (status === 'expired') {
    return <Tag icon={<ClockCircleOutlined />}>{t('codingChallenge.inviteStatusExpired', 'Expired')}</Tag>
  }
  return <Tag color="processing" icon={<ClockCircleOutlined />}>{t('codingChallenge.inviteStatusPending', 'Pending')}</Tag>
}

export default function InviteCandidatesModal({ open, quizId, onClose, t }) {
  const { token: designToken } = theme.useToken()
  const { message } = App.useApp()
  const [emails, setEmails] = useState([])
  const [sending, setSending] = useState(false)
  const [results, setResults] = useState(null)
  const [invites, setInvites] = useState(null)
  const [loadingInvites, setLoadingInvites] = useState(false)
  const [resendingEmail, setResendingEmail] = useState(null)

  const loadInvites = async () => {
    setLoadingInvites(true)
    try {
      const res = await codingChallengeAPI.listInvites(quizId)
      setInvites(res.data)
    } catch {
      // supplementary list — a failed fetch shouldn't block sending new invites
    } finally {
      setLoadingInvites(false)
    }
  }

  useEffect(() => {
    if (open) {
      setEmails([])
      setResults(null)
      loadInvites()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, quizId])

  const validEmails = emails.filter(isValidEmail)
  const hasInvalid = emails.some((e) => !isValidEmail(e))

  const handleSend = async () => {
    if (validEmails.length === 0) return
    setSending(true)
    try {
      const res = await codingChallengeAPI.invite(quizId, validEmails)
      setResults(res.data)
      setEmails(emails.filter((e) => !isValidEmail(e))) // keep invalid ones so the host can fix/remove them
      loadInvites()
    } catch (error) {
      message.error(error.response?.data?.detail || t('common.error'))
    } finally {
      setSending(false)
    }
  }

  const handleResend = async (email) => {
    setResendingEmail(email)
    try {
      const res = await codingChallengeAPI.invite(quizId, [email])
      const r = res.data[0]
      message[r.sent ? 'success' : 'warning'](
        r.sent
          ? t('codingChallenge.resendSuccess', 'Invite resent to {{email}}', { email })
          : t('codingChallenge.inviteEmailFailed', "Couldn't email the invite — please share the link directly.")
      )
      loadInvites()
    } catch (error) {
      message.error(error.response?.data?.detail || t('common.error'))
    } finally {
      setResendingEmail(null)
    }
  }

  const close = () => onClose()

  return (
    <SafeModal
      title={t('codingChallenge.inviteCandidates', 'Invite Candidates')}
      open={open}
      onCancel={close}
      width={560}
      footer={[
        <Button key="close" onClick={close}>{t('common.close', 'Close')}</Button>,
        <Button key="send" type="primary" loading={sending} disabled={validEmails.length === 0} onClick={handleSend}>
          {t('codingChallenge.sendInvites', 'Send Invites')}
          {validEmails.length > 0 ? ` (${validEmails.length})` : ''}
        </Button>,
      ]}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <Text>{t('codingChallenge.inviteEmailPrompt', 'Add candidate emails — press Enter, comma, or paste a list:')}</Text>
        <EmailChipInput
          value={emails}
          onChange={setEmails}
          placeholder="candidate@example.com"
          maxItems={MAX_BATCH}
          autoFocus
        />
        {hasInvalid && (
          <Text type="danger" style={{ fontSize: 12 }}>
            {t('codingChallenge.inviteInvalidHint', 'Fix or remove the highlighted email(s) before sending.')}
          </Text>
        )}

        {results && (
          <div style={{ border: `1px solid ${designToken.colorBorderSecondary}`, borderRadius: 8, padding: 10, background: designToken.colorFillQuaternary }}>
            <Text strong style={{ fontSize: 12 }}>
              {t('codingChallenge.inviteResultsSummary', '{{sent}} of {{total}} sent', {
                sent: results.filter((r) => r.sent).length, total: results.length,
              })}
            </Text>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
              {results.map((r) => (
                <div key={r.email} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, fontSize: 12 }}>
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {r.error ? (
                      <Tooltip title={r.error}>
                        <span>{'⚠'} {r.email}</span>
                      </Tooltip>
                    ) : (
                      <>{r.sent ? '✓' : '⚠'} {r.email}</>
                    )}
                  </span>
                  <Tooltip title={t('exam.copyLink')}>
                    <Button
                      size="small" type="text" icon={<CopyOutlined />}
                      onClick={() => { navigator.clipboard.writeText(r.invite_url); message.success(t('exam.linkCopied')) }}
                    />
                  </Tooltip>
                </div>
              ))}
            </div>
          </div>
        )}

        <div style={{ marginTop: 4 }}>
          <Text strong style={{ fontSize: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
            <HistoryOutlined /> {t('codingChallenge.previouslyInvited', 'Previously Invited')}
          </Text>
          <div style={{ maxHeight: 220, overflowY: 'auto', marginTop: 6 }}>
            {loadingInvites ? (
              <Text type="secondary" style={{ fontSize: 12 }}>{t('common.loading', 'Loading...')}</Text>
            ) : !invites || invites.length === 0 ? (
              <Text type="secondary" style={{ fontSize: 12 }}>{t('codingChallenge.noInvitesYet', 'No one invited yet.')}</Text>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {invites.map((inv) => (
                  <div
                    key={inv.candidate_email}
                    style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8,
                      padding: '6px 8px', borderRadius: 6, fontSize: 12,
                      background: designToken.colorBgContainer, border: `1px solid ${designToken.colorBorderSecondary}`,
                    }}
                  >
                    <div style={{ overflow: 'hidden' }}>
                      <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{inv.candidate_email}</div>
                      <Text type="secondary" style={{ fontSize: 11 }}>{dayjs(inv.invited_at).format('MMM D, h:mm A')}</Text>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
                      <StatusTag status={inv.status} t={t} />
                      {inv.status !== 'started' && (
                        <Tooltip title={t('codingChallenge.resendInvite', 'Resend invite')}>
                          <Button
                            size="small" type="text" icon={<ReloadOutlined />}
                            loading={resendingEmail === inv.candidate_email}
                            onClick={() => handleResend(inv.candidate_email)}
                          />
                        </Tooltip>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </SafeModal>
  )
}
