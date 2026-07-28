import fs from 'fs';
import path from 'path';

const filePath = path.join(process.cwd(), 'frontend', 'src', 'components', 'HistoryDatabase.vue');
let content = fs.readFileSync(filePath, 'utf8');

const newStyles = `
<style scoped>
.simulation-history-workbench {
  position: relative;
  width: 100%;
  min-height: 380px;
  margin-top: 60px;
  padding: 40px 0;
  background: transparent;
  border-top: 1px solid var(--border-color);
}

.section-title-area {
  text-align: center;
  margin-bottom: 32px;
}

.section-label {
  font-weight: 700;
  font-size: 1.5rem;
  letter-spacing: -0.5px;
  color: var(--text-primary);
}

.section-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.workbench-cards-grid {
  position: relative;
  display: flex;
  justify-content: center;
  padding: 0 40px;
  transition: min-height 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}

.simulation-card {
  position: absolute;
  width: 280px;
  height: 280px;
  border: 1px solid var(--border-color);
  background: var(--surface-color);
  backdrop-filter: blur(16px);
  border-radius: var(--radius-md);
  padding: 16px;
  cursor: pointer;
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
}

.simulation-card:hover {
  box-shadow: 0 12px 40px 0 rgba(255, 69, 0, 0.2);
  transform: translate3d(0, -6px, 0) scale(1.02) !important;
  z-index: 2000 !important;
  border-color: var(--accent-color);
}

.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-color);
}

.simulation-id {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 11px;
  color: var(--text-primary);
}

.capability-flags {
  display: flex;
  gap: 4px;
}
.flag {
  width: 20px;
  height: 20px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 8px;
  font-weight: 700;
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.03);
}
.flag.active {
  background: var(--accent-color);
  color: #fff;
  border-color: var(--accent-color);
  box-shadow: 0 0 8px var(--accent-glow);
}

.card-preview-area {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  height: 68px;
  margin-bottom: 12px;
  padding: 8px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.file-strip {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  margin-bottom: 4px;
  padding: 2px 6px;
}

.type-tag {
  font-family: var(--font-mono);
  font-size: 7px;
  font-weight: 700;
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-secondary);
  padding: 1px 3px;
  border-radius: 2px;
}
.type-tag.pdf { background: rgba(239, 68, 68, 0.2); color: #f87171; }
.type-tag.xls { background: rgba(16, 185, 129, 0.2); color: #34d399; }
.type-tag.doc { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
.type-tag.ppt { background: rgba(245, 158, 11, 0.2); color: #fbbf24; }

.filename-text {
  font-size: 9px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--text-primary);
}

.more-files-indicator {
  font-size: 8px;
  font-weight: 600;
  color: var(--text-secondary);
  text-align: right;
  margin-top: 2px;
}

.empty-files-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}
.empty-text {
  font-size: 9px;
  font-weight: 500;
  color: var(--text-secondary);
}

.card-content-block {
  flex-grow: 1;
}
.requirement-title {
  font-weight: 700;
  font-size: 13px;
  margin-bottom: 4px;
  color: var(--text-primary);
}
.requirement-preview {
  font-size: 10px;
  line-height: 1.5;
  height: 30px;
  overflow: hidden;
  color: var(--text-secondary);
}

.card-footer-row {
  margin-top: 12px;
  padding-top: 8px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.timestamp-group {
  display: flex;
  flex-direction: column;
  font-family: var(--font-mono);
  font-size: 8px;
  font-weight: 500;
  color: var(--text-secondary);
}
.execution-progress {
  display: flex;
  align-items: center;
  gap: 4px;
  font-weight: 700;
  font-size: 9px;
}
.status-indicator {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.state-complete {
  color: #34d399;
}
.state-complete .status-indicator {
  background: #34d399;
  box-shadow: 0 0 6px rgba(52, 211, 153, 0.5);
}
.state-active {
  color: var(--accent-color);
}
.state-active .status-indicator {
  background: var(--accent-color);
  animation: pulse 1s infinite;
  box-shadow: 0 0 6px var(--accent-glow);
}
.state-pending {
  color: var(--text-secondary);
}
.state-pending .status-indicator {
  background: var(--text-secondary);
}

.workbench-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 40px;
  color: var(--text-secondary);
}
.spinner {
  width: 24px;
  height: 24px;
  border: 2.5px solid var(--border-color);
  border-top-color: var(--accent-color);
  border-radius: 50%;
  animation: spin 1s infinite linear;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.loading-label {
  font-weight: 600;
  font-size: 11px;
}

/* Modal Styles */
.workbench-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(12px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.modal-card {
  background: var(--bg-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  width: 580px;
  max-width: 90vw;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.8);
  display: flex;
  flex-direction: column;
  max-height: 90vh;
  color: var(--text-primary);
}

.modal-header-block {
  padding: 24px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.id-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.modal-sim-id {
  font-weight: 700;
  font-size: 20px;
  color: var(--text-primary);
}
.modal-badges {
  display: flex;
  align-items: center;
  gap: 10px;
}
.modal-status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
  font-size: 9px;
  padding: 2px 8px;
  border-radius: 20px;
  border: 1px solid var(--border-color);
  background: rgba(255, 255, 255, 0.05);
}
.creation-stamp {
  font-size: 10px;
  color: var(--text-secondary);
}

.close-modal-btn {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
  border: none;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}
.close-modal-btn:hover {
  background: rgba(255, 69, 0, 0.2);
  color: var(--accent-color);
}

.modal-scroll-area {
  padding: 24px;
  overflow-y: auto;
  flex-grow: 1;
}
.modal-section {
  margin-bottom: 24px;
}
.section-heading {
  font-weight: 700;
  font-size: 10px;
  letter-spacing: 0.5px;
  color: var(--text-secondary);
  margin-bottom: 8px;
  text-transform: uppercase;
}
.requirement-box {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 16px;
  font-size: 13px;
  line-height: 1.6;
  background: rgba(0, 0, 0, 0.3);
  color: var(--text-primary);
}

.modal-file-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.modal-file-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.03);
  color: var(--text-primary);
}
.file-extension-pill {
  font-weight: 700;
  font-size: 8px;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-secondary);
}
.file-extension-pill.pdf { background: rgba(239, 68, 68, 0.2); color: #f87171; }
.file-extension-pill.xls { background: rgba(16, 185, 129, 0.2); color: #34d399; }
.file-extension-pill.doc { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
.file-extension-pill.ppt { background: rgba(245, 158, 11, 0.2); color: #fbbf24; }

.modal-playback-divider {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 24px;
  position: relative;
}
.modal-playback-divider::before {
  content: "";
  position: absolute;
  left: 24px;
  right: 24px;
  height: 1px;
  background: var(--border-color);
  top: 50%;
  z-index: 1;
}
.playback-label {
  font-weight: 700;
  font-size: 9px;
  letter-spacing: 1px;
  text-transform: uppercase;
  background: var(--bg-color);
  color: var(--text-secondary);
  padding: 0 10px;
  position: relative;
  z-index: 2;
}

.modal-navigation-grid {
  display: flex;
  gap: 12px;
  padding: 24px;
}
.nav-btn {
  flex: 1;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.05);
  padding: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: var(--text-primary);
}
.nav-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(255, 69, 0, 0.2);
  border-color: var(--accent-color);
  background: rgba(255, 69, 0, 0.1);
}
.nav-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
  background: rgba(0, 0, 0, 0.2);
}

.step-num {
  font-size: 8px;
  font-weight: 700;
  color: var(--text-secondary);
}
.action-label {
  font-weight: 700;
  font-size: 11px;
  color: var(--text-primary);
}

.modal-notice {
  padding: 0 24px 24px;
  text-align: center;
}
.modal-notice p {
  font-size: 10px;
  font-weight: 500;
  color: var(--text-secondary);
}

/* Transitions */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.25s ease;
}
.modal-fade-enter-active .modal-card,
.modal-fade-leave-active .modal-card {
  transition: transform 0.25s ease, opacity 0.25s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
.modal-fade-enter-from .modal-card,
.modal-fade-leave-to .modal-card {
  opacity: 0;
  transform: scale(0.95);
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
console.log('Updated HistoryDatabase.vue CSS.');
