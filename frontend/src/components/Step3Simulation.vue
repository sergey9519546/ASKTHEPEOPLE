<template>
  <div class="simulation-panel">
    <!-- Top Control Bar -->
    <div class="control-bar">
      <div class="status-group">
        <!-- Twitter/Info Plaza Platform Status -->
        <div
          class="platform-status twitter"
          :class="{
            active: runStatus.twitter_running,
            completed: runStatus.twitter_completed,
          }"
        >
          <div class="platform-header">
            <svg
              class="platform-icon"
              viewBox="0 0 24 24"
              width="14"
              height="14"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="2" y1="12" x2="22" y2="12"></line>
              <path
                d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"
              ></path>
            </svg>
            <span class="platform-name">Info Plaza (X)</span>
            <span v-if="runStatus.twitter_completed" class="status-badge">
              <svg
                viewBox="0 0 24 24"
                width="12"
                height="12"
                fill="none"
                stroke="currentColor"
                stroke-width="3"
              >
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            </span>
          </div>
          <div class="platform-stats">
            <span class="stat">
              <span class="stat-label">ROUND</span>
              <span class="stat-value mono"
                >{{ runStatus.twitter_current_round || 0
                }}<span class="stat-total"
                  >/{{ runStatus.total_rounds || maxRounds || "-" }}</span
                ></span
              >
            </span>
            <span class="stat">
              <span class="stat-label">Elapsed Time</span>
              <span class="stat-value mono">{{ twitterElapsedTime }}</span>
            </span>
            <span class="stat">
              <span class="stat-label">ACTS</span>
              <span class="stat-value mono">{{
                runStatus.twitter_actions_count || 0
              }}</span>
            </span>
          </div>
          <!-- Available Actions Tooltip -->
          <div class="actions-tooltip">
            <div class="tooltip-title">Available Actions</div>
            <div class="tooltip-actions">
              <span class="tooltip-action">POST</span>
              <span class="tooltip-action">LIKE</span>
              <span class="tooltip-action">REPOST</span>
              <span class="tooltip-action">QUOTE</span>
              <span class="tooltip-action">FOLLOW</span>
              <span class="tooltip-action">IDLE</span>
            </div>
          </div>
        </div>

        <!-- Reddit/Topic Community Platform Status -->
        <div
          class="platform-status reddit"
          :class="{
            active: runStatus.reddit_running,
            completed: runStatus.reddit_completed,
          }"
        >
          <div class="platform-header">
            <svg
              class="platform-icon"
              viewBox="0 0 24 24"
              width="14"
              height="14"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"
              ></path>
            </svg>
            <span class="platform-name">Topic Community (Reddit)</span>
            <span v-if="runStatus.reddit_completed" class="status-badge">
              <svg
                viewBox="0 0 24 24"
                width="12"
                height="12"
                fill="none"
                stroke="currentColor"
                stroke-width="3"
              >
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            </span>
          </div>
          <div class="platform-stats">
            <span class="stat">
              <span class="stat-label">ROUND</span>
              <span class="stat-value mono"
                >{{ runStatus.reddit_current_round || 0
                }}<span class="stat-total"
                  >/{{ runStatus.total_rounds || maxRounds || "-" }}</span
                ></span
              >
            </span>
            <span class="stat">
              <span class="stat-label">Elapsed Time</span>
              <span class="stat-value mono">{{ redditElapsedTime }}</span>
            </span>
            <span class="stat">
              <span class="stat-label">ACTS</span>
              <span class="stat-value mono">{{
                runStatus.reddit_actions_count || 0
              }}</span>
            </span>
          </div>
          <!-- Available Actions Tooltip -->
          <div class="actions-tooltip">
            <div class="tooltip-title">Available Actions</div>
            <div class="tooltip-actions">
              <span class="tooltip-action">POST</span>
              <span class="tooltip-action">COMMENT</span>
              <span class="tooltip-action">LIKE</span>
              <span class="tooltip-action">DISLIKE</span>
              <span class="tooltip-action">SEARCH</span>
              <span class="tooltip-action">TREND</span>
              <span class="tooltip-action">FOLLOW</span>
              <span class="tooltip-action">MUTE</span>
              <span class="tooltip-action">REFRESH</span>
              <span class="tooltip-action">IDLE</span>
            </div>
          </div>
        </div>
      </div>

      <div class="action-controls" style="display: flex; gap: 10px; align-items: center;">
        <button
          class="inject-action-btn"
          style="background: rgba(225, 29, 72, 0.15); color: #f43f5e; border: 1fr solid rgba(225, 29, 72, 0.3); padding: 10px 16px; border-radius: 8px; font-weight: 700; font-size: 11px; cursor: pointer; display: flex; items-center; gap: 6px; transition: all 0.2s;"
          @click="showInjectModal = true"
        >
          ⚡ INJECT SCENARIO EVENT
        </button>
        <button
          class="final-action-btn"
          :disabled="!canGenerateReport || isGeneratingReport"
          @click="handleNextStep"
        >
          <span v-if="isGeneratingReport" class="spinner-sm"></span>
          {{
            isGeneratingReport
              ? "GENERATING REPORT..."
              : "GENERATE CONVERSION REPORT ➝"
          }}
        </button>
      </div>
    </div>

    <!-- Preflight / Diagnostics Strip -->
    <div
      class="contract-strip"
      v-if="preflight || diagnostics || diagnosticsError"
    >
      <div
        class="contract-card"
        :class="
          preflight?.status === 'failed' ? 'contract-failed' : 'contract-ok'
        "
      >
        <span class="contract-label">Preflight</span>
        <span class="contract-value">{{ preflight?.status || "loading" }}</span>
        <span class="contract-meta" v-if="preflight">
          {{ preflight.failed_checks?.length || 0 }} FAILED CHECKS
        </span>
      </div>

      <div class="contract-card" v-if="diagnostics">
        <span class="contract-label">Canonical Agents</span>
        <span class="contract-value">{{
          diagnostics.canonical_agents?.length || 0
        }}</span>
        <span class="contract-meta">
          {{ diagnostics.entity_type_registry?.length || 0 }} NORMALIZED ROLES
        </span>
      </div>

      <div class="contract-card" v-if="diagnostics">
        <span class="contract-label">Bootstrap Graph</span>
        <span class="contract-value">{{
          diagnostics.relationship_bootstrap?.length || 0
        }}</span>
        <span class="contract-meta">RELATIONSHIP SEEDS Loaded</span>
      </div>

      <div class="contract-card" v-if="diagnostics?.model_resolution?.actor">
        <span class="contract-label">Actor Model</span>
        <span class="contract-value">{{
          diagnostics.model_resolution.actor.model_name || "unknown"
        }}</span>
        <span class="contract-meta">
          {{ diagnostics.model_resolution.actor.provider_mode || "unknown" }}
        </span>
      </div>

      <div class="contract-card contract-error" v-if="diagnosticsError">
        <span class="contract-label">Diagnostics</span>
        <span class="contract-value">UNAVAILABLE</span>
        <span class="contract-meta">{{ diagnosticsError }}</span>
      </div>
    </div>

    <!-- Main Content: Dual Timeline & Metrics -->
    <div class="main-content-area" ref="scrollContainer">
      <!-- Timeline Header -->
      <div class="timeline-header" v-if="allActions.length > 0 || phase === 2">
        <div class="timeline-stats">
          <div class="subtabs-nav">
            <button
              class="subtab-btn"
              :class="{ 'is-active': activeSubTab === 'timeline' }"
              @click="activeSubTab = 'timeline'"
            >
              TIMELINE FEED
            </button>
            <button
              class="subtab-btn"
              :class="{ 'is-active': activeSubTab === 'metrics' }"
              @click="activeSubTab = 'metrics'"
            >
              NETWORK ANALYTICS
            </button>
          </div>

          <span class="platform-breakdown" v-if="activeSubTab === 'timeline'">
            <span class="breakdown-item twitter">
              <svg
                class="mini-icon"
                viewBox="0 0 24 24"
                width="12"
                height="12"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="2" y1="12" x2="22" y2="12"></line>
                <path
                  d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"
                ></path>
              </svg>
              <span class="mono">{{ twitterActionsCount }}</span>
            </span>
            <span class="breakdown-divider">/</span>
            <span class="breakdown-item reddit">
              <svg
                class="mini-icon"
                viewBox="0 0 24 24"
                width="12"
                height="12"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <path
                  d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"
                ></path>
              </svg>
              <span class="mono">{{ redditActionsCount }}</span>
            </span>
          </span>
          <span class="platform-breakdown" v-else-if="metricsData">
            <span class="breakdown-item mono">
              AGENTS: {{ metricsData.total_agents }} / ACTIONS: {{ metricsData.total_actions }}
            </span>
          </span>
        </div>
      </div>

      <!-- Timeline Feed -->
      <div class="timeline-feed" v-show="activeSubTab === 'timeline'">
        <div class="timeline-axis"></div>

        <TransitionGroup name="timeline-item">
          <div
            v-for="action in chronologicalActions"
            :key="
              action._uniqueId ||
              action.id ||
              `${action.timestamp}-${action.agent_id}`
            "
            class="timeline-item-wrapper"
            :class="action.platform"
          >
            <div class="timeline-marker">
              <div class="marker-dot"></div>
            </div>

            <div class="timeline-card">
              <div class="timeline-card-header">
                <div class="agent-info">
                  <div class="avatar-placeholder">
                    {{ (action.agent_name || "A")[0] }}
                  </div>
                  <span class="agent-name">{{ action.agent_name }}</span>
                </div>

                <div class="header-meta">
                  <div class="platform-indicator">
                    <svg
                      v-if="action.platform === 'twitter'"
                      viewBox="0 0 24 24"
                      width="12"
                      height="12"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <circle cx="12" cy="12" r="10"></circle>
                      <line x1="2" y1="12" x2="22" y2="12"></line>
                      <path
                        d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"
                      ></path>
                    </svg>
                    <svg
                      v-else
                      viewBox="0 0 24 24"
                      width="12"
                      height="12"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path
                        d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"
                      ></path>
                    </svg>
                  </div>
                  <div
                    class="action-badge"
                    :class="getActionTypeClass(action.action_type)"
                  >
                    {{ getActionTypeLabel(action.action_type) }}
                  </div>
                </div>
              </div>

              <div class="card-body">
                <!-- CREATE_POST -->
                <div
                  v-if="
                    action.action_type === 'CREATE_POST' &&
                    action.action_args?.content
                  "
                  class="content-text main-text"
                >
                  {{ action.action_args.content }}
                </div>

                <!-- QUOTE_POST -->
                <template v-if="action.action_type === 'QUOTE_POST'">
                  <div
                    v-if="action.action_args?.quote_content"
                    class="content-text"
                  >
                    {{ action.action_args.quote_content }}
                  </div>
                  <div
                    v-if="action.action_args?.original_content"
                    class="quoted-block"
                  >
                    <div class="quote-header">
                      <svg
                        class="icon-small"
                        viewBox="0 0 24 24"
                        width="12"
                        height="12"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                      >
                        <path
                          d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"
                        ></path>
                        <path
                          d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"
                        ></path>
                      </svg>
                      <span class="quote-label"
                        >@{{
                          action.action_args.original_author_name || "User"
                        }}</span
                      >
                    </div>
                    <div class="quote-text">
                      {{
                        truncateContent(
                          action.action_args.original_content,
                          150,
                        )
                      }}
                    </div>
                  </div>
                </template>

                <!-- REPOST -->
                <template v-if="action.action_type === 'REPOST'">
                  <div class="repost-info">
                    <svg
                      class="icon-small"
                      viewBox="0 0 24 24"
                      width="14"
                      height="14"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <polyline points="17 1 21 5 17 9"></polyline>
                      <path d="M3 11V9a4 4 0 0 1 4-4h14"></path>
                      <polyline points="7 23 3 19 7 15"></polyline>
                      <path d="M21 13v2a4 4 0 0 1-4 4H3"></path>
                    </svg>
                    <span class="repost-label"
                      >Reposted from @{{
                        action.action_args?.original_author_name || "User"
                      }}</span
                    >
                  </div>
                  <div
                    v-if="action.action_args?.original_content"
                    class="repost-content"
                  >
                    {{
                      truncateContent(action.action_args.original_content, 200)
                    }}
                  </div>
                </template>

                <!-- LIKE_POST -->
                <template v-if="action.action_type === 'LIKE_POST'">
                  <div class="like-info">
                    <svg
                      class="icon-small filled"
                      viewBox="0 0 24 24"
                      width="14"
                      height="14"
                      fill="currentColor"
                    >
                      <path
                        d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"
                      ></path>
                    </svg>
                    <span class="like-label"
                      >Liked @{{
                        action.action_args?.post_author_name || "User"
                      }}'s post</span
                    >
                  </div>
                  <div
                    v-if="action.action_args?.post_content"
                    class="liked-content"
                  >
                    "{{
                      truncateContent(action.action_args.post_content, 120)
                    }}"
                  </div>
                </template>

                <!-- CREATE_COMMENT -->
                <template v-if="action.action_type === 'CREATE_COMMENT'">
                  <div v-if="action.action_args?.content" class="content-text">
                    {{ action.action_args.content }}
                  </div>
                  <div
                    v-if="action.action_args?.post_id"
                    class="comment-context"
                  >
                    <svg
                      class="icon-small"
                      viewBox="0 0 24 24"
                      width="12"
                      height="12"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path
                        d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"
                      ></path>
                    </svg>
                    <span>Reply to post #{{ action.action_args.post_id }}</span>
                  </div>
                </template>

                <!-- SEARCH_POSTS -->
                <template v-if="action.action_type === 'SEARCH_POSTS'">
                  <div class="search-info">
                    <svg
                      class="icon-small"
                      viewBox="0 0 24 24"
                      width="14"
                      height="14"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <circle cx="11" cy="11" r="8"></circle>
                      <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                    </svg>
                    <span class="search-label">Search Query:</span>
                    <span class="search-query"
                      >"{{ action.action_args?.query || "" }}"</span
                    >
                  </div>
                </template>

                <!-- FOLLOW -->
                <template v-if="action.action_type === 'FOLLOW'">
                  <div class="follow-info">
                    <svg
                      class="icon-small"
                      viewBox="0 0 24 24"
                      width="14"
                      height="14"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path
                        d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"
                      ></path>
                      <circle cx="8.5" cy="7" r="4"></circle>
                      <line x1="20" y1="8" x2="20" y2="14"></line>
                      <line x1="23" y1="11" x2="17" y2="11"></line>
                    </svg>
                    <span class="follow-label"
                      >Followed @{{
                        action.action_args?.target_user ||
                        action.action_args?.user_id ||
                        "User"
                      }}</span
                    >
                  </div>
                </template>

                <!-- UPVOTE / DOWNVOTE -->
                <template
                  v-if="
                    action.action_type === 'UPVOTE_POST' ||
                    action.action_type === 'DOWNVOTE_POST'
                  "
                >
                  <div class="vote-info">
                    <svg
                      v-if="action.action_type === 'UPVOTE_POST'"
                      class="icon-small"
                      viewBox="0 0 24 24"
                      width="14"
                      height="14"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <polyline points="18 15 12 9 6 15"></polyline>
                    </svg>
                    <svg
                      v-else
                      class="icon-small"
                      viewBox="0 0 24 24"
                      width="14"
                      height="14"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <polyline points="6 9 12 15 18 9"></polyline>
                    </svg>
                    <span class="vote-label"
                      >{{
                        action.action_type === "UPVOTE_POST"
                          ? "Upvoted"
                          : "Downvoted"
                      }}
                      Post</span
                    >
                  </div>
                  <div
                    v-if="action.action_args?.post_content"
                    class="voted-content"
                  >
                    "{{
                      truncateContent(action.action_args.post_content, 120)
                    }}"
                  </div>
                </template>

                <!-- DO_NOTHING -->
                <template v-if="action.action_type === 'DO_NOTHING'">
                  <div class="idle-info">
                    <svg
                      class="icon-small"
                      viewBox="0 0 24 24"
                      width="14"
                      height="14"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <circle cx="12" cy="12" r="10"></circle>
                      <line x1="12" y1="8" x2="12" y2="12"></line>
                      <line x1="12" y1="16" x2="12.01" y2="16"></line>
                    </svg>
                    <span class="idle-label">Action Skipped (Idle)</span>
                  </div>
                </template>

                <!-- Unknown fallback -->
                <div
                  v-if="
                    ![
                      'CREATE_POST',
                      'QUOTE_POST',
                      'REPOST',
                      'LIKE_POST',
                      'CREATE_COMMENT',
                      'SEARCH_POSTS',
                      'FOLLOW',
                      'UPVOTE_POST',
                      'DOWNVOTE_POST',
                      'DO_NOTHING',
                    ].includes(action.action_type) &&
                    action.action_args?.content
                  "
                  class="content-text"
                >
                  {{ action.action_args.content }}
                </div>
              </div>

              <div class="card-footer">
                <span class="time-tag"
                  >ROUND {{ action.round_num }} •
                  {{ formatActionTime(action.timestamp) }}</span
                >
              </div>
            </div>
          </div>
        </TransitionGroup>

        <div v-if="allActions.length === 0" class="waiting-state">
          <div class="spinner-sm"></div>
          <span>Synchronizing simulation nodes...</span>
        </div>
      </div>

      <!-- Network Metrics Content -->
      <div class="metrics-dashboard" v-show="activeSubTab === 'metrics'">
        <div v-if="loadingMetrics" class="metrics-loading">
          <div class="spinner-sm"></div>
          <span>Calculating polarization, modularity and cascades...</span>
        </div>

        <div v-else-if="metricsError" class="metrics-error">
          <div class="error-icon">⚠️</div>
          <div class="error-msg">Failed to load simulation metrics: {{ metricsError }}</div>
          <button class="retry-btn" @click="fetchMetrics">Retry Metrics Calculation</button>
        </div>

        <div v-else-if="!metricsData" class="metrics-empty">
          <span>No metrics calculated yet. Finish the simulation to calculate modularity and inequality scores.</span>
        </div>

        <div v-else class="metrics-content">
          <!-- TOP ROW: OVERALL INDICES -->
          <div class="metrics-grid">
            <!-- Modularity / Polarization Score -->
            <div class="metric-card polarization">
              <span class="metric-label">Polarization Index (Q Score)</span>
              <div class="metric-value-wrapper">
                <span class="metric-value mono">{{ (metricsData.polarization_index || 0).toFixed(3) }}</span>
                <span class="metric-badge" :class="polarizationLevelClass">
                  {{ polarizationLevelText }}
                </span>
              </div>
              <p class="metric-desc">
                Measures network clustering modularity. High modularity (>0.4) indicates clear ideological polarization and echo-chambers.
              </p>
              <div class="gauge-bar">
                <div class="gauge-fill" :style="{ width: `${(metricsData.polarization_index || 0) * 100}%`, backgroundColor: 'var(--accent-color)' }"></div>
              </div>
            </div>

            <!-- Engagement Gini Coefficient -->
            <div class="metric-card gini">
              <span class="metric-label">Engagement Gini Coefficient</span>
              <div class="metric-value-wrapper">
                <span class="metric-value mono">{{ (metricsData.engagement_gini || 0).toFixed(3) }}</span>
                <span class="metric-badge" :class="giniLevelClass">
                  {{ giniLevelText }}
                </span>
              </div>
              <p class="metric-desc">
                Measures engagement skew. High coefficient (>0.6) shows that a few elite agents account for the vast majority of interactions.
              </p>
              <div class="gauge-bar">
                <div class="gauge-fill" :style="{ width: `${(metricsData.engagement_gini || 0) * 100}%`, backgroundColor: 'var(--accent-secondary)' }"></div>
              </div>
            </div>

            <!-- Echo Chamber Score -->
            <div class="metric-card echo-chamber">
              <span class="metric-label">Echo Chamber Index</span>
              <div class="metric-value-wrapper">
                <span class="metric-value mono">{{ ((metricsData.echo_chamber_score || 0) * 100).toFixed(1) }}%</span>
                <span class="metric-badge" :class="echoLevelClass">
                  {{ echoLevelText }}
                </span>
              </div>
              <p class="metric-desc">
                The percentage of total interactions (replies, likes, quotes) occurring between agents of the same social cluster.
              </p>
              <div class="gauge-bar">
                <div class="gauge-fill" :style="{ width: `${(metricsData.echo_chamber_score || 0) * 100}%`, backgroundColor: 'var(--accent-tertiary)' }"></div>
              </div>
            </div>
          </div>

          <!-- SECOND ROW: DUAL PANELS -->
          <div class="metrics-dual-layout">
            <!-- Left: Top Participating Agents & Action Type Distribution -->
            <div class="metrics-left-panel">
              <div class="analytics-section">
                <h3>ACTION TYPE DISTRIBUTION</h3>
                <div class="distribution-list">
                  <div 
                    v-for="(count, type) in metricsData.action_type_distribution" 
                    :key="type" 
                    class="dist-item"
                  >
                    <div class="dist-meta">
                      <span class="dist-type mono">{{ type }}</span>
                      <span class="dist-count mono">{{ count }}</span>
                    </div>
                    <div class="dist-bar">
                      <div class="dist-bar-fill" :style="{ width: `${(count / (metricsData.total_actions || 1)) * 100}%` }"></div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="analytics-section" style="margin-top: 30px;">
                <h3>TOP PARTICIPATING AGENTS</h3>
                <div class="top-agents-table">
                  <div class="table-header">
                    <span class="col-agent">AGENT</span>
                    <span class="col-actions">ACTIONS</span>
                  </div>
                  <div 
                    v-for="agent in metricsData.top_agents" 
                    :key="agent.agent_id" 
                    class="table-row"
                  >
                    <span class="col-agent truncate-text">
                      <span class="agent-avatar">{{ (agent.agent_name || 'A')[0] }}</span>
                      @{{ agent.agent_name }}
                    </span>
                    <span class="col-actions mono">{{ agent.action_count }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Right: Top 5 Virality Cascades -->
            <div class="metrics-right-panel">
              <div class="analytics-section">
                <h3>VIRALITY & INFECTIOUS CASCADES</h3>
                <p class="section-subtitle">Top posts ordered by viral reach and multi-agent engagement cascades.</p>
                
                <div v-if="!metricsData.cascade_stats || metricsData.cascade_stats.length === 0" class="no-cascades">
                  No viral cascades detected in this run.
                </div>
                <div v-else class="cascade-cards-list">
                  <div 
                    v-for="(post, index) in metricsData.cascade_stats.slice(0, 5)" 
                    :key="post.post_id" 
                    class="cascade-post-card"
                  >
                    <div class="cascade-post-header">
                      <span class="cascade-rank mono">#{{ index + 1 }}</span>
                      <span class="cascade-author">@{{ post.author_name }}</span>
                      <span class="cascade-platform-badge" :class="post.platform">{{ post.platform.toUpperCase() }}</span>
                    </div>
                    
                    <p class="cascade-post-content">"{{ post.content }}"</p>
                    
                    <div class="cascade-post-stats">
                      <div class="stat-item">
                        <span class="stat-icon">❤️</span>
                        <span class="stat-num mono">{{ post.likes }}</span>
                      </div>
                      <div class="stat-item" v-if="post.reposts !== undefined">
                        <span class="stat-icon">🔄</span>
                        <span class="stat-num mono">{{ post.reposts }}</span>
                      </div>
                      <div class="stat-item">
                        <span class="stat-icon">💬</span>
                        <span class="stat-num mono">{{ post.comments }}</span>
                      </div>
                      <div class="stat-item total">
                        <span class="stat-label">SCORE:</span>
                        <span class="stat-num mono highlighted">{{ post.engagement_score }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Bottom Info / Logs -->
    <div class="system-logs">
      <div class="log-header">
        <span class="log-title">SIMULATION MONITOR</span>
        <span class="log-id">{{ simulationId || "NO SIMULATION" }}</span>
      </div>
      <div class="log-content" ref="logContent">
        <div class="log-line" v-for="(log, idx) in systemLogs" :key="idx">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-msg">{{ log.msg }}</span>
        </div>
      </div>
    </div>

    <!-- LIVE SCENARIO INJECTION MODAL -->
    <div v-if="showInjectModal" class="modal-overlay" style="position: fixed; inset: 0; z-index: 1000; background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(4px); display: flex; items-center; justify-content: center; padding: 16px;" @click.self="showInjectModal = false">
      <div class="modal-card" style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px; width: 100%; max-width: 520px; padding: 24px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <h3 style="font-size: 14px; font-weight: 700; color: #0f172a; text-transform: uppercase; letter-spacing: 0.05em; display: flex; align-items: center; gap: 6px; margin: 0;">
            <span>⚡</span> Inject Live Scenario Event
          </h3>
          <button @click="showInjectModal = false" style="background: transparent; border: none; font-size: 18px; color: #64748b; cursor: pointer;">✕</button>
        </div>
        <p style="font-size: 12px; color: #64748b; margin-bottom: 16px; leading-height: 1.5;">
          Inject a breaking press release, external statement, or crisis event into the live simulation. All social agents will process this event in subsequent rounds.
        </p>

        <div style="margin-bottom: 16px;">
          <label style="font-size: 11px; font-weight: 700; color: #475569; text-transform: uppercase; display: block; margin-bottom: 6px;">Target Platform</label>
          <select v-model="injectPlatform" style="width: 100%; padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 12px; background: #f8fafc; outline: none;">
            <option value="parallel">Parallel (Both X/Twitter & Reddit)</option>
            <option value="twitter">X (Twitter) Plaza Only</option>
            <option value="reddit">Reddit Community Only</option>
          </select>
        </div>

        <div style="margin-bottom: 16px;">
          <label style="font-size: 11px; font-weight: 700; color: #475569; text-transform: uppercase; display: block; margin-bottom: 6px;">Event Content / Breaking News Text</label>
          <textarea 
            v-model="injectContent" 
            rows="4" 
            placeholder="e.g. BREAKING: Regulatory authorities announce unexpected policy shift impacting market pricing..."
            style="width: 100%; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 12px; outline: none; font-family: inherit; resize: vertical;"
          ></textarea>
        </div>

        <div v-if="injectMessage" style="font-size: 11px; font-weight: 600; padding: 10px; border-radius: 6px; margin-bottom: 16px;" :style="{ background: injectMessage.startsWith('✓') ? '#ecfdf5' : '#fef2f2', color: injectMessage.startsWith('✓') ? '#047857' : '#b91c1c' }">
          {{ injectMessage }}
        </div>

        <div style="display: flex; justify-content: flex-end; gap: 8px;">
          <button @click="showInjectModal = false" style="padding: 8px 16px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 12px; font-weight: 600; color: #475569; background: #ffffff; cursor: pointer;">Cancel</button>
          <button 
            @click="handleInjectScenario" 
            :disabled="isInjecting || !injectContent.trim()" 
            style="padding: 8px 16px; border: none; border-radius: 8px; font-size: 12px; font-weight: 700; color: #ffffff; background: #e11d48; cursor: pointer; display: flex; align-items: center; gap: 6px;"
          >
            <span v-if="isInjecting" class="spinner-sm"></span>
            <span>Inject Event</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import { generateReport } from "../api/report";
import {
  getSimulationActions,
  getSimulationDiagnostics,
  getSimulationPreflight,
  startSimulation,
  getSimulationMetrics,
} from "../api/simulation";
import axios from "axios";
import { connectSimulationWs } from "../api/ws";

// Live Scenario Injection State
const showInjectModal = ref(false);
const injectContent = ref("");
const injectPlatform = ref("parallel");
const isInjecting = ref(false);
const injectMessage = ref("");

const props = defineProps({
  simulationId: String,
  maxRounds: Number,
  minutesPerRound: {
    type: Number,
    default: 15, // Updated default to 15m/round for precision
  },
  projectData: Object,
  graphData: Object,
  systemLogs: Array,
});

const emit = defineEmits(["go-back", "next-step", "add-log", "update-status"]);
const router = useRouter();

// State
const isGeneratingReport = ref(false);
const phase = ref(0); // 0: Idle, 1: Running, 2: Completed
const isStarting = ref(false);
const isStopping = ref(false);
const startError = ref(null);
const runStatus = ref({});
const allActions = ref([]);
const actionIds = ref(new Set());
const scrollContainer = ref(null);
const preflight = ref(null);
const diagnostics = ref(null);
const diagnosticsError = ref(null);

// Metrics Dashboard State
const activeSubTab = ref("timeline");
const metricsData = ref(null);
const loadingMetrics = ref(false);
const metricsError = ref(null);

const chronologicalActions = computed(() => {
  return allActions.value;
});

const twitterActionsCount = computed(() => {
  return allActions.value.filter((a) => a.platform === "twitter").length;
});

const redditActionsCount = computed(() => {
  return allActions.value.filter((a) => a.platform === "reddit").length;
});

const formatElapsedTime = (currentRound) => {
  if (!currentRound || currentRound <= 0) return "0h 0m";
  const totalMinutes = currentRound * props.minutesPerRound;
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return `${hours}h ${minutes}m`;
};

const twitterElapsedTime = computed(() => {
  return formatElapsedTime(runStatus.value.twitter_current_round || 0);
});

const redditElapsedTime = computed(() => {
  return formatElapsedTime(runStatus.value.reddit_current_round || 0);
});

const canGenerateReport = computed(() => {
  return phase.value === 2 && runStatus.value.runner_status !== "interrupted";
});

// Computed properties for metrics levels
const polarizationLevelText = computed(() => {
  const q = metricsData.value?.polarization_index || 0;
  if (q < 0.3) return "LOW";
  if (q < 0.5) return "MODERATE";
  return "HIGH";
});
const polarizationLevelClass = computed(() => {
  const q = metricsData.value?.polarization_index || 0;
  if (q < 0.3) return "badge-green";
  if (q < 0.5) return "badge-yellow";
  return "badge-red";
});

const giniLevelText = computed(() => {
  const g = metricsData.value?.engagement_gini || 0;
  if (g < 0.35) return "EQUAL";
  if (g < 0.6) return "BALANCED";
  return "CONCENTRATED";
});
const giniLevelClass = computed(() => {
  const g = metricsData.value?.engagement_gini || 0;
  if (g < 0.35) return "badge-green";
  if (g < 0.6) return "badge-yellow";
  return "badge-red";
});

const echoLevelText = computed(() => {
  const e = metricsData.value?.echo_chamber_score || 0;
  if (e < 0.45) return "OPEN";
  if (e < 0.7) return "PARTIAL";
  return "SEGREGATED";
});
const echoLevelClass = computed(() => {
  const e = metricsData.value?.echo_chamber_score || 0;
  if (e < 0.45) return "badge-green";
  if (e < 0.7) return "badge-yellow";
  return "badge-red";
});

const fetchMetrics = async (force = false) => {
  if (!props.simulationId) return;
  loadingMetrics.value = true;
  metricsError.value = null;
  try {
    const res = await getSimulationMetrics(props.simulationId, force);
    if (res.success && res.data) {
      metricsData.value = res.data;
    } else {
      metricsError.value = res.error || "Failed to load metrics data";
    }
  } catch (err) {
    metricsError.value = err.message || "Error contacting metrics API";
  } finally {
    loadingMetrics.value = false;
  }
};

const addLog = (msg) => {
  emit("add-log", msg);
};

const fetchExecutionContracts = async () => {
  if (!props.simulationId) return;

  diagnosticsError.value = null;
  try {
    const [preflightRes, diagnosticsRes] = await Promise.all([
      getSimulationPreflight(props.simulationId),
      getSimulationDiagnostics(props.simulationId),
    ]);

    if (preflightRes.success) {
      preflight.value = preflightRes.data;
    }

    if (diagnosticsRes.success) {
      diagnostics.value = diagnosticsRes.data;
    } else {
      diagnosticsError.value =
        diagnosticsRes.error || "failed to load diagnostics";
    }
  } catch (err) {
    diagnosticsError.value = err.message || "failed to load diagnostics";
  }
};

const resetAllState = () => {
  phase.value = 0;
  runStatus.value = {};
  allActions.value = [];
  actionIds.value = new Set();
  prevTwitterRound.value = 0;
  prevRedditRound.value = 0;
  startError.value = null;
  isStarting.value = false;
  isStopping.value = false;
  stopWs();
};

const doStartSimulation = async () => {
  if (!props.simulationId) {
    addLog("Error: Missing simulationId");
    return;
  }

  resetAllState();
  isStarting.value = true;
  startError.value = null;
  addLog("Initiating dual-platform parallel simulation engine...");
  emit("update-status", "processing");

  try {
    const params = {
      simulation_id: props.simulationId,
      platform: "parallel",
      force: true,
      enable_graph_memory_update: true,
    };

    if (props.maxRounds) {
      params.max_rounds = props.maxRounds;
      addLog(`Setting temporal depth: ${props.maxRounds} rounds`);
    }

    const res = await startSimulation(params);

    if (res.success && res.data) {
      if (res.data.force_restarted) {
        addLog("✓ Flushed legacy logs, restarting from seed state");
      }
      addLog("✓ Simulation engine initiated successfully");
      addLog(`  └─ Engine PID: ${res.data.process_pid || "-"}`);

      phase.value = 1;
      runStatus.value = res.data;

      startWs();
    } else {
      startError.value = res.error || "failed to start";
      addLog(`✗ Initiation failed: ${res.error || "unknown error"}`);
      emit("update-status", "error");
    }
  } catch (err) {
    startError.value = err.message;
    addLog(`✗ Initiation exception: ${err.message}`);
    emit("update-status", "error");
  } finally {
    isStarting.value = false;
  }
};

let _simWs = null;

const prevTwitterRound = ref(0);
const prevRedditRound = ref(0);

const _mergeActions = (incoming) => {
  incoming.forEach((action) => {
    const actionId =
      action.id ||
      `${action.timestamp}-${action.platform}-${action.agent_id}-${action.action_type}`;
    if (!actionIds.value.has(actionId)) {
      actionIds.value.add(actionId);
      allActions.value.push({ ...action, _uniqueId: actionId });
    }
  });
};

const _handleWsFrame = async (frame) => {
  if (frame.type === "state") {
    const data = frame;
    runStatus.value = data;

    if (data.runner_status === "interrupted") {
      addLog(`Simulation Interrupted: ${data.error || "runtime failure"}`);
      phase.value = 2;
      stopWs();
      emit("update-status", "error");
      return;
    }

    if (data.twitter_current_round > prevTwitterRound.value) {
      addLog(
        `[PLAZA] R${data.twitter_current_round}/${data.total_rounds} | T:${data.twitter_simulated_hours || 0}h | A:${data.twitter_actions_count}`,
      );
      prevTwitterRound.value = data.twitter_current_round;
    }

    if (data.reddit_current_round > prevRedditRound.value) {
      addLog(
        `[COMMUNITY] R${data.reddit_current_round}/${data.total_rounds} | T:${data.reddit_simulated_hours || 0}h | A:${data.reddit_actions_count}`,
      );
      prevRedditRound.value = data.reddit_current_round;
    }

    if (Array.isArray(data.recent_actions)) {
      _mergeActions(data.recent_actions);
    }

    const isCompleted =
      data.runner_status === "completed" || data.runner_status === "stopped";
    const platformsCompleted = checkPlatformsCompleted(data);

    if (isCompleted || platformsCompleted) {
      addLog("✓ Simulation cycle complete");
      phase.value = 2;
      stopWs();
      emit("update-status", "completed");
      fetchMetrics();
      // Load full action history once
      try {
        const res = await getSimulationActions(props.simulationId);
        if (res.success && res.data) {
          _mergeActions(res.data.actions || res.data || []);
        }
      } catch (_) { /* non-critical */ }
    }
  } else if (frame.type === "done") {
    addLog("✓ Simulation cycle complete");
    phase.value = 2;
    stopWs();
    emit("update-status", "completed");
    fetchMetrics();
    try {
      const res = await getSimulationActions(props.simulationId);
      if (res.success && res.data) {
        _mergeActions(res.data.actions || res.data || []);
      }
    } catch (_) { /* non-critical */ }
  } else if (frame.type === "error") {
    addLog(`WS error: ${frame.message || "unknown"}`);
  }
};

const startWs = () => {
  if (!props.simulationId) return;
  stopWs();
  _simWs = connectSimulationWs(props.simulationId, {
    onMessage: _handleWsFrame,
    onClose: () => { _simWs = null; },
    onError: (e) => { if (import.meta.env.DEV) console.warn("Simulation WS error:", e); },
  });
};

const stopWs = () => {
  if (_simWs) {
    _simWs.close();
    _simWs = null;
  }
};

const checkPlatformsCompleted = (data) => {
  if (!data) return false;
  const twitterCompleted = data.twitter_completed === true;
  const redditCompleted = data.reddit_completed === true;
  const twitterEnabled =
    data.twitter_actions_count > 0 || data.twitter_running || twitterCompleted;
  const redditEnabled =
    data.reddit_actions_count > 0 || data.reddit_running || redditCompleted;
  if (!twitterEnabled && !redditEnabled) return false;
  if (twitterEnabled && !twitterCompleted) return false;
  if (redditEnabled && !redditCompleted) return false;
  return true;
};

const getActionTypeLabel = (type) => {
  const labels = {
    CREATE_POST: "POST",
    REPOST: "REPOST",
    LIKE_POST: "LIKE",
    CREATE_COMMENT: "COMMENT",
    LIKE_COMMENT: "LIKE",
    DO_NOTHING: "IDLE",
    FOLLOW: "FOLLOW",
    SEARCH_POSTS: "SEARCH",
    QUOTE_POST: "QUOTE",
    UPVOTE_POST: "UPVOTE",
    DOWNVOTE_POST: "DOWNVOTE",
  };
  return labels[type] || type || "UNKNOWN";
};

const getActionTypeClass = (type) => {
  const classes = {
    CREATE_POST: "badge-post",
    REPOST: "badge-blue",
    LIKE_POST: "badge-red",
    CREATE_COMMENT: "badge-yellow",
    LIKE_COMMENT: "badge-red",
    QUOTE_POST: "badge-post",
    FOLLOW: "badge-black",
    SEARCH_POSTS: "badge-black",
    UPVOTE_POST: "badge-blue",
    DOWNVOTE_POST: "badge-red",
    DO_NOTHING: "badge-idle",
  };
  return classes[type] || "badge-default";
};

const truncateContent = (content, maxLength = 100) => {
  if (!content) return "";
  if (content.length > maxLength)
    return content.substring(0, maxLength) + "...";
  return content;
};

const formatActionTime = (timestamp) => {
  if (!timestamp) return "";
  try {
    return new Date(timestamp).toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return "";
  }
};

const handleNextStep = async () => {
  if (!props.simulationId) {
    addLog("Error: Missing simulationId");
    return;
  }
  if (isGeneratingReport.value) return;

  isGeneratingReport.value = true;
  addLog("Initiating report synthesis engine...");

  try {
    const res = await generateReport({
      simulation_id: props.simulationId,
      force_regenerate: true,
    });

    if (res.success && res.data) {
      const reportId = res.data.report_id;
      addLog(`✓ Report synthesis task initiated: ${reportId}`);
      router.push({ name: "Report", params: { reportId } });
    } else {
      addLog(`✗ Report synthesis failed: ${res.error || "unknown error"}`);
      isGeneratingReport.value = false;
    }
  } catch (err) {
    addLog(`✗ Report synthesis exception: ${err.message}`);
    isGeneratingReport.value = false;
  }
};

const handleInjectScenario = async () => {
  if (!injectContent.value.trim() || !props.simulationId) return;
  isInjecting.value = true;
  injectMessage.value = "";

  try {
    const res = await axios.post(`/api/simulation/${props.simulationId}/inject`, {
      content: injectContent.value.trim(),
      platform: injectPlatform.value,
    });

    if (res.data?.success) {
      injectMessage.value = "✓ Breaking scenario event injected into simulation stream!";
      addLog(`[LIVE INJECTION] ${injectContent.value.slice(0, 50)}...`);
      injectContent.value = "";
      setTimeout(() => {
        showInjectModal.value = false;
        injectMessage.value = "";
      }, 1500);
    } else {
      injectMessage.value = `✗ Injection failed: ${res.data?.error || "Unknown error"}`;
    }
  } catch (err) {
    injectMessage.value = `✗ Injection exception: ${err.response?.data?.error || err.message}`;
  } finally {
    isInjecting.value = false;
  }
};

watch(activeSubTab, (newTab) => {
  if (newTab === "metrics" && !metricsData.value && !loadingMetrics.value) {
    fetchMetrics();
  }
});

onMounted(() => {
  addLog("Step 3 Simulation Initialized");
  fetchExecutionContracts();
  if (props.simulationId) {
    doStartSimulation();
  }
});

onUnmounted(() => {
  stopWs();
});
</script>

<style scoped>
.simulation-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: var(--bg-color);
  font-family: var(--font-sans);
  overflow: hidden;
  color: var(--text-primary);
}

/* Control Bar */
.control-bar {
  background: var(--bg-color);
  padding: 16px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-color);
  z-index: 10;
}

