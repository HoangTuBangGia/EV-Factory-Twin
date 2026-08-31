"use client";

import { useAuth } from "@/components/auth/auth-provider";
import { CreateTaskForm } from "@/components/tasks/create-task-form";
import { TaskTable } from "@/components/tasks/task-table";

export default function TasksPage() {
  const { user } = useAuth();
  return <>
    <header className="page-head"><div><h2>Battery delivery tasks</h2><p>ROS Task Manager owns assignment and execution lifecycle.</p></div></header>
    {user?.role === "MONITOR" && <CreateTaskForm/>}
    <section className="panel"><div className="panel-head"><h3>Current tasks</h3><span>DELIVER_BATTERY</span></div><TaskTable/></section>
  </>;
}
