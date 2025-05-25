"use client"

import type React from "react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
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
} from "lucide-react"
import { useMemo, useState, useRef, useEffect } from "react"

interface Job {
  job_id: number
  status: string
  command: string
  group_name: string
  depends_on: string[]
  cpu_usage?: number
  memory_usage?: number
  progress?: number
  start_time?: string
  estimated_duration?: number
}

const DUMMY_JOBS: Job[] = [
  {
    job_id: 789012,
    status: "COMPLETED",
    command: "jrun analyze --input dataset.csv --output results/",
    group_name: "data_prep",
    depends_on: [],
    cpu_usage: 0,
    memory_usage: 0,
    progress: 100,
    start_time: "2024-01-15T10:00:00Z",
    estimated_duration: 300,
  },
  {
    job_id: 123456,
    status: "RUNNING",
    command: "jrun viz --type scatter --input results/analysis.json",
    group_name: "visualization",
    depends_on: ["789012"],
    cpu_usage: 85,
    memory_usage: 60,
    progress: 65,
    start_time: "2024-01-15T10:05:00Z",
    estimated_duration: 180,
  },
  {
    job_id: 123457,
    status: "COMPLETED",
    command: "jrun viz --type histogram --input results/analysis.json",
    group_name: "visualization",
    depends_on: ["789012"],
    cpu_usage: 0,
    memory_usage: 0,
    progress: 100,
    start_time: "2024-01-15T10:05:00Z",
    estimated_duration: 120,
  },
  {
    job_id: 123458,
    status: "PENDING",
    command: "jrun viz --type boxplot --input results/analysis.json",
    group_name: "visualization",
    depends_on: ["789012"],
    cpu_usage: 0,
    memory_usage: 0,
    progress: 0,
    estimated_duration: 150,
  },
  {
    job_id: 345678,
    status: "COMPLETED",
    command: "jrun preprocess --input data.csv --normalize --scale",
    group_name: "preprocessing",
    depends_on: ["789012"],
    cpu_usage: 0,
    memory_usage: 0,
    progress: 100,
    start_time: "2024-01-15T10:05:00Z",
    estimated_duration: 240,
  },
  {
    job_id: 901234,
    status: "RUNNING",
    command: "jrun model_training --model linear --epochs 100",
    group_name: "ml_pipeline",
    depends_on: ["345678"],
    cpu_usage: 95,
    memory_usage: 80,
    progress: 45,
    start_time: "2024-01-15T10:10:00Z",
    estimated_duration: 600,
  },
  {
    job_id: 901235,
    status: "PENDING",
    command: "jrun model_training --model random_forest --trees 500",
    group_name: "ml_pipeline",
    depends_on: ["345678"],
    cpu_usage: 0,
    memory_usage: 0,
    progress: 0,
    estimated_duration: 800,
  },
  {
    job_id: 901236,
    status: "FAILED",
    command: "jrun model_training --model neural_net --layers 5",
    group_name: "ml_pipeline",
    depends_on: ["345678"],
    cpu_usage: 0,
    memory_usage: 0,
    progress: 25,
    start_time: "2024-01-15T10:10:00Z",
    estimated_duration: 1200,
  },
  {
    job_id: 567890,
    status: "PENDING",
    command: "jrun validation --cross-validate --folds 5",
    group_name: "validation",
    depends_on: ["123456", "123457", "345678"],
    cpu_usage: 0,
    memory_usage: 0,
    progress: 0,
    estimated_duration: 300,
  },
  {
    job_id: 567891,
    status: "PENDING",
    command: "jrun validation --holdout --split 0.2",
    group_name: "validation",
    depends_on: ["123456", "123457", "345678"],
    cpu_usage: 0,
    memory_usage: 0,
    progress: 0,
    estimated_duration: 200,
  },
  {
    job_id: 111222,
    status: "PENDING",
    command: "jrun report --format pdf --template executive",
    group_name: "reporting",
    depends_on: ["567890", "567891"],
    cpu_usage: 0,
    memory_usage: 0,
    progress: 0,
    estimated_duration: 60,
  },
  {
    job_id: 111223,
    status: "PENDING",
    command: "jrun report --format html --interactive",
    group_name: "reporting",
    depends_on: ["567890", "567891"],
    cpu_usage: 0,
    memory_usage: 0,
    progress: 0,
    estimated_duration: 90,
  },
  {
    job_id: 111224,
    status: "PENDING",
    command: "jrun report --format json --detailed",
    group_name: "reporting",
    depends_on: ["567890", "567891"],
    cpu_usage: 0,
    memory_usage: 0,
    progress: 0,
    estimated_duration: 30,
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
      className="absolute z-50 bg-white border border-gray-200 rounded-lg shadow-lg p-3 max-w-xs"
      style={{ left: tooltip.x + 10, top: tooltip.y - 10 }}
    >
      <div className="space-y-2">
        <div className="font-semibold">Job #{tooltip.job.job_id}</div>
        <div className="text-sm text-gray-600">{tooltip.job.command}</div>
        <div className="flex items-center gap-2">
          <Badge variant={getStatusVariant(tooltip.job.status)} className="text-xs">
            {tooltip.job.status}
          </Badge>
          {tooltip.job.progress !== undefined && <span className="text-xs text-gray-500">{tooltip.job.progress}%</span>}
        </div>
        {tooltip.job.status === "RUNNING" && (
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs">
              <Cpu className="w-3 h-3" />
              <span>CPU: {tooltip.job.cpu_usage}%</span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <HardDrive className="w-3 h-3" />
              <span>Memory: {tooltip.job.memory_usage}%</span>
            </div>
          </div>
        )}
        {tooltip.job.estimated_duration && (
          <div className="text-xs text-gray-500">Est. duration: {formatDuration(tooltip.job.estimated_duration)}</div>
        )}
      </div>
    </div>
  )
}

