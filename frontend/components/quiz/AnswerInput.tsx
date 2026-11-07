"use client";

import type { QuizQuestion } from "@/lib/types";

interface AnswerInputProps {
  question: QuizQuestion;
  value: unknown;
  onChange: (value: unknown) => void;
  disabled?: boolean;
}

/** 按题型渲染答题控件（单选/多选/判断/填空/主观题）。 */
export default function AnswerInput({
  question,
  value,
  onChange,
  disabled = false,
}: AnswerInputProps) {
  const name = `question-${question.id}`;

  if (question.question_type === "single_choice") {
    return (
      <div className="answer-options" role="radiogroup" aria-label="选择答案">
        {(question.options ?? []).map((option) => {
          const checked = value === option.key;
          return (
            <label
              key={option.key}
              className={`answer-option${checked ? " answer-option-selected" : ""}`}
            >
              <input
                type="radio"
                name={name}
                value={option.key}
                checked={checked}
                disabled={disabled}
                onChange={() => onChange(option.key)}
              />
              <span className="answer-option-key">{option.key}</span>
              <span>{option.text}</span>
            </label>
          );
        })}
      </div>
    );
  }

  if (question.question_type === "multiple_choice") {
    const selected = Array.isArray(value) ? value.map(String) : [];
    const toggle = (key: string) => {
      const next = selected.includes(key)
        ? selected.filter((item) => item !== key)
        : [...selected, key];
      onChange(next);
    };
    return (
      <div className="answer-options" aria-label="选择多个答案">
        {(question.options ?? []).map((option) => {
          const checked = selected.includes(option.key);
          return (
            <label
              key={option.key}
              className={`answer-option${checked ? " answer-option-selected" : ""}`}
            >
              <input
                type="checkbox"
                name={name}
                value={option.key}
                checked={checked}
                disabled={disabled}
                onChange={() => toggle(option.key)}
              />
              <span className="answer-option-key">{option.key}</span>
              <span>{option.text}</span>
            </label>
          );
        })}
      </div>
    );
  }

  if (question.question_type === "true_false") {
    return (
      <div className="answer-options answer-options-inline" role="radiogroup" aria-label="判断对错">
        {[
          { label: "正确（True）", bool: true },
          { label: "错误（False）", bool: false },
        ].map((item) => (
          <label
            key={String(item.bool)}
            className={`answer-option${value === item.bool ? " answer-option-selected" : ""}`}
          >
            <input
              type="radio"
              name={name}
              checked={value === item.bool}
              disabled={disabled}
              onChange={() => onChange(item.bool)}
            />
            <span>{item.label}</span>
          </label>
        ))}
      </div>
    );
  }

  if (question.question_type === "fill_blank") {
    return (
      <input
        type="text"
        className="form-input answer-text-input"
        value={typeof value === "string" ? value : ""}
        disabled={disabled}
        placeholder="请输入答案"
        aria-label="填空答案"
        onChange={(event) => onChange(event.target.value)}
      />
    );
  }

  const isCodeQuestion =
    question.question_type === "code_analysis" ||
    question.question_type === "code_writing";
  return (
    <textarea
      className={`form-textarea answer-textarea${isCodeQuestion ? " answer-code" : ""}`}
      rows={isCodeQuestion ? 7 : 4}
      value={typeof value === "string" ? value : ""}
      disabled={disabled}
      placeholder={
        isCodeQuestion
          ? "请用文字提交代码或分析过程；小码不会执行你提交的代码"
          : "请用文字作答"
      }
      aria-label="文字答案"
      onChange={(event) => onChange(event.target.value)}
    />
  );
}
