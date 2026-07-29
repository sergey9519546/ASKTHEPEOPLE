<template>
  <div class="fixed inset-0 z-[100] flex items-center justify-center bg-[#000000]/80 p-4 font-sans">
    <!-- Modal Window (Modern Minimalist Style) -->
    <div class="w-full max-w-4xl bg-white border border-slate-200 rounded-2xl shadow-xl flex flex-col max-h-[90vh] overflow-hidden animate-in fade-in zoom-in-95 duration-200">
      
      <!-- HEADER -->
      <header class="bg-white border-b border-slate-100 p-5 flex justify-between items-center">
        <div class="flex items-center gap-3">
          <span class="material-symbols-outlined text-2xl text-rose-500">settings_input_component</span>
          <h2 class="text-lg font-bold text-slate-800 tracking-tight uppercase">System Configuration</h2>
        </div>
        <button 
          @click="$emit('close')" 
          class="border-none bg-transparent hover:bg-slate-100 text-slate-400 hover:text-slate-600 w-8 h-8 rounded-full flex items-center justify-center p-0 cursor-pointer transition-colors"
        >
          <span class="material-symbols-outlined text-lg">close</span>
        </button>
      </header>

      <!-- BODY -->
      <div class="flex-grow p-6 md:p-8 overflow-y-auto space-y-6 scrollbar-thin">
        
        <!-- PRESETS PICKER -->
        <section class="border border-slate-200 rounded-xl p-5 bg-slate-50">
          <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">
            Endpoint Presets
          </h3>
          <p class="text-[11px] text-slate-500 mb-4">
            Select a preset provider to automatically populate endpoints and model configurations:
          </p>
          <div class="grid grid-cols-2 md:grid-cols-5 gap-3">
            <button 
              v-for="p in presets" 
              :key="p.id" 
              @click="applyPreset(p)"
              class="w-full py-2 px-3 border border-slate-200 rounded-lg text-xs font-semibold text-center hover:bg-slate-100 transition-all p-0 flex flex-col justify-center items-center gap-0.5"
              :class="p.id === activePresetId ? 'bg-rose-50 border-rose-400 text-rose-600 font-bold' : 'bg-white text-slate-700'"
            >
              <span>{{ p.name }}</span>
              <span class="text-[8px] font-normal opacity-60">{{ p.sub }}</span>
            </button>
          </div>
        </section>

        <!-- LLM SETTINGS -->
        <section class="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          <!-- PRIMARY MODEL CONFIG -->
          <div class="border border-slate-200 rounded-xl p-5 bg-white space-y-4">
            <h3 class="text-xs font-bold text-rose-500 uppercase tracking-wider mb-2">
              Primary Engine (Simulation & Context)
            </h3>
            
            <div class="space-y-1">
              <label class="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">LLM API Key</label>
              <div class="relative flex border border-slate-200 rounded-lg overflow-hidden focus-within:border-rose-500 focus-within:ring-1 focus-within:ring-rose-500 transition-all">
                <input 
                  :type="showKeys.primary ? 'text' : 'password'" 
                  v-model="form.LLM_API_KEY"
                  placeholder="nvapi-... or sk-..."
                  class="w-full px-3 py-2 font-mono text-xs outline-none bg-white border-none"
                />
                <button 
                  @click="showKeys.primary = !showKeys.primary"
                  type="button"
                  class="border-l border-slate-200 border-r-0 border-t-0 border-b-0 px-3 py-1 bg-slate-50 hover:bg-slate-100 text-[10px] font-bold text-slate-500 p-0 cursor-pointer"
                >
                  {{ showKeys.primary ? 'HIDE' : 'SHOW' }}
                </button>
              </div>
            </div>

            <div class="space-y-1">
              <label class="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">LLM Base URL</label>
              <input 
                type="text" 
                v-model="form.LLM_BASE_URL" 
                placeholder="https://integrate.api.nvidia.com/v1"
                class="w-full px-3 py-2 border border-slate-200 rounded-lg font-mono text-xs outline-none focus:border-rose-500 focus:ring-1 focus:ring-rose-500 transition-all bg-white"
              />
            </div>

            <div class="space-y-1">
              <label class="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">LLM Model Name</label>
              <input 
                type="text" 
                v-model="form.LLM_MODEL_NAME" 
                placeholder="meta/llama-4-maverick-17b-128e-instruct"
                class="w-full px-3 py-2 border border-slate-200 rounded-lg font-mono text-xs outline-none focus:border-rose-500 focus:ring-1 focus:ring-rose-500 transition-all bg-white"
              />
            </div>
          </div>

          <!-- BOOST MODEL CONFIG (OPTIONAL) -->
          <div class="border border-slate-200 rounded-xl p-5 bg-white space-y-4">
            <h3 class="text-xs font-bold text-blue-500 uppercase tracking-wider mb-2">
              Boost Engine (Reports & Analysis)
            </h3>

            <div class="space-y-1">
              <label class="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Boost API Key</label>
              <div class="relative flex border border-slate-200 rounded-lg overflow-hidden focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500 transition-all">
                <input 
                  :type="showKeys.boost ? 'text' : 'password'" 
                  v-model="form.LLM_BOOST_API_KEY"
                  placeholder="Same as Primary if left blank"
                  class="w-full px-3 py-2 font-mono text-xs outline-none bg-white border-none"
                />
                <button 
                  @click="showKeys.boost = !showKeys.boost"
                  type="button"
                  class="border-l border-slate-200 border-r-0 border-t-0 border-b-0 px-3 py-1 bg-slate-50 hover:bg-slate-100 text-[10px] font-bold text-slate-500 p-0 cursor-pointer"
                >
                  {{ showKeys.boost ? 'HIDE' : 'SHOW' }}
                </button>
              </div>
            </div>

            <div class="space-y-1">
              <label class="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Boost Base URL</label>
              <input 
                type="text" 
                v-model="form.LLM_BOOST_BASE_URL" 
                placeholder="https://integrate.api.nvidia.com/v1"
                class="w-full px-3 py-2 border border-slate-200 rounded-lg font-mono text-xs outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all bg-white"
              />
            </div>

            <div class="space-y-1">
              <label class="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Boost Model Name</label>
              <input 
                type="text" 
                v-model="form.LLM_BOOST_MODEL_NAME" 
                placeholder="mistralai/mistral-large-3-675b-instruct-2512"
                class="w-full px-3 py-2 border border-slate-200 rounded-lg font-mono text-xs outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all bg-white"
              />
            </div>
          </div>
        </section>

        <!-- GRAPH DATABASE & AUX SETTINGS -->
        <section class="border border-slate-200 rounded-xl p-5 bg-white space-y-4">
          <h3 class="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
            Zep Graph Memory & Search Configurations
          </h3>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="space-y-1">
              <label class="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Zep Graph API Key</label>
              <div class="relative flex border border-slate-200 rounded-lg overflow-hidden focus-within:border-rose-500 focus-within:ring-1 focus-within:ring-rose-500 transition-all">
                <input 
                  :type="showKeys.zep ? 'text' : 'password'" 
                  v-model="form.ZEP_API_KEY"
                  placeholder="z_..."
                  class="w-full px-3 py-2 font-mono text-xs outline-none bg-white border-none"
                />
                <button 
                  @click="showKeys.zep = !showKeys.zep"
                  type="button"
                  class="border-l border-slate-200 border-r-0 border-t-0 border-b-0 px-3 py-1 bg-slate-50 hover:bg-slate-100 text-[10px] font-bold text-slate-500 p-0 cursor-pointer"
                >
                  {{ showKeys.zep ? 'HIDE' : 'SHOW' }}
                </button>
              </div>
            </div>

            <div class="space-y-1">
              <label class="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Brave Search API Key (Optional)</label>
              <div class="relative flex border border-slate-200 rounded-lg overflow-hidden focus-within:border-rose-500 focus-within:ring-1 focus-within:ring-rose-500 transition-all">
                <input 
                  :type="showKeys.brave ? 'text' : 'password'" 
                  v-model="form.BRAVE_SEARCH_API_KEY"
                  placeholder="BSA_..."
                  class="w-full px-3 py-2 font-mono text-xs outline-none bg-white border-none"
                />
                <button 
                  @click="showKeys.brave = !showKeys.brave"
                  type="button"
                  class="border-l border-slate-200 border-r-0 border-t-0 border-b-0 px-3 py-1 bg-slate-50 hover:bg-slate-100 text-[10px] font-bold text-slate-500 p-0 cursor-pointer"
                >
                  {{ showKeys.brave ? 'HIDE' : 'SHOW' }}
                </button>
              </div>
            </div>
          </div>
        </section>

        <!-- CONNECTION DIAGNOSTICS -->
        <section class="border border-slate-200 rounded-xl p-5 bg-white space-y-4">
          <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h3 class="text-xs font-bold text-slate-700 uppercase tracking-wider">Connection Diagnostics</h3>
              <p class="text-[11px] text-slate-500 mt-1">Verify that your primary engine configurations can authenticate successfully.</p>
            </div>
            <button 
              @click="runConnectionTest" 
              :disabled="testing"
              class="w-full md:w-auto bg-slate-900 text-white hover:bg-rose-600 transition-colors px-5 py-2.5 rounded-lg text-xs font-bold uppercase tracking-wider"
            >
              <span v-if="testing">Diagnosing...</span>
              <span v-else>Test Connection</span>
            </button>
          </div>

          <!-- Connection Test Feedback -->
          <div v-if="testResult" class="border rounded-lg p-4 text-xs font-mono" :class="testResult.success ? 'bg-emerald-50 border-emerald-200 text-emerald-800' : 'bg-rose-50 border-rose-200 text-rose-800'">
            <div class="flex items-center gap-2 font-bold mb-1">
              <span class="material-symbols-outlined text-lg">{{ testResult.success ? 'check_circle' : 'error' }}</span>
              <span>{{ testResult.success ? 'CONNECTION SUCCESSFUL' : 'CONNECTION FAILED' }}</span>
            </div>
            <p class="whitespace-pre-wrap mt-1 leading-relaxed text-[11px]">
              {{ testResult.message }}
            </p>
          </div>
        </section>

        <!-- LOCAL MODEL INSTRUCTIONS -->
        <section class="border border-dashed border-slate-200 rounded-xl p-5 bg-slate-50 text-xs text-slate-500 space-y-2">
          <div class="flex items-center gap-2 font-bold uppercase text-slate-700">
            <span class="material-symbols-outlined text-sm">info</span>
            <span>Running Local LLM Models (Ollama / LM Studio)</span>
          </div>
          <ul class="list-disc pl-5 space-y-1.5 leading-relaxed text-[11px]">
            <li>
              <strong>Ollama</strong>: Set Base URL to <code class="bg-white border border-slate-200 px-1 rounded">http://localhost:11434/v1</code>, set Model Name to your pulled model (e.g. <code class="bg-white border border-slate-200 px-1 rounded">llama3</code>), and enter a dummy key (like <code class="bg-white border border-slate-200 px-1 rounded">ollama</code>).
            </li>
            <li>
              <strong>LM Studio</strong>: Set Base URL to <code class="bg-white border border-slate-200 px-1 rounded">http://localhost:1234/v1</code>, set Model Name to your active model, and set API Key to any dummy text.
            </li>
          </ul>
        </section>

      </div>

      <!-- FOOTER -->
      <footer class="bg-slate-50 px-6 py-4 flex flex-col sm:flex-row justify-end items-center gap-3 border-t border-slate-100">
        <button 
          @click="$emit('close')" 
          class="w-full sm:w-auto px-6 py-2.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition-colors border border-slate-200"
        >
          Cancel
        </button>
        <button 
          @click="save" 
          :disabled="saving"
          class="w-full sm:w-auto bg-rose-500 hover:bg-rose-600 text-white transition-colors px-6 py-2.5 rounded-lg text-xs font-bold tracking-wider flex items-center justify-center gap-2"
        >
          <span v-if="saving" class="spinner-small"></span>
          <span v-else>Save Configurations</span>
        </button>
      </footer>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getSettings, updateSettings, testConnection } from '../api/settings'

