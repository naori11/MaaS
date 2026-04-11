"use client";

import type { MouseEventHandler, ReactNode } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import {
  buttonInteractionVariants,
  cardInteractionVariants,
  pageVariants,
  presenceCollapseVariants,
  reducedFadeVariants,
  sectionVariants,
  staggerContainerVariants,
  staggerItemVariants,
} from "../../_lib/motion/variants";
import { MOTION_DURATION } from "../../_lib/motion/tokens";

type ChildrenProps = {
  children: ReactNode;
  className?: string;
};

export function MotionPage({ children, className }: ChildrenProps) {
  const shouldReduceMotion = useReducedMotion();
  const variants = shouldReduceMotion ? reducedFadeVariants : pageVariants;

  return (
    <motion.div className={className} variants={variants} initial="initial" animate="animate" exit="exit">
      {children}
    </motion.div>
  );
}

export function MotionSection({ children, className }: ChildrenProps) {
  const shouldReduceMotion = useReducedMotion();
  const variants = shouldReduceMotion ? reducedFadeVariants : sectionVariants;

  return (
    <motion.div className={className} variants={variants} initial="initial" animate="animate" exit="exit">
      {children}
    </motion.div>
  );
}

export function MotionStaggerContainer({ children, className }: ChildrenProps) {
  const shouldReduceMotion = useReducedMotion();

  return (
    <motion.div
      className={className}
      variants={shouldReduceMotion ? reducedFadeVariants : staggerContainerVariants}
      initial="initial"
      animate="animate"
      exit="exit"
    >
      {children}
    </motion.div>
  );
}

export function MotionStaggerItem({ children, className }: ChildrenProps) {
  const shouldReduceMotion = useReducedMotion();

  return (
    <motion.div className={className} variants={shouldReduceMotion ? reducedFadeVariants : staggerItemVariants}>
      {children}
    </motion.div>
  );
}

type MotionPresenceProps = {
  show: boolean;
  children: ReactNode;
  className?: string;
};

export function MotionPresenceBlock({ show, children, className }: MotionPresenceProps) {
  const shouldReduceMotion = useReducedMotion();

  return (
    <AnimatePresence initial={false} mode="wait">
      {show ? (
        <motion.div
          key="presence"
          className={className}
          variants={shouldReduceMotion ? reducedFadeVariants : presenceCollapseVariants}
          initial="initial"
          animate="animate"
          exit="exit"
          style={{ overflow: "hidden" }}
        >
          {children}
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}

type MotionButtonProps = {
  children: ReactNode;
  className?: string;
  type?: "button" | "submit" | "reset";
  onClick?: MouseEventHandler<HTMLButtonElement>;
  disabled?: boolean;
  ariaLabel?: string;
  ariaPressed?: boolean;
};

export function MotionButton({ children, className, type = "button", onClick, disabled, ariaLabel, ariaPressed }: MotionButtonProps) {
  const shouldReduceMotion = useReducedMotion();

  return (
    <motion.button
      type={type}
      className={className}
      onClick={onClick}
      disabled={disabled}
      aria-label={ariaLabel}
      aria-pressed={ariaPressed}
      variants={shouldReduceMotion ? undefined : buttonInteractionVariants}
      initial="rest"
      whileHover={disabled || shouldReduceMotion ? "rest" : "hover"}
      whileTap={disabled || shouldReduceMotion ? "rest" : "tap"}
      animate="rest"
      transition={{ duration: MOTION_DURATION.fast }}
    >
      {children}
    </motion.button>
  );
}

type MotionCardProps = {
  children: ReactNode;
  className?: string;
};

export function MotionCard({ children, className }: MotionCardProps) {
  const shouldReduceMotion = useReducedMotion();

  return (
    <motion.div
      className={className}
      variants={shouldReduceMotion ? undefined : cardInteractionVariants}
      initial="rest"
      whileHover={shouldReduceMotion ? "rest" : "hover"}
      whileTap={shouldReduceMotion ? "rest" : "tap"}
      animate="rest"
      transition={{ duration: MOTION_DURATION.fast }}
    >
      {children}
    </motion.div>
  );
}
