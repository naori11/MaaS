import { beforeEach, describe, expect, it, vi } from "vitest";
import { AUTH_EXPIRES_AT_COOKIE, AUTH_TOKEN_COOKIE } from "./_lib/mock-auth";

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
      get: vi.fn((name: string) => {
        if (name === AUTH_TOKEN_COOKIE) {
          return { value: "jwt-token" };
        }

        if (name === AUTH_EXPIRES_AT_COOKIE) {
          return { value: String(Date.now() + 60_000) };
        }

        return undefined;
      }),
    });

    const { default: Home } = await import("./page");
    await Home();

    expect(redirect).toHaveBeenCalledWith("/calculator/focused");
  });
});