const emit = defineEmits(['close', 'saved'])

// Key visibility states
const showKeys = ref({
  primary: false,
  boost: false,
  zep: false,
  brave: false
})

const activePresetId = ref('')
const testing = ref(false)
const saving = ref(false)
const testResult = ref(null)

const form = ref({
  LLM_API_KEY: '',
  LLM_BASE_URL: '',
  LLM_MODEL_NAME: '',
  ZEP_API_KEY: '',
  BRAVE_SEARCH_API_KEY: '',
  LLM_BOOST_API_KEY: '',
  LLM_BOOST_BASE_URL: '',
  LLM_BOOST_MODEL_NAME: ''
})

const presets = [
  {
    id: 'nvidia',
    name: 'Nvidia NIM',
    sub: 'API Catalog',
    LLM_BASE_URL: 'https://integrate.api.nvidia.com/v1',
    LLM_MODEL_NAME: 'meta/llama-4-maverick-17b-128e-instruct',
    LLM_BOOST_BASE_URL: 'https://integrate.api.nvidia.com/v1',
    LLM_BOOST_MODEL_NAME: 'mistralai/mistral-large-3-675b-instruct-2512'
  },
  {
    id: 'together',
    name: 'Together AI',
    sub: 'Llama-3.1',
    LLM_BASE_URL: 'https://api.together.xyz/v1',
    LLM_MODEL_NAME: 'MiniMaxAI/MiniMax-M2.7',
    LLM_BOOST_BASE_URL: 'https://api.together.xyz/v1',
    LLM_BOOST_MODEL_NAME: 'meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo'
  },
  {
    id: 'openai',
    name: 'OpenAI Cloud',
    sub: 'Standard API',
    LLM_BASE_URL: 'https://api.openai.com/v1',
    LLM_MODEL_NAME: 'gpt-4o-mini',
    LLM_BOOST_BASE_URL: 'https://api.openai.com/v1',
    LLM_BOOST_MODEL_NAME: 'gpt-4o'
  },
  {
    id: 'ollama',
    name: 'Ollama Local',
    sub: 'Port 11434',
    LLM_BASE_URL: 'http://localhost:11434/v1',
    LLM_MODEL_NAME: 'llama3',
    LLM_BOOST_BASE_URL: 'http://localhost:11434/v1',
    LLM_BOOST_MODEL_NAME: 'llama3'
  },
  {
    id: 'lm_studio',
    name: 'LM Studio',
    sub: 'Port 1234',
    LLM_BASE_URL: 'http://localhost:1234/v1',
    LLM_MODEL_NAME: 'meta-llama-3-8b-instruct',
    LLM_BOOST_BASE_URL: 'http://localhost:1234/v1',
    LLM_BOOST_MODEL_NAME: 'meta-llama-3-8b-instruct'
  }
]

