import type { Transition } from "framer-motion";

export const MOTION_DURATION = {
  instant: 0.01,
  fast: 0.16,
  base: 0.24,
  slow: 0.34,
} as const;

export const MOTION_EASE = {
  standard: [0.22, 1, 0.36, 1],
  emphasized: [0.16, 1, 0.3, 1],
  exit: [0.4, 0, 1, 1],
} as const;

export const MOTION_DISTANCE = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 18,
} as const;

export const MOTION_STAGGER = {
  tight: 0.035,
  base: 0.05,
} as const;

export const MOTION_TRANSITION: Record<"fast" | "base" | "slow", Transition> = {
  fast: {
    duration: MOTION_DURATION.fast,
    ease: MOTION_EASE.standard,
  },
  base: {
    duration: MOTION_DURATION.base,
    ease: MOTION_EASE.standard,
  },
  slow: {
    duration: MOTION_DURATION.slow,
    ease: MOTION_EASE.emphasized,
  },
};

export const SUBTLE_SPRING: Transition = {
  type: "spring",
  stiffness: 260,
  damping: 28,
  mass: 0.9,
};
