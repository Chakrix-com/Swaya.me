import { useState, useEffect } from 'react';
import { Form, Input, InputNumber, Button, Tooltip, Radio } from 'antd';
import { ThunderboltOutlined, LoadingOutlined } from '@ant-design/icons';
import './GradingPanel.css';

const RESULT_VISIBILITY_OPTIONS = [
  { value: 'hidden', labelKey: 'codingChallenge.resultVisibilityHidden', descKey: 'codingChallenge.resultVisibilityHiddenDesc' },
  { value: 'status_only', labelKey: 'codingChallenge.resultVisibilityStatusOnly', descKey: 'codingChallenge.resultVisibilityStatusOnlyDesc' },
  { value: 'full', labelKey: 'codingChallenge.resultVisibilityFull', descKey: 'codingChallenge.resultVisibilityFullDesc' },
]

const { TextArea } = Input;

const CRITERION_LABEL_KEYS = {
  functional_correctness: 'codingChallenge.critFunctionalCorrectness',
  ai_usage_efficiency: 'codingChallenge.critAiUsageEfficiency',
  prompt_quality: 'codingChallenge.critPromptQuality',
  validation_discipline: 'codingChallenge.critValidationDiscipline',
  code_quality: 'codingChallenge.critCodeQuality',
  architecture: 'codingChallenge.critArchitecture',
  time_taken: 'codingChallenge.critTimeTaken',
};

