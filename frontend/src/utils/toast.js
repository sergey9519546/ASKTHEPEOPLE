import { ref } from 'vue';

export const toasts = ref([]);
let toastIdCounter = 0;

export function addToast({ title = '', message = '', type = 'info', duration = 4000 }) {
  const id = ++toastIdCounter;
  const toast = { id, title, message, type, duration };
  toasts.value.push(toast);

  if (duration > 0) {
    setTimeout(() => {
      removeToast(id);
    }, duration);
  }
  return id;
}

export function removeToast(id) {
  const idx = toasts.value.findIndex(t => t.id === id);
  if (idx !== -1) {
    toasts.value.splice(idx, 1);
  }
}

export const toast = {
  success(message, title = 'Success', duration = 4000) {
    return addToast({ title, message, type: 'success', duration });
  },
  error(message, title = 'Error', duration = 6000) {
    return addToast({ title, message, type: 'error', duration });
  },
  warning(message, title = 'Warning', duration = 5000) {
    return addToast({ title, message, type: 'warning', duration });
  },
  info(message, title = 'Information', duration = 4000) {
    return addToast({ title, message, type: 'info', duration });
  }
};
