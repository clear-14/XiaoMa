/** 知识点讲解卡片：PRD §5.1，讲解正文 + 可选示例与要点。 */

import type { ReactNode } from "react";

import {
  readString,
  readStringArray,
  type LessonCard,
} from "@/lib/cards";

import CardShell, { CardFacts, CardSection } from "./CardShell";

export default function LessonCard({
  card,
  actions,
  index,
}: {
  card: LessonCard;
  actions?: ReactNode;
  index?: number;
}) {
  const payload = card.payload;
  const chapter = readString(payload, "chapter_title");
  const exampleCode = readString(payload, "example_code");
  const exampleOutput = readString(payload, "example_output");
  const keyPoints = readStringArray(payload, "key_points");

  return (
    <CardShell
      type="lesson_card"
      title={payload.knowledge_point_name}
      meta={payload.knowledge_point_code}
      actions={actions}
      index={index}
    >
      <CardFacts
        items={chapter ? [{ label: "所属章节", value: chapter }] : []}
      />
      <p className="win-card-prose">{payload.explanation}</p>
      {keyPoints.length > 0 ? (
        <CardSection title="本节要点">
          <ul className="win-card-list">
            {keyPoints.map((point, i) => (
              <li key={`${i}-${point}`}>{point}</li>
            ))}
          </ul>
        </CardSection>
      ) : null}
      {exampleCode ? (
        <CardSection title="示例代码">
          <pre className="win-card-code">
            <code>{exampleCode}</code>
          </pre>
        </CardSection>
      ) : null}
      {exampleOutput ? (
        <CardSection title="示例输出">
          <pre className="win-card-code win-card-code-output">
            <code>{exampleOutput}</code>
          </pre>
        </CardSection>
      ) : null}
    </CardShell>
  );
}
