import { describe, it, expect, beforeEach } from 'vitest';
import { toasts, addToast, removeToast, toast } from '../utils/toast.js';

describe('Toast Notification Utility', () => {
  beforeEach(() => {
    toasts.value = [];
  });

  it('adds a toast to the active toasts list', () => {
    addToast({ title: 'Test', message: 'Hello World', type: 'success', duration: 0 });
    expect(toasts.value.length).toBe(1);
    expect(toasts.value[0].title).toBe('Test');
    expect(toasts.value[0].type).toBe('success');
  });

  it('removes a toast by ID', () => {
    const id = addToast({ title: 'Remove Me', duration: 0 });
    expect(toasts.value.length).toBe(1);
    removeToast(id);
    expect(toasts.value.length).toBe(0);
  });

  it('provides helper methods for success, error, warning, info', () => {
    toast.success('Operation complete');
    toast.error('Something went wrong');
    expect(toasts.value.length).toBe(2);
    expect(toasts.value[0].type).toBe('success');
    expect(toasts.value[1].type).toBe('error');
  });
});
