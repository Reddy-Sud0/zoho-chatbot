import axios from "axios";

const API_BASE = "http://localhost:8000";

export async function sendChat({ sessionId, message, confirmed }) {
  const payload = { session_id: sessionId, message };
  if (typeof confirmed === "boolean") payload.confirmed = confirmed;
  const { data } = await axios.post(`${API_BASE}/chat`, payload);
  return data;
}
