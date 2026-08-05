<template>
  <div class="synthetic-profiles">
    <div v-if="isLoading" class="loading-state">
      <div class="spinner"></div>
      <p>Loading synthetic profiles...</p>
    </div>
    
    <div v-else-if="error" class="error-state">
      <div class="error-icon">⚠️</div>
      <h3>Failed to Load Profiles</h3>
      <p>{{ error }}</p>
      <button @click="loadProfiles" class="retry-button">Try Again</button>
    </div>
    
    <div v-else-if="profiles.length === 0" class="empty-state">
      <div class="empty-icon">👥</div>
      <h3>No Synthetic Profiles</h3>
      <p>No profiles have been generated for this simulation yet.</p>
    </div>
    
    <div v-else class="profiles-grid">
      <div 
        v-for="profile in profiles" 
        :key="profile.id" 
        class="profile-card"
        :class="{ 'selected': selectedProfileId === profile.id }"
        @click="selectProfile(profile.id)"
      >
        <div class="profile-header">
          <div class="profile-avatar">{{ getInitials(profile.name) }}</div>
          <div class="profile-info">
            <h4>{{ profile.name }}</h4>
            <p class="profile-demographics">{{ profile.demographics }}</p>
          </div>
        </div>
        
        <div class="profile-details">
          <div class="detail-item" v-if="profile.occupation">
            <span class="detail-label">Occupation:</span>
            <span class="detail-value">{{ profile.occupation }}</span>
          </div>
          <div class="detail-item" v-if="profile.location">
            <span class="detail-label">Location:</span>
            <span class="detail-value">{{ profile.location }}</span>
          </div>
          <div class="detail-item" v-if="profile.background">
            <span class="detail-label">Background:</span>
            <span class="detail-value">{{ truncate(profile.background, 100) }}</span>
          </div>
        </div>
        
        <div class="profile-actions">
          <button 
            @click.stop="viewFullProfile(profile)" 
            class="view-button"
          >
            View Full Profile
          </button>
        </div>
      </div>
    </div>
    
    <!-- Group Questions Section -->
    <div v-if="groupQuestions.length > 0" class="group-questions">
      <h3>Group Questions</h3>
      <div class="questions-list">
        <div 
          v-for="(question, index) in groupQuestions" 
          :key="index" 
          class="question-item"
        >
          <span class="question-number">{{ index + 1 }}</span>
          <p class="question-text">{{ question }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useSyntheticProfiles } from '@/composables/useSyntheticProfiles';

const props = defineProps({
  simulationId: { type: String, required: true }
});

const emit = defineEmits(['profile-selected']);

const { 
  profiles, 
  groupQuestions, 
  isLoading, 
  error, 
  selectedProfileId,
  loadProfiles, 
  selectProfile, 
  viewFullProfile 
} = useSyntheticProfiles(props.simulationId);

const getInitials = (name) => {
  if (!name) return '?';
  return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
};

const truncate = (text, maxLength) => {
  if (!text || text.length <= maxLength) return text;
  return text.slice(0, maxLength) + '...';
};
</script>

<style scoped>
.synthetic-profiles {
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

.profiles-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}

.profile-card {
  background: white;
  border: 1px solid var(--border-subtle, #e9ecef);
  border-radius: 8px;
  padding: 1rem;
  cursor: pointer;
  transition: all 0.2s;
}

.profile-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  transform: translateY(-2px);
}

.profile-card.selected {
  border-color: var(--primary-color, #007bff);
  background: #f0f7ff;
}

.profile-header {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.profile-avatar {
  width: 48px;
  height: 48px;
  background: var(--primary-color, #007bff);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  flex-shrink: 0;
}

.profile-info h4 {
  margin: 0 0 0.25rem 0;
  font-size: 1rem;
}

.profile-demographics {
  margin: 0;
  font-size: 0.85rem;
  color: #6c757d;
}

.profile-details {
  margin-bottom: 1rem;
}

.detail-item {
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
}

.detail-label {
  font-weight: 600;
  color: #495057;
}

.detail-value {
  color: #6c757d;
}

.profile-actions {
  border-top: 1px solid var(--border-subtle, #e9ecef);
  padding-top: 0.75rem;
}

.view-button {
  width: 100%;
  padding: 0.5rem;
  background: transparent;
  color: var(--primary-color, #007bff);
  border: 1px solid var(--primary-color, #007bff);
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s;
}

.view-button:hover {
  background: var(--primary-color, #007bff);
  color: white;
}

.group-questions {
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 2px solid var(--border-subtle, #e9ecef);
}

.questions-list {
  margin-top: 1rem;
}

.question-item {
  display: flex;
  gap: 0.75rem;
  padding: 0.75rem;
  background: #f8f9fa;
  border-radius: 6px;
  margin-bottom: 0.5rem;
}

.question-number {
  background: var(--primary-color, #007bff);
  color: white;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
  flex-shrink: 0;
}

.question-text {
  margin: 0;
  font-size: 0.95rem;
}
</style>
