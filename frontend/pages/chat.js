import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/router";
import ChatBox from "../components/ChatBox";
import Message from "../components/Message";
import ConfirmDialog from "../components/ConfirmDialog";
import { sendChat } from "../utils/api";

export default function ChatPage() {
  const router = useRouter();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState("");
  const [awaitingConfirm, setAwaitingConfirm] = useState(false);
  const [pendingAction, setPendingAction] = useState(null);

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

  async function handleSend() {
    const text = input.trim();
    if (!text || !sessionId) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    setLoading(true);
    try {
      const res = await sendChat({ sessionId, message: text });
      if (res.awaiting_confirmation) {
        setAwaitingConfirm(true);
        setPendingAction(res.pending_action || null);
        setMessages((m) => [...m, { role: "bot", content: res.reply }]);
      } else {
        setMessages((m) => [...m, { role: "bot", content: res.reply }]);
      }
    } catch (e) {
      setMessages((m) => [...m, { role: "bot", content: "Error talking to backend." }]);
    } finally {
      setLoading(false);
    }
  }

  async function confirm() {
    if (!sessionId) return;
    setLoading(true);
    try {
      const res = await sendChat({ sessionId, message: "yes", confirmed: true });
      setAwaitingConfirm(false);
      setPendingAction(null);
      setMessages((m) => [...m, { role: "user", content: "yes" }, { role: "bot", content: res.reply }]);
    } finally {
      setLoading(false);
    }
  }

  async function cancel() {
    if (!sessionId) return;
    setLoading(true);
    try {
      const res = await sendChat({ sessionId, message: "no", confirmed: false });
      setAwaitingConfirm(false);
      setPendingAction(null);
      setMessages((m) => [...m, { role: "user", content: "no" }, { role: "bot", content: res.reply }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="mx-auto flex min-h-screen max-w-3xl flex-col px-4 py-6">
        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-lg font-bold text-gray-900">Zoho Project Assistant</div>
              <div className="text-xs text-gray-500">
                Session: {sessionId ? sessionId.slice(0, 8) + "…" : "not set"}
              </div>
            </div>
            <a className="text-sm font-semibold text-blue-700 hover:underline" href="/">
              Logout
            </a>
          </div>
        </div>

        <div className="mt-4 flex-1 overflow-y-auto rounded-2xl bg-white p-5 shadow-sm">
          {messages.length === 0 ? (
            <div className="text-sm text-gray-500">
              Log in first, then ask things like “What projects do I have?” or “Create a task called API Integration”.
            </div>
          ) : (
            messages.map((m, idx) => <Message key={idx} role={m.role} content={m.content} />)
          )}

          {awaitingConfirm && (
            <ConfirmDialog
              description={(pendingAction && pendingAction.description) || "I’m about to perform a write action. Continue?"}
              onConfirm={confirm}
              onCancel={cancel}
            />
          )}

          {loading && <div className="mt-3 text-xs text-gray-500">Bot is typing…</div>}
        </div>

        <div className="mt-4 rounded-2xl bg-white p-5 shadow-sm">
          {!sessionId ? (
            <div className="text-sm text-red-600">No session found. Please login from the home page.</div>
          ) : (
            <ChatBox value={input} onChange={setInput} onSend={handleSend} disabled={loading || awaitingConfirm} />
          )}
        </div>
      </div>
    </div>
  );
}

