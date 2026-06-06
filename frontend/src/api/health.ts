import { apiGet } from "./client";

export type HealthResponse = {
  status: string;
};

export function getHealth() {
  return apiGet<HealthResponse>("/health");
}
