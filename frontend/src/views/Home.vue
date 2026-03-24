<template>
  <div class="bauhaus-home-root">
    <!-- BAUHAUS DECORATIVE ELEMENTS -->
    <div class="geo-decoration circle-red"></div>
    <div class="geo-decoration square-blue"></div>
    <div class="geo-decoration triangle-yellow"></div>

    <!-- NAVIGATION OVERLAY -->
    <nav class="bauhaus-nav">
      <div class="brand-block">
        <span class="brand-text">ASK THE PEOPLE</span>
        <span class="brand-version">BETA_V1.1</span>
      </div>
      <div class="nav-actions">
        <a href="https://github.com/sergey9519546/ASKTHEPEOPLE" target="_blank" class="bauhaus-nav-link">
          SOURCE_CODE_<span class="arrow">↗</span>
        </a>
      </div>
    </nav>

    <main class="bauhaus-main">
      <!-- HERO: THE BRUTALIST STATEMENT -->
      <section class="hero-brutal">
        <div class="hero-left">
          <div class="status-ribbon">ENGINE_ONLINE // SYSTEM_STABLE</div>
          <h1 class="hero-title">
            SIMULATE<br />
            <span class="text-blue">COLLECTIVE</span><br />
            <span class="text-brutal">REALITY.</span>
          </h1>
        </div>
        <div class="hero-right">
          <p class="hero-manifesto">
            The first autonomous crowd intelligence engine. 
            Deploy millions of digital twins. Predict emergent human behavior. 
            Transform documents into living, breathing simulations.
          </p>
        </div>
      </section>

      <!-- WORKBENCH INITIALIZATION -->
      <section class="workbench-init">
        <div class="init-grid">
          <!-- LEFT: SEED UPLOAD -->
          <div class="init-card upload-card">
            <header class="card-header">
              <span class="step-tag">STEP_01</span>
              <h3>KNOWLEDGE SEEDING</h3>
            </header>
            
            <div 
              class="bauhaus-dropzone"
              :class="{ 'is-active': isDragOver }"
              @dragover.prevent="isDragOver = true"
              @dragleave.prevent="isDragOver = false"
              @drop.prevent="handleDrop"
              @click="triggerFileInput"
            >
              <input ref="fileInput" type="file" multiple accept=".pdf,.md,.txt" @change="handleFileSelect" hidden />
              
              <div v-if="files.length === 0" class="dropzone-empty">
                <div class="massive-plus">+</div>
                <div class="drop-msg">
                  <span class="primary">ATTACH DATA_SEEDS</span>
                  <span class="secondary">PDF / MARKDOWN / TXT</span>
                </div>
              </div>

              <div v-else class="file-manifest">
                <div v-for="(file, i) in files" :key="i" class="file-item-bauhaus">
                  <span class="f-ext">{{ file.name.split('.').pop().toUpperCase() }}</span>
                  <span class="f-name">{{ file.name }}</span>
                  <button class="f-remove" @click.stop="removeFile(i)">×</button>
                </div>
              </div>
            </div>

            <div class="input-group-bauhaus">
              <label>SIMULATION_OBJECTIVE</label>
              <textarea 
                v-model="formData.simulationRequirement"
                placeholder="What reality do you wish to manifest? Define your scenario, audience, or core question..."
                class="bauhaus-textarea"
              ></textarea>
            </div>

            <button 
              class="bauhaus-launch-btn" 
              @click="startSimulation" 
              :disabled="!canSubmit || loading"
            >
              <span v-if="!loading">INITIALIZE ENGINE_SEQUENCE</span>
              <span v-else class="bauhaus-spinner-small"></span>
              <span class="launch-arrow" v-if="!loading">→</span>
            </button>
          </div>

          <!-- RIGHT: SPECS & CAPABILITIES -->
          <div class="init-card specs-card">
            <header class="card-header">
              <span class="step-tag">TECH_SPECS</span>
              <h3>ARCHITECTURAL FLOW</h3>
            </header>

            <div class="capability-list">
              <div v-for="(step, i) in steps" :key="i" class="cap-item">
                <div class="cap-num">0{{ i + 1 }}</div>
                <div class="cap-content">
                  <span class="cap-title">{{ step.item }}</span>
                  <span class="cap-desc">{{ step.desc }}</span>
                </div>
              </div>
            </div>

            <div class="system-metrics">
              <div class="metric-box">
                <label>ENGINE_MODEL</label>
                <div class="val">GraphRAG_LTM_V2</div>
              </div>
              <div class="metric-box">
                <label>AGENT_CAPACITY</label>
                <div class="val">∞ SCALABLE</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- HISTORY / ARCHIVE -->
      <section class="archive-section">
        <header class="archive-header">
          <div class="header-line"></div>
          <h2>HISTORICAL_DATABASE</h2>
        </header>
        <HistoryDatabase borderless />
      </section>
    </main>

    <footer class="bauhaus-footer">
      <div class="footer-block">© 2026 ASK THE PEOPLE // NO_RIGHTS_RESERVED</div>
      <div class="footer-block">ENCODED IN MODERNIST_BRUTAL</div>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import HistoryDatabase from "../components/HistoryDatabase.vue";

