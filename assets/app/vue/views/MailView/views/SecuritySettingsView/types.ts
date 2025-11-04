export interface ActiveSession {
  id: string;
  device_info: Record<string, any> | null;
  ip_address: string;
  last_access: number;
}
