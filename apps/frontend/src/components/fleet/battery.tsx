export function Battery({ value }: { value: number }) {
  const rounded = Math.round(value); const low = value < 20;
  return <div className={`battery ${low ? "low" : ""}`} aria-label={low ? "Low battery" : "Battery level"}><div className="battery-track"><div className="battery-fill" style={{ width: `${value}%` }}/></div><span>{rounded}%</span></div>;
}
