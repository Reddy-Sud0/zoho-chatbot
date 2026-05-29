
export function extractMessageText(content) {
  if (!content) return "";
  if (typeof content === "string") {
    const s = content.trim();
    if (s.startsWith("[{") && s.includes("'type'")) {
      const match = s.match(/'text':\s*'([^']*)'/);
      if (match) return match[1].replace(/\\n/g, "\n");
    }
    return s;
  }
  if (Array.isArray(content)) {
    return content
      .map((b) => (typeof b === "object" && b?.text ? b.text : String(b)))
      .filter(Boolean)
      .join("\n\n");
  }
  return String(content);
}