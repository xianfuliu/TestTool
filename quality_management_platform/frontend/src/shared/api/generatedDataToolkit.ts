import { post } from "@/shared/api/client";

export type GeneratedRuntimeVariablesPayload = {
  variables: Record<string, string>;
};

export function fetchGeneratedRuntimeVariables(config?: Record<string, unknown>) {
  return post<GeneratedRuntimeVariablesPayload>("/api/test-data/runtime-variables/", {
    config: config ?? {},
  });
}
