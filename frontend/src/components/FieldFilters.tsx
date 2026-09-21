import { KNOWN_FIELDS } from "../types";

interface Props {
  value: string | null;
  onChange: (field: string | null) => void;
}

export default function FieldFilters({ value, onChange }: Props) {
  return (
    <div className="field-filters">
      <button className={"chip" + (value === null ? " active" : "")} onClick={() => onChange(null)}>
        All fields
      </button>
      {KNOWN_FIELDS.map((field) => (
        <button
          key={field}
          className={"chip" + (value === field ? " active" : "")}
          onClick={() => onChange(field)}
        >
          {field.replace("_", " ")}
        </button>
      ))}
    </div>
  );
}
