export type EnvironmentRecord = {
  id: number;
  name: string;
  base_url?: string;
  description?: string;
  created_at?: string;
  updated_at?: string;
};

export type EnvironmentPayload = {
  name: string;
  base_url: string;
  description?: string;
};
