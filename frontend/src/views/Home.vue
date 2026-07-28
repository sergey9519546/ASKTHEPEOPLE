<template>
  <div class="bauhaus-interface selection:bg-bauhaus-red selection:text-white">
    <!-- HEADER -->
    <header class="bg-white/80 backdrop-blur-md sticky top-0 z-50 flex flex-col md:flex-row justify-between items-center w-full px-10 py-4 gap-6 border-b border-slate-200">
        <div class="flex items-center gap-6">
            <div class="text-xl font-bold tracking-tight uppercase leading-none px-3 py-1 border border-slate-200 rounded-lg bg-slate-50">ATP</div>
            <div class="hidden md:flex flex-col text-[9px] font-bold font-mono opacity-50 leading-tight uppercase tracking-widest">
                <span>Terminal_Auth: active</span>
                <span>Uptime: 99.98%</span>
            </div>
        </div>
        <nav class="flex gap-1 items-center bg-slate-100/50 p-1 rounded-xl border border-slate-200/50">
            <button @click="scrollToSection('hero')" class="bg-slate-900 text-white px-6 py-2 rounded-lg text-xs font-medium uppercase tracking-wider hover:bg-slate-800 transition-colors border-none shadow-none">DEPLOY</button>
            <button @click="scrollToSection('sessions')" class="px-6 py-2 text-xs font-medium uppercase tracking-wider rounded-lg hover:bg-slate-100 hover:text-slate-900 border-none bg-transparent shadow-none">ANALYTICS</button>
            <button @click="scrollToSection('archive')" class="px-6 py-2 text-xs font-medium uppercase tracking-wider rounded-lg hover:bg-slate-100 hover:text-slate-900 border-none bg-transparent shadow-none">ARCHIVE</button>
        </nav>
        <div class="flex items-center gap-6">
            <div class="hidden lg:flex flex-col items-end text-[10px] font-mono font-bold leading-none uppercase">
                <span class="text-rose-500">// LINK_ESTABLISHED</span>
                <span class="opacity-40">node_id: 8172_alpha</span>
            </div>
            <div class="flex gap-2">
                <button class="w-9 h-9 border border-slate-200 rounded-lg flex items-center justify-center hover:bg-slate-50 p-0 bg-white"><span class="material-symbols-outlined text-slate-600">person</span></button>
                <button @click="showSettings = true" class="w-9 h-9 border border-slate-200 rounded-lg flex items-center justify-center hover:bg-slate-50 p-0 bg-white" title="System Settings"><span class="material-symbols-outlined text-slate-600">settings_input_component</span></button>
            </div>
        </div>
    </header>

    <!-- SIDEBAR -->
    <aside class="hidden lg:flex fixed left-6 top-24 bottom-6 w-20 hover:w-64 bg-white/90 backdrop-blur-md border border-slate-200/80 rounded-2xl flex-col z-40 pt-12 transition-all duration-300 group overflow-hidden shadow-xl shadow-slate-100/50">
        <div class="flex-grow space-y-2 px-3">
            <a class="flex items-center w-full px-4 py-4 rounded-xl hover:bg-rose-50 hover:text-rose-600 transition-colors text-slate-600" href="#">
                <span class="material-symbols-outlined text-xl min-w-[32px]">sensors</span>
                <span class="ml-4 text-xs font-semibold uppercase tracking-wider whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">Realtime_Stream</span>
            </a>
            <a class="flex items-center w-full px-4 py-4 rounded-xl hover:bg-amber-50 hover:text-amber-600 transition-colors text-slate-600" href="#">
                <span class="material-symbols-outlined text-xl min-w-[32px]">account_balance</span>
                <span class="ml-4 text-xs font-semibold uppercase tracking-wider whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">Macro_Econ</span>
            </a>
            <a class="flex items-center w-full px-4 py-4 rounded-xl hover:bg-blue-50 hover:text-blue-600 transition-colors text-slate-600" href="#">
                <span class="material-symbols-outlined text-xl min-w-[32px]">biotech</span>
                <span class="ml-4 text-xs font-semibold uppercase tracking-wider whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">Sovereign_Tech</span>
            </a>
            <a class="flex items-center w-full px-4 py-4 rounded-xl hover:bg-slate-100 hover:text-slate-900 transition-colors text-slate-600" href="#">
                <span class="material-symbols-outlined text-xl min-w-[32px]">data_exploration</span>
                <span class="ml-4 text-xs font-semibold uppercase tracking-wider whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">Vector_Maps</span>
            </a>
        </div>
        <div class="p-3 bg-slate-50 border-t border-slate-100 rounded-b-2xl">
            <button @click="scrollToSection('hero')" class="w-full bg-slate-900 hover:bg-slate-800 text-white font-medium py-3 rounded-lg text-xs uppercase tracking-wider flex justify-center border-none shadow-none">
                <span class="group-hover:hidden">++</span>
                <span class="hidden group-hover:inline">NEW_ENTRY</span>
            </button>
        </div>
    </aside>

    <!-- MAIN CONTENT -->
    <!-- MAIN CONTENT -->
    <main class="lg:ml-28 pt-8 pb-24 px-6 md:px-16 min-h-screen">
        <!-- HERO / DEPLOY SECTION -->
        <section id="hero" class="py-16 flex flex-col items-start relative overflow-hidden border-b border-slate-200">
            <div class="absolute right-0 top-1/2 -translate-y-1/2 opacity-5 pointer-events-none">
                <svg height="400" viewBox="0 0 100 100" width="400">
                    <circle cx="50" cy="50" fill="none" r="48" stroke="currentColor" stroke-dasharray="2 2" stroke-width="0.5" class="text-slate-400"></circle>
                    <rect fill="none" height="60" stroke="currentColor" stroke-width="0.5" width="60" x="20" y="20" class="text-slate-400"></rect>
                    <path d="M0 50 L100 50 M50 0 L50 100" stroke="currentColor" stroke-width="0.2" class="text-slate-400"></path>
                </svg>
            </div>
            <div class="bg-slate-100 text-slate-600 px-3 py-1 rounded-full text-[10px] font-mono font-bold uppercase tracking-[0.3em] mb-6">
                COMMAND_INTERFACE // 00-CORE
            </div>
            <h1 class="text-[clamp(2.5rem,6vw,5rem)] font-extrabold leading-[1.05] tracking-tight mb-8 text-slate-900 uppercase">
                DECISION<br>MATRIX<span class="text-rose-500">.</span>
            </h1>
            
            <div class="w-full max-w-6xl space-y-12">
                <p class="text-lg md:text-xl font-normal max-w-2xl leading-relaxed text-slate-500 border-l-2 border-rose-500 pl-6 py-1">
                    High-fidelity consensus mapping. Simplified for rapid systemic evolution.
                </p>

                <!-- INITIALIZATION INTERFACE -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-8 items-stretch">
                    <!-- INPUT AREA -->
                    <div class="space-y-6 flex flex-col justify-between">
                        <div class="space-y-2 flex-grow flex flex-col">
                            <span class="text-xs font-semibold uppercase tracking-wider text-slate-400">Simulation Objective</span>
                            <textarea 
                                v-model="formData.simulationRequirement"
                                placeholder="What reality do you wish to manifest? Define your scenario, audience, or core question..."
                                class="w-full h-44 border border-slate-200 rounded-xl p-5 font-sans font-normal text-base focus:border-rose-500 focus:ring-4 focus:ring-rose-500/5 outline-none transition-all resize-none shadow-sm flex-grow"
                            ></textarea>
                        </div>
                        
                        <div class="flex gap-4">
                            <button @click="startSimulation" :disabled="!canSubmit || loading"
                                        class="w-full bg-slate-900 text-white p-5 rounded-xl font-medium text-base flex items-center justify-center gap-4 hover:bg-slate-800 transition-all group border-none shadow-md">
                                    <span v-if="!loading">INITIALIZE ENGINE SEQUENCE</span>
                                    <span v-else class="bauhaus-spinner-small"></span>
                                    <span class="material-symbols-outlined group-hover:translate-x-1.5 transition-transform text-slate-300">arrow_forward</span>
                                </button>
                        </div>
                    </div>

                    <!-- DROPZONE AREA -->
                    <div 
                        class="h-full border border-dashed border-slate-300 rounded-xl flex flex-col items-center justify-center p-8 transition-all relative min-h-[250px] bg-slate-50/50 hover:bg-slate-50 cursor-pointer"
                        :class="{ 'bg-rose-50/30 border-rose-400': isDragOver }"
                        @dragover.prevent="isDragOver = true"
                        @dragleave.prevent="isDragOver = false"
                        @drop.prevent="handleDrop"
                        @click="triggerFileInput"
                    >
                        <input ref="fileInput" type="file" multiple accept=".pdf,.md,.txt" @change="handleFileSelect" hidden />
                        
                        <div v-if="files.length === 0" class="text-center group">
                            <span class="material-symbols-outlined text-5xl mb-3 text-slate-400 group-hover:scale-105 transition-transform">upload_file</span>
                            <div class="text-xs font-semibold uppercase tracking-widest text-slate-600">Attach Data Seeds</div>
                            <div class="text-[10px] font-mono opacity-40 mt-1">PDF / MARKDOWN / TXT</div>
                        </div>

                        <div v-else class="w-full grid grid-cols-1 gap-2">
                           <div v-for="(file, i) in files" :key="i" class="flex items-center justify-between bg-white border border-slate-200 rounded-lg p-3 group shadow-sm">
                                <div class="flex items-center gap-3 overflow-hidden">
                                    <span class="text-rose-500 font-mono font-bold text-[9px] bg-rose-50 px-2 py-0.5 rounded">{{ file.name.split('.').pop().toUpperCase() }}</span>
                                    <span class="font-medium text-xs text-slate-700 truncate">{{ file.name }}</span>
                                </div>
                                <button @click.stop="removeFile(i)" class="w-6 h-6 hover:bg-slate-100 rounded-full flex items-center justify-center border-none bg-transparent shadow-none p-0 text-sm">×</button>
                           </div>
                           <button class="mt-4 text-[10px] font-semibold tracking-wider uppercase text-slate-500 hover:text-rose-500 border-none bg-transparent shadow-none" @click.stop="triggerFileInput">+ Add More Files</button>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- SESSIONS / ANALYTICS SECTION -->
        <section id="sessions" class="py-16">
            <div class="flex flex-col md:flex-row justify-between items-baseline mb-10 border-b border-slate-200 pb-4">
                <h2 class="text-2xl md:text-3xl font-bold uppercase tracking-tight text-slate-800">Live Sessions</h2>
                <div class="flex items-center gap-6 font-mono text-[10px] font-bold text-slate-400">
                    <span class="flex items-center gap-2 text-rose-500">
                        <span class="w-2 h-2 rounded-full bg-rose-500 animate-pulse"></span> Streaming Data
                    </span>
                    <span class="opacity-70">Nodes Connected: 82.4K</span>
                </div>
            </div>
            
            <div class="grid grid-cols-1 md:grid-cols-12 gap-6 font-sans">
                <!-- Large Placeholder Vote Card -->
                <div class="md:col-span-8 bg-white border border-slate-200 p-0 flex flex-col group relative overflow-hidden rounded-2xl shadow-xl shadow-slate-100/50">
                    <div class="flex border-b border-slate-100 bg-slate-50/50">
                        <div class="bg-rose-500 text-white p-5 aspect-square flex items-center justify-center">
                            <span class="material-symbols-outlined text-2xl">policy</span>
                        </div>
                        <div class="flex-grow p-5 flex items-center justify-between">
                            <span class="text-xs font-semibold tracking-wider text-slate-500 uppercase">Sub Module: Sovereign AI</span>
                            <span class="text-[9px] font-mono font-bold text-slate-400">Ref ID: 9912-X</span>
                        </div>
                    </div>
                    <div class="p-8 md:p-10">
                        <h3 class="text-2xl md:text-3xl font-extrabold leading-snug tracking-tight mb-8 text-slate-800 uppercase">
                            GRANT LEGAL PERSONHOOD TO SYNTHETIC AGENTS?
                        </h3>
                        <div class="grid grid-cols-1 md:grid-cols-12 gap-8 items-center">
                            <div class="space-y-4 md:col-span-8">
                                <div class="flex justify-between items-end">
                                    <span class="text-xs font-semibold uppercase tracking-wider text-slate-400">Affirmative</span>
                                    <span class="text-2xl font-bold text-slate-800">64.2%</span>
                                </div>
                                <div class="h-6 bg-slate-100 rounded-full relative overflow-hidden">
                                    <div class="absolute inset-y-0 left-0 bg-rose-500 rounded-full" style="width: 64.2%;"></div>
                                </div>
                            </div>
                            <button class="md:col-span-4 bg-slate-900 text-white py-4 rounded-xl text-xs font-semibold uppercase tracking-wider hover:bg-slate-800 transition-colors flex items-center justify-center gap-2 border-none shadow-md">
                                Vote Now <span class="material-symbols-outlined text-sm">bolt</span>
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Small Vote Cards Placeholder -->
                <div class="md:col-span-4 flex flex-col gap-4">
                    <div class="flex-grow bg-white border border-slate-200 p-6 rounded-2xl flex flex-col justify-between hover:border-slate-300 transition-colors cursor-pointer group shadow-sm">
                        <div>
                            <div class="flex justify-between mb-6">
                                <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Urban Systems</span>
                                <span class="material-symbols-outlined text-slate-400">domain</span>
                            </div>
                            <h3 class="text-lg font-bold leading-snug text-slate-800 uppercase">REPLACE PUBLIC TRANSIT WITH AUTONOMOUS PODS?</h3>
                        </div>
                        <div class="flex justify-between items-end mt-6">
                            <div class="text-[10px] font-bold text-amber-600 bg-amber-50 px-2 py-0.5 rounded">Stage: Evaluation</div>
                            <span class="material-symbols-outlined text-slate-400 group-hover:translate-x-1 transition-transform">arrow_forward</span>
                        </div>
                    </div>
                    <div class="flex-grow bg-white border border-slate-200 p-6 rounded-2xl flex flex-col justify-between hover:border-slate-300 transition-all cursor-pointer group shadow-sm">
                        <div>
                            <div class="flex justify-between mb-6">
                                <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Data Privacy</span>
                                <span class="material-symbols-outlined text-slate-400">encrypted</span>
                            </div>
                            <h3 class="text-lg font-bold leading-snug text-slate-800 uppercase">GLOBAL MANDATORY BIO-ENCRYPTION FOR PAYMENTS?</h3>
                        </div>
                        <div class="flex justify-between items-end mt-6">
                            <div class="text-[10px] font-bold text-rose-600 bg-rose-50 px-2 py-0.5 rounded">Status: Critical</div>
                            <span class="material-symbols-outlined text-slate-400 group-hover:translate-x-1 transition-transform">arrow_forward</span>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- ARCHIVE SECTION -->
        <section id="archive" class="py-16 border-t border-slate-200">
            <div class="flex flex-col md:flex-row justify-between items-baseline mb-10 border-b border-slate-200 pb-4">
                <h2 class="text-2xl md:text-3xl font-bold uppercase tracking-tight text-slate-800">Archive DB</h2>
                <div class="text-[10px] font-mono font-bold text-slate-400 uppercase">Accessing Historical Knowledge Nodes...</div>
            </div>
            
            <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
                <HistoryDatabase borderless />
            </div>
        </section>

        <!-- METRICS & SYSTEM INFO -->
        <section class="py-16 border-t border-slate-200">
            <div class="flex flex-col md:flex-row gap-8">
                <div class="w-full md:w-1/3">
                    <div class="bg-slate-900 text-white p-8 rounded-2xl flex flex-col justify-between h-full min-h-[250px] shadow-md">
                        <div>
                            <h4 class="text-[10px] font-mono font-bold tracking-[0.2em] mb-4 opacity-50 uppercase">System Analytics</h4>
                            <p class="text-2xl font-bold leading-snug uppercase mb-6">The geometry of modern consensus.</p>
                        </div>
                        <div class="space-y-4">
                            <div class="text-[9px] font-mono opacity-50 uppercase">Current Processing Cycle: 8.2s</div>
                            <div class="w-full h-1 bg-white/20 rounded-full">
                                <div class="w-2/3 h-full bg-rose-500 rounded-full"></div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="w-full md:w-2/3 grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div class="border border-slate-200 rounded-2xl p-6 bg-white flex flex-col justify-center shadow-sm">
                        <div class="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-4">Global Consensus Drift</div>
                        <div class="h-28 flex items-end gap-3 mb-3">
                            <div class="bg-rose-500 w-full rounded-t-sm" style="height: 40%"></div>
                            <div class="bg-slate-800 w-full rounded-t-sm" style="height: 70%"></div>
                            <div class="bg-blue-500 w-full rounded-t-sm" style="height: 55%"></div>
                            <div class="bg-emerald-500 w-full rounded-t-sm" style="height: 90%"></div>
                            <div class="bg-slate-400 w-full rounded-t-sm" style="height: 30%"></div>
                            <div class="bg-rose-400 w-full rounded-t-sm" style="height: 65%"></div>
                        </div>
                        <div class="flex justify-between text-[8px] font-mono font-bold text-slate-400">
                            <span>P_01</span><span>P_02</span><span>P_03</span><span>P_04</span><span>P_05</span><span>P_06</span>
                        </div>
                    </div>
                    <div class="border border-slate-200 rounded-2xl p-6 bg-white flex flex-col justify-between shadow-sm">
                        <div>
                            <div class="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">System Health</div>
                            <div class="text-4xl font-extrabold text-slate-800">0.998</div>
                        </div>
                        <div class="flex gap-1.5 mt-4">
                            <span class="w-3 h-3 bg-rose-500 rounded-full"></span>
                            <span class="w-3 h-3 bg-blue-500 rounded-full"></span>
                            <span class="w-3 h-3 bg-emerald-500 rounded-full"></span>
                            <span class="w-3 h-3 bg-slate-900 rounded-full"></span>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- TEMPLATE GALLERY -->
        <section class="py-16 border-t border-slate-200 bg-slate-900 text-white rounded-2xl p-8 md:p-16 relative overflow-hidden shadow-xl">
            <div class="absolute inset-0 opacity-5 pointer-events-none">
                <div class="w-full h-full" style="background-image: radial-gradient(circle at 2px 2px, white 1px, transparent 0); background-size: 24px 24px;"></div>
            </div>
            <div class="relative z-10 flex flex-col items-center text-center">
                <span class="font-mono text-[10px] font-semibold tracking-[0.4em] mb-6 border border-white/20 px-3 py-1.5 rounded-full uppercase">Core Seed Templates</span>
                <h2 class="text-3xl md:text-5xl font-extrabold leading-tight mb-10 tracking-tight uppercase">READY TO INPUT?</h2>
                
                <div v-if="templates.length" class="grid grid-cols-1 md:grid-cols-3 gap-4 w-full max-w-5xl">
                    <button 
                        v-for="tmp in templates" 
                        :key="tmp.id"
                        @click="selectTemplate(tmp)"
                        class="bg-white/10 hover:bg-white text-white hover:text-slate-900 p-6 rounded-xl transition-all border-none shadow-none text-left flex flex-col justify-between min-h-[160px]"
                    >
                        <div class="flex justify-between w-full mb-4">
                           <span class="text-xl">{{ tmp.icon }}</span>
                           <span class="material-symbols-outlined text-sm">add_circle</span>
                        </div>
                        <div>
                            <div class="font-bold text-sm mb-1">{{ tmp.name }}</div>
                            <div class="text-[9px] opacity-60 font-normal leading-normal">{{ tmp.description }}</div>
                        </div>
                    </button>
                </div>
            </div>
        </section>
    </main>

    <!-- MOBILE NAV -->
    <nav class="md:hidden fixed bottom-0 left-0 w-full h-16 z-50 flex bg-white/95 backdrop-blur-md border-t border-slate-200">
        <button @click="scrollToSection('hero')" class="flex-1 flex flex-col items-center justify-center bg-slate-900 text-white border-none rounded-none">
            <span class="material-symbols-outlined text-lg mb-0.5">dashboard_customize</span>
            <span class="text-[8px] font-bold uppercase tracking-wider">CORE</span>
        </button>
        <button @click="scrollToSection('sessions')" class="flex-1 flex flex-col items-center justify-center bg-transparent text-slate-600 border-none rounded-none">
            <span class="material-symbols-outlined text-lg mb-0.5">analytics</span>
            <span class="text-[8px] font-bold uppercase tracking-wider">DATA</span>
        </button>
        <button @click="scrollToSection('archive')" class="flex-1 flex flex-col items-center justify-center bg-transparent text-slate-600 border-none rounded-none">
            <span class="material-symbols-outlined text-lg mb-0.5">history</span>
            <span class="text-[8px] font-bold uppercase tracking-wider">ARCHIVE</span>
        </button>
    </nav>

    <!-- FAB -->
    <div class="fixed bottom-8 right-8 z-50 hidden md:block">
        <button @click="scrollToSection('hero')" class="w-14 h-14 bg-rose-500 text-white rounded-full flex items-center justify-center shadow-lg hover:bg-rose-600 transition-colors border-none p-0" title="New Objective">
            <span class="material-symbols-outlined text-2xl">add</span>
        </button>
    </div>

    <!-- SETTINGS MODAL -->
    <SettingsModal v-if="showSettings" @close="showSettings = false" />
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { getTemplates } from "../api/graph";
import HistoryDatabase from "../components/HistoryDatabase.vue";
import SettingsModal from "../components/SettingsModal.vue";

