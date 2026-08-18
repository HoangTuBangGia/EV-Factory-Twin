export const env = {
  dataSource: process.env.NEXT_PUBLIC_DATA_SOURCE ?? "mock",
  apiUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  wsUrl: process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/factory",
  supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL,
  supabasePublishableKey: process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY,
};

export const usesMockData = env.dataSource !== "api";

export function getSupabaseConfig() {
  if (!env.supabaseUrl || !env.supabasePublishableKey) return null;
  return {
    url: env.supabaseUrl,
    publishableKey: env.supabasePublishableKey,
  };
}
