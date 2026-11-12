/** 模型配置 API 封装（API Key 只在写入时提交，读取时始终为脱敏值）。 */

import { api } from "@/lib/api";
import type {
  ModelConfig,
  ModelConfigInput,
  TestConnectionResult,
} from "@/lib/types";

export type {
  ModelConfig,
  ModelConfigInput,
  ModelProvider,
  TestConnectionResult,
} from "@/lib/types";

/** AI 连接测试可能等待模型响应，使用较长超时。 */
const TEST_TIMEOUT_MS = 90_000;

export function listModelConfigs(): Promise<ModelConfig[]> {
  return api.get<ModelConfig[]>("/model-configs");
}

export function createModelConfig(input: ModelConfigInput): Promise<ModelConfig> {
  return api.post<ModelConfig>("/model-configs", input);
}

export function updateModelConfig(
  id: string,
  input: Partial<ModelConfigInput>,
): Promise<ModelConfig> {
  return api.put<ModelConfig>(`/model-configs/${id}`, input);
}

export function deleteModelConfig(id: string): Promise<void> {
  return api.delete<void>(`/model-configs/${id}`);
}

export function setDefaultModel(id: string): Promise<ModelConfig> {
  return api.post<ModelConfig>(`/model-configs/${id}/default`);
}

export function testModelConnection(id: string): Promise<TestConnectionResult> {
  return api.post<TestConnectionResult>(
    `/model-configs/${id}/test`,
    undefined,
    TEST_TIMEOUT_MS,
  );
}
