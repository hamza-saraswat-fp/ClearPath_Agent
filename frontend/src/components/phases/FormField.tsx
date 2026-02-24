"use client";

import type { FormFieldDefinition, FormFieldValue } from "@/lib/form-schema";

interface FormFieldProps {
  field: FormFieldDefinition;
  value: FormFieldValue;
  onChange: (fieldId: string, value: FormFieldValue) => void;
  highlighted?: boolean;
}

export function FormField({
  field,
  value,
  onChange,
  highlighted = false,
}: FormFieldProps) {
  const wrapperClass = highlighted ? "ring-1 ring-amber-300 rounded-xl" : "";

  return (
    <div className={`space-y-1.5 ${wrapperClass}`}>
      <label className="block text-sm font-medium text-foreground">
        {field.label}
        {field.required && <span className="text-red-400 ml-0.5">*</span>}
      </label>

      {field.type === "text" && (
        <input
          type="text"
          value={(value as string) ?? ""}
          onChange={(e) => onChange(field.id, e.target.value || null)}
          placeholder={field.placeholder}
          className="w-full px-4 py-3 rounded-xl border border-border bg-white text-[15px]
            placeholder:text-muted-light outline-none
            focus:border-accent focus:ring-1 focus:ring-accent/20 transition-all"
        />
      )}

      {field.type === "textarea" && (
        <textarea
          value={(value as string) ?? ""}
          onChange={(e) => onChange(field.id, e.target.value || null)}
          placeholder={field.placeholder}
          className="w-full px-4 py-3 rounded-xl border border-border bg-white text-[15px]
            placeholder:text-muted-light outline-none min-h-[80px] resize-none
            focus:border-accent focus:ring-1 focus:ring-accent/20 transition-all"
        />
      )}

      {field.type === "dropdown" && (
        <select
          value={(value as string) ?? ""}
          onChange={(e) => onChange(field.id, e.target.value || null)}
          className={`
            w-full px-4 py-3 rounded-xl border border-border bg-white text-[15px]
            outline-none transition-all appearance-none
            bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2212%22%20height%3D%2212%22%20fill%3D%22none%22%20stroke%3D%22%236b7280%22%20stroke-width%3D%222%22%3E%3Cpath%20d%3D%22m2%204%204%204%204-4%22%2F%3E%3C%2Fsvg%3E')]
            bg-[length:12px] bg-[right_16px_center] bg-no-repeat
            focus:border-accent focus:ring-1 focus:ring-accent/20
            ${!value ? "text-muted-light" : "text-foreground"}
          `}
        >
          <option value="">Select...</option>
          {field.options?.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      )}

      {field.type === "multi-select" && (
        <div className="flex flex-wrap gap-2">
          {field.options?.map((opt) => {
            const selected = Array.isArray(value) && value.includes(opt.value);
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => {
                  const current = Array.isArray(value) ? value : [];
                  const next = selected
                    ? current.filter((v) => v !== opt.value)
                    : [...current, opt.value];
                  onChange(field.id, next.length > 0 ? next : null);
                }}
                className={`
                  rounded-xl text-sm font-medium px-3 py-2 border transition-all duration-150
                  ${
                    selected
                      ? "border-accent bg-accent-light text-accent"
                      : "border-border bg-white text-foreground hover:border-muted-light"
                  }
                `}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      )}

      {field.type === "toggle" && (
        <div className="flex gap-2">
          {[
            { label: "Yes", val: true },
            { label: "No", val: false },
          ].map((opt) => (
            <button
              key={opt.label}
              type="button"
              onClick={() => onChange(field.id, opt.val)}
              className={`
                flex-1 py-2.5 rounded-xl border text-sm font-medium transition-all duration-150
                ${
                  value === opt.val
                    ? "border-accent bg-accent-light text-accent"
                    : "border-border bg-white text-foreground hover:border-muted-light"
                }
              `}
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}

      {field.type === "checkboxes" && (
        <div className="flex flex-col gap-2">
          {field.options?.map((opt) => {
            const selected = Array.isArray(value) && value.includes(opt.value);
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => {
                  const current = Array.isArray(value) ? value : [];
                  const next = selected
                    ? current.filter((v) => v !== opt.value)
                    : [...current, opt.value];
                  onChange(field.id, next.length > 0 ? next : null);
                }}
                className={`
                  rounded-xl text-sm font-medium px-3 py-2 border text-left transition-all duration-150
                  ${
                    selected
                      ? "border-accent bg-accent-light text-accent"
                      : "border-border bg-white text-foreground hover:border-muted-light"
                  }
                `}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      )}

      {field.helpText && (
        <p className="text-xs text-muted mt-1">{field.helpText}</p>
      )}
    </div>
  );
}
