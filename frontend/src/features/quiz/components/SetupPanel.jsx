import dayjs from 'dayjs';
import { Form, Input, DatePicker, InputNumber, Switch, Button, Tooltip, Alert } from 'antd';
import {
  SaveOutlined, ThunderboltOutlined, LoadingOutlined,
  WarningOutlined, CheckOutlined,
} from '@ant-design/icons';
import { skins } from '../../../themes/skins';
import './SetupPanel.css';

const { TextArea } = Input;

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
  isLiveMode,
  loading,
  mainRewriting,
  onSave,
  onUnpublish,
  onMainRewrite,
  onFinish,
  i18n,
  t,
}) {
  const typeLabel = isExam
    ? t('exam.typeLabel')
    : isOfflinePoll
      ? t('offlinePoll.typeLabel', 'Poll')
      : isPoll
        ? t('quiz.poll', 'Online Poll')
        : t('quiz.quizTypeLabel', 'Online Quiz');

  const typeColor = isExam ? '#059669' : isOfflinePoll ? '#DB2777' : isPoll ? '#EA580C' : '#4F46E5';

  const statusLabel = quiz?.status === 'ready'
    ? t('quiz.statusReady')
    : quiz?.status === 'archived'
      ? t('quiz.statusArchived')
      : t('quiz.statusDraft');

  const saveLabel = isExam
    ? t('exam.saveSettings')
    : isOfflinePoll
      ? t('offlinePoll.updateOfflinePoll', 'Update Offline Poll')
      : isPoll
        ? t('quiz.updatePoll')
        : t('quiz.editQuiz');

  return (
    <div className="sp-wrap">
      {/* ── Header ── */}
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

      {/* ── Live lock banner ── */}
      {isLiveMode && (
        <div className="sp-live-banner">
          <WarningOutlined className="sp-live-banner-icon" />
          <div className="sp-live-banner-text">
            <strong>{t('quiz.unpublishToEditBannerTitle', isExam ? '✏️ Unpublish to edit settings' : '✏️ Unpublish → Edit → Republish')}</strong>
            <span>{t('quiz.unpublishToEditBannerDesc', isExam ? 'This test is live. Unpublish it to make changes, then republish when ready.' : 'This activity is published and live. Unpublish it to edit settings, then republish when ready.')}</span>
          </div>
          <Button size="small" onClick={onUnpublish} loading={loading}>
            {isExam ? t('exam.unpublishExam') : isPoll ? t('quiz.unpublishPoll') : t('quiz.unpublishQuiz')}
          </Button>
        </div>
      )}

      <Form form={form} layout="vertical" onFinish={onFinish} disabled={isLiveMode}>
        <Form.Item name="quiz_type" hidden><Input /></Form.Item>

        {/* ── Basics ── */}
        <div className="sp-section">
          <div className="sp-section-title">{t('quiz.basicsSection', 'Basics')}</div>

          <Form.Item
            name="title"
            label={isExam ? t('exam.examTitle') : isOfflinePoll ? t('offlinePoll.pollTitle', 'Offline Poll Title') : isPoll ? t('quiz.pollTitle') : t('quiz.quizTitle')}
            rules={[{ required: true, message: isExam ? t('exam.examTitleRequired') : isOfflinePoll ? t('offlinePoll.pollTitleRequired', 'Please enter a title') : isPoll ? t('quiz.pollTitleRequired') : t('quiz.quizTitleRequired') }]}
            style={{ marginBottom: 14 }}
          >
            <Input
              placeholder={isExam ? t('exam.enterExamTitle') : isOfflinePoll ? t('offlinePoll.enterPollTitle', 'Enter offline poll title') : isPoll ? t('quiz.enterPollTitle') : t('quiz.enterQuizTitle')}
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
                    onClick={() => onMainRewrite('title', isExam ? 'exam title' : isPoll ? 'poll title' : 'quiz title')}
                  />
                </Tooltip>
              )}
            />
          </Form.Item>

          <Form.Item
            name="description"
            label={isExam ? t('exam.examDescription') : isOfflinePoll ? t('offlinePoll.pollDescription', 'Description') : isPoll ? t('quiz.pollDescription') : t('quiz.quizDescription')}
            style={{ marginBottom: 0 }}
          >
            <div className="sp-desc-wrap">
              <TextArea
                rows={3}
                placeholder={isExam ? t('exam.enterExamDescription') : isOfflinePoll ? t('offlinePoll.enterPollDescription', 'Enter offline poll description (optional)') : isPoll ? t('quiz.enterPollDescription') : t('quiz.enterQuizDescription')}
                spellCheck="true"
                lang={i18n.language}
              />
              <div className="sp-desc-ai">
                <Button
                  size="small"
                  type="text"
                  icon={mainRewriting['description'] ? <LoadingOutlined spin /> : <ThunderboltOutlined />}
                  loading={mainRewriting['description']}
                  onClick={() => onMainRewrite('description', isPoll ? 'poll description' : 'quiz description')}
                >
                  {t('ai.rewrite')}
                </Button>
              </div>
            </div>
          </Form.Item>
        </div>

        {/* ── Appearance ── */}
        <div className="sp-section">
          <div className="sp-section-title">{t('quiz.appearanceSection', 'Appearance')}</div>
          <div className="sp-section-label">{t('quiz.skinLabel', 'Participant skin')}</div>
          <Form.Item name="skin" noStyle>
            <SkinCard disabled={isLiveMode} t={t} />
          </Form.Item>
        </div>

        {/* ── Schedule (exam / offline poll only) ── */}
        {(isExam || isOfflinePoll) && (
          <div className="sp-section">
            <div className="sp-section-title">{t('quiz.scheduleSection', 'Schedule')}</div>
            <div className="sp-inline-row">
              <Form.Item
                name={isOfflinePoll ? 'offline_start_at' : 'exam_start_at'}
                label={isOfflinePoll ? t('offlinePoll.startDate', 'Start Date & Time') : t('exam.startAt')}
                rules={[{ required: true, message: isOfflinePoll ? t('quiz.startDateRequired') : t('exam.startAtRequired') }]}
                style={{ marginBottom: 0, flex: '1 1 180px' }}
              >
                <DatePicker
                  showTime={{ format: 'HH:mm' }}
                  format="YYYY-MM-DD HH:mm"
                  style={{ width: '100%' }}
                  disabledDate={(d) => d && d.isBefore(dayjs().startOf('day'))}
                />
              </Form.Item>
              <Form.Item
                name={isOfflinePoll ? 'offline_end_at' : 'exam_end_at'}
                label={isOfflinePoll ? t('offlinePoll.endDate', 'End Date & Time') : t('exam.endAt')}
                rules={[{ required: true, message: isOfflinePoll ? t('quiz.endDateRequired') : t('exam.endAtRequired') }]}
                style={{ marginBottom: 0, flex: '1 1 180px' }}
              >
                <DatePicker
                  showTime={{ format: 'HH:mm' }}
                  format="YYYY-MM-DD HH:mm"
                  style={{ width: '100%' }}
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
          </div>
        )}

        {/* ── Save footer ── */}
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
      </Form>
    </div>
  );
}
