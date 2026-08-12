"use client";

import ReactECharts from "echarts-for-react";
import { cycleHistory, throughputHistory } from "@/lib/fixtures";

export function OperationsChart({ mode = "both" }: { mode?: "both" | "throughput" | "cycle" }) {
  const both = mode === "both";
  const series = [
    ...(mode !== "cycle" ? [{ name:"Throughput", type:"line" as const, smooth:true, data:throughputHistory, lineStyle:{color:"#2dd4bf"}, itemStyle:{color:"#2dd4bf"}, areaStyle:{color:"rgba(45,212,191,.08)"} }] : []),
    ...(mode !== "throughput" ? [{ name:"Cycle time", type:"line" as const, smooth:true, yAxisIndex:both?1:0, data:cycleHistory, lineStyle:{color:"#38bdf8"}, itemStyle:{color:"#38bdf8"} }] : []),
  ];
  return <ReactECharts style={{height:280}} option={{ backgroundColor:"transparent", tooltip:{trigger:"axis"}, legend:{textStyle:{color:"#83a0aa"}}, grid:{left:38,right:both?42:20,top:35,bottom:28}, xAxis:{type:"category",data:["08:00","09:00","10:00","11:00","12:00","13:00"],axisLine:{lineStyle:{color:"#29424c"}},axisLabel:{color:"#6f8992"}}, yAxis:[{type:"value",axisLabel:{color:"#6f8992"},splitLine:{lineStyle:{color:"#142932"}}},...(both?[{type:"value",axisLabel:{color:"#6f8992"},splitLine:{show:false}}]:[])],series}}/>;
}
