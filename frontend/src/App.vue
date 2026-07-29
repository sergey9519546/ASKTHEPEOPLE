<template>
  <router-view />
  <ToastContainer />

  <!-- Global crash banner (Layer 1 safety net) -->
  <div v-if="hasCrashed" class="crash-overlay">
    <div class="crash-banner">
      <div class="crash-message">
        <span class="crash-title">Something went wrong</span>
        <span class="crash-subtitle">An unexpected error occurred. Reload to continue.</span>
      </div>
      <button class="crash-reload" @click="reloadPage">Reload</button>
    </div>
  </div>
</template>

<script setup>
import ToastContainer from './components/ToastContainer.vue';
import { hasCrashed } from './composables/useCrashState.js';

function reloadPage() {
  window.location.reload();
}
</script>

<style>
/* ==========================================================================
   ASKTHEPEOPLE — Simulation Command Center
   Aesthetic: Bloomberg terminal × editorial serif × stripe-docs clarity.
   Solid dark, hairline borders, single bold accent, no glass.
   Self-hosted fonts loaded via design-tokens.css (@fontsource).
   ========================================================================== */

:root {
  /* Pure dark surfaces — NO transparency/blur */
  --bg-void: #000000;
  --bg-base: #0a0a0a;
  --bg-panel: #111111;
  --bg-elevated: #161616;
  --bg-input: #0d0d0d;
  --bg-hover: #1c1c1c;

  /* Hairline border tokens */
  --line: #1f1f1f;
  --line-strong: #2a2a2a;
  --line-active: #3a3a3a;

  /* Text hierarchy */
  --text-void: #ededed;
  --text-primary: #d4d4d4;
  --text-secondary: #8a8a8a;
  --text-muted: #595959;
  --text-dim: #3f3f3f;

  /* Single bold accent — electric lime for live/active state.
     This is the ONLY chromatic accent in the system. Everything else
     uses neutral grays. This single-color discipline is what gives
     the design its distinctive character vs the multi-color rainbow
     that defines generic AI SaaS. */
  --accent: #a3e635;
  --accent-bright: #bef264;
  --accent-dim: #65a30d;
  --accent-ink: #1a2e05;        /* accent on dark for text/shadow use */

  /* Status colors — used SPARINGLY, only for true state indicators */
  --status-live: #a3e635;
  --status-warn: #f59e0b;
  --status-error: #ef4444;
  --status-info: #60a5fa;

  /* Typography */
  --font-serif: 'Fraunces', Georgia, serif;
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'JetBrains Mono', 'SF Mono', Menlo, monospace;

  /* Geometry — sharp by default */
  --radius-xs: 0px;
  --radius-sm: 2px;
  --radius-md: 4px;
  --radius-full: 9999px;        /* only for status dots */

  /* Legacy aliases */
  --bg-color: var(--bg-void);
  --surface-color: var(--bg-panel);
  --surface-hover: var(--bg-hover);
  --border-color: var(--line);
  --border-color-hover: var(--line-active);
  --accent-color: var(--accent);
  --accent-secondary: var(--accent);
  --accent-tertiary: var(--accent);
  --accent-amber: var(--status-warn);
  --accent-cyan: var(--status-info);
  --atp-light-gray: var(--bg-elevated);
  --text-color: var(--text-primary);
  --shadow-glass: none;
  --shadow-glass-hover: none;
  --shadow-card: none;
  --bg-dark: var(--bg-void);
  --bg-card: var(--bg-panel);
  --bg-card-hover: var(--bg-elevated);
  --bg-glass: var(--bg-panel);
  --bg-glass-heavy: var(--bg-panel);
  --primary: var(--accent);
  --accent-purple: var(--accent);
  --accent-emerald: var(--accent);
  --accent-rose: var(--status-error);
  --glow-primary: none;
  --glow-purple: none;
  --glow-emerald: none;
}

/* Global Reset — NO rounded corners anywhere by default */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

::selection {
  background: var(--accent);
  color: var(--accent-ink);
}

html, body {
  width: 100%;
  min-height: 100vh;
  background-color: var(--bg-void);
  color: var(--text-void);
  font-family: var(--font-sans);
  font-feature-settings: 'ss01', 'cv11';
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  overflow-x: hidden;
}

/* Subtle dot grid — visible but quiet, gives surface texture */
body::before {
  content: '';
  position: fixed;
  inset: 0;
  background-image: radial-gradient(circle, #1a1a1a 1px, transparent 1px);
  background-size: 24px 24px;
  opacity: 0.4;
  pointer-events: none;
  z-index: 0;
}

#app {
  position: relative;
  z-index: 1;
}

