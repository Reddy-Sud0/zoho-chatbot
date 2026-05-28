import { extractMessageText } from "../utils/formatMessage";

function renderMarkdownish(text) {
  const lines = text.split("\n");
  const blocks = [];
  let listItems = [];

  const flushList = () => {
    if (!listItems.length) return;
    blocks.push(
      <ul key={`ul-${blocks.length}`} className="my-2 list-disc space-y-1 pl-5">
        {listItems.map((item, i) => (
          <li key={i} className="leading-relaxed">
            {item}
          </li>
        ))}
      </ul>
    );
    listItems = [];
  };

  lines.forEach((line, idx) => {
    const trimmed = line.trim();
    if (!trimmed) {
      flushList();
      return;
    }

    if (trimmed.startsWith("## ")) {
      flushList();
      blocks.push(
        <h3 key={`h-${idx}`} className="mt-2 text-sm font-semibold text-gray-900">
          {trimmed.slice(3)}
        </h3>
      );
      return;
    }

    if (trimmed.startsWith("* ") || trimmed.startsWith("- ")) {
      listItems.push(trimmed.slice(2));
      return;
    }

    flushList();
    blocks.push(
      <p key={`p-${idx}`} className="leading-relaxed text-gray-800">
        {trimmed}
      </p>
    );
  });

  flushList();
  return blocks;
}

export default function Message({ role, content }) {
  const isUser = role === "user";
  const text = extractMessageText(content);

  if (isUser) {
    return (
      <div className="flex justify-end my-3">
        <div className="max-w-[80%] rounded-2xl rounded-br-md bg-blue-600 px-4 py-3 text-sm text-white shadow-md">
          <p className="whitespace-pre-wrap leading-relaxed">{text}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start my-3 gap-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-xs font-bold text-white shadow">
        AI
      </div>
      <div className="max-w-[85%] rounded-2xl rounded-bl-md border border-gray-200 bg-white px-4 py-3 text-sm shadow-sm">
        <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-indigo-600">
          Zoho Assistant
        </div>
        <div className="space-y-1">{renderMarkdownish(text)}</div>
      </div>
    </div>
  );
}
