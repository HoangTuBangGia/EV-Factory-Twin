import { NextResponse, type NextRequest } from "next/server";
import { refreshSupabaseSession } from "@/lib/supabase/middleware";

function copyCookies(source: NextResponse, target: NextResponse) {
  for (const cookie of source.cookies.getAll()) target.cookies.set(cookie);
  return target;
}

export async function middleware(request: NextRequest) {
  const { response, user } = await refreshSupabaseSession(request, false);
  const pathname = request.nextUrl.pathname;
  const isPublic = pathname === "/homepage" || pathname === "/login";

  if (!user && pathname === "/") {
    const homepageUrl = request.nextUrl.clone();
    homepageUrl.pathname = "/homepage";
    homepageUrl.search = "";
    return copyCookies(response, NextResponse.redirect(homepageUrl));
  }

  if (!user && !isPublic) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = "/login";
    loginUrl.search = "";
    loginUrl.searchParams.set(
      "returnTo",
      `${request.nextUrl.pathname}${request.nextUrl.search}`,
    );
    return copyCookies(response, NextResponse.redirect(loginUrl));
  }

  response.headers.set("Cache-Control", "private, no-store");
  return response;
}

export const config = {
  matcher: [
    "/((?!scene-probe|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
