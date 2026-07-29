<template>
  <div class="app-interface cmd-noise-overlay min-h-screen bg-[#000000] text-[#d4d4d4]">
    <!-- HEADER -->
    <header class="sticky top-0 z-50 flex flex-col md:flex-row justify-between items-center w-full px-6 py-3 gap-4 bg-[#0a0a0a] border-b border-[#222222]">
        <div class="flex items-center gap-4">
            <div class="text-sm font-mono font-bold tracking-widest uppercase px-3 py-1 border border-[#333333] bg-[#121212] text-[#a3e635]">ATP // CMD</div>
            <div class="hidden md:flex flex-col text-[10px] font-mono opacity-60 leading-tight uppercase tracking-wider text-[#9ca3af]">
                <span>Terminal: active</span>
                <span>Uptime: 99.98%</span>
            </div>
        </div>
        <nav class="flex gap-1 items-center bg-[#121212] p-1 border border-[#222222]">
            <button @click="scrollToSection('hero')" class="bg-[#a3e635] text-[#1a2e05] px-5 py-1.5 text-xs font-mono font-bold uppercase tracking-wider hover:bg-[#bef264] transition-colors border-none">DEPLOY</button>
            <button @click="scrollToSection('sessions')" class="px-5 py-1.5 text-xs font-mono font-medium uppercase tracking-wider text-[#9ca3af] hover:text-[#f3f4f6] hover:bg-[#1c1c1c] border-none bg-transparent">ANALYTICS</button>
            <button @click="scrollToSection('archive')" class="px-5 py-1.5 text-xs font-mono font-medium uppercase tracking-wider text-[#9ca3af] hover:text-[#f3f4f6] hover:bg-[#1c1c1c] border-none bg-transparent">ARCHIVE</button>
        </nav>
        <div class="flex items-center gap-4">
            <div class="hidden lg:flex flex-col items-end text-[10px] font-mono leading-none uppercase">
                <span class="text-[#a3e635]">// LINK_ESTABLISHED</span>
                <span class="text-[#4b5563]">node_id: 8172_alpha</span>
            </div>
            <div class="flex gap-2">
                <button @click="showSettings = true" class="w-8 h-8 border border-[#333333] bg-[#121212] hover:bg-[#1c1c1c] text-[#d4d4d4] flex items-center justify-center p-0" title="System Settings">
                  <span class="material-symbols-outlined text-sm">settings_input_component</span>
                </button>
            </div>
        </div>
    </header>

    <!-- SIDEBAR -->
    <aside class="hidden lg:flex fixed left-6 top-24 bottom-6 w-20 hover:w-64 bg-[#0a0a0a] border border-[#222222] flex-col z-40 pt-12 transition-all duration-300 group overflow-hidden shadow-none rounded-none">
        <div class="flex-grow space-y-1 px-3">
            <a class="flex items-center w-full px-4 py-4 rounded-none hover:bg-[#1a1a1a] hover:text-[#a3e635] transition-colors text-[#9ca3af] group/link" href="#">
                <span class="material-symbols-outlined text-xl min-w-[32px] group-hover/link:text-[#a3e635]">sensors</span>
                <span class="ml-4 text-[10px] font-mono font-semibold uppercase tracking-widest whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">Realtime_Stream</span>
            </a>
            <a class="flex items-center w-full px-4 py-4 rounded-none hover:bg-[#1a1a1a] hover:text-[#a3e635] transition-colors text-[#9ca3af] group/link" href="#">
                <span class="material-symbols-outlined text-xl min-w-[32px] group-hover/link:text-[#a3e635]">account_balance</span>
                <span class="ml-4 text-[10px] font-mono font-semibold uppercase tracking-widest whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">Macro_Econ</span>
            </a>
            <a class="flex items-center w-full px-4 py-4 rounded-none hover:bg-[#1a1a1a] hover:text-[#a3e635] transition-colors text-[#9ca3af] group/link" href="#">
                <span class="material-symbols-outlined text-xl min-w-[32px] group-hover/link:text-[#a3e635]">biotech</span>
                <span class="ml-4 text-[10px] font-mono font-semibold uppercase tracking-widest whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">Sovereign_Tech</span>
            </a>
            <a class="flex items-center w-full px-4 py-4 rounded-none hover:bg-[#1a1a1a] hover:text-[#a3e635] transition-colors text-[#9ca3af] group/link" href="#">
                <span class="material-symbols-outlined text-xl min-w-[32px] group-hover/link:text-[#a3e635]">data_exploration</span>
                <span class="ml-4 text-[10px] font-mono font-semibold uppercase tracking-widest whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">Vector_Maps</span>
            </a>
        </div>
        <div class="p-3 bg-transparent border-t border-[#222222]">
            <button @click="scrollToSection('hero')" class="w-full bg-[#a3e635] hover:bg-[#bef264] text-[#1a2e05] py-3 rounded-none text-[10px] font-mono font-bold uppercase tracking-[0.2em] flex justify-center border-none transition-colors">
                <span class="group-hover:hidden">++</span>
                <span class="hidden group-hover:inline">NEW_ENTRY</span>
            </button>
        </div>
    </aside>

    <!-- MAIN CONTENT -->
    <main class="lg:ml-28 pt-8 pb-24 px-6 md:px-16 min-h-screen">
        <!-- HERO / DEPLOY SECTION -->
        <section id="hero" class="py-16 flex flex-col items-start relative overflow-hidden border-b border-[#222222]">
            <div class="absolute right-0 top-1/2 -translate-y-1/2 opacity-5 pointer-events-none">
                <svg height="400" viewBox="0 0 100 100" width="400">
                    <circle cx="50" cy="50" fill="none" r="48" stroke="currentColor" stroke-dasharray="2 2" stroke-width="0.5" class="text-[#9ca3af]"></circle>
                    <rect fill="none" height="60" stroke="currentColor" stroke-width="0.5" width="60" x="20" y="20" class="text-[#9ca3af]"></rect>
                    <path d="M0 50 L100 50 M50 0 L50 100" stroke="currentColor" stroke-width="0.2" class="text-[#9ca3af]"></path>
                </svg>
            </div>
            <div class="bg-[#121212] border border-[#333333] text-[#9ca3af] px-3 py-1 rounded-none text-[10px] font-mono font-bold uppercase tracking-[0.3em] mb-6">
                COMMAND_INTERFACE // 00-CORE
            </div>
            <h1 class="text-[clamp(2.5rem,6vw,5rem)] font-extrabold leading-[1.05] tracking-tight mb-8 text-[#f3f4f6] uppercase font-serif">
                DECISION<br>MATRIX<span class="text-[#a3e635]">.</span>
            </h1>
            
            <div class="w-full max-w-6xl space-y-12">
                <p class="text-lg md:text-xl font-normal max-w-2xl leading-relaxed text-[#9ca3af] border-l-2 border-[#a3e635] pl-6 py-1 font-serif">
                    High-fidelity consensus mapping. Simplified for rapid systemic evolution.
                </p>

                <!-- INITIALIZATION INTERFACE -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-8 items-stretch">
                    <!-- INPUT AREA -->
                    <div class="space-y-6 flex flex-col justify-between">
                        <div class="space-y-2 flex-grow flex flex-col">
                            <span class="text-[10px] font-mono font-semibold uppercase tracking-widest text-[#6b7280]">Simulation Objective</span>
                            <textarea 
                                v-model="formData.simulationRequirement"
                                placeholder="What reality do you wish to manifest? Define your scenario, audience, or core question..."
                                class="w-full h-44 bg-[#0a0a0a] border border-[#333333] rounded-none p-5 font-mono text-sm text-[#d4d4d4] focus:border-[#a3e635] outline-none transition-all resize-none shadow-none flex-grow placeholder:text-[#4b5563]"
                            ></textarea>
                        </div>
                        
                        <div class="flex gap-4">
                            <button @click="startSimulation" :disabled="!canSubmit || loading"
                                        class="w-full bg-[#a3e635] text-[#1a2e05] p-5 rounded-none font-mono font-bold text-[13px] uppercase tracking-[0.1em] flex items-center justify-center gap-4 hover:bg-[#bef264] disabled:opacity-50 disabled:bg-[#121212] disabled:text-[#6b7280] disabled:border disabled:border-[#333333] transition-all group border-none shadow-none cursor-pointer">
                                    <span v-if="!loading">INITIALIZE ENGINE SEQUENCE</span>
                                    <span v-else class="app-spinner-small border-t-[#1a2e05]"></span>
                                    <span class="material-symbols-outlined group-hover:translate-x-1.5 transition-transform text-[#1a2e05]">arrow_forward</span>
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
                           <div v-for="(file, i) in files" :key="i" class="flex items-center justify-between bg-[#121212] border border-[#333333] p-3 group">
                                <div class="flex items-center gap-3 overflow-hidden">
                                    <span class="text-[#a3e635] font-mono font-bold text-[9px] bg-[#1a2e05] px-2 py-0.5">{{ file.name.split('.').pop().toUpperCase() }}</span>
                                    <span class="font-mono text-xs text-[#d4d4d4] truncate">{{ file.name }}</span>
                                </div>
                                <button @click.stop="removeFile(i)" class="w-6 h-6 hover:bg-[#222222] text-[#9ca3af] hover:text-[#f3f4f6] flex items-center justify-center border-none bg-transparent p-0 text-sm">×</button>
                           </div>
                           <button class="mt-4 text-[10px] font-mono font-semibold tracking-wider uppercase text-[#9ca3af] hover:text-[#a3e635] border-none bg-transparent" @click.stop="triggerFileInput">+ Add More Files</button>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- SESSIONS / ANALYTICS SECTION -->
        <section id="sessions" class="py-16">
            <div class="flex flex-col md:flex-row justify-between items-baseline mb-10 border-b border-[#222222] pb-4">
                <h2 class="text-2xl md:text-3xl font-serif font-bold uppercase tracking-tight text-[#f3f4f6]">Live Telemetry Sessions</h2>
                <div class="flex items-center gap-6 font-mono text-[10px] text-[#9ca3af]">
                    <span class="flex items-center gap-2 text-[#a3e635]">
                        <span class="w-2 h-2 rounded-full bg-[#a3e635] animate-pulse"></span> Streaming Telemetry
                    </span>
                    <span class="text-[#4b5563]">Nodes Active: 82.4K</span>
                </div>
            </div>
            
            <div class="grid grid-cols-1 md:grid-cols-12 gap-6 font-sans">
                <!-- Large Vote Card (Latest Session) -->
                <div v-if="simulationHistory.length > 0" class="md:col-span-8 bg-[#0a0a0a] border border-[#222222] p-0 flex flex-col group relative overflow-hidden cursor-pointer hover:border-[#333333] transition-colors" @click="router.push({ name: 'Process', params: { projectId: simulationHistory[0].project_id } })">
                    <div class="flex border-b border-[#222222] bg-[#121212]">
                        <div class="bg-[#a3e635] text-[#1a2e05] p-5 aspect-square flex items-center justify-center">
                            <span class="material-symbols-outlined text-2xl">sensors</span>
                        </div>
                        <div class="flex-grow p-5 flex items-center justify-between">
                            <span class="text-xs font-mono font-semibold tracking-wider text-[#9ca3af] uppercase">Status: {{ simulationHistory[0].status }}</span>
                            <span class="text-[9px] font-mono font-bold text-[#4b5563]">REF_ID: {{ simulationHistory[0].simulation_id.substring(0, 8) }}</span>
                        </div>
                    </div>
                    <div class="p-8 md:p-10">
                        <h3 class="text-2xl md:text-3xl font-serif font-extrabold leading-snug tracking-tight mb-8 text-[#f3f4f6] uppercase line-clamp-2">
                            {{ simulationHistory[0].prompt || 'Unnamed Simulation Goal' }}
                        </h3>
                        <div class="grid grid-cols-1 md:grid-cols-12 gap-8 items-center">
                            <div class="space-y-4 md:col-span-8">
                                <div class="flex justify-between items-end">
                                    <span class="text-xs font-mono font-semibold uppercase tracking-wider text-[#9ca3af]">Active Population Nodes</span>
                                    <span class="text-2xl font-mono font-bold text-[#f3f4f6]">{{ simulationHistory[0].entities_count || 0 }}</span>
                                </div>
                                <div class="h-4 bg-[#121212] border border-[#222222] relative overflow-hidden">
                                    <div class="absolute inset-y-0 left-0 bg-[#a3e635]" style="width: 100%;"></div>
                                </div>
                            </div>
                            <button class="md:col-span-4 bg-[#a3e635] text-[#1a2e05] py-4 text-xs font-mono font-bold uppercase tracking-wider hover:bg-[#bef264] transition-colors flex items-center justify-center gap-2 border-none">
                                Inspect Telemetry <span class="material-symbols-outlined text-sm">arrow_forward</span>
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Fallback Large Placeholder Vote Card -->
                <div v-else class="md:col-span-8 bg-[#0a0a0a] border border-[#222222] p-0 flex flex-col group relative overflow-hidden">
                    <div class="flex border-b border-[#222222] bg-[#121212]">
                        <div class="bg-[#a3e635] text-[#1a2e05] p-5 aspect-square flex items-center justify-center">
                            <span class="material-symbols-outlined text-2xl">sensors</span>
                        </div>
                        <div class="flex-grow p-5 flex items-center justify-between">
                            <span class="text-xs font-mono font-semibold tracking-wider text-[#9ca3af] uppercase">Module: Sovereign Telemetry</span>
                            <span class="text-[9px] font-mono font-bold text-[#4b5563]">REF_ID: 9912-X</span>
                        </div>
                    </div>
                    <div class="p-8 md:p-10">
                        <h3 class="text-2xl md:text-3xl font-serif font-extrabold leading-snug tracking-tight mb-8 text-[#f3f4f6] uppercase">
                            SYNTHETIC POPULATION CONSENSUS SIMULATION
                        </h3>
                        <div class="grid grid-cols-1 md:grid-cols-12 gap-8 items-center">
                            <div class="space-y-4 md:col-span-8">
                                <div class="flex justify-between items-end">
                                    <span class="text-xs font-mono font-semibold uppercase tracking-wider text-[#9ca3af]">Affirmative Convergence</span>
                                    <span class="text-2xl font-mono font-bold text-[#a3e635]">64.2%</span>
                                </div>
                                <div class="h-4 bg-[#121212] border border-[#222222] relative overflow-hidden">
                                    <div class="absolute inset-y-0 left-0 bg-[#a3e635]" style="width: 64.2%;"></div>
                                </div>
                            </div>
                            <button class="md:col-span-4 bg-[#a3e635] text-[#1a2e05] py-4 text-xs font-mono font-bold uppercase tracking-wider hover:bg-[#bef264] transition-colors flex items-center justify-center gap-2 border-none">
                                Launch Telemetry <span class="material-symbols-outlined text-sm">bolt</span>
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Small Vote Cards -->
                <div class="md:col-span-4 flex flex-col gap-4">
                    <template v-if="simulationHistory.length > 1">
                        <div v-for="sim in simulationHistory.slice(1, 3)" :key="sim.simulation_id" @click="router.push({ name: 'Process', params: { projectId: sim.project_id } })" class="flex-grow bg-[#0a0a0a] border border-[#222222] p-6 flex flex-col justify-between hover:border-[#333333] transition-colors cursor-pointer group">
                            <div>
                                <div class="flex justify-between mb-6">
                                    <span class="text-[10px] font-mono uppercase tracking-wider text-[#4b5563]">{{ new Date(sim.created_at).toLocaleDateString() }}</span>
                                    <span class="material-symbols-outlined text-[#4b5563]">data_object</span>
                                </div>
                                <h3 class="text-lg font-serif font-bold leading-snug text-[#f3f4f6] uppercase line-clamp-2">{{ sim.prompt || 'Unnamed Goal' }}</h3>
                            </div>
                            <div class="flex justify-between items-end mt-6">
                                <div class="text-[10px] font-mono font-bold text-[#a3e635] bg-[#1a2e05] px-2 py-0.5 border border-[#a3e635]/30">Status: {{ sim.status }}</div>
                                <span class="material-symbols-outlined text-[#9ca3af] group-hover:translate-x-1 transition-transform">arrow_forward</span>
                            </div>
                        </div>
                    </template>
                    <template v-else>
                        <!-- Fallback Small Vote Cards -->
                        <div class="flex-grow bg-[#0a0a0a] border border-[#222222] p-6 flex flex-col justify-between hover:border-[#333333] transition-colors cursor-pointer group">
                            <div>
                                <div class="flex justify-between mb-6">
                                    <span class="text-[10px] font-mono uppercase tracking-wider text-[#4b5563]">Urban Dynamics</span>
                                    <span class="material-symbols-outlined text-[#4b5563]">domain</span>
                                </div>
                                <h3 class="text-lg font-serif font-bold leading-snug text-[#f3f4f6] uppercase">AUTONOMOUS URBAN MOBILITY DRIFT</h3>
                            </div>
                            <div class="flex justify-between items-end mt-6">
                                <div class="text-[10px] font-mono font-bold text-[#a3e635] bg-[#1a2e05] px-2 py-0.5 border border-[#a3e635]/30">Stage: Evaluation</div>
                                <span class="material-symbols-outlined text-[#9ca3af] group-hover:translate-x-1 transition-transform">arrow_forward</span>
                            </div>
                        </div>
                        <div class="flex-grow bg-[#0a0a0a] border border-[#222222] p-6 flex flex-col justify-between hover:border-[#333333] transition-all cursor-pointer group">
                            <div>
                                <div class="flex justify-between mb-6">
                                    <span class="text-[10px] font-mono uppercase tracking-wider text-[#4b5563]">Data Governance</span>
                                    <span class="material-symbols-outlined text-[#4b5563]">encrypted</span>
                                </div>
                                <h3 class="text-lg font-serif font-bold leading-snug text-[#f3f4f6] uppercase">BIO-ENCRYPTION CONSENSUS PROTOCOL</h3>
                            </div>
                            <div class="flex justify-between items-end mt-6">
                                <div class="text-[10px] font-mono font-bold text-[#f59e0b] bg-[#451a03] px-2 py-0.5 border border-[#f59e0b]/30">Status: Critical</div>
                                <span class="material-symbols-outlined text-[#9ca3af] group-hover:translate-x-1 transition-transform">arrow_forward</span>
                            </div>
                        </div>
                    </template>
                </div>
            </div>
        </section>

        <!-- ARCHIVE SECTION -->
        <section id="archive" class="py-16 border-t border-[#222222]">
            <div class="flex flex-col md:flex-row justify-between items-baseline mb-10 border-b border-[#222222] pb-4">
                <h2 class="text-2xl md:text-3xl font-serif font-bold uppercase tracking-tight text-[#f3f4f6]">Archive Database</h2>
                <div class="text-[10px] font-mono font-bold text-[#4b5563] uppercase">Accessing Historical Knowledge Nodes...</div>
            </div>
            
            <div class="bg-[#0a0a0a] border border-[#222222] p-6">
                <HistoryDatabase borderless />
            </div>
        </section>

        <!-- METRICS & SYSTEM INFO -->
        <section class="py-16 border-t border-[#222222]">
            <div class="flex flex-col md:flex-row gap-8">
                <div class="w-full md:w-1/3">
                    <div class="bg-[#0a0a0a] border border-[#222222] text-[#f3f4f6] p-8 flex flex-col justify-between h-full min-h-[250px]">
                        <div>
                            <h4 class="text-[10px] font-mono font-bold tracking-[0.2em] mb-4 text-[#a3e635] uppercase">System Telemetry</h4>
                            <p class="text-2xl font-serif font-bold leading-snug uppercase mb-6 text-[#f3f4f6]">The geometry of modern consensus.</p>
                        </div>
                        <div class="space-y-4">
                            <div class="text-[9px] font-mono text-[#9ca3af] uppercase">Current Processing Cycle: 8.2s</div>
                            <div class="w-full h-1.5 bg-[#121212] border border-[#222222]">
                                <div class="w-2/3 h-full bg-[#a3e635]"></div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="w-full md:w-2/3 grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div class="border border-[#222222] p-6 bg-[#0a0a0a] flex flex-col justify-center">
                        <div class="text-[10px] font-mono font-bold uppercase tracking-widest text-[#9ca3af] mb-4">Global Consensus Drift</div>
                        <div class="h-28 flex items-end gap-3 mb-3">
                            <div class="bg-[#a3e635] w-full" style="height: 40%"></div>
                            <div class="bg-[#333333] w-full" style="height: 70%"></div>
                            <div class="bg-[#3b82f6] w-full" style="height: 55%"></div>
                            <div class="bg-[#10b981] w-full" style="height: 90%"></div>
                            <div class="bg-[#4b5563] w-full" style="height: 30%"></div>
                            <div class="bg-[#a3e635] w-full" style="height: 65%"></div>
                        </div>
                        <div class="flex justify-between text-[8px] font-mono font-bold text-[#4b5563]">
                            <span>P_01</span><span>P_02</span><span>P_03</span><span>P_04</span><span>P_05</span><span>P_06</span>
                        </div>
                    </div>
                    <div class="border border-[#222222] p-6 bg-[#0a0a0a] flex flex-col justify-between">
                        <div>
                            <div class="text-[10px] font-mono font-bold uppercase tracking-widest text-[#9ca3af] mb-2">System Health Index</div>
                            <div class="text-4xl font-mono font-extrabold text-[#a3e635]">0.998</div>
                        </div>
                        <div class="flex gap-2 mt-4">
                            <span class="w-2.5 h-2.5 bg-[#a3e635]"></span>
                            <span class="w-2.5 h-2.5 bg-[#3b82f6]"></span>
                            <span class="w-2.5 h-2.5 bg-[#10b981]"></span>
                            <span class="w-2.5 h-2.5 bg-[#333333]"></span>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- TEMPLATE GALLERY -->
        <section class="py-16 border-t border-[#222222] bg-[#0a0a0a] border border-[#222222] text-[#f3f4f6] p-8 md:p-16 relative overflow-hidden">
            <div class="relative z-10 flex flex-col items-center text-center">
                <span class="font-mono text-[10px] font-semibold tracking-[0.4em] mb-6 border border-[#333333] bg-[#121212] px-3 py-1.5 uppercase text-[#a3e635]">Core Seed Templates</span>
                <h2 class="text-3xl md:text-5xl font-serif font-extrabold leading-tight mb-10 tracking-tight uppercase text-[#f3f4f6]">READY TO INITIALIZE?</h2>
                
                <div v-if="templates.length" class="grid grid-cols-1 md:grid-cols-3 gap-4 w-full max-w-5xl">
                    <button 
                        v-for="tmp in templates" 
                        :key="tmp.id"
                        @click="selectTemplate(tmp)"
                        class="bg-[#121212] hover:bg-[#1c1c1c] text-[#f3f4f6] p-6 border border-[#222222] hover:border-[#a3e635] transition-all text-left flex flex-col justify-between min-h-[160px]"
                    >
                        <div class="flex justify-between w-full mb-4">
                           <span class="text-xl text-[#a3e635]">{{ tmp.icon }}</span>
                           <span class="material-symbols-outlined text-sm text-[#9ca3af]">add_circle</span>
                        </div>
                        <div>
                            <div class="font-mono font-bold text-sm mb-1 text-[#f3f4f6]">{{ tmp.name }}</div>
                            <div class="text-[10px] font-mono text-[#9ca3af] leading-normal">{{ tmp.description }}</div>
                        </div>
                    </button>
                </div>
            </div>
        </section>
    </main>

    <!-- MOBILE NAV -->
    <nav class="md:hidden fixed bottom-0 left-0 w-full h-16 z-50 flex bg-[#0a0a0a] border-t border-[#222222]">
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
import { getSimulationHistory } from "../api/simulation";
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
const simulationHistory = ref([]);

const fetchHistory = async () => {
  try {
    const res = await getSimulationHistory(3); // Fetch the latest 3 for the dashboard
    if (res.success && res.data) {
      simulationHistory.value = res.data;
    }
  } catch (err) {
    if (import.meta.env.DEV) console.warn("Failed to fetch simulation history:", err);
  }
};

const fetchTemplates = async () => {
  try {
    const res = await getTemplates();
    if (res.success) {
      templates.value = res.data;
    }
  } catch (err) {
    if (import.meta.env.DEV) console.warn("Failed to fetch templates:", err);
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
fetchHistory();
</script>