const router = useRouter();
const formData = ref({ simulationRequirement: "" });
const files = ref([]);
const loading = ref(false);
const isDragOver = ref(false);
const fileInput = ref(null);

const steps = [
  { item: "GRAPH_SYNTHESIS", desc: "Recursive extraction of knowledge nodes." },
  { item: "AGENT_DEPLOYMENT", desc: "Injection of hyper-realistic digital twins." },
  { item: "SOCIAL_DYNAMICS", desc: "Massively parallel interaction runtime." },
  { item: "EMERGENT_REPORTS", desc: "Real-time behavior pattern recognition." },
  { item: "DEEP_DIALOGUE", desc: "Direct interface with simulated crowds." },
];

const canSubmit = computed(() => formData.value.simulationRequirement.trim() !== "" && files.value.length > 0);

const triggerFileInput = () => fileInput.value?.click();
const handleFileSelect = (e) => addFiles(Array.from(e.target.files));
const addFiles = (newFiles) => {
  const valid = newFiles.filter((f) => ["pdf", "md", "txt"].includes(f.name.split(".").pop().toLowerCase()));
  files.value.push(...valid);
};
const removeFile = (i) => files.value.splice(i, 1);
const handleDrop = (e) => { isDragOver.value = false; addFiles(Array.from(e.dataTransfer.files)); };

const startSimulation = () => {
  if (!canSubmit.value || loading.value) return;
  loading.value = true;
  import("../store/pendingUpload.js").then(({ setPendingUpload }) => {
    setPendingUpload(files.value, formData.value.simulationRequirement);
    router.push({ name: "Process", params: { projectId: "new" } });
  });
};
</script>

<style scoped>
.bauhaus-home-root {
  min-height: 100vh;
  background-color: white;
  color: black;
  font-family: var(--font-sans);
  position: relative;
  overflow-x: hidden;
  padding-bottom: 60px;
}

/* DECORATIVE SHAPES */
.geo-decoration { position: absolute; z-index: 0; opacity: 0.8; pointer-events: none; }
.circle-red { width: 400px; height: 400px; border-radius: 50%; background: var(--atp-red); top: -100px; right: -100px; }
.square-blue { width: 300px; height: 300px; background: var(--atp-blue); bottom: 20%; left: -100px; transform: rotate(15deg); }
.triangle-yellow { 
  width: 0; height: 0; 
  border-left: 150px solid transparent; 
  border-right: 150px solid transparent; 
  border-bottom: 250px solid var(--atp-yellow);
  top: 40%; right: 5%; transform: rotate(-10deg);
}

.bauhaus-nav {
  height: 80px; padding: 0 40px;
  display: flex; justify-content: space-between; align-items: center;
  border-bottom: 4px solid var(--atp-black);
  background: var(--atp-white); position: sticky; top: 0; z-index: 100;
}
.brand-text { font-weight: 950; font-size: 1.5rem; letter-spacing: -1px; }
.brand-version { font-family: var(--font-mono); font-size: 10px; background: var(--atp-black); color: var(--atp-white); padding: 2px 8px; margin-left: 15px; }

.bauhaus-nav-link {
  font-family: var(--font-mono); font-weight: 900; font-size: 12px;
  text-decoration: none; color: var(--atp-black); border: 3px solid var(--atp-black); padding: 8px 20px;
  transition: 0.2s;
}
.bauhaus-nav-link:hover { background: var(--atp-yellow); transform: translate(-4px, -4px); box-shadow: 4px 4px 0 var(--atp-black); }

.bauhaus-main { max-width: 1400px; margin: 0 auto; padding: 60px 40px; position: relative; z-index: 1; }

.hero-brutal { display: flex; gap: 60px; margin-bottom: 100px; align-items: flex-end; }
.hero-left { flex: 1.4; }
.hero-right { flex: 1; padding-bottom: 20px; }

.status-ribbon { font-family: var(--font-mono); font-weight: 900; font-size: 11px; margin-bottom: 20px; }
.hero-title { font-size: clamp(4rem, 10vw, 10rem); line-height: 0.85; font-weight: 950; letter-spacing: -4px; text-transform: uppercase; }
.text-blue { color: var(--atp-blue); }
.text-brutal { text-shadow: 4px 4px 0 var(--atp-yellow); }

