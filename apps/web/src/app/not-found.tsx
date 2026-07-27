"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/common/EmptyState";

export default function NotFound() {
  return (
    <EmptyState
      icon="search"
      title="Page not found"
      description={"The page you're looking for doesn't exist or has been moved."}
      actions={
        <Button asChild>
          <Link href="/">Go home</Link>
        </Button>
      }
    />
  );
}
