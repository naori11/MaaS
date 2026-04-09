import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Home from "./page";

describe("Home page", () => {
  it("renders the initialized frontend text", () => {
    render(<Home />);

    expect(
      screen.getByRole("heading", { name: "Math-as-a-Service" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Next.js + Tailwind frontend initialized."),
    ).toBeInTheDocument();
  });
});
