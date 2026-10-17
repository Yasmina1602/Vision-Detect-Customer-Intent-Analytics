const nf = new Intl.NumberFormat("ru-RU");

export function num(n: number | null | undefined): string {
  return n == null ? "—" : nf.format(n);
}

export function compact(n: number): string {
  if (Math.abs(n) >= 1e9) return (n / 1e9).toFixed(1).replace(/\.0$/, "") + " mlrd";
  if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, "") + " mln";
  if (Math.abs(n) >= 1e4) return (n / 1e3).toFixed(0) + " ming";
  return nf.format(n);
}

const CUR: Record<string, string> = { UZS: "so'm", USD: "$", EUR: "€", RUB: "₽" };

/** Pul har doim butun son (eng kichik birlik) sifatida keladi. */
export function money(minor: number | null | undefined, currency = "UZS", short = false): string {
  if (minor == null) return "—";
  const v = minor / 100;
  const s = short ? compact(v) : nf.format(Math.round(v));
  const sym = CUR[currency] ?? currency;
  return sym === "$" || sym === "€" ? `${sym}${s}` : `${s} ${sym}`;
}

export function pct(n: number | null | undefined, digits = 1): string {
  return n == null ? "—" : `${n.toFixed(digits).replace(/\.0+$/, "")}%`;
}

const MONTHS = ["yan", "fev", "mar", "apr", "may", "iyn", "iyl", "avg", "sen", "okt", "noy", "dek"];

export function shortDate(iso: string): string {
  const d = new Date(iso + (iso.length === 10 ? "T00:00:00" : ""));
  return `${d.getDate()} ${MONTHS[d.getMonth()]}`;
}

/** API UTC naive datetime qaytaradi → mahalliy vaqtda ko'rsatamiz. */
export function dateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(/[zZ]|[+-]\d\d:\d\d$/.test(iso) ? iso : iso + "Z");
  return `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear() !== new Date().getFullYear() ? d.getFullYear() + " " : ""}${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(/[zZ]|[+-]\d\d:\d\d$/.test(iso) ? iso : iso + "Z");
  const s = Math.round((Date.now() - d.getTime()) / 1000);
  if (s < 60) return "hozirgina";
  if (s < 3600) return `${Math.floor(s / 60)} daq oldin`;
  if (s < 86400) return `${Math.floor(s / 3600)} soat oldin`;
  return `${Math.floor(s / 86400)} kun oldin`;
}

export const ROLE_LABELS: Record<string, string> = {
  owner: "Egasi", admin: "Administrator", catalog_manager: "Katalog menejeri", analyst: "Analitik", viewer: "Kuzatuvchi",
};
export const ROLE_RANK: Record<string, number> = { viewer: 0, analyst: 1, catalog_manager: 2, admin: 3, owner: 4 };

export function can(role: string | undefined, min: string): boolean {
  return role != null && ROLE_RANK[role] >= ROLE_RANK[min];
}

/** O'zbekcha rang nomi → ko'rsatish uchun hex. */
export const COLOR_HEX: Record<string, string> = {
  qora: "#1f2937", oq: "#f8fafc", kulrang: "#9ca3af", qizil: "#dc2626", pushti: "#ec4899", "to'q sariq": "#f97316",
  sariq: "#eab308", yashil: "#16a34a", "ko'k": "#2563eb", "to'q ko'k": "#1e3a8a", havorang: "#38bdf8",
  binafsha: "#7c3aed", jigarrang: "#92400e", bej: "#d6c7a1", rangli: "conic-gradient(red,yellow,lime,cyan,blue,magenta,red)",
};

/** API rasmlari (/media/...) dashboard domeni orqali olinadi — API boshqa hostda bo'lsa ham ko'rinadi. */
export function img(url: string | null | undefined): string {
  if (!url) return "";
  const i = url.indexOf("/media/");
  return i >= 0 ? url.slice(i) : url;
}
