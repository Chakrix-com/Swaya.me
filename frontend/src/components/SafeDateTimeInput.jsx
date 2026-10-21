import dayjs from 'dayjs';
import { theme } from 'antd';

const NATIVE_FORMAT = 'YYYY-MM-DDTHH:mm';

// Native <input type="datetime-local"> as a drop-in for antd's
// <DatePicker showTime /> inside a Form.Item (value/onChange are dayjs | null).
//
// antd's DatePicker popup is driven by rc-trigger mouse coordination and
// previews hovered cells into the field — on the user's VDI that combination
// sets seemingly random dates/times. The browser's own picker has neither
// problem. See frontend/CLAUDE.md for the same reasoning applied to Dropdown/Select.
export function SafeDateTimeInput({ value, onChange, min, disabled, style, id, ...rest }) {
  const { token } = theme.useToken();
  const parsed = value ? dayjs(value) : null;
  const native = parsed && parsed.isValid() ? parsed.format(NATIVE_FORMAT) : '';

  return (
    <input
      type="datetime-local"
      id={id}
      step={60}
      value={native}
      min={min ? dayjs(min).format(NATIVE_FORMAT) : undefined}
      disabled={disabled}
      onChange={(e) => {
        const v = e.target.value;
        onChange?.(v ? dayjs(v) : null);
      }}
      style={{
        height: token.controlHeight,
        padding: `0 ${token.paddingSM}px`,
        fontSize: token.fontSize,
        fontFamily: 'inherit',
        color: token.colorText,
        background: disabled ? token.colorBgContainerDisabled : token.colorBgContainer,
        border: `1px solid ${token.colorBorder}`,
        borderRadius: token.borderRadius,
        boxSizing: 'border-box',
        colorScheme: 'inherit',
        ...style,
      }}
      {...rest}
    />
  );
}
