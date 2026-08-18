<script setup lang="ts">
type SecurityAccessRecord = {
  id: string;
  label: string;
  ipAddress: string;
  location: string;
  lastAccess: string;
  isCurrent?: boolean;
};

type ColumnLabels = {
  primary: string;
  ipAddress: string;
  location: string;
  lastAccess: string;
  actions: string;
};

defineProps<{
  records: SecurityAccessRecord[];
  columnLabels: ColumnLabels;
  attribution: string;
}>();

defineSlots<{
  action(props: { record: SecurityAccessRecord }): unknown;
}>();
</script>

<template>
  <div class="table-wrapper">
    <table>
      <thead>
        <tr>
          <th scope="col">{{ columnLabels.primary }}</th>
          <th scope="col">{{ columnLabels.ipAddress }}</th>
          <th scope="col">{{ columnLabels.location }}</th>
          <th scope="col">{{ columnLabels.lastAccess }}</th>
          <th scope="col">{{ columnLabels.actions }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="record in records" :key="record.id">
          <td>{{ record.label }}</td>
          <td>{{ record.ipAddress }}</td>
          <td>{{ record.location }}</td>
          <td>{{ record.lastAccess }}</td>
          <td class="action-cell">
            <slot name="action" :record="record" />
          </td>
        </tr>
      </tbody>
    </table>
  </div>
  <p class="location-attribution">
    <a href="https://db-ip.com" rel="noopener noreferrer" target="_blank">
      {{ attribution }}
    </a>
  </p>
</template>

<style scoped>
.table-wrapper {
  overflow-x: auto;
  margin-block-end: 1rem;
  color: var(--colour-ti-secondary);
}

table {
  width: 100%;
  min-width: 700px;
  border-collapse: collapse;
  table-layout: fixed;
}

thead {
  border-block-end: solid 1px var(--surface-border-intense);
}

th,
td {
  box-sizing: border-box;
  padding: 1rem;
  text-align: left;
}

th {
  height: 3rem;
  color: var(--colour-ti-secondary);
  font-size: 0.8125rem;
  font-weight: 600;
  letter-spacing: 0.39px;
  text-transform: uppercase;
}

td {
  background-color: var(--surface-lower);
  font-size: 0.75rem;
  overflow-wrap: anywhere;
  vertical-align: middle;
}

.action-cell {
  white-space: nowrap;
}

.location-attribution {
  font-size: 0.6875rem;
  line-height: 1.3;
  margin-block-start: -0.5rem;
  margin-block-end: 1rem;

  a {
    color: var(--colour-ti-muted);
  }
}

:deep(button.base.link.filled) {
  color: var(--colour-ti-muted);
  font-size: 0.75rem;
  padding-inline: 0;
}

@media (max-width: 767px) {
  th,
  td {
    padding-inline: 0.75rem;
  }
}
</style>
