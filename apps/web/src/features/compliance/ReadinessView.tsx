"use client";

import { FileSearch } from "lucide-react";
import { ComingSoon } from "@/components/common/ComingSoon";

type Props = {
  projectId: string;
};

/**
 * Spec Readiness is under construction. This tab previously rendered a
 * client-side mock scored as a server audit — replaced with an honest
 * placeholder until the real readiness backend exists. `projectId` is kept
 * so the parent tab contract does not change.
 */
export function ReadinessView({ projectId: _projectId }: Props) {
  return (
    <ComingSoon
      icon={<FileSearch className="size-5" aria-hidden="true" />}
      title="Spec Readiness is under construction"
      description={
        <>
          What is readiness? A pre-implementation score of how clear and testable each
          requirement is — before any code exists. Requirement extraction and PR
          verification are working today in the Requirements and Verification tabs;
          this audit view is next.
        </>
      }
    />
  );
}
