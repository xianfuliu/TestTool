import { get, post } from "@/shared/api/client";

import type {
  EnterpriseWorkspace,
  TestDataConfig,
  TestDataMeta,
  TestDataWorkspace,
  UserWorkspace,
} from "./types";

export function fetchTestDataMeta() {
  return get<TestDataMeta>("/api/test-data/meta/");
}

export function generateTestDataWorkspace(config: TestDataConfig) {
  return post<TestDataWorkspace>("/api/test-data/workspace/", { config });
}

export function generateUserWorkspace(config: TestDataConfig) {
  return post<UserWorkspace>("/api/test-data/user-workspace/", { config });
}

export function generateEnterpriseWorkspace(config: TestDataConfig) {
  return post<EnterpriseWorkspace>("/api/test-data/enterprise-workspace/", { config });
}

export function refreshUserField(config: TestDataConfig, workspace: UserWorkspace, field: string) {
  return post<UserWorkspace>("/api/test-data/refresh-user-field/", {
    config,
    field,
    state: {
      id_data: workspace.id_card.data,
    },
  });
}

export function refreshEnterpriseField(
  config: TestDataConfig,
  workspace: EnterpriseWorkspace,
  field: string,
) {
  return post<EnterpriseWorkspace>("/api/test-data/refresh-enterprise-field/", {
    config,
    field,
    state: {
      business_data: workspace.business_license.data,
    },
  });
}

export function refreshTestDataField(
  config: TestDataConfig,
  workspace: TestDataWorkspace,
  field: string,
) {
  return post<TestDataWorkspace>("/api/test-data/refresh-field/", {
    config,
    field,
    state: {
      id_data: workspace.id_card.data,
      business_data: workspace.business_license.data,
    },
  });
}
