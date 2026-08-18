<template>
  <nav class="project-links" aria-label="Project transparency">
    <a
      href="https://github.com/sergey9519546/ASKTHEPEOPLE"
      target="_blank"
      rel="noopener noreferrer"
    >
      Source
    </a>
    <a
      href="https://github.com/sergey9519546/ASKTHEPEOPLE/blob/main/LICENSE"
      target="_blank"
      rel="noopener noreferrer"
    >
      AGPL-3.0
    </a>
    <a
      href="https://github.com/sergey9519546/ASKTHEPEOPLE/blob/main/PROVENANCE.md"
      target="_blank"
      rel="noopener noreferrer"
    >
      Provenance
    </a>
    <a
      href="https://github.com/sergey9519546/ASKTHEPEOPLE/blob/main/docs/THIRD_PARTY_NOTICES.md"
      target="_blank"
      rel="noopener noreferrer"
    >
      Notices
    </a>
  </nav>
</template>

<style scoped>
.project-links {
  display: flex;
  justify-content: flex-end;
  width: 100%;
  border-top: 1px solid var(--signal);
  background: var(--ink-deep);
}

.project-links a {
  padding: 0.48rem 0.65rem;
  border-right: 1px solid var(--line-dark);
  color: var(--paper-muted);
  font-family: var(--font-mono);
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.045em;
  text-decoration: none;
  text-transform: uppercase;
}

.project-links a:hover,
.project-links a:focus-visible {
  background: var(--signal);
  color: var(--ink);
}

@media (max-width: 540px) {
  .project-links a {
    flex: 1;
    text-align: center;
  }
}
</style>
