import { beforeEach, describe, expect, it, vi } from "vitest";

const redirect = vi.fn();
const cookies = vi.fn();

vi.mock("next/navigation", () => ({
  redirect,
}));

vi.mock("next/headers", () => ({
  cookies,
}));

describe("Home page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("redirects unauthenticated users to login", async () => {
    cookies.mockResolvedValue({
      get: vi.fn().mockReturnValue(undefined),
    });

    const { default: Home } = await import("./page");
    await Home();

    expect(redirect).toHaveBeenCalledWith("/login");
  });

  it("redirects authenticated users to calculator", async () => {
    cookies.mockResolvedValue({
      get: vi.fn().mockReturnValue({ value: "1" }),
    });

    const { default: Home } = await import("./page");
    await Home();

    expect(redirect).toHaveBeenCalledWith("/calculator/focused");
  });
});
