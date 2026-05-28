import Head from "next/head";
import { useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const FEATURES = [
  {
    icon: "🔐",
    title: "OAuth 2.0 Login",
    desc: "Secure per-user token management with silent auto-refresh.",
  },
  {
    icon: "🤖",
    title: "Multi-Agent AI",
    desc: "Separate Query & Action agents orchestrated by LangGraph.",
  },
  {
    icon: "🛡️",
    title: "Human-in-the-Loop",
    desc: "Every write operation requires explicit user confirmation.",
  },
  {
    icon: "🧠",
    title: "Persistent Memory",
    desc: "Short-term session context + long-term cross-session memory.",
  },
];

export default function Home() {
  const [hovered, setHovered] = useState(false);

  return (
    <>
      <Head>
        <title>Zoho Assistant — Login</title>
        <meta name="description" content="AI-powered Zoho Projects chatbot. Login with your Zoho account to get started." />
        <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🤖</text></svg>" />
      </Head>

      <div className="bg-mesh flex min-h-screen items-center justify-center p-6">

        {/* ─── Background orbs ─── */}
        <div className="pointer-events-none fixed inset-0 overflow-hidden">
          <div
            className="absolute -top-40 -left-40 h-96 w-96 rounded-full opacity-30 blur-3xl"
            style={{ background: "radial-gradient(circle, #7c3aed 0%, transparent 70%)" }}
          />
          <div
            className="absolute -bottom-40 -right-40 h-96 w-96 rounded-full opacity-20 blur-3xl"
            style={{ background: "radial-gradient(circle, #06b6d4 0%, transparent 70%)" }}
          />
          <div
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-64 w-64 rounded-full opacity-10 blur-3xl"
            style={{ background: "radial-gradient(circle, #4f46e5 0%, transparent 70%)" }}
          />
        </div>

        <div className="relative z-10 w-full max-w-5xl">

          {/* ─── HERO CARD ─── */}
          <div className="glass-strong rounded-3xl overflow-hidden shadow-2xl" style={{ boxShadow: "0 25px 60px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.06)" }}>

            {/* Top rainbow accent bar */}
            <div className="h-px w-full bg-gradient-to-r from-transparent via-violet-500 to-transparent opacity-60" />

            <div className="grid md:grid-cols-2 gap-0">

              {/* ─── LEFT: Login panel ─── */}
              <div className="flex flex-col justify-center p-10 md:p-14">

                {/* Badge */}
                <div className="mb-8 flex items-center gap-2">
                  <div
                    className="flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-semibold text-violet-300"
                    style={{ background: "rgba(124,58,237,0.15)", border: "1px solid rgba(124,58,237,0.3)" }}
                  >
                    <span className="h-1.5 w-1.5 rounded-full bg-violet-400 animate-breathe" />
                    AI-Powered · LangGraph Multi-Agent
                  </div>
                </div>

                {/* Headline */}
                <h1 className="mb-4 text-4xl font-bold leading-tight tracking-tight">
                  <span className="text-white">Your Zoho Projects,</span>
                  <br />
                  <span className="gradient-text">Supercharged with AI</span>
                </h1>

                <p className="mb-10 text-sm leading-relaxed text-[#9ca3c2]">
                  Manage projects and tasks through natural conversation.
                  Query, create, update, and delete — all with intelligent confirmation.
                </p>

                {/* Login button */}
                <a
                  href={`${API_BASE}/auth/login`}
                  onMouseEnter={() => setHovered(true)}
                  onMouseLeave={() => setHovered(false)}
                  className="btn-gradient group relative mb-4 flex items-center justify-center gap-3 rounded-2xl px-8 py-4 text-base font-semibold text-white shadow-xl"
                  style={{ boxShadow: hovered ? "0 15px 40px rgba(124,58,237,0.5)" : "0 8px 25px rgba(124,58,237,0.3)" }}
                >
                  <span className="relative z-10 flex items-center gap-3">
                    {/* Zoho-like Z icon */}
                    <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-white/15 text-sm font-black">Z</span>
                    Continue with Zoho
                    <svg viewBox="0 0 24 24" fill="none" className={`h-4 w-4 transition-transform duration-200 ${hovered ? "translate-x-1" : ""}`} stroke="currentColor" strokeWidth="2.5">
                      <path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </span>
                </a>

                {/* Trust line */}
                <p className="text-center text-[11px] text-[#5c6285]">
                  🔒 Your credentials are never stored — OAuth only
                </p>

                {/* Divider */}
                <div className="my-8 flex items-center gap-3">
                  <div className="flex-1 h-px bg-white/5" />
                  <span className="text-[10px] text-[#5c6285] uppercase tracking-widest">Features</span>
                  <div className="flex-1 h-px bg-white/5" />
                </div>

                {/* Feature list */}
                <div className="space-y-3">
                  {FEATURES.map((f) => (
                    <div key={f.title} className="flex items-start gap-3">
                      <span className="text-lg leading-none mt-0.5">{f.icon}</span>
                      <div>
                        <p className="text-xs font-semibold text-white">{f.title}</p>
                        <p className="text-[11px] text-[#5c6285] leading-relaxed">{f.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* ─── RIGHT: Visual panel ─── */}
              <div
                className="relative hidden md:flex flex-col justify-center p-10 overflow-hidden"
                style={{ background: "rgba(124,58,237,0.05)", borderLeft: "1px solid rgba(255,255,255,0.06)" }}
              >
                {/* Decorative blobs */}
                <div
                  className="absolute top-0 right-0 h-64 w-64 rounded-full opacity-20 blur-3xl"
                  style={{ background: "radial-gradient(circle, #7c3aed 0%, transparent 70%)" }}
                />
                <div
                  className="absolute bottom-0 left-0 h-48 w-48 rounded-full opacity-15 blur-3xl"
                  style={{ background: "radial-gradient(circle, #06b6d4 0%, transparent 70%)" }}
                />

                {/* Mock chat preview */}
                <div className="relative space-y-4">
                  <p className="text-[10px] uppercase tracking-widest text-[#5c6285] mb-6">Live Preview</p>

                  {/* Mock messages */}
                  {[
                    { role: "user", text: "What projects do I have?" },
                    { role: "bot", text: "You have **3 active projects**:\n* Website Redesign\n* API Integration\n* Mobile App" },
                    { role: "user", text: "Create a task called Deploy v2" },
                    { role: "bot", text: "**Confirmation required**\nI am about to create task **Deploy v2**.\nShall I proceed?" },
                  ].map((m, i) => (
                    <div
                      key={i}
                      className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
                      style={{ animationDelay: `${i * 0.1}s` }}
                    >
                      <div
                        className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-xs leading-relaxed ${
                          m.role === "user"
                            ? "bubble-user text-white rounded-br-sm"
                            : "bubble-bot text-[#d1d5f0] rounded-bl-sm"
                        }`}
                      >
                        {m.text.split("\n").map((line, li) => (
                          <span key={li} className="block">
                            {line.replace(/\*\*(.+?)\*\*/g, "$1").replace(/^\* /, "• ")}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}

                  {/* Typing dots */}
                  <div className="flex justify-start">
                    <div className="bubble-bot flex items-center gap-1.5 rounded-2xl rounded-bl-sm px-4 py-3">
                      <span className="typing-dot" />
                      <span className="typing-dot" />
                      <span className="typing-dot" />
                    </div>
                  </div>
                </div>

                {/* Stats row */}
                <div className="relative mt-8 grid grid-cols-3 gap-3">
                  {[
                    { val: "8", label: "Tools" },
                    { val: "2", label: "Agents" },
                    { val: "∞", label: "Memory" },
                  ].map((s) => (
                    <div
                      key={s.label}
                      className="flex flex-col items-center rounded-xl py-3"
                      style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}
                    >
                      <span className="text-xl font-bold gradient-text">{s.val}</span>
                      <span className="text-[10px] text-[#5c6285] mt-0.5">{s.label}</span>
                    </div>
                  ))}
                </div>
              </div>

            </div>

            {/* Bottom bar */}
            <div
              className="flex items-center justify-between px-10 py-3"
              style={{ borderTop: "1px solid rgba(255,255,255,0.05)", background: "rgba(0,0,0,0.2)" }}
            >
              <p className="text-[10px] text-[#5c6285]">Built with FastAPI · LangGraph · Next.js · Zoho Projects API</p>
              <div className="flex items-center gap-4">
                <a href="https://github.com/Reddy-Sud0/zoho-chatbot" target="_blank" rel="noopener noreferrer"
                  className="text-[10px] text-[#5c6285] hover:text-violet-400 transition-colors flex items-center gap-1">
                  <svg viewBox="0 0 24 24" fill="currentColor" className="h-3 w-3">
                    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
                  </svg>
                  GitHub
                </a>
                <span className="text-[10px] text-[#5c6285]">v1.0.0</span>
              </div>
            </div>

          </div>
        </div>
      </div>
    </>
  );
}
