/// <reference types="vite/client" />

import { CustomDomain } from '@/views/MailView/sections/CustomDomainsSection/types';
import { ServerMessage } from '@/types';

declare global {
  interface Window {
    _page: {
      pageId?: string;
      isAuthenticated?: boolean;
      isAwaitingPaymentVerification?: boolean;
      hasActiveSubscription?: boolean;
      userEmail?: string;
      userFullName?: string;
      userDisplayName?: string;
      connectionInfo?: {
        'SMTP': {'HOST': string, 'PORT': number, 'TLS': boolean},
        'IMAP': {'HOST': string, 'PORT': number, 'TLS': boolean},
        'JMAP': {'HOST': string, 'PORT': number, 'TLS': boolean},
      };
      formError?: string | null;
      csrfToken?: string;
      paddleToken?: string;
      paddleEnvironment?: string;
      paddlePlanInfo?: string[];
      successRedirect?: string;
      signedUserId?: string;
      appPasswords?: string[];
      cancelRedirect?: string;
      allowedDomains?: string[];
      customDomains?: CustomDomain[];
      emailAddresses?: string[];
      maxCustomDomains?: number;
      maxEmailAliases?: number;
      tbProAppointmentUrl?: string;
      tbProSendUrl?: string;
      currentView?: Record<string, any>;
      serverMessages: ServerMessage[];
    };
  }
}

export {};
