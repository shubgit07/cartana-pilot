"use client";

import { MessageSquare } from "lucide-react";
import { ComingSoon } from "@/components/common/ComingSoon";

/**
 * Chat placeholder. `ChatPanel` stays intact for later wiring; this screen
 * owns the Chat tab until the chat backend exists (currently HTTP 501).
 */
export function ChatComingSoon() {
  return (
    <ComingSoon
      icon={<MessageSquare className="size-5" aria-hidden="true" />}
      title="Chat is under construction"
      description={
        <>
          Grounded Q&A over your specs, with citations, is on the roadmap. The main
          feature — verifying pull requests against requirements — is working now in
          the Compliance tab.
        </>
      }
    />
  );
}