.status-group {
  display: flex;
  gap: 16px;
}

.platform-status {
  padding: 12px 18px;
  background: var(--bg-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  position: relative;
  transition: all 0.2s ease;
}

.platform-status.twitter {
  border-left: 4px solid var(--accent-color);
}
.platform-status.reddit {
  border-left: 4px solid var(--accent-secondary);
}

.platform-status.active {
  background: #fffbeb;
  border-color: #fde68a;
}

.platform-status.completed {
  background: rgba(255, 255, 255, 0.03);
  color: var(--text-secondary);
  border-color: var(--border-color);
}

.actions-tooltip {
  position: absolute;
  top: 100%;
  left: 0;
  width: 100%;
  margin-top: 8px;
  padding: 12px;
  background: var(--surface-color);
  color: var(--bg-color);
  border-radius: var(--radius-md);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  opacity: 0;
  visibility: hidden;
  z-index: 100;
  pointer-events: none;
  transition: all 0.15s ease;
}

.platform-status:hover .actions-tooltip {
  opacity: 1;
  visibility: visible;
}

.tooltip-title {
  font-family: var(--font-sans);
  font-size: 9px;
  font-weight: 700;
  color: #38bdf8;
  text-transform: uppercase;
  margin-bottom: 8px;
}

.tooltip-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.tooltip-action {
  font-family: var(--font-mono);
  font-size: 8px;
  background: rgba(255, 255, 255, 0.1);
  padding: 2px 4px;
  border-radius: 2px;
}

.platform-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.platform-name {
  font-weight: 700;
  font-size: 11px;
}

.platform-stats {
  display: flex;
  gap: 16px;
}

.stat {
  display: flex;
  flex-direction: column;
}

.stat-label {
  font-size: 9px;
  font-weight: 600;
  opacity: 0.5;
  text-transform: uppercase;
}

.stat-value {
  font-size: 12px;
  font-weight: 700;
}

.final-action-btn {
  padding: 10px 20px;
  background: var(--surface-color);
  color: var(--bg-color);
  border: none;
  border-radius: var(--radius-sm);
  font-weight: 600;
  font-size: 12px;
  text-transform: uppercase;
  cursor: pointer;
  transition: background 0.2s ease;
}

.final-action-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
}

