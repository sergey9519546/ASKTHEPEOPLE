<template>
  <router-view />
</template>

<script setup>
// Use Vue Router to manage navigation
</script>

<style>
:root {
  /* Bauhaus Design System - Primary Palette */
  --bauhaus-red: #e63946;
  --bauhaus-blue: #1d3557;
  --bauhaus-yellow: #ffb703;
  --atp-black: #000000;
  --atp-white: #ffffff;
  --atp-light-gray: #f9f9f9;
  --background: #f8f9fa;
  --surface: #ffffff;
  --on-background: #0f0f0f;
  --on-surface-variant: #2d2d2d;

  /* Semantic Variables - Bauhaus Mapping */
  --bg-color: var(--background);
  --surface-color: var(--surface);
  --border-color: var(--atp-black);
  --border-width: 2px;
  --border-width-heavy: 4px;

  --text-primary: var(--atp-black);
  --text-secondary: #555555;
  --accent-color: var(--bauhaus-red);
  --accent-secondary: var(--bauhaus-blue);
  --accent-tertiary: var(--bauhaus-yellow);

  /* Typography */
  --font-mono: "JetBrains Mono", monospace;
  --font-sans: "Space Grotesk", sans-serif;

  /* Geometry - Brutalist (Zero Radius) */
  --radius-none: 0px;
  --radius-sm: 0px;
  --radius-md: 0px;
  --radius-lg: 0px;

  /* Spacing */
  --gap: 24px;
  --grid-unit: 40px;
}

/* Custom Selection Color - Bauhaus */
::selection {
  background: var(--bauhaus-red);
  color: var(--atp-white);
}

/* Utility Classes - Bauhaus Palette */
.bg-accent-red {
  background-color: var(--bauhaus-red) !important;
}
.text-accent-red {
  color: var(--bauhaus-red) !important;
}
.bg-accent-blue {
  background-color: var(--bauhaus-blue) !important;
}
.text-accent-blue {
  color: var(--bauhaus-blue) !important;
}
.bg-accent-yellow {
  background-color: var(--bauhaus-yellow) !important;
}
.text-accent-yellow {
  color: var(--bauhaus-yellow) !important;
}
/* Legacy support - map old classes to new colors */
.bg-accent-cyan {
  background-color: var(--bauhaus-red) !important;
}
.text-accent-cyan {
  color: var(--bauhaus-red) !important;
}
.bg-accent-purple {
  background-color: var(--bauhaus-blue) !important;
}
.text-accent-purple {
  color: var(--bauhaus-blue) !important;
}
.bg-accent-green {
  background-color: var(--bauhaus-yellow) !important;
}
.text-accent-green {
  color: var(--bauhaus-yellow) !important;
}

/* Global Style Reset */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  background-color: var(--bg-color);
  color: var(--text-primary);
}

#app {
  font-family: var(--font-sans);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Scrollbar - Modernist Brutal */
::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}

::-webkit-scrollbar-track {
  background: var(--atp-white);
  border-left: var(--border-width) solid var(--atp-black);
}

::-webkit-scrollbar-thumb {
  background: var(--atp-black);
  border: 1px solid var(--atp-white);
}

::-webkit-scrollbar-thumb:hover {
  background: var(--bauhaus-red);
}

/* Global Button - Bauhaus Brutalist */
button {
  font-family: var(--font-mono);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  padding: 12px 24px;
  border: var(--border-width-heavy) solid var(--atp-black);
  background: var(--atp-white);
  color: var(--atp-black);
  border-radius: var(--radius-none);
  transition: all 0.15s ease;
  position: relative;
}

button:hover {
  background: var(--atp-black);
  color: var(--atp-white);
  transform: translate(-4px, -4px);
  box-shadow: 8px 8px 0px var(--bauhaus-red);
}

button:active {
  transform: translate(0, 0);
  box-shadow: none;
}

button:disabled {
  background: #eee;
  color: #aaa;
  border-color: #aaa;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}
</style>
