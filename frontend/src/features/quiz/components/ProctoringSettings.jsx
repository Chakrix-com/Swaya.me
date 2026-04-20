import { useState, useEffect } from 'react';
import {
  Card, Switch, Form, InputNumber, Space, Alert,
  Divider, Typography, Tag, Button, message, Tooltip,
} from 'antd';
import { LockOutlined, CameraOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { quizAPI, proctoringAPI } from '../../../services/api';
import { useTranslation } from 'react-i18next';

const { Text, Title } = Typography;

const TIER_ORDER = { free: 0, basic: 1, pro: 2, enterprise: 3 };

function tierGte(tenantTier, ruleTier) {
  return (TIER_ORDER[tenantTier] || 0) >= (TIER_ORDER[ruleTier] || 0);
}

const PRESET_LEVELS = {
  soft: ['fullscreen_enforce', 'tab_switch_detect', 'right_click_block'],
  hard: ['fullscreen_enforce', 'tab_switch_detect', 'right_click_block', 'copy_paste_block', 'multi_tab_detect', 'bot_signal_detect', 'honeypot_traps'],
  paranoid: null, // all rules
};

export function ProctoringSettings({ quizId, quizType, tenantTier, currentPolicy, onSaved }) {
  const { t } = useTranslation();
  const [policy, setPolicy] = useState(currentPolicy || { enabled: false, rules: {}, escalation: { lock_on_violation_count: 3, auto_submit_on_lock: false } });
  const [saving, setSaving] = useState(false);
  const [platformRules, setPlatformRules] = useState([]);

  useEffect(() => {
    if (currentPolicy) setPolicy(currentPolicy);
  }, [currentPolicy]);

  useEffect(() => {
    // Use the user-tier-filtered endpoint (not super-admin-only)
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

  const handleSave = async () => {
    setSaving(true);
    try {
      await quizAPI.update(quizId, { proctoring_policy: policy });
      message.success('Proctoring settings saved');
      onSaved?.(policy);
    } catch (e) {
      message.error('Failed to save proctoring settings');
    } finally {
      setSaving(false);
    }
  };

  const toggleRule = (ruleId, enabled) => {
    setPolicy((p) => ({
      ...p,
      rules: { ...p.rules, [ruleId]: { ...(p.rules?.[ruleId] || {}), enabled } },
    }));
  };

  const isRuleEnabled = (ruleId) => {
    return policy.rules?.[ruleId]?.enabled !== false;
  };

  const applyPreset = (level) => {
    const allowed = PRESET_LEVELS[level];
    const newRules = {};
    applicableRules.forEach((r) => {
      newRules[r.rule_id] = { enabled: allowed === null || allowed.includes(r.rule_id) };
    });
    setPolicy((p) => ({ ...p, rules: newRules }));
  };

  if (!isExamOrPoll && quizType) {
    return (
      <Card style={{ marginTop: 24 }}>
        <Alert
          message="Proctoring is available for Exam and Offline Poll types only."
          type="info"
          showIcon
          icon={<LockOutlined />}
        />
      </Card>
    );
  }

  return (
    <Card
      title={<Space><LockOutlined /> Proctoring Settings</Space>}
      style={{ marginTop: 24 }}
      extra={
        <Button type="primary" onClick={handleSave} loading={saving}>
          Save Proctoring Settings
        </Button>
      }
    >
      <Form layout="vertical">
        <Form.Item label={<Text strong>Enable Proctoring</Text>}>
          <Switch
            checked={policy.enabled}
            onChange={(v) => setPolicy((p) => ({ ...p, enabled: v }))}
          />
          <Text type="secondary" style={{ marginLeft: 12 }}>
            When disabled, no rules are active and participants have zero overhead.
          </Text>
        </Form.Item>

        {policy.enabled && (
          <>
            <Divider />
            <Form.Item label={<Text strong>Preset Level</Text>}>
              <Space>
                <Button size="small" onClick={() => applyPreset('soft')}>Soft</Button>
                <Button size="small" onClick={() => applyPreset('hard')}>Hard</Button>
                <Button size="small" onClick={() => applyPreset('paranoid')}>Paranoid</Button>
              </Space>
              <Text type="secondary" style={{ marginLeft: 12, fontSize: 12 }}>
                Soft = fullscreen + tab detection. Hard = all free rules. Paranoid = all available rules.
              </Text>
            </Form.Item>

            <Divider />
            <Title level={5}>Active Rules</Title>

            {applicableRules.length === 0 && (
              <Alert message="No rules available for your plan." type="warning" showIcon />
            )}

            {applicableRules.map((rule) => (
              <Form.Item
                key={rule.rule_id}
                label={
                  <Space>
                    <Text>{rule.display_name}</Text>
                    <Tag color={rule.severity === 'lock' ? 'red' : 'orange'}>
                      {rule.severity}
                    </Tag>
                    <Tag color="blue">{rule.tier_minimum}</Tag>
                    {rule.is_silent && (
                      <Tooltip title="Silent — participant does not see a warning">
                        <Tag color="default">silent</Tag>
                      </Tooltip>
                    )}
                  </Space>
                }
              >
                <Switch
                  checked={isRuleEnabled(rule.rule_id)}
                  onChange={(v) => toggleRule(rule.rule_id, v)}
                />
                {rule.description && (
                  <Text type="secondary" style={{ marginLeft: 12, fontSize: 12 }}>
                    {rule.description}
                  </Text>
                )}
              </Form.Item>
            ))}

            <Divider />
            <Title level={5}>Escalation Settings</Title>

            <Form.Item label="Lock session after N violations">
              <InputNumber
                min={1}
                max={20}
                value={policy.escalation?.lock_on_violation_count ?? 3}
                onChange={(v) =>
                  setPolicy((p) => ({
                    ...p,
                    escalation: { ...(p.escalation || {}), lock_on_violation_count: v },
                  }))
                }
              />
            </Form.Item>

            <Form.Item label="Auto-submit answers when session is locked">
              <Switch
                checked={policy.escalation?.auto_submit_on_lock || false}
                onChange={(v) =>
                  setPolicy((p) => ({
                    ...p,
                    escalation: { ...(p.escalation || {}), auto_submit_on_lock: v },
                  }))
                }
              />
            </Form.Item>

            {isRuleEnabled('webcam_monitoring') && applicableRules.some(r => r.rule_id === 'webcam_monitoring') && (
              <>
                <Divider />
                <Alert
                  message={<Space><CameraOutlined /> Webcam is enabled — participants who deny camera access cannot start this exam.</Space>}
                  type="warning"
                  showIcon={false}
                />
              </>
            )}
          </>
        )}
      </Form>
    </Card>
  );
}
