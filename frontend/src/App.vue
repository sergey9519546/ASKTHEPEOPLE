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
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');

:root {
  /* Modern Clean Palette */
  --bauhaus-red: #f43f5e;       /* Elegant rose/coral */
  --bauhaus-blue: #3b82f6;      /* Modern royal blue */
  --bauhaus-yellow: #10b981;    /* Emerald green */
  --atp-black: #0f172a;         /* Slate-900 */
  --atp-white: #ffffff;
  --atp-light-gray: #f8fafc;    /* Slate-50 */
  
  --background: #fcfcfc;
  --surface: #ffffff;
  --on-background: #0f172a;
  --on-surface-variant: #475569; /* Slate-600 */

  /* Semantic Layout Variables */
  --bg-color: var(--background);
  --surface-color: var(--surface);
  --border-color: #e2e8f0;       /* Soft border */
  --border-width: 1px;
  --border-width-heavy: 1px;

  --text-primary: var(--atp-black);
  --text-secondary: var(--on-surface-variant);
  --accent-color: var(--bauhaus-red);
  --accent-secondary: var(--bauhaus-blue);
  --accent-tertiary: var(--bauhaus-yellow);

  /* Typography */
  --font-mono: "JetBrains Mono", monospace;
  --font-sans: "Outfit", sans-serif;

  /* Geometry - Smooth and rounded */
  --radius-none: 12px;
  --radius-sm: 8px;
  --radius-md: 14px;
  --radius-lg: 24px;

  /* Spacing */
  --gap: 24px;
  --grid-unit: 24px;
}

/* Custom Selection Color */
::selection {
  background: rgba(244, 63, 94, 0.15);
  color: var(--accent-color);
}

/* Global Reset */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  background-color: var(--bg-color);
  color: var(--text-primary);
  font-family: var(--font-sans);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Translucent & Smooth Scrollbars */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 10px;
}

::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

/* Modern Minimalist Button Reset */
button, .btn {
  font-family: var(--font-sans);
  font-weight: 500;
  text-transform: none;
  letter-spacing: normal;
  cursor: pointer;
  padding: 10px 20px;
  border: 1px solid var(--border-color) !important;
  background: var(--surface);
  color: var(--text-primary);
  border-radius: var(--radius-sm) !important;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03) !important;
  transform: none !important;
}

button:hover, .btn:hover {
  background: var(--atp-light-gray) !important;
  border-color: #cbd5e1 !important;
  color: var(--text-primary) !important;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03) !important;
  transform: translateY(-1px) !important;
}

button:active, .btn:active {
  transform: translateY(0) !important;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03) !important;
}

button:disabled, .btn:disabled {
  background: #f1f5f9 !important;
  color: #94a3b8 !important;
  border-color: #e2e8f0 !important;
  cursor: not-allowed;
  transform: none !important;
  box-shadow: none !important;
}

/* Global Card & Border Redefinitions (Override Brutalism) */
.border-black, .border-4, .border-2, .border-r-4, .border-b-4, .border-t-4 {
  border-color: var(--border-color) !important;
  border-width: 1px !important;
}

/* Soft Modern Shadows replacing blocky offset shadows */
[class*="shadow-["], [class*="shadow-sm"], [class*="shadow-md"] {
  box-shadow: 0 10px 30px -10px rgba(15, 23, 42, 0.04), 0 1px 3px -1px rgba(15, 23, 42, 0.02) !important;
}

/* Layout Specific Overrides */
.atelier-grid, .content-area {
  background-image: radial-gradient(#e2e8f0 1px, transparent 1px) !important;
  background-size: var(--grid-unit) var(--grid-unit) !important;
  background-color: var(--background) !important;
}

/* Custom Overrides for Color Badges/Fills */
.bg-bauhaus-red {
  background-color: var(--bauhaus-red) !important;
  color: white !important;
}
.text-bauhaus-red {
  color: var(--bauhaus-red) !important;
}
.bg-bauhaus-blue {
  background-color: var(--bauhaus-blue) !important;
  color: white !important;
}
.text-bauhaus-blue {
  color: var(--bauhaus-blue) !important;
}
.bg-bauhaus-yellow {
  background-color: var(--atp-light-gray) !important;
  color: var(--text-primary) !important;
}
.text-bauhaus-yellow {
  color: #d97706 !important; /* Soft Amber */
}

/* Inputs & Textareas */
input[type="text"], textarea, select {
  font-family: var(--font-sans) !important;
  font-size: 15px !important;
  border: 1px solid var(--border-color) !important;
  border-radius: var(--radius-sm) !important;
  background: var(--surface) !important;
  padding: 12px 16px !important;
  color: var(--text-primary) !important;
  transition: all 0.2s ease !important;
  outline: none !important;
}

input[type="text"]:focus, textarea:focus, select:focus {
  border-color: var(--accent-secondary) !important;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
}

/* Rounded Cards */
.panel-wrapper, .bg-white {
  border-radius: var(--radius-md) !important;
}

/* Animation utilities */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-fade-in {
  animation: fadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

/* Global crash banner (Layer 1 safety net) — dark glass theme */
.crash-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.crash-banner {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 24px 32px;
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--radius-md);
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.35);
  color: #ffffff;
}

.crash-message {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.crash-title {
  font-family: var(--font-sans);
  font-weight: 600;
  font-size: 17px;
  color: #ffffff;
}

.crash-subtitle {
  font-family: var(--font-sans);
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
}

.crash-reload {
  font-family: var(--font-sans) !important;
  font-weight: 500 !important;
  padding: 10px 22px !important;
  background: var(--bauhaus-red) !important;
  color: #ffffff !important;
  border: 1px solid var(--bauhaus-red) !important;
  border-radius: var(--radius-sm) !important;
  cursor: pointer;
  white-space: nowrap;
}

.crash-reload:hover {
  background: #e11d48 !important;
  border-color: #e11d48 !important;
  color: #ffffff !important;
}
</style>
