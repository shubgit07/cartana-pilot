"use client";

import { LottieIcon } from "@/components/ui";
import cartanaLogo from "@/assets/cartana-logo.json";

export function CartanaLogo({ className }: { className?: string }) {
  return <LottieIcon animationData={cartanaLogo} className={className} />;
}