const router = useRouter();
const showSettings = ref(false);
const formData = ref({ simulationRequirement: "" });
const files = ref([]);
const loading = ref(false);
const isDragOver = ref(false);
const fileInput = ref(null);
const templates = ref([]);

const fetchTemplates = async () => {
  try {
    const res = await getTemplates();
    if (res.success) {
      templates.value = res.data;
    }
  } catch (err) {
    console.warn("Failed to fetch templates:", err);
  }
};

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

const selectTemplate = (template) => {
  formData.value.simulationRequirement = template.prompt_base + "\n\n" + template.suggested_ontology_goal;
};

const scrollToSection = (id) => {
  const el = document.getElementById(id);
  if (el) el.scrollIntoView({ behavior: 'smooth' });
};

fetchTemplates();
</script>

<style scoped>
.bauhaus-interface {
  background-color: #F8F9FA;
  color: #0F0F0F;
  font-family: 'Space Grotesk', sans-serif;
}

.atelier-grid {
    background-image: 
        linear-gradient(to right, #e5e7eb 1px, transparent 1px),
        linear-gradient(to bottom, #e5e7eb 1px, transparent 1px);
    background-size: 40px 40px;
}

.command-center-header {
    border-bottom: 4px solid black;
}

.stat-value {
    font-variant-numeric: tabular-nums;
    font-family: 'JetBrains Mono', monospace;
}

.geometric-decoration {
    clip-path: polygon(0% 0%, 100% 0%, 100% 75%, 75% 100%, 0% 100%);
}

.bauhaus-spinner-small { 
  width: 24px; 
  height: 24px; 
  border: 4px solid white; 
  border-top-color: #E63946; 
  border-radius: 50%; 
  animation: spin 1s infinite linear; 
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Ensure Material symbols line up */
.material-symbols-outlined {
    font-variation-settings: 'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 24;
}

/* Custom Overrides for imported components if needed */
:deep(.simulation-history-workbench) {
  border: none !important;
  padding: 0 !important;
  margin-top: 0 !important;
}
</style>