/* Scrollbar — thin, dark, minimal */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-void); }
::-webkit-scrollbar-thumb {
  background: #2a2a2a;
  border-radius: 0;
}
::-webkit-scrollbar-thumb:hover { background: #3a3a3a; }

/* ==========================================================================
   TYPOGRAPHY UTILITIES
   ========================================================================== */

.serif {
  font-family: var(--font-serif);
  font-feature-settings: 'ss01';
  font-optical-sizing: auto;
}

.mono {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.tnum {
  font-variant-numeric: tabular-nums;
  font-family: var(--font-mono);
}

.eyebrow {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  color: var(--text-muted);
}

.label {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--text-secondary);
}

/* ==========================================================================
   BUTTONS — sharp edges, monochrome, accent on primary
   ========================================================================== */

button, .btn {
  font-family: var(--font-sans);
  font-weight: 500;
  cursor: pointer;
  padding: 9px 16px;
  border-radius: 0;
  border: 1px solid var(--line-strong);
  background: var(--bg-elevated);
  color: var(--text-primary);
  transition: background 0.1s ease, border-color 0.1s ease, color 0.1s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  outline: none;
  font-size: 13px;
  letter-spacing: -0.01em;
}

button:hover, .btn:hover {
  background: var(--bg-hover);
  border-color: var(--line-active);
  color: var(--text-void);
}

button:active, .btn:active {
  background: var(--bg-elevated);
  transform: translateY(1px);
}

button.btn-primary, .btn-primary {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--accent-ink);
  font-weight: 600;
}

button.btn-primary:hover, .btn-primary:hover {
  background: var(--accent-bright);
  border-color: var(--accent-bright);
  color: var(--accent-ink);
}

button:disabled, .btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* ==========================================================================
   INPUTS — flat, dark, with bottom-border-only accent on focus
   ========================================================================== */

input[type="text"], input[type="password"], textarea, select {
  font-family: var(--font-sans) !important;
  font-size: 13px !important;
  border: 1px solid var(--line) !important;
  border-radius: 0 !important;
  background: var(--bg-input) !important;
  color: var(--text-void) !important;
  padding: 10px 14px !important;
  outline: none !important;
  transition: border-color 0.1s ease !important;
}

input[type="text"]:focus, input[type="password"]:focus, textarea:focus, select:focus {
  border-color: var(--accent) !important;
}

/* ==========================================================================
   STATUS & CHIPS — sharp pills with dot prefix
   ========================================================================== */

.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 8px;
  border: 1px solid var(--line);
  background: var(--bg-panel);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-secondary);
  border-radius: 0;
}

.chip-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-muted);
  flex-shrink: 0;
}

.chip-dot.live { background: var(--status-live); }
.chip-dot.warn { background: var(--status-warn); }
.chip-dot.error { background: var(--status-error); }
.chip-dot.info { background: var(--status-info); }

.chip-live {
  border-color: var(--accent-dim);
  color: var(--accent-bright);
}
.chip-live .chip-dot {
  background: var(--status-live);
  animation: pulseDot 1.5s ease-in-out infinite;
}

@keyframes pulseDot {
  0%, 100% { opacity: 1; box-shadow: 0 0 0 0 var(--accent); }
  50% { opacity: 0.6; box-shadow: 0 0 0 4px transparent; }
}

/* ==========================================================================
   DIVIDERS & RULES
   ========================================================================== */

hr {
  border: none;
  border-top: 1px solid var(--line);
  margin: 16px 0;
}

.rule-thick {
  border-top: 1px solid var(--line-strong);
}

/* ==========================================================================
   PANELS — flat, with hairline borders, no shadows
   ========================================================================== */

.panel {
  background: var(--bg-panel);
  border: 1px solid var(--line);
  border-radius: 0;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--line);
  background: var(--bg-elevated);
}

/* ==========================================================================
   STATUS / SIGNAL BARS
   ========================================================================== */

.signal-bar {
  height: 2px;
  background: var(--line);
  position: relative;
  overflow: hidden;
}

.signal-bar-fill {
  height: 100%;
  background: var(--accent);
  transition: width 0.3s ease;
}

/* ==========================================================================
   DATA DISPLAY — monospace tabular nums
   ========================================================================== */

.data-value {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  font-weight: 500;
  color: var(--text-void);
}

.data-label {
  font-family: var(--font-mono);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
}

/* ==========================================================================
   ANIMATIONS
   ========================================================================== */

@keyframes scanline {
  0% { transform: translateY(-100%); }
  100% { transform: translateY(100vh); }
}

@keyframes blink {
  0%, 49% { opacity: 1; }
  50%, 100% { opacity: 0; }
}

.animate-fade-in {
  animation: fadeIn 0.2s ease-out forwards;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* ==========================================================================
   GLOBAL CRASH OVERLAY — kept functional, restyled to match aesthetic
   ========================================================================== */

.crash-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.95);
}

.crash-banner {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 20px 28px;
  background: var(--bg-panel);
  border: 1px solid var(--status-error);
  border-radius: 0;
  color: var(--text-void);
  max-width: 600px;
}

.crash-message {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.crash-title {
  font-family: var(--font-serif);
  font-weight: 600;
  font-size: 17px;
  color: var(--text-void);
}

.crash-subtitle {
  font-family: var(--font-sans);
  font-size: 13px;
  color: var(--text-secondary);
}

.crash-reload {
  font-family: var(--font-mono) !important;
  font-weight: 600 !important;
  padding: 9px 18px !important;
  background: var(--status-error) !important;
  color: #ffffff !important;
  border: 1px solid var(--status-error) !important;
  border-radius: 0 !important;
  cursor: pointer;
  white-space: nowrap;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 11px !important;
}

.crash-reload:hover {
  background: #dc2626 !important;
}
</style>
