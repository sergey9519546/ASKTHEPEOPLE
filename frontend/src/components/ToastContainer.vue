<template>
  <div class="toast-container font-sans">
    <transition-group name="toast">
      <div 
        v-for="item in toasts" 
        :key="item.id" 
        class="toast-item"
        :class="item.type"
      >
        <div class="toast-icon">
          <span v-if="item.type === 'success'">✓</span>
          <span v-else-if="item.type === 'error'">✕</span>
          <span v-else-if="item.type === 'warning'">⚠️</span>
          <span v-else>ℹ</span>
        </div>
        <div class="toast-body">
          <div v-if="item.title" class="toast-title">{{ item.title }}</div>
          <div class="toast-message">{{ item.message }}</div>
        </div>
        <button class="toast-close" @click="removeToast(item.id)">×</button>
      </div>
    </transition-group>
  </div>
</template>

<script setup>
import { toasts, removeToast } from '../utils/toast.js';
</script>

<style scoped>
.toast-container {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: 400px;
  pointer-events: none;
}

.toast-item {
  pointer-events: auto;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.toast-item.success {
  border-left: 4px solid #10b981;
}

.toast-item.error {
  border-left: 4px solid #f43f5e;
}

.toast-item.warning {
  border-left: 4px solid #f59e0b;
}

.toast-item.info {
  border-left: 4px solid #3b82f6;
}

.toast-icon {
  font-size: 14px;
  font-weight: 700;
}

.toast-item.success .toast-icon { color: #10b981; }
.toast-item.error .toast-icon { color: #f43f5e; }
.toast-item.warning .toast-icon { color: #f59e0b; }
.toast-item.info .toast-icon { color: #3b82f6; }

.toast-body {
  flex: 1;
}

.toast-title {
  font-size: 12px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 2px;
}

.toast-message {
  font-size: 11px;
  color: #475569;
  line-height: 1.4;
}

.toast-close {
  background: transparent;
  border: none;
  font-size: 16px;
  color: #94a3b8;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.toast-close:hover {
  color: #475569;
}

/* Animations */
.toast-enter-from {
  opacity: 0;
  transform: translateY(20px) scale(0.95);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
}
</style>
