interface PromptInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
}

const defaultPlaceholder =
  'Design a modern 3BHK house on a 40x60 plot with parking and open kitchen.';

export default function PromptInput({
  value,
  onChange,
  placeholder = defaultPlaceholder,
  disabled = false,
}: PromptInputProps) {
  return (
    <textarea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      disabled={disabled}
      rows={5}
      className="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-gray-900 placeholder-gray-400 shadow-sm transition focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 disabled:cursor-not-allowed disabled:bg-gray-50 disabled:text-gray-500"
    />
  );
}
