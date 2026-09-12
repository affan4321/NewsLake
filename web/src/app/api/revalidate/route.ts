import { revalidatePath } from "next/cache";
import { NextRequest, NextResponse } from "next/server";

/*
 * Called by the Airflow DAG's last task right after a pipeline run finishes successfully.
 * The homepage is cached for up to an hour (`revalidate = 3600` in page.tsx) so normal
 * traffic doesn't hit Postgres on every request -- fine for the daily schedule, but it
 * means a manual/off-schedule run wouldn't show up on the site until that cache expired.
 * This forces an immediate refresh instead of waiting.
 */
export async function POST(req: NextRequest) {
  const secret = process.env.REVALIDATE_SECRET;
  const provided = req.headers.get("authorization")?.replace(/^Bearer\s+/i, "");

  if (!secret || provided !== secret) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  revalidatePath("/");
  return NextResponse.json({ revalidated: true, revalidatedAt: new Date().toISOString() });
}
