/**
 * Shared JS for Attendance UI. Cookie credentials for session auth.
 */

const API_BASE = "";

function fetchApi(path, options = {}) {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  const opts = {
    ...options,
    headers: {
      "Accept": "application/json",
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    credentials: "same-origin",
  };
  if (options.body instanceof FormData) {
    opts.body = options.body;
    delete opts.headers["Content-Type"];
  } else if (options.body && typeof options.body === "object") {
    opts.body = JSON.stringify(options.body);
  } else if (options.body) {
    opts.body = options.body;
  }
  return fetch(url, opts);
}

function showMsg(el, text, isError) {
  if (!el) return;
  el.textContent = text;
  el.className = "msg " + (isError ? "error" : "success");
  el.hidden = false;
}

function hideMsg(el) {
  if (!el) return;
  el.hidden = true;
}
