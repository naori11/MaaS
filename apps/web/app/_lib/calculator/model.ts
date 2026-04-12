export type CalculatorOperator = "÷" | "×" | "−" | "+";

export type CalculatorKey =
  | CalculatorOperator
  | "AC"
  | "+/-"
  | "%"
  | "="
  | "."
  | "0"
  | "1"
  | "2"
  | "3"
  | "4"
  | "5"
  | "6"
  | "7"
  | "8"
  | "9";

export interface CalculatorState {
  currentInput: string;
  expression: string;
  storedOperand: number | null;
  pendingOperator: CalculatorOperator | null;
  replaceInput: boolean;
  error: string | null;
}

export interface EvaluateCommand {
  type: "evaluate";
  operator: CalculatorOperator;
  operandA: number;
  operandB: number;
}

export type CalculatorCommand = { type: "none" } | EvaluateCommand;

export interface CalculatorTransition {
  nextState: CalculatorState;
  command: CalculatorCommand;
}

const NONE_COMMAND: CalculatorCommand = { type: "none" };

const isDigitKey = (key: CalculatorKey): key is Extract<CalculatorKey, `${number}`> => /^\d$/.test(key);

const formatNumber = (value: number) => {
  if (!Number.isFinite(value)) {
    return "0";
  }

  return Number.parseFloat(value.toFixed(12)).toString();
};

const toNumber = (value: string) => Number.parseFloat(value);

const appendToExpression = (state: CalculatorState, value: string) => {
  if (state.pendingOperator && state.storedOperand !== null) {
    return `${formatNumber(state.storedOperand)} ${state.pendingOperator} ${value}`;
  }

  return value;
};

export const createInitialCalculatorState = (): CalculatorState => ({
  currentInput: "0",
  expression: "0",
  storedOperand: null,
  pendingOperator: null,
  replaceInput: false,
  error: null,
});

const applyNumberInput = (state: CalculatorState, key: Extract<CalculatorKey, `${number}`> | "."): CalculatorState => {
  if (key === ".") {
    if (state.replaceInput) {
      return {
        ...state,
        currentInput: "0.",
        expression: appendToExpression(state, "0."),
        replaceInput: false,
      };
    }

    if (state.currentInput.includes(".")) {
      return state;
    }

    const nextValue = `${state.currentInput}.`;

    return {
      ...state,
      currentInput: nextValue,
      expression: appendToExpression(state, nextValue),
    };
  }

  const nextValue = state.replaceInput ? key : state.currentInput === "0" ? key : `${state.currentInput}${key}`;

  return {
    ...state,
    currentInput: nextValue,
    expression: appendToExpression(state, nextValue),
    replaceInput: false,
  };
};

const applyOperatorInput = (state: CalculatorState, operator: CalculatorOperator): CalculatorState => {
  const lhs = toNumber(state.currentInput);

  return {
    ...state,
    storedOperand: lhs,
    pendingOperator: operator,
    replaceInput: true,
    expression: `${formatNumber(lhs)} ${operator}`,
  };
};

const applyToggleSign = (state: CalculatorState): CalculatorState => {
  const nextValue = state.currentInput.startsWith("-") ? state.currentInput.slice(1) : `-${state.currentInput}`;
  const normalized = nextValue === "-0" ? "0" : nextValue;

  return {
    ...state,
    currentInput: normalized,
    expression: appendToExpression(state, normalized),
  };
};

const applyPercent = (state: CalculatorState): CalculatorState => {
  const nextNumber = toNumber(state.currentInput) / 100;
  const nextValue = formatNumber(nextNumber);

  return {
    ...state,
    currentInput: nextValue,
    expression: appendToExpression(state, nextValue),
    replaceInput: false,
  };
};

export const applyCalculatorKey = (state: CalculatorState, key: CalculatorKey): CalculatorTransition => {
  const baseState = key === "AC" || state.error === null ? state : createInitialCalculatorState();

  if (key === "AC") {
    return {
      nextState: createInitialCalculatorState(),
      command: NONE_COMMAND,
    };
  }

  if (isDigitKey(key) || key === ".") {
    return {
      nextState: applyNumberInput(baseState, key),
      command: NONE_COMMAND,
    };
  }

  if (key === "+/-") {
    return {
      nextState: applyToggleSign(baseState),
      command: NONE_COMMAND,
    };
  }

  if (key === "%") {
    return {
      nextState: applyPercent(baseState),
      command: NONE_COMMAND,
    };
  }

  if (key === "=" && baseState.pendingOperator && baseState.storedOperand !== null && !baseState.replaceInput) {
    const operandA = baseState.storedOperand;
    const operandB = toNumber(baseState.currentInput);

    if (baseState.pendingOperator === "÷" && operandB === 0) {
      return {
        nextState: {
          ...createInitialCalculatorState(),
          expression: `${formatNumber(operandA)} ÷ 0`,
          error: "Cannot divide by zero.",
        },
        command: NONE_COMMAND,
      };
    }

    return {
      nextState: {
        ...baseState,
        expression: `${formatNumber(operandA)} ${baseState.pendingOperator} ${formatNumber(operandB)}`,
        replaceInput: true,
      },
      command: {
        type: "evaluate",
        operator: baseState.pendingOperator,
        operandA,
        operandB,
      },
    };
  }

  if (key === "÷" || key === "×" || key === "−" || key === "+") {
    return {
      nextState: applyOperatorInput(baseState, key),
      command: NONE_COMMAND,
    };
  }

  return {
    nextState: baseState,
    command: NONE_COMMAND,
  };
};

export const applyEvaluationSuccess = (state: CalculatorState, command: EvaluateCommand, result: number): CalculatorState => {
  return {
    ...state,
    currentInput: formatNumber(result),
    expression: `${formatNumber(command.operandA)} ${command.operator} ${formatNumber(command.operandB)} =`,
    storedOperand: null,
    pendingOperator: null,
    replaceInput: true,
    error: null,
  };
};

export const applyEvaluationFailure = (command: EvaluateCommand, message: string): CalculatorState => {
  return {
    ...createInitialCalculatorState(),
    expression: `${formatNumber(command.operandA)} ${command.operator} ${formatNumber(command.operandB)}`,
    error: message,
  };
};
