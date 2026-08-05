<template>
  <div class="chat-interface">
    <div class="messages-container" ref="messagesContainer">
      <div 
        v-for="(message, index) in messages" 
        :key="index" 
        class="message"
        :class="message.role"
      >
        <div class="message-avatar">
          {{ message.role === 'user' ? '👤' : '🤖' }}
        </div>
        <div class="message-content">
          <div class="message-text">{{ message.content }}</div>
          <div class="message-time">{{ formatTime(message.timestamp) }}</div>
        </div>
      </div>
      <div v-if="isStreaming" class="message assistant streaming">
        <div class="message-avatar">🤖</div>
        <div class="message-content">
          <div class="message-text typing-indicator">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>
    </div>
    
    <div class="input-area">
      <textarea 
        v-model="inputMessage" 
        @keydown.enter.exact.prevent="sendMessage"
        placeholder="Ask a question..."
        :disabled="isStreaming || isLoading"
        rows="3"
      ></textarea>
      <button 
        @click="sendMessage" 
        :disabled="!inputMessage.trim() || isStreaming || isLoading"
        class="send-button"
      >
        <span v-if="!isStreaming">Send</span>
        <span v-else>Sending...</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue';
import { useChatConversation } from '../composables/useChatConversation';

const props = defineProps({
  simulationId: { type: String, required: true },
  isLoading: { type: Boolean, default: false }
});

const { messages, isStreaming, sendMessage: sendChatMessage, clearChat } = useChatConversation(props.simulationId);

const inputMessage = ref('');
const messagesContainer = ref(null);

const sendMessage = async () => {
  if (!inputMessage.value.trim()) return;
  await sendChatMessage(inputMessage.value);
  inputMessage.value = '';
};

const formatTime = (timestamp) => {
  if (!timestamp) return '';
  return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

watch(messages, () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    }
  });
}, { deep: true });

defineExpose({ clearChat });
</script>

<style scoped>
.chat-interface {
  display: flex;
  flex-direction: column;
  height: 100%;
  border: 1px solid #e0e0e0;
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
  max-width: 80%;
}

.message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message.assistant {
  align-self: flex-start;
}

.message-avatar {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.message-content {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.message-text {
  background: #f5f5f5;
  padding: 0.75rem 1rem;
  border-radius: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
}

.message.user .message-text {
  background: #007bff;
  color: white;
}

.message-time {
  font-size: 0.75rem;
  color: #666;
  padding: 0 0.5rem;
}

.message.user .message-time {
  text-align: right;
}

.input-area {
  display: flex;
  gap: 0.5rem;
  padding: 1rem;
  border-top: 1px solid #e0e0e0;
  background: white;
}

textarea {
  flex: 1;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  resize: none;
  font-family: inherit;
}

textarea:focus {
  outline: 2px solid #007bff;
  border-color: transparent;
}

.send-button {
  padding: 0.75rem 1.5rem;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: background 0.2s;
}

.send-button:hover:not(:disabled) {
  background: #0056b3;
}

.send-button:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.typing-indicator span {
  display: inline-block;
  width: 6px;
  height: 6px;
  background: #666;
  border-radius: 50%;
  margin: 0 2px;
  animation: bounce 1.4s infinite ease-in-out both;
}

.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}
</style>
