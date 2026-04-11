"use client";

import type { ReactNode } from "react";
import { MotionConfig } from "framer-motion";
import { MOTION_TRANSITION } from "../../_lib/motion/tokens";

type MotionProviderProps = {
  children: ReactNode;
};

export function MotionProvider({ children }: MotionProviderProps) {
  return (
    <MotionConfig reducedMotion="user" transition={MOTION_TRANSITION.base}>
      {children}
    </MotionConfig>
  );
}
