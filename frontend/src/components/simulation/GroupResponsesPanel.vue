<template>
  <div class="group-responses-panel">
    <div v-if="isLoading" class="loading-state">
      <div class="spinner"></div>
      <p>Loading group responses...</p>
    </div>
    
    <div v-else-if="error" class="error-state">
      <div class="error-icon">⚠️</div>
      <h3>Failed to Load Responses</h3>
      <p>{{ error }}</p>
      <button @click="loadResponses" class="retry-button">Try Again</button>
    </div>
    
    <div v-else-if="responses.length === 0" class="empty-state">
      <div class="empty-icon">💬</div>
      <h3>No Group Responses Yet</h3>
      <p>Ask a question to generate multiple synthetic responses.</p>
    </div>
    
    <div v-else class="responses-list">
      <div class="question-summary" v-if="currentQuestion">
        <h3>Current Question</h3>
        <p class="question-text">{{ currentQuestion }}</p>
      </div>
      
      <div 
        v-for="(response, index) in responses" 
        :key="index" 
        class="response-card"
      >
        <div class="response-header">
          <div class="profile-badge">
            <span class="profile-avatar">{{ getInitials(response.profile_name) }}</span>
            <div class="profile-meta">
              <strong>{{ response.profile_name }}</strong>
              <span class="profile-demographics">{{ response.demographics }}</span>
            </div>
          </div>
          <span class="response-number">#{{ index + 1 }}</span>
        </div>
        
        <div class="response-content">
          <p>{{ response.content }}</p>
        </div>
        
        <div class="response-footer" v-if="response.confidence || response.reasoning">
          <div v-if="response.confidence" class="confidence-indicator">
            <span class="label">Confidence:</span>
            <span class="value" :class="getConfidenceClass(response.confidence)">
              {{ response.confidence }}%
            </span>
          </div>
        </div>
      </div>
      
      <!-- Ask New Question Form -->
      <div class="ask-question-section">
        <h3>Ask the Group a Question</h3>
        <form @submit.prevent="submitQuestion" class="question-form">
          <textarea 
            v-model="newQuestion" 
            placeholder="What would you like to ask the synthetic group?"
            rows="3"
            required
          ></textarea>
          <div class="form-actions">
            <button 
              type="submit" 
              :disabled="!newQuestion.trim() || isSubmitting"
              class="submit-button"
            >
              {{ isSubmitting ? 'Generating...' : 'Ask Group' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useSyntheticProfiles } from '@/composables/useSyntheticProfiles';

const props = defineProps({
  simulationId: { type: String, required: true }
});

const { profiles, groupQuestions, isLoading, error, loadProfiles } = useSyntheticProfiles(props.simulationId);

const newQuestion = ref('');
const isSubmitting = ref(false);
const responses = ref([]);
const currentQuestion = ref('');

// Use first profile's group questions as current question
const questionText = computed(() => {
  return groupQuestions.value.length > 0 ? groupQuestions.value[0] : null;
});

const getInitials = (name) => {
  if (!name) return '?';
  return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
};

const getConfidenceClass = (confidence) => {
  if (confidence >= 80) return 'high';
  if (confidence >= 60) return 'medium';
  return 'low';
};

const submitQuestion = async () => {
  if (!newQuestion.value.trim() || isSubmitting.value) return;
  
  isSubmitting.value = true;
  currentQuestion.value = newQuestion.value;
  
  try {
    // TODO: Implement actual API call to generate group responses
    // For now, simulate with mock data
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    responses.value = profiles.value.slice(0, 5).map(profile => ({
      profile_name: profile.name,
      demographics: profile.demographics,
      content: `[Simulated response from ${profile.name} to: ${newQuestion.value}]`,
      confidence: Math.floor(Math.random() * 40) + 60
    }));
    
    newQuestion.value = '';
  } catch (err) {
    console.error('Failed to generate group responses:', err);
  } finally {
    isSubmitting.value = false;
  }
};

const loadResponses = async () => {
  await loadProfiles();
};
</script>

<style scoped>
.group-responses-panel {
  padding: 1rem;
}

.loading-state, .error-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 1rem;
  text-align: center;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid var(--border-subtle, #e9ecef);
  border-top-color: var(--primary-color, #007bff);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-icon, .empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.retry-button {
  margin-top: 1rem;
  padding: 0.5rem 1.5rem;
  background: var(--primary-color, #007bff);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.responses-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.question-summary {
  background: #f0f7ff;
  padding: 1rem;
  border-left: 4px solid var(--primary-color, #007bff);
  border-radius: 4px;
}

.question-summary h3 {
  margin: 0 0 0.5rem 0;
  font-size: 0.95rem;
  color: #495057;
}

.question-text {
  margin: 0;
  font-weight: 500;
  font-size: 1.05rem;
}

.response-card {
  background: white;
  border: 1px solid var(--border-subtle, #e9ecef);
  border-radius: 8px;
  overflow: hidden;
}

.response-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: #f8f9fa;
  border-bottom: 1px solid var(--border-subtle, #e9ecef);
}

.profile-badge {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.profile-avatar {
  width: 36px;
  height: 36px;
  background: var(--primary-color, #007bff);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.9rem;
}

.profile-meta strong {
  display: block;
  font-size: 0.95rem;
}

.profile-demographics {
  font-size: 0.85rem;
  color: #6c757d;
}

.response-number {
  background: #dee2e6;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 600;
}

.response-content {
  padding: 1rem;
}

.response-content p {
  margin: 0;
  line-height: 1.6;
}

.response-footer {
  padding: 0.75rem 1rem;
  background: #f8f9fa;
  border-top: 1px solid var(--border-subtle, #e9ecef);
}

.confidence-indicator {
  display: flex;
  gap: 0.5rem;
  font-size: 0.9rem;
}

.confidence-indicator .label {
  color: #6c757d;
}

.confidence-indicator .value {
  font-weight: 600;
}

.value.high { color: #28a745; }
.value.medium { color: #ffc107; }
.value.low { color: #dc3545; }

.ask-question-section {
  margin-top: 1rem;
  padding-top: 1.5rem;
  border-top: 2px solid var(--border-subtle, #e9ecef);
}

.ask-question-section h3 {
  margin: 0 0 1rem 0;
  font-size: 1.1rem;
}

.question-form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid var(--border-subtle, #e9ecef);
  border-radius: 6px;
  font-family: inherit;
  font-size: 0.95rem;
  resize: vertical;
  outline: none;
  transition: border-color 0.2s;
}

textarea:focus {
  border-color: var(--primary-color, #007bff);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
}

.submit-button {
  padding: 0.75rem 2rem;
  background: var(--primary-color, #007bff);
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}

.submit-button:hover:not(:disabled) {
  opacity: 0.9;
}

.submit-button:disabled {
  background: #ccc;
  cursor: not-allowed;
}
</style>
