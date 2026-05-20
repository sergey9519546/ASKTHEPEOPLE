import fs from 'fs';
import path from 'path';

const filePath = path.join(process.cwd(), 'frontend', 'src', 'views', 'Process.vue');
let css = fs.readFileSync(filePath, 'utf8');

css = css.replace(/\.attr\('stroke', '#ccc'\)/g, `.attr('stroke', 'rgba(255, 255, 255, 0.2)')`);
css = css.replace(/\.attr\('fill', '#333'\)/g, `.attr('fill', 'rgba(255, 255, 255, 0.8)')`);
css = css.replace(/\.attr\('fill', '#999'\)/g, `.attr('fill', 'rgba(255, 255, 255, 0.5)')`);
css = css.replace(/\.attr\('stroke', '#fff'\)/g, `.attr('stroke', 'rgba(0, 0, 0, 0.3)')`);

const newCss = `
<style scoped>
.process-page { min-height: 100vh; background: var(--bg-color); font-family: var(--font-mono); overflow: hidden; }
.navbar { display: flex; align-items: center; justify-content: space-between; padding: 0 24px; height: 56px; background: var(--surface-color); backdrop-filter: blur(16px); border-bottom: 1px solid var(--border-color); z-index: 10; position: relative; }
.nav-brand { font-family: var(--font-mono); font-weight: 800; font-size: 1.1rem; letter-spacing: 2px; cursor: pointer; color: var(--text-primary); }
.nav-center { display: flex; align-items: center; gap: 12px; position: absolute; left: 50%; transform: translateX(-50%); }
.step-badge { background: var(--accent-color); color: var(--bg-color); padding: 4px 10px; font-size: 0.75rem; font-weight: 700; border-radius: var(--radius-sm); box-shadow: 0 0 10px var(--accent-glow); }
.step-name { font-size: 0.9rem; font-weight: 600; color: var(--text-primary); }
.nav-status { display: flex; align-items: center; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--text-secondary); margin-right: 8px; }
.status-dot.processing { background: var(--accent-color); animation: pulse 1.5s infinite; box-shadow: 0 0 10px var(--accent-glow); }
.status-dot.completed { background: #1A936F; box-shadow: 0 0 10px rgba(26, 147, 111, 0.5); }
.status-dot.error { background: #C5283D; box-shadow: 0 0 10px rgba(197, 40, 61, 0.5); }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; box-shadow: none; } }
.status-text { font-size: 0.8rem; color: var(--text-secondary); }

.main-content { display: flex; height: calc(100vh - 56px); position: relative; }
.left-panel { width: 50%; flex: none; display: flex; flex-direction: column; border-right: 1px solid var(--border-color); transition: width 0.35s cubic-bezier(0.4, 0, 0.2, 1); background: transparent; z-index: 5; }
.left-panel.full-screen { width: 100%; border-right: none; }
.panel-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 24px; border-bottom: 1px solid var(--border-color); background: rgba(0,0,0,0.2); height: 50px; }
.header-left { display: flex; align-items: center; gap: 8px; }
.header-deco { color: var(--accent-color); font-size: 0.8rem; }
.header-title { font-size: 0.9rem; font-weight: 600; color: var(--text-primary); }
.header-right { display: flex; align-items: center; gap: 16px; font-size: 0.8rem; color: var(--text-secondary); }
.stat-item { display: flex; align-items: center; gap: 4px; }
.stat-val { font-weight: 600; color: var(--text-primary); }
.stat-divider { color: var(--border-color); }
.action-buttons { display: flex; align-items: center; gap: 8px; }
.action-btn { display: flex; align-items: center; justify-content: center; width: 28px; height: 28px; background: transparent; border: 1px solid transparent; cursor: pointer; transition: all 0.2s; color: var(--text-secondary); border-radius: var(--radius-sm); }
.action-btn:hover:not(:disabled) { background: rgba(255, 255, 255, 0.1); color: var(--text-primary); border-color: var(--border-color); }
.action-btn:disabled { opacity: 0.3; cursor: not-allowed; }
.icon-refresh, .icon-fullscreen { font-size: 1.1rem; line-height: 1; }
.icon-refresh.spinning { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.graph-container { flex: 1; position: relative; overflow: hidden; }
.graph-loading, .graph-waiting, .graph-error { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; }
.loading-animation { position: relative; width: 80px; height: 80px; margin: 0 auto 20px; }
.loading-ring { position: absolute; border: 2px solid transparent; border-radius: 50%; animation: ring-rotate 1.5s linear infinite; }
.loading-ring:nth-child(1) { width: 80px; height: 80px; border-top-color: var(--text-secondary); }
.loading-ring:nth-child(2) { width: 60px; height: 60px; top: 10px; left: 10px; border-right-color: var(--accent-color); animation-delay: 0.2s; }
.loading-ring:nth-child(3) { width: 40px; height: 40px; top: 20px; left: 20px; border-bottom-color: rgba(255,255,255,0.3); animation-delay: 0.4s; }
@keyframes ring-rotate { to { transform: rotate(360deg); } }
.loading-text, .waiting-text { font-size: 0.95rem; color: var(--text-primary); margin: 0 0 8px; }
.waiting-hint { font-size: 0.85rem; color: var(--text-secondary); margin: 0; }
.waiting-icon { margin-bottom: 20px; }
.network-icon { width: 100px; height: 100px; opacity: 0.5; stroke: var(--text-secondary); filter: drop-shadow(0 0 10px rgba(255,255,255,0.1)); }
.graph-view { width: 100%; height: 100%; position: relative; }
.graph-svg { width: 100%; height: 100%; display: block; }
.graph-building-hint { position: absolute; bottom: 16px; left: 16px; display: flex; align-items: center; gap: 8px; padding: 10px 16px; background: rgba(255, 69, 0, 0.1); border: 1px solid var(--accent-color); font-size: 0.85rem; color: var(--accent-color); border-radius: var(--radius-sm); backdrop-filter: blur(4px); box-shadow: 0 0 15px rgba(255,69,0,0.15); }
.building-dot { width: 8px; height: 8px; background: var(--accent-color); border-radius: 50%; animation: pulse 1s infinite; }

.detail-panel { position: absolute; top: 16px; right: 16px; width: 340px; max-height: calc(100% - 32px); background: var(--surface-color); backdrop-filter: blur(16px); border: 1px solid var(--border-color); box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5); border-radius: var(--radius-md); overflow: hidden; display: flex; flex-direction: column; z-index: 100; }
.detail-panel-header { display: flex; align-items: center; gap: 10px; padding: 15px 20px; background: rgba(0,0,0,0.3); border-bottom: 1px solid var(--border-color); }
.detail-title { font-size: 1rem; font-weight: 600; color: var(--text-primary); }
.detail-badge { padding: 3px 10px; font-size: 0.75rem; color: #fff; border-radius: 4px; text-transform: uppercase; letter-spacing: 1px; }
.detail-close { margin-left: auto; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; background: rgba(255,255,255,0.1); border: 1px solid transparent; font-size: 1.2rem; color: var(--text-primary); cursor: pointer; border-radius: 50%; transition: all 0.2s; }
.detail-close:hover { background: rgba(255,0,0,0.2); color: #ff5555; }
.detail-content { padding: 20px; overflow-y: auto; flex: 1; }
.detail-row { display: flex; align-items: flex-start; margin-bottom: 12px; }
.detail-label { font-size: 0.85rem; color: var(--text-secondary); min-width: 80px; flex-shrink: 0; }
.detail-value { font-size: 0.9rem; color: var(--text-primary); word-break: break-word; }
.detail-value.uuid { font-family: var(--font-mono); font-size: 0.75rem; color: var(--text-secondary); opacity: 0.7; }
.detail-value.highlight { font-weight: 700; color: var(--accent-color); }
.detail-section { margin-bottom: 15px; }
.detail-summary { margin: 10px 0 0 0; font-size: 0.9rem; color: var(--text-primary); line-height: 1.6; padding: 12px; background: rgba(0,0,0,0.2); border-radius: var(--radius-sm); border-left: 3px solid var(--accent-color); }
.detail-labels { display: flex; flex-wrap: wrap; gap: 8px; }
.label-tag { padding: 4px 10px; font-size: 0.75rem; background: rgba(255,255,255,0.05); border: 1px solid var(--border-color); color: var(--text-primary); border-radius: var(--radius-sm); }
.edge-relation { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; padding: 15px; background: rgba(0,0,0,0.2); border: 1px solid var(--border-color); border-radius: var(--radius-sm); }
.edge-source, .edge-target { font-size: 0.9rem; font-weight: 600; color: var(--text-primary); }
.edge-arrow { color: var(--text-secondary); }
.edge-type { padding: 3px 10px; font-size: 0.75rem; background: var(--accent-color); color: var(--bg-color); border-radius: 4px; font-weight: 700; }
.detail-subtitle { font-size: 1rem; font-weight: 600; color: var(--text-primary); margin: 20px 0 15px 0; padding-bottom: 10px; border-bottom: 1px solid var(--border-color); }
.properties-list { margin-top: 10px; padding: 12px; background: rgba(0,0,0,0.2); border: 1px solid var(--border-color); border-radius: var(--radius-sm); }
.property-item { display: flex; margin-bottom: 8px; font-size: 0.85rem; }
.property-item:last-child { margin-bottom: 0; }
.property-key { color: var(--text-secondary); margin-right: 10px; font-family: var(--font-mono); }
.property-value { color: var(--text-primary); word-break: break-word; }
.episodes-list { margin-top: 10px; display: flex; flex-direction: column; gap: 8px; }
.episode-tag { display: block; padding: 8px 12px; font-size: 0.8rem; font-family: var(--font-mono); background: rgba(0,0,0,0.2); border: 1px solid var(--border-color); color: var(--text-primary); word-break: break-all; border-radius: var(--radius-sm); }
.error-icon { font-size: 2.5rem; display: block; margin-bottom: 15px; text-shadow: 0 0 20px rgba(255,0,0,0.5); }

.graph-legend { display: flex; flex-wrap: wrap; gap: 16px; padding: 15px 24px; border-top: 1px solid var(--border-color); background: rgba(0,0,0,0.3); }
.legend-item { display: flex; align-items: center; gap: 8px; font-size: 0.8rem; }
.legend-dot { width: 12px; height: 12px; border-radius: 50%; box-shadow: 0 0 10px rgba(255,255,255,0.2); }
.legend-label { color: var(--text-primary); }
.legend-count { color: var(--text-secondary); font-family: var(--font-mono); background: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; }

.right-panel { width: 50%; flex: none; display: flex; flex-direction: column; background: transparent; transition: width 0.35s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease, transform 0.3s ease; overflow: hidden; opacity: 1; }
.right-panel.hidden { width: 0; opacity: 0; transform: translateX(20px); pointer-events: none; }
.right-panel .panel-header.dark-header { background: rgba(0,0,0,0.4); border-bottom: 1px solid var(--border-color); }
.right-panel .header-icon { color: var(--accent-color); margin-right: 10px; text-shadow: 0 0 10px var(--accent-glow); }

.process-content { flex: 1; overflow-y: auto; padding: 30px; }
.process-phase { margin-bottom: 30px; border: 1px solid var(--border-color); opacity: 0.5; transition: all 0.3s; border-radius: var(--radius-md); background: var(--surface-color); backdrop-filter: blur(10px); }
.process-phase.active, .process-phase.completed { opacity: 1; }
.process-phase.active { border-color: var(--accent-color); box-shadow: 0 0 20px rgba(255, 69, 0, 0.1); }
.process-phase.completed { border-color: #1A936F; }

.phase-header { display: flex; align-items: flex-start; gap: 20px; padding: 20px; background: rgba(0,0,0,0.2); border-bottom: 1px solid var(--border-color); border-radius: var(--radius-md) var(--radius-md) 0 0; }
.process-phase.active .phase-header { background: rgba(255, 69, 0, 0.05); border-bottom-color: rgba(255, 69, 0, 0.2); }
.process-phase.completed .phase-header { background: rgba(26, 147, 111, 0.05); border-bottom-color: rgba(26, 147, 111, 0.2); }
.phase-num { font-size: 1.8rem; font-weight: 800; color: rgba(255,255,255,0.2); line-height: 1; font-family: var(--font-mono); }
.process-phase.active .phase-num { color: var(--accent-color); text-shadow: 0 0 15px var(--accent-glow); }
.process-phase.completed .phase-num { color: #1A936F; }
.phase-info { flex: 1; }
.phase-title { font-size: 1.1rem; font-weight: 700; margin-bottom: 6px; color: var(--text-primary); }
.phase-api { font-size: 0.8rem; color: var(--text-secondary); font-family: var(--font-mono); background: rgba(255,255,255,0.05); padding: 2px 8px; border-radius: 4px; display: inline-block; }
.phase-status { font-size: 0.75rem; padding: 4px 10px; background: rgba(255,255,255,0.1); color: var(--text-secondary); border-radius: 4px; font-weight: 600; font-family: var(--font-mono); }
.phase-status.active { background: var(--accent-color); color: var(--bg-color); box-shadow: 0 0 10px var(--accent-glow); }
.phase-status.completed { background: #1A936F; color: #fff; box-shadow: 0 0 10px rgba(26, 147, 111, 0.4); }

.phase-detail { padding: 20px; }
.entity-tags { display: flex; flex-wrap: wrap; gap: 10px; }
.entity-tag { font-size: 0.8rem; padding: 6px 12px; background: rgba(255,255,255,0.05); border: 1px solid var(--border-color); color: var(--text-primary); border-radius: var(--radius-sm); }
.entity-tag:hover { border-color: var(--accent-color); color: var(--accent-color); }
.relation-list { font-size: 0.85rem; }
.relation-item { display: flex; align-items: center; gap: 10px; padding: 10px; border-bottom: 1px dashed rgba(255,255,255,0.1); background: rgba(0,0,0,0.2); margin-bottom: 4px; border-radius: 4px; }
.relation-item:last-child { border-bottom: none; margin-bottom: 0; }
.rel-source, .rel-target { color: var(--text-primary); font-weight: 500; }
.rel-arrow { color: var(--text-secondary); }
.rel-name { color: var(--accent-color); font-weight: 700; font-family: var(--font-mono); background: rgba(255,69,0,0.1); padding: 2px 6px; border-radius: 4px; }
.relation-more { padding-top: 10px; color: var(--text-secondary); font-size: 0.8rem; text-align: center; }

.ontology-progress { display: flex; align-items: center; gap: 15px; padding: 15px; background: rgba(255, 69, 0, 0.05); border: 1px solid rgba(255, 69, 0, 0.2); border-radius: var(--radius-sm); }
.progress-spinner { width: 24px; height: 24px; border: 2px solid rgba(255,255,255,0.1); border-top-color: var(--accent-color); border-radius: 50%; animation: spin 1s linear infinite; }
.progress-text { font-size: 0.9rem; color: var(--text-primary); }
.waiting-state { padding: 20px; background: rgba(0,0,0,0.2); border: 1px dashed var(--border-color); text-align: center; border-radius: var(--radius-sm); }
.waiting-hint { font-size: 0.9rem; color: var(--text-secondary); }

.progress-bar { height: 8px; background: rgba(255,255,255,0.1); margin-bottom: 10px; border-radius: 4px; overflow: hidden; box-shadow: inset 0 1px 3px rgba(0,0,0,0.5); }
.progress-fill { height: 100%; background: var(--accent-color); transition: width 0.3s; box-shadow: 0 0 10px var(--accent-glow); }
.progress-info { display: flex; justify-content: space-between; font-size: 0.85rem; font-family: var(--font-mono); }
.progress-message { color: var(--text-secondary); }
.progress-percent { color: var(--accent-color); font-weight: 700; }

.build-result { display: flex; gap: 20px; }
.result-item { flex: 1; text-align: center; padding: 20px; background: rgba(0,0,0,0.2); border: 1px solid var(--border-color); border-radius: var(--radius-sm); transition: transform 0.2s; }
.result-item:hover { transform: translateY(-3px); border-color: rgba(255,255,255,0.2); background: rgba(0,0,0,0.4); }
.result-value { display: block; font-size: 1.8rem; font-weight: 800; color: var(--text-primary); margin-bottom: 8px; font-family: var(--font-mono); text-shadow: 0 0 10px rgba(255,255,255,0.2); }
.result-label { font-size: 0.75rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 1px; }

.next-step-section { margin-top: 30px; padding-top: 30px; border-top: 1px solid var(--border-color); }
.next-step-btn { width: 100%; display: flex; align-items: center; justify-content: center; gap: 12px; padding: 18px; background: var(--text-primary); color: var(--bg-color); border: none; font-size: 1.1rem; font-weight: 700; letter-spacing: 1px; cursor: pointer; transition: all 0.3s; border-radius: var(--radius-sm); font-family: var(--font-mono); }
.next-step-btn:hover:not(:disabled) { background: var(--accent-color); color: var(--text-primary); box-shadow: 0 5px 20px rgba(255, 69, 0, 0.4); transform: translateY(-2px); }
.next-step-btn:disabled { background: rgba(255,255,255,0.1); color: rgba(255,255,255,0.3); border: 1px solid var(--border-color); cursor: not-allowed; }

.project-panel { border-top: 1px solid var(--border-color); background: rgba(0,0,0,0.3); }
.project-header { display: flex; align-items: center; gap: 12px; padding: 15px 30px; border-bottom: 1px solid var(--border-color); }
.project-icon { color: var(--accent-color); font-size: 1.2rem; }
.project-title { font-size: 1rem; font-weight: 600; color: var(--text-primary); letter-spacing: 1px; }
.project-details { padding: 20px 30px; }
.project-item { display: flex; justify-content: space-between; align-items: flex-start; padding: 10px 0; border-bottom: 1px dashed rgba(255,255,255,0.1); font-size: 0.9rem; }
.project-item:last-child { border-bottom: none; }
.item-label { color: var(--text-secondary); flex-shrink: 0; }
.item-value { color: var(--text-primary); text-align: right; max-width: 65%; word-break: break-all; }
.item-value.code { font-family: var(--font-mono); font-size: 0.8rem; color: var(--text-secondary); background: rgba(255,255,255,0.05); padding: 2px 8px; border-radius: var(--radius-sm); border: 1px solid rgba(255,255,255,0.1); }

@media (max-width: 1024px) {
  .main-content { flex-direction: column; }
  .left-panel { border-bottom: 1px solid var(--border-color); height: 50vh; }
  .right-panel { height: 50vh; opacity: 1 !important; transform: none !important; }
}
</style>
`;

css = css.replace(/<style scoped>[\s\S]*<\/style>/, newCss);
fs.writeFileSync(filePath, css, 'utf8');
