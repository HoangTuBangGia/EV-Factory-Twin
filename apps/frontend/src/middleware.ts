import { NextResponse, type NextRequest } from "next/server";
import { refreshSupabaseSession } from "@/lib/supabase/middleware";

function copyCookies(source: NextResponse, target: NextResponse) {
  for (const cookie of source.cookies.getAll()) target.cookies.set(cookie);
  return target;
}

export async function middleware(request: NextRequest) {
  const isAdminRoute = request.nextUrl.pathname === "/admin"
    || request.nextUrl.pathname.startsWith("/admin/");
  const { response, user, role } = await refreshSupabaseSession(request, isAdminRoute);
  const isLogin = request.nextUrl.pathname === "/login";

  if (!user && !isLogin) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = "/login";
    loginUrl.search = "";
    loginUrl.searchParams.set(
      "returnTo",
      `${request.nextUrl.pathname}${request.nextUrl.search}`,
    );
    return copyCookies(response, NextResponse.redirect(loginUrl));
  }

  if (user && isAdminRoute && role !== "ADMIN") {
    const forbiddenUrl = request.nextUrl.clone();
    forbiddenUrl.pathname = "/forbidden";
    forbiddenUrl.search = "";
    return copyCookies(response, NextResponse.redirect(forbiddenUrl));
  }

  response.headers.set("Cache-Control", "private, no-store");
  return response;
}

export const config = {
  matcher: [
    "/((?!scene-probe|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
