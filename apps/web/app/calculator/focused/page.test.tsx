import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import CalculatorFocusedPage from "./page";

describe("Calculator focused page", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("renders calculator display and primary controls", () => {
    render(<CalculatorFocusedPage />);

    expect(screen.getByRole("heading", { name: "Calculator View" })).toBeInTheDocument();
    expect(screen.getByText("Current Expression")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "=" })).toBeInTheDocument();
  });

  it("computes simple addition", () => {
    render(<CalculatorFocusedPage />);

    fireEvent.click(screen.getByRole("button", { name: "2" }));
    fireEvent.click(screen.getByRole("button", { name: "+" }));
    fireEvent.click(screen.getByRole("button", { name: "3" }));
    fireEvent.click(screen.getByRole("button", { name: "=" }));

    expect(screen.getByLabelText("Calculator result")).toHaveTextContent("5");
  });
});
