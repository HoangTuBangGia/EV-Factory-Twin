import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { getSupabaseConfig } from "@/lib/env";
import { appRoleSchema, type AppRole } from "@/schemas/auth";

export async function refreshSupabaseSession(request: NextRequest, includeRole = false) {
  let response = NextResponse.next({ request });
  const config = getSupabaseConfig();
  if (!config) return { response, user: null, role: null };

  const supabase = createServerClient(config.url, config.publishableKey, {
    cookies: {
      getAll: () => request.cookies.getAll(),
      setAll: (cookiesToSet) => {
        for (const { name, value } of cookiesToSet) request.cookies.set(name, value);
        response = NextResponse.next({ request });
        for (const { name, value, options } of cookiesToSet) {
          response.cookies.set(name, value, options);
        }
      },
    },
  });

  const { data: { user } } = await supabase.auth.getUser();
  let role: AppRole | null = null;
  if (includeRole && user) {
    const { data: profile } = await supabase
      .from("profiles")
      .select("role,is_active")
      .eq("id", user.id)
      .maybeSingle();
    const parsedRole = appRoleSchema.safeParse(profile?.role);
    if (profile?.is_active === true && parsedRole.success) role = parsedRole.data;
  }
  return { response, user, role };
}
