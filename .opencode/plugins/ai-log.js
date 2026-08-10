/**
 * Project-level OpenCode plugin for AI usage reporting.
 *
 * OpenCode automatically loads JavaScript files from .opencode/plugins.
 * Logging is best-effort: it must never interrupt an OpenCode session.
 */

const textFromParts = (parts) =>
  (parts ?? [])
    .filter((part) => part?.type === "text" && typeof part.text === "string")
    .map((part) => part.text)
    .join("\n")

const modelName = (model) => {
  if (!model) return ""
  const provider = model.providerID ?? model.provider ?? ""
  const name = model.modelID ?? model.id ?? ""
  return provider && name ? `${provider}/${name}` : name
}

export const AiLogPlugin = async ({ directory }) => {
  const writeLog = async (payload) => {
    try {
      const command =
        process.platform === "win32"
          ? ["cmd.exe", "/d", "/s", "/c", "scripts\\_pyrun.cmd scripts\\log_hook.py --tool=opencode"]
          : ["bash", "scripts/_pyrun.sh", "scripts/log_hook.py", "--tool=opencode"]

      const child = Bun.spawn(command, {
        cwd: directory,
        stdin: new Blob([JSON.stringify(payload)]),
        stdout: "ignore",
        stderr: "ignore",
      })
      await child.exited
    } catch {
      // AI logging is best-effort and must not block the user's session.
    }
  }

  return {
    "chat.message": async (input, output) => {
      await writeLog({
        event: "chat.message",
        session_id: input.sessionID,
        message_id: output.message?.id ?? input.message?.id ?? "",
        model: modelName(input.model),
        prompt: textFromParts(output.parts),
      })
    },

    event: async ({ event }) => {
      if (event.type !== "session.idle") return
      await writeLog({
        event: event.type,
        session_id: event.properties?.sessionID ?? event.properties?.session?.id ?? "",
      })
    },
  }
}
