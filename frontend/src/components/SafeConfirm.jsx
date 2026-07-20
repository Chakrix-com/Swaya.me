import SafeModal from './SafeModal'

// Popconfirm replacement — same rc-component/trigger lineage as the
// confirmed-broken Dropdown/Select/click-Popover bug (see frontend/CLAUDE.md).
// Never confirmed broken itself, but built on SafeModal precautionarily so
// destructive-action confirms don't depend on rc-trigger either. Reused by
// MoreActionsMenu's `confirm:` items and by the imperative
// Modal.confirm-replacement call sites (see SafeModal.jsx for the base
// pattern this builds on).
export default function SafeConfirm({
  open,
  title,
  description,
  onConfirm,
  onCancel,
  okText = 'OK',
  cancelText = 'Cancel',
  danger = true,
  confirmLoading = false,
}) {
  return (
    <SafeModal
      open={open}
      onCancel={onCancel}
      onOk={onConfirm}
      title={title}
      okText={okText}
      cancelText={cancelText}
      okButtonProps={{ danger }}
      confirmLoading={confirmLoading}
      width={420}
    >
      {description}
    </SafeModal>
  )
}
