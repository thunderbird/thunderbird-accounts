/// <reference types="vite/client" />

declare global {
  interface Window {
    _page: {
      pageId?: string;
      isAuthenticated?: boolean;
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
      customDomains?: { name: string, status: string, emailsCount?: number }[];
      currentView?: Record<string, any>;
    };
  }
}

export {};