.final-action-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Contracts */
.contract-strip {
  display: flex;
  gap: 12px;
  padding: 12px 24px;
  background: rgba(255, 255, 255, 0.03);
  border-bottom: 1px solid var(--border-color);
}

.contract-card {
  flex: 1;
  padding: 10px 14px;
  background: var(--bg-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
}

.contract-label {
  font-family: var(--font-sans);
  font-size: 9px;
  font-weight: 600;
  opacity: 0.5;
  text-transform: uppercase;
}

.contract-value {
  font-weight: 700;
  font-size: 12px;
  text-transform: uppercase;
  margin: 2px 0;
}

.contract-meta {
  font-size: 9px;
  color: var(--text-secondary);
}

.contract-ok {
  background: var(--bg-color);
}

.contract-failed {
  border-color: #fca5a5;
  color: var(--accent-color);
}

/* Timeline */
.main-content-area {
  flex: 1;
  overflow-y: auto;
  background: var(--bg-color);
}

.timeline-header {
  padding: 12px 24px;
  border-bottom: 1px solid var(--border-color);
  position: sticky;
  top: 0;
  background: var(--bg-color);
  z-index: 5;
}

.timeline-stats {
  display: flex;
  justify-content: space-between;
  font-family: var(--font-sans);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.timeline-feed {
  padding: 24px;
  max-width: 800px;
  margin: 0 auto;
  position: relative;
}

.timeline-axis {
  position: absolute;
  left: 40px;
  top: 0;
  bottom: 0;
  width: 1px;
  background: var(--border-color);
}

.timeline-item-wrapper {
  display: flex;
  gap: 20px;
  margin-bottom: 24px;
  position: relative;
}

.timeline-marker {
  width: 32px;
  z-index: 2;
  display: flex;
  justify-content: center;
  padding-top: 8px;
}

.marker-dot {
  width: 10px;
  height: 10px;
  background: var(--bg-color);
  border: 2px solid var(--border-color);
  border-radius: 50%;
}

.twitter .marker-dot {
  background: var(--accent-color);
  border-color: var(--accent-color);
}
.reddit .marker-dot {
  background: var(--accent-secondary);
  border-color: var(--accent-secondary);
}

.timeline-card {
  flex: 1;
  background: var(--bg-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 20px;
  transition: box-shadow 0.2s ease;
}

.timeline-card:hover {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}

.twitter .timeline-card {
  border-left: 3px solid var(--accent-color);
}
.reddit .timeline-card {
  border-left: 3px solid var(--accent-secondary);
}

.timeline-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 8px;
}

.agent-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.avatar-placeholder {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 11px;
}

.agent-name {
  font-weight: 700;
  font-size: 12px;
}

.action-badge {
  font-family: var(--font-sans);
  font-size: 9px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 10px;
  text-transform: uppercase;
}

.badge-post {
  background: #fee2e2;
  color: var(--accent-color);
}
.badge-blue {
  background: #eff6ff;
  color: var(--accent-secondary);
}
.badge-red {
  background: #fee2e2;
  color: var(--accent-color);
}
.badge-yellow {
  background: #fffbeb;
  color: var(--accent-tertiary);
}
.badge-black {
  background: rgba(255, 255, 255, 0.03);
  color: var(--text-secondary);
}

.content-text {
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-primary);
}

.quoted-block {
  margin-top: 12px;
  padding: 12px;
  border: 1px dashed var(--border-color);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.03);
}

