// Revelação no scroll: copiado do <script> inline da fonte
  const vigia = new IntersectionObserver((itens) => {
    itens.forEach((item) => {
      if (item.isIntersecting) { item.target.classList.add('visto'); vigia.unobserve(item.target); }
    });
  }, {rootMargin: '0px 0px -10% 0px'});
  document.querySelectorAll('.revelar').forEach((el) => vigia.observe(el));