.hero-manifesto { font-size: 1.4rem; line-height: 1.4; font-weight: 600; color: #333; }

.init-grid { display: grid; grid-template-columns: 1.6fr 1fr; gap: 40px; }

.init-card { background: var(--atp-white); border: 4px solid var(--atp-black); padding: 40px; box-shadow: 15px 15px 0 var(--atp-black); }
.card-header { border-bottom: 4px solid var(--atp-black); padding-bottom: 20px; margin-bottom: 30px; display: flex; align-items: center; gap: 20px; }
.step-tag { background: var(--atp-black); color: var(--atp-white); font-family: var(--font-mono); font-weight: 900; font-size: 11px; padding: 4px 10px; }
.card-header h3 { font-weight: 950; font-size: 1.4rem; letter-spacing: -0.5px; }

.bauhaus-dropzone {
  height: 200px; border: 3px dashed var(--atp-black); display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: 0.2s; background: #fafafa; margin-bottom: 30px;
}
.bauhaus-dropzone:hover, .bauhaus-dropzone.is-active { background: var(--atp-yellow); border-style: solid; }
.massive-plus { font-size: 50px; font-weight: 950; line-height: 1; }
.drop-msg { margin-left: 20px; display: flex; flex-direction: column; }
.drop-msg .primary { font-weight: 950; font-size: 1.1rem; }
.drop-msg .secondary { font-family: var(--font-mono); font-size: 10px; font-weight: 800; opacity: 0.6; }

.file-manifest { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; width: 100%; padding: 20px; }
.file-item-bauhaus { 
  background: var(--atp-white); border: 2.5px solid var(--atp-black); padding: 6px 10px; display: flex; align-items: center; gap: 10px;
  font-size: 11px; font-weight: 900;
}
.f-ext { color: var(--atp-blue); }
.f-name { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.f-remove { background: none; border: none; font-size: 18px; font-weight: 950; cursor: pointer; color: var(--atp-red); }

.input-group-bauhaus label { display: block; font-weight: 950; font-size: 11px; margin-bottom: 10px; letter-spacing: 1px; }
.bauhaus-textarea {
  width: 100%; height: 120px; border: 3px solid var(--atp-black); padding: 15px; font-family: inherit; font-size: 1rem;
  font-weight: 600; outline: none; transition: 0.2s; resize: none;
}
.bauhaus-textarea:focus { background: var(--atp-white); box-shadow: 8px 8px 0 var(--atp-yellow); transform: translate(-4px, -4px); }

.bauhaus-launch-btn {
  width: 100%; height: 70px; margin-top: 30px; background: var(--atp-black); color: var(--atp-white);
  border: none; font-weight: 950; font-size: 1.2rem; cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: 20px; transition: 0.2s;
}
.bauhaus-launch-btn:not(:disabled):hover { background: var(--atp-blue); transform: translate(-6px, -6px); box-shadow: 10px 10px 0 var(--atp-black); }
.bauhaus-launch-btn:disabled { opacity: 0.2; cursor: not-allowed; }

.cap-item { display: flex; gap: 20px; margin-bottom: 25px; }
.cap-num { 
  width: 32px; height: 32px; border: 2.5px solid var(--atp-black); display: flex; align-items: center; justify-content: center;
  font-family: var(--font-mono); font-weight: 950; font-size: 13px; flex-shrink: 0;
}
.cap-title { display: block; font-weight: 950; font-size: 11px; margin-bottom: 4px; }
.cap-desc { font-size: 12px; color: #555; font-weight: 600; line-height: 1.4; }

.system-metrics { border-top: 3px solid var(--atp-black); padding-top: 30px; display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.metric-box label { font-size: 9px; font-weight: 950; color: #888; display: block; margin-bottom: 5px; }
.metric-box .val { font-family: var(--font-mono); font-weight: 950; font-size: 1.1rem; }

.archive-section { margin-top: 100px; }
.archive-header { display: flex; align-items: center; gap: 20px; margin-bottom: 40px; }
.header-line { flex: 1; height: 4px; background: var(--atp-black); }
.archive-header h2 { font-weight: 950; font-size: 2rem; letter-spacing: -1px; }

.bauhaus-footer {
  padding: 40px; border-top: 4px solid var(--atp-black); display: flex; justify-content: space-between;
  font-family: var(--font-mono); font-weight: 900; font-size: 11px;
}

@media (max-width: 1100px) {
  .hero-brutal { flex-direction: column; align-items: flex-start; gap: 30px; }
  .init-grid { grid-template-columns: 1fr; }
  .hero-title { font-size: 5rem; }
}

.bauhaus-spinner-small { width: 24px; height: 24px; border: 4px solid var(--atp-white); border-top-color: var(--atp-yellow); border-radius: 50%; animation: spin 1s infinite linear; }
@keyframes spin { to { transform: rotate(360deg); } }

</style>