.quote-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  font-family: var(--font-sans);
  font-size: 10px;
  font-weight: 700;
  color: var(--text-secondary);
}

.repost-info,
.like-info,
.search-info,
.follow-info,
.vote-info,
.idle-info {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  font-weight: 700;
  text-transform: uppercase;
  font-size: 10px;
  color: var(--text-secondary);
}

.card-footer {
  margin-top: 16px;
  border-top: 1px solid var(--border-color);
  padding-top: 8px;
}

.time-tag {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--text-secondary);
  font-weight: 600;
}

/* Logs */
.system-logs {
  background: var(--surface-color);
  padding: 20px;
  color: var(--bg-color);
  min-height: 180px;
  display: flex;
  flex-direction: column;
}

.log-title {
  font-family: var(--font-sans);
  font-size: 11px;
  font-weight: 700;
  color: var(--accent-tertiary);
}

.log-content {
  margin-top: 10px;
  height: 100px;
  overflow-y: auto;
  font-family: var(--font-mono);
  font-size: 10px;
  flex-grow: 1;
}

/* Animations */
.timeline-item-enter-active {
  transition: all 0.5s ease;
}
.timeline-item-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.spinner-sm {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.2);
  border-top-color: var(--accent-tertiary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  100% {
    transform: rotate(360deg);
  }
}

