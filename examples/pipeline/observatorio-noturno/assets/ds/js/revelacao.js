// Revelação no scroll e contador do hero, copiados do <script> inline da fonte
(() => {
  const alvos = document.querySelectorAll('.aparecer, .mapa__grafico');
  const observador = new IntersectionObserver((entradas) => {
    for (const e of entradas) {
      if (e.isIntersecting) { e.target.classList.add('revelado'); observador.unobserve(e.target); }
    }
  }, {threshold: 0.18});
  alvos.forEach((el) => observador.observe(el));

  const contador = document.querySelector('[data-contar]');
  if (contador && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const fim = Number(contador.dataset.contar), inicio = performance.now(), duracao = 1600;
    const passo = (agora) => {
      const t = Math.min(1, (agora - inicio) / duracao), suave = 1 - Math.pow(1 - t, 3);
      contador.textContent = Math.round(fim * suave).toLocaleString('pt-BR');
      if (t < 1) requestAnimationFrame(passo);
    };
    requestAnimationFrame(passo);
  }
})();
