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

export interface SubscriptionFeatures {
  mailStorage: string | null;
  sendStorage: string | null;
  emailAddresses: string | null;
  domains: string | null;
}
  
export interface SubscriptionData {
  name: string;
  price: string;
  currency: string;
  period: string;
  description: string;
  features: SubscriptionFeatures;
  autoRenewal: string | null;
  usedQuota: string;
}

export interface SendStorageData {
  used: number;
  total: number;
}