onMounted(async () => {
  try {
    const res = await getSettings()
    if (res.success && res.data) {
      // Map response to form fields (pre-populate)
      Object.keys(form.value).forEach(key => {
        form.value[key] = res.data[key] || ''
      })
      
      // Determine if a preset is active
      detectPreset()
    }
  } catch (err) {
    if (import.meta.env.DEV) console.error('Failed to load settings:', err)
  }
})

function detectPreset() {
  const match = presets.find(p => 
    form.value.LLM_BASE_URL.trim().replace(/\/$/, '') === p.LLM_BASE_URL.trim().replace(/\/$/, '') &&
    form.value.LLM_MODEL_NAME.trim() === p.LLM_MODEL_NAME.trim()
  )
  activePresetId.value = match ? match.id : ''
}

function applyPreset(preset) {
  activePresetId.value = preset.id
  form.value.LLM_BASE_URL = preset.LLM_BASE_URL
  form.value.LLM_MODEL_NAME = preset.LLM_MODEL_NAME
  form.value.LLM_BOOST_BASE_URL = preset.LLM_BOOST_BASE_URL
  form.value.LLM_BOOST_MODEL_NAME = preset.LLM_BOOST_MODEL_NAME
}

async function runConnectionTest() {
  testing.value = true
  testResult.value = null
  
  try {
    const res = await testConnection({
      LLM_API_KEY: form.value.LLM_API_KEY,
      LLM_BASE_URL: form.value.LLM_BASE_URL,
      LLM_MODEL_NAME: form.value.LLM_MODEL_NAME
    })
    
    if (res.success) {
      testResult.value = {
        success: true,
        message: `Success! The model responded correctly: "${res.response}"`
      }
    } else {
      testResult.value = {
        success: false,
        message: res.error || 'Connection failed without details'
      }
    }
  } catch (err) {
    testResult.value = {
      success: false,
      message: err.message || 'Network request failed. Ensure your backend is running.'
    }
  } finally {
    testing.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const res = await updateSettings(form.value)
    if (res.success) {
      emit('saved')
      emit('close')
    } else {
      alert(`Failed to save settings: ${res.error}`)
    }
  } catch (err) {
    alert(`Failed to save settings: ${err.message}`)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
/* Scoped overrides — convert light theme to dark glass (matches App.vue design system) */

.scrollbar-thin::-webkit-scrollbar {
  width: 6px;
}
.scrollbar-thin::-webkit-scrollbar-track {
  background: transparent;
  border-left: none;
}
.scrollbar-thin::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}
.scrollbar-thin::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.2);
}

