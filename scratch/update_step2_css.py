import re

with open("C:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/frontend/src/components/Step2EnvSetup.vue", "r", encoding="utf-8") as f:
    content = f.read()

new_style = """<style scoped>
.env-setup-panel {
  height: 100%;
  background-color: transparent;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  font-family: var(--font-sans);
  color: var(--paper);
}

.scroll-container {
  flex: 1;
  overflow-y: auto;
  padding: clamp(1.5rem, 3vw, 3rem);
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

/* Preparation Banner */
.preparation-banner {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 1.5rem;
  align-items: center;
  padding: 1.5rem 2rem;
  background: rgba(15, 23, 42, 0.5);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-lg);
  color: var(--paper);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.preparation-banner::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0) 100%);
  pointer-events: none;
}

.preparation-banner > div:first-child {
  display: grid;
  gap: 0.4rem;
  z-index: 1;
}

.preparation-label {
  color: var(--signal);
  font-family: var(--font-display);
  font-size: 0.85rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.preparation-banner strong {
  font-family: var(--font-display);
  font-size: 1.8rem;
  font-weight: 500;
  letter-spacing: -0.01em;
}

.preparation-banner p,
.empty-state,
.readiness-note {
  margin: 0;
  color: var(--paper-muted);
  font-size: 0.9rem;
  line-height: 1.5;
}

.preparation-banner.is-error {
  border-color: rgba(244, 63, 94, 0.4);
  background: rgba(244, 63, 94, 0.05);
  box-shadow: 0 0 20px rgba(244, 63, 94, 0.15);
}

.preparation-banner.is-error .preparation-label,
.badge.error {
  color: #fda4af;
}

.preparation-banner.is-completed .preparation-label {
  color: #6ee7b7;
}

.preparation-progress {
  grid-column: 1 / -1;
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
}

.preparation-progress span {
  display: block;
  height: 100%;
  background: var(--signal);
  box-shadow: 0 0 10px var(--signal);
  transition: width 0.3s ease-out;
}

.retry-button {
  z-index: 1;
  padding: 0.75rem 1.5rem;
  background: rgba(244, 63, 94, 0.15);
  border: 1px solid rgba(244, 63, 94, 0.3);
  color: #fda4af;
  border-radius: var(--radius-sm);
  font-family: var(--font-display);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  cursor: pointer;
  transition: all 0.2s ease;
}

.retry-button:hover {
  background: rgba(244, 63, 94, 0.25);
  transform: translateY(-1px);
}

/* Step Card */
.step-card {
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-lg);
  padding: 2rem;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
}

.step-card:hover {
  border-color: rgba(255, 255, 255, 0.15);
  background: rgba(20, 30, 50, 0.5);
}

.step-card.active {
  border-color: var(--signal);
  box-shadow: 0 0 30px rgba(99, 102, 241, 0.15), inset 0 0 20px rgba(99, 102, 241, 0.05);
  background: rgba(15, 23, 42, 0.6);
}

.step-card.active::before {
  content: '';
  position: absolute;
  top: -1px; left: -1px; right: -1px; bottom: -1px;
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, rgba(99,102,241,0.5), transparent 40%);
  z-index: -1;
  opacity: 0.5;
  pointer-events: none;
}

.step-card.completed {
  opacity: 0.7;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding-bottom: 1rem;
}

.step-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.step-num {
  font-family: var(--font-mono);
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--signal);
}

.step-title {
  font-family: var(--font-display);
  font-size: 1.25rem;
  font-weight: 500;
  color: var(--paper);
  letter-spacing: 0.02em;
}

.badge {
  font-size: 0.7rem;
  padding: 0.3rem 0.75rem;
  border-radius: var(--radius-full);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.badge.success {
  background: rgba(16, 185, 129, 0.15);
  color: #6ee7b7;
  border: 1px solid rgba(16, 185, 129, 0.3);
}
.badge.processing {
  background: rgba(99, 102, 241, 0.15);
  color: #a5b4fc;
  border: 1px solid rgba(99, 102, 241, 0.3);
  animation: pulse-glow 2s infinite;
}
.badge.accent {
  background: rgba(139, 92, 246, 0.15);
  color: #c4b5fd;
  border: 1px solid rgba(139, 92, 246, 0.3);
}
.badge.pending {
  background: rgba(30, 41, 59, 0.4);
  color: var(--paper-muted);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

@keyframes pulse-glow {
  0% { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.4); }
  70% { box-shadow: 0 0 0 6px rgba(99, 102, 241, 0); }
  100% { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0); }
}

.api-note {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--signal);
  margin-bottom: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.05em;
}

.description {
  font-size: 0.95rem;
  line-height: 1.6;
  margin-bottom: 2rem;
  color: var(--paper-muted);
}

/* Profiles */
.profiles-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 1.25rem;
  margin-bottom: 1.5rem;
}

.profile-card {
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-md);
  padding: 1.25rem;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.profile-card:hover {
  background: rgba(30, 41, 59, 0.6);
  border-color: var(--signal);
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3), inset 0 0 15px rgba(99, 102, 241, 0.1);
  transform: translateY(-3px);
}

.profile-header {
  display: flex;
  flex-direction: column;
}

.profile-realname {
  display: block;
  font-family: var(--font-display);
  font-weight: 500;
  font-size: 1.1rem;
  color: var(--paper);
}

.profile-username {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--paper-muted);
}

.profile-meta {
  margin: 0.25rem 0;
}

.profile-profession {
  font-family: var(--font-sans);
  font-size: 0.65rem;
  font-weight: 700;
  background: rgba(99, 102, 241, 0.15);
  color: #a5b4fc;
  border: 1px solid rgba(99, 102, 241, 0.3);
  padding: 0.2rem 0.6rem;
  border-radius: var(--radius-full);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.profile-bio {
  font-size: 0.8rem;
  line-height: 1.5;
  color: var(--paper-muted);
  height: 2.4rem;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.profile-topics {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-top: auto;
}

.topic-tag {
  font-family: var(--font-sans);
  font-size: 0.65rem;
  font-weight: 600;
  border: 1px solid rgba(99, 102, 241, 0.25);
  background: rgba(99, 102, 241, 0.08);
  padding: 0.2rem 0.5rem;
  border-radius: var(--radius-sm);
  color: #a5b4fc;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.topic-more {
  font-size: 0.65rem;
  color: var(--paper-muted);
  align-self: center;
}

/* Config Blocks */
.config-block {
  margin-top: 1.5rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-md);
  padding: 1.5rem;
  background: rgba(15, 23, 42, 0.4);
  margin-bottom: 1.5rem;
  transition: border-color 0.3s ease;
}

.config-block:hover {
  border-color: rgba(255, 255, 255, 0.15);
}

.config-block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.25rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding-bottom: 0.75rem;
}

.config-block-title {
  font-family: var(--font-display);
  font-weight: 500;
  font-size: 1rem;
  text-transform: uppercase;
  color: var(--paper);
  letter-spacing: 0.05em;
}

.config-block-badge {
  font-family: var(--font-sans);
  font-size: 0.65rem;
  font-weight: 700;
  background: rgba(139, 92, 246, 0.15);
  color: #c4b5fd;
  padding: 0.2rem 0.6rem;
  border-radius: var(--radius-full);
  border: 1px solid rgba(139, 92, 246, 0.3);
  text-transform: uppercase;
}

.platforms-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.25rem;
}

.platform-card {
  padding: 1.25rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-md);
  background: rgba(30, 41, 59, 0.3);
  transition: all 0.3s ease;
}

.platform-card:hover {
  border-color: rgba(99, 102, 241, 0.3);
  background: rgba(30, 41, 59, 0.6);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
}

.platform-name {
  font-family: var(--font-display);
  font-weight: 500;
  font-size: 0.9rem;
  margin-bottom: 1rem;
  display: block;
  color: var(--signal);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.param-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: var(--font-sans);
  font-size: 0.8rem;
  margin-bottom: 0.5rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}
.param-row:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.param-label {
  color: var(--paper-muted);
}

.param-value {
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--paper);
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 1rem;
}

.config-item {
  text-align: center;
  padding: 1.25rem 1rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-md);
  background: rgba(30, 41, 59, 0.3);
  transition: all 0.3s ease;
}

.config-item:hover {
  border-color: rgba(255, 255, 255, 0.15);
  background: rgba(30, 41, 59, 0.5);
  transform: translateY(-2px);
}

.config-item-label {
  display: block;
  font-size: 0.65rem;
  font-weight: 700;
  color: var(--paper-muted);
  margin-bottom: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.config-item-value {
  font-family: var(--font-mono);
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--paper);
}

/* Narrative */
.narrative-box {
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-md);
  padding: 1.5rem;
  background: rgba(15, 23, 42, 0.4);
  margin-bottom: 1.25rem;
  transition: border-color 0.3s ease;
}
.narrative-box:hover {
  border-color: rgba(255, 255, 255, 0.15);
}

.box-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  font-size: 0.75rem;
  margin-bottom: 0.75rem;
  color: var(--signal);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.narrative-text {
  font-size: 0.95rem;
  line-height: 1.6;
  color: var(--paper);
}

.hot-topics-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.hot-topic-tag {
  background: rgba(244, 63, 94, 0.15);
  color: #fda4af;
  border: 1px solid rgba(244, 63, 94, 0.3);
  padding: 0.25rem 0.6rem;
  border-radius: var(--radius-sm);
  font-family: var(--font-sans);
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.posts-timeline {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  margin-top: 1rem;
}

.timeline-item {
  display: flex;
  gap: 1.25rem;
}

.timeline-marker {
  width: 2px;
  background: linear-gradient(180deg, var(--signal), transparent);
  flex-shrink: 0;
  border-radius: 2px;
  opacity: 0.7;
}

.timeline-content {
  flex: 1;
  padding: 1.25rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-md);
  background: rgba(30, 41, 59, 0.4);
}

.post-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  padding-bottom: 0.5rem;
}

.post-role {
  font-family: var(--font-sans);
  font-weight: 700;
  font-size: 0.65rem;
  color: var(--paper-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.post-agent-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.post-username {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: #a5b4fc;
}

.post-id {
  font-size: 0.65rem;
  padding: 0.1rem 0.4rem;
  background: rgba(255,255,255,0.1);
  border-radius: var(--radius-sm);
  color: var(--paper);
}

.post-text {
  font-size: 0.95rem;
  line-height: 1.5;
  color: var(--paper);
}

/* Activation / Slider */
.rounds-config-section {
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  margin: 1.5rem 0;
  background: rgba(15, 23, 42, 0.5);
}

.rounds-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
}

.section-title {
  font-family: var(--font-display);
  font-size: 1.25rem;
  font-weight: 500;
  color: var(--paper);
  display: block;
  margin-bottom: 0.25rem;
  letter-spacing: 0.02em;
}

.section-desc {
  font-size: 0.85rem;
  color: var(--paper-muted);
}

.switch-control {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.switch-track {
  width: 44px;
  height: 24px;
  background: rgba(30, 41, 59, 0.8);
  border-radius: 12px;
  position: relative;
  transition: background 0.3s ease;
  border: 1px solid rgba(255, 255, 255, 0.15);
}

.switch-track::after {
  content: "";
  position: absolute;
  top: 2px;
  left: 2px;
  width: 18px;
  height: 18px;
  background: #f8fafc;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
  transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

input:checked + .switch-track {
  background: var(--signal);
  border-color: var(--signal);
}

input:checked + .switch-track::after {
  transform: translateX(20px);
}

.switch-label {
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  color: var(--paper);
}

.val-num {
  font-size: 3rem;
  font-weight: 400;
  font-family: var(--font-display);
  color: var(--paper);
  line-height: 1;
}

.val-unit {
  font-size: 1rem;
  color: var(--paper-muted);
  margin-left: 0.25rem;
}

.slider-display {
  display: flex;
  align-items: baseline;
  gap: 1rem;
  margin-bottom: 1rem;
}

.slider-meta-info {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--signal);
  background: rgba(99, 102, 241, 0.1);
  padding: 0.2rem 0.6rem;
  border-radius: var(--radius-sm);
}

.minimal-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 6px;
  background: linear-gradient(to right, var(--signal) 0%, var(--signal) var(--percent, 50%), rgba(255, 255, 255, 0.1) var(--percent, 50%), rgba(255, 255, 255, 0.1) 100%);
  border-radius: var(--radius-full);
  outline: none;
  cursor: pointer;
  margin: 1rem 0;
}

.minimal-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #ffffff;
  border: 3px solid var(--signal);
  box-shadow: 0 0 10px rgba(99, 102, 241, 0.5);
  cursor: pointer;
  transition: transform 0.1s;
}
.minimal-slider::-webkit-slider-thumb:hover {
  transform: scale(1.2);
}

.range-marks {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--paper-muted);
}

.mark-recommend {
  background: none;
  border: none;
  color: var(--signal);
  font-family: var(--font-mono);
  font-size: 0.75rem;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 4px;
}
.mark-recommend:hover {
  color: #fff;
}

.auto-info-card {
  display: flex;
  align-items: center;
  gap: 2rem;
  background: rgba(0,0,0,0.1);
  padding: 1.5rem;
  border-radius: var(--radius-md);
  border: 1px solid rgba(255,255,255,0.05);
}

.auto-meta-row {
  margin-bottom: 0.5rem;
}

.duration-badge {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  background: rgba(255,255,255,0.1);
  padding: 0.2rem 0.5rem;
  border-radius: var(--radius-sm);
  color: var(--paper);
}

.highlight-tip {
  background: none;
  border: none;
  color: var(--signal);
  cursor: pointer;
  padding: 0;
  font-size: 0.85rem;
  margin-top: 0.5rem;
  text-decoration: underline;
  text-underline-offset: 4px;
}
.highlight-tip:hover {
  color: #fff;
}

.rounds-unavailable {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1.5rem;
  border: 1px dashed rgba(255,255,255,0.2);
  border-radius: var(--radius-md);
  text-align: center;
  color: var(--paper-muted);
}
.rounds-unavailable strong {
  color: var(--paper);
  font-weight: 500;
  font-family: var(--font-display);
  font-size: 1.1rem;
}

/* Action Button */
.action-btn {
  width: 100%;
  padding: 1rem;
  background: var(--signal);
  color: var(--ink);
  border: none;
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: 1rem;
  font-family: var(--font-display);
  letter-spacing: 0.05em;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 8px 20px rgba(99, 102, 241, 0.2);
}

.action-btn:hover:not(:disabled) {
  box-shadow: 0 12px 25px rgba(99, 102, 241, 0.4);
  transform: translateY(-2px);
  background: #fff;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}

.action-btn.secondary {
  background: rgba(255,255,255,0.05);
  color: var(--paper);
  border: 1px solid rgba(255,255,255,0.1);
  padding: 0.5rem 1rem;
  font-size: 0.85rem;
  margin-top: 1rem;
  box-shadow: none;
}
.action-btn.secondary:hover {
  background: rgba(255,255,255,0.1);
}

/* Modal */
.profile-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(9, 13, 22, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1.5rem;
}

.profile-modal {
  background: rgba(15, 23, 42, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 800px;
  max-height: 85vh;
  overflow-y: auto;
  padding: 2.5rem;
  position: relative;
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.5);
  color: var(--paper);
}

.modal-header {
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding-bottom: 1.5rem;
  margin-bottom: 1.5rem;
}

.modal-name-row {
  display: flex;
  align-items: baseline;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.modal-realname {
  font-size: 2rem;
  font-weight: 500;
  font-family: var(--font-display);
  color: var(--paper);
}

.modal-username {
  font-family: var(--font-mono);
  font-size: 1rem;
  color: var(--paper-muted);
}

.modal-profession {
  font-size: 0.9rem;
  color: var(--signal);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
}

.modal-info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.info-label {
  display: block;
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--paper-muted);
  margin-bottom: 0.4rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.info-value {
  font-size: 1.1rem;
  font-weight: 500;
  color: var(--paper);
}

.info-value.mbti {
  font-family: var(--font-mono);
  color: #a5b4fc;
}

.modal-section {
  margin-bottom: 2rem;
}

.section-label {
  display: block;
  font-family: var(--font-display);
  font-size: 1.2rem;
  font-weight: 500;
  color: var(--paper);
  margin-bottom: 1rem;
}

.section-bio, .section-persona {
  font-size: 1rem;
  line-height: 1.6;
  color: var(--paper-muted);
}

.topics-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.topic-item {
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  padding: 0.4rem 0.8rem;
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
  color: var(--paper);
}

.persona-dimensions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.dimension-card {
  padding: 1rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-md);
  background: rgba(30, 41, 59, 0.3);
}

.dim-title {
  display: block;
  font-weight: 600;
  font-size: 0.8rem;
  text-transform: uppercase;
  color: var(--signal);
  margin-bottom: 0.4rem;
  letter-spacing: 0.05em;
}

.dim-desc {
  font-size: 0.85rem;
  color: var(--paper-muted);
  line-height: 1.4;
}

/* System Logs */
.activity-status {
  display: flex;
  align-items: baseline;
  gap: 1rem;
  padding: 1rem 1.5rem;
  border-top: 1px solid rgba(255,255,255,0.05);
  background: rgba(0,0,0,0.2);
}

.activity-status span {
  font-family: var(--font-display);
  font-size: 0.85rem;
  color: var(--paper-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.activity-status strong {
  font-size: 0.95rem;
  color: var(--paper);
}

.activity-disclosure {
  background: rgba(0,0,0,0.3);
  border-top: 1px solid rgba(255,255,255,0.05);
}

.activity-disclosure summary {
  padding: 1rem 1.5rem;
  color: var(--paper-muted);
  cursor: pointer;
  font-size: 0.85rem;
  display: flex;
  justify-content: space-between;
  list-style: none;
}
.activity-disclosure summary::-webkit-details-marker {
  display: none;
}
.activity-disclosure summary:hover {
  background: rgba(255,255,255,0.02);
  color: var(--paper);
}

.activity-list {
  max-height: 200px;
  overflow-y: auto;
  padding: 0 1.5rem 1.5rem;
  font-family: var(--font-mono);
  font-size: 0.8rem;
}

.activity-line {
  display: flex;
  gap: 1rem;
  margin-bottom: 0.5rem;
  color: var(--paper-muted);
}

.activity-time {
  color: #64748b;
  flex-shrink: 0;
}

.close-btn {
  position: absolute;
  top: 1.5rem;
  right: 1.5rem;
  background: rgba(255,255,255,0.05);
  border: none;
  color: var(--paper);
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  font-size: 1.5rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}
.close-btn:hover {
  background: rgba(244, 63, 94, 0.2);
  color: #fda4af;
  transform: rotate(90deg);
}

.assumption-brief {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1px;
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: var(--radius-md);
  overflow: hidden;
  margin-bottom: 1.5rem;
}

.assumption-brief article {
  background: rgba(15, 23, 42, 0.6);
  padding: 1.5rem;
}

.assumption-brief span {
  display: block;
  font-size: 0.75rem;
  color: var(--signal);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
  font-weight: 600;
}

.assumption-brief strong {
  display: block;
  font-family: var(--font-display);
  font-size: 1.25rem;
  color: var(--paper);
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.assumption-brief p {
  font-size: 0.85rem;
  color: var(--paper-muted);
  line-height: 1.5;
  margin: 0;
}

.advanced-assumptions {
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: var(--radius-md);
  background: rgba(0,0,0,0.2);
  overflow: hidden;
}

.advanced-assumptions summary {
  padding: 1rem 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  list-style: none;
}
.advanced-assumptions summary::-webkit-details-marker {
  display: none;
}
.advanced-assumptions summary:hover {
  background: rgba(255,255,255,0.02);
}

.advanced-assumptions summary strong {
  color: var(--paper);
  font-weight: 500;
  display: block;
}

.advanced-assumptions summary small {
  color: var(--paper-muted);
  font-size: 0.8rem;
}

.advanced-assumptions-body {
  padding: 0 1.5rem 1.5rem;
  border-top: 1px solid rgba(255,255,255,0.05);
}

@media (max-width: 768px) {
  .preparation-banner {
    grid-template-columns: 1fr;
  }
  .auto-info-card {
    flex-direction: column;
    align-items: flex-start;
  }
  .rounds-header {
    flex-direction: column;
    gap: 1rem;
  }
}
</style>"""

content = re.sub(r"<style scoped>.*?</style>", new_style, content, flags=re.DOTALL)

with open("C:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/frontend/src/components/Step2EnvSetup.vue", "w", encoding="utf-8") as f:
    f.write(content)
