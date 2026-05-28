import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/router";
import Head from "next/head";
import ChatBox from "../components/ChatBox";
import Message from "../components/Message";
import ConfirmDialog from "../components/ConfirmDialog";
import TypingIndicator from "../components/TypingIndicator";
import { sendChat } from "../utils/api";

/* ─── Suggestion chips ─── */
const SUGGESTIONS = [
  { icon: "📋", label: "List my projects" },
  { icon: "✅", label: "Show open tasks" },
  { icon: "➕", label: "Create a task" },
  { icon: "👥", label: "Show project members" },
  { icon: "📊", label: "Task utilisation report" },
];

/* ─── Logo mark ─── */
function LogoMark() {
  return (
    <div className="flex items-center gap-2.5">
      <div className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-indigo-700 shadow-lg glow-violet-sm">
        <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5 text-white" stroke="currentColor" strokeWidth="1.8">
          <rect x="5" y="9" width="14" height="10" rx="2" />
          <circle cx="9.5" cy="13.5" r="1" fill="currentColor" stroke="none" />
          <circle cx="14.5" cy="13.5" r="1" fill="currentColor" stroke="none" />
          <path d="M9 17h6" strokeLinecap="round" />
          <path d="M12 9V6" strokeLinecap="round" />
          <circle cx="12" cy="5" r="1.2" fill="currentColor" stroke="none" />
        </svg>
        {/* Spinning glow ring */}
        <div className="absolute inset-0 rounded-xl border border-violet-400/30 animate-spin-slow" />
      </div>
      <div>
        <p className="text-sm font-bold leading-none text-white">Zoho Assistant</p>
        <p className="text-[10px] text-violet-400/80 leading-none mt-0.5">AI-Powered</p>
      </div>
    </div>
  );
}

/* ─── Sidebar nav item ─── */
function NavItem({ icon, label, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`sidebar-item flex w-full items-center gap-3 text-left ${active ? "active" : ""}`}
    >
      <span className="text-base">{icon}</span>
      <span className={`text-xs font-medium ${active ? "text-violet-300" : "text-[#9ca3c2]"}`}>{label}</span>
      {active && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-violet-400 animate-breathe" />}
    </button>
  );
}

