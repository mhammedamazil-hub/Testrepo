/* KILN — motion.

   One easing curve for the whole site, one duration family, no libraries. The rule is
   that motion explains structure: a line of type is uncovered, an image settles, a
   section arrives from the direction it sits in the page. Nothing bounces.

   Everything is inert until it is in view, everything is undone under
   prefers-reduced-motion, and the whole file is 3 KB. */

(() => {
  'use strict';

  const EASE = 'cubic-bezier(.16,1,.3,1)';
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const hasIO = 'IntersectionObserver' in window;

  /* ── line reveals ───────────────────────────────────────────────────────
     Headlines declare their lines in markup (`<span class="l">`), because a
     splitter that measures line boxes will break on a serif with tight leading
     and will silently swallow word spaces. Each declared line is wrapped in a
     mask and uncovered from below; the words inside never move. */
  function prepare() {
    document.documentElement.style.setProperty('--ease', EASE);
    document.querySelectorAll('[data-split]').forEach((h) => {
      h.querySelectorAll(':scope > .l').forEach((line) => {
        if (line.dataset.masked) return;
        line.dataset.masked = '1';
        const mask = document.createElement('span');
        mask.className = 'mask';
        line.parentNode.insertBefore(mask, line);
        mask.appendChild(line);
      });
    });
  }

  /* ── reveal ─────────────────────────────────────────────────────────────
     Each revealed element gets a small stagger offset derived from its order
     inside its parent, so a row of three plates arrives as a cadence rather
     than in unison. */
  const revealables = [...document.querySelectorAll('[data-reveal]')];

  function play(el, i = 0) {
    el.style.transitionDelay = `${Math.min(i * 70, 280)}ms`;
    el.classList.add('in');
    el.addEventListener('transitionend', () => {
      el.style.transitionDelay = '';
      el.classList.remove('pre');
    }, { once: true });
  }

  function init() {
    prepare();

    if (reduced) {
      document.querySelectorAll('[data-reveal]').forEach((el) => el.classList.add('in'));
      document.querySelectorAll('[data-split]').forEach((h) => h.classList.add('in'));
      document.documentElement.classList.add('no-motion');
      return;
    }

    revealables.forEach((el) => el.classList.add('pre'));

    if (!hasIO) {
      revealables.forEach((el) => el.classList.add('in'));
      document.querySelectorAll('[data-split]').forEach((h) => h.classList.add('in'));
      return;
    }

    const counts = new WeakMap();
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const el = entry.target;
        const parent = el.parentElement;
        const n = counts.get(parent) || 0;
        counts.set(parent, n + 1);
        if (el.hasAttribute('data-split')) el.classList.add('in');
        else play(el, n);
        io.unobserve(el);
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.12 });

    revealables.forEach((el) => io.observe(el));
    document.querySelectorAll('[data-split]').forEach((el) => io.observe(el));

    /* Failsafe: if anything goes wrong with the observer, or the page is captured
       or printed without scrolling, everything becomes visible after four seconds.
       A reveal must never be the reason a visitor cannot read the page. */
    setTimeout(() => {
      revealables.forEach((el) => el.classList.add('in'));
      document.querySelectorAll('[data-split]').forEach((el) => el.classList.add('in'));
    }, 4000);
  }

  /* ── scroll: the hero plate drifts, the nav condenses ───────────────────
     A single rAF loop, transform-only, disabled under reduced motion. */
  function scroll() {
    if (reduced) return;
    const fig = document.querySelector('.hero-figure img');
    const nav = document.querySelector('.nav');
    let ticking = false;
    const update = () => {
      const y = window.scrollY;
      if (fig && y < window.innerHeight * 1.2) {
        fig.style.transform = `translate3d(0, ${(y * 0.06).toFixed(2)}px, 0) scale(1.02)`;
      }
      if (nav) nav.classList.toggle('condensed', y > 40);
      ticking = false;
    };
    window.addEventListener('scroll', () => {
      if (!ticking) { ticking = true; requestAnimationFrame(update); }
    }, { passive: true });
    update();
  }

  /* ── film: play when in view, pause when not ─────────────────────────────
     preload="none" keeps the 166 KB off the critical path. */
  function film() {
    const v = document.querySelector('.film-video');
    if (!v) return;
    v.addEventListener('mouseenter', () => v.play().catch(() => {}));
    if (!hasIO) return;
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) { v.play().catch(() => {}); }
        else { v.pause(); }
      });
    }, { threshold: 0.35 });
    io.observe(v);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => { init(); scroll(); film(); });
  } else { init(); scroll(); film(); }
})();
