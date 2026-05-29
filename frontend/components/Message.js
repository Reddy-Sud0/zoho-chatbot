import { extractMessageText } from "../utils/formatMessage";

function renderMarkdown(text) {
  const lines = text.split("\n");
  const blocks = [];
  let listItems = [];
  let numberedItems = [];

  const flushList = () => {
    if (listItems.length) {
      blocks.push(
        <ul key={`ul-${blocks.length}`} className="my-2 space-y-1.5 pl-4">
          {listItems.map((item, i) => (
            <li key={i} className="flex items-start gap-2 text-sm leading-relaxed text-[#d1d5f0]">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-violet-500" />
              <span dangerouslySetInnerHTML={{ __html: inlineMd(item) }} />
            </li>
          ))}
        </ul>
      );
      listItems = [];
    }
    if (numberedItems.length) {
      blocks.push(
        <ol key={`ol-${blocks.length}`} className="my-2 space-y-1.5 pl-4 list-decimal list-inside">
          {numberedItems.map((item, i) => (
            <li key={i} className="text-sm leading-relaxed text-[#d1d5f0]"
              dangerouslySetInnerHTML={{ __html: inlineMd(item) }} />
          ))}
        </ol>
      );
      numberedItems = [];
    }
  };

  const inlineMd = (s) =>
    s
      .replace(/\*\*(.+?)\*\*/g, '<strong class="font-semibold text-violet-300">$1</strong>')
      .replace(/`(.+?)`/g, '<code class="font-mono text-xs bg-violet-900/30 text-violet-300 px-1.5 py-0.5 rounded">$1</code>');

  lines.forEach((line, idx) => {
    const trimmed = line.trim();
    if (!trimmed) { flushList(); return; }

    if (trimmed.startsWith("# ")) {
      flushList();
      blocks.push(<h2 key={idx} className="mt-3 mb-1 text-base font-bold text-violet-300">{trimmed.slice(2)}</h2>);
      return;
    }
    if (trimmed.startsWith("## ") || trimmed.startsWith("### ")) {
      flushList();
      const lvl = trimmed.startsWith("### ") ? 3 : 2;
      const t = trimmed.slice(lvl + 1);
      blocks.push(<h3 key={idx} className="mt-2 mb-1 text-sm font-semibold text-violet-400 tracking-wide">{t}</h3>);
      return;
    }
    if (trimmed.startsWith("* ") || trimmed.startsWith("- ")) {
      numberedItems.length && flushList();
      listItems.push(trimmed.slice(2));
      return;
    }
    const numMatch = trimmed.match(/^(\d+)\.\s(.+)/);
    if (numMatch) {
      listItems.length && flushList();
      numberedItems.push(numMatch[2]);
      return;
    }
    if (trimmed.startsWith("---")) {
      flushList();
      blocks.push(<hr key={idx} className="my-3 border-white/10" />);
      return;
    }
    flushList();
    blocks.push(
      <p key={idx} className="text-sm leading-relaxed text-[#d1d5f0]"
        dangerouslySetInnerHTML={{ __html: inlineMd(trimmed) }} />
    );
  });

  flushList();
  return blocks;
}

function BotAvatar() {
  return (
    <div className="relative shrink-0">
      <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-indigo-700 shadow-lg glow-violet-sm">
        <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5 text-white" stroke="currentColor" strokeWidth="1.8">
          <rect x="5" y="9" width="14" height="10" rx="2" />
          <circle cx="9.5" cy="13.5" r="1" fill="currentColor" stroke="none" />
          <circle cx="14.5" cy="13.5" r="1" fill="currentColor" stroke="none" />
          <path d="M9 17h6" strokeLinecap="round" />
          <path d="M12 9V6" strokeLinecap="round" />
          <circle cx="12" cy="5" r="1.2" fill="currentColor" stroke="none" />
        </svg>
      </div>
      <span className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-[#0a0b14] bg-emerald-400" />
    </div>
  );
}

function UserAvatar() {
  return (
    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-fuchsia-500 to-violet-600 text-xs font-bold text-white shadow-lg">
      You
    </div>
  );
}

export default function Message({ role, content }) {
  const isUser = role === "user";
  const text = extractMessageText(content);

  if (isUser) {
    return (
      <div className="flex justify-end gap-3 my-4 animate-fade-left">
        <div className="flex max-w-[75%] flex-col items-end">
          <div className="bubble-user rounded-2xl rounded-br-sm px-4 py-3">
            <p className="text-sm leading-relaxed text-white whitespace-pre-wrap">{text}</p>
          </div>
          <span className="mt-1 text-[10px] text-[#5c6285]">Just now</span>
        </div>
        <UserAvatar />
      </div>
    );
  }

  return (
    <div className="flex justify-start gap-3 my-4 animate-fade-right">
      <BotAvatar />
      <div className="flex max-w-[80%] flex-col items-start">
        <div className="mb-1 flex items-center gap-2">
          <span className="text-[10px] font-semibold uppercase tracking-widest text-violet-400">Zoho Assistant</span>
        </div>
        <div className="bubble-bot rounded-2xl rounded-bl-sm px-4 py-3">
          <div className="md-content space-y-1">{renderMarkdown(text)}</div>
        </div>
        <span className="mt-1 text-[10px] text-[#5c6285]">Just now</span>
      </div>
    </div>
  );
}