<script setup lang="ts">
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import {
  PhCheck,
  PhCheckCircle,
  PhCopySimple,
  PhInfo,
  PhWarning,
  PhWarningCircle,
  PhWarningOctagon,
} from '@phosphor-icons/vue';

import { DecoratedDnsTableRow, InlineIssue, RecordTab } from '../types';
import { hasCopyableValue } from '../utils';

const props = defineProps<{
  rows: DecoratedDnsTableRow[];
  unanchoredValidationIssues: InlineIssue[];
  showRecordStatus?: boolean;
  activeTab?: RecordTab;
}>();

const { t } = useI18n();

const copiedCellKey = ref<string | null>(null);
let copiedResetTimer: ReturnType<typeof setTimeout> | undefined;

const filteredRows = computed(() => {
  if (props.showRecordStatus) {
    return props.rows.filter((row) => {
      if (props.activeTab === RecordTab.CONFLICTING) {
        return row.status === 'warning' || row.status === 'critical';
      }

      return true;
    });
  }

  return props.rows;
});

const copyCellValue = async (cellKey: string, value: string) => {
  try {
    await navigator.clipboard.writeText(value);
    copiedCellKey.value = cellKey;
    clearTimeout(copiedResetTimer);
    copiedResetTimer = setTimeout(() => {
      copiedCellKey.value = null;
    }, 1500);
  } catch (error) {
    console.error(error);
  }
};
</script>

<template>
  <div class="records-table-wrapper" :class="{ 'records-table-wrapper-with-status': showRecordStatus }">
    <div class="records-table">
      <div class="records-table-header">
        <p v-if="showRecordStatus" class="records-cell-status" aria-hidden="true"></p>
        <p>{{ t('views.mail.sections.customDomains.recordsTableHeaderType') }}</p>
        <p>{{ t('views.mail.sections.customDomains.recordsTableHeaderNameHost') }}</p>
        <p>{{ t('views.mail.sections.customDomains.recordsTableHeaderValueData') }}</p>
        <p>{{ t('views.mail.sections.customDomains.recordsTableHeaderPriority') }}</p>
        <p class="records-cell-action" aria-hidden="true"></p>
      </div>
      <div
        class="records-table-row"
        :class="{ 'record-warning': row.status === 'warning' || row.status === 'critical' }"
        v-for="row in filteredRows"
        :key="row.key"
      >
        <div v-if="showRecordStatus" class="records-cell records-cell-status">
          <ph-check-circle
            v-if="row.status === 'success'"
            size="16"
            weight="duotone"
            class="status-icon status-icon-success"
            aria-hidden="true"
          />
          <ph-warning v-else size="16" weight="duotone" class="status-icon status-icon-warning" aria-hidden="true" />
        </div>

        <p class="records-cell">{{ row.record.type }}</p>

        <div class="records-cell records-cell-copyable">
          <span>{{ row.record.name }}</span>
          <button
            v-if="hasCopyableValue(row.record.name)"
            type="button"
            class="copy-button"
            :aria-label="t('views.mail.sections.customDomains.copyValue')"
            @click="copyCellValue(`${row.key}-name`, row.record.name)"
          >
            <ph-check v-if="copiedCellKey === `${row.key}-name`" size="14" />
            <ph-copy-simple v-else size="14" />
          </button>
        </div>

        <div class="records-cell records-cell-copyable">
          <span>{{ row.record.content }}</span>
          <button
            v-if="hasCopyableValue(row.record.content)"
            type="button"
            class="copy-button"
            :aria-label="t('views.mail.sections.customDomains.copyValue')"
            @click="copyCellValue(`${row.key}-content`, row.record.content)"
          >
            <ph-check v-if="copiedCellKey === `${row.key}-content`" size="14" />
            <ph-copy-simple v-else size="14" />
          </button>
        </div>

        <div class="records-cell records-cell-copyable">
          <span>{{ row.record.priority || '-' }}</span>
          <button
            v-if="hasCopyableValue(row.record.priority)"
            type="button"
            class="copy-button"
            :aria-label="t('views.mail.sections.customDomains.copyValue')"
            @click="copyCellValue(`${row.key}-priority`, row.record.priority || '')"
          >
            <ph-check v-if="copiedCellKey === `${row.key}-priority`" size="16" />
            <ph-copy-simple v-else size="16" />
          </button>
        </div>

        <div class="records-cell records-cell-action">
          <template v-if="row.action">
            <span class="action-badge">
              {{ t(`views.mail.sections.customDomains.recordAction.${row.action}`) }}
            </span>
            <ph-info
              size="16"
              class="action-info-icon"
              :title="row.issues.map((issue) => issue.text).join('\n')"
            />
          </template>
        </div>
      </div>

      <div class="records-table-footer" v-if="unanchoredValidationIssues.length > 0">
        <p
          v-for="issue in unanchoredValidationIssues"
          :key="issue.key"
          class="inline-issue"
          :class="`inline-issue-${issue.severity}`"
        >
          <ph-warning-octagon v-if="issue.severity === 'critical'" size="18" weight="fill" aria-hidden="true" />
          <ph-warning-circle v-else size="18" weight="fill" aria-hidden="true" />
          <span>{{ issue.text }}</span>
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.records-table-wrapper {
  --records-grid-columns: max-content minmax(150px, 1fr) minmax(200px, 1fr) max-content max-content;

  overflow-x: auto;
  margin-block-end: 1.5rem;

  &.records-table-wrapper-with-status {
    --records-grid-columns: 3rem max-content minmax(150px, 1fr) minmax(200px, 1fr) max-content max-content;
  }
}

