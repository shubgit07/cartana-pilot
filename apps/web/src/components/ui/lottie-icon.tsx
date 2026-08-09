"use client";

import { useEffect, useRef } from "react";
import { useLottie } from "lottie-react";
import { cn } from "@/lib/cn";

export function LottieIcon({
  animationData,
  className,
  color = "currentColor",
  playsOnHover = true,
  "aria-hidden": ariaHidden = true,
}: {
  animationData: unknown;
  className?: string;
  color?: string;
  playsOnHover?: boolean;
  "aria-hidden"?: boolean;
}) {
  const reducedMotionRef = useRef(false);

  const { View, goToAndStop, goToAndPlay, animationContainerRef } = useLottie({
    animationData,
    loop: false,
    autoplay: false,
    className: cn("lottie-icon", className),
    "aria-hidden": ariaHidden,
    onDOMLoaded: () => {
      recolor(animationContainerRef.current, color);
      goToAndStop(lastFrame(animationData), true);
    },
    onPointerEnter: () => {
      if (!playsOnHover || reducedMotionRef.current) return;
      goToAndPlay(0, true);
    },
  });

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sync = () => {
      reducedMotionRef.current = mq.matches;
    };
    sync();
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, []);

  return View;
}

function lastFrame(animationData: unknown): number {
  const op = (animationData as { op?: number } | null)?.op;
  return typeof op === "number" && op > 0 ? op - 1 : 89;
}

function recolor(container: HTMLDivElement | null, color: string) {
  if (!container) return;
  container
    .querySelectorAll<SVGElement>("path, line, polyline, polygon, rect, circle, ellipse, text")
    .forEach((el) => {
      const stroke = el.getAttribute("stroke");
      if (stroke && stroke !== "none" && stroke !== "transparent") {
        el.style.stroke = color;
      }
      const fill = el.getAttribute("fill");
      if (fill && fill !== "none" && fill !== "transparent") {
        el.style.fill = color;
      }
    });
}