/* Modal container → solid dark command center modal */
.w-full.max-w-4xl.bg-white.border.border-slate-200.rounded-2xl.shadow-xl {
  background: var(--bg-elevated, #121212) !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  border: 1px solid var(--line-strong, #333333) !important;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.8) !important;
  color: #f8fafc;
  border-radius: 0px !important;
}

/* Header */
.bg-white.border-b.border-slate-100 {
  background: rgba(15, 23, 42, 0.6) !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
}

.text-2xl.text-rose-500 {
  color: #f43f5e !important;
}

.text-lg.font-bold.text-slate-800.tracking-tight.uppercase {
  color: #f8fafc !important;
}

button.border-none.bg-transparent.hover\:bg-slate-100 {
  color: #94a3b8 !important;
}
button.border-none.bg-transparent.hover\:bg-slate-100:hover {
  background: rgba(30, 41, 59, 0.6) !important;
  color: #f8fafc !important;
}

/* Body scroll */
.flex-grow.p-6.md\:p-8.overflow-y-auto.space-y-6 {
  color: #f8fafc;
}

/* Preset picker card */
section.border.border-slate-200.rounded-xl.p-5.bg-slate-50 {
  background: rgba(30, 41, 59, 0.4) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
}

.text-xs.font-bold.text-slate-400.uppercase.tracking-wider {
  color: #94a3b8 !important;
}

.text-\[11px\].text-slate-500 {
  color: #94a3b8 !important;
}

/* Preset buttons */
button.w-full.py-2.px-3.border.border-slate-200.rounded-lg.bg-white {
  background: rgba(30, 41, 59, 0.5) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  color: #cbd5e1 !important;
  transition: all 0.2s ease !important;
}

button.w-full.py-2.px-3.border.border-slate-200.rounded-lg.bg-white:hover {
  background: rgba(99, 102, 241, 0.15) !important;
  border-color: rgba(99, 102, 241, 0.3) !important;
  color: #a5b4fc !important;
  transform: translateY(-1px);
}

/* Active preset */
button.bg-rose-50.border-rose-400.text-rose-600.font-bold,
button[class*="bg-rose-50"] {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(139, 92, 246, 0.2)) !important;
  border: 1px solid #6366f1 !important;
  color: #a5b4fc !important;
  box-shadow: 0 0 20px rgba(99, 102, 241, 0.25) !important;
}

