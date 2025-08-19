// Centralized API helper for JSON requests with CSRF and normalized errors
(function(){
  function getCsrfToken() {
    try {
      const meta = document.querySelector('meta[name="csrf-token"]');
      return (meta && meta.getAttribute('content')) || '';
    } catch (_) {
      return '';
    }
  }

  async function postJSON(url, body) {
    const resp = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken()
      },
      body: JSON.stringify(body || {})
    });

    let data = null;
    try {
      data = await resp.json();
    } catch (_) {
      // Non-JSON error
    }

    if (!resp.ok) {
      const message = (data && (data.error || data.message)) || 'Unknown server error';
      const err = new Error(message);
      err.status = resp.status;
      err.data = data;
      throw err;
    }

    return data;
  }

  async function getJSON(url) {
    const resp = await fetch(url, {
      method: 'GET',
      headers: {
        'Accept': 'application/json'
      }
    });

    let data = null;
    try {
      data = await resp.json();
    } catch (_) {}

    if (!resp.ok) {
      const message = (data && (data.error || data.message)) || 'Unknown server error';
      const err = new Error(message);
      err.status = resp.status;
      err.data = data;
      throw err;
    }

    return data;
  }

  // expose globally
  window.postJSON = postJSON;
  window.getJSON = getJSON;
})();
