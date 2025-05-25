"use client"

import type React from "react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Terminal,
  Clock,
  CheckCircle,
  XCircle,
  Pause,
  Users,
  GitBranch,
  Search,
  Filter,
  Cpu,
  HardDrive,
  Moon,
  Sun,
} from "lucide-react"
import { useMemo, useState, useRef, useEffect } from "react"
import { Progress } from "@/components/ui/progress"

interface JobStats {
  gpu_memory_used_mb?: number
  gpu_memory_total_mb?: number
  gpu_count?: number
}

interface Job {
  job_id: number
  command: string
  preamble: string
  group_name: string
  depends_on: string[]
  status: string
  inactive_deps: string[]
  stats?: JobStats
}

const DUMMY_JOBS: Job[] = [
  {
    job_id: 789012,
    command: "jrun analyze --input dataset.csv --output results/",
    preamble: "#!/bin/bash\n#SBATCH --job-name=analyze\n#SBATCH --time=01:00:00",
    group_name: "data_prep",
    depends_on: [],
    status: "COMPLETED",
    inactive_deps: [],
  },
  {
    job_id: 123456,
    command: "jrun viz --type scatter --input results/analysis.json",
    preamble: "#!/bin/bash\n#SBATCH --job-name=viz-scatter\n#SBATCH --gres=gpu:1",
    group_name: "visualization",
    depends_on: ["789012"],
    status: "RUNNING",
    inactive_deps: [],
    stats: {
      gpu_memory_used_mb: 8192,
      gpu_memory_total_mb: 12288,
      gpu_count: 1,
    },
  },
  {
    job_id: 123457,
    command: "jrun viz --type histogram --input results/analysis.json",
    preamble: "#!/bin/bash\n#SBATCH --job-name=viz-histogram\n#SBATCH --gres=gpu:1",
    group_name: "visualization",
    depends_on: ["789012"],
    status: "COMPLETED",
    inactive_deps: [],
  },
  {
    job_id: 123458,
    command: "jrun viz --type boxplot --input results/analysis.json",
    preamble: "#!/bin/bash\n#SBATCH --job-name=viz-boxplot\n#SBATCH --gres=gpu:1",
    group_name: "visualization",
    depends_on: ["789012"],
    status: "PENDING",
    inactive_deps: [],
  },
  {
    job_id: 345678,
    command: "jrun preprocess --input data.csv --normalize --scale",
    preamble: "#!/bin/bash\n#SBATCH --job-name=preprocess\n#SBATCH --time=02:00:00",
    group_name: "preprocessing",
    depends_on: ["789012"],
    status: "COMPLETED",
    inactive_deps: [],
  },
  {
    job_id: 901234,
    command: "jrun model_training --model linear --epochs 100",
    preamble: "#!/bin/bash\n#SBATCH --job-name=train-linear\n#SBATCH --gres=gpu:2",
    group_name: "ml_pipeline",
    depends_on: ["345678"],
    status: "RUNNING",
    inactive_deps: [],
    stats: {
      gpu_memory_used_mb: 20480,
      gpu_memory_total_mb: 24576,
      gpu_count: 2,
    },
  },
  {
    job_id: 901235,
    command: "jrun model_training --model random_forest --trees 500",
    preamble: "#!/bin/bash\n#SBATCH --job-name=train-rf\n#SBATCH --time=04:00:00",
    group_name: "ml_pipeline",
    depends_on: ["345678"],
    status: "PENDING",
    inactive_deps: [],
  },
  {
    job_id: 901236,
    command: "jrun model_training --model neural_net --layers 5",
    preamble: "#!/bin/bash\n#SBATCH --job-name=train-nn\n#SBATCH --gres=gpu:4",
    group_name: "ml_pipeline",
    depends_on: ["345678"],
    status: "FAILED",
    inactive_deps: [],
  },
  {
    job_id: 567890,
    command: "jrun validation --cross-validate --folds 5",
    preamble: "#!/bin/bash\n#SBATCH --job-name=validation-cv\n#SBATCH --time=01:30:00",
    group_name: "validation",
    depends_on: ["123456", "123457", "345678"],
    status: "PENDING",
    inactive_deps: [],
  },
  {
    job_id: 567891,
    command: "jrun validation --holdout --split 0.2",
    preamble: "#!/bin/bash\n#SBATCH --job-name=validation-holdout\n#SBATCH --time=01:00:00",
    group_name: "validation",
    depends_on: ["123456", "123457", "345678"],
    status: "PENDING",
    inactive_deps: [],
  },
  {
    job_id: 111222,
    command: "jrun report --format pdf --template executive",
    preamble: "#!/bin/bash\n#SBATCH --job-name=report-pdf\n#SBATCH --time=00:30:00",
    group_name: "reporting",
    depends_on: ["567890", "567891"],
    status: "PENDING",
    inactive_deps: [],
  },
  {
    job_id: 111223,
    command: "jrun report --format html --interactive",
    preamble: "#!/bin/bash\n#SBATCH --job-name=report-html\n#SBATCH --time=00:45:00",
    group_name: "reporting",
    depends_on: ["567890", "567891"],
    status: "PENDING",
    inactive_deps: [],
  },
  {
    job_id: 111224,
    command: "jrun report --format json --detailed",
    preamble: "#!/bin/bash\n#SBATCH --job-name=report-json\n#SBATCH --time=00:15:00",
    group_name: "reporting",
    depends_on: ["567890", "567891"],
    status: "PENDING",
    inactive_deps: [],
  },
]

