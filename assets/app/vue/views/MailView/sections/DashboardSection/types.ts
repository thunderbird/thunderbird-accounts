import type { Component } from 'vue';

export interface SegmentedControlTab {
  id: string;
  label: string;
  icon?: Component;
}

export enum SETUP_TABS {
  DESKTOP = 'desktop',
  MOBILE = 'mobile',
  OTHER = 'other',
}
