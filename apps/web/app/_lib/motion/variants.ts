import type { Variants } from "framer-motion";
import { MOTION_DISTANCE, MOTION_DURATION, MOTION_EASE, MOTION_STAGGER, SUBTLE_SPRING } from "./tokens";

export const reducedFadeVariants: Variants = {
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { duration: MOTION_DURATION.fast } },
  exit: { opacity: 0, transition: { duration: MOTION_DURATION.fast } },
};

export const pageVariants: Variants = {
  initial: {
    opacity: 0,
    y: MOTION_DISTANCE.md,
    scale: 0.995,
  },
  animate: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      duration: MOTION_DURATION.slow,
      ease: MOTION_EASE.emphasized,
    },
  },
  exit: {
    opacity: 0,
    y: MOTION_DISTANCE.sm,
    transition: {
      duration: MOTION_DURATION.fast,
      ease: MOTION_EASE.exit,
    },
  },
};

export const sectionVariants: Variants = {
  initial: {
    opacity: 0,
    y: MOTION_DISTANCE.sm,
  },
  animate: {
    opacity: 1,
    y: 0,
    transition: {
      duration: MOTION_DURATION.base,
      ease: MOTION_EASE.standard,
    },
  },
  exit: {
    opacity: 0,
    y: MOTION_DISTANCE.xs,
    transition: {
      duration: MOTION_DURATION.fast,
      ease: MOTION_EASE.exit,
    },
  },
};

export const staggerContainerVariants: Variants = {
  initial: { opacity: 0 },
  animate: {
    opacity: 1,
    transition: {
      staggerChildren: MOTION_STAGGER.base,
      delayChildren: 0.04,
    },
  },
};

export const staggerItemVariants: Variants = {
  initial: {
    opacity: 0,
    y: MOTION_DISTANCE.sm,
  },
  animate: {
    opacity: 1,
    y: 0,
    transition: {
      duration: MOTION_DURATION.base,
      ease: MOTION_EASE.standard,
    },
  },
  exit: {
    opacity: 0,
    y: MOTION_DISTANCE.xs,
    transition: {
      duration: MOTION_DURATION.fast,
    },
  },
};

export const presenceCollapseVariants: Variants = {
  initial: {
    opacity: 0,
    height: 0,
    y: -MOTION_DISTANCE.xs,
  },
  animate: {
    opacity: 1,
    height: "auto",
    y: 0,
    transition: {
      ...SUBTLE_SPRING,
      duration: MOTION_DURATION.base,
    },
  },
  exit: {
    opacity: 0,
    height: 0,
    y: -MOTION_DISTANCE.xs,
    transition: {
      duration: MOTION_DURATION.fast,
      ease: MOTION_EASE.exit,
    },
  },
};

export const cardInteractionVariants: Variants = {
  rest: {
    y: 0,
    scale: 1,
  },
  hover: {
    y: -2,
    scale: 1.005,
    transition: {
      duration: MOTION_DURATION.fast,
      ease: MOTION_EASE.standard,
    },
  },
  tap: {
    y: 0,
    scale: 0.992,
    transition: {
      duration: MOTION_DURATION.fast,
      ease: MOTION_EASE.standard,
    },
  },
};

export const buttonInteractionVariants: Variants = {
  rest: {
    y: 0,
    scale: 1,
  },
  hover: {
    y: -1,
    scale: 1.01,
    transition: {
      duration: MOTION_DURATION.fast,
      ease: MOTION_EASE.standard,
    },
  },
  tap: {
    y: 0,
    scale: 0.985,
    transition: {
      duration: MOTION_DURATION.fast,
      ease: MOTION_EASE.standard,
    },
  },
};
