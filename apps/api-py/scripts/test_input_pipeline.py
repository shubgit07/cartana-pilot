"""Local Dry-Run Tester for Cartana Input System.

Run this script to test PDF/Text Requirement Parsing + 1,000-5,000 line Git Diff Noise Filtering
and Hunk Compression 100% in-memory locally, WITHOUT writing any data to Neon DB or Qdrant Cloud.

Usage:
    python -m scripts.test_input_pipeline
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.api.services.input_service import dry_run_pipeline_test

SAMPLE_REQUIREMENT_MD = """
# Feature: Offline Song Download & Streaming

## Functional Requirements
- R1: Add a prominent "Download" button on the song details view.
- R2: Only authenticated users with an active "Premium" tier are allowed to download songs.
- R3: Downloaded audio files must be stored in local encrypted cache for offline playback.
- R4: Show a success toast message when download finishes and update button state to "Downloaded".

## Non-Functional Constraints
- C1: Downloading must not impair or introduce stutter to active audio streaming playback.
- C2: Handle offline network drops gracefully with an automatic resume prompt.
"""

SAMPLE_LARGE_DIFF = """
diff --git a/pnpm-lock.yaml b/pnpm-lock.yaml
index 123456..789101 100644
--- a/pnpm-lock.yaml
+++ b/pnpm-lock.yaml
@@ -1,5 +1,5 @@
 lockfileVersion: '6.0'
-dependencies: react@18.2.0
+dependencies: react@18.3.1

diff --git a/dist/bundle.min.js b/dist/bundle.min.js
index abcdef..ghijkl 100644
--- a/dist/bundle.min.js
+++ b/dist/bundle.min.js
@@ -1 +1 @@
-var a=1;console.log(a);
+var a=1;console.log(a);var b=2;

diff --git a/src/components/DownloadButton.tsx b/src/components/DownloadButton.tsx
new file mode 100644
index 000000..abcdef
--- /dev/null
+++ b/src/components/DownloadButton.tsx
@@ -0,0 +1,24 @@
+import React from 'react';
+import { Button } from './ui/button';
+import { useToast } from './ui/toast';
+
+export function DownloadButton({ songId, isPremium }: { songId: string; isPremium: boolean }) {
+  const { toast } = useToast();
+  const handleDownload = () => {
+    toast({ title: "Download Started", description: "Saving song for offline playback." });
+  };
+  return (
+    <Button onClick={handleDownload}>
+      Download Song
+    </Button>
+  );
+}

diff --git a/src/services/downloadService.ts b/src/services/downloadService.ts
new file mode 100644
index 000000..123456
--- /dev/null
+++ b/src/services/downloadService.ts
@@ -0,0 +1,18 @@
+export async function downloadSong(songId: string, userTier: string) {
+  // NOTE: Premium check is currently missing here!
+  console.log("Downloading song", songId);
+  return { status: "downloaded", localPath: `/cache/${songId}.mp3` };
+}
+"""


def main():
    print("=" * 65)
    print("  CARTANA INPUT SYSTEM — LOCAL DRY-RUN PIPELINE TEST")
    print("=" * 65)

    req_bytes = SAMPLE_REQUIREMENT_MD.encode("utf-8")
    result = dry_run_pipeline_test(
        req_bytes=req_bytes,
        req_filename="sample_spec.md",
        req_kind="text",
        raw_diff=SAMPLE_LARGE_DIFF,
    )

    print("\n--- 1. REQUIREMENT PARSING RESULTS ---")
    print(f"File Name: {result['requirement_file']}")
    print(f"Raw Text Length: {result['requirement_text_length']} chars")
    print(f"Extracted Requirements Count: {result['parsed_requirements_count']}")
    print("Parsed Requirements Preview:")
    for r in result["requirements_preview"]:
        print(f"  [{r['id']}] ({r['kind']}): {r['title']}")

    print("\n--- 2. GIT DIFF NOISE FILTERING & COMPRESSION ---")
    print(f"Total Files in Diff: {result['diff_total_files']}")
    print(f"Kept Code Files: {result['diff_kept_files']}")
    print(f"Ignored Noise Files (lockfiles/bundles): {result['diff_ignored_files']}")
    print(f"Raw Diff Length: {result['raw_diff_chars']} chars")
    print(f"Compressed Diff Length: {result['compressed_diff_chars']} chars")
    print(f"Token Overhead Reduction: {result['token_reduction_percent']}%")

    print("\n" + "=" * 65)
    print("  SUCCESS: 0 bytes sent to cloud databases (In-Memory Dry Run)")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