function getStatusIcon(status: string) {
  switch (status.toLowerCase()) {
    case "running":
      return <Clock className="w-4 h-4" />
    case "completed":
      return <CheckCircle className="w-4 h-4" />
    case "failed":
      return <XCircle className="w-4 h-4" />
    case "pending":
      return <Pause className="w-4 h-4" />
    default:
      return <Clock className="w-4 h-4" />
  }
}

function getStatusVariant(status: string): "default" | "secondary" | "destructive" | "outline" {
  switch (status.toLowerCase()) {
    case "running":
      return "default"
    case "completed":
      return "secondary"
    case "failed":
      return "destructive"
    case "pending":
      return "outline"
    default:
      return "outline"
  }
}

function getStatusColor(status: string) {
  switch (status.toLowerCase()) {
    case "running":
      return "#3b82f6"
    case "completed":
      return "#10b981"
    case "failed":
      return "#ef4444"
    case "pending":
      return "#f59e0b"
    default:
      return "#6b7280"
  }
}

function getGroupStatus(jobs: Job[]): string {
  if (jobs.every((job) => job.status === "COMPLETED")) return "COMPLETED"
  if (jobs.some((job) => job.status === "FAILED")) return "FAILED"
  if (jobs.some((job) => job.status === "RUNNING")) return "RUNNING"
  return "PENDING"
}

function getGroupProgress(jobs: Job[]): number {
  const completed = jobs.filter((job) => job.status === "COMPLETED").length
  return (completed / jobs.length) * 100
}

interface JobGroup {
  id: string
  jobs: Job[]
  parents: Set<string>
  children: Set<string>
  x: number
  y: number
  level: number
}

interface GraphEdge {
  from: string
  to: string
}

interface TooltipData {
  job: Job
  x: number
  y: number
  visible: boolean
}

