export default function TypingIndicator() {
  return (
    <div className="flex justify-start gap-3 my-4 animate-fade-right">
      {/* Bot avatar mini */}
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-indigo-700 shadow-lg">
        <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5 text-white" stroke="currentColor" strokeWidth="1.8">
          <rect x="5" y="9" width="14" height="10" rx="2" />
          <circle cx="9.5" cy="13.5" r="1" fill="currentColor" stroke="none" />
          <circle cx="14.5" cy="13.5" r="1" fill="currentColor" stroke="none" />
          <path d="M9 17h6" strokeLinecap="round" />
          <path d="M12 9V6" strokeLinecap="round" />
          <circle cx="12" cy="5" r="1.2" fill="currentColor" stroke="none" />
        </svg>
      </div>
      <div className="flex flex-col items-start">
        <div className="mb-1">
          <span className="text-[10px] font-semibold uppercase tracking-widest text-violet-400">Zoho Assistant</span>
        </div>
        <div
          className="flex items-center gap-1.5 rounded-2xl rounded-bl-sm px-5 py-4"
          style={{
            background: "rgba(255,255,255,0.04)",
            border: "1px solid rgba(255,255,255,0.08)",
          }}
        >
          <span className="typing-dot" />
          <span className="typing-dot" />
          <span className="typing-dot" />
        </div>
      </div>
    </div>
  );
}
