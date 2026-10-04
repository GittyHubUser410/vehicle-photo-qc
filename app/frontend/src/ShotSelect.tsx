import { useRef, useState } from "react";
import { Check, ChevronDown } from "lucide-react";
import { label } from "./api";
import { Modal } from "./ui";

export function ShotSelect({
  value,
  options,
  onChange,
  disabled = false,
  title = "Shot type",
}: {
  value: string;
  options: string[];
  onChange: (value: string) => void;
  disabled?: boolean;
  title?: string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const search = useRef<HTMLInputElement>(null);
  const normalize = (text: string) =>
    text.toLowerCase().replace(/[’']/g, "").replace(/¾/g, "3/4");
  const choices = [
    ...new Set(options.includes(value) ? options : [value, ...options]),
  ];
  const filtered = choices.filter((key) =>
    normalize(label(key)).includes(normalize(query.trim())),
  );
  const close = () => {
    search.current?.blur();
    setOpen(false);
  };
  return (
    <div className="field shot-select">
      <span>{title}</span>
      <button
        type="button"
        className="shot-trigger"
        aria-label={title}
        aria-haspopup="dialog"
        disabled={disabled}
        onClick={() => {
          setQuery("");
          setOpen(true);
        }}
      >
        {label(value)}
        <ChevronDown size={16} />
      </button>
      {open && (
        <Modal title={`Choose ${title.toLowerCase()}`} onClose={close}>
          <input
            ref={search}
            className="shot-search"
            aria-label="Search shot types"
            placeholder="Search shot types…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoComplete="off"
            enterKeyHint="done"
            onKeyDown={(e) => {
              if (e.key === "Enter" && filtered.length) {
                e.preventDefault();
                onChange(filtered[0]);
                close();
              }
            }}
          />
          <div className="shot-options">
            {filtered.map((key) => (
              <button
                type="button"
                key={key}
                aria-pressed={key === value}
                onClick={() => {
                  onChange(key);
                  close();
                }}
              >
                {label(key)}
                {key === value && <Check size={16} />}
              </button>
            ))}
            {!filtered.length && <p>No matching shot types.</p>}
          </div>
        </Modal>
      )}
    </div>
  );
}
