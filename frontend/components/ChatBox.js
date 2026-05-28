export default function ChatBox({ value, onChange, onSend, disabled }) {
  return (
    <div className="flex gap-2">
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) onSend();
        }}
        placeholder="Ask about projects, tasks, or create/update/delete tasks…"
        className="flex-1 rounded-xl border border-gray-200 px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-blue-500"
        disabled={disabled}
      />
      <button
        onClick={onSend}
        disabled={disabled}
        className="rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
      >
        Send
      </button>
    </div>
  );
}

