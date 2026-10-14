import axios from "axios";

export const BACKEND = process.env.REACT_APP_BACKEND_URL;

export const api = axios.create({ baseURL: `${BACKEND}/api`, withCredentials: true });

api.interceptors.request.use((cfg) => {
  const t = localStorage.getItem("tt_token");
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

export function errMsg(e) {
  const d = e?.response?.data?.detail;
  if (d == null) return e?.message || "Something went wrong. Please try again.";
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x?.msg || JSON.stringify(x)).join(" ");
  return d.msg || String(d);
}

export async function downloadFile(path, params, fallbackName) {
  const res = await api.get(path, { params, responseType: "blob" });
  const cd = res.headers["content-disposition"] || "";
  const m = cd.match(/filename="?([^"]+)"?/);
  const url = URL.createObjectURL(res.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = m ? m[1] : fallbackName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export const fmtDate = (v) => {
  if (!v) return "-";
  const d = new Date(v);
  return isNaN(d) ? String(v) : d.toLocaleString(undefined, { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
};

export const show = (v) => {
  if (v === null || v === undefined || v === "") return "-";
  if (typeof v === "boolean") return v ? "Yes" : "No";
  if (Array.isArray(v)) return v.length ? v.join(", ") : "-";
  return String(v);
};