.mono {
  font-family: var(--font-mono);
}

/* Subtabs Navigation */
.subtabs-nav {
  display: flex;
  gap: 8px;
}

.subtab-btn {
  background: transparent;
  border: 1px solid var(--border-color);
  padding: 4px 12px;
  border-radius: 4px;
  font-family: var(--font-sans);
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  cursor: pointer;
  transition: all 0.2s ease;
  color: var(--text-secondary);
}

.subtab-btn:hover {
  background: rgba(255, 255, 255, 0.03);
  color: var(--surface-color);
}

.subtab-btn.is-active {
  background: var(--surface-color);
  color: var(--bg-color);
  border-color: var(--surface-color);
}

/* Metrics Dashboard */
.metrics-dashboard {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.metrics-loading,
.metrics-error,
.metrics-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  border: 1px dashed var(--border-color);
  background: var(--bg-color);
  text-align: center;
  font-weight: 700;
  font-family: var(--font-sans);
  gap: 12px;
  text-transform: uppercase;
  border-radius: var(--radius-md);
}

.metrics-loading {
  border-style: solid;
}

.error-icon {
  font-size: 24px;
}

.error-msg {
  color: var(--accent-color);
}

.retry-btn {
  background: var(--surface-color);
  color: var(--bg-color);
  border: none;
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  font-family: var(--font-sans);
  font-weight: 600;
  cursor: pointer;
  text-transform: uppercase;
  transition: background 0.2s ease;
}

