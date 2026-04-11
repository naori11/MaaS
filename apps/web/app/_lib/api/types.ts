export type GatewayErrorCode = "unauthorized" | "bad_request" | "rate_limited" | "internal_error" | string;

export type GatewayErrorEnvelope = {
  error: {
    code: GatewayErrorCode;
    message: string;
  };
  request_id?: string;
};

export type AuthLoginRequest = {
  email: string;
  password: string;
};

export type AuthLoginResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
};
