export default function ConfirmDialog({ description, onConfirm, onCancel }) {
  return (
    <div className="my-4 rounded-2xl border border-amber-200 bg-amber-50 p-4">
      <div className="text-sm font-semibold text-amber-900">Confirmation required</div>
      <div className="mt-2 text-sm text-amber-900">{description}</div>
      <div className="mt-4 flex gap-2">
        <button
          onClick={onConfirm}
          className="rounded-xl bg-green-600 px-4 py-2 text-sm font-semibold text-white hover:bg-green-700"
        >
          Yes, proceed
        </button>
        <button
          onClick={onCancel}
          className="rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

