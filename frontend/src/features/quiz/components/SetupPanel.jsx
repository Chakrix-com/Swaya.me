import dayjs from 'dayjs';
import { Form, Input, DatePicker, InputNumber, Switch, Button, Tooltip, Alert, Space, theme } from 'antd';
import {
  SaveOutlined, ThunderboltOutlined, LoadingOutlined,
  WarningOutlined, CheckOutlined, InfoCircleOutlined,
} from '@ant-design/icons';
import { skins } from '../../../themes/skins';
import './SetupPanel.css';
import './GradingPanel.css'; // reuses .gp-row / .gp-section--accent-info for the Environment section

const { TextArea } = Input;

const REACTION_STYLES = [
  { id: null, emoji: '🚫', name: 'None', description: 'No reactions' },
  { id: 'thumbs', emoji: '👍', name: 'Thumbs', description: '👎 👍 👍👍', preview: ['👎', '👍', '👍👍'] },
  { id: 'hearts', emoji: '❤️', name: 'Hearts', description: '💔 ❤️ ❤️‍🔥', preview: ['💔', '❤️', '❤️‍🔥'] },
  { id: 'vibes', emoji: '🤩', name: 'Vibes', description: '😴 😐 😊 🤩', preview: ['😴', '😐', '😊', '🤩'] },
  { id: 'stars', emoji: '⭐', name: 'Stars', description: '⭐ 1-5 rating', preview: ['⭐'] },
];

function ReactionStylePicker({ value, onChange, disabled }) {
  return (
    <div className="sp-reaction-grid">
      {REACTION_STYLES.map((style) => {
        const isActive = (value ?? null) === style.id;
        return (
          <button
            key={style.id ?? 'none'}
            type="button"
            disabled={disabled}
            className={`sp-reaction-card${isActive ? ' sp-reaction-card--active' : ''}`}
            onClick={() => onChange(style.id)}
          >
            <span className="sp-reaction-card__emoji">{style.emoji}</span>
            <span className="sp-reaction-card__name">{style.name}</span>
            <span className="sp-reaction-card__desc">{style.description}</span>
            {isActive && <span className="sp-reaction-card__check"><CheckOutlined /></span>}
          </button>
        );
      })}
    </div>
  );
}

