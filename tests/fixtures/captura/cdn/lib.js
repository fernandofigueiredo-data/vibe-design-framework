document.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => document.querySelectorAll('.entrada').forEach(e => { e.classList.add('visivel'); e.classList.remove('opacity-0'); }), 50);
  fetch("{{CDN}}/dados.json").then(r => r.json()).then(d => { document.getElementById('dados').textContent = d.mensagem; });
  const base = "{{CDN}}".split("/").slice(0, 3).join("/");
  fetch(base + "/din" + "amico.json").then(r => r.json()).then(d => { document.getElementById('dinamico').textContent = d.mensagem; });
});
