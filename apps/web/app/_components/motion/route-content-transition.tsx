"use client";

import type { ReactNode } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { usePathname } from "next/navigation";
import { MOTION_DURATION, MOTION_EASE } from "../../_lib/motion/tokens";

type RouteContentTransitionProps = {
  children: ReactNode;
  className?: string;
};

export function RouteContentTransition({ children, className }: RouteContentTransitionProps) {
  const pathname = usePathname();
  const shouldReduceMotion = useReducedMotion();

  return (
    <motion.div
      key={pathname}
      className={className}
      initial={shouldReduceMotion ? { opacity: 0.98 } : { opacity: 0.98, y: 2 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: shouldReduceMotion ? MOTION_DURATION.fast : MOTION_DURATION.fast,
        ease: MOTION_EASE.standard,
      }}
    >
      {children}
    </motion.div>
  );
}