// Compact single-line skin picker for coding challenges — a native <select>
// styled with antd theme tokens (not antd's Select — banned for new UI here,
// see frontend/CLAUDE.md), matching the header's LanguageSwitcher pattern.
function SkinSelect({ value, onChange, disabled }) {
  const { token } = theme.useToken();
  const arrowSvg = `data:image/svg+xml,${encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="${token.colorPrimary}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>`
  )}`;
  return (
    <select
      value={value ?? 'default'}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value === 'default' ? null : e.target.value)}
      style={{
        boxSizing: 'border-box',
        width: 95,
        height: 30,
        lineHeight: '28px',
        borderRadius: token.borderRadius,
        border: `1px solid ${token.colorBorder}`,
        background: `${token.colorBgContainer} url("${arrowSvg}") no-repeat right 8px center / 10px`,
        color: token.colorText,
        padding: '0 26px 0 10px',
        fontFamily: 'inherit',
        fontSize: 13,
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.6 : 1,
        appearance: 'none',
        WebkitAppearance: 'none',
        MozAppearance: 'none',
      }}
    >
      {Object.values(skins).map((skin) => (
        <option key={skin.id} value={skin.id}>{skin.emoji} {skin.name}</option>
      ))}
    </select>
  );
}

function SkinCard({ value, onChange, disabled }) {
  return (
    <div className="sp-skin-grid">
      {Object.values(skins).map((skin) => {
        const isActive = (value ?? null) === (skin.id === 'default' ? null : skin.id);
        const gradient = `linear-gradient(90deg, ${skin.preview.join(', ')})`;
        return (
          <button
            key={skin.id}
            type="button"
            disabled={disabled}
            className={`sp-skin-card${isActive ? ' sp-skin-card--active' : ''}`}
            onClick={() => onChange(skin.id === 'default' ? null : skin.id)}
          >
            <div className="sp-skin-swatch" style={{ background: gradient }}>
              {isActive && <span className="sp-skin-check"><CheckOutlined /></span>}
            </div>
            <div className="sp-skin-meta">
              <span className="sp-skin-name">{skin.emoji} {skin.name}</span>
              <span className="sp-skin-desc">{skin.description}</span>
            </div>
          </button>
        );
      })}
    </div>
  );
}

export function SetupPanel({
  quiz,
  form,
  isExam,
  isPoll,
  isOfflinePoll,
  isCodingChallenge,
  isLiveMode,
  loading,
  mainRewriting,
  onSave,
  onUnpublish,
  onMainRewrite,
  onFinish,
  onAutoSave,
  titleInputRef,
  i18n,
  t,
}) {
  const handleFormBlur = (e) => {
    if (!onAutoSave || !isCodingChallenge) return
    if (e.currentTarget.contains(e.relatedTarget)) return
    onAutoSave(form.getFieldsValue(true))
  }
  const typeLabel = isCodingChallenge
    ? t('codingChallenge.questionTypeLabel', 'Coding Challenge')
    : isExam
      ? t('exam.typeLabel')
      : isOfflinePoll
        ? t('offlinePoll.typeLabel', 'Poll')
        : isPoll
          ? t('quiz.poll', 'Online Poll')
          : t('quiz.quizTypeLabel', 'Online Quiz');

  const typeColor = isCodingChallenge ? '#0284C7' : isExam ? '#059669' : isOfflinePoll ? '#DB2777' : isPoll ? '#EA580C' : '#4F46E5';

  const statusLabel = quiz?.status === 'ready'
    ? t('quiz.statusReady')
    : quiz?.status === 'archived'
      ? t('quiz.statusArchived')
      : t('quiz.statusDraft');

  const saveLabel = isCodingChallenge
    ? t('codingChallenge.saveButton', 'Save Challenge')
    : isExam
      ? t('exam.saveSettings')
      : isOfflinePoll
        ? t('offlinePoll.updateOfflinePoll', 'Update Offline Poll')
        : isPoll
          ? t('quiz.updatePoll')
          : t('quiz.editQuiz');

  return (
    <div className={`sp-wrap${isCodingChallenge ? ' sp-wrap--cc' : ''}`}>
      {/* ── Header — skipped for coding challenges: the rail nav already
           identifies this as "Challenge Setup", and status/type are visible
           in the page topbar, so repeating them here just costs vertical
           space. The Save/Unpublish actions live in the topbar too. ── */}
      {!isCodingChallenge && (
        <div className="sp-header">
          <div className="sp-header-left">
            <span className="sp-header-icon">⚙</span>
            <span className="sp-header-title">{t('quiz.setupLabel', 'Setup')}</span>
            {quiz && (
              <span className="sp-header-badges">
                <span className={`sp-badge sp-badge--status${quiz.status === 'ready' ? ' sp-badge--live' : ''}`}>
                  {statusLabel}
                </span>
                <span className="sp-badge" style={{ background: `${typeColor}15`, color: typeColor, borderColor: `${typeColor}40` }}>
                  {typeLabel}
                </span>
              </span>
            )}
          </div>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            loading={loading}
            disabled={isLiveMode}
            onClick={onSave}
          >
            {saveLabel}
          </Button>
        </div>
      )}

      {/* ── Live lock banner — for coding challenges this now lives inline
           in the page topbar instead, so nothing renders here. ── */}
      {isLiveMode && !isCodingChallenge && (
        <div className="sp-live-banner">
          <WarningOutlined className="sp-live-banner-icon" />
          <div className="sp-live-banner-text">
            <strong>{isExam ? t('quiz.unpublishToEditBannerTitleExam', '✏️ Unpublish to edit settings') : t('quiz.unpublishToEditBannerTitleQuiz', '✏️ Unpublish → Edit → Republish')}</strong>
            <span>{isExam ? t('quiz.unpublishToEditBannerDescExam', 'This test is live. Unpublish it to make changes, then republish when ready.') : t('quiz.unpublishToEditBannerDescQuiz', 'This activity is published and live. Unpublish it to edit settings, then republish when ready.')}</span>
          </div>
          <Button size="small" onClick={onUnpublish} loading={loading}>
            {isExam ? t('exam.unpublishExam') : isPoll ? t('quiz.unpublishPoll') : t('quiz.unpublishQuiz')}
          </Button>
        </div>
      )}

      <div onBlur={handleFormBlur}>
      <Form form={form} layout="vertical" onFinish={onFinish} disabled={isLiveMode}>
        <Form.Item name="quiz_type" hidden><Input /></Form.Item>

        {/* ── Basics ── */}
        <div className="sp-section">
          {!isCodingChallenge && <div className="sp-section-title">{t('quiz.basicsSection', 'Basics')}</div>}

          <Form.Item
            name="title"
            label={isCodingChallenge ? t('codingChallenge.titleLabelShort', 'Title') : isExam ? t('exam.examTitle') : isOfflinePoll ? t('offlinePoll.pollTitle', 'Offline Poll Title') : isPoll ? t('quiz.pollTitle') : t('quiz.quizTitle')}
            rules={[{ required: true, whitespace: true, message: isCodingChallenge ? t('codingChallenge.titleRequired', 'Please enter a title') : isExam ? t('exam.examTitleRequired') : isOfflinePoll ? t('offlinePoll.pollTitleRequired', 'Please enter a title') : isPoll ? t('quiz.pollTitleRequired') : t('quiz.quizTitleRequired') }]}
            style={{ marginBottom: 14 }}
          >
            <Input
              ref={titleInputRef}
              placeholder={isCodingChallenge ? t('codingChallenge.enterTitle', 'Enter coding challenge title') : isExam ? t('exam.enterExamTitle') : isOfflinePoll ? t('offlinePoll.enterPollTitle', 'Enter offline poll title') : isPoll ? t('quiz.enterPollTitle') : t('quiz.enterQuizTitle')}
              size="large"
              spellCheck="true"
              lang={i18n.language}
              suffix={(
                <Tooltip title={t('ai.rewriteWithAI')}>
                  <Button
                    type="text"
                    size="small"
                    icon={mainRewriting['title'] ? <LoadingOutlined spin /> : <ThunderboltOutlined />}
                    loading={mainRewriting['title']}
                    onClick={() => onMainRewrite('title', isCodingChallenge ? 'coding challenge title' : isExam ? 'exam title' : isPoll ? 'poll title' : 'quiz title')}
                  />
                </Tooltip>
              )}
            />
          </Form.Item>

          <Form.Item
            label={isCodingChallenge ? t('codingChallenge.descriptionLabel', 'Description') : isExam ? t('exam.examDescription') : isOfflinePoll ? t('offlinePoll.pollDescription', 'Description') : isPoll ? t('quiz.pollDescription') : t('quiz.quizDescription')}
            style={{ marginBottom: 0 }}
          >
            <div className={`sp-desc-wrap${isCodingChallenge ? ' sp-desc-wrap--cc' : ''}`}>
              {/* name must live on this inner, direct-child Form.Item — antd only
                  wires value/onChange into an immediate child, so nesting the real
                  control inside the wrapper div (as the outer Form.Item's child)
                  silently disconnects it from form state: it always renders empty
                  regardless of a saved value, and saving would wipe that value to
                  null. Found via the Grading tab reusing this exact pattern. */}
              <Form.Item name="description" noStyle>
                <TextArea
                  rows={isCodingChallenge ? 2 : 3}
                  placeholder={isCodingChallenge ? t('codingChallenge.enterDescription', 'Enter coding challenge description (optional)') : isExam ? t('exam.enterExamDescription') : isOfflinePoll ? t('offlinePoll.enterPollDescription', 'Enter offline poll description (optional)') : isPoll ? t('quiz.enterPollDescription') : t('quiz.enterQuizDescription')}
                  spellCheck="true"
                  lang={i18n.language}
                  style={isCodingChallenge ? { paddingRight: 32 } : undefined}
                />
              </Form.Item>
              <div className="sp-desc-ai">
                {isCodingChallenge ? (
                  <Tooltip title={t('ai.rewriteWithAI')}>
                    <Button
                      size="small"
                      type="text"
                      icon={mainRewriting['description'] ? <LoadingOutlined spin /> : <ThunderboltOutlined />}
                      loading={mainRewriting['description']}
                      onClick={() => onMainRewrite('description', 'coding challenge description')}
                    />
                  </Tooltip>
                ) : (
                  <Button
                    size="small"
                    type="text"
                    icon={mainRewriting['description'] ? <LoadingOutlined spin /> : <ThunderboltOutlined />}
                    loading={mainRewriting['description']}
                    onClick={() => onMainRewrite('description', isPoll ? 'poll description' : 'quiz description')}
                  >
                    {t('ai.rewrite')}
                  </Button>
                )}
              </div>
            </div>
          </Form.Item>
        </div>

        {/* ── Environment (coding challenge only) — repo/test command are how the
             candidate's workspace runs, not a grading judgment call, so they live
             here rather than on the Grading tab. ── */}
        {isCodingChallenge && (
          <div className="gp-section gp-section--accent-info" style={{ borderBottom: '1px solid var(--sw-border, #e5e7eb)' }}>
            <div className="gp-section-title">🔗 {t('codingChallenge.environmentSectionTitle', 'Environment')}</div>
            <div className="gp-row">
              <label className="gp-row-label">
                {t('codingChallenge.gitRepoUrl', 'Starter repo URL')}
                <span className="gp-row-hint">{t('codingChallenge.gitRepoUrlHelp', 'A public GitHub repo. The candidate\'s workspace clones it — the language is whatever this repo already is, never a candidate-facing choice.')}</span>
              </label>
              <Form.Item name="git_repo_url" noStyle rules={[{ required: true, message: t('codingChallenge.gitRepoUrlRequired', 'Please enter the starter repo URL') }]}>
                <Input className="gp-row-value" placeholder="https://github.com/your-org/starter-repo" />
              </Form.Item>
            </div>
            <div className="gp-row">
              <label className="gp-row-label">
                {t('codingChallenge.testCommand', 'Test command')}
                <span className="gp-row-hint">{t('codingChallenge.testCommandHelp', 'For Java repos, use a command that recompiles (e.g. "mvn test", not "mvn surefire:test") — otherwise a hidden test won\'t be picked up.')}</span>
              </label>
              <Form.Item name="test_command" noStyle>
                <Input className="gp-row-value" placeholder="pytest -q" />
              </Form.Item>
            </div>
          </div>
        )}

        {/* ── Time Limit (coding challenge only) ── */}
        {isCodingChallenge && (
          <div className="sp-section sp-section--inline">
            <span className="sp-section-label--inline">
              {t('codingChallenge.timeBudget', 'Time Limit (minutes)')}
              <Tooltip title={t('codingChallenge.timeBudgetHelp')}>
                <InfoCircleOutlined style={{ marginLeft: 6, color: 'var(--sw-text3, #999)', cursor: 'help' }} />
              </Tooltip>
            </span>
            <Form.Item name="time_budget_seconds" noStyle initialValue={120}>
              <InputNumber min={1} style={{ width: 95 }} />
            </Form.Item>
          </div>
        )}

        {/* ── Appearance ── */}
        {isCodingChallenge ? (
          <div className="sp-section sp-section--inline">
            <span className="sp-section-label sp-section-label--inline">{t('quiz.skinLabel', 'Participant skin')}</span>
            <Form.Item name="skin" noStyle>
              <SkinSelect disabled={isLiveMode} />
            </Form.Item>
          </div>
        ) : (
          <div className="sp-section">
            <div className="sp-section-title">{t('quiz.appearanceSection', 'Appearance')}</div>
            <div className="sp-section-label">{t('quiz.skinLabel', 'Participant skin')}</div>
            <Form.Item name="skin" noStyle>
              <SkinCard disabled={isLiveMode} t={t} />
            </Form.Item>
          </div>
        )}

        {/* ── Reactions (not for exam / coding challenge) ── */}
        {!isExam && !isCodingChallenge && (
          <div className="sp-section">
            <div className="sp-section-title">{t('quiz.reactionsSection', 'Participant Reactions')}</div>
            <div className="sp-section-label">{t('quiz.reactionsHint', 'Let participants react after the session ends')}</div>
            <Form.Item name="reaction_style" noStyle>
              <ReactionStylePicker disabled={isLiveMode} />
            </Form.Item>
          </div>
        )}

        {/* ── Behaviour (quiz / poll only — not exam/offline poll/coding challenge) ── */}
        {!isExam && !isOfflinePoll && !isCodingChallenge && (
          <div className="sp-section">
            <div className="sp-section-title">{t('quiz.behaviourSection', 'Behaviour')}</div>
            <Space direction="vertical" style={{ width: '100%' }} size={12}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ fontWeight: 500, fontSize: 13 }}>{t('quiz.shuffleQuestions', 'Shuffle questions')}</div>
                  <div style={{ fontSize: 12, color: 'var(--sw-text3)' }}>{t('quiz.shuffleQuestionsHint', 'Randomize question order for each participant')}</div>
                </div>
                <Form.Item name="shuffle_questions" valuePropName="checked" noStyle>
                  <Switch disabled={isLiveMode} />
                </Form.Item>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ fontWeight: 500, fontSize: 13 }}>{t('quiz.shuffleOptions', 'Shuffle answer options')}</div>
                  <div style={{ fontSize: 12, color: 'var(--sw-text3)' }}>{t('quiz.shuffleOptionsHint', 'Randomize MCQ option order for each participant')}</div>
                </div>
                <Form.Item name="shuffle_options" valuePropName="checked" noStyle>
                  <Switch disabled={isLiveMode} />
                </Form.Item>
              </div>
              <Form.Item
                name="default_question_time_seconds"
                label={t('quiz.defaultQuestionTime', 'Default time per question (seconds)')}
                extra={t('quiz.defaultQuestionTimeHint', 'Applied to questions with no individual time set. Leave blank for unlimited time.')}
                style={{ marginBottom: 0 }}
              >
                <InputNumber
                  min={5}
                  max={3600}
                  placeholder={t('quiz.unlimitedTime', '∞ unlimited')}
                  addonAfter="s"
                  style={{ width: 160 }}
                  disabled={isLiveMode}
                />
              </Form.Item>
            </Space>
          </div>
        )}

        {/* ── Schedule (exam / offline poll only) ── */}
        {(isExam || isOfflinePoll) && (
          <div className="sp-section">
            <div className="sp-section-title">{t('quiz.scheduleSection', 'Schedule')}</div>
            <div className="sp-inline-row">
              <Form.Item
                name={isOfflinePoll ? 'offline_start_at' : 'exam_start_at'}
                label={isOfflinePoll ? t('offlinePoll.startDate', 'Start Date & Time') : t('exam.startAt')}
                rules={[{ required: true, message: isOfflinePoll ? t('quiz.startDateRequired') : t('exam.startAtRequired') }]}
                style={{ marginBottom: 0, flex: '0 0 auto' }}
              >
                <DatePicker
                  showTime={{ format: 'HH:mm' }}
                  format="YYYY-MM-DD HH:mm"
                  style={{ width: 178 }}
                  disabledDate={(d) => d && d.isBefore(dayjs().startOf('day'))}
                />
              </Form.Item>
              <Form.Item
                name={isOfflinePoll ? 'offline_end_at' : 'exam_end_at'}
                label={isOfflinePoll ? t('offlinePoll.endDate', 'End Date & Time') : t('exam.endAt')}
                rules={[{ required: true, message: isOfflinePoll ? t('quiz.endDateRequired') : t('exam.endAtRequired') }]}
                style={{ marginBottom: 0, flex: '0 0 auto' }}
              >
                <DatePicker
                  showTime={{ format: 'HH:mm' }}
                  format="YYYY-MM-DD HH:mm"
                  style={{ width: 178 }}
                  disabledDate={(d) => {
                    if (!d) return false;
                    const startKey = isOfflinePoll ? 'offline_start_at' : 'exam_start_at';
                    const start = form.getFieldValue(startKey);
                    const floor = start ? start.startOf('day') : dayjs().startOf('day');
                    return d.isBefore(floor);
                  }}
                />
              </Form.Item>
              {isExam && (
                <Form.Item
                  name="exam_time_limit_minutes"
                  label={t('exam.timeLimitMinutes')}
                  style={{ marginBottom: 0, flex: '0 0 auto' }}
                >
                  <InputNumber min={1} max={600} placeholder={t('exam.timeLimitPlaceholder')} style={{ width: 110 }} addonAfter={t('quiz.minutes', 'min')} />
                </Form.Item>
              )}
              {isOfflinePoll && (
                <Form.Item
                  name="offline_results_email"
                  label={t('offlinePoll.resultsEmail', 'Email Results To (optional)')}
                  style={{ marginBottom: 0, flex: '1 1 180px' }}
                >
                  <Input type="email" placeholder={t('offlinePoll.resultsEmailPlaceholder')} />
                </Form.Item>
              )}
            </div>
          </div>
        )}

        {/* ── Access (exam only) ── */}
        {isExam && (
          <div className="sp-section">
            <div className="sp-section-title">{t('quiz.accessSection', 'Access')}</div>
            <div className="sp-inline-row sp-inline-row--align-end">
              <div className="sp-access-toggle-wrap">
                <span className="sp-section-label" style={{ marginBottom: 4 }}>{t('exam.requireEmailOn', 'Email verification')}</span>
                <Form.Item name="exam_require_email" valuePropName="checked" noStyle>
                  <Switch checkedChildren={t('exam.requireEmailOn')} unCheckedChildren={t('exam.requireEmailOff')} />
                </Form.Item>
              </div>
              <Form.Item noStyle shouldUpdate={(prev, cur) => prev.exam_require_email !== cur.exam_require_email}>
                {({ getFieldValue }) => getFieldValue('exam_require_email') ? (
                  <Form.Item
                    name="exam_allowed_domains"
                    label={t('exam.allowedDomains', 'Allowed email domains (optional)')}
                    extra={t('exam.allowedDomainsHint', 'Comma-separated domains, e.g. natwest.com, rbs.com — leave blank to allow any email')}
                    style={{ marginBottom: 0, flex: '1 1 240px' }}
                  >
                    <Input placeholder={t('exam.allowedDomainsPlaceholder')} />
                  </Form.Item>
                ) : (
                  <span className="sp-access-hint">{t('exam.requireEmailHint')}</span>
                )}
              </Form.Item>
            </div>
            <Form.Item
              name="exam_results_email"
              label={t('exam.resultsEmail', 'Email results to (optional)')}
              extra={t('exam.resultsEmailHint', 'A summary of exam results will be emailed here when the session ends')}
              style={{ marginTop: 12 }}
            >
              <Input type="email" placeholder={t('exam.resultsEmailPlaceholder', 'e.g. teacher@school.edu')} />
            </Form.Item>
          </div>
        )}

        {/* ── Save footer — coding challenges already have Save in the
             topbar, so skip the duplicate down here. ── */}
        {!isCodingChallenge && (
          <div className="sp-save-footer">
            <Button
              type="primary"
              size="large"
              icon={<SaveOutlined />}
              loading={loading}
              disabled={isLiveMode}
              onClick={onSave}
              block
            >
              {saveLabel}
            </Button>
          </div>
        )}
      </Form>
      </div>
    </div>
  );
}
