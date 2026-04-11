import { requestJson } from "./client";
import type { AuthLoginRequest, AuthLoginResponse } from "./types";

export async function loginWithPassword(payload: AuthLoginRequest): Promise<AuthLoginResponse> {
  return requestJson<AuthLoginResponse>("/api/v1/auth/login", {
    method: "POST",
    body: payload,
  });
}
