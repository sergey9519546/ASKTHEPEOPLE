<template>
  <div class="chat-interface">
    <!-- Messages Area -->
    <div class="messages-container" ref="messagesContainer">
      <div 
        v-for="(message, index) in messages" 
        :key="index" 
        class="message"
        :class="{ 'user-message': message.role === 'user', 'system-message': message.role !== 'user' }"
      >
        <div class="message-avatar">
          <span v-if="message.role === 'user'">👤</span>
          <span v-else>🤖</span>
        </div>
        <div class="message-content">
          <p>{{ message.content }}</p>
          <small class="message-time">{{ formatTime(message.timestamp) }}</small>
        </div>
      </div>
      
      <!-- Loading Indicator -->
      <div v-if="isGenerating" class="message system-message">
        <div class="message-avatar">🤖</div>
        <div class="message-content">
          <div class="typing-indicator">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>
    </div>

    <!-- Input Area -->
    <div class="input-area">
      <textarea 
        v-model="inputMessage" 
        placeholder="Ask a question about your simulation..."
        @keydown.enter.exact.prevent="sendMessage"
        :disabled="isGenerating || !canSend"
        rows="2"
      ></textarea>
      <button 
        @click="sendMessage" 
        :disabled="!inputMessage.trim() || isGenerating || !canSend"
        class="send-button"
      >
        <span v-if="!isGenerating">Send</span>
        <span v-else>Generating...</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue';
import { useChatConversation } from '@/composables/useChatConversation';

const props = defineProps({
  simulationId: { type: String, required: true },
  canSend: { type: Boolean, default: true }
});

const emit = defineEmits(['message-sent']);

const { messages, isGenerating, sendMessage: sendChatMessage } = useChatConversation(props.simulationId);

const inputMessage = ref('');
const messagesContainer = ref(null);

const sendMessage = async () => {
  if (!inputMessage.value.trim() || isGenerating.value) return;
  
  const content = inputMessage.value.trim();
  inputMessage.value = '';
  
  await sendChatMessage(content);
  emit('message-sent', content);
};

const formatTime = (timestamp) => {
  if (!timestamp) return '';
  return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

// Auto-scroll to bottom on new message
watch(messages, () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    }
  });
}, { deep: true });
</script>

<style scoped>
.chat-interface {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--surface-secondary, #f8f9fa);
  border-radius: 8px;
  overflow: hidden;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.message {
  display: flex;
  gap: 0.75rem;
  max-width: 85%;
}

.user-message {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.system-message {
  align-self: flex-start;
}

.message-avatar {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.message-content {
  background: white;
  padding: 0.75rem 1rem;
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.user-message .message-content {
  background: var(--primary-color, #007bff);
  color: white;
}

.message-time {
  display: block;
  margin-top: 0.25rem;
  opacity: 0.7;
  font-size: 0.75rem;
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 0.5rem 0;
}

.typing-indicator span {
  width: 6px;
  height: 6px;
  background: #ccc;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.input-area {
  display: flex;
  gap: 0.5rem;
  padding: 1rem;
  background: white;
  border-top: 1px solid var(--border-subtle, #e9ecef);
}

textarea {
  flex: 1;
  resize: none;
  padding: 0.75rem;
  border: 1px solid var(--border-subtle, #e9ecef);
  border-radius: 8px;
  font-family: inherit;
  font-size: 0.95rem;
  outline: none;
  transition: border-color 0.2s;
}

textarea:focus {
  border-color: var(--primary-color, #007bff);
}

textarea:disabled {
  background: #f1f3f5;
  cursor: not-allowed;
}

.send-button {
  padding: 0 1.5rem;
  background: var(--primary-color, #007bff);
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}

.send-button:hover:not(:disabled) {
  opacity: 0.9;
}

.send-button:disabled {
  background: #ccc;
  cursor: not-allowed;
}
</style>