function JobTooltip({ tooltip }: { tooltip: TooltipData }) {
  if (!tooltip.visible) return null

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}m ${secs}s`
  }

  return (
    <div
      className="absolute z-50 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3 max-w-xs"
      style={{ left: tooltip.x + 10, top: tooltip.y - 10 }}
    >
      <div className="space-y-2">
        <div className="font-semibold text-gray-900 dark:text-white">Job #{tooltip.job.job_id}</div>
        <div className="text-sm text-gray-600 dark:text-gray-400">{tooltip.job.command}</div>
        <div className="flex items-center gap-2">
          <Badge variant={getStatusVariant(tooltip.job.status)} className="text-xs">
            {tooltip.job.status}
          </Badge>
        </div>
        {tooltip.job.status === "RUNNING" && tooltip.job.stats && (
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs">
              <HardDrive className="w-3 h-3" />
              <span>
                GPU Memory: {tooltip.job.stats.gpu_memory_used_mb}MB / {tooltip.job.stats.gpu_memory_total_mb}MB
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <Cpu className="w-3 h-3" />
              <span>GPUs: {tooltip.job.stats.gpu_count}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function DependencyGraph({ jobs }: { jobs: Job[] }) {
  const [expandedGroup, setExpandedGroup] = useState<JobGroup | null>(null)
  const [tooltip, setTooltip] = useState<TooltipData>({ job: jobs[0], x: 0, y: 0, visible: false })
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [isPanning, setIsPanning] = useState(false)
  const [highlightedChain, setHighlightedChain] = useState<Set<string>>(new Set())
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; jobId: string; visible: boolean }>({
    x: 0,
    y: 0,
    jobId: "",
    visible: false,
  })
  const svgRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    const handleEscapeKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setExpandedGroup(null)
      }
    }

    document.addEventListener("keydown", handleEscapeKey)
    return () => document.removeEventListener("keydown", handleEscapeKey)
  }, [])

  const { groups, edges, individualNodes } = useMemo(() => {
    // Build parent-to-child mapping
    const parentToChildMap = new Map<string, Set<string>>()
    jobs.forEach((job) => {
      const jobId = job.job_id.toString()
      job.depends_on.forEach((depId) => {
        if (!parentToChildMap.has(depId)) {
          parentToChildMap.set(depId, new Set())
        }
        parentToChildMap.get(depId)!.add(jobId)
      })
    })

    // Group jobs by their dependency signature
    const groupMap = new Map<string, Job[]>()
    jobs.forEach((job) => {
      const jobId = job.job_id.toString()
      const parents = new Set(job.depends_on)
      const children = parentToChildMap.get(jobId) || new Set()

      const parentsKey = Array.from(parents).sort().join(",")
      const childrenKey = Array.from(children).sort().join(",")
      const signature = `${parentsKey}|${childrenKey}`

      if (!groupMap.has(signature)) {
        groupMap.set(signature, [])
      }
      groupMap.get(signature)!.push(job)
    })

    // Convert groups to JobGroup objects
    const groups: JobGroup[] = []
    let groupIndex = 0

    groupMap.forEach((groupJobs) => {
      const groupId = `group_${groupIndex++}`
      const firstJob = groupJobs[0]
      const parents = new Set(firstJob.depends_on)
      const children = parentToChildMap.get(firstJob.job_id.toString()) || new Set()

      groups.push({
        id: groupId,
        jobs: groupJobs,
        parents,
        children,
        x: 0,
        y: 0,
        level: 0,
      })
    })

    // Calculate levels and positions
    const levels = new Map<string, number>()
    const visited = new Set<string>()

    function calculateLevel(groupId: string): number {
      if (levels.has(groupId)) return levels.get(groupId)!
      if (visited.has(groupId)) return 0

      visited.add(groupId)
      const group = groups.find((g) => g.id === groupId)!
      const parentGroups = Array.from(group.parents)
        .map((parentId) => groups.find((g) => g.jobs.some((j) => j.job_id.toString() === parentId)))
        .filter(Boolean)

      const maxParentLevel =
        parentGroups.length > 0 ? Math.max(...parentGroups.map((pg) => calculateLevel(pg!.id))) : -1

      const level = maxParentLevel + 1
      levels.set(groupId, level)
      group.level = level
      visited.delete(groupId)
      return level
    }

    groups.forEach((group) => calculateLevel(group.id))

    // Position groups and individual nodes
    const levelGroups = new Map<number, JobGroup[]>()
    groups.forEach((group) => {
      if (!levelGroups.has(group.level)) {
        levelGroups.set(group.level, [])
      }
      levelGroups.get(group.level)!.push(group)
    })

    // Remove individualNodes logic since we're not ungrouping in-place anymore
    const individualNodes: Array<Job & { x: number; y: number; groupId: string }> = []

    const levelSpacing = 200
    const nodeSpacing = 80
    levelGroups.forEach((items, level) => {
      items.forEach((item, index) => {
        const totalItems = items.length
        const startY = (-(totalItems - 1) * nodeSpacing) / 2

        const baseX = level * levelSpacing + 80
        const baseY = startY + index * nodeSpacing + 250

        // It's a group
        item.x = baseX
        item.y = baseY
      })
    })

    // Create edges
    const finalEdges: GraphEdge[] = []
    groups.forEach((group) => {
      Array.from(group.parents).forEach((parentId) => {
        const parentGroup = groups.find((g) => g.jobs.some((j) => j.job_id.toString() === parentId))
        if (parentGroup && parentGroup.id !== group.id) {
          finalEdges.push({ from: parentGroup.id, to: group.id })
        }
      })
    })

    return { groups, edges: finalEdges, individualNodes }
  }, [jobs])

  // Dependency chain highlighting
  const findDependencyChain = (nodeId: string): Set<string> => {
    const chain = new Set<string>()
    const visited = new Set<string>()

    function traverse(id: string) {
      if (visited.has(id)) return
      visited.add(id)
      chain.add(id)

      // Find job by ID
      const job = jobs.find((j) => j.job_id.toString() === id)
      if (job) {
        // Add parents
        job.depends_on.forEach((parentId) => traverse(parentId))

        // Add children
        jobs.forEach((j) => {
          if (j.depends_on.includes(id)) {
            traverse(j.job_id.toString())
          }
        })
      }
    }

    traverse(nodeId)
    return chain
  }

  // Mouse event handlers
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault()
    const delta = e.deltaY > 0 ? 0.9 : 1.1
    const newZoom = Math.max(0.1, Math.min(3, zoom * delta))
    setZoom(newZoom)
  }

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button === 0) {
      setIsPanning(true)
    }
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isPanning) {
      setPan((prev) => ({
        x: prev.x + e.movementX,
        y: prev.y + e.movementY,
      }))
    }
  }

  const handleMouseUp = () => {
    setIsPanning(false)
  }

  const handleNodeMouseEnter = (job: Job, nodeId: string, event: React.MouseEvent) => {
    const rect = (event.target as Element).getBoundingClientRect()
    setTooltip({
      job,
      x: rect.right,
      y: rect.top,
      visible: true,
    })

    // Highlight dependency chain
    const chain = findDependencyChain(job.job_id.toString())
    setHighlightedChain(chain)
  }

  const handleNodeMouseLeave = () => {
    setTooltip((prev) => ({ ...prev, visible: false }))
    setHighlightedChain(new Set())
  }

  const handleContextMenu = (e: React.MouseEvent, jobId: string) => {
    e.preventDefault()
    setContextMenu({
      x: e.clientX,
      y: e.clientY,
      jobId,
      visible: true,
    })
  }

  const handleContextAction = (action: string, jobId: string) => {
    console.log(`${action} job ${jobId}`)
    setContextMenu((prev) => ({ ...prev, visible: false }))
    // Implement actual actions here
  }

  // Close context menu on click outside
  useEffect(() => {
    const handleClickOutside = () => setContextMenu((prev) => ({ ...prev, visible: false }))
    document.addEventListener("click", handleClickOutside)
    return () => document.removeEventListener("click", handleClickOutside)
  }, [])

  const svgWidth = Math.max(
    1000,
    (Math.max(...groups.map((g) => g.level), ...individualNodes.map((n) => Math.floor(n.x / 200))) + 1) * 200 + 160,
  )
  const svgHeight = Math.max(600, Math.max(...groups.map((g) => g.y), ...individualNodes.map((n) => n.y)) + 150)

  const openGroupModal = (group: JobGroup) => {
    setExpandedGroup(group)
  }

  const closeGroupModal = () => {
    setExpandedGroup(null)
  }

  return (
    <div className="w-full overflow-hidden relative">
      {/* Zoom Controls */}
      <div className="absolute top-4 right-4 z-10 flex flex-col gap-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-2 shadow-lg">
        <button
          onClick={() => setZoom((prev) => Math.min(3, prev * 1.2))}
          className="px-2 py-1 text-sm bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded text-gray-900 dark:text-gray-100"
        >
          +
        </button>
        <span className="text-xs text-center text-gray-900 dark:text-gray-100">{Math.round(zoom * 100)}%</span>
        <button
          onClick={() => setZoom((prev) => Math.max(0.1, prev * 0.8))}
          className="px-2 py-1 text-sm bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded text-gray-900 dark:text-gray-100"
        >
          -
        </button>
        <button
          onClick={() => {
            setZoom(1)
            setPan({ x: 0, y: 0 })
          }}
          className="px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900 hover:bg-blue-200 dark:hover:bg-blue-800 rounded text-gray-900 dark:text-gray-100"
        >
          Reset
        </button>
      </div>

      {/* Context Menu */}
      {contextMenu.visible && (
        <div
          className="absolute z-50 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg py-1"
          style={{ left: contextMenu.x, top: contextMenu.y }}
        >
          <button
            onClick={() => handleContextAction("view-logs", contextMenu.jobId)}
            className="block w-full px-4 py-2 text-sm text-left hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-900 dark:text-gray-100"
          >
            View Logs
          </button>
          <button
            onClick={() => handleContextAction("restart", contextMenu.jobId)}
            className="block w-full px-4 py-2 text-sm text-left hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-900 dark:text-gray-100"
          >
            Restart Job
          </button>
          <button
            onClick={() => handleContextAction("cancel", contextMenu.jobId)}
            className="block w-full px-4 py-2 text-sm text-left hover:bg-gray-100 dark:hover:bg-gray-700 text-red-600 dark:text-red-400"
          >
            Cancel Job
          </button>
          <button
            onClick={() => handleContextAction("clone", contextMenu.jobId)}
            className="block w-full px-4 py-2 text-sm text-left hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-900 dark:text-gray-100"
          >
            Clone Job
          </button>
        </div>
      )}

      <svg
        ref={svgRef}
        width="100%"
        height="600"
        className="border rounded-lg bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 cursor-grab"
        style={{ cursor: isPanning ? "grabbing" : "grab" }}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
          {/* Edges */}
          {edges.map((edge, index) => {
            const fromGroup = groups.find((g) => g.id === edge.from)
            const toGroup = groups.find((g) => g.id === edge.to)
            if (!fromGroup || !toGroup) return null

            const isHighlighted =
              highlightedChain.has(fromGroup.jobs[0]?.job_id.toString()) &&
              highlightedChain.has(toGroup.jobs[0]?.job_id.toString())

            return (
              <line
                key={index}
                x1={fromGroup.x + 80}
                y1={fromGroup.y + 30}
                x2={toGroup.x}
                y2={toGroup.y + 30}
                stroke={isHighlighted ? "#3b82f6" : "#6b7280"}
                strokeWidth={isHighlighted ? "3" : "2"}
                markerEnd="url(#arrowhead)"
                className="transition-all duration-200"
              />
            )
          })}

          {/* Arrow marker */}
          <defs>
            <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="#6b7280" />
            </marker>
          </defs>

          {/* Group nodes */}
          {groups.map((group) => {
            const groupStatus = getGroupStatus(group.jobs)
            const groupProgress = getGroupProgress(group.jobs)
            const jobIds = group.jobs.map((j) => j.job_id)
            const displayText = smartRangeDisplay(jobIds)
            const groupName = group.jobs[0].group_name || "root"
            const isHighlighted = group.jobs.some((job) => highlightedChain.has(job.job_id.toString()))

            return (
              <g key={group.id} className="transition-all duration-200">
                <rect
                  x={group.x}
                  y={group.y}
                  width="160"
                  height="60"
                  rx="8"
                  fill={getStatusColor(groupStatus)}
                  fillOpacity={isHighlighted ? "0.3" : "0.1"}
                  stroke={getStatusColor(groupStatus)}
                  strokeWidth={isHighlighted ? "3" : "2"}
                  className="cursor-pointer transition-all duration-200"
                  onClick={() => openGroupModal(group)}
                  onMouseEnter={(e) => handleNodeMouseEnter(group.jobs[0], group.id, e)}
                  onMouseLeave={handleNodeMouseLeave}
                  onContextMenu={(e) => handleContextMenu(e, group.jobs[0].job_id.toString())}
                />
                <text
                  x={group.x + 80} // Keep centered
                  y={group.y + 16}
                  textAnchor="middle"
                  className="text-sm font-bold fill-gray-900 pointer-events-none"
                >
                  #{displayText}
                </text>
                <text
                  x={group.x + 80}
                  y={group.y + 30}
                  textAnchor="middle"
                  className="text-xs fill-gray-600 pointer-events-none"
                >
                  {groupName}
                </text>
                <text
                  x={group.x + 80}
                  y={group.y + 42}
                  textAnchor="middle"
                  className="text-xs font-medium pointer-events-none"
                  fill={getStatusColor(groupStatus)}
                >
                  {groupStatus}
                </text>
                {getGroupProgress(group.jobs) > 0 && (
                  <rect
                    x={group.x + 10}
                    y={group.y + 48}
                    width={140 * (getGroupProgress(group.jobs) / 100)}
                    height="4"
                    rx="2"
                    fill={getStatusColor(groupStatus)}
                    fillOpacity="0.6"
                    className="pointer-events-none"
                  />
                )}
              </g>
            )
          })}
        </g>
      </svg>
      {/* Group Expansion Modal */}
      {expandedGroup && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onClick={closeGroupModal}
        >
          <div
            className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl max-h-[80vh] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Group: {smartRangeDisplay(expandedGroup.jobs.map((j) => j.job_id))}
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {expandedGroup.jobs[0].group_name} • {expandedGroup.jobs.length} jobs
                  </p>
                </div>
                <button
                  onClick={closeGroupModal}
                  className="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 text-xl font-bold"
                >
                  ×
                </button>
              </div>
            </div>

            <div className="p-6 overflow-y-auto max-h-96">
              <div className="grid gap-4">
                {expandedGroup.jobs.map((job) => (
                  <div
                    key={job.job_id}
                    className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:bg-gray-50 dark:hover:bg-gray-700"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-semibold">#{job.job_id}</span>
                        <Badge variant={getStatusVariant(job.status)} className="flex items-center gap-1">
                          {getStatusIcon(job.status)}
                          {job.status}
                        </Badge>
                      </div>
                    </div>

                    <code className="block bg-gray-100 dark:bg-gray-700 px-3 py-2 rounded text-sm mb-2 text-gray-900 dark:text-gray-100">
                      {job.command}
                    </code>

                    <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
                      <div>
                        {job.depends_on.length > 0 ? (
                          <span>Depends on: {job.depends_on.map((dep) => `#${dep}`).join(", ")}</span>
                        ) : (
                          <span>No dependencies</span>
                        )}
                      </div>

                      {job.status === "RUNNING" && job.stats && (
                        <div className="flex items-center gap-4">
                          <div className="flex items-center gap-1">
                            <HardDrive className="w-3 h-3" />
                            <span>
                              GPU: {job.stats.gpu_memory_used_mb}MB / {job.stats.gpu_memory_total_mb}MB
                            </span>
                          </div>
                          <div className="flex items-center gap-1">
                            <Cpu className="w-3 h-3" />
                            <span>GPUs: {job.stats.gpu_count}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const smartRangeDisplay = (jobIds: number[]): string => {
  const sorted = jobIds.sort((a, b) => a - b)

  if (sorted.length === 1) {
    return sorted[0].toString()
  } else if (sorted.length <= 3) {
    return sorted.join(", ")
  } else {
    const isContinuous = sorted.every((id, i) => i === 0 || id === sorted[i - 1] + 1)

    if (isContinuous) {
      return `${sorted[0]}-${sorted[sorted.length - 1]} (${sorted.length})`
    } else {
      return `${sorted[0]}...${sorted[sorted.length - 1]} (${sorted.length})`
    }
  }
}

export default function Component() {
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [groupFilter, setGroupFilter] = useState<string>("all")
  const [searchQuery, setSearchQuery] = useState<string>("")
  const [expandedGroupInTable, setExpandedGroupInTable] = useState<JobGroup | null>(null)
  const [tooltip, setTooltip] = useState<TooltipData>({ job: DUMMY_JOBS[0], x: 0, y: 0, visible: false })
  const [isDarkMode, setIsDarkMode] = useState(false)

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add("dark")
    } else {
      document.documentElement.classList.remove("dark")
    }
  }, [isDarkMode])

  const filteredJobs = useMemo(() => {
    return DUMMY_JOBS.filter((job) => {
      const matchesStatus = statusFilter === "all" || job.status.toLowerCase() === statusFilter.toLowerCase()
      const matchesGroup = groupFilter === "all" || job.group_name === groupFilter
      const matchesSearch =
        searchQuery === "" ||
        job.command.toLowerCase().includes(searchQuery.toLowerCase()) ||
        job.job_id.toString().includes(searchQuery)

      return matchesStatus && matchesGroup && matchesSearch
    })
  }, [statusFilter, groupFilter, searchQuery])

  const uniqueGroups = useMemo(() => {
    return Array.from(new Set(DUMMY_JOBS.map((job) => job.group_name).filter(Boolean)))
  }, [])

  const uniqueStatuses = useMemo(() => {
    return Array.from(new Set(DUMMY_JOBS.map((job) => job.status)))
  }, [])

  const groupedJobs = useMemo(() => {
    // Build parent-to-child mapping
    const parentToChildMap = new Map<string, Set<string>>()
    filteredJobs.forEach((job) => {
      const jobId = job.job_id.toString()
      job.depends_on.forEach((depId) => {
        if (!parentToChildMap.has(depId)) {
          parentToChildMap.set(depId, new Set())
        }
        parentToChildMap.get(depId)!.add(jobId)
      })
    })

    // Group jobs by their dependency signature
    const groupMap = new Map<string, Job[]>()
    filteredJobs.forEach((job) => {
      const jobId = job.job_id.toString()
      const parents = new Set(job.depends_on)
      const children = parentToChildMap.get(jobId) || new Set()

      const parentsKey = Array.from(parents).sort().join(",")
      const childrenKey = Array.from(children).sort().join(",")
      const signature = `${parentsKey}|${childrenKey}`

      if (!groupMap.has(signature)) {
        groupMap.set(signature, [])
      }
      groupMap.get(signature)!.push(job)
    })

    // Convert groups to JobGroup objects
    const groups: JobGroup[] = []
    let groupIndex = 0

    groupMap.forEach((groupJobs) => {
      const groupId = `group_${groupIndex++}`
      const firstJob = groupJobs[0]
      const parents = new Set(firstJob.depends_on)
      const children = parentToChildMap.get(firstJob.job_id.toString()) || new Set()

      groups.push({
        id: groupId,
        jobs: groupJobs,
        parents,
        children,
        x: 0,
        y: 0,
        level: 0,
      })
    })

    return groups
  }, [filteredJobs])

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-4">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">SLURM Job Dashboard</h1>
          <p className="text-gray-600 dark:text-gray-400">Monitor your job queue status and dependencies</p>
        </div>

        {/* Dark Mode Toggle */}
        <div className="mb-6 flex justify-end">
          <button
            onClick={() => setIsDarkMode(!isDarkMode)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            {isDarkMode ? (
              <>
                <Sun className="w-4 h-4 text-yellow-500" />
                <span className="text-gray-700 dark:text-gray-300">Light Mode</span>
              </>
            ) : (
              <>
                <Moon className="w-4 h-4 text-blue-500" />
                <span className="text-gray-700 dark:text-gray-300">Dark Mode</span>
              </>
            )}
          </button>
        </div>

        {/* Filters */}
        <Card className="bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700">
          <CardContent className="pt-6">
            <div className="flex flex-wrap gap-4 items-center">
              <div className="flex items-center gap-2">
                <Search className="w-4 h-4 text-gray-500" />
                <Input
                  placeholder="Search jobs..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-64"
                />
              </div>
              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-gray-500" />
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder="Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Statuses</SelectItem>
                    {uniqueStatuses.map((status) => (
                      <SelectItem key={status} value={status}>
                        {status}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-gray-500" />
                <Select value={groupFilter} onValueChange={setGroupFilter}>
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder="Group" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Groups</SelectItem>
                    {uniqueGroups.map((group) => (
                      <SelectItem key={group} value={group}>
                        {group}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">
                Showing {filteredJobs.length} of {DUMMY_JOBS.length} jobs
              </div>
            </div>
          </CardContent>
        </Card>

        <Tabs defaultValue="table" className="w-full">
          <TabsList className="grid w-full grid-cols-3 max-w-lg">
            <TabsTrigger value="table" className="flex items-center gap-2">
              <Terminal className="w-4 h-4" />
              Table View
            </TabsTrigger>
            <TabsTrigger value="grouped" className="flex items-center gap-2">
              <Users className="w-4 h-4" />
              Grouped Table
            </TabsTrigger>
            <TabsTrigger value="graph" className="flex items-center gap-2">
              <GitBranch className="w-4 h-4" />
              Dependency Graph
            </TabsTrigger>
          </TabsList>

          <TabsContent value="table" className="mt-6">
            <Card className="bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-gray-900 dark:text-white">
                  <Terminal className="w-5 h-5" />
                  Job Queue ({filteredJobs.length} jobs)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Table className="dark:text-gray-100">
                  <TableHeader>
                    <TableRow className="border-gray-200 dark:border-gray-700">
                      <TableHead className="text-gray-900 dark:text-gray-100">Job ID</TableHead>
                      <TableHead className="text-gray-900 dark:text-gray-100">Status</TableHead>
                      <TableHead className="text-gray-900 dark:text-gray-100">Command</TableHead>
                      <TableHead className="text-gray-900 dark:text-gray-100">Group</TableHead>
                      <TableHead className="text-gray-900 dark:text-gray-100">Resources</TableHead>
                      <TableHead className="text-gray-900 dark:text-gray-100">Dependencies</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredJobs.map((job) => (
                      <TableRow
                        key={job.job_id}
                        className="hover:bg-gray-50 dark:hover:bg-gray-700 border-gray-200 dark:border-gray-700"
                      >
                        <TableCell className="font-mono font-medium">#{job.job_id}</TableCell>
                        <TableCell>
                          <Badge variant={getStatusVariant(job.status)} className="flex items-center gap-1 w-fit">
                            {getStatusIcon(job.status)}
                            {job.status}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <code className="bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded text-sm text-gray-900 dark:text-gray-100">
                            {job.command}
                          </code>
                        </TableCell>
                        <TableCell>
                          {job.group_name ? (
                            <Badge variant="outline" className="flex items-center gap-1 w-fit">
                              <Users className="w-3 h-3" />
                              {job.group_name}
                            </Badge>
                          ) : (
                            <span className="text-gray-400">—</span>
                          )}
                        </TableCell>
                        <TableCell>
                          {job.status === "RUNNING" && job.stats ? (
                            <div className="space-y-1">
                              <div className="flex items-center gap-1 text-xs">
                                <HardDrive className="w-3 h-3" />
                                <span>
                                  {job.stats.gpu_memory_used_mb}MB / {job.stats.gpu_memory_total_mb}MB
                                </span>
                              </div>
                              <div className="flex items-center gap-1 text-xs">
                                <Cpu className="w-3 h-3" />
                                <span>{job.stats.gpu_count} GPUs</span>
                              </div>
                            </div>
                          ) : (
                            <span className="text-gray-400">—</span>
                          )}
                        </TableCell>
                        <TableCell>
                          {job.depends_on.length > 0 ? (
                            <div className="flex flex-wrap gap-1">
                              {job.depends_on.map((dep, index) => (
                                <Badge key={index} variant="outline" className="text-xs">
                                  #{dep}
                                </Badge>
                              ))}
                            </div>
                          ) : (
                            <span className="text-gray-400">None</span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="grouped" className="mt-6">
            <Card className="bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-gray-900 dark:text-white">
                  <Users className="w-5 h-5" />
                  Grouped Jobs ({groupedJobs.length} groups)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-gray-900 dark:text-gray-100">Job IDs</TableHead>
                      <TableHead className="text-gray-900 dark:text-gray-100">Group Name</TableHead>
                      <TableHead className="text-gray-900 dark:text-gray-100">Status</TableHead>
                      <TableHead className="text-gray-900 dark:text-gray-100">Progress</TableHead>
                      <TableHead className="text-gray-900 dark:text-gray-100">Dependencies</TableHead>
                      <TableHead className="text-gray-900 dark:text-gray-100">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {groupedJobs.map((group, index) => (
                      <TableRow key={index} className="hover:bg-gray-50">
                        <TableCell className="font-mono font-medium">
                          #{smartRangeDisplay(group.jobs.map((j) => j.job_id))}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className="flex items-center gap-1 w-fit">
                            <Users className="w-3 h-3" />
                            {group.jobs[0].group_name}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={getStatusVariant(getGroupStatus(group.jobs))}
                            className="flex items-center gap-1 w-fit"
                          >
                            {getStatusIcon(getGroupStatus(group.jobs))}
                            {getGroupStatus(group.jobs)}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Progress value={getGroupProgress(group.jobs)} className="w-20" />
                            <span className="text-xs text-gray-500">
                              {group.jobs.filter((j) => j.status === "COMPLETED").length}/{group.jobs.length}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          {group.jobs[0].depends_on.length > 0 ? (
                            <div className="flex flex-wrap gap-1">
                              {group.jobs[0].depends_on.map((dep, depIndex) => (
                                <Badge key={depIndex} variant="outline" className="text-xs">
                                  #{dep}
                                </Badge>
                              ))}
                            </div>
                          ) : (
                            <span className="text-gray-400">None</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <button
                            onClick={() => setExpandedGroupInTable(group)}
                            className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 text-sm"
                          >
                            View Jobs ({group.jobs.length})
                          </button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="graph" className="mt-6">
            <Card className="bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-gray-900 dark:text-white">
                  <GitBranch className="w-5 h-5" />
                  Dependency Graph
                </CardTitle>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Visual representation of job dependencies. Click groups to temporarily ungroup. Hover for details.
                </p>
              </CardHeader>
              <CardContent>
                <DependencyGraph jobs={filteredJobs} />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Grouped Table Expansion Modal */}
        {expandedGroupInTable && (
          <div
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
            onClick={() => setExpandedGroupInTable(null)}
          >
            <div
              className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl max-h-[80vh] overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="p-6 border-b border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                      Group: {smartRangeDisplay(expandedGroupInTable.jobs.map((j) => j.job_id))}
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {expandedGroupInTable.jobs[0].group_name} • {expandedGroupInTable.jobs.length} jobs •
                      {expandedGroupInTable.jobs.filter((j) => j.status === "COMPLETED").length} completed
                    </p>
                  </div>
                  <button
                    onClick={() => setExpandedGroupInTable(null)}
                    className="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 text-xl font-bold"
                  >
                    ×
                  </button>
                </div>
              </div>

              <div className="p-6 overflow-y-auto max-h-96">
                <Table className="dark:text-gray-100">
                  <TableHeader>
                    <TableRow className="border-gray-200 dark:border-gray-700">
                      <TableHead className="text-gray-900 dark:text-gray-100">Job ID</TableHead>
                      <TableHead className="text-gray-900 dark:text-gray-100">Status</TableHead>
                      <TableHead className="text-gray-900 dark:text-gray-100">Command</TableHead>
                      <TableHead className="text-gray-900 dark:text-gray-100">Resources</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {expandedGroupInTable.jobs.map((job) => (
                      <TableRow
                        key={job.job_id}
                        className="hover:bg-gray-50 dark:hover:bg-gray-700 border-gray-200 dark:border-gray-700"
                      >
                        <TableCell className="font-mono font-medium">#{job.job_id}</TableCell>
                        <TableCell>
                          <Badge variant={getStatusVariant(job.status)} className="flex items-center gap-1 w-fit">
                            {getStatusIcon(job.status)}
                            {job.status}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <code className="bg-gray-100 px-2 py-1 rounded text-sm">{job.command}</code>
                        </TableCell>
                        <TableCell>
                          {job.status === "RUNNING" && job.stats ? (
                            <div className="space-y-1">
                              <div className="flex items-center gap-1 text-xs">
                                <HardDrive className="w-3 h-3" />
                                <span>
                                  {job.stats.gpu_memory_used_mb}MB / {job.stats.gpu_memory_total_mb}MB
                                </span>
                              </div>
                              <div className="flex items-center gap-1 text-xs">
                                <Cpu className="w-3 h-3" />
                                <span>{job.stats.gpu_count} GPUs</span>
                              </div>
                            </div>
                          ) : (
                            <span className="text-gray-400">—</span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          </div>
        )}
      </div>
      <JobTooltip tooltip={tooltip} />
    </div>
  )
}
