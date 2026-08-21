// Shared reveal.js head/foot for the orientation-family decks (course
// orientations and Advisory). deck.css stays frozen; each generator passes
// its own one-off CSS into head().
export const esc = t => String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

export const head = (title, css = '') => `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" href="/assets/img/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<title>${esc(title)}</title>

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Familjen+Grotesk:ital,wght@0,500;0,600;0,700;1,500&family=Atkinson+Hyperlegible+Next:wght@400;500;600;700&family=Fragment+Mono&display=swap" rel="stylesheet">

<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/reveal.css">
<link rel="stylesheet" href="/assets/slides/deck.css">
<style>
${css}</style>
</head>
<body>
<div class="reveal"><div class="slides">`;

export const FOOT = `</div></div>
<script src="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/reveal.js"></script>
<script src="https://cdn.jsdelivr.net/npm/reveal.js@5/plugin/notes/notes.js"></script>
<script>
  Reveal.initialize({ hash: true, slideNumber: 'c/t', plugins: [ RevealNotes ] });
</script>
</body>
</html>
`;

export const notes = t => `<aside class="notes">${t}</aside>`;

// Three-ring binder, drawn in the deck's blue.
export const BINDER_SVG = `<svg viewBox="0 0 64 72" width="64" height="72" aria-hidden="true"><rect x="10" y="4" width="48" height="64" rx="5" fill="#fff" stroke="#0E406A" stroke-width="3"/><rect x="10" y="4" width="12" height="64" rx="3" fill="#0E406A"/><g fill="none" stroke="#0E406A" stroke-width="3" stroke-linecap="round"><circle cx="16" cy="18" r="5" fill="#fff"/><circle cx="16" cy="36" r="5" fill="#fff"/><circle cx="16" cy="54" r="5" fill="#fff"/></g><g stroke="#d6dde6" stroke-width="3" stroke-linecap="round"><line x1="30" y1="22" x2="50" y2="22"/><line x1="30" y1="34" x2="50" y2="34"/><line x1="30" y1="46" x2="44" y2="46"/></g></svg>`;
