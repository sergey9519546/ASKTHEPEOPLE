import fs from 'fs';
import path from 'path';

const filePath = path.join(process.cwd(), 'frontend', 'src', 'components', 'GraphPanel.vue');
let content = fs.readFileSync(filePath, 'utf8');

// Replace D3 colors
content = content.replace(/\.attr\("stroke", "#e2e8f0"\)/g, `.attr("stroke", "rgba(255, 255, 255, 0.2)")`);
content = content.replace(/\.attr\("fill", "#334155"\)/g, `.attr("fill", "rgba(255, 255, 255, 0.85)")`);
content = content.replace(/\.attr\("stroke", "#ffffff"\)/g, `.attr("stroke", "rgba(0, 0, 0, 0.4)")`);

const newStyles = `
<style scoped>
.graph-panel-workbench {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  position: relative;
  overflow: hidden;
}

.panel-header-block {
  height: 50px;
  padding: 0 16px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--surface-color);
  backdrop-filter: blur(16px);
}

.panel-label {
  font-weight: 700;
  font-size: 13px;
  letter-spacing: -0.2px;
  color: var(--text-primary);
}

.header-right {
  display: flex;
  gap: 8px;
}

.viewport-container {
  flex-grow: 1;
  position: relative;
  overflow: hidden;
  background: var(--bg-color);
}

.graph-canvas-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
}

.graph-svg-element {
  width: 100%;
  height: 100%;
  display: block;
}

.status-overlay-hint {
  position: absolute;
  top: 16px;
  left: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 69, 0, 0.1);
  backdrop-filter: blur(8px);
  border: 1px solid var(--accent-color);
  padding: 6px 12px;
  border-radius: 20px;
  z-index: 10;
  box-shadow: 0 0 15px rgba(255, 69, 0, 0.2);
}
.completion-hint {
  background: rgba(16, 185, 129, 0.1);
  border-color: #10b981;
  box-shadow: 0 0 15px rgba(16, 185, 129, 0.2);
}
.status-msg {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 9px;
  color: var(--text-primary);
  letter-spacing: 0.5px;
}
.status-icon-box {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #10b981;
  font-weight: 700;
  font-size: 10px;
}
.pulse-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent-color);
  animation: pulse 1s infinite;
}
@keyframes pulse {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 69, 0, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(255, 69, 0, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 69, 0, 0); }
}
.hint-close {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  margin-left: 4px;
}
.hint-close:hover {
  color: var(--text-primary);
}

.entity-detail-panel {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 280px;
  max-height: calc(100% - 32px);
  background: var(--surface-color);
  backdrop-filter: blur(16px);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  z-index: 100;
  color: var(--text-primary);
}

.detail-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  gap: 8px;
}
.detail-category {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 9px;
  color: var(--text-secondary);
}
.type-badge {
  font-size: 8px;
  font-weight: 700;
  color: #fff;
  padding: 2px 6px;
  border-radius: 4px;
  text-transform: uppercase;
}
.close-detail-btn {
  background: none;
  border: none;
  font-size: 16px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: color 0.15s ease;
  margin-left: auto;
}
.close-detail-btn:hover {
  color: var(--accent-color);
}

.detail-scroll-area {
  padding: 16px;
  overflow-y: auto;
  flex-grow: 1;
}
.attr-row {
  margin-bottom: 12px;
}
.attr-row label {
  display: block;
  font-weight: 700;
  font-size: 9px;
  color: var(--text-secondary);
  margin-bottom: 2px;
  text-transform: uppercase;
}
.attr-value {
  font-weight: 600;
  font-size: 12px;
  color: var(--text-primary);
}
.attr-value.title {
  font-size: 14px;
  font-weight: 700;
}
.attr-value.mono {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--text-secondary);
  word-break: break-all;
}

.attr-section {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
}
.section-label {
  font-weight: 700;
  font-size: 9px;
  margin-bottom: 8px;
  color: var(--text-secondary);
  text-transform: uppercase;
}
.summary-box {
  font-size: 11px;
  line-height: 1.6;
  background: rgba(0, 0, 0, 0.3);
  padding: 10px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
}

.graph-ui-overlays {
  position: absolute;
  bottom: 16px;
  left: 0;
  right: 0;
  padding: 0 16px;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  pointer-events: none;
}

.type-legend {
  padding: 10px 12px;
  max-width: 240px;
  background: var(--surface-color);
  backdrop-filter: blur(16px);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  pointer-events: auto;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
}
.legend-header {
  font-weight: 700;
  font-size: 9px;
  color: var(--text-secondary);
  margin-bottom: 6px;
}
.legend-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 100px;
  overflow-y: auto;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}
.color-swatch {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.type-name {
  font-weight: 600;
  font-size: 9px;
  color: var(--text-primary);
}

.view-controls {
  padding: 8px 12px;
  background: var(--surface-color);
  backdrop-filter: blur(16px);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  pointer-events: auto;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
}
.control-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.control-label {
  font-weight: 700;
  font-size: 9px;
  color: var(--text-secondary);
}

.btn-action {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-color);
  padding: 6px 12px;
  font-weight: 600;
  font-size: 11px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--text-primary);
}
.btn-action:hover {
  background: rgba(255, 69, 0, 0.1);
  border-color: var(--accent-color);
  color: var(--accent-color);
}
.btn-action.square {
  padding: 6px;
  width: 28px;
  height: 28px;
  justify-content: center;
}
.is-spinning {
  animation: spin 0.8s infinite linear;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Switch styling */
.switch-control {
  position: relative;
  width: 28px;
  height: 16px;
  display: inline-block;
}
.switch-control input {
  opacity: 0;
  width: 0;
  height: 0;
}
.switch-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(255, 255, 255, 0.2);
  border-radius: 34px;
  transition: .2s;
}
.switch-slider:before {
  position: absolute;
  content: "";
  height: 10px;
  width: 10px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  border-radius: 50%;
  transition: .2s;
}
input:checked + .switch-slider {
  background-color: var(--accent-color);
}
input:checked + .switch-slider:before {
  transform: translateX(12px);
}

.state-placeholder {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: var(--text-secondary);
}
.spinner-large {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-color);
  border-top-color: var(--accent-color);
  border-radius: 50%;
  animation: spin 1s infinite linear;
}
.geometric-shape {
  width: 24px;
  height: 24px;
  border: 2px solid var(--border-color);
  border-radius: 4px;
  transform: rotate(45deg);
}

.scrollbar-thin::-webkit-scrollbar {
  width: 4px;
}
.scrollbar-thin::-webkit-scrollbar-track {
  background: transparent;
}
.scrollbar-thin::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 2px;
}
</style>
`;

content = content.replace(/<style scoped>[\s\S]*<\/style>/, newStyles);
fs.writeFileSync(filePath, content, 'utf8');
console.log('Updated GraphPanel.vue CSS and D3 styling.');
