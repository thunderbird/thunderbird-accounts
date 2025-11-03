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
}
