<template>
  <main class="not-found-view" aria-labelledby="not-found-heading">
    <aside aria-hidden="true">
      <span>404</span>
      <strong>Wrong turn</strong>
    </aside>

    <section>
      <p>Ask The People · Route recovery</p>
      <h1 id="not-found-heading">This path does not exist.</h1>
      <div class="route-line" aria-hidden="true">
        <span></span>
        <i></i>
        <b></b>
      </div>
      <p>
        The link may be outdated or incomplete. Return to the start to open a
        saved project or begin a new scenario.
      </p>
      <a class="nav-home-link" href="/" aria-label="Return to the start">
        Return to the start
        <span aria-hidden="true">→</span>
      </a>
    </section>

    <footer>
      <span>Clear route</span>
      <strong>One safe next step</strong>
    </footer>
  </main>
</template>

<script setup>
import { useRouter } from "vue-router";

const router = useRouter();
</script>

<style scoped>
.not-found-view {
  display: grid;
  grid-template-columns: minmax(16rem, 0.72fr) minmax(0, 1.8fr);
  grid-template-rows: minmax(0, 1fr) auto;
  min-height: 100dvh;
  background: var(--ink-deep);
  color: var(--paper);
}

.not-found-view > aside {
  position: relative;
  display: flex;
  grid-row: 1 / -1;
  flex-direction: column;
  justify-content: space-between;
  min-height: 100%;
  padding: clamp(2rem, 5vw, 5rem) clamp(1.5rem, 4vw, 4rem);
  overflow: hidden;
  border-right: 4px solid var(--signal);
  background: var(--ink);
  color: var(--paper);
}

.not-found-view > aside::after {
  position: absolute;
  right: -5rem;
  bottom: -3rem;
  width: 10rem;
  height: 58%;
  transform: rotate(9deg);
  background: linear-gradient(105deg, transparent 40%, rgba(242, 235, 221, 0.08) 60%, transparent 80%);
  content: "";
}

.not-found-view > aside span {
  position: relative;
  z-index: 1;
  font-family: var(--font-display);
  font-size: clamp(8rem, 18vw, 18rem);
  line-height: 0.75;
}

.not-found-view > aside strong {
  position: relative;
  z-index: 1;
  max-width: 6ch;
  font-family: var(--font-display);
  font-size: clamp(3.5rem, 8vw, 7rem);
  font-weight: 400;
  line-height: 0.82;
  text-transform: uppercase;
}

.not-found-view > section {
  align-self: center;
  max-width: 65rem;
  padding: clamp(3rem, 8vw, 8rem);
}

.not-found-view > section > p:first-child {
  margin: 0 0 1rem;
  color: var(--signal);
  font-family: var(--font-display);
  font-size: 1rem;
  letter-spacing: 0.065em;
  text-transform: uppercase;
}

.not-found-view h1 {
  max-width: 11ch;
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(4rem, 9vw, 9rem);
  font-weight: 400;
  letter-spacing: -0.02em;
  line-height: 0.86;
}

.route-line {
  display: grid;
  grid-template-columns: auto minmax(3rem, 1fr) auto;
  align-items: center;
  max-width: 42rem;
  margin: 2.2rem 0 1.7rem;
}

.route-line span,
.route-line b {
  width: 1.15rem;
  height: 1.15rem;
  border: 0.3rem solid var(--signal);
  border-radius: 50%;
}

.route-line b {
  background: var(--signal);
}

.route-line i {
  height: 0.3rem;
  background: var(--signal);
}

.not-found-view > section > p:last-of-type {
  max-width: 49ch;
  margin: 0;
  color: var(--paper-muted);
  font-size: 1rem;
  line-height: 1.6;
}

.not-found-view .nav-home-link {
  display: inline-flex;
  gap: 2rem;
  align-items: center;
  justify-content: space-between;
  min-width: 18rem;
  min-height: 3.8rem;
  margin-top: 2rem;
  padding: 0.8rem 1.2rem;
  border: 0;
  border-radius: 0;
  background: var(--signal);
  color: var(--ink);
  font-family: var(--font-display);
  font-size: 1.2rem;
  font-weight: 400;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  text-decoration: none;
}

.not-found-view .nav-home-link:hover {
  background: var(--paper-strong);
  transform: translateX(0.3rem);
}

.not-found-view .nav-home-link span {
  font-family: var(--font-sans);
  font-size: 1.5rem;
  font-weight: 700;
}

.not-found-view > footer {
  display: flex;
  gap: 1rem;
  align-items: center;
  justify-content: space-between;
  padding: 1.1rem clamp(1.5rem, 4vw, 4rem);
  border-top: 1px solid var(--line-dark);
  color: var(--paper-muted);
  font-size: 0.72rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.not-found-view > footer strong {
  color: var(--signal);
}

@media (max-width: 760px) {
  .not-found-view {
    grid-template-columns: 1fr;
    grid-template-rows: auto minmax(0, 1fr) auto;
  }

  .not-found-view > aside {
    grid-row: auto;
    min-height: 9rem;
    padding: 1.2rem;
  }

  .not-found-view > aside::after {
    right: 18%;
    bottom: -5rem;
    width: 7rem;
    height: 14rem;
  }

  .not-found-view > aside span {
    font-size: 6rem;
  }

  .not-found-view > aside strong {
    align-self: flex-end;
    margin-top: -2rem;
    padding: 0.15rem 0.35rem;
    background: var(--signal);
    font-size: 2.8rem;
    text-align: right;
  }

  .not-found-view > section {
    align-self: start;
    padding: 2.5rem 1.2rem;
  }

  .not-found-view h1 {
    font-size: clamp(4rem, 20vw, 6rem);
  }

  .not-found-view .nav-home-link {
    width: 100%;
    min-width: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .not-found-view .nav-home-link {
    transition: none;
  }
}
</style>
