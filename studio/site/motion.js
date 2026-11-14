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

  /* ── line splitting ─────────────────────────────────────────────────────
     Headlines are split into masked lines at load so each one can be uncovered
     rather than faded. The markup keeps its <br> and <em>; splitting happens on
     the rendered line boxes, so a line break in the sentence is respected. */
  function splitLines(el) {
    if (el.dataset.split === 'done') return [];
    const nodes = [...el.childNodes];
    // Wrap each inline run in a span we can measure, preserving <em>/<strong>.
    const runs = [];
    nodes.forEach((node) => {
      if (node.nodeType === Node.TEXT_NODE) {
        const text = node.textContent;
        if (!text.trim()) return;
        text.split(/(\s+)/).forEach((word) => {
          if (!word.trim()) return;
          const w = document.createElement('span');
          w.className = 'w';
          w.textContent = word;
          runs.push(w);
        });
        if (node.nextSibling && node.nextSibling.nodeName === 'BR') return;
      } else if (node.nodeName === 'BR') {
        const br = document.createElement('span');
        br.className = 'w brk';
        br.style.display = 'block';
        br.style.height = '0';
        runs.push(br);
      } else if (node.nodeType === Node.ELEMENT_NODE) {
        const text = node.textContent.trim();
        if (!text) return;
        text.split(/\s+/).forEach((word) => {
          const w = document.createElement('span');
          w.className = 'w';
          const inner = document.createElement(node.nodeName.toLowerCase() === 'em' ? 'em' : 'span');
          inner.textContent = word;
          w.appendChild(inner);
          runs.push(w);
        });
      }
    });

    el.textContent = '';
    el.dataset.split = 'done';
    runs.forEach((r) => el.appendChild(r));
    return [...el.querySelectorAll('.w')];
  }

  /* ── reveal ─────────────────────────────────────────────────────────────
     Each revealed element gets a small stagger offset derived from its order
     inside its parent, so a row of three plates arrives as a cadence rather
     than in unison. */
  const revealables = [...document.querySelectorAll('[data-reveal]')];

  function prepare() {
    document.documentElement.style.setProperty('--ease', EASE);
    document.querySelectorAll('[data-split]').forEach((h) => {
      const words = splitLines(h);
      words.forEach((w) => {
        w.style.display = 'inline-block';
        w.style.overflow = 'hidden';
        w.style.verticalAlign = 'bottom';
      });
      h.style.setProperty('--n', words.length);
    });
  }

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
