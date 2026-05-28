import { useRef, useEffect } from "react";

/* ─── Send icon ─── */
function SendIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" stroke="currentColor" strokeWidth="2">
      <path d="M22 2L11 13" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M22 2L15 22L11 13L2 9L22 2Z" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function ChatBox({ value, onChange, onSend, disabled }) {
  const textareaRef = useRef(null);

  /* Auto-resize textarea */
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
  }, [value]);

  function handleKey(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!disabled && value.trim()) onSend();
    }
  }

  const canSend = !disabled && value.trim().length > 0;

  return (
    <div
      className="flex items-end gap-3 rounded-2xl p-3 transition-all duration-200"
      style={{
        background: "rgba(255,255,255,0.04)",
        border: "1px solid rgba(255,255,255,0.1)",
        boxShadow: value ? "0 0 0 2px rgba(124,58,237,0.2), 0 0 20px rgba(124,58,237,0.08)" : "none",
      }}
    >
      {/* Mic / attachment hint icon */}
      <button
        type="button"
        className="mb-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-[#5c6285] transition-colors hover:text-violet-400"
        tabIndex={-1}
      >
        <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" stroke="currentColor" strokeWidth="1.8">
          <rect x="9" y="2" width="6" height="11" rx="3" />
          <path d="M5 10a7 7 0 0 0 14 0" strokeLinecap="round" />
          <path d="M12 17v4" strokeLinecap="round" />
          <path d="M8 21h8" strokeLinecap="round" />
        </svg>
      </button>

      {/* Auto-grow textarea */}
      <textarea
        ref={textareaRef}
        rows={1}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKey}
        placeholder='Ask me anything… "What projects do I have?" or "Create a task"'
        disabled={disabled}
        className="chat-input flex-1 resize-none bg-transparent text-sm leading-relaxed text-[#f0f0ff] placeholder-[#5c6285] outline-none transition-all"
        style={{ maxHeight: "120px", fontFamily: "Inter, sans-serif" }}
      />

      {/* Character count hint */}
      {value.length > 0 && (
        <span className="mb-1 text-[10px] text-[#5c6285] shrink-0">{value.length}</span>
      )}

      {/* Send button */}
      <button
        onClick={onSend}
        disabled={!canSend}
        className={`
          btn-gradient relative mb-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-white
          transition-all duration-200
          ${canSend ? "opacity-100" : "opacity-30 cursor-not-allowed"}
        `}
      >
        <span className="relative z-10">
          <SendIcon />
        </span>
      </button>
    </div>
  );
}