function DependencyGraph({ jobs }: { jobs: Job[] }) {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set())
  const [tooltip, setTooltip] = useState<TooltipData>({ job: jobs[0], x: 0, y: 0, visible: false })
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [isPanning, setIsPanning] = useState(false)
  const [draggedNode, setDraggedNode] = useState<string | null>(null)
  const [nodePositions, setNodePositions] = useState<Map<string, { x: number; y: number }>>(new Map())
  const [highlightedChain, setHighlightedChain] = useState<Set<string>>(new Set())
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; jobId: string; visible: boolean }>({
    x: 0,
    y: 0,
    jobId: "",
    visible: false,
  })
  const svgRef = useRef<SVGSVGElement>(null)

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
    const levelGroups = new Map<number, (JobGroup | Job)[]>()
    groups.forEach((group) => {
      if (!levelGroups.has(group.level)) {
        levelGroups.set(group.level, [])
      }

      if (expandedGroups.has(group.id)) {
        group.jobs.forEach((job) => {
          levelGroups.get(group.level)!.push(job)
        })
      } else {
        levelGroups.get(group.level)!.push(group)
      }
    })

    const levelSpacing = 200
    const nodeSpacing = 80
    const individualNodes: Array<Job & { x: number; y: number; groupId: string }> = []

    levelGroups.forEach((items, level) => {
      items.forEach((item, index) => {
        const totalItems = items.length
        const startY = (-(totalItems - 1) * nodeSpacing) / 2

        const baseX = level * levelSpacing + 80
        const baseY = startY + index * nodeSpacing + 250

        if ("jobs" in item) {
          // It's a group
          const customPos = nodePositions.get(item.id)
          item.x = customPos?.x ?? baseX
          item.y = customPos?.y ?? baseY
        } else {
          // It's an individual job
          const group = groups.find((g) => g.jobs.some((j) => j.job_id === item.job_id))!
          const customPos = nodePositions.get(`job-${item.job_id}`)
          individualNodes.push({
            ...item,
            x: customPos?.x ?? baseX,
            y: customPos?.y ?? baseY,
            groupId: group.id,
          })
        }
      })
    })

    // Create edges
    const finalEdges: GraphEdge[] = []
    groups.forEach((group) => {
      if (!expandedGroups.has(group.id)) {
        Array.from(group.parents).forEach((parentId) => {
          const parentGroup = groups.find((g) => g.jobs.some((j) => j.job_id.toString() === parentId))
          if (parentGroup && parentGroup.id !== group.id) {
            finalEdges.push({ from: parentGroup.id, to: group.id })
          }
        })
      }
    })

    return { groups, edges: finalEdges, individualNodes }
  }, [jobs, expandedGroups, nodePositions])

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
    if (e.button === 0 && !draggedNode) {
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

    if (draggedNode && svgRef.current) {
      const rect = svgRef.current.getBoundingClientRect()
      const x = (e.clientX - rect.left - pan.x) / zoom
      const y = (e.clientY - rect.top - pan.y) / zoom

      setNodePositions((prev) => new Map(prev.set(draggedNode, { x: x - 80, y: y - 30 })))
    }
  }

  const handleMouseUp = () => {
    setIsPanning(false)
    setDraggedNode(null)
  }

  const handleNodeMouseDown = (nodeId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setDraggedNode(nodeId)
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

  const getGroupStatus = (jobs: Job[]) => {
    const statusCounts = jobs.reduce(
      (acc, job) => {
        acc[job.status] = (acc[job.status] || 0) + 1
        return acc
      },
      {} as Record<string, number>,
    )

    const completed = statusCounts.COMPLETED || 0
    const total = jobs.length
    const hasRunning = statusCounts.RUNNING > 0
    const hasFailed = (statusCounts.FAILED || 0) + (statusCounts.CANCELLED || 0) > 0
    const hasPending = statusCounts.PENDING > 0

    if (hasFailed) return "FAILED"
    if (hasRunning) return "RUNNING"
    if (hasPending) return "PENDING"
    if (completed === total) return "COMPLETED"
    return "MIXED"
  }

  const getGroupProgress = (jobs: Job[]) => {
    const totalProgress = jobs.reduce((sum, job) => sum + (job.progress || 0), 0)
    return Math.round(totalProgress / jobs.length)
  }

  const toggleGroup = (groupId: string) => {
    const newExpanded = new Set(expandedGroups)
    if (newExpanded.has(groupId)) {
      newExpanded.delete(groupId)
    } else {
      newExpanded.add(groupId)
    }
    setExpandedGroups(newExpanded)
  }

  const svgWidth = Math.max(
    1000,
    (Math.max(...groups.map((g) => g.level), ...individualNodes.map((n) => Math.floor(n.x / 200))) + 1) * 200 + 160,
  )
  const svgHeight = Math.max(600, Math.max(...groups.map((g) => g.y), ...individualNodes.map((n) => n.y)) + 150)

  return (
    <div className="w-full overflow-hidden relative">
      {/* Zoom Controls */}
      <div className="absolute top-4 right-4 z-10 flex flex-col gap-2 bg-white border rounded-lg p-2 shadow-lg">
        <button
          onClick={() => setZoom((prev) => Math.min(3, prev * 1.2))}
          className="px-2 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded"
        >
          +
        </button>
        <span className="text-xs text-center">{Math.round(zoom * 100)}%</span>
        <button
          onClick={() => setZoom((prev) => Math.max(0.1, prev * 0.8))}
          className="px-2 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded"
        >
          -
        </button>
        <button
          onClick={() => {
            setZoom(1)
            setPan({ x: 0, y: 0 })
          }}
          className="px-2 py-1 text-xs bg-blue-100 hover:bg-blue-200 rounded"
        >
          Reset
        </button>
      </div>

      {/* Context Menu */}
      {contextMenu.visible && (
        <div
          className="absolute z-50 bg-white border border-gray-200 rounded-lg shadow-lg py-1"
          style={{ left: contextMenu.x, top: contextMenu.y }}
        >
          <button
            onClick={() => handleContextAction("view-logs", contextMenu.jobId)}
            className="block w-full px-4 py-2 text-sm text-left hover:bg-gray-100"
          >
            View Logs
          </button>
          <button
            onClick={() => handleContextAction("restart", contextMenu.jobId)}
            className="block w-full px-4 py-2 text-sm text-left hover:bg-gray-100"
          >
            Restart Job
          </button>
          <button
            onClick={() => handleContextAction("cancel", contextMenu.jobId)}
            className="block w-full px-4 py-2 text-sm text-left hover:bg-gray-100 text-red-600"
          >
            Cancel Job
          </button>
          <button
            onClick={() => handleContextAction("clone", contextMenu.jobId)}
            className="block w-full px-4 py-2 text-sm text-left hover:bg-gray-100"
          >
            Clone Job
          </button>
        </div>
      )}

      <svg
        ref={svgRef}
        width="100%"
        height="600"
        className="border rounded-lg bg-white cursor-grab"
        style={{ cursor: isPanning ? "grabbing" : draggedNode ? "grabbing" : "grab" }}
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
            if (!fromGroup || !toGroup || expandedGroups.has(fromGroup.id) || expandedGroups.has(toGroup.id))
              return null

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
            if (expandedGroups.has(group.id)) return null

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
                  onClick={() => toggleGroup(group.id)}
                  onMouseDown={(e) => handleNodeMouseDown(group.id, e)}
                  onMouseEnter={(e) => handleNodeMouseEnter(group.jobs[0], group.id, e)}
                  onMouseLeave={handleNodeMouseLeave}
                  onContextMenu={(e) => handleContextMenu(e, group.jobs[0].job_id.toString())}
                />
                <text
                  x={group.x + 20}
                  y={group.y + 16}
                  className="text-sm font-bold fill-gray-900 cursor-pointer pointer-events-none"
                >
                  {expandedGroups.has(group.id) ? "▼" : "▶"}
                </text>
                <text
                  x={group.x + 90}
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
                {groupProgress > 0 && (
                  <rect
                    x={group.x + 10}
                    y={group.y + 48}
                    width={140 * (groupProgress / 100)}
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

          {/* Individual job nodes */}
          {individualNodes.map((job) => {
            const isHighlighted = highlightedChain.has(job.job_id.toString())

            return (
              <g key={`individual-${job.job_id}`} className="transition-all duration-200">
                <rect
                  x={job.x}
                  y={job.y}
                  width="160"
                  height="50"
                  rx="6"
                  fill={getStatusColor(job.status)}
                  fillOpacity={isHighlighted ? "0.3" : "0.1"}
                  stroke={getStatusColor(job.status)}
                  strokeWidth={isHighlighted ? "3" : "2"}
                  className="cursor-pointer transition-all duration-200"
                  onMouseDown={(e) => handleNodeMouseDown(`job-${job.job_id}`, e)}
                  onMouseEnter={(e) => handleNodeMouseEnter(job, `job-${job.job_id}`, e)}
                  onMouseLeave={handleNodeMouseLeave}
                  onContextMenu={(e) => handleContextMenu(e, job.job_id.toString())}
                />
                <text
                  x={job.x + 80}
                  y={job.y + 16}
                  textAnchor="middle"
                  className="text-sm font-bold fill-gray-900 pointer-events-none"
                >
                  #{job.job_id}
                </text>
                <text
                  x={job.x + 80}
                  y={job.y + 30}
                  textAnchor="middle"
                  className="text-xs fill-gray-600 pointer-events-none"
                >
                  {job.status}
                </text>
                {job.progress !== undefined && job.progress > 0 && (
                  <rect
                    x={job.x + 10}
                    y={job.y + 38}
                    width={140 * (job.progress / 100)}
                    height="3"
                    rx="1.5"
                    fill={getStatusColor(job.status)}
                    fillOpacity="0.6"
                    className="pointer-events-none"
                  />
                )}
              </g>
            )
          })}
        </g>
      </svg>
      <JobTooltip tooltip={tooltip} />
    </div>
  )
}

export default function Component() {
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [groupFilter, setGroupFilter] = useState<string>("all")
  const [searchQuery, setSearchQuery] = useState<string>("")

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

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">SLURM Job Dashboard</h1>
          <p className="text-gray-600">Monitor your job queue status and dependencies</p>
        </div>

        {/* Filters */}
        <Card className="mb-6">
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
              <div className="text-sm text-gray-500">
                Showing {filteredJobs.length} of {DUMMY_JOBS.length} jobs
              </div>
            </div>
          </CardContent>
        </Card>

        <Tabs defaultValue="table" className="w-full">
          <TabsList className="grid w-full grid-cols-2 max-w-md">
            <TabsTrigger value="table" className="flex items-center gap-2">
              <Terminal className="w-4 h-4" />
              Table View
            </TabsTrigger>
            <TabsTrigger value="graph" className="flex items-center gap-2">
              <GitBranch className="w-4 h-4" />
              Dependency Graph
            </TabsTrigger>
          </TabsList>

          <TabsContent value="table" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Terminal className="w-5 h-5" />
                  Job Queue ({filteredJobs.length} jobs)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Job ID</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Progress</TableHead>
                      <TableHead>Command</TableHead>
                      <TableHead>Group</TableHead>
                      <TableHead>Resources</TableHead>
                      <TableHead>Dependencies</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredJobs.map((job) => (
                      <TableRow key={job.job_id} className="hover:bg-gray-50">
                        <TableCell className="font-mono font-medium">#{job.job_id}</TableCell>
                        <TableCell>
                          <Badge variant={getStatusVariant(job.status)} className="flex items-center gap-1 w-fit">
                            {getStatusIcon(job.status)}
                            {job.status}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {job.progress !== undefined ? (
                            <div className="flex items-center gap-2">
                              <Progress value={job.progress} className="w-16" />
                              <span className="text-xs text-gray-500">{job.progress}%</span>
                            </div>
                          ) : (
                            <span className="text-gray-400">—</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <code className="bg-gray-100 px-2 py-1 rounded text-sm">{job.command}</code>
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
                          {job.status === "RUNNING" ? (
                            <div className="space-y-1">
                              <div className="flex items-center gap-1 text-xs">
                                <Cpu className="w-3 h-3" />
                                <span>{job.cpu_usage}%</span>
                              </div>
                              <div className="flex items-center gap-1 text-xs">
                                <HardDrive className="w-3 h-3" />
                                <span>{job.memory_usage}%</span>
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

          <TabsContent value="graph" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <GitBranch className="w-5 h-5" />
                  Dependency Graph
                </CardTitle>
                <p className="text-sm text-gray-600">
                  Visual representation of job dependencies. Click groups to expand. Hover for details.
                </p>
              </CardHeader>
              <CardContent>
                <DependencyGraph jobs={filteredJobs} />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
