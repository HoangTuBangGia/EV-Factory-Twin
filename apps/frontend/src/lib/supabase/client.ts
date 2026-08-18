import { createBrowserClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";
import { getSupabaseConfig } from "@/lib/env";

let browserClient: SupabaseClient | null = null;

export function getSupabaseBrowserClient() {
  const config = getSupabaseConfig();
  if (!config) return null;
  browserClient ??= createBrowserClient(config.url, config.publishableKey);
  return browserClient;
}
