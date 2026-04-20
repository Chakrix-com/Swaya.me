import { useState, useEffect } from 'react';
import {
  Card, Switch, Form, InputNumber, Space, Alert,
  Divider, Typography, Tag, Tooltip,
} from 'antd';
import { LockOutlined, CameraOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const { Text, Title } = Typography;

const TIER_ORDER = { free: 0, basic: 1, pro: 2, enterprise: 3 };

function tierGte(tenantTier, ruleTier) {
  return (TIER_ORDER[tenantTier] || 0) >= (TIER_ORDER[ruleTier] || 0);
}

const PRESET_LEVELS = {
  light: ['fullscreen_enforce', 'tab_switch_detect', 'right_click_block'],
  standard: ['fullscreen_enforce', 'tab_switch_detect', 'right_click_block', 'copy_paste_block', 'multi_tab_detect', 'bot_signal_detect', 'honeypot_traps'],
  maximum: null, // all rules
};

export function ProctoringSettings({ quizId, quizType, tenantTier, currentPolicy, onChange }) {
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

  if (!isExamOrPoll && quizType) {
    return (
      <Card style={{ marginTop: 16 }}>
        <Alert
          message={t('proctoring.settings.examOnly')}
          type="info"
          showIcon
          icon={<LockOutlined />}
        />
      </Card>
    );
  }

  const lockAt = policy.escalation?.lock_on_violation_count ?? 3;
  const warnings = lockAt - 1;

  return (
    <Card
      title={<Space><LockOutlined /> {t('proctoring.settings.title')}</Space>}
      style={{ marginTop: 16 }}
    >
      <Form layout="vertical">
        <Form.Item
          label={<Text strong>{t('proctoring.settings.enableLabel')}</Text>}
          extra={<Text type="secondary">{t('proctoring.settings.enableHint')}</Text>}
        >
          <Switch
            checked={policy.enabled}
            onChange={(v) => updatePolicy({ ...policy, enabled: v })}
          />
        </Form.Item>

        {policy.enabled && (
          <>
            <Divider />
            <Form.Item
              label={<Text strong>{t('proctoring.settings.presetLabel')}</Text>}
            >
              <Space wrap>
                <div
                  onClick={() => applyPreset('light')}
                  style={{ cursor: 'pointer', border: '1px solid #d9d9d9', borderRadius: 6, padding: '8px 14px', minWidth: 160, background: '#fafafa' }}
                >
                  <Text strong style={{ display: 'block' }}>{t('proctoring.preset.light')}</Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>{t('proctoring.preset.lightDesc')}</Text>
                </div>
                <div
                  onClick={() => applyPreset('standard')}
                  style={{ cursor: 'pointer', border: '1px solid #d9d9d9', borderRadius: 6, padding: '8px 14px', minWidth: 160, background: '#fafafa' }}
                >
                  <Text strong style={{ display: 'block' }}>{t('proctoring.preset.standard')}</Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>{t('proctoring.preset.standardDesc')}</Text>
                </div>
                <div
                  onClick={() => applyPreset('maximum')}
                  style={{ cursor: 'pointer', border: '1px solid #d9d9d9', borderRadius: 6, padding: '8px 14px', minWidth: 160, background: '#fafafa' }}
                >
                  <Text strong style={{ display: 'block' }}>{t('proctoring.preset.maximum')}</Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>{t('proctoring.preset.maximumDesc')}</Text>
                </div>
              </Space>
            </Form.Item>

            <Divider />
            <Title level={5}>{t('proctoring.settings.rulesTitle')}</Title>

            {applicableRules.length === 0 && (
              <Alert message={t('proctoring.settings.noRules')} type="warning" showIcon />
            )}

            {applicableRules.map((rule) => (
              <Form.Item
                key={rule.rule_id}
                label={
                  <Space>
                    <Text>{rule.display_name}</Text>
                    <Tag color={rule.severity === 'lock' ? 'red' : 'orange'}>
                      {rule.severity === 'lock' ? t('proctoring.settings.severityLock') : t('proctoring.settings.severityWarn')}
                    </Tag>
                    {rule.tier_minimum !== 'free' && (
                      <Tag color="blue">{rule.tier_minimum}</Tag>
                    )}
                    {rule.is_silent && (
                      <Tooltip title={t('proctoring.settings.silentHint')}>
                        <Tag color="default">{t('proctoring.settings.silent')}</Tag>
                      </Tooltip>
                    )}
                  </Space>
                }
                extra={rule.description && (
                  <Text type="secondary" style={{ fontSize: 12 }}>{rule.description}</Text>
                )}
              >
                <Switch
                  checked={isRuleEnabled(rule.rule_id)}
                  onChange={(v) => toggleRule(rule.rule_id, v)}
                />
              </Form.Item>
            ))}

            <Divider />
            <Title level={5}>{t('proctoring.settings.escalationTitle')}</Title>

            <Form.Item
              label={t('proctoring.escalation.lockLabel')}
              extra={<Text type="secondary" style={{ fontSize: 12 }}>{t('proctoring.escalation.lockHint', { warnings, lockAt })}</Text>}
            >
              <InputNumber
                min={1}
                max={20}
                value={lockAt}
                onChange={(v) =>
                  updatePolicy({ ...policy, escalation: { ...(policy.escalation || {}), lock_on_violation_count: v } })
                }
              />
            </Form.Item>

            <Form.Item
              label={t('proctoring.escalation.autoSubmitLabel')}
              extra={<Text type="secondary" style={{ fontSize: 12 }}>{t('proctoring.escalation.autoSubmitHint')}</Text>}
            >
              <Switch
                checked={policy.escalation?.auto_submit_on_lock || false}
                onChange={(v) =>
                  updatePolicy({ ...policy, escalation: { ...(policy.escalation || {}), auto_submit_on_lock: v } })
                }
              />
            </Form.Item>

            <Alert
              type="info"
              showIcon
              message={t('proctoring.escalation.summary', { warnings, lockAt })}
              description={policy.escalation?.auto_submit_on_lock
                ? t('proctoring.escalation.autoSubmitOn')
                : t('proctoring.escalation.autoSubmitOff')}
              style={{ marginTop: 4 }}
            />

            {isRuleEnabled('webcam_monitoring') && applicableRules.some(r => r.rule_id === 'webcam_monitoring') && (
              <Alert
                message={<Space><CameraOutlined /> {t('proctoring.settings.webcamNotice')}</Space>}
                type="warning"
                showIcon={false}
                style={{ marginTop: 12 }}
              />
            )}
          </>
        )}
      </Form>
    </Card>
  );
}
