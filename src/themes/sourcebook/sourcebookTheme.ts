import {defineTheme} from '@astryxdesign/core/theme';
import {matchaTheme} from '@astryxdesign/theme-matcha/built';
// Extend, do not eject: keep Astryx's accessible states, scales and icon registry.
// System fonts keep the Android build self-contained; no Google Fonts import.
export const sourcebookTheme = defineTheme({
  name: 'sourcebook',
  extends: matchaTheme,
  typography: {
    body: {family: 'system-ui', fallbacks: 'sans-serif'},
    heading: {family: 'system-ui', fallbacks: 'sans-serif'},
    code: {family: 'ui-monospace', fallbacks: 'monospace'},
  },
  components: {
    button: {base: {borderRadius: 'var(--radius-element)'}},
    card: {base: {borderRadius: 'var(--radius-container)'}},
  },
  tokens: {
    '--font-family-body': 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    '--font-family-heading': 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    '--font-family-code': 'ui-monospace, monospace',
  },
  motion: {tempo: 0.9, character: 'expressive'},
});
