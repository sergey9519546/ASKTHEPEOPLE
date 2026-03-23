<template>
  <router-view />
</template>

<script setup>
// 使用 Vue Router 来管理页面
</script>

<style>
:root {
  /* Bauhaus Core Palette */
  --bau-bg: #F0EFEA;      /* Warm off-white / Paper */
  --bau-black: #1A1A1A;   /* Deep charcoal */
  --bau-red: #E14B3B;     /* Primary vermillion */
  --bau-yellow: #F4D03F;  /* Primary cadmium yellow */
  --bau-blue: #2E5A88;    /* Primary cobalt blue */
  
  /* Semantic Variables - Bauhaus Transition */
  --bg-color: var(--bau-bg);
  --surface-color: #FFFFFF;
  --surface-hover: #E9E8E3;
  --border-color: var(--bau-black);
  --border-width: 2px;
  
  --text-primary: var(--bau-black);
  --text-secondary: #4A4A4A;
  --accent-color: var(--bau-red);
  
  /* Typography - Clean Geometric Sans */
  --font-mono: "JetBrains Mono", monospace;
  --font-sans: "Inter", "Helvetica Neue", "Arial", sans-serif;
  
  /* Geometry - Sharp Edges */
  --radius-sm: 0px;
  --radius-md: 0px;
  --radius-lg: 0px;

  /* Spacing & Layout */
  --gap: 24px;
}

/* 全局样式重置 */
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

/* 滚动条样式 - Bauhaus 简约 */
::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}

::-webkit-scrollbar-track {
  background: var(--bau-bg);
  border-left: var(--border-width) solid var(--bau-black);
}

::-webkit-scrollbar-thumb {
  background: var(--bau-black);
  border: 2px solid var(--bau-bg);
}

::-webkit-scrollbar-thumb:hover {
  background: var(--bau-red);
}

/* 全局按钮样式 - Bauhaus 坚硬矩形 */
button {
  font-family: inherit;
  cursor: pointer;
  transition: all 0.1s step-end;
  border: var(--border-width) solid var(--border-color);
  background: var(--surface-color);
  color: var(--text-primary);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

button:hover {
  background: var(--bau-yellow);
  transform: translate(-2px, -2px);
  box-shadow: 4px 4px 0 var(--bau-black);
}

button:active {
  transform: translate(0, 0);
  box-shadow: none;
}
</style>
