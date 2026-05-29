import { useEffect, useState } from "react";

function WarningIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5 text-amber-400" stroke="currentColor" strokeWidth="1.8">
      <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" strokeLinecap="round" />
      <line x1="12" y1="17" x2="12.01" y2="17" strokeLinecap="round" strokeWidth="2.5" />
    </svg>
  );
}

export default function ConfirmDialog({ description, onConfirm, onCancel }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 50);
    return () => clearTimeout(t);
  }, []);

  return (
    <div
      className={`
        my-5 rounded-2xl overflow-hidden
        transition-all duration-300
        ${visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-3"}
      `}
      style={{
        background: "rgba(245, 158, 11, 0.06)",
        border: "1px solid rgba(245, 158, 11, 0.25)",
        boxShadow: "0 0 30px rgba(245, 158, 11, 0.08)",
      }}
    >
      <div className="h-0.5 w-full bg-gradient-to-r from-amber-500/60 via-amber-400 to-amber-500/60" />

      <div className="p-4">
        <div className="flex items-center gap-2.5 mb-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-500/15">
            <WarningIcon />
          </div>
          <div>
            <p className="text-sm font-semibold text-amber-300">Confirmation Required</p>
            <p className="text-[10px] text-amber-500/70">Human-in-the-loop checkpoint</p>
          </div>
        </div>

        <div
          className="mb-4 rounded-xl p-3 text-sm leading-relaxed text-amber-100/80"
          style={{ background: "rgba(245, 158, 11, 0.06)", border: "1px solid rgba(245, 158, 11, 0.12)" }}
        >
          {description}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onConfirm}
            className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-white transition-all duration-200 hover:bg-emerald-400 hover:shadow-lg hover:shadow-emerald-500/30 active:scale-95"
          >
            <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" stroke="currentColor" strokeWidth="2.5">
              <path d="M20 6L9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Yes, Proceed
          </button>
          <button
            onClick={onCancel}
            className="flex flex-1 items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold text-[#9ca3c2] transition-all duration-200 hover:bg-white/5 hover:text-white active:scale-95"
            style={{ border: "1px solid rgba(255,255,255,0.1)" }}
          >
            <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" stroke="currentColor" strokeWidth="2.5">
              <path d="M18 6L6 18M6 6l12 12" strokeLinecap="round" />
            </svg>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}