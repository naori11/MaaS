import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import HistoryPage from "./page";

describe("History page", () => {
  beforeEach(() => {
    window.localStorage.clear();
    Object.defineProperty(URL, "createObjectURL", {
      writable: true,
      value: vi.fn(() => "blob:mock"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      writable: true,
      value: vi.fn(),
    });
    HTMLAnchorElement.prototype.click = vi.fn();
  });

  it("renders history heading and key controls", () => {
    render(<HistoryPage />);

    expect(screen.getByRole("heading", { name: "Calculation History" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /export csv/i })).toBeInTheDocument();
    expect(screen.getByText("#TX-94281-MA")).toBeInTheDocument();
  });

  it("cycles filter modes", () => {
    render(<HistoryPage />);

    const filterButton = screen.getByRole("button", { name: /filter view/i });

    fireEvent.click(filterButton);
    expect(screen.getByRole("button", { name: /filter view: success/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /filter view: success/i }));
    expect(screen.getByRole("button", { name: /filter view: errors/i })).toBeInTheDocument();
  });

  it("exports filtered rows to csv", () => {
    render(<HistoryPage />);

    fireEvent.click(screen.getByRole("button", { name: /export csv/i }));

    expect(URL.createObjectURL).toHaveBeenCalled();
    expect(URL.revokeObjectURL).toHaveBeenCalled();
  });
});
