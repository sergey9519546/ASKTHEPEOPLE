/**
 * Step1GraphBuild — Refactored with Progressive Intelligence
 * 
 * BEFORE: Shows all entity types, relationship types, attributes, and technical
 * terminology immediately. Users see "ontology generation", entity type schemas,
 * and relationship cardinality before understanding what these mean for their task.
 * 
 * AFTER: Guides through context. First-time users see "Key people and places found"
 * with the top 6 entities. Advanced users get direct access to full schema. Help
 * appears when relevant, not as always-visible explanatory paragraphs.
 */

<script setup>
import { computed, ref } from 'vue';
import { useAdaptiveUI } from '../composables/useAdaptiveUI';
import ProgressiveGuidance from './ProgressiveGuidance.vue';
import ContextualHelp from './ContextualHelp.vue';

const props = defineProps({
  currentPhase: { type: Number, default: -1 },
  projectData: { type: Object, default: null },
  ontologyProgress: { type: Object, default: null },
  buildProgress: { type: Object, default: null },
  graphData: { type: Object, default: null },
  systemLogs: { type: Array, default: () => [] }
});

const emit = defineEmits(['next-step']);

const { 
  adaptiveClasses,
  actionLabel,
  statusMessage,
  adaptiveCopy,
  guidance
} = useAdaptiveUI();

// Local state
const selectedEntity = ref(null);
const showAllEntities = ref(false);

// Adaptive title based on capability
const stepTitle = computed(() => adaptiveCopy('step1_title', {
  first_use: 'Review what we found in your sources',
  learning: 'Review extracted entities and relationships',
  practiced: 'Source map entities',
  expert: 'Entities'
}));

// Entity organization
const entities = computed(() => 
  props.projectData?.ontology?.entity_types || []
);

const topEntities = computed(() => 
  entities.value.slice(0, 6)
);

const remainingEntities = computed(() => 
  entities.value.slice(6)
);

const hasGraphContent = computed(() => 
  Number(props.graphData?.node_count || 0) > 0 ||
  (Array.isArray(props.graphData?.nodes) && props.graphData.nodes.length > 0)
);

// Status
const stepStatus = computed(() => {
  if (props.currentPhase < 0) return 'waiting';
  if (props.currentPhase === 0) return 'processing';
  if (props.currentPhase >= 2 && hasGraphContent.value) return 'ready';
  if (props.currentPhase >= 2) return 'error';
  return 'processing';
});

const handleEntityClick = (entity) => {
  guidance.trackInteraction('entity_detail');
  selectedEntity.value = entity;
};

const handleContinue = () => {
  guidance.completeCheckpoint('source_mapping');
  emit('next-step');
};
</script>

