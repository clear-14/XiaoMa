/** 数据库备份 API 封装。恢复操作需停止后端后使用 CLI，见部署文档。 */

import { api } from "@/lib/api";
import type { BackupInfo } from "@/lib/types";

export type { BackupInfo } from "@/lib/types";

export function listBackups(): Promise<BackupInfo[]> {
  return api.get<BackupInfo[]>("/data/backups");
}

export function createBackup(): Promise<BackupInfo> {
  return api.post<BackupInfo>("/data/backups");
}

export function deleteBackup(name: string): Promise<void> {
  return api.delete<void>(`/data/backups/${encodeURIComponent(name)}`);
}

/** 下载备份并通过浏览器保存为文件。 */
export async function downloadBackup(name: string): Promise<void> {
  const blob = await api.download(`/data/backups/${encodeURIComponent(name)}`);
  const url = URL.createObjectURL(blob);
  try {
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = name;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  } finally {
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
  }
}
