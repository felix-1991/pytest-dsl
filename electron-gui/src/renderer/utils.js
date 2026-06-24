export function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

export function countLines(content) {
  if (!content) {
    return 0;
  }
  return content.endsWith("\n")
    ? content.split("\n").length - 1
    : content.split("\n").length;
}

export function fileNameFromPath(filePath) {
  const parts = String(filePath || "").split(/[\\/]/);
  return parts[parts.length - 1] || "source";
}

export function errorMessage(error) {
  return error && error.message ? error.message : String(error);
}

export function isPlainObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

export function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

export function escapeAttr(value) {
  return escapeHtml(value);
}

export function cssEscape(value) {
  if (window.CSS && typeof window.CSS.escape === "function") {
    return window.CSS.escape(String(value || ""));
  }
  return String(value || "").replace(/["\\]/g, "\\$&");
}