.retry-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

/* Dashboard Content */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
  margin-bottom: 32px;
}

.metric-card {
  background: var(--bg-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 20px;
  display: flex;
  flex-direction: column;
  position: relative;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02);
}

.metric-card.polarization {
  border-top: 4px solid var(--accent-color);
}

.metric-card.gini {
  border-top: 4px solid var(--accent-secondary);
}

.metric-card.echo-chamber {
  border-top: 4px solid var(--accent-tertiary);
}

.metric-label {
  font-family: var(--font-sans);
  font-size: 10px;
  font-weight: 700;
  opacity: 0.6;
  text-transform: uppercase;
  margin-bottom: 6px;
}

.metric-value-wrapper {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 2rem;
  font-weight: 700;
  line-height: 1;
}

.metric-badge {
  font-family: var(--font-sans);
  font-size: 9px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 4px;
  text-transform: uppercase;
}

.badge-green {
  background: #ecfdf5;
  color: #10b981;
}

.badge-yellow {
  background: #fffbeb;
  color: #d97706;
}

.badge-red {
  background: #fee2e2;
  color: var(--accent-color);
}

.metric-desc {
  font-size: 11px;
  line-height: 1.5;
  margin: 0 0 12px 0;
  color: var(--text-secondary);
  flex-grow: 1;
}

