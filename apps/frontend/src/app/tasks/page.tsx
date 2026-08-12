import { TaskTable } from "@/components/tasks/task-table";
export default function TasksPage(){return <><header className="page-head"><div><h2>Battery delivery tasks</h2><p>Assignments and lifecycle state are owned by the backend.</p></div></header><section className="panel"><div className="panel-head"><h3>Current tasks</h3><span>DELIVER_BATTERY</span></div><TaskTable/></section></>}
