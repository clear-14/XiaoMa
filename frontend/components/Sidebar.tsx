"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";

interface NavItem {
  href: string;
  label: string;
  icon: ReactNode;
}

/** 简洁线性图标（内联 SVG，不引入图标库依赖） */
function Icon({ children }: { children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

const NAV_ITEMS: NavItem[] = [
  {
    href: "/",
    label: "首页",
    icon: (
      <Icon>
        <path d="M3 10.5 12 3l9 7.5" />
        <path d="M5 9.5V21h14V9.5" />
      </Icon>
    ),
  },
  {
    href: "/plan",
    label: "学习计划",
    icon: (
      <Icon>
        <rect x="3" y="5" width="18" height="16" rx="2" />
        <path d="M8 3v4M16 3v4M3 11h18" />
      </Icon>
    ),
  },
  {
    href: "/learn",
    label: "课程学习",
    icon: (
      <Icon>
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
      </Icon>
    ),
  },
  {
    href: "/workspace",
    label: "AI 学习工作台",
    icon: (
      <Icon>
        <path d="M21 11.5a8.5 8.5 0 0 1-8.5 8.5c-1.5 0-2.9-.4-4.1-1L3 20l1.2-5.2A8.5 8.5 0 1 1 21 11.5z" />
      </Icon>
    ),
  },
  {
    href: "/quiz",
    label: "测验中心",
    icon: (
      <Icon>
        <rect x="5" y="3" width="14" height="18" rx="2" />
        <path d="M9 3.5V2h6v1.5" />
        <path d="m9 13 2 2 4-4" />
      </Icon>
    ),
  },
  {
    href: "/mistakes",
    label: "错题本",
    icon: (
      <Icon>
        <path d="M12 3 2.5 20h19L12 3z" />
        <path d="M12 10v4.5" />
        <path d="M12 17.8v.2" />
      </Icon>
    ),
  },
  {
    href: "/profile",
    label: "学习档案",
    icon: (
      <Icon>
        <circle cx="12" cy="8" r="4" />
        <path d="M4 21c0-4 3.6-6 8-6s8 2 8 6" />
      </Icon>
    ),
  },
  {
    href: "/chat-history",
    label: "聊天历史",
    icon: (
      <Icon>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 2" />
      </Icon>
    ),
  },
  {
    href: "/settings",
    label: "系统设置",
    icon: (
      <Icon>
        <circle cx="12" cy="12" r="3" />
        <path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9 17 7M7 17l-2.1 2.1" />
      </Icon>
    ),
  },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);

  return (
    <>
      {/* 移动端顶栏 */}
      <header className="mobile-topbar">
        <button
          type="button"
          className="icon-btn"
          aria-label={open ? "关闭导航菜单" : "打开导航菜单"}
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          <svg
            viewBox="0 0 24 24"
            width="20"
            height="20"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            aria-hidden="true"
          >
            <path d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <span className="mobile-topbar-brand">小码 Xiaoma</span>
      </header>

      {open && (
        <div className="sidebar-overlay" onClick={() => setOpen(false)} aria-hidden="true" />
      )}

      <aside className={`sidebar${open ? " sidebar-open" : ""}`}>
        <div className="sidebar-brand">
          <span className="sidebar-logo">小</span>
          <span>小码 Xiaoma</span>
        </div>
        <nav className="sidebar-nav" aria-label="主导航">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`nav-item${isActive(item.href) ? " active" : ""}`}
              aria-current={isActive(item.href) ? "page" : undefined}
              onClick={() => setOpen(false)}
            >
              {item.icon}
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>
      </aside>
    </>
  );
}
