<template>
  <div class="bauhaus-interface selection:bg-bauhaus-red selection:text-white">
    <!-- HEADER -->
    <header class="bg-white sticky top-0 z-50 command-center-header flex flex-col md:flex-row justify-between items-center w-full px-10 py-4 gap-6 border-b-4 border-black shadow-sm">
        <div class="flex items-center gap-6">
            <div class="text-3xl font-black tracking-tighter uppercase leading-none border-4 border-black px-3 py-1">ATP</div>
            <div class="hidden md:flex flex-col text-[9px] font-bold font-mono opacity-60 leading-tight uppercase tracking-widest">
                <span>Terminal_Auth: active</span>
                <span>Uptime: 99.98%</span>
            </div>
        </div>
        <nav class="flex gap-0 items-center border-2 border-black overflow-hidden">
            <button @click="scrollToSection('hero')" class="bg-black text-white px-8 py-3 text-xs font-black uppercase tracking-widest hover:bg-bauhaus-red transition-colors">DEPLOY</button>
            <button @click="scrollToSection('sessions')" class="px-8 py-3 text-xs font-black uppercase tracking-widest border-l-2 border-black hover:bg-black hover:text-white transition-all">ANALYTICS</button>
            <button @click="scrollToSection('archive')" class="px-8 py-3 text-xs font-black uppercase tracking-widest border-l-2 border-black hover:bg-black hover:text-white transition-all">ARCHIVE</button>
        </nav>
        <div class="flex items-center gap-8">
            <div class="hidden lg:flex flex-col items-end text-[10px] font-mono font-bold leading-none uppercase">
                <span class="text-bauhaus-red">// LINK_ESTABLISHED</span>
                <span class="opacity-40">node_id: 8172_alpha</span>
            </div>
            <div class="flex gap-1">
                <button class="w-10 h-10 border-2 border-black flex items-center justify-center hover:bg-black hover:text-white p-0"><span class="material-symbols-outlined">person</span></button>
                <button class="w-10 h-10 border-2 border-black flex items-center justify-center hover:bg-black hover:text-white p-0"><span class="material-symbols-outlined">settings_input_component</span></button>
            </div>
        </div>
    </header>

    <!-- SIDEBAR -->
    <aside class="hidden lg:flex fixed left-0 top-0 h-full w-24 hover:w-72 bg-white border-r-4 border-black flex-col z-40 pt-28 transition-all duration-300 group overflow-hidden">
        <div class="flex-grow">
            <a class="flex items-center w-full px-8 py-6 hover:bg-bauhaus-red hover:text-white border-b-2 border-black/5 transition-colors" href="#">
                <span class="material-symbols-outlined text-2xl min-w-[40px]">sensors</span>
                <span class="ml-4 text-xs font-black uppercase tracking-[0.3em] whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">Realtime_Stream</span>
            </a>
            <a class="flex items-center w-full px-8 py-6 hover:bg-bauhaus-yellow hover:text-black border-b-2 border-black/5 transition-colors" href="#">
                <span class="material-symbols-outlined text-2xl min-w-[40px]">account_balance</span>
                <span class="ml-4 text-xs font-black uppercase tracking-[0.3em] whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">Macro_Econ</span>
            </a>
            <a class="flex items-center w-full px-8 py-6 hover:bg-bauhaus-blue hover:text-white border-b-2 border-black/5 transition-colors" href="#">
                <span class="material-symbols-outlined text-2xl min-w-[40px]">biotech</span>
                <span class="ml-4 text-xs font-black uppercase tracking-[0.3em] whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">Sovereign_Tech</span>
            </a>
            <a class="flex items-center w-full px-8 py-6 hover:bg-black hover:text-white border-b-2 border-black/5 transition-colors" href="#">
                <span class="material-symbols-outlined text-2xl min-w-[40px]">data_exploration</span>
                <span class="ml-4 text-xs font-black uppercase tracking-[0.3em] whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">Vector_Maps</span>
            </a>
        </div>
        <div class="p-4 bg-black group-hover:p-6 transition-all">
            <button @click="scrollToSection('hero')" class="w-full text-white font-black py-4 text-xs uppercase tracking-[0.4em] flex justify-center border-none hover:bg-transparent shadow-none hover:translate-x-0 hover:translate-y-0">
                <span class="group-hover:hidden">++</span>
                <span class="hidden group-hover:inline">NEW_ENTRY</span>
            </button>
        </div>
    </aside>

    <!-- MAIN CONTENT -->
    <main class="lg:ml-24 pt-4 pb-24 px-6 md:px-12 atelier-grid min-h-screen">
        <!-- HERO / DEPLOY SECTION -->
        <section id="hero" class="py-20 flex flex-col items-start relative overflow-hidden border-b-4 border-black">
            <div class="absolute right-0 top-1/2 -translate-y-1/2 opacity-10 pointer-events-none">
                <svg height="400" viewBox="0 0 100 100" width="400">
                    <circle cx="50" cy="50" fill="none" r="48" stroke="black" stroke-dasharray="2 2" stroke-width="0.5"></circle>
                    <rect fill="none" height="60" stroke="black" stroke-width="0.5" width="60" x="20" y="20"></rect>
                    <path d="M0 50 L100 50 M50 0 L50 100" stroke="black" stroke-width="0.2"></path>
                </svg>
            </div>
            <div class="bg-black text-white px-3 py-1 text-[10px] font-mono font-bold uppercase tracking-[0.5em] mb-8">
                COMMAND_INTERFACE // 00-CORE
            </div>
            <h1 class="text-[clamp(4rem,10vw,10rem)] font-black leading-[0.75] tracking-tighter mb-12 uppercase">
                DECISION<br>MATRIX<span class="text-bauhaus-red">.</span>
            </h1>
            
            <div class="w-full max-w-6xl space-y-12">
                <p class="text-2xl md:text-3xl font-light max-w-2xl leading-tight opacity-90 border-l-8 border-black pl-8 py-2">
                    High-fidelity consensus mapping. Simplified for rapid systemic evolution.
                </p>

                <!-- INITIALIZATION INTERFACE -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
                    <!-- INPUT AREA -->
                    <div class="space-y-6">
                        <div class="bauhaus-input-container">
                            <span class="text-xs font-black uppercase text-gray-500">Simulation Objective</span>
                            <textarea 
                                v-model="formData.simulationRequirement"
                                placeholder="What reality do you wish to manifest? Define your scenario, audience, or core question..."
                                class="w-full h-48 border-4 border-black p-6 font-body font-bold text-lg focus:bg-bauhaus-yellow/5 outline-none transition-colors resize-none"
                            ></textarea>
                        </div>
                        
                        <div class="flex flex-col md:flex-row gap-4">
                            <button @click="startSimulation" :disabled="!canSubmit || loading"
                                        class="w-full bg-black text-white p-6 font-black text-lg flex items-center justify-center gap-4 hover:bg-bauhaus-red transition-all group active:translate-y-1">
                                    <span v-if="!loading">INITIALIZE ENGINE SEQUENCE</span>
                                    <span v-else class="bauhaus-spinner-small"></span>
                                    <span class="material-symbols-outlined group-hover:translate-x-2 transition-transform">arrow_forward</span>
                                </button>
                        </div>
                    </div>

                    <!-- DROPZONE AREA -->
                    <div 
                        class="h-full border-4 border-black border-dashed flex flex-col items-center justify-center p-8 transition-all relative min-h-[300px]"
                        :class="{ 'bg-bauhaus-yellow/20 border-solid': isDragOver }"
                        @dragover.prevent="isDragOver = true"
                        @dragleave.prevent="isDragOver = false"
                        @drop.prevent="handleDrop"
                        @click="triggerFileInput"
                    >
                        <input ref="fileInput" type="file" multiple accept=".pdf,.md,.txt" @change="handleFileSelect" hidden />
                        
                        <div v-if="files.length === 0" class="text-center group cursor-pointer">
                            <span class="material-symbols-outlined text-8xl mb-4 group-hover:scale-110 transition-transform">upload_file</span>
                            <div class="text-xs font-black uppercase tracking-[0.3em]">Attach Data Seeds</div>
                            <div class="text-[10px] font-mono opacity-40 mt-2">PDF / MARKDOWN / TXT</div>
                        </div>

                        <div v-else class="w-full grid grid-cols-1 gap-2">
                           <div v-for="(file, i) in files" :key="i" class="flex items-center justify-between bg-white border-2 border-black p-3 group">
                                <div class="flex items-center gap-3 overflow-hidden">
                                    <span class="text-bauhaus-red font-mono font-bold text-[10px]">{{ file.name.split('.').pop().toUpperCase() }}</span>
                                    <span class="font-bold text-xs truncate">{{ file.name }}</span>
                                </div>
                                <button @click.stop="removeFile(i)" class="p-1 hover:text-bauhaus-red border-none bg-transparent shadow-none hover:translate-x-0 hover:translate-y-0 text-lg">×</button>
                           </div>
                           <button class="mt-4 text-[10px] font-black uppercase underline hover:text-bauhaus-red border-none bg-transparent shadow-none hover:translate-x-0 hover:translate-y-0" @click.stop="triggerFileInput">Add More Files</button>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- SESSIONS / ANALYTICS SECTION -->
        <section id="sessions" class="py-16">
            <div class="flex flex-col md:flex-row justify-between items-baseline mb-12 border-b-2 border-black pb-4">
                <h2 class="text-6xl font-black uppercase tracking-tighter text-bauhaus-blue">Live Sessions</h2>
                <div class="flex items-center gap-6 font-mono text-[11px] font-bold">
                    <span class="flex items-center gap-2 text-bauhaus-red">
                        <span class="w-2 h-2 rounded-full bg-bauhaus-red animate-pulse"></span> Streaming Data
                    </span>
                    <span class="opacity-40">Nodes Connected: 82.4K</span>
                </div>
            </div>
            
            <div class="grid grid-cols-1 md:grid-cols-12 gap-4 font-mono">
                <!-- Large Placeholder Vote Card (Maintains design) -->
                <div class="md:col-span-8 bg-white border-4 border-black p-0 flex flex-col group relative overflow-hidden shadow-[12px_12px_0px_0px_rgba(0,0,0,1)]">
                    <div class="flex border-b-4 border-black">
                        <div class="bg-bauhaus-red text-white p-6 aspect-square flex items-center justify-center">
                            <span class="material-symbols-outlined text-4xl">policy</span>
                        </div>
                        <div class="flex-grow p-6 flex items-center justify-between">
                            <span class="text-xs font-black tracking-widest">Sub Module: Sovereign AI</span>
                            <span class="text-[10px] font-bold opacity-40">Ref ID: 9912-X</span>
                        </div>
                    </div>
                    <div class="p-8 md:p-12">
                        <h3 class="text-4xl md:text-6xl font-black font-body leading-[0.85] tracking-tighter mb-12 uppercase">
                            GRANT LEGAL PERSONHOOD TO SYNTHETIC AGENTS?
                        </h3>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
                            <div class="space-y-6">
                                <div class="flex justify-between items-end">
                                    <span class="text-xs font-black uppercase">Affirmative</span>
                                    <span class="text-4xl font-black stat-value">64.2%</span>
                                </div>
                                <div class="h-12 bg-black/5 border-2 border-black relative overflow-hidden">
                                    <div class="absolute inset-y-0 left-0 bg-bauhaus-red" style="width: 64.2%;"></div>
                                    <div class="absolute inset-y-0 left-0 w-full flex items-center px-4 mix-blend-difference text-white text-[10px] font-black">Progress Meter</div>
                                </div>
                            </div>
                            <button class="h-full bg-black text-white p-8 text-sm font-black uppercase tracking-[0.4em] hover:bg-bauhaus-blue transition-colors flex items-center justify-center gap-4 border-none shadow-none hover:translate-x-0 hover:translate-y-0">
                                Vote Now <span class="material-symbols-outlined">bolt</span>
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Small Vote Cards Placeholder -->
                <div class="md:col-span-4 flex flex-col gap-4">
                    <div class="flex-grow bg-bauhaus-yellow border-4 border-black p-8 flex flex-col justify-between hover:bg-white transition-colors cursor-pointer group shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]">
                        <div>
                            <div class="flex justify-between mb-8">
                                <span class="text-[10px] font-black uppercase border-b-2 border-black">Urban Systems</span>
                                <span class="material-symbols-outlined">domain</span>
                            </div>
                            <h3 class="text-2xl font-black font-body leading-none uppercase">REPLACE PUBLIC TRANSIT WITH AUTONOMOUS PODS?</h3>
                        </div>
                        <div class="flex justify-between items-end mt-8">
                            <div class="text-xs font-bold">Stage: Evaluation</div>
                            <span class="material-symbols-outlined group-hover:translate-x-2 transition-transform">arrow_forward</span>
                        </div>
                    </div>
                    <div class="flex-grow bg-white border-4 border-black p-8 flex flex-col justify-between hover:bg-bauhaus-blue hover:text-white transition-colors cursor-pointer group shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]">
                        <div>
                            <div class="flex justify-between mb-8">
                                <span class="text-[10px] font-black uppercase border-b-2 border-black">Data Privacy</span>
                                <span class="material-symbols-outlined">encrypted</span>
                            </div>
                            <h3 class="text-2xl font-black font-body leading-none uppercase">GLOBAL MANDATORY BIO-ENCRYPTION FOR PAYMENTS?</h3>
                        </div>
                        <div class="flex justify-between items-end mt-8">
                            <div class="text-xs font-bold">Status: Critical</div>
                            <span class="material-symbols-outlined group-hover:translate-x-2 transition-transform">arrow_forward</span>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- ARCHIVE SECTION -->
        <section id="archive" class="py-24 border-t-4 border-black">
            <div class="flex flex-col md:flex-row justify-between items-baseline mb-12 border-b-2 border-black pb-4">
                <h2 class="text-6xl font-black uppercase tracking-tighter">Archive DB</h2>
                <div class="text-[10px] font-mono font-bold opacity-40 uppercase">Accessing Historical Knowledge Nodes...</div>
            </div>
            
            <div class="bg-white border-4 border-black p-8 shadow-[16px_16px_0px_0px_rgba(230,57,70,1)]">
                <HistoryDatabase borderless />
            </div>
        </section>

        <!-- METRICS & SYSTEM INFO -->
        <section class="py-24 border-t-4 border-black">
            <div class="flex flex-col md:flex-row gap-16">
                <div class="w-full md:w-1/3">
                    <div class="bg-black text-white p-10 flex flex-col justify-between h-full geometric-decoration min-h-[300px]">
                        <div>
                            <h4 class="text-xs font-mono font-bold tracking-[0.4em] mb-6 opacity-60">System Analytics</h4>
                            <p class="text-4xl font-black leading-tight uppercase mb-8">The geometry of modern consensus.</p>
                        </div>
                        <div class="space-y-4">
                            <div class="text-[10px] font-mono opacity-50 uppercase">Current Processing Cycle: 8.2s</div>
                            <div class="w-full h-1 bg-white/20">
                                <div class="w-2/3 h-full bg-bauhaus-red"></div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="w-full md:w-2/3 grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div class="border-4 border-black p-8 bg-white flex flex-col justify-center shadow-[10px_10px_0px_0px_rgba(255,183,3,1)]">
                        <div class="text-[10px] font-black uppercase tracking-widest mb-6 opacity-40">Global Consensus Drift</div>
                        <div class="h-32 flex items-end gap-2 mb-4">
                            <div class="bg-bauhaus-red w-full" style="height: 40%"></div>
                            <div class="bg-black w-full" style="height: 70%"></div>
                            <div class="bg-bauhaus-blue w-full" style="height: 55%"></div>
                            <div class="bg-bauhaus-yellow w-full" style="height: 90%"></div>
                            <div class="bg-black w-full" style="height: 30%"></div>
                            <div class="bg-bauhaus-red w-full" style="height: 65%"></div>
                        </div>
                        <div class="flex justify-between text-[10px] font-mono font-bold">
                            <span>P_01</span><span>P_02</span><span>P_03</span><span>P_04</span><span>P_05</span><span>P_06</span>
                        </div>
                    </div>
                    <div class="border-4 border-black p-8 bg-white flex flex-col justify-between shadow-[10px_10px_0px_0px_rgba(29,53,87,1)]">
                        <div>
                            <div class="text-[10px] font-black uppercase tracking-widest mb-4 opacity-40">System Health</div>
                            <div class="text-6xl font-black stat-value">0.998</div>
                        </div>
                        <div class="flex gap-2">
                            <span class="w-4 h-4 bg-bauhaus-red"></span>
                            <span class="w-4 h-4 bg-bauhaus-blue"></span>
                            <span class="w-4 h-4 bg-bauhaus-yellow"></span>
                            <span class="w-4 h-4 bg-black"></span>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- TEMPLATE GALLERY (Integration) -->
        <section class="py-24 border-t-4 border-black bg-black text-white p-12 md:p-24 relative overflow-hidden">
            <div class="absolute inset-0 opacity-20 pointer-events-none">
                <div class="w-full h-full" style="background-image: radial-gradient(circle at 2px 2px, white 1px, transparent 0); background-size: 24px 24px;"></div>
            </div>
            <div class="relative z-10 flex flex-col items-center text-center">
                <span class="font-mono text-[11px] font-bold tracking-[0.8em] mb-8 border border-white/30 px-4 py-2 uppercase">Core Seed Templates</span>
                <h2 class="text-5xl md:text-8xl font-black leading-none mb-12 tracking-tighter uppercase">READY TO <br><span class="text-bauhaus-red">INPUT?</span></h2>
                
                <div v-if="templates.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-1 w-full max-w-6xl font-mono">
                    <button 
                        v-for="tmp in templates" 
                        :key="tmp.id"
                        @click="selectTemplate(tmp)"
                        class="bg-white text-black p-8 font-black uppercase text-xs hover:bg-bauhaus-yellow transition-all border-none shadow-none hover:translate-x-0 hover:translate-y-0 text-left flex flex-col justify-between min-h-[200px]"
                    >
                        <div class="flex justify-between w-full">
                           <span class="text-2xl">{{ tmp.icon }}</span>
                           <span class="material-symbols-outlined">add_circle</span>
                        </div>
                        <div>
                            <div class="mb-1">{{ tmp.name }}</div>
                            <div class="text-[9px] opacity-60 font-medium">{{ tmp.description }}</div>
                        </div>
                    </button>
                </div>
            </div>
        </section>
    </main>

    <!-- MOBILE NAV -->
    <nav class="md:hidden fixed bottom-0 left-0 w-full h-20 z-50 flex bg-white border-t-4 border-black">
        <button @click="scrollToSection('hero')" class="flex-1 flex flex-col items-center justify-center bg-black text-white border-none rounded-none">
            <span class="material-symbols-outlined mb-1">dashboard_customize</span>
            <span class="text-[9px] font-black uppercase">CORE</span>
        </button>
        <button @click="scrollToSection('sessions')" class="flex-1 flex flex-col items-center justify-center border-r border-black/10 bg-transparent text-black border-none rounded-none">
            <span class="material-symbols-outlined mb-1">analytics</span>
            <span class="text-[9px] font-black uppercase">DATA</span>
        </button>
        <button @click="scrollToSection('archive')" class="flex-1 flex flex-col items-center justify-center bg-transparent text-black border-none rounded-none">
            <span class="material-symbols-outlined mb-1">history</span>
            <span class="text-[9px] font-black uppercase">ARCHIVE</span>
        </button>
    </nav>

    <!-- FAB -->
    <div class="fixed bottom-10 right-10 z-50 hidden md:block">
        <button @click="scrollToSection('hero')" class="w-24 h-24 bg-bauhaus-red text-white flex flex-col items-center justify-center border-4 border-black hover:bg-black transition-all shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] active:translate-x-1 active:translate-y-1 active:shadow-none group p-0">
            <span class="material-symbols-outlined text-4xl mb-1">add</span>
            <span class="text-[9px] font-black uppercase tracking-widest">SIGNAL</span>
        </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { getTemplates } from "../api/graph";
import HistoryDatabase from "../components/HistoryDatabase.vue";

const router = useRouter();
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
