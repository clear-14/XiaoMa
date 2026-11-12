"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import ErrorState from "@/components/ErrorState";
import LoadingState from "@/components/LoadingState";
import { getErrorMessage } from "@/lib/api";
import { getAuthStatus, logout, type AuthStatus } from "@/lib/auth";
import {
  createBackup,
  deleteBackup,
  downloadBackup,
  listBackups,
  type BackupInfo,
} from "@/lib/backups";
import { formatDateTime } from "@/lib/format";
import {
  createModelConfig,
  deleteModelConfig,
  listModelConfigs,
  setDefaultModel,
  testModelConnection,
  updateModelConfig,
  type ModelConfig,
  type ModelConfigInput,
  type ModelProvider,
  type TestConnectionResult,
} from "@/lib/models";

const PROVIDERS: { value: ModelProvider; label: string }[] = [
  { value: "deepseek", label: "DeepSeek" },
  { value: "qwen", label: "通义千问（DashScope 兼容模式）" },
  { value: "openai", label: "OpenAI" },
  { value: "custom", label: "自定义 OpenAI 兼容接口" },
];

interface FormState {
  name: string;
  provider: ModelProvider;
  model_name: string;
  base_url: string;
  api_key: string;
  temperature: string;
  max_tokens: string;
  timeout: string;
  is_default: boolean;
}

const EMPTY_FORM: FormState = {
  name: "",
  provider: "deepseek",
  model_name: "deepseek-chat",
  base_url: "",
  api_key: "",
  temperature: "0.7",
  max_tokens: "2048",
  timeout: "60",
  is_default: false,
};

function configToForm(config: ModelConfig): FormState {
  return {
    name: config.name,
    provider: config.provider as ModelProvider,
    model_name: config.model_name,
    base_url: config.base_url ?? "",
    api_key: "",
    temperature: String(config.temperature),
    max_tokens: String(config.max_tokens),
    timeout: String(config.timeout),
    is_default: config.is_default,
  };
}

