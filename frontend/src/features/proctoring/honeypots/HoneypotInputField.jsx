export function HoneypotInputField({ config, reportViolation }) {
  const fieldName = config?.hidden_field_name || 'confirm_trap';
  return (
    <input
      type="text"
      name={fieldName}
      style={{ display: 'none' }}
      tabIndex={-1}
      autoComplete="off"
      onChange={(e) => {
        if (e.target.value) {
          reportViolation('honeypot_traps', 'HONEYPOT_FIELD_FILLED', { field: fieldName });
        }
      }}
    />
  );
}
