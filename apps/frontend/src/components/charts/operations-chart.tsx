"use client";

import ReactECharts from "echarts-for-react";
import { usesMockData } from "@/lib/env";
import { cycleHistory, throughputHistory } from "@/lib/fixtures";
import { useFactoryStore } from "@/stores/factory-store";

export const OPERATIONS_TREND_LIVE_LABEL = "Live · 5 s sampling · 5 min window";

type TimeValue = [timestamp: number, value: number];

export function OperationsChart({ mode = "both" }: { mode?: "both" | "throughput" | "cycle" }) {
  const metricsHistory = useFactoryStore((state) => state.metricsHistory);
  const both = mode === "both";
  const throughputData: number[] | TimeValue[] = usesMockData
    ? throughputHistory
    : metricsHistory.map((sample): TimeValue => [
        sample.timestamp,
        sample.throughput_per_hour,
      ]);
  const cycleData: number[] | TimeValue[] = usesMockData
    ? cycleHistory
    : metricsHistory.map((sample): TimeValue => [
        sample.timestamp,
        sample.average_cycle_time_seconds,
      ]);

  if (!usesMockData && metricsHistory.length === 0) {
    return <div className="empty">Waiting for the first metrics update from WebSocket…</div>;
  }

  const axisStyle = {
    axisLine: { lineStyle: { color: "#29424c" } },
    axisLabel: { color: "#6f8992", hideOverlap: true },
  };
  const xAxis = usesMockData
    ? {
        type: "category" as const,
        data: ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00"],
        ...axisStyle,
      }
    : {
        type: "time" as const,
        ...axisStyle,
        axisLabel: {
          ...axisStyle.axisLabel,
          formatter: (value: number) => new Date(value).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          }),
        },
      };
  const series = [
    ...(mode !== "cycle" ? [{ name:"Throughput · tasks/h", type:"line" as const, smooth:true, showSymbol:false, symbol:"none", sampling:"lttb", data:throughputData, lineStyle:{color:"#2dd4bf"}, itemStyle:{color:"#2dd4bf"}, areaStyle:{color:"rgba(45,212,191,.08)"} }] : []),
    ...(mode !== "throughput" ? [{ name:"Cycle time · s", type:"line" as const, smooth:true, showSymbol:false, symbol:"none", sampling:"lttb", yAxisIndex:both?1:0, data:cycleData, lineStyle:{color:"#38bdf8"}, itemStyle:{color:"#38bdf8"} }] : []),
  ];
  return <ReactECharts lazyUpdate style={{height:280}} option={{ backgroundColor:"transparent", animationDuration:200, animationDurationUpdate:150, tooltip:{trigger:"axis",axisPointer:{type:"cross"}}, legend:{textStyle:{color:"#83a0aa"}}, grid:{left:48,right:both?52:20,top:35,bottom:32}, xAxis, yAxis:[{type:"value",name:mode==="cycle"?"seconds":"tasks/h",nameTextStyle:{color:"#6f8992"},axisLabel:{color:"#6f8992"},splitLine:{lineStyle:{color:"#142932"}}},...(both?[{type:"value",name:"seconds",nameTextStyle:{color:"#6f8992"},axisLabel:{color:"#6f8992"},splitLine:{show:false}}]:[])],series }}/>
}