function formatBytes(value: number): string {
  if (value < 1024) {
    return `${value} 字节`;
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

export default function SettingsClient() {
  const [authStatus, setAuthStatus] = useState<AuthStatus | null>(null);
  const [configs, setConfigs] = useState<ModelConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [formOpen, setFormOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [rowError, setRowError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<
    Record<string, TestConnectionResult>
  >({});

  const [backups, setBackups] = useState<BackupInfo[]>([]);
  const [backupBusy, setBackupBusy] = useState(false);
  const [backupError, setBackupError] = useState<string | null>(null);
  const [backupNotice, setBackupNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const [status, list, backupList] = await Promise.all([
        getAuthStatus(),
        listModelConfigs(),
        listBackups(),
      ]);
      setAuthStatus(status);
      setConfigs(list);
      setBackups(backupList);
    } catch (err) {
      setLoadError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  const openCreateForm = () => {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setFormError(null);
    setFormOpen(true);
  };

  const openEditForm = (config: ModelConfig) => {
    setEditingId(config.id);
    setForm(configToForm(config));
    setFormError(null);
    setFormOpen(true);
  };

  const closeForm = () => {
    if (saving) {
      return;
    }
    setFormOpen(false);
    setEditingId(null);
    setFormError(null);
  };

  const updateForm = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setFormError(null);
    const payload: ModelConfigInput = {
      name: form.name.trim(),
      provider: form.provider,
      model_name: form.model_name.trim(),
      base_url: form.base_url.trim() || null,
      temperature: Number(form.temperature),
      max_tokens: Number(form.max_tokens),
      timeout: Number(form.timeout),
      is_default: form.is_default,
    };
    if (form.api_key.trim()) {
      payload.api_key = form.api_key.trim();
    }
    try {
      if (editingId) {
        await updateModelConfig(editingId, payload);
      } else {
        if (!payload.api_key) {
          throw new Error("添加模型时必须填写 API Key");
        }
        await createModelConfig(payload);
      }
      setFormOpen(false);
      setEditingId(null);
      await load();
    } catch (err) {
      setFormError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const makeDefault = async (config: ModelConfig) => {
    setBusyId(config.id);
    setRowError(null);
    try {
      await setDefaultModel(config.id);
      await load();
    } catch (err) {
      setRowError(getErrorMessage(err));
    } finally {
      setBusyId(null);
    }
  };

  const remove = async (config: ModelConfig) => {
    if (
      !window.confirm(
        `确定删除模型配置「${config.name}」吗？删除后该配置的 API Key 将从数据库中移除。`,
      )
    ) {
      return;
    }
    setBusyId(config.id);
    setRowError(null);
    try {
      await deleteModelConfig(config.id);
      await load();
    } catch (err) {
      setRowError(getErrorMessage(err));
    } finally {
      setBusyId(null);
    }
  };

  const test = async (config: ModelConfig) => {
    setBusyId(config.id);
    setRowError(null);
    try {
      const result = await testModelConnection(config.id);
      setTestResults((current) => ({ ...current, [config.id]: result }));
    } catch (err) {
      setRowError(getErrorMessage(err));
    } finally {
      setBusyId(null);
    }
  };

  const doBackup = async () => {
    setBackupBusy(true);
    setBackupError(null);
    setBackupNotice(null);
    try {
      const info = await createBackup();
      setBackups(await listBackups());
      setBackupNotice(`备份已创建：${info.name}`);
    } catch (err) {
      setBackupError(getErrorMessage(err));
    } finally {
      setBackupBusy(false);
    }
  };

  const doDownload = async (name: string) => {
    setBackupError(null);
    try {
      await downloadBackup(name);
    } catch (err) {
      setBackupError(getErrorMessage(err));
    }
  };

  const doDeleteBackup = async (name: string) => {
    if (!window.confirm(`确定删除备份「${name}」吗？删除后不可恢复。`)) {
      return;
    }
    setBackupError(null);
    setBackupNotice(null);
    try {
      await deleteBackup(name);
      setBackups(await listBackups());
      setBackupNotice(`已删除备份：${name}`);
    } catch (err) {
      setBackupError(getErrorMessage(err));
    }
  };

  if (loading) {
    return <LoadingState label="加载系统设置…" />;
  }

  if (loadError) {
    return (
      <ErrorState
        title="无法加载系统设置"
        message={loadError}
        action={
          <button type="button" className="btn" onClick={() => void load()}>
            重试
          </button>
        }
      />
    );
  }

  return (
    <div className="settings-sections">
      <section className="card settings-section" id="access-security">
        <div className="section-head">
          <div>
            <h2 className="section-title">访问安全</h2>
            <p className="muted">
              默认仅允许本机访问；开放局域网或公网时必须启用访问密码，且由后端强制校验。
            </p>
          </div>
        </div>
        {authStatus?.required ? (
          <div className="settings-row">
            <div>
              <span className="badge badge-completed">访问密码已启用</span>
              <p className="muted settings-row-desc">
                所有数据接口均要求登录会话。会话默认保存 24 小时，后端重启后需重新登录。
              </p>
            </div>
            <button
              type="button"
              className="btn"
              onClick={() => void logout()}
            >
              退出登录
            </button>
          </div>
        ) : (
          <div className="notice">
            当前未启用访问密码，服务应只在本机访问。需要局域网或公网访问时，
            请在 `.env` 中设置 `XIAOMA_ACCESS_PASSWORD`，并参考
            `docs/Docker部署.md` 的“局域网访问”章节。
          </div>
        )}
      </section>

      <section className="card settings-section" id="model-configs">
        <div className="section-head">
          <div>
            <h2 className="section-title">模型配置</h2>
            <p className="muted">
              API Key 使用 Fernet 加密保存，页面只展示脱敏值；日志不会记录完整密钥。
            </p>
          </div>
          <button type="button" className="btn btn-primary" onClick={openCreateForm}>
            添加模型
          </button>
        </div>

        {rowError && <div className="inline-error">{rowError}</div>}

        {configs.length === 0 ? (
          <div className="notice">
            尚未配置模型。添加一个模型并设为默认后，AI 教学与测验变式题才能使用；
            计划、进度、测验、错题和资源查询不依赖模型。
          </div>
        ) : (
          <ul className="config-list">
            {configs.map((config) => {
              const result = testResults[config.id];
              return (
                <li key={config.id} className="config-card">
                  <div className="config-main">
                    <div className="tag-row">
                      <strong>{config.name}</strong>
                      {config.is_default && (
                        <span className="badge badge-completed">默认模型</span>
                      )}
                      <span className="badge badge-pending">
                        {PROVIDERS.find((item) => item.value === config.provider)?.label ??
                          config.provider}
                      </span>
                    </div>
                    <p className="config-meta">
                      模型：{config.model_name} · Key：{config.api_key_masked ?? "未保存"}
                    </p>
                    <p className="config-meta">
                      端点：{config.base_url ?? "使用服务商预设"} · temperature{" "}
                      {config.temperature} · max_tokens {config.max_tokens} · timeout{" "}
                      {config.timeout}s
                    </p>
                    {result && (
                      <div
                        className={`notice ${
                          result.ok ? "notice-success" : "notice-warning"
                        }`}
                      >
                        {result.ok
                          ? `连接成功（${result.latency_ms ?? "?"} ms）：${result.reply ?? ""}`
                          : `连接失败：${result.error ?? "未知原因"}`}
                      </div>
                    )}
                  </div>
                  <div className="row-actions config-actions">
                    {!config.is_default && (
                      <button
                        type="button"
                        className="btn btn-sm"
                        disabled={busyId === config.id}
                        onClick={() => void makeDefault(config)}
                      >
                        设为默认
                      </button>
                    )}
                    <button
                      type="button"
                      className="btn btn-sm"
                      disabled={busyId === config.id}
                      onClick={() => void test(config)}
                    >
                      {busyId === config.id ? "处理中…" : "测试连接"}
                    </button>
                    <button
                      type="button"
                      className="btn btn-sm"
                      disabled={busyId === config.id}
                      onClick={() => openEditForm(config)}
                    >
                      编辑
                    </button>
                    <button
                      type="button"
                      className="btn btn-sm btn-danger"
                      disabled={busyId === config.id}
                      onClick={() => void remove(config)}
                    >
                      删除
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}

        {formOpen && (
          <form className="config-form card" onSubmit={save}>
            <h3 className="section-title">
              {editingId ? "编辑模型配置" : "添加模型配置"}
            </h3>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label" htmlFor="config-name">
                  配置名称
                </label>
                <input
                  id="config-name"
                  className="form-input"
                  required
                  maxLength={64}
                  value={form.name}
                  onChange={(event) => updateForm("name", event.target.value)}
                  placeholder="例如：DeepSeek 主力模型"
                />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="config-provider">
                  服务商
                </label>
                <select
                  id="config-provider"
                  className="form-select"
                  value={form.provider}
                  onChange={(event) =>
                    updateForm("provider", event.target.value as ModelProvider)
                  }
                >
                  {PROVIDERS.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label" htmlFor="config-model">
                  模型名称
                </label>
                <input
                  id="config-model"
                  className="form-input"
                  required
                  maxLength={128}
                  value={form.model_name}
                  onChange={(event) => updateForm("model_name", event.target.value)}
                  placeholder="deepseek-chat"
                />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="config-base-url">
                  Base URL（可选）
                </label>
                <input
                  id="config-base-url"
                  className="form-input"
                  maxLength={256}
                  value={form.base_url}
                  onChange={(event) => updateForm("base_url", event.target.value)}
                  placeholder="自定义接口必填，例如 https://api.example.com/v1"
                />
              </div>
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor="config-api-key">
                API Key {editingId ? "（留空表示保持原 Key 不变）" : ""}
              </label>
              <input
                id="config-api-key"
                className="form-input"
                type="password"
                autoComplete="new-password"
                required={!editingId}
                maxLength={256}
                value={form.api_key}
                onChange={(event) => updateForm("api_key", event.target.value)}
                placeholder={editingId ? "不修改请留空" : "sk-…"}
              />
              <p className="form-hint">
                Key 仅用于本次提交并立即加密保存，不会以明文回显或写入日志。
              </p>
            </div>
            <div className="form-row form-row-3">
              <div className="form-group">
                <label className="form-label" htmlFor="config-temperature">
                  temperature（0–2）
                </label>
                <input
                  id="config-temperature"
                  className="form-input"
                  type="number"
                  min={0}
                  max={2}
                  step={0.1}
                  required
                  value={form.temperature}
                  onChange={(event) => updateForm("temperature", event.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="config-max-tokens">
                  max_tokens
                </label>
                <input
                  id="config-max-tokens"
                  className="form-input"
                  type="number"
                  min={1}
                  max={65536}
                  required
                  value={form.max_tokens}
                  onChange={(event) => updateForm("max_tokens", event.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="config-timeout">
                  timeout（秒）
                </label>
                <input
                  id="config-timeout"
                  className="form-input"
                  type="number"
                  min={1}
                  max={600}
                  required
                  value={form.timeout}
                  onChange={(event) => updateForm("timeout", event.target.value)}
                />
              </div>
            </div>
            {!editingId && (
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={form.is_default}
                  onChange={(event) => updateForm("is_default", event.target.checked)}
                />
                添加后设为默认模型
              </label>
            )}
            {formError && <div className="inline-error">{formError}</div>}
            <div className="row-actions form-actions">
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? "保存中…" : "保存配置"}
              </button>
              <button type="button" className="btn" onClick={closeForm} disabled={saving}>
                取消
              </button>
            </div>
          </form>
        )}
      </section>

      <section className="card settings-section" id="data-backups">
        <div className="section-head">
          <div>
            <h2 className="section-title">数据备份</h2>
            <p className="muted">
              备份保存在 SQLite 数据目录的 backups/ 中（Docker 下位于数据卷，容器重启不丢失）。
            </p>
          </div>
          <button
            type="button"
            className="btn btn-primary"
            disabled={backupBusy}
            onClick={() => void doBackup()}
          >
            {backupBusy ? "正在备份…" : "立即备份"}
          </button>
        </div>

        {backupError && <div className="inline-error">{backupError}</div>}
        {backupNotice && <div className="notice notice-success">{backupNotice}</div>}

        {backups.length === 0 ? (
          <div className="notice">暂无备份。建议在完成学习计划调整或批量导入数据前后备份。</div>
        ) : (
          <ul className="backup-list">
            {backups.map((backup) => (
              <li key={backup.name} className="backup-row">
                <div>
                  <strong className="backup-name">{backup.name}</strong>
                  <p className="muted">
                    {formatDateTime(backup.created_at)} · {formatBytes(backup.size_bytes)}
                  </p>
                </div>
                <div className="row-actions">
                  <button
                    type="button"
                    className="btn btn-sm"
                    onClick={() => void doDownload(backup.name)}
                  >
                    下载
                  </button>
                  <button
                    type="button"
                    className="btn btn-sm btn-danger"
                    onClick={() => void doDeleteBackup(backup.name)}
                  >
                    删除
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}

        <div className="notice settings-notice">
          <strong>恢复数据库：</strong>为避免运行中的连接损坏数据，恢复必须停止后端后执行。
          Docker 部署示例：<code>docker compose stop backend</code>，
          然后 <code>docker compose run --rm backend python -m app.cli restore-db 备份文件名 --yes</code>，
          最后 <code>docker compose start backend</code>。恢复前会自动备份当前数据库。
          详见 <code>docs/备份与恢复.md</code>。
        </div>
      </section>
    </div>
  );
}
