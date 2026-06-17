import { useState, useEffect } from 'react';
import { Switch, InputNumber, Tag, Tooltip, Alert, Space, Button } from 'antd';
import { LockOutlined, CameraOutlined, ThunderboltOutlined, SafetyOutlined, FireOutlined, SaveOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import './ProctoringSettings.css';

const TIER_ORDER = { free: 0, basic: 1, pro: 2, enterprise: 3 };

function tierGte(tenantTier, ruleTier) {
  return (TIER_ORDER[tenantTier] || 0) >= (TIER_ORDER[ruleTier] || 0);
}

const PRESET_LEVELS = {
  light: ['fullscreen_enforce', 'tab_switch_detect', 'right_click_block'],
  standard: ['fullscreen_enforce', 'tab_switch_detect', 'right_click_block', 'copy_paste_block', 'multi_tab_detect', 'bot_signal_detect', 'honeypot_traps'],
  maximum: null,
};

const PRESET_META = {
  light:    { icon: <ThunderboltOutlined />, colorClass: 'ps-preset-card--light' },
  standard: { icon: <SafetyOutlined />,      colorClass: 'ps-preset-card--standard' },
  maximum:  { icon: <FireOutlined />,        colorClass: 'ps-preset-card--maximum' },
};

export function ProctoringSettings({ quizId, quizType, tenantTier, currentPolicy, onChange, onSave, saving }) {
  const { t } = useTranslation();
  const [policy, setPolicy] = useState(
    currentPolicy || { enabled: false, rules: {}, escalation: { lock_on_violation_count: 3, auto_submit_on_lock: false } }
  );
  const [platformRules, setPlatformRules] = useState([]);

  useEffect(() => {
    if (currentPolicy) setPolicy(currentPolicy);
  }, [currentPolicy]);

  useEffect(() => {
    import('../../../services/api').then(({ default: api }) => {
      api.get('/proctoring/rules').then((res) => setPlatformRules(res.data)).catch(() => {});
    });
  }, []);

  const applicableRules = platformRules.filter((r) => {
    if (!tierGte(tenantTier || 'free', r.tier_minimum)) return false;
    const qt = quizType || 'quiz';
    const applies = r.applies_to?.quiz_types || [];
    return applies.includes(qt) || applies.includes('all');
  });

  const isExamOrPoll = quizType === 'exam' || quizType === 'offline_poll';

  const updatePolicy = (newPolicy) => {
    setPolicy(newPolicy);
    onChange?.(newPolicy);
  };

  const toggleRule = (ruleId, enabled) => {
    updatePolicy({
      ...policy,
      rules: { ...policy.rules, [ruleId]: { ...(policy.rules?.[ruleId] || {}), enabled } },
    });
  };

  const isRuleEnabled = (ruleId) => policy.rules?.[ruleId]?.enabled !== false;

  const applyPreset = (level) => {
    const allowed = PRESET_LEVELS[level];
    const newRules = {};
    applicableRules.forEach((r) => {
      newRules[r.rule_id] = { enabled: allowed === null || allowed.includes(r.rule_id) };
    });
    updatePolicy({ ...policy, rules: newRules });
  };

  const activePreset = (() => {
    if (!applicableRules.length) return null;
    for (const level of ['light', 'standard', 'maximum']) {
      const allowed = PRESET_LEVELS[level];
      const matches = applicableRules.every((r) => {
        const enabled = isRuleEnabled(r.rule_id);
        const inSet = allowed === null || allowed.includes(r.rule_id);
        return enabled === inSet;
      });
      if (matches) return level;
    }
    return null;
  })();

  if (!isExamOrPoll && quizType) {
    return (
      <div className="ps-wrap">
        <div className="ps-header">
          <div className="ps-header-left">
            <span className="ps-header-icon"><LockOutlined /></span>
            <div>
              <div className="ps-header-title">{t('proctoring.settings.title')}</div>
            </div>
          </div>
        </div>
        <div className="ps-exam-only-notice">
          <LockOutlined style={{ marginRight: 8, opacity: 0.5 }} />
          {t('proctoring.settings.examOnly')}
        </div>
      </div>
    );
  }

  const lockAt = policy.escalation?.lock_on_violation_count ?? 3;
  const warnings = lockAt - 1;

  const leftRules = applicableRules.filter((_, i) => i % 2 === 0);
  const rightRules = applicableRules.filter((_, i) => i % 2 === 1);

  return (
    <div className="ps-wrap">
      {/* ── Header / Master Toggle ── */}
      <div className={`ps-header${policy.enabled ? ' ps-header--on' : ''}`}>
        <div className="ps-header-left">
          <span className="ps-header-icon"><LockOutlined /></span>
          <div>
            <div className="ps-header-title">{t('proctoring.settings.title')}</div>
            <div className="ps-header-hint">
              {policy.enabled
                ? t('proctoring.settings.enabledHint', 'Monitoring is active for this exam.')
                : t('proctoring.settings.enableHint')}
            </div>
          </div>
        </div>
        <div className="ps-header-right">
          <span className="ps-toggle-label">{policy.enabled ? t('common.on', 'ON') : t('common.off', 'OFF')}</span>
          <Switch
            checked={policy.enabled}
            onChange={(v) => updatePolicy({ ...policy, enabled: v })}
          />
          {onSave && (
            <Button
              type="primary"
              icon={<SaveOutlined />}
              loading={saving}
              onClick={onSave}
              size="small"
            >
              {t('common.save', 'Save')}
            </Button>
          )}
        </div>
      </div>

      {policy.enabled && (
        <>
          {/* ── Quick Setup Presets ── */}
          <div className="ps-section">
            <div className="ps-section-title">{t('proctoring.settings.presetLabel')}</div>
            <div className="ps-presets">
              {(['light', 'standard', 'maximum']).map((level) => {
                const meta = PRESET_META[level];
                const isActive = activePreset === level;
                return (
                  <button
                    key={level}
                    type="button"
                    className={`ps-preset-card ${meta.colorClass}${isActive ? ' ps-preset-card--active' : ''}`}
                    onClick={() => applyPreset(level)}
                  >
                    <span className="ps-preset-icon">{meta.icon}</span>
                    <span className="ps-preset-name">{t(`proctoring.preset.${level}`)}</span>
                    <span className="ps-preset-desc">{t(`proctoring.preset.${level}Desc`)}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* ── Monitoring Rules (2-col grid) ── */}
          <div className="ps-section">
            <div className="ps-section-title">{t('proctoring.settings.rulesTitle')}</div>

            {applicableRules.length === 0 ? (
              <div className="ps-no-rules">{t('proctoring.settings.noRules')}</div>
            ) : (
              <div className="ps-rules-grid">
                {[leftRules, rightRules].map((col, ci) => (
                  <div key={ci} className="ps-rules-col">
                    {col.map((rule) => (
                      <div key={rule.rule_id} className="ps-rule-row">
                        <div className="ps-rule-info">
                          <span className="ps-rule-name">{rule.display_name}</span>
                          <span className="ps-rule-badges">
                            <Tag
                              color={rule.severity === 'lock' ? 'red' : 'orange'}
                              style={{ fontSize: 10, padding: '0 5px', marginRight: 0 }}
                            >
                              {rule.severity === 'lock'
                                ? t('proctoring.settings.severityLock')
                                : t('proctoring.settings.severityWarn')}
                            </Tag>
                            {rule.tier_minimum !== 'free' && (
                              <Tag color="blue" style={{ fontSize: 10, padding: '0 5px', marginRight: 0 }}>
                                {rule.tier_minimum}
                              </Tag>
                            )}
                            {rule.is_silent && (
                              <Tooltip title={t('proctoring.settings.silentHint')}>
                                <Tag style={{ fontSize: 10, padding: '0 5px', marginRight: 0 }}>
                                  {t('proctoring.settings.silent')}
                                </Tag>
                              </Tooltip>
                            )}
                          </span>
                          {rule.description && (
                            <span className="ps-rule-desc">{rule.description}</span>
                          )}
                        </div>
                        <Switch
                          checked={isRuleEnabled(rule.rule_id)}
                          onChange={(v) => toggleRule(rule.rule_id, v)}
                          size="small"
                        />
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* ── Escalation ── */}
          <div className="ps-section">
            <div className="ps-section-title">{t('proctoring.settings.escalationTitle')}</div>
            <div className="ps-escalation">
              <div className="ps-escalation-controls">
                <span className="ps-esc-label ps-esc-label--inline">
                  {t('proctoring.escalation.lockLabel').split('___').map((part, i, arr) => (
                    i < arr.length - 1 ? (
                      <span key={i}>
                        {part}
                        <InputNumber
                          min={1}
                          max={20}
                          value={lockAt}
                          size="small"
                          style={{ width: 56, margin: '0 4px' }}
                          onChange={(v) =>
                            updatePolicy({ ...policy, escalation: { ...(policy.escalation || {}), lock_on_violation_count: v } })
                          }
                        />
                      </span>
                    ) : <span key={i}>{part}</span>
                  ))}
                </span>
                <label className="ps-esc-label">
                  <span className="ps-esc-label-text">{t('proctoring.escalation.autoSubmitLabel')}</span>
                  <Switch
                    checked={policy.escalation?.auto_submit_on_lock || false}
                    size="small"
                    onChange={(v) =>
                      updatePolicy({ ...policy, escalation: { ...(policy.escalation || {}), auto_submit_on_lock: v } })
                    }
                  />
                </label>
              </div>
              <div className="ps-esc-summary">
                {t('proctoring.escalation.summary', { warnings, lockAt })}
                {' — '}
                {policy.escalation?.auto_submit_on_lock
                  ? t('proctoring.escalation.autoSubmitOn')
                  : t('proctoring.escalation.autoSubmitOff')}
              </div>
            </div>
          </div>

          {/* ── Webcam notice ── */}
          {isRuleEnabled('webcam_monitoring') && applicableRules.some(r => r.rule_id === 'webcam_monitoring') && (
            <div className="ps-section ps-section--last">
              <Alert
                message={<Space><CameraOutlined /> {t('proctoring.settings.webcamNotice')}</Space>}
                type="warning"
                showIcon={false}
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}
