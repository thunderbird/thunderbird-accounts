export interface ActiveSession {
  id: string;
  device_info: {
    device?: string | null;
    os?: string | null;
    os_version?: string | null;
    browser?: string | null;
    is_mobile?: boolean | null;
  } | null;
  ip_address: string;
  last_access: number;
  is_current?: boolean;
}
