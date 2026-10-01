interface SaveButtonProps {
  onSave: () => void
  saving: boolean
  disabled?: boolean
}

export function SaveButton({ onSave, saving, disabled = false }: SaveButtonProps) {
  return (
    <button
      type="button"
      onClick={onSave}
      disabled={disabled || saving}
      aria-busy={saving}
      className="rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
    >
      {saving ? 'Saving…' : 'Save'}
    </button>
  )
}