.gauge-bar {
  height: 6px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 3px;
  overflow: hidden;
}

.gauge-fill {
  height: 100%;
  transition: width 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

/* Dual Panel Layout */
.metrics-dual-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

@media (max-width: 900px) {
  .metrics-dual-layout {
    grid-template-columns: 1fr;
  }
}

.analytics-section {
  background: var(--bg-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 20px;
}

.analytics-section h3 {
  font-family: var(--font-sans);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 1px;
  margin: 0 0 16px 0;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 6px;
  color: var(--text-secondary);
}

.section-subtitle {
  font-size: 11px;
  opacity: 0.7;
  margin-top: -10px;
  margin-bottom: 16px;
  color: var(--text-secondary);
}

/* Distribution List */
.distribution-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dist-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.dist-meta {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
}

.dist-type {
  font-weight: 600;
  text-transform: uppercase;
}

.dist-count {
  font-weight: 700;
}

.dist-bar {
  height: 8px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
  overflow: hidden;
}

.dist-bar-fill {
  height: 100%;
  background: var(--surface-color);
  transition: width 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

/* Top Agents Table */
.top-agents-table {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.table-header {
  display: flex;
  background: rgba(255, 255, 255, 0.03);
  color: var(--text-secondary);
  font-family: var(--font-sans);
  font-size: 10px;
  font-weight: 700;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-color);
}

.table-row {
  display: flex;
  border-bottom: 1px solid var(--border-color);
  padding: 8px 12px;
  align-items: center;
}

.table-row:last-child {
  border-bottom: none;
}

.col-agent {
  flex: 1;
  font-weight: 600;
  font-size: 11px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.col-actions {
  font-weight: 700;
  font-size: 11px;
  width: 80px;
  text-align: right;
}

.agent-avatar {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-secondary);
  font-weight: 700;
  font-size: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  text-transform: uppercase;
}

/* Cascades */
.no-cascades {
  padding: 24px 0;
  text-align: center;
  font-family: var(--font-sans);
  font-size: 11px;
  opacity: 0.6;
}

.cascade-cards-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.cascade-post-card {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 12px;
  background: var(--bg-color);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02);
}

.cascade-post-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  font-size: 11px;
}

.cascade-rank {
  font-weight: 700;
  color: var(--accent-color);
}

.cascade-author {
  font-weight: 700;
}

.cascade-platform-badge {
  font-family: var(--font-sans);
  font-size: 8px;
  font-weight: 700;
  padding: 1px 4px;
  border-radius: 2px;
}

.cascade-platform-badge.twitter {
  background: #fee2e2;
  color: var(--accent-color);
}

.cascade-platform-badge.reddit {
  background: #eff6ff;
  color: var(--accent-secondary);
}

.cascade-post-content {
  font-size: 11px;
  line-height: 1.4;
  margin: 0 0 8px 0;
  color: var(--text-secondary);
  font-style: italic;
}

.cascade-post-stats {
  display: flex;
  gap: 12px;
  font-family: var(--font-sans);
  font-size: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  padding-top: 6px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 2px;
}

.stat-icon {
  font-size: 10px;
}

.stat-num {
  font-weight: 600;
}

.stat-item.total {
  margin-left: auto;
}

.stat-label {
  font-weight: 600;
  margin-right: 2px;
}

.stat-num.highlighted {
  background: #fffbeb;
  padding: 0 4px;
  border: 1px solid #fde68a;
  border-radius: 2px;
  font-weight: 700;
}

.truncate-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
