import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import { hasCrashed } from "./composables/useCrashState.js";
import "./assets/design-tokens.css";
import "./assets/adaptive-utilities.css";

const app = createApp(App);

// Global safety net: any uncaught Vue error flips the shared crash flag so
// App.vue can render the recovery banner instead of a frozen/blank screen.
// The error itself is only logged in development to avoid leaking details.
app.config.errorHandler = (err, instance, info) => {
  if (import.meta.env.DEV) {
    console.error('Vue global error:', err, info);
  }
  hasCrashed.value = true;
};

app.use(router);

app.mount("#app");
