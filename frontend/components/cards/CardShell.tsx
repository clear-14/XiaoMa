/**
 * V1.4 批次 4：卡片统一骨架与信息行原语。
 *
 * 视觉方向沿用批次 3 冻结的 Brutally minimal：暖白表面、发丝分隔线、
 * 等宽短码竖标、刻度式 label/value 行；不引入新的字体或强调色。
 * 九类卡片共用骨架，但各自的内容构成不同（刻度条 / 代码块 / 题目列表 /
 * 前后差异对照 / 解析列表），避免「一模一样的圆角卡片」这一反模式。
 */

import type { CSSProperties, ReactNode } from "react";

import { CARD_TYPE_CODES, CARD_TYPE_LABELS, type CardType } from "@/lib/cards";

export interface CardFact {
  label: string;
  value: ReactNode;
}

/** 刻度式信息行：label / value 两列，发丝线分隔，数值用等宽数字。 */
export function CardFacts({ items }: { items: CardFact[] }) {
  if (items.length === 0) {
    return null;
  }
  return (
    <dl className="win-card-facts">
      {items.map((item, index) => (
        <div className="win-card-fact" key={`${item.label}-${index}`}>
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

/** 卡片内次级区块，用于把长内容（示例、解析、题目）与信息行分开。 */
export function CardSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="win-card-section">
      <h4 className="win-card-section-title">{title}</h4>
      <div className="win-card-section-body">{children}</div>
    </section>
  );
}

/** 可选增强字段的统一占位：没有数据就明确写「未提供」，不编造内容。 */
export const NOT_PROVIDED = "—";

export interface CardShellProps {
  type: CardType;
  title: string;
  meta?: string | null;
  /** 批次 5 注入真实业务按钮；批次 4 不渲染任何假按钮。 */
  actions?: ReactNode;
  children: ReactNode;
  /** 同一条消息内多张卡片的错峰入场序号（80ms 递进，最多 5 组）。 */
  index?: number;
  tone?: "default" | "danger";
}

export default function CardShell({
  type,
  title,
  meta,
  actions,
  children,
  index = 0,
  tone = "default",
}: CardShellProps) {
  const delay = Math.min(Math.max(index, 0), 4) * 80;
  const style: CSSProperties = { animationDelay: `${delay}ms` };
  return (
    <section
      className={`win-card${tone === "danger" ? " win-card-danger" : ""}`}
      role="group"
      aria-label={`${CARD_TYPE_LABELS[type]}卡片`}
      data-card-type={type}
      style={style}
    >
      <div className="win-card-rail" aria-hidden="true">
        <span className="win-card-rail-code">{CARD_TYPE_CODES[type]}</span>
      </div>
      <div className="win-card-body">
        <header className="win-card-head">
          <span className="win-card-type">{CARD_TYPE_LABELS[type]}</span>
          {meta ? <span className="win-card-meta">{meta}</span> : null}
        </header>
        <h3 className="win-card-title">{title}</h3>
        <div className="win-card-content">{children}</div>
        {actions ? <div className="win-card-actions">{actions}</div> : null}
      </div>
    </section>
  );
}