/* Settings section cards (Primary/Boost Engine) */
section.grid.grid-cols-1.md\:grid-cols-2.gap-6 > div,
section.border.border-slate-200.rounded-xl.p-5.bg-white {
  background: rgba(15, 23, 42, 0.5) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
}

.text-xs.font-bold.text-rose-500.uppercase.tracking-wider {
  background: linear-gradient(135deg, #f43f5e, #8b5cf6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  color: transparent !important;
}

.text-xs.font-bold.text-blue-500.uppercase.tracking-wider {
  background: linear-gradient(135deg, #06b6d4, #6366f1);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  color: transparent !important;
}

.text-xs.font-bold.text-slate-700.uppercase.tracking-wider {
  color: #f8fafc !important;
}

/* Form labels */
.text-\[11px\].font-bold.text-slate-500.uppercase.tracking-wider {
  color: #94a3b8 !important;
}

/* Input containers */
.relative.flex.border.border-slate-200.rounded-lg {
  background: var(--bg-input) !important;
  border: 1px solid var(--line) !important;
  border-radius: 0 !important;
}

.relative.flex.border.border-slate-200.rounded-lg:focus-within {
  border-color: var(--accent) !important;
  box-shadow: none !important;
}

input.w-full.px-3.py-2.font-mono.text-xs.outline-none.bg-white.border-none {
  background: transparent !important;
  color: var(--text-void) !important;
  border: none !important;
}

input.w-full.px-3.py-2.font-mono.text-xs.outline-none.bg-white.border-none::placeholder {
  color: var(--text-dim) !important;
}

/* Show/hide buttons */
button.border-l.border-slate-200.border-r-0.border-t-0.border-b-0.px-3.py-1.bg-slate-50 {
  background: var(--bg-elevated) !important;
  border-left: 1px solid var(--line) !important;
  color: var(--text-secondary) !important;
  font-family: var(--font-mono) !important;
  border-radius: 0 !important;
}

button.border-l.border-slate-200.border-r-0.border-t-0.border-b-0.px-3.py-1.bg-slate-50:hover {
  background: var(--bg-hover) !important;
  color: var(--accent-bright) !important;
}

/* Standalone inputs */
input.w-full.px-3.py-2.border.border-slate-200.rounded-lg.font-mono.text-xs.outline-none.bg-white {
  background: var(--bg-input) !important;
  border: 1px solid var(--line) !important;
  color: var(--text-void) !important;
  border-radius: 0 !important;
}

input.w-full.px-3.py-2.border.border-slate-200.rounded-lg.font-mono.text-xs.outline-none.bg-white:focus {
  border-color: var(--accent) !important;
  box-shadow: none !important;
}

input.w-full.px-3.py-2.border.border-slate-200.rounded-lg.font-mono.text-xs.outline-none.bg-white::placeholder {
  color: var(--text-dim) !important;
}

/* Connection diagnostics section */
section.border.border-slate-200.rounded-xl.p-5.bg-white.space-y-4 {
  background: var(--bg-base) !important;
  border: 1px solid var(--line) !important;
  border-radius: 0 !important;
}

/* Test connection button */
button.w-full.md\:w-auto.bg-slate-900.text-white.hover\:bg-rose-600 {
  background: var(--accent) !important;
  color: var(--accent-ink) !important;
  border: 1px solid var(--accent) !important;
  font-family: var(--font-mono) !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.08em !important;
  border-radius: 0 !important;
  box-shadow: none !important;
}

button.w-full.md\:w-auto.bg-slate-900.text-white.hover\:bg-rose-600:hover {
  background: var(--accent-bright) !important;
  border-color: var(--accent-bright) !important;
  transform: none !important;
}

/* Connection feedback */
div.border.rounded-lg.p-4.text-xs.font-mono.bg-emerald-50,
div.border.rounded-lg.p-4.text-xs.font-mono.bg-rose-50 {
  color: var(--text-void) !important;
  border-radius: 0 !important;
}

.bg-emerald-50.border-emerald-200 {
  background: var(--bg-panel) !important;
  border: 1px solid var(--accent) !important;
  color: var(--accent-bright) !important;
}

.bg-rose-50.border-rose-200 {
  background: var(--bg-panel) !important;
  border: 1px solid var(--status-error) !important;
  color: var(--status-error) !important;
}

.bg-emerald-50 .material-symbols-outlined,
.bg-rose-50 .material-symbols-outlined {
  color: inherit !important;
}

/* Local model instructions */
section.border.border-dashed.border-slate-200.rounded-xl.p-5.bg-slate-50 {
  background: var(--bg-base) !important;
  border: 1px dashed var(--line-strong) !important;
  border-radius: 0 !important;
}

section.border-dashed.text-xs.text-slate-500 {
  color: var(--text-secondary) !important;
}

section.border-dashed strong {
  color: var(--text-void) !important;
}

section.border-dashed code {
  background: var(--bg-void) !important;
  border: 1px solid var(--line) !important;
  color: var(--accent) !important;
  padding: 1px 6px;
  border-radius: 0;
  font-size: 11px;
}

/* Footer */
footer.bg-slate-50.px-6.py-4.flex {
  background: var(--bg-base) !important;
  border-top: 1px solid var(--line) !important;
}

button.w-full.sm\:w-auto.px-6.py-2-5.text-xs.font-semibold.text-slate-600 {
  background: var(--bg-elevated) !important;
  border: 1px solid var(--line) !important;
  color: var(--text-secondary) !important;
  border-radius: 0 !important;
  font-family: var(--font-mono) !important;
}

button.w-full.sm\:w-auto.px-6.py-2-5.text-xs.font-semibold.text-slate-600:hover {
  background: var(--bg-hover) !important;
  color: var(--text-void) !important;
}

button.w-full.sm\:w-auto.bg-rose-500.hover\:bg-rose-600 {
  background: var(--accent) !important;
  color: var(--accent-ink) !important;
  border: 1px solid var(--accent) !important;
  font-family: var(--font-mono) !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.08em !important;
  border-radius: 0 !important;
  box-shadow: none !important;
}

button.w-full.sm\:w-auto.bg-rose-500.hover\:bg-rose-600:hover {
  background: var(--accent-bright) !important;
  border-color: var(--accent-bright) !important;
  transform: none !important;
}

.spinner-small {
  width: 14px;
  height: 14px;
  border: 2px solid var(--line-strong);
  border-radius: 0;
  border-top-color: var(--accent-ink);
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
