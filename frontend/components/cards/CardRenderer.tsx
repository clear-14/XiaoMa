/**
 * V1.4 批次 4：卡片渲染分发器。
 *
 * 10 类消息类型全覆盖：`text` 由消息气泡的文本通道渲染（不是卡片），
 * 其余 9 类按判别联合 `card.type` 分发到对应组件。
 * 运行时若出现 TS 判别联合之外的类型（历史脏数据 / 未来版本），
 * 统一降级 `error_card`，绝不渲染空白。
 *
 * `renderActions` 是批次 5 的接线插槽：届时按卡片类型注入调用真实业务
 * 接口的按钮。批次 4 不传该回调，因此界面上不会出现任何「假按钮」。
 */

import type { ReactNode } from "react";

import { buildErrorCard, type Card } from "@/lib/cards";

import ErrorCardView from "./ErrorCard";
import LessonCardView from "./LessonCard";
import MistakeCardView from "./MistakeCard";
import PlanCardView from "./PlanCard";
import PlanChangeCardView from "./PlanChangeCard";
import ProgressCardView from "./ProgressCard";
import QuizCardView from "./QuizCard";
import QuizResultCardView from "./QuizResultCard";
import TaskCardView from "./TaskCard";

export interface CardRendererProps {
  cards: Card[];
  /** 批次 5 注入：按卡片类型返回真实业务按钮，未注入时不渲染按钮。 */
  renderActions?: (card: Card) => ReactNode;
}

function CardView({
  card,
  actions,
  index,
}: {
  card: Card;
  actions?: ReactNode;
  index: number;
}) {
  switch (card.type) {
    case "task_card":
      return <TaskCardView card={card} actions={actions} index={index} />;
    case "lesson_card":
      return <LessonCardView card={card} actions={actions} index={index} />;
    case "quiz_card":
      return <QuizCardView card={card} actions={actions} index={index} />;
    case "quiz_result_card":
      return <QuizResultCardView card={card} actions={actions} index={index} />;
    case "mistake_card":
      return <MistakeCardView card={card} actions={actions} index={index} />;
    case "plan_card":
      return <PlanCardView card={card} actions={actions} index={index} />;
    case "plan_change_card":
      return (
        <PlanChangeCardView card={card} actions={actions} index={index} />
      );
    case "progress_card":
      return <ProgressCardView card={card} actions={actions} index={index} />;
    case "error_card":
      return <ErrorCardView card={card} actions={actions} index={index} />;
    default:
      // 历史脏数据或未按协议构造的对象：明确降级，不静默丢弃。
      return <ErrorCardView card={buildErrorCard("不支持的卡片类型")} index={index} />;
  }
}

export default function CardRenderer({
  cards,
  renderActions,
}: CardRendererProps) {
  if (!cards || cards.length === 0) {
    return null;
  }
  return (
    <div className="win-card-stack" role="list" aria-label="结构化业务卡片">
      {cards.map((card, index) => (
        <div
          className="win-card-stack-item"
          role="listitem"
          key={`${card.type}-${index}`}
        >
          <CardView
            card={card}
            index={index}
            actions={renderActions?.(card)}
          />
        </div>
      ))}
      <p className="win-card-stack-source">
        卡片数据来自后端业务结果，不由对话内容推断。
      </p>
    </div>
  );
}
