import type { CalculatorOperator } from "../calculator/model";
import { clearAuthSession, getAuthTokenFromBrowserSession, getAuthTokenTypeFromBrowserSession } from "../mock-auth";

const endpointByOperator: Record<CalculatorOperator, string> = {
  "+": "/api/v1/calculate/add",
  "−": "/api/v1/calculate/subtract",
  "×": "/api/v1/calculate/multiply",
  "÷": "/api/v1/calculate/divide",
};

const gatewayBaseUrl = (process.env.NEXT_PUBLIC_API_GATEWAY_URL ?? "http://localhost:4000").replace(/\/$/, "");

interface GatewayMathResponse {
  operation: "addition" | "subtraction" | "multiplication" | "division";
  result: number;
  transaction_id: string;
  timestamp: string;
}

class GatewayMathError extends Error {
  constructor(message: string, readonly status?: number, readonly code?: "auth_required" | "session_expired") {
    super(message);
    this.name = "GatewayMathError";
  }
}

const readResponseMessage = async (response: Response) => {
  try {
    const payload = (await response.json()) as { message?: string };
    return payload.message;
  } catch {
    return null;
  }
};

export const calculateGatewayOperation = async (
  operator: CalculatorOperator,
  operandA: number,
  operandB: number,
): Promise<GatewayMathResponse> => {
  const endpoint = `${gatewayBaseUrl}${endpointByOperator[operator]}`;
  const token = getAuthTokenFromBrowserSession();

  if (!token) {
    throw new GatewayMathError("Authentication required. Please sign in.", 401, "auth_required");
  }

  const tokenType = getAuthTokenTypeFromBrowserSession();

  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `${tokenType} ${token}`,
    },
    body: JSON.stringify({
      operand_a: operandA,
      operand_b: operandB,
    }),
  });

  if (response.status === 401) {
    clearAuthSession();
    throw new GatewayMathError("Session expired. Please sign in again.", 401, "session_expired");
  }

  if (!response.ok) {
    const responseMessage = await readResponseMessage(response);
    throw new GatewayMathError(responseMessage ?? "Calculation request failed.", response.status);
  }

  const payload = (await response.json()) as Partial<GatewayMathResponse>;

  if (typeof payload.result !== "number") {
    throw new GatewayMathError("Received invalid calculation response.");
  }

  return payload as GatewayMathResponse;
};

export const isAuthGatewayMathError = (error: unknown) => {
  return error instanceof GatewayMathError && (error.code === "auth_required" || error.code === "session_expired");
};

export const toCalculatorErrorMessage = (error: unknown) => {
  if (error instanceof GatewayMathError) {
    return error.message;
  }

  return "Unable to reach math gateway at http://localhost:4000.";
};
