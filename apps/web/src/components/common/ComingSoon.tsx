"use client";

import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "./EmptyState";

type Props = {
  icon: React.ReactNode;
  title: string;
  description: React.ReactNode;
};

/**
 * Honest placeholder for tabs whose backend is not wired yet.
 * Keeps the tab clickable and explains what the feature will be,
 * instead of faking functionality that does not exist.
 */
export function ComingSoon({ icon, title, description }: Props) {
  return (
    <EmptyState
      icon={icon}
      title={title}
      description={description}
      actions={
        <Badge variant="warning" className="font-mono uppercase">
          In development
        </Badge>
      }
    />
  );
}
