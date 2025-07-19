import { NextRequest, NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  try {
    const filePath = path.join("/app/av_output", ...params.path);

    // Check if file exists
    try {
      await fs.access(filePath);
    } catch {
      return NextResponse.json({ error: "File not found" }, { status: 404 });
    }

    // Read the file
    const fileBuffer = await fs.readFile(filePath);

    // Determine content type based on file extension
    const ext = path.extname(filePath).toLowerCase();
    let contentType = "application/octet-stream";

    if (ext === ".mp4") {
      contentType = "video/mp4";
    } else if (ext === ".webm") {
      contentType = "video/webm";
    } else if (ext === ".ogg") {
      contentType = "video/ogg";
    } else if (ext === ".mp3") {
      contentType = "audio/mpeg";
    } else if (ext === ".wav") {
      contentType = "audio/wav";
    }

    // Return the file with appropriate headers
    return new NextResponse(fileBuffer, {
      headers: {
        "Content-Type": contentType,
        "Content-Length": fileBuffer.length.toString(),
        "Cache-Control": "public, max-age=3600", // Cache for 1 hour
      },
    });
  } catch (error) {
    console.error("Error serving file:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