.records-table {
  display: grid;
  grid-template-columns: var(--records-grid-columns);
  min-width: max-content;
}

.records-table-header,
.records-table-row {
  display: grid;
  grid-column: 1 / -1;
  grid-template-columns: subgrid;
  align-items: center;
}

.records-table-header {
  border-block-end: 1px solid var(--colour-neutral-border);

  p {
    padding: 1rem;
    text-transform: uppercase;
    font-weight: 600;
    font-size: 0.8125rem;
    letter-spacing: 0.39px;
  }
}

.records-table-row {
  border-block-end: 0.0625rem solid var(--colour-neutral-border);

  &.record-warning {
    border-block-end-color: var(--colour-warning-default);
    background-color: var(--colour-warning-soft);
  }
}

.records-cell {
  padding: 1rem;
  margin: 0;
  font-size: 0.75rem;
  word-break: break-word;
}

.records-cell-status {
  display: flex;
  align-items: center;
  justify-content: center;
  padding-inline: 0;
}

.status-icon {
  flex: 0 0 auto;
}

.status-icon-success {
  color: var(--colour-success-pressed);
}

.status-icon-warning {
  color: var(--colour-ti-warning);
}

.records-cell-copyable {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;

  span {
    word-break: break-word;
  }
}

.copy-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  padding: 0.25rem;
  border: none;
  background: none;
  color: var(--colour-ti-secondary);
  cursor: pointer;

  &:hover {
    color: var(--colour-primary-hover);
  }

  &:active {
    color: var(--colour-primary-pressed);
  }
}

.records-cell-action {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.action-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.75rem;
  border: 1px solid currentColor;
  border-radius: 300px;
  font-size: 0.6875rem;
  margin: 0 auto;
  color: var(--colour-ti-warning);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.39px;
  white-space: nowrap;
}

.action-info-icon {
  flex: 0 0 auto;
  color: var(--colour-ti-warning);
}

.records-table-footer {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0 1rem 1rem;
  grid-column: 1 / -1;
  border-block-start: 1px solid var(--colour-neutral-border);
  padding-block-start: 1rem;
}

.inline-issue {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.35;

  svg {
    flex: 0 0 auto;
    margin-block-start: 0.0625rem;
  }
}

.inline-issue-warning {
  color: var(--colour-ti-warning);
}

@media (min-width: 768px) {
  .records-table-wrapper {
    overflow-x: visible;
  }

  .records-table {
    min-width: auto;
  }
}
</style>
