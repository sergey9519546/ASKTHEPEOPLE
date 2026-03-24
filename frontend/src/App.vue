<template>
  <router-view />
</template>

<script setup>
// Use Vue Router to manage navigation
</script>

<style>
:root {
  /* Modernist Brutal - "Creative Studio" Palette */
  --atp-black: #000000;
  --atp-white: #ffffff;
  --atp-cyan: #22d3ee;
  --atp-purple: #a855f7;
  --atp-green: #4ade80;
  --atp-light-gray: #f9f9f9;

  /* Semantic Variables */
  --bg-color: var(--atp-white);
  --surface-color: var(--atp-white);
  --border-color: var(--atp-black);
  --border-width: 2px;

  --text-primary: var(--atp-black);
  --text-secondary: #555555;
  --accent-color: var(--atp-cyan); /* Default accent is now Cyan */

  /* Typography */
  --font-mono: "JetBrains Mono", monospace;
  --font-sans: "Space Grotesk", "Inter", sans-serif;

  /* Geometry */
  --radius-none: 0px;
  --radius-sm: 0px;
  --radius-md: 0px;
  --radius-lg: 0px;

  /* Spacing */
  --gap: 24px;
}

/* Custom Selection Color */
::selection {
  background: var(--atp-cyan);
  color: var(--atp-black);
}

/* Utility Classes for usage */
.bg-accent-cyan { background-color: var(--atp-cyan) !important; }
.text-accent-cyan { color: var(--atp-cyan) !important; }
.bg-accent-purple { background-color: var(--atp-purple) !important; }
.text-accent-purple { color: var(--atp-purple) !important; }
.bg-accent-green { background-color: var(--atp-green) !important; }
.text-accent-green { color: var(--atp-green) !important; }

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
  background: var(--atp-cyan);
}

/* Global Button - Modernist Brutal */
button {
  font-family: var(--font-mono);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  padding: 12px 24px;
  border: var(--border-width) solid var(--atp-black);
  background: var(--atp-white);
  color: var(--atp-black);
  border-radius: var(--radius-none);
  transition: all 0.1s;
  position: relative;
}

button:hover {
  background: var(--atp-black);
  color: var(--atp-white);
  transform: translate(-2px, -2px);
  box-shadow: 4px 4px 0px var(--atp-cyan);
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
