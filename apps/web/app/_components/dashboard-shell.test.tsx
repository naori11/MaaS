import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DashboardShell } from "./dashboard-shell";

describe("DashboardShell", () => {
  it("keeps sidebar and mobile nav without duplicate top tab links", () => {
    const { container } = render(
      <DashboardShell activeTab="calculator" title="Calculator View">
        <div>content</div>
      </DashboardShell>,
    );

    expect(container.querySelectorAll('a[href="/calculator/focused"]')).toHaveLength(2);
    expect(container.querySelectorAll('a[href="/history"]')).toHaveLength(2);
    expect(container.querySelectorAll('a[href="/billing"]')).toHaveLength(2);
    expect(screen.queryByRole("link", { name: /^calculator$/i })).not.toBeInTheDocument();
  });
});
