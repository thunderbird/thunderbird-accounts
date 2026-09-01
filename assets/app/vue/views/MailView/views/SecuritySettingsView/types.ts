export interface ActiveSession {
  id: string;
  device_info: {
    device?: string | null;
    os?: string | null;
    os_version?: string | null;
    browser?: string | null;
    app?: string | null;
    is_mobile?: boolean | null;
  } | null;
  ip_address: string;
  location?: {
    city?: string | null;
    state?: string | null;
    country_code?: string | null;
    continent?: string | null;
  } | null;
  last_access: number;
  is_current?: boolean;
}

export interface ConnectedApp {
  client_id: string;
  session_id?: string | null;
  app_name: string;
  ip_address?: string | null;
  location?: {
    city?: string | null;
    state?: string | null;
    country_code?: string | null;
    continent?: string | null;
  } | null;
  last_access?: number | null;
}

export interface DisplayConnectedApp {
  id: string;
  clientId: string;
  label: string;
  ipAddress: string;
  location: string;
  lastAccess: string;
}
