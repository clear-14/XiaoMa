import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AccessGate from "@/components/AccessGate";
import { getAuthStatus, login } from "@/lib/auth";

vi.mock("@/lib/auth", () => ({
  getAuthStatus: vi.fn(),
  login: vi.fn(),
}));

const getAuthStatusMock = vi.mocked(getAuthStatus);
const loginMock = vi.mocked(login);

beforeEach(() => {
  getAuthStatusMock.mockReset();
  loginMock.mockReset();
});

describe("AccessGate 访问密码门禁", () => {
  it("未启用访问密码时直接显示应用内容", async () => {
    getAuthStatusMock.mockResolvedValue({
      required: false,
      authenticated: true,
    });

    render(
      <AccessGate>
        <div>应用内容</div>
      </AccessGate>,
    );

    expect(await screen.findByText("应用内容")).toBeInTheDocument();
  });

  it("启用访问密码时先显示登录页，登录成功后进入应用", async () => {
    getAuthStatusMock.mockResolvedValue({
      required: true,
      authenticated: false,
    });
    loginMock.mockResolvedValue();

    render(
      <AccessGate>
        <div>应用内容</div>
      </AccessGate>,
    );

    const input = await screen.findByLabelText("访问密码");
    expect(screen.queryByText("应用内容")).not.toBeInTheDocument();
    fireEvent.change(input, { target: { value: "my-password" } });
    fireEvent.click(screen.getByRole("button", { name: "进入小码" }));

    await waitFor(() => expect(loginMock).toHaveBeenCalledWith("my-password"));
    expect(await screen.findByText("应用内容")).toBeInTheDocument();
  });

  it("密码错误时显示后端错误且不进入应用", async () => {
    getAuthStatusMock.mockResolvedValue({
      required: true,
      authenticated: false,
    });
    loginMock.mockRejectedValue(new Error("访问密码错误"));

    render(
      <AccessGate>
        <div>应用内容</div>
      </AccessGate>,
    );

    const input = await screen.findByLabelText("访问密码");
    fireEvent.change(input, { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button", { name: "进入小码" }));

    expect(await screen.findByText("访问密码错误")).toBeInTheDocument();
    expect(screen.queryByText("应用内容")).not.toBeInTheDocument();
  });
});
