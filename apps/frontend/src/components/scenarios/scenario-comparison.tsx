import type { ScenarioMetrics, ScenarioStatus } from "@/schemas/scenario";

type MetricKey = keyof Pick<
  ScenarioMetrics,
  | "throughput_per_hour"
  | "average_cycle_time"
  | "average_waiting_time"
  | "completion_rate"
  | "unfinished_tasks"
>;

interface MetricRow {
  key: MetricKey;
  label: string;
  unit: string;
  higherIsBetter: boolean;
  format: (value: number) => string;
}

const number = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });

const rows: MetricRow[] = [
  {
    key: "throughput_per_hour",
    label: "Throughput",
    unit: "tasks/h",
    higherIsBetter: true,
    format: (value) => number.format(value),
  },
  {
    key: "average_cycle_time",
    label: "Average cycle time",
    unit: "s",
    higherIsBetter: false,
    format: (value) => number.format(value),
  },
  {
    key: "average_waiting_time",
    label: "Average waiting time",
    unit: "s",
    higherIsBetter: false,
    format: (value) => number.format(value),
  },
  {
    key: "completion_rate",
    label: "Completion rate",
    unit: "",
    higherIsBetter: true,
    format: (value) => `${number.format(value * 100)}%`,
  },
  {
    key: "unfinished_tasks",
    label: "Backlog",
    unit: "tasks",
    higherIsBetter: false,
    format: (value) => number.format(value),
  },
];

function assessment(candidate: number, baseline: number, higherIsBetter: boolean) {
  if (candidate === baseline) return { label: "Same", className: "same" };
  const better = higherIsBetter ? candidate > baseline : candidate < baseline;
  return better
    ? { label: "Better", className: "better" }
    : { label: "Worse", className: "worse" };
}

export function ScenarioStatusBadge({ status }: { status: ScenarioStatus }) {
  return <span className={`scenario-status ${status}`}>{status}</span>;
}

export function ScenarioComparison({
  baseline,
  candidate,
}: {
  baseline: ScenarioMetrics;
  candidate: ScenarioMetrics;
}) {
  return (
    <div className="table-wrap">
      <table className="data-table comparison-table">
        <thead>
          <tr>
            <th>Metric</th>
            <th>Baseline</th>
            <th>Candidate</th>
            <th>Result</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const baselineValue = baseline[row.key];
            const candidateValue = candidate[row.key];
            const result = assessment(candidateValue, baselineValue, row.higherIsBetter);
            return (
              <tr key={row.key}>
                <td>{row.label}</td>
                <td>{row.format(baselineValue)} {row.unit}</td>
                <td>{row.format(candidateValue)} {row.unit}</td>
                <td><span className={`comparison-result ${result.className}`}>{result.label}</span></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