/* ─── Empty state ─── */
function EmptyState({ onSuggest }) {
  return (
    <div className="flex flex-col items-center justify-center h-full px-8 text-center gap-6 select-none">
      {/* Big icon */}
      <div className="relative">
        <div className="flex h-20 w-20 items-center justify-center rounded-3xl bg-gradient-to-br from-violet-600/20 to-indigo-600/20 border border-violet-500/20">
          <svg viewBox="0 0 24 24" fill="none" className="h-10 w-10 text-violet-400" stroke="currentColor" strokeWidth="1.5">
            <rect x="5" y="9" width="14" height="10" rx="2" />
            <circle cx="9.5" cy="13.5" r="1" fill="currentColor" stroke="none" />
            <circle cx="14.5" cy="13.5" r="1" fill="currentColor" stroke="none" />
            <path d="M9 17h6" strokeLinecap="round" />
            <path d="M12 9V6" strokeLinecap="round" />
            <circle cx="12" cy="5" r="1.2" fill="currentColor" stroke="none" />
          </svg>
        </div>
        <div className="absolute -inset-2 rounded-[28px] border border-violet-500/10 animate-spin-slow" />
      </div>

      <div>
        <h2 className="text-xl font-bold gradient-text mb-2">How can I help you?</h2>
        <p className="text-xs text-[#5c6285] max-w-xs leading-relaxed">
          Ask me about your Zoho Projects, tasks, team members, or let me create and manage tasks for you.
        </p>
      </div>

      {/* Suggestion chips */}
      <div className="flex flex-wrap justify-center gap-2 max-w-sm">
        {SUGGESTIONS.map((s) => (
          <button
            key={s.label}
            onClick={() => onSuggest(s.label)}
            className="flex items-center gap-1.5 rounded-full px-3.5 py-2 text-xs font-medium text-[#9ca3c2] transition-all duration-200 hover:text-white hover:border-violet-500/50 active:scale-95"
            style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}
          >
            <span>{s.icon}</span>
            <span>{s.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export default function ChatPage() {
  const router = useRouter();
  const bottomRef = useRef(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState("");
  const [awaitingConfirm, setAwaitingConfirm] = useState(false);
  const [pendingAction, setPendingAction] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeNav, setActiveNav] = useState("chat");

  const urlSessionId = useMemo(() => {
    if (!router.isReady) return "";
    const v = router.query.session_id;
    return typeof v === "string" ? v : "";
  }, [router.isReady, router.query.session_id]);

  useEffect(() => {
    const existing = window.localStorage.getItem("zoho_session_id") || "";
    const sid = urlSessionId || existing;
    if (sid) {
      setSessionId(sid);
      window.localStorage.setItem("zoho_session_id", sid);
    }
  }, [urlSessionId]);

  /* Auto-scroll to bottom */
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSend(text) {
    const msg = (text || input).trim();
    if (!msg || !sessionId) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: msg }]);
    setLoading(true);
    try {
      const res = await sendChat({ sessionId, message: msg });
      if (res.awaiting_confirmation) {
        setAwaitingConfirm(true);
        setPendingAction(res.pending_action || null);
        setMessages((m) => [...m, { role: "bot", content: res.reply }]);
      } else {
        setMessages((m) => [...m, { role: "bot", content: res.reply }]);
      }
    } catch {
      setMessages((m) => [...m, { role: "bot", content: "⚠️ Connection error. Please check the backend is running." }]);
    } finally {
      setLoading(false);
    }
  }

  async function confirm() {
    setLoading(true);
    try {
      const res = await sendChat({ sessionId, message: "yes", confirmed: true });
      setAwaitingConfirm(false);
      setPendingAction(null);
      setMessages((m) => [...m, { role: "user", content: "✅ Confirmed" }, { role: "bot", content: res.reply }]);
    } finally {
      setLoading(false);
    }
  }

  async function cancel() {
    setLoading(true);
    try {
      const res = await sendChat({ sessionId, message: "no", confirmed: false });
      setAwaitingConfirm(false);
      setPendingAction(null);
      setMessages((m) => [...m, { role: "user", content: "❌ Cancelled" }, { role: "bot", content: res.reply }]);
    } finally {
      setLoading(false);
    }
  }

  function handleLogout() {
    window.localStorage.removeItem("zoho_session_id");
    router.push("/");
  }

  function clearChat() {
    setMessages([]);
    setAwaitingConfirm(false);
    setPendingAction(null);
  }

  const hasSession = !!sessionId;

  return (
    <>
      <Head>
        <title>Zoho Assistant — AI Chat</title>
        <meta name="description" content="AI-powered Zoho Projects chatbot with multi-agent LangGraph" />
        <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🤖</text></svg>" />
      </Head>

      <div className="bg-mesh flex h-screen w-screen overflow-hidden">

        {/* ─── SIDEBAR ─── */}
        <aside
          className={`
            glass flex flex-col transition-all duration-300 ease-in-out shrink-0
            ${sidebarOpen ? "w-56" : "w-0 overflow-hidden"}
          `}
          style={{ borderRight: "1px solid rgba(255,255,255,0.07)" }}
        >
          {/* Logo */}
          <div className="flex items-center justify-between p-4 pb-3">
            <LogoMark />
          </div>

          <div className="mx-4 mb-3 h-px bg-white/5" />

          {/* Nav */}
          <nav className="flex flex-col gap-1 px-3 py-1">
            <NavItem icon="💬" label="Chat" active={activeNav === "chat"} onClick={() => setActiveNav("chat")} />
            <NavItem icon="📋" label="Projects" active={activeNav === "projects"} onClick={() => setActiveNav("projects")} />
            <NavItem icon="✅" label="Tasks" active={activeNav === "tasks"} onClick={() => setActiveNav("tasks")} />
            <NavItem icon="👥" label="Team" active={activeNav === "team"} onClick={() => setActiveNav("team")} />
            <NavItem icon="📊" label="Reports" active={activeNav === "reports"} onClick={() => setActiveNav("reports")} />
          </nav>

          <div className="mx-4 mt-3 mb-2 h-px bg-white/5" />

          {/* Quick actions */}
          <div className="px-3">
            <p className="mb-2 px-3 text-[9px] font-semibold uppercase tracking-widest text-[#5c6285]">Quick Actions</p>
            {SUGGESTIONS.slice(0, 3).map((s) => (
              <button
                key={s.label}
                onClick={() => { setActiveNav("chat"); handleSend(s.label); }}
                className="sidebar-item flex w-full items-center gap-2.5 text-left"
              >
                <span className="text-sm">{s.icon}</span>
                <span className="text-xs text-[#9ca3c2]">{s.label}</span>
              </button>
            ))}
          </div>

          {/* Bottom: session + logout */}
          <div className="mt-auto p-4">
            <div className="mx-0 mb-3 h-px bg-white/5" />
            {hasSession ? (
              <div className="flex items-center gap-2 mb-3">
                <div className="status-dot" />
                <div className="flex-1 overflow-hidden">
                  <p className="text-[10px] font-medium text-emerald-400">Connected</p>
                  <p className="text-[9px] text-[#5c6285] truncate">{sessionId.slice(0, 18)}…</p>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2 mb-3">
                <div className="h-2 w-2 rounded-full bg-rose-500 animate-breathe" />
                <p className="text-[10px] text-rose-400">Not connected</p>
              </div>
            )}
            <div className="flex gap-1.5">
              <button
                onClick={clearChat}
                title="Clear chat"
                className="flex flex-1 items-center justify-center gap-1.5 rounded-xl py-2 text-[11px] font-medium text-[#9ca3c2] transition-colors hover:bg-white/5 hover:text-white"
                style={{ border: "1px solid rgba(255,255,255,0.08)" }}
              >
                <svg viewBox="0 0 24 24" fill="none" className="h-3.5 w-3.5" stroke="currentColor" strokeWidth="2">
                  <path d="M3 6h18M19 6l-1 14H6L5 6M10 11v6M14 11v6M8 6V4h8v2" strokeLinecap="round" />
                </svg>
                Clear
              </button>
              <button
                onClick={handleLogout}
                className="flex flex-1 items-center justify-center gap-1.5 rounded-xl py-2 text-[11px] font-medium text-rose-400 transition-colors hover:bg-rose-500/10"
                style={{ border: "1px solid rgba(244,63,94,0.2)" }}
              >
                <svg viewBox="0 0 24 24" fill="none" className="h-3.5 w-3.5" stroke="currentColor" strokeWidth="2">
                  <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" strokeLinecap="round" />
                </svg>
                Logout
              </button>
            </div>
          </div>
        </aside>

        {/* ─── MAIN CONTENT ─── */}
        <main className="flex flex-1 flex-col overflow-hidden">

          {/* ─── TOP BAR ─── */}
          <header
            className="flex shrink-0 items-center gap-3 px-5 py-3"
            style={{ borderBottom: "1px solid rgba(255,255,255,0.06)", background: "rgba(10,11,20,0.6)", backdropFilter: "blur(12px)" }}
          >
            {/* Hamburger */}
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="flex h-8 w-8 items-center justify-center rounded-lg text-[#9ca3c2] transition-colors hover:bg-white/5 hover:text-white"
            >
              <svg viewBox="0 0 24 24" fill="none" className="h-4.5 w-4.5" stroke="currentColor" strokeWidth="2">
                {sidebarOpen
                  ? <path d="M3 6h18M3 12h18M3 18h18" strokeLinecap="round" />
                  : <path d="M3 6h18M3 12h18M3 18h18" strokeLinecap="round" />}
              </svg>
            </button>

            {/* Title */}
            <div className="flex-1">
              <h1 className="text-sm font-semibold text-white">
                {activeNav.charAt(0).toUpperCase() + activeNav.slice(1)}
              </h1>
              <p className="text-[10px] text-[#5c6285]">
                {messages.length > 0 ? `${messages.length} messages` : "Start a conversation"}
              </p>
            </div>

            {/* Status pill */}
            <div
              className="flex items-center gap-2 rounded-full px-3 py-1.5"
              style={{ background: "rgba(16,185,129,0.1)", border: "1px solid rgba(16,185,129,0.2)" }}
            >
              <span className="status-dot h-2 w-2" />
              <span className="text-[10px] font-semibold text-emerald-400">Backend Live</span>
            </div>

            {/* Model badge */}
            <div
              className="flex items-center gap-1.5 rounded-full px-3 py-1.5"
              style={{ background: "rgba(124,58,237,0.12)", border: "1px solid rgba(124,58,237,0.25)" }}
            >
              <svg viewBox="0 0 24 24" fill="none" className="h-3 w-3 text-violet-400" stroke="currentColor" strokeWidth="2">
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
              </svg>
              <span className="text-[10px] font-semibold text-violet-400">Gemini 2.5</span>
            </div>
          </header>

          {/* ─── MESSAGES AREA ─── */}
          <div className="flex-1 overflow-y-auto px-5 py-4">
            {!hasSession ? (
              /* No session warning */
              <div className="flex flex-col items-center justify-center h-full gap-4">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl" style={{ background: "rgba(244,63,94,0.1)", border: "1px solid rgba(244,63,94,0.2)" }}>
                  <svg viewBox="0 0 24 24" fill="none" className="h-8 w-8 text-rose-400" stroke="currentColor" strokeWidth="1.8">
                    <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" strokeLinecap="round" /><line x1="12" y1="16" x2="12.01" y2="16" strokeLinecap="round" strokeWidth="2.5" />
                  </svg>
                </div>
                <div className="text-center">
                  <p className="text-base font-semibold text-rose-300">No Session Found</p>
                  <p className="text-xs text-[#5c6285] mt-1">Please login with your Zoho account to continue.</p>
                </div>
                <a
                  href="/"
                  className="btn-gradient relative flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold text-white"
                >
                  <span className="relative z-10 flex items-center gap-2">
                    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" stroke="currentColor" strokeWidth="2">
                      <path d="M15 3h4a2 2 0 012 2v14a2 2 0 01-2 2h-4M10 17l5-5-5-5M15 12H3" strokeLinecap="round" />
                    </svg>
                    Go to Login
                  </span>
                </a>
              </div>
            ) : messages.length === 0 ? (
              <EmptyState onSuggest={(label) => { handleSend(label); }} />
            ) : (
              <>
                {messages.map((m, idx) => (
                  <Message key={idx} role={m.role} content={m.content} />
                ))}

                {/* HIL Confirm dialog inline */}
                {awaitingConfirm && (
                  <ConfirmDialog
                    description={(pendingAction && pendingAction.description) || "I'm about to perform a write action. Would you like to continue?"}
                    onConfirm={confirm}
                    onCancel={cancel}
                  />
                )}

                {/* Typing indicator */}
                {loading && <TypingIndicator />}

                <div ref={bottomRef} />
              </>
            )}
          </div>

          {/* ─── INPUT BAR ─── */}
          {hasSession && (
            <div
              className="shrink-0 px-5 py-4"
              style={{ borderTop: "1px solid rgba(255,255,255,0.06)", background: "rgba(10,11,20,0.7)", backdropFilter: "blur(12px)" }}
            >
              <ChatBox
                value={input}
                onChange={setInput}
                onSend={() => handleSend()}
                disabled={loading || awaitingConfirm}
              />
              <p className="mt-2 text-center text-[10px] text-[#5c6285]">
                Press <kbd className="rounded bg-white/5 px-1.5 py-0.5 font-mono text-[9px] text-[#9ca3c2]">Enter</kbd> to send · <kbd className="rounded bg-white/5 px-1.5 py-0.5 font-mono text-[9px] text-[#9ca3c2]">Shift+Enter</kbd> for new line
              </p>
            </div>
          )}
        </main>
      </div>
    </>
  );
}
