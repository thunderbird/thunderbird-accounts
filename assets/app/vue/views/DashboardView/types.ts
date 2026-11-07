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

/** Metadata of one Stalwart app password; the secret is only ever returned once, on creation. */
export interface AppPasswordSummary {
  id: string;
  name: string;
  createdAt: string | null;
}

export interface AppPasswordApiResponse {
  success: boolean;
  error?: string;
  code?: string;
  /** HTTP status of the response, so callers can tell "already gone" (404) apart from real failures. */
  status: number;
}

export interface AppPasswordListResponse extends AppPasswordApiResponse {
  username?: string;
  appPasswords?: AppPasswordSummary[];
}

export interface AppPasswordCreateResponse extends AppPasswordApiResponse {
  appPassword?: AppPasswordSummary;
  secret?: string;
  username?: string;
}

export interface AppPasswordRevokeResponse extends AppPasswordApiResponse {
  id?: string;
}

/** One-time handoff state shown right after a password is generated. */
export interface GeneratedAppPassword {
  id: string;
  name: string;
  secret: string;
  username: string;
}
