"use client";

import * as React from "react";
import { auditApi } from "@/lib/api";
import { messageOf } from "./projects";

export function useVerifyPR(projectId: string) {
  const [brief, setBrief] = React.useState<import("@cartana/shared").PRTrustBrief | null>(null);
  const [fromCache, setFromCache] = React.useState(false);
  const [verifying, setVerifying] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const verify = React.useCallback(
    async (input: import("@cartana/shared").VerifyPRInput) => {
      setVerifying(true);
      setError(null);
      try {
        const res = await auditApi.verifyPR(projectId, input);
        setBrief(res.brief);
        setFromCache(res.fromCache);
        return res.brief;
      } catch (e: unknown) {
        const msg = messageOf(e) || "PR Verification failed.";
        setError(msg);
        throw e;
      } finally {
        setVerifying(false);
      }
    },
    [projectId]
  );

  const clear = React.useCallback(() => {
    setBrief(null);
    setError(null);
    setFromCache(false);
  }, []);

  const loadBrief = React.useCallback(
    (next: import("@cartana/shared").PRTrustBrief) => {
      setBrief(next);
      setFromCache(false);
      setError(null);
    },
    []
  );

  return { brief, fromCache, verifying, error, verify, clear, loadBrief };
}
