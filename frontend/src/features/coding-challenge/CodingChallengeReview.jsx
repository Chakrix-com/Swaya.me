/**
 * CodingChallengeReview — examiner review page
 * Route: /quiz/coding-challenge-review/:questionId (authenticated host)
 * One entry per candidate who has a workspace for this question (a question can
 * have many candidates via repeated invites). All candidate-originated content
 * (transcript, timeline, test output) is rendered as plain text — never
 * dangerouslySetInnerHTML, matching the project's stance elsewhere.
 */
import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  Typography, Table, Tag, Collapse, Alert, Spin, Result, Button, Space, Select, Empty,
} from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import { codingChallengeAPI } from '../../services/api'

const { Title, Text, Paragraph } = Typography

const STATUS_COLORS = {
  graded: 'success',
  partial_failed: 'warning',
  failed: 'error',
  queued: 'default',
  grading: 'processing',
}

const CRITERION_LABELS = {
  functional_correctness: 'codingChallenge.critFunctionalCorrectness',
  ai_usage_efficiency: 'codingChallenge.critAiUsageEfficiency',
  prompt_quality: 'codingChallenge.critPromptQuality',
  validation_discipline: 'codingChallenge.critValidationDiscipline',
  code_quality: 'codingChallenge.critCodeQuality',
  architecture: 'codingChallenge.critArchitecture',
  time_taken: 'codingChallenge.critTimeTaken',
  proctoring: 'codingChallenge.critProctoring',
}

function ScoreBreakdownTable({ breakdown, t }) {
  const rows = Object.entries(breakdown || {}).map(([criterion, data]) => ({
    key: criterion,
    criterion: t(CRITERION_LABELS[criterion] || criterion, criterion),
    weight: data.weight,
    score: data.score,
    contribution: data.contribution,
  }))
  return (
    <Table
      dataSource={rows}
      pagination={false}
      size="small"
      columns={[
        { title: t('codingChallenge.criterion', 'Criterion'), dataIndex: 'criterion' },
        { title: t('codingChallenge.weight', 'Weight'), dataIndex: 'weight', render: (w) => `${w}%` },
        { title: t('codingChallenge.score', 'Score'), dataIndex: 'score' },
        { title: t('codingChallenge.contribution', 'Contribution'), dataIndex: 'contribution' },
      ]}
    />
  )
}

function CandidateDetail({ entry, t }) {
  const submission = entry.submission
  if (!submission) {
    return <Alert type="info" showIcon message={t('codingChallenge.notSubmittedYet', 'Not submitted yet')} />
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Space>
        <Tag color={STATUS_COLORS[submission.status] || 'default'}>{submission.status}</Tag>
        {submission.ai_score != null && (
          <Text strong>{t('codingChallenge.aiScore', 'Score')}: {submission.ai_score}/100 ({submission.ai_verdict})</Text>
        )}
      </Space>

      {(submission.status === 'failed' || submission.status === 'partial_failed') && submission.error_message && (
        <Alert
          type={submission.status === 'failed' ? 'error' : 'warning'}
          showIcon
          message={submission.status === 'partial_failed'
            ? t('codingChallenge.partialFailedTitle', 'Graded with a partial result')
            : t('codingChallenge.failedTitle', 'Grading could not be completed')}
          description={submission.error_message}
        />
      )}

      {submission.total_count != null && (
        <Text>{t('codingChallenge.testResults', 'Test results')}: {submission.passed_count}/{submission.total_count}</Text>
      )}

      {submission.score_breakdown && (
        <div>
          <Title level={5}>{t('codingChallenge.scoreBreakdown', 'Score Breakdown')}</Title>
          <ScoreBreakdownTable breakdown={submission.score_breakdown} t={t} />
          {submission.ai_rationale && (
            <Paragraph type="secondary" style={{ marginTop: 8 }}>{submission.ai_rationale}</Paragraph>
          )}
        </div>
      )}

      {submission.ai_token_usage && (
        <div>
          <Text strong>{t('codingChallenge.tokenUsage', 'AI Token Usage')}: </Text>
          <Text>
            {submission.ai_token_usage.input_tokens || 0} {t('codingChallenge.inputTokens', 'input')},{' '}
            {submission.ai_token_usage.output_tokens || 0} {t('codingChallenge.outputTokens', 'output')}
            {' '}({submission.ai_token_usage.turns || 0} {t('codingChallenge.turns', 'turns')})
          </Text>
        </div>
      )}

      <Collapse
        items={[
          submission.test_output != null && {
            key: 'test_output',
            label: t('codingChallenge.testOutput', 'Test Output'),
            children: <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{submission.test_output}</pre>,
          },
          submission.code_timeline != null && {
            key: 'code_timeline',
            label: t('codingChallenge.codeTimeline', 'Code Timeline (git log -p)'),
            children: <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', maxHeight: 500, overflowY: 'auto' }}>{submission.code_timeline}</pre>,
          },
          submission.ai_transcript_raw != null && {
            key: 'transcript',
            label: t('codingChallenge.aiTranscript', 'AI Chat Transcript (raw)'),
            children: <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', maxHeight: 500, overflowY: 'auto' }}>{submission.ai_transcript_raw}</pre>,
          },
        ].filter(Boolean)}
      />
    </Space>
  )
}

export default function CodingChallengeReview() {
  const { questionId } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)
  const [selectedEmail, setSelectedEmail] = useState(null)

  useEffect(() => {
    const load = async () => {
      try {
        const res = await codingChallengeAPI.getReview(questionId)
        setData(res.data)
        if (res.data.candidates?.length > 0) {
          setSelectedEmail(res.data.candidates[0].candidate_email)
        }
      } catch (err) {
        setError(err.response?.data?.detail || t('common.error'))
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [questionId, t])

  if (loading) {
    return <div style={{ textAlign: 'center', paddingTop: 80 }}><Spin size="large" /></div>
  }
  if (error) {
    return <Result status="error" title={t('common.error')} subTitle={error} />
  }

  const selectedEntry = data.candidates.find((c) => c.candidate_email === selectedEmail)

  return (
    <div style={{ padding: 24 }}>
      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)} style={{ marginBottom: 16 }}>
        {t('common.back', 'Back')}
      </Button>
      <Title level={3}>{t('codingChallenge.reviewTitle', 'Coding Challenge Review')}</Title>

      {data.candidates.length === 0 ? (
        <Empty description={t('codingChallenge.noCandidatesYet', 'No candidates have started this challenge yet')} />
      ) : (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Select
            value={selectedEmail}
            onChange={setSelectedEmail}
            style={{ width: 320 }}
            options={data.candidates.map((c) => ({
              value: c.candidate_email,
              label: `${c.candidate_email} (${c.submission?.status || 'not_submitted'})`,
            }))}
          />
          {selectedEntry && <CandidateDetail entry={selectedEntry} t={t} />}
        </Space>
      )}
    </div>
  )
}
