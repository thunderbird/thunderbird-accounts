import { appendFile } from 'node:fs/promises';

import type { FullConfig, Reporter, Suite, TestCase } from '@playwright/test/reporter';

type SummaryStatus = 'Passed' | 'Failed' | 'Skipped';

const statusIcon: Record<SummaryStatus, string> = {
  Passed: '✅',
  Failed: '❌',
  Skipped: '⏭️',
};

function summaryStatus(test: TestCase): SummaryStatus {
  switch (test.outcome()) {
    case 'expected':
    case 'flaky':
      return 'Passed';
    case 'skipped':
      return 'Skipped';
    case 'unexpected':
      return 'Failed';
  }
}

function testName(test: TestCase): string {
  const describeTitles: string[] = [];
  let suite: Suite | undefined = test.parent;

  while (suite) {
    if (suite.type === 'describe' && suite.title) {
      describeTitles.unshift(suite.title);
    }
    suite = suite.parent;
  }

  return [...describeTitles, test.title].join(' › ');
}

function escapeHtml(value: string): string {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
    .replaceAll('|', '&#124;')
    .replaceAll(/\s+/g, ' ')
    .trim();
}

export default class GitHubSummaryReporter implements Reporter {
  private tests: TestCase[] = [];

  onBegin(_config: FullConfig, suite: Suite): void {
    this.tests = suite.allTests();
  }

  async onEnd(): Promise<void> {
    const tests = this.tests.map((test) => ({
      name: testName(test),
      status: summaryStatus(test),
    }));
    const counts = tests.reduce(
      (totals, test) => {
        totals[test.status] += 1;
        return totals;
      },
      { Passed: 0, Failed: 0, Skipped: 0 }
    );
    const summaryPath = process.env.GITHUB_STEP_SUMMARY;
    if (!summaryPath) {
      return;
    }

    const rows = tests.map(
      ({ name, status }) => `| ${statusIcon[status]} ${status} | <code>${escapeHtml(name)}</code> |`
    );
    const summary = [
      '## E2E Test Results',
      '',
      `**${counts.Passed} passed · ${counts.Failed} failed · ${counts.Skipped} skipped**`,
      '',
      '| Status | Test |',
      '| --- | --- |',
      ...rows,
      '',
    ].join('\n');

    await appendFile(summaryPath, summary);
  }

  // This reporter writes only to the GitHub Actions summary. The separately
  // configured dot reporter owns the existing terminal output.
  printsToStdio(): boolean {
    return false;
  }
}
