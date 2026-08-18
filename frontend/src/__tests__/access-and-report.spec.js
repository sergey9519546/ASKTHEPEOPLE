import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { beforeEach, describe, expect, it } from 'vitest';

import service from '../api/index.js';
import {
  accessMessage,
  accessRequired,
  clearAccessKey,
  getAccessKey,
  saveAccessKey,
} from '../composables/useAccessKey.js';
import {
  normalizeAgentLogEntry,
  normalizeLogPage,
  normalizeReportEvidence,
  outlineSectionTitles,
} from '../api/report.js';

function requestHandler() {
  return service.interceptors.request.handlers.find(
    (handler) => handler && typeof handler.fulfilled === 'function',
  ).fulfilled;
}

function responseErrorHandler() {
  return service.interceptors.response.handlers.find(
    (handler) => handler && typeof handler.rejected === 'function',
  ).rejected;
}

describe('runtime deployment access key', () => {
  beforeEach(() => {
    sessionStorage.clear();
    accessRequired.value = false;
    accessMessage.value = '';
  });

  it('uses session storage only and can be explicitly forgotten', () => {
    expect(getAccessKey()).toBe('');

    expect(saveAccessKey('  tab-only-key  ')).toBe(true);
    expect(getAccessKey()).toBe('tab-only-key');

    const source = readFileSync(
      resolve('src/composables/useAccessKey.js'),
      'utf8',
    );
    expect(source).not.toContain('localStorage');

    clearAccessKey();
    expect(getAccessKey()).toBe('');
  });

  it('attaches the runtime key as a bearer credential', () => {
    saveAccessKey('runtime-secret');
    const config = requestHandler()({ headers: {} });
    expect(config.headers.Authorization).toBe('Bearer runtime-secret');
  });

  it('turns a 401 into a clean access-gate state', async () => {
    const rejected = responseErrorHandler();

    await expect(
      rejected({ response: { status: 401 }, message: 'Unauthorized' }),
    ).rejects.toMatchObject({
      code: 'ACCESS_REQUIRED',
      status: 401,
    });
    expect(accessRequired.value).toBe(true);
    expect(accessMessage.value).toContain('access key');
  });
});