export function GradingPanel({
  question,
  form,
  isLiveMode,
  loading,
  mainRewriting,
  onFinish,
  onMainRewrite,
  criteria,
  defaults,
  t,
}) {
  const [hiddenTestOpen, setHiddenTestOpen] = useState(false);
  const watched = Form.useWatch([], form) || {};

  useEffect(() => {
    if (!question) return;
    const weights = question.grading_weights || defaults;
    const weightFields = {};
    criteria.forEach((c) => { weightFields[`weight_${c}`] = weights[c] ?? defaults[c]; });
    form.setFieldsValue({
      hidden_test_filename: question.hidden_test_filename || '',
      hidden_test_content: question.hidden_test_content || '',
      grading_rubric: question.grading_rubric || '',
      result_visibility: question.result_visibility || 'hidden',
      ...weightFields,
    });
    setHiddenTestOpen(!!(question.hidden_test_filename || question.hidden_test_content));
  }, [question]);

  const weightSum = criteria.reduce((sum, c) => sum + (Number(watched[`weight_${c}`]) || 0), 0);
  const weightValid = Math.abs(weightSum - 100) < 0.05;

  const resetWeights = () => {
    const weightFields = {};
    criteria.forEach((c) => { weightFields[`weight_${c}`] = defaults[c]; });
    form.setFieldsValue(weightFields);
  };

  return (
    <div className="gp-wrap">
      <Form form={form} layout="vertical" onFinish={onFinish} disabled={isLiveMode}>
        {/* ── Hidden Tests — verification the candidate never sees, used only for
             grading (repo URL / test command moved to Challenge Setup — they're
             environment config, not a grading judgment call). ── */}
        <div className="gp-section gp-section--accent-info">
          <div className="gp-section-title">🧪 {t('codingChallenge.hiddenTestSectionTitle', 'Hidden Tests')}</div>

          <button type="button" className="gp-toggle" onClick={() => setHiddenTestOpen((v) => !v)}>
            {hiddenTestOpen ? '▾' : '▸'} {t('codingChallenge.hiddenTestSection', 'Hidden test (optional, candidate never sees this)')}
          </button>
          {hiddenTestOpen && (
            <div className="gp-hidden-test">
              <div className="gp-row">
                <label className="gp-row-label">
                  {t('codingChallenge.hiddenTestFilename', 'File path (relative to the repo root)')}
                  <span className="gp-row-hint">{t('codingChallenge.hiddenTestFilenameHelp', 'Dropped into the candidate\'s workspace before grading and run alongside the test command — pick a path that won\'t collide with the starter repo\'s own files.')}</span>
                </label>
                <Form.Item name="hidden_test_filename" noStyle>
                  <Input className="gp-row-value" placeholder="test_hidden.py" />
                </Form.Item>
              </div>
              <Form.Item
                name="hidden_test_content"
                label={t('codingChallenge.hiddenTestContent', 'File content')}
                style={{ marginTop: 10, marginBottom: 0 }}
              >
                <TextArea rows={6} maxLength={20000} showCount style={{ fontFamily: 'monospace' }} />
              </Form.Item>
            </div>
          )}
        </div>

        {/* ── Grading Rubric ── */}
        <div className="gp-section">
          <div className="gp-section-title">🎯 {t('quiz.gradingRubric', 'Grading criteria')}</div>
          <Form.Item
            help={t('codingChallenge.gradingRubricHelp', 'What the AI judge should look for beyond passing tests — code quality, approach, etc.')}
            style={{ marginBottom: 14 }}
          >
            {/* name lives on this inner, direct-child Form.Item, not the outer one —
                see SetupPanel.jsx's Description field for why: antd only wires
                value/onChange into an immediate child, so wrapping the real control
                in a div breaks form-state binding silently (always renders empty,
                and saving wipes the real value to null). */}
            <div className="gp-desc-wrap">
              <Form.Item name="grading_rubric" noStyle>
                <TextArea rows={4} maxLength={5000} showCount style={{ paddingRight: 32 }} />
              </Form.Item>
              <div className="gp-desc-ai">
                <Tooltip title={t('ai.rewriteWithAI')}>
                  <Button
                    size="small"
                    type="text"
                    icon={mainRewriting['grading_rubric'] ? <LoadingOutlined spin /> : <ThunderboltOutlined />}
                    loading={mainRewriting['grading_rubric']}
                    onClick={() => onMainRewrite('grading_rubric', 'coding challenge grading rubric', form)}
                  />
                </Tooltip>
              </div>
            </div>
          </Form.Item>
        </div>

        {/* ── Result Visibility — what the candidate sees on their own session
             page once grading finishes. Always gated server-side on the
             submission actually reaching GRADED — a system failure never
             reveals anything to the candidate no matter what's picked here. ── */}
        <div className="gp-section gp-section--accent-info">
          <div className="gp-section-title">👁️ {t('codingChallenge.resultVisibilityTitle', 'Candidate Result Visibility')}</div>
          <p className="gp-weights-hint">
            {t('codingChallenge.resultVisibilityHint', 'How much of the graded result the candidate sees on their own page. A system grading failure never shows anything to the candidate, regardless of this setting.')}
          </p>
          <Form.Item name="result_visibility" noStyle>
            <Radio.Group optionType="button" buttonStyle="solid">
              {RESULT_VISIBILITY_OPTIONS.map((opt) => (
                <Radio.Button key={opt.value} value={opt.value}>{t(opt.labelKey)}</Radio.Button>
              ))}
            </Radio.Group>
          </Form.Item>
          <p className="gp-weights-hint" style={{ marginTop: 8, marginBottom: 0 }}>
            {t(RESULT_VISIBILITY_OPTIONS.find((o) => o.value === watched.result_visibility)?.descKey || RESULT_VISIBILITY_OPTIONS[0].descKey)}
          </p>
        </div>

        {/* ── Scoring Weights ── */}
        <div className="gp-section gp-section--accent-primary">
          <div className="gp-section-header">
            <div className="gp-section-title">⚖️ {t('codingChallenge.scoringWeightsTitle', 'Scoring Weights')}</div>
            <span className={`gp-weight-sum${weightValid ? ' gp-weight-sum--ok' : ' gp-weight-sum--bad'}`}>
              {weightValid ? `100% ✓` : t('codingChallenge.weightsTotal', 'Total: {{total}}%', { total: weightSum })}
            </span>
          </div>
          <p className="gp-weights-hint">
            {t('codingChallenge.weightsHint', 'These become the active grading weights once saved. Until then, this challenge uses the platform defaults (which include a fixed 5% for Proctoring Compliance).')}
          </p>
          {criteria.map((c) => (
            <div className="gp-row gp-row--weight" key={c}>
              <label className="gp-row-label">{t(CRITERION_LABEL_KEYS[c])}</label>
              <Form.Item name={`weight_${c}`} noStyle>
                <InputNumber className="gp-row-value gp-weight-input" min={0} max={100} precision={0} addonAfter="%" />
              </Form.Item>
            </div>
          ))}
          <button type="button" className="gp-reset-link" onClick={resetWeights}>
            {t('codingChallenge.resetWeights', 'Reset to defaults')}
          </button>
        </div>
      </Form>
    </div>
  );
}
