/* LeIA client for the cognitive service. Routes follow the service as observed in its templates.
   window.LEIA_API_BASE = "" (same origin, default) or "https://api.example" when the interface is served elsewhere. */
(function (global) {
  const base = () => (global.LEIA_API_BASE || "").replace(/\/$/, "");

  async function getTask(hash) {
    const r = await fetch(`${base()}/api/t/${hash}`, { headers: { Accept: "application/json" } });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  }

  async function submitQuiz(hash, respostas) {
    const r = await fetch(`${base()}/api/t/${hash}/quiz`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ respostas })
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  }

  /* SSE over fetch: events are "data: {t: '...'}" or "data: {error: '...'}". onChunk(text) is called per token. */
  async function chat(hash, mensagem, onChunk) {
    const r = await fetch(`${base()}/api/t/${hash}/chat`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mensagem })
    });
    if (!r.ok || !r.body) throw new Error(`HTTP ${r.status}`);
    const reader = r.body.getReader(); const dec = new TextDecoder(); let buf = ""; let acc = "";
    for (;;) {
      const { done, value } = await reader.read(); if (done) break;
      buf += dec.decode(value, { stream: true }); let i;
      while ((i = buf.indexOf("\n\n")) >= 0) {
        const chunk = buf.slice(0, i).trim(); buf = buf.slice(i + 2);
        if (!chunk.startsWith("data:")) continue;
        try {
          const ev = JSON.parse(chunk.slice(5).trim());
          if (ev.t) { acc += ev.t; onChunk(acc, false); }
          if (ev.error) throw new Error(ev.error);
        } catch (e) { if (e instanceof SyntaxError) continue; throw e; }
      }
    }
    onChunk(acc, true); return acc;
  }

  const receiptUrl = (hash) => `${base()}/t/${hash}/comprovante`;
  global.LeiaApi = { getTask, submitQuiz, chat, receiptUrl };
})(window);
