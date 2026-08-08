import re

with open("C:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/frontend/src/components/Step4Report.vue", "r", encoding="utf-8") as f:
    content = f.read()

new_style = """<style scoped>
.decision-report-shell {
  min-height: 100%;
  overflow-x: hidden;
  overflow-y: auto;
  background-color: transparent;
  color: var(--paper);
  font-family: var(--font-sans);
  scroll-behavior: smooth;
}

.skip-link {
  position: absolute;
  top: 1rem;
  left: 1rem;
  z-index: 50;
  padding: 0.75rem 1.25rem;
  transform: translateY(-200%);
  background: rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(12px);
  border: 1px solid var(--signal);
  border-radius: var(--radius-md);
  color: var(--signal);
  font-weight: 600;
  text-decoration: none;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 4px 20px rgba(0,0,0,0.5);
}

.skip-link:focus {
  transform: translateY(0);
}

/* Masthead */
.report-masthead {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(18rem, 24rem);
  gap: clamp(2rem, 6vw, 5rem);
  align-items: end;
  min-height: 24rem;
  padding: clamp(2rem, 5vw, 5rem);
  overflow: hidden;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.2) 0%, rgba(15, 23, 42, 0.6) 100%);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.report-masthead::before {
  content: '';
  position: absolute;
  top: -50%; left: -10%;
  width: 60%; height: 150%;
  background: radial-gradient(circle, rgba(99,102,241,0.15) 0%, transparent 70%);
  pointer-events: none;
  z-index: 0;
}

.masthead-copy,
.truth-stamp {
  position: relative;
  z-index: 1;
}

.route-label,
.section-kicker {
  margin: 0 0 1rem;
  font-family: var(--font-display);
  font-size: 0.85rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.route-label {
  display: flex;
  align-items: center;
  gap: 1rem;
  color: var(--signal);
}

.route-number {
  display: grid;
  width: 2.5rem;
  height: 2.5rem;
  place-items: center;
  background: rgba(99, 102, 241, 0.15);
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: 50%;
  box-shadow: 0 0 15px rgba(99, 102, 241, 0.2);
}

.report-masthead h1 {
  max-width: 18ch;
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(2.5rem, 5vw, 5.5rem);
  font-weight: 500;
  letter-spacing: -0.02em;
  line-height: 1.05;
  color: #fff;
  text-shadow: 0 4px 20px rgba(0,0,0,0.5);
}

.decision-question {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-width: 58rem;
  margin: clamp(2rem, 4vw, 3.3rem) 0 0;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(255,255,255,0.1);
  color: var(--paper);
  font-size: clamp(1rem, 1.4vw, 1.25rem);
  line-height: 1.5;
}

.decision-question span {
  color: var(--signal);
  font-family: var(--font-display);
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

/* Truth Stamp */
.truth-stamp {
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: 2rem;
  background: rgba(15, 23, 42, 0.5);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-lg);
  box-shadow: 0 10px 30px rgba(0,0,0,0.3);
  position: relative;
  overflow: hidden;
}
.truth-stamp::before {
  content: '';
  position: absolute;
  top: 0; left: 0;
  width: 4px; height: 100%;
  background: linear-gradient(180deg, var(--signal), #a5b4fc);
  box-shadow: 0 0 10px var(--signal);
}

.truth-kicker {
  color: var(--paper-muted);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin-bottom: auto;
}

.truth-stamp strong {
  margin-top: 2rem;
  color: var(--signal);
  font-family: var(--font-display);
  font-size: clamp(2rem, 3vw, 3.5rem);
  font-weight: 500;
  line-height: 1;
}

.truth-stamp > span:not(.truth-kicker) {
  margin-top: 0.5rem;
  font-family: var(--font-display);
  font-size: 1.2rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #fff;
}

.truth-stamp p {
  margin: 1rem 0 0;
  color: var(--paper-muted);
  font-size: 0.85rem;
  line-height: 1.5;
}

/* Reading Route */
.reading-route {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1px;
  background: rgba(255,255,255,0.05);
  border-bottom: 1px solid rgba(255,255,255,0.08);
}

.reading-route a {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 1.5rem 2rem;
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(8px);
  color: var(--paper);
  text-decoration: none;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.reading-route a::before {
  content: '';
  position: absolute;
  bottom: 0; left: 0; right: 0; height: 2px;
  background: var(--signal);
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 0.3s ease;
}

.reading-route a:hover {
  background: rgba(30, 41, 59, 0.6);
}
.reading-route a:hover::before {
  transform: scaleX(1);
}

.reading-route a > span {
  font-family: var(--font-display);
  font-size: 1.2rem;
  color: var(--signal);
  margin-bottom: 0.5rem;
}

.reading-route strong {
  font-family: var(--font-display);
  font-size: 1.1rem;
  font-weight: 500;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  margin-bottom: 0.25rem;
}

.reading-route small {
  font-size: 0.8rem;
  color: var(--paper-muted);
}

/* Generation Strip */
.generation-strip {
  display: grid;
  grid-template-columns: minmax(12rem, 20rem) minmax(8rem, 1fr) auto;
  gap: 1.5rem;
  align-items: center;
  padding: 1.25rem clamp(2rem, 5vw, 5rem);
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(255,255,255,0.08);
}

.generation-strip > div:first-child {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.generation-strip span,
.generation-strip b {
  font-family: var(--font-display);
  font-size: 0.8rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--paper-muted);
}

.generation-strip strong {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--signal);
  animation: pulse-text 2s infinite;
}

@keyframes pulse-text {
  0%, 100% { opacity: 1; text-shadow: 0 0 10px rgba(99,102,241,0.5); }
  50% { opacity: 0.7; text-shadow: none; }
}

.progress-track {
  height: 6px;
  background: rgba(255,255,255,0.1);
  border-radius: 3px;
  overflow: hidden;
}

.progress-track span {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--signal), #a5b4fc);
  box-shadow: 0 0 10px var(--signal);
  transform-origin: left;
  transition: transform 0.5s ease-out;
}

/* Grid Layout */
.report-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(22rem, 28rem);
  gap: clamp(3rem, 6vw, 6rem);
  width: min(100%, 100rem);
  margin: 0 auto;
  padding: clamp(3rem, 6vw, 6rem) clamp(2rem, 5vw, 5rem);
  outline: none;
}

/* Findings Section */
.findings-intro {
  margin-bottom: clamp(4rem, 8vw, 6rem);
}

.findings-intro h2,
.trace-section h2,
.limits-section h2,
.next-step-section h2 {
  font-family: var(--font-display);
  font-weight: 500;
  letter-spacing: 0;
  line-height: 1.1;
  color: #fff;
  margin: 0;
}

.findings-intro h2 {
  font-size: clamp(2.5rem, 4vw, 4.5rem);
}

.findings-intro > p:last-child {
  margin: 1.5rem 0 0;
  color: var(--paper-muted);
  font-size: 1.1rem;
  line-height: 1.6;
}

.finding-section {
  display: grid;
  grid-template-columns: 3rem minmax(0, 1fr);
  gap: clamp(1.5rem, 4vw, 3rem);
  margin-bottom: 4rem;
}

.finding-route {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.finding-route span {
  display: grid;
  width: 3rem;
  height: 3rem;
  place-items: center;
  background: rgba(15, 23, 42, 0.8);
  border: 2px solid rgba(255,255,255,0.1);
  border-radius: 50%;
  color: var(--paper-muted);
  font-family: var(--font-display);
  font-size: 1.2rem;
  z-index: 2;
  transition: all 0.3s ease;
}

.finding-section.is-drafting .finding-route span,
.finding-section:not(.is-drafting):has(.report-prose) .finding-route span {
  border-color: var(--signal);
  color: var(--signal);
  box-shadow: 0 0 15px rgba(99,102,241,0.3);
}

.finding-section.is-drafting .finding-route span {
  animation: pulse-glow 2s infinite;
}

@keyframes pulse-glow {
  0% { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.4); }
  70% { box-shadow: 0 0 0 10px rgba(99, 102, 241, 0); }
  100% { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0); }
}

.finding-route i {
  width: 2px;
  flex: 1;
  background: rgba(255,255,255,0.1);
  margin-top: 0.5rem;
}

.finding-section:last-child .finding-route i {
  background: repeating-linear-gradient(to bottom, rgba(255,255,255,0.1) 0, rgba(255,255,255,0.1) 4px, transparent 4px, transparent 8px);
}

.finding-copy {
  background: rgba(15, 23, 42, 0.3);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: var(--radius-lg);
  padding: 2.5rem;
  transition: all 0.3s ease;
}

.finding-copy:hover {
  background: rgba(30, 41, 59, 0.4);
  border-color: rgba(255,255,255,0.1);
}

.finding-copy > header {
  margin-bottom: 2rem;
}

.finding-copy > header p {
  margin: 0 0 0.75rem;
  color: var(--signal);
  font-family: var(--font-display);
  font-size: 0.8rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.finding-copy h3 {
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(1.8rem, 3vw, 2.5rem);
  font-weight: 500;
  line-height: 1.2;
  color: #fff;
}

.report-prose {
  color: var(--paper-muted);
  font-size: 1.05rem;
  line-height: 1.7;
}

.report-prose p,
.report-prose ul,
.report-prose ol,
.report-prose blockquote {
  margin: 0 0 1.5rem;
}

.report-prose h4 {
  margin: 2.5rem 0 1rem;
  font-family: var(--font-display);
  font-size: 1.4rem;
  color: var(--paper);
  font-weight: 500;
}

.report-prose ul, .report-prose ol {
  padding-left: 1.5rem;
}

.report-prose li {
  margin-bottom: 0.75rem;
}

.report-prose li::marker {
  color: var(--signal);
}

.report-prose blockquote {
  padding: 1.25rem 1.5rem;
  background: rgba(99, 102, 241, 0.05);
  border-left: 3px solid var(--signal);
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
  color: #a5b4fc;
  font-style: italic;
}

/* Side Rail */
.trace-section {
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.trace-section > header {
  padding: 2rem;
  background: rgba(30, 41, 59, 0.6);
  border-bottom: 1px solid rgba(255,255,255,0.05);
}

.trace-section h2, .limits-section h2, .next-step-section h2 {
  font-size: 1.8rem;
  margin-bottom: 1rem;
}

.trace-section > header > p:last-child {
  margin: 0;
  color: var(--paper-muted);
  font-size: 0.9rem;
  line-height: 1.5;
}

.trace-list {
  list-style: none;
  margin: 0; padding: 0;
}

.trace-list > li {
  padding: 1.5rem 2rem;
  border-bottom: 1px solid rgba(255,255,255,0.05);
  transition: background 0.2s;
}
.trace-list > li:hover {
  background: rgba(255,255,255,0.02);
}

.trace-list article > header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.trace-list article > header strong {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-family: var(--font-display);
  color: var(--paper);
  text-transform: uppercase;
  font-size: 0.9rem;
  letter-spacing: 0.05em;
}

.trace-list article > header strong small {
  color: var(--signal);
  font-size: 0.7rem;
}

.trace-excerpt {
  font-size: 0.95rem;
  line-height: 1.6;
  color: var(--paper);
  margin-bottom: 1rem;
}

.trace-meaning {
  padding: 1rem;
  background: rgba(0,0,0,0.2);
  border-left: 2px solid var(--signal);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  color: var(--paper-muted);
  font-size: 0.85rem;
  line-height: 1.5;
}

.limits-section {
  margin-top: 3rem;
  padding: 2rem;
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: var(--radius-lg);
}

.limits-section ul {
  list-style: none;
  padding: 0;
  margin: 1.5rem 0 0;
}

.limits-section li {
  position: relative;
  padding-left: 1.5rem;
  margin-bottom: 1rem;
  color: var(--paper-muted);
  font-size: 0.95rem;
  line-height: 1.5;
}

.limits-section li::before {
  content: '';
  position: absolute;
  top: 0.5rem; left: 0;
  width: 6px; height: 6px;
  background: var(--signal);
  border-radius: 50%;
}

.next-step-section {
  margin-top: 3rem;
}

.action-button {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 1.25rem 2rem;
  border-radius: var(--radius-md);
  font-family: var(--font-display);
  font-size: 1rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  cursor: pointer;
  transition: all 0.3s ease;
  border: none;
}

.action-button::after {
  content: '→';
  font-family: var(--font-sans);
  font-size: 1.25rem;
  transition: transform 0.2s;
}

.action-button:hover:not(:disabled)::after {
  transform: translateX(5px);
}

.action-button.is-primary {
  background: var(--signal);
  color: var(--ink);
  box-shadow: 0 10px 20px rgba(99,102,241,0.2);
}

.action-button.is-primary:hover:not(:disabled) {
  background: #fff;
  box-shadow: 0 15px 30px rgba(99,102,241,0.4);
  transform: translateY(-2px);
}

.action-button.is-dark {
  background: rgba(30, 41, 59, 0.8);
  color: var(--paper);
  border: 1px solid rgba(255,255,255,0.1);
  margin-top: 1rem;
}

.action-button.is-dark:hover:not(:disabled) {
  background: rgba(50, 65, 90, 0.9);
  border-color: rgba(255,255,255,0.2);
}

.terminal-report-alert {
  display: flex;
  gap: 2rem;
  margin: 3rem auto;
  padding: 3rem;
  max-width: 800px;
  background: rgba(244, 63, 94, 0.05);
  border: 1px solid rgba(244, 63, 94, 0.2);
  border-radius: var(--radius-lg);
  backdrop-filter: blur(12px);
}
.terminal-report-alert > div:first-child {
  font-size: 3rem;
  color: #fda4af;
  background: rgba(244, 63, 94, 0.15);
  width: 5rem; height: 5rem;
  display: flex; justify-content: center; align-items: center;
  border-radius: 50%;
  flex-shrink: 0;
}
.recovery-actions {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 1.5rem;
}

.report-message {
  padding: 2rem;
  background: rgba(244, 63, 94, 0.05);
  border-left: 4px solid #fda4af;
  border-radius: var(--radius-md);
  margin-bottom: 2rem;
}

.report-skeleton {
  display: grid;
  grid-template-columns: 3rem minmax(0, 1fr);
  gap: 2rem;
  opacity: 0.5;
}

.skeleton-route {
  width: 3rem; height: 3rem;
  border-radius: 50%;
  background: rgba(255,255,255,0.1);
  animation: pulse-glow 2s infinite;
}

.report-skeleton > div:last-child {
  display: flex; flex-direction: column; gap: 1rem;
}

.report-skeleton i {
  height: 1rem; background: rgba(255,255,255,0.1); border-radius: var(--radius-sm);
  animation: pulse-glow 2s infinite;
}

.finding-pending {
  display: flex; align-items: center; gap: 1rem;
  color: var(--paper-muted);
}
.finding-pending span {
  width: 1.5rem; height: 1.5rem;
  border: 2px solid rgba(255,255,255,0.1);
  border-top-color: var(--signal);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 1024px) {
  .report-masthead {
    grid-template-columns: 1fr;
    padding: 3rem 2rem;
  }
  .truth-stamp {
    margin-top: 2rem;
  }
  .report-grid {
    grid-template-columns: 1fr;
  }
}
</style>"""

content = re.sub(r"<style scoped>.*?</style>", new_style, content, flags=re.DOTALL)

with open("C:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/frontend/src/components/Step4Report.vue", "w", encoding="utf-8") as f:
    f.write(content)
