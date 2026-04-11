import type { CalculatorOperator } from "../calculator/model";

const endpointByOperator: Record<CalculatorOperator, string> = {
  "+": "/api/v1/calculate/add",
  "−": "/api/v1/calculate/subtract",
  "×": "/api/v1/calculate/multiply",
  "÷": "/api/v1/calculate/divide",
};

interface GatewayMathResponse {
  operation: "addition" | "subtraction" | "multiplication" | "division";
  result: number;
  transaction_id: string;
  timestamp: string;
}

class GatewayMathError extends Error {
  constructor(message: string, readonly status?: number) {
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
  const endpoint = endpointByOperator[operator];

  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      operand_a: operandA,
      operand_b: operandB,
    }),
  });

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

export const toCalculatorErrorMessage = (error: unknown) => {
  if (error instanceof GatewayMathError) {
    return error.message;
  }

  return "Unable to reach math gateway.";
};