<template>
  <div class="workbench-panel">
    <h2 class="sr-only">Source map construction</h2>
    <div class="scroll-container scrollbar-thin">
      
      <!-- STEP HEADER: Adaptive title and contextual status -->
      <div class="step-card" :class="{ active: currentPhase >= 0 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">01</span>
            <span class="step-title">{{ stepTitle }}</span>
          </div>
          <div class="step-status">
            <span :class="['badge', stepStatus]">
              {{ statusMessage(stepStatus, { 
                stage: currentPhase === 0 ? 'Reading sources' : 'Complete',
                itemCount: entities.length 
              }) }}
            </span>
          </div>
        </div>

        <div class="card-content">
          
          <!-- CONTEXTUAL HELP: Only appears when relevant -->
          <ContextualHelp
            help-id="source-reading-intro"
            concept="entity_extraction"
            :content="{
              first_use: 'The system identifies key people, places, and concepts from your sources. These will be used to build realistic generated profiles for the scenario.',
              learning: 'Extracted entities help structure the scenario around what matters in your sources.',
              practiced: 'Source entities feed profile generation',
              expert: null
            }"
            :auto-show-phases="['mapping']"
            variant="inline"
          />

          <!-- PROCESSING STATE -->
          <div
            v-if="currentPhase === 0 && ontologyProgress"
            :class="adaptiveClasses('processing_indicator', 'primary')"
            class="progress-section"
          >
            <div class="spinner-sm"></div>
            <span>{{ ontologyProgress.message || 'Reading source material…' }}</span>
          </div>

          <!-- PRIMARY: Key entities overview (always visible when ready) -->
          <ProgressiveGuidance
            id="key_entities"
            level="primary"
            :phases="['mapping']"
            :expandable="false"
          >
            <div class="entities-summary">
              <div class="summary-header">
                <span class="summary-label">
                  {{ adaptiveCopy('entities_label', {
                    first_use: 'Key people, places, and concepts',
                    learning: 'Extracted entities',
                    practiced: 'Entities',
                    expert: 'Entities'
                  }) }}
                </span>
                <span class="summary-count">{{ entities.length }} found</span>
              </div>
              
              <div v-if="topEntities.length" class="entity-chips">
                <button
                  v-for="entity in topEntities"
                  :key="entity.name"
                  class="entity-chip"
                  type="button"
                  @click="handleEntityClick(entity)"
                >
                  {{ entity.name }}
                </button>
              </div>
              
              <p v-else class="empty-state">
                {{ adaptiveCopy('no_entities', {
                  first_use: 'No entities were extracted from your sources. You can continue without source material.',
                  default: 'No entities extracted'
                }) }}
              </p>
            </div>
          </ProgressiveGuidance>

          <!-- SECONDARY: Show remaining entities -->
          <ProgressiveGuidance
            v-if="remainingEntities.length > 0"
            id="remaining_entities"
            level="secondary"
            :phases="['mapping']"
          >
            <template #preview>
              <span>{{ remainingEntities.length }} more entities</span>
            </template>
            
            <template #default>
              <div class="entity-chips">
                <button
                  v-for="entity in remainingEntities"
                  :key="entity.name"
                  class="entity-chip"
                  type="button"
                  @click="handleEntityClick(entity)"
                >
                  {{ entity.name }}
                </button>
              </div>
            </template>
          </ProgressiveGuidance>

          <!-- AVAILABLE: Relationship types (for thorough users) -->
          <ProgressiveGuidance
            v-if="projectData?.ontology?.relationship_types?.length"
            id="relationship_types"
            level="available"
            :capabilities="['learning', 'practiced', 'expert']"
            :phases="['mapping']"
          >
            <template #preview>
              <span>{{ projectData.ontology.relationship_types.length }} relationship types identified</span>
            </template>
            
            <template #trigger-label>relationship types</template>
            
            <template #default>
              <div class="relationship-list">
                <div
                  v-for="rel in projectData.ontology.relationship_types"
                  :key="rel.name"
                  class="relationship-item"
                >
                  <strong>{{ rel.name }}</strong>
                  <p>{{ rel.description }}</p>
                </div>
              </div>
            </template>
          </ProgressiveGuidance>

          <!-- ADVANCED: Attribute schema details (expert only) -->
          <ProgressiveGuidance
            v-if="selectedEntity"
            id="entity_attributes"
            level="advanced"
            :capabilities="['practiced', 'expert']"
            :phases="['mapping']"
          >
            <template #trigger-label>entity schema details</template>
            
            <template #default>
              <div class="entity-detail-panel">
                <h3>{{ selectedEntity.name }}</h3>
                <p>{{ selectedEntity.description }}</p>
                
                <div v-if="selectedEntity.attributes?.length" class="attributes-section">
                  <h4>Attributes</h4>
                  <div
                    v-for="attr in selectedEntity.attributes"
                    :key="attr.name"
                    class="attribute-item"
                  >
                    <div class="attr-header">
                      <span class="attr-name">{{ attr.name }}</span>
                      <span class="attr-type">({{ attr.type }})</span>
                    </div>
                    <p class="attr-desc">{{ attr.description }}</p>
                  </div>
                </div>
                
                <div v-if="selectedEntity.examples?.length" class="examples-section">
                  <h4>Examples</h4>
                  <div class="example-tags">
                    <span
                      v-for="ex in selectedEntity.examples"
                      :key="ex"
                      class="example-tag"
                    >
                      {{ ex }}
                    </span>
                  </div>
                </div>
              </div>
            </template>
          </ProgressiveGuidance>

          <!-- PRIMARY ACTION -->
          <div class="action-section">
            <button
              type="button"
              class="action-btn primary"
              :disabled="stepStatus !== 'ready'"
              @click="handleContinue"
            >
              {{ actionLabel('continue', {
                explicit: 'Continue to set assumptions',
                default: 'Continue',
                terse: 'Next'
              }) }}
            </button>
          </div>

        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Reuse existing card styles, add adaptive enhancements */

.entities-summary {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem 0;
}

.summary-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.summary-label {
  font-family: var(--font-display);
  font-size: 0.875rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--paper-muted);
}

.summary-count {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--paper-dim);
}

.entity-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.entity-chip {
  padding: 0.5rem 0.875rem;
  border: 1px solid var(--line-dark);
  background: var(--ink-deep);
  color: var(--paper);
  font-family: var(--font-body);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.entity-chip:hover {
  border-color: var(--signal);
  background: var(--signal);
  color: var(--ink);
}

.relationship-list,
.entity-detail-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem;
  border: 1px solid var(--line-dark);
  background: var(--ink-deep);
}

.relationship-item strong {
  display: block;
  margin-bottom: 0.25rem;
  color: var(--paper);
  font-size: 0.875rem;
}

.relationship-item p {
  margin: 0;
  color: var(--paper-muted);
  font-size: 0.8125rem;
  line-height: 1.5;
}

.action-section {
  display: flex;
  gap: 0.75rem;
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--line-dark);
}

.action-btn {
  padding: 0.875rem 1.5rem;
  border: 2px solid var(--signal);
  background: var(--signal);
  color: var(--ink);
  font-family: var(--font-display);
  font-size: 0.875rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  cursor: pointer;
  transition: all 0.15s ease;
}

.action-btn:hover:not(:disabled) {
  background: var(--signal-strong);
  border-color: var(--signal-strong);
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.empty-state {
  padding: 2rem 1rem;
  color: var(--paper-muted);
  font-size: 0.875rem;
  text-align: center;
}
</style>
