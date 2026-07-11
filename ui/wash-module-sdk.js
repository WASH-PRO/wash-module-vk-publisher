/**
 * WASH Module UI SDK
 */
(function (global) {
  const API_PREFIX = '/api/crm/modules';
  function getToken() { return localStorage.getItem('wash_crm_token') || ''; }
  async function api(path, options) {
    const token = getToken();
    const res = await fetch(`${API_PREFIX}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options && options.headers ? options.headers : {}),
      },
    });
    const json = await res.json();
    if (!res.ok || json.success !== true) throw new Error(json.error || `HTTP ${res.status}`);
    return json.data;
  }
  global.WashModule = { api };
})(window);
