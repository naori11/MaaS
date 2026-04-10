import React from "react";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import LoginPage from "./page";

const push = vi.fn();
const refresh = vi.fn();
let nextValue: string | null = "/history";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push,
    refresh,
  }),
  useSearchParams: () => ({
    get: () => nextValue,
  }),
}));

describe("Login page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    nextValue = "/history";
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders session initiation form", () => {
    render(<LoginPage />);

    expect(screen.getByRole("heading", { name: "Initiate Session" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Initiate Session" })).toBeInTheDocument();
    expect(screen.getByLabelText("Node Identity")).toBeInTheDocument();
    expect(screen.getByLabelText("Access Cipher")).toBeInTheDocument();
  });

  it("submits and navigates to next route", async () => {
    render(<LoginPage />);

    fireEvent.change(screen.getByLabelText("Node Identity"), { target: { value: "user@example.com" } });
    fireEvent.change(screen.getByLabelText("Access Cipher"), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: "Initiate Session" }));

    act(() => {
      vi.advanceTimersByTime(300);
    });

    expect(push).toHaveBeenCalledWith("/history");
    expect(refresh).toHaveBeenCalled();
  });

  it("shows validation error when fields are empty", () => {
    render(<LoginPage />);

    fireEvent.click(screen.getByRole("button", { name: "Initiate Session" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Node Identity and Access Cipher are required.");
  });
});
