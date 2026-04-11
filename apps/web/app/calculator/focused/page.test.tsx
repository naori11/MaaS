import React from "react";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import CalculatorFocusedPage from "./page";

describe("Calculator focused page", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("renders calculator display and primary controls", () => {
    render(<CalculatorFocusedPage />);

    expect(screen.getByText("Current Expression")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "=" })).toBeInTheDocument();
  });
});