describe('report DTO normalization and safe rendering', () => {
  it('normalizes paged logs and nested event details', () => {
    const page = normalizeLogPage({
      data: {
        from_line: 8,
        total_lines: 12,
        has_more: true,
        logs: [
          {
            action: 'llm_response',
            details: {
              tool_name: 'quick_search',
              parameters: { query: 'transit access' },
              content: 'A bounded generated result',
              has_final_answer: false,
            },
          },
        ],
      },
    });
    const entry = normalizeAgentLogEntry(page.logs[0]);

    expect(page).toMatchObject({
      fromLine: 8,
      nextFromLine: 9,
      totalLines: 12,
      hasMore: true,
    });
    expect(entry).toMatchObject({
      tool_name: 'quick_search',
      params: { query: 'transit access' },
      content: 'A bounded generated result',
      final_answer: false,
      thinking: true,
    });
  });

  it('accepts both string and object report outlines', () => {
    expect(
      outlineSectionTitles({
        sections: ['Context', { title: 'Possible paths' }, { title: '' }],
      }),
    ).toEqual(['Context', 'Possible paths']);
  });

  it('normalizes nested within-run records without exposing claim semantics', () => {
    expect(
      normalizeReportEvidence({
        data: {
          report_id: 'report-1',
          evidence: [
            {
              trace_id: 'section_1_trace_2',
              source_type: 'round_summary',
              excerpt: '{"generated_actions": 14}',
              evidence_class: 'generated_observation',
              human_respondents: 0,
              interpretation:
                'Generated within this simulation run; not observed human behavior.',
            },
          ],
        },
      }),
    ).toEqual([
      expect.objectContaining({
        trace_id: 'section_1_trace_2',
        source_type: 'round_summary',
        excerpt: '{"generated_actions": 14}',
        evidence_class: 'generated_observation',
        human_respondents: 0,
        interpretation:
          'Generated within this simulation run; not observed human behavior.',
      }),
    ]);
  });

  it('normalizes legacy claim identifiers into trace identifiers', () => {
    const [record] = normalizeReportEvidence({
      data: {
        evidence: [
          {
            claim_id: 'section_1_claim_4',
            source_type: 'post',
            excerpt: 'Generated text',
          },
        ],
      },
    });

    expect(record.trace_id).toBe('section_1_trace_4');
    expect(record).not.toHaveProperty('claim_id');
  });

  it('keeps the report safe and defaults to the public decision brief', () => {
    const step4 = readFileSync(
      resolve('src/components/Step4Report.vue'),
      'utf8',
    );
    const step5 = readFileSync(
      resolve('src/components/Step5Interaction.vue'),
      'utf8',
    );

    expect(step4).not.toContain('v-html');
    expect(step5).not.toContain('v-html');
    expect(step4).toContain('Keyword-related examples from this run');
    expect(step4).toContain('0 human respondents');
    expect(step4).toContain('Not a forecast');
    expect(step4).toContain('Limits of this run');
    expect(step4).toContain('Generation details and event records');
    expect(step4).toContain('class="generation-disclosure"');
    expect(step4).not.toContain('activeTab');
    expect(step4).not.toContain('Source evidence');
    expect(step4).toContain('fetchReportEvidence');
    expect(step4).toContain('EVIDENCE_MAX_ATTEMPTS');
  });

  it('keeps the selected report mode exclusive and full-height on mobile', () => {
    const reportView = readFileSync(resolve('src/views/ReportView.vue'), 'utf8');

    expect(reportView).toContain(':aria-pressed="viewMode === m"');
    expect(reportView).toContain('split: "Compare"');
    expect(reportView).toContain(':class="`mode-${viewMode}`"');
    expect(reportView).toContain(
      '.workbench-viewport.mode-workbench .panel-container.left',
    );
    expect(reportView).toContain('display: none !important;');
    expect(reportView).toContain('height: calc(100dvh - 11rem) !important;');
    expect(reportView).toContain('Review the run');
    expect(reportView).toContain(
      'Review findings, related records, and limits',
    );
    expect(reportView).not.toContain('Review evidence');
  });
});

describe('product safety and deployment UI contracts', () => {
  it('requires exploratory-use acknowledgement and sends the policy fields', () => {
    const home = readFileSync(resolve('src/views/Home.vue'), 'utf8');
    const workflow = readFileSync(resolve('src/views/MainView.vue'), 'utf8');

    expect(home).toContain('v-model="usePolicyAcknowledged"');
    expect(home).toContain('required');
    expect(home).toContain('maxlength="120"');
    expect(home).toContain('maxlength="4000"');
    expect(home).toContain('maxlength="8000"');
    expect(workflow).toContain('"use_policy_acknowledged"');
    expect(workflow).toContain('"intended_use", "scenario_planning"');
  });

  it('ships no runtime Tailwind loader and gates model editing by deployment capability', () => {
    const document = readFileSync(resolve('index.html'), 'utf8');
    const settings = readFileSync(
      resolve('src/components/SettingsModal.vue'),
      'utf8',
    );

    expect(document).not.toContain('cdn.tailwindcss.com');
    expect(settings).toContain('runtime_settings_enabled');
    expect(settings).toContain('v-else-if="!runtimeSettingsEnabled"');
  });

  it('does not expose an automatic retry helper for mutating requests', () => {
    const apiIndex = readFileSync(resolve('src/api/index.js'), 'utf8');
    const graph = readFileSync(resolve('src/api/graph.js'), 'utf8');
    const simulation = readFileSync(resolve('src/api/simulation.js'), 'utf8');
    const report = readFileSync(resolve('src/api/report.js'), 'utf8');

    expect(`${apiIndex}${graph}${simulation}${report}`).not.toContain(
      'requestWithRetry',
    );
  });
});
