const DEFAULT_GATEWAY_URL = "http://localhost:4000";
const FALLBACK_ERROR_MESSAGE = "Unable to provision account. Please try again.";

type RegisterInput = {
  email: string;
  password: string;
};

type RegisterResponse = {
  id: string;
  email: string;
  created_at: string;
};

type GatewayErrorResponse = {
  error?: {
    message?: string;
  };
};

function resolveGatewayBaseUrl() {
  const value = process.env.NEXT_PUBLIC_API_GATEWAY_URL?.trim();

  if (!value) {
    return DEFAULT_GATEWAY_URL;
  }

  return value.endsWith("/") ? value.slice(0, -1) : value;
}

export async function register(input: RegisterInput): Promise<RegisterResponse> {
  const response = await fetch(`${resolveGatewayBaseUrl()}/api/v1/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    let message = FALLBACK_ERROR_MESSAGE;

    try {
      const data = (await response.json()) as GatewayErrorResponse;
      message = data.error?.message ?? message;
    } catch {
      message = FALLBACK_ERROR_MESSAGE;
    }

    throw new Error(message);
  }

  return (await response.json()) as RegisterResponse;
}
