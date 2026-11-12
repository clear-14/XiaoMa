/** 学习档案与学习进度概览 API 封装。 */

import { api } from "@/lib/api";
import type {
  LearningOverview,
  Profile,
  ProfileUpdateInput,
} from "@/lib/types";

export type { LearningOverview, Profile } from "@/lib/types";

export function getProfile(): Promise<Profile> {
  return api.get<Profile>("/profile");
}

export function updateProfile(input: ProfileUpdateInput): Promise<Profile> {
  return api.put<Profile>("/profile", input);
}

export function getLearningOverview(): Promise<LearningOverview> {
  return api.get<LearningOverview>("/overview");
}
