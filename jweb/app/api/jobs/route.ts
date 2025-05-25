import { NextResponse } from "next/server"
import { exec } from "child_process"
import { promisify } from "util"

const execAsync = promisify(exec)

export async function GET() {
  try {
    // Execute the jrun viz --mode json command
    const { stdout, stderr } = await execAsync("jrun viz --mode json")

    if (stderr) {
      console.error("jrun stderr:", stderr)
    }

    // Parse the JSON output
    const jobsData = JSON.parse(stdout)

    return NextResponse.json(jobsData)
  } catch (error) {
    console.error("Error executing jrun command:", error)

    // Return a fallback response with empty data
    return NextResponse.json(
      {
        jobs: [],
        stats: {
          completed: 0,
          running: 0,
          pending: 0,
          blocked: 0,
          cancelled: 0,
          timeout: 0,
          failed: 0,
          total: 0,
        },
        count: 0,
      },
      { status: 500 },
    )
  }
}
